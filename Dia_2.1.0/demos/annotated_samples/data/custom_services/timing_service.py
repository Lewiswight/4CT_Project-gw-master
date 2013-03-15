"""\
Timing based annotation service

Transforms Samples into AnnotatedSamples at the expiration of a
timeout based on user configuration data.
"""
import traceback, sys

from services.service_base import ServiceBase
from settings.settings_base import SettingsBase, Setting
from channels.channel_source import ChannelSource
from channels.channel_database import ChannelDoesNotExist

from samples.sample import Sample
from annotated_sample import AnnotatedSample

class ChannelSourceTimedProperty(ChannelSource):
    """\
    Channel Source for timing annotation
    
    When a channel becomes configured for annotation, this object will 
    replace it in the channel database, so that writes will properly   
    receive their annotations.

    This channel source works by replacing an existing channel source
    in the channel database and intercepting published Sample objects
    in order to track them for possible annotation in the future.  It
    stores a local copy of the previous source in order to complete
    the publish operation.

    .. note::
        This ChannelSource implementation is intended to be used
        specifically to implement the functionality of the class
        :class:`TimingService` and may not be appropriate for general
        usage.
"""    
    def __init__(self, scheduler, channel_name = "", timeout = None):
        """\
        Initialize ChannelSourceTimed property

        scheduler
            A reference to the scheduler service that is used to
            trigger the events that compute time out of sample data.

        channel_name
            The name of the channel being timed.

        timeout
            The interval after which data last received on this
            channel will be considered stale.
        """
        self._source = None
        self._event_handle = None
        self._timeout = timeout
        self._scheduler = scheduler

        self._channel_name = channel_name

    # inherited interface functions from ChannelSource

    def producer_get(self):
        """Direct passthrough to linked :class:`ChannelSource`"""
        return self._source.producer_get()

    def producer_set(self, sample):
        """Passthrough to linked :class:`ChannelSource`.

        Schedules a timeout to expire data if necessary"""
        self._schedule()
        self._source.producer_set(sample)

    def consumer_refresh(self):
        """Direct passthrough to linked :class:`ChannelSource`"""
        self._source.consumer_refresh()

    def consumer_get(self):
        """Direct passthrough to linked :class:`ChannelSource`"""
        return self._source.consumer_get()

    def consumer_set(self, sample):
        """Passthrough to linked :class:`ChannelSource`.

        Schedules a timeout to expire data if necessary"""
        self._schedule()
        self._source.consumer_set(sample)

    # Class specialization logic

    def set_source(self, source):
        """\
        Link this source to the original channel database source

        source
            Original channel source from channel database.
        """
        self._source = source
        self.type = source.type
        self.perms_mask = source.perms_mask
        self.options = source.options

    def get_source(self):
        """Retrieve linked channel source"""
        return self._source

    def clear_timeout(self):
        """\
        Disable timeout annotation behavior of channel source.

        Remains linked
        """
        self._timeout = None
        self._cancel_event()

    def set_timeout(self, timeout):
        """Set timeout value to use to expire channel"""
        
        self._timeout = timeout

    def _schedule(self):
        # Sets a new event in the scheduler to check for staleness of
        # channel data
        
        print "Scheduling %s: +%s" % (self._channel_name, self._timeout)
        self._cancel_event()

        if self._timeout:
            self._event_handle = self._scheduler.schedule_after(
                                            self._timeout, self._expire)
    
    def _cancel_event(self):
        # Cancel any outstanding event yet to trigger in the
        # scheduler.
        
        if self._event_handle:
            # The use of a heapq object in the common scheduler may
            # result in some unnecessary performance hits here.
            # Removal requires a re-heapify of the heap in O(n) time.
            # Not bad, but not really optimal, the scheduler is
            # optimized for insertion, not removal.  However saving
            # ourselves the thread overhead is probably well worth it.
            self._scheduler.cancel(self._event_handle)
            self._event_handle = None

    def _expire(self):
        # Callback that gets run when a timing event triggers from the
        # scheduler. 
        sample = self._source.producer_get()
        if not isinstance(sample, AnnotatedSample):
            sample = AnnotatedSample(sample)

        sample.errors.add('timeout')
        self._source.producer_set(sample)
        self._event_handle = None

class TimingService(ServiceBase):
    """\
    Annotate system based on configurable timing characteristics.

    Given a list of channels and timeout values, this service will
    cause :class:`Sample` objects published to the channel database to
    be replaced with :class:`AnnotatedSample` objects with an error
    value of `timeout` if the sample is not replaced in the given time
    period.

    Example configuration block::

      - name: timing0
        driver: services.timing_service:TimingService
        settings:
          timings:
            template.counter: 1

    Settings

      timings
          This is a dictionary of key value pairs.  The key is the
          channel name to impose a timing limitation upon and the
          value is the seconds after which any data published to the
          channel is deemed to have timed out.
    """
    def __init__(self, name, core_services):
        """\
        Initialize TimingService

        Standard service arguments see :class:`ServiceBase`
        """

        self.__name = name
        self.__core = core_services

        self._channel_sources = {}
        self._enrolled_sources = {}

        settings_list = [
            Setting(
                name='timings', type=dict, required=False,
                default_value=[]),
        ]

        ServiceBase.__init__(self, name, settings_list)

    def _destroy_timers(self):
        # Walk through all ChannelSourceTimedProperty objects and
        # clear them in preparation for re-configuration.
        for source in self._channel_sources.values():
            source.clear_timeout()           

    def _create_timers(self):
        # Walk instance list and if necessary create
        # ChannelSourceTimedProperty objects for each channel,
        scheduler = self.__core.get_service('scheduler')
        chans = self.get_setting('timings')

        for channel_name in chans:
            if not channel_name in self._channel_sources:
                channel_source = self._channel_sources[channel_name] = \
                    ChannelSourceTimedProperty(scheduler, channel_name)
            else:
                channel_source = self._channel_sources[item['name']]

            channel_source.set_timeout(chans[channel_name])

    def _enroll_single_source(self, channel_name):
        # Add a single channel into the channel database
        # Channel.__source object.
        source = self._channel_sources[channel_name]
        cm = self.__core.get_service('channel_manager')
        cdb = cm.channel_database_get()

        try:
            chan = cdb.channel_get(channel_name)
        except KeyError:
            # Subscribe with ChannelPublisher and try again later
            print "TimingService(%s) WARNING: %s does not yet exist" % (
                self.__name, channel_name)

            cp = cm.channel_publisher_get()
            cp.subscribe(channel_name, self._new_channel)
            return False

        # Put our own source in to replace the existing one
        # TODO: modify reciprocal interfaces to clean this up
        # OUCH, kind of cheating here
        source.set_source(chan._Channel__channel_source)
        chan._Channel__channel_source = source

        self._enrolled_sources[channel_name] = source
        return True
    
    def _enroll_channel_sources(self):
        # Find ChannelSourceTimedProperty objects that have not
        # been placed into the channel database and add them as the
        # Channel.__source object in the DB.  If we can't find a
        # channel in the database, it may not be present yet.  Use the
        # ChannelPublisher so that we can subscribe to it for
        # enrollment later.  Emit a warning.
        for channel_name in self._channel_sources:
            if not channel_name in self._enrolled_sources:
                self._enroll_single_source(channel_name)
                
    def _new_channel(self, channel):
        # Our ChannelPublisher callback.  We install it if a channel
        # was not present during configuration.
        cm = self.__core.get_service('channel_manager')
        cp = cm.channel_publisher_get()
        cp.unsubscribe(channel.name(), self._new_channel)

        if self._enroll_single_source(channel.name()):
            # Re-call so that we can start timing from this point
            channel.producer_set(channel.producer_get())

    def apply_settings(self):
        """\
            Called when new configuration settings are available.
       
            Must return tuple of three dictionaries: a dictionary of
            accepted settings, a dictionary of rejected settings,
            and a dictionary of required settings that were not
            found.
        """
        
        SettingsBase.merge_settings(self)
        accepted, rejected, not_found = SettingsBase.verify_settings(self)
        if len(rejected) or len(not_found):
            print "TimingService(%s) Settings rejected/not found: %s %s" % (
                self.__name, rejected, not_found)

        SettingsBase.commit_settings(self, accepted)

        # Tear down and rebuild annotation system, this does mean that
        # reconfiguration will cause a window where stale data will
        # not be reported at the time where it technically becomes
        # stale under either configuration necessarily.
        self._destroy_timers()
        self._create_timers()
        self._enroll_channel_sources()

        return (accepted, rejected, not_found)

    def start(self):
        pass

    def stop(self):
        pass
