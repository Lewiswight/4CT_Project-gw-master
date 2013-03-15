"""\
Value based annotation service

Transforms Samples into AnnotatedSamples at channel publication time
based on user configuration data.
"""
import traceback, sys
from copy import copy

from services.service_base import ServiceBase
from settings.settings_base import SettingsBase, Setting
from channels.channel_source import ChannelSource
from channels.channel_database import ChannelDoesNotExist

from samples.sample import Sample
from annotated_sample import AnnotatedSample

class ChannelSourceAnnotatedProperty(ChannelSource):
    """\
    Channel Source for timing annotation
    
    When a channel becomes configured for annotation, this object will 
    replace it in the channel database, so that writes will properly   
    receive their annotations.

    This channel source works by replacing an existing channel source
    in the channel database and intercepting published Sample objects
    in order to analyze them using the configured expression.  It
    stores a local copy of the previous channel source in order to complete
    the publish operation.

    .. note::
        This ChannelSource implementation is intended to be used
        specifically to implement the functionality of the class
        :class:`ValueService` and may not be appropriate for general
        usage.
"""    
    
    def __init__(self):
        """\
        Initialize ChannelSourceAnnotatedProperty

        .. warning::
            A newly created object is not useful until it has had a
            source attached and annotations configured.
        """
        self._source = None
        self._annotations = []

    # inherited interface functions from ChannelSource
    
    def producer_get(self):
        """Direct passthrough to linked :class:`ChannelSource`"""

        return self._source.producer_get()

    def producer_set(self, sample):
        """\
        Check annotations and pass resulting
        :class:`Sample` or :class:`AnnotatedSample` to linked
        :class:`ChannelSource`
        """
        sample = self._annotate(sample)
        self._source.producer_set(sample)

    def consumer_refresh(self):
        """Direct passthrough to linked :class:`ChannelSource`"""

        self._source.consumer_refresh()

    def consumer_get(self):
        """Direct passthrough to linked :class:`ChannelSource`"""

        return self._source.consumer_get()

    def consumer_set(self, sample):
        """\
        Check annotations and pass resulting
        :class:`Sample` or :class:`AnnotatedSample` to linked
        :class:`ChannelSource`
        """

        sample = self._annotate(sample)
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

    def clear_annotations(self):
        """\
        Remove any :class:`Annotation`s from the object.

        If no annotations exist, this purely passes Samples on
        untouched.
        """
        self._annotations = []

    def add_annotation(self, a):
        """\
        Add an :class:`Annotation` object to the list to be checked on
        each set
        """
        self._annotations.append(a)

    def _annotate(self, sample):
        # Iterate over all of the Annotation objects checking their
        # expressions for transformation into an AnnotatedSample
        for annotation in self._annotations:
            sample = annotation.annotate(sample)

        return sample

class Annotation(SettingsBase):
    """\
    Helper class for tracking expressions for :class:`ValueService`
    """
    
    def __init__(self, parent, channel, tag):
        """\
        Create a new :class:`Annotation`

        parent
            :class:`ValueService` instance managing this object

        channel
            Channel name of channel this annotation will act upon.

        tag
            name to place in :class:`AnnotatedSample` set if
            annotation needs to occur

        :class:`Annotation` objects inherit from :class:`SettingsBase`
        with a binding beneath that of the parent
        :class:`ValueService` and take the following settings.

        Settings
            expr (required)
                Python expression that must evaluate to a boolean.
                When true, the `tag` will be annotated on the
                :class:`AnnotatedSample` object. The sample object
                will be available as the symbol `sample.
            error (optional, default: True)
                Boolean value that determines the set to annotate
                within. On `True` the `tag` will be placed in the
                `errors` set.  It will be placed in `other` on `False`
            
        """
        self._parent = parent
        self._channel_name = channel
        self._tag_name = tag

        settings_list = [
            Setting(
                name='expr', type=str, required=True),
            Setting(
                name='error', type=bool, required=False,
                default_value=True),
        ]
        # Use parent binding to create our own child binding 
        SettingsBase.__init__(self, 
                              binding=parent._settings_binding + \
                                  ((channel,),
                                   'checks',
                                   (tag,),
                                   'definition'), 
                              setting_defs=settings_list)

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
            print "Settings rejected/not found: %s %s" % (rejected, not_found)

        SettingsBase.commit_settings(self, accepted)

        return (accepted, rejected, not_found)

    def annotate(self, sample):
        """Evaluate object expression and annotated `sample` if necessary"""
    
        expr = self.get_setting('expr')

        # evaluation namespace
        eval_ns = { }
        eval_ns.update(globals())
        eval_ns["sample"] = copy(sample)

        try:
            value = eval(expr, eval_ns)
        except:
            exc = sys.exc_info()
            raise ValueError, \
                "Annotation(%s:%s) ERROR: failed to evaluate expression:\n%s" \
                % (channel_name, tag,
                    "".join(traceback.format_exception_only(exc[0], exc[1])))

        if value:
            if not isinstance(sample, AnnotatedSample):
                sample = AnnotatedSample(sample)

            if self.get_setting('error'):
                sample.errors.add(self._tag_name)
            else:
                sample.other.add(self._tag_name)
                
        return sample
                             

class ValueService(ServiceBase):
    """\
    Annotate system based on configurable value expressions.

    Given a list of criteria, this service will cause :class:`Sample`
    objects published to the channel database to be replaced with
    :class:`AnnotatedSample` objects when those expressions evaluate
    to true.

    Example configuration block::

      - name: value0
        driver: services.value_service:ValueService
        settings:
          - name: template.counter
            checks:
              - name: too_high
                definition:
                  expr: sample.value > 100
                  error: False

    The `settings` are a list of individual annotations, each
    annotation has a `name` which is the name of the channel it
    applies to, as well as a 'checks' section.

    The `checks` section of each annotation in turn is a list of
    criteria to be checked against the top level channel.  Each
    element of the list contains a name, which is the tag to assign to
    an :class:`AnnotatedSample` and a definition, which is described
    as a subsidiary settings binding managed by :class:`Annotation`.
    """
    def __init__(self, name, core_services):
        """Standard :class:`ServiceBase` initialization"""
        self.__name = name
        self.__core = core_services

        self._channel_sources = {}
        self._enrolled_sources = {}

        settings_list = [
            Setting(
                name='instance_list', type=list, required=False,
                default_value=[]),
        ]

        ServiceBase.__init__(self, name, settings_list)

    def _destroy_existing_annotations(self):
        # Walk through all ChannelSourceAnnotatedProperty objects and
        # clear their annotation list in preparation for
        # re-configuration.
        for source in self._channel_sources.values():
            source.clear_annotations()           

    def _enumerate_channel_settings(self):
        # Walk instance list and if necessary create
        # ChannelSourceAnnotatedProperty objects for each channel,
        # populate them with Annotation objects
        chans = self.get_setting('instance_list')

        for item in chans:
            if not item['name'] in self._channel_sources:                
                channel_source = self._channel_sources[item['name']] = \
                    ChannelSourceAnnotatedProperty()
            else:
                channel_source = self._channel_sources[item['name']]
            
            for check in item['checks']['instance_list']:
                # BUG?: We may have an object leak on reconfiguration
                # here. The global setting binding registry may keep
                # old Annotation bindings in the system. In fact, it
                # probably does.  We probably want to calculate the
                # binding here and see if we can re-use an existing
                # Annotation object. Another way to 'fix' would be to
                # only allow a single binding at each location.
                channel_source.add_annotation(Annotation(self, 
                                                         item['name'],
                                                         check['name']))

    def _enroll_single_source(self, channel_name):
#       # Add a single channel into the channel database
        # Channel.__source object.
        source = self._channel_sources[channel_name]
        cm = self.__core.get_service('channel_manager')
        cdb = cm.channel_database_get()

        try:
            chan = cdb.channel_get(channel_name)
        except KeyError:
            # Subscribe with ChannelPublisher and try again later
            print "ValueService(%s) WARNING: %s does not yet exist" % (
                self.__name, channel_name)

            cp = cm.channel_publisher_get()
            cp.subscribe(channel_name, self._new_channel)
            return False

        # Put our own source in to replace the existing one
        # OUCH, kind of cheating here
        # TODO: modify these object interfaces to be more cleanly reciprocal
        source.set_source(chan._Channel__channel_source)
        chan._Channel__channel_source = source

        self._enrolled_sources[channel_name] = source
        return True
    
    def _enroll_channel_sources(self):
        # Find ChannelSourceAnnotatedProperty objects that have not
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
            # Re-call so that we have a possibly annotated start value
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
            print "ValueService(%s) Settings rejected/not found: %s %s" % (
                self.__name, rejected, not_found)

        SettingsBase.commit_settings(self, accepted)

        # Tear down and rebuild annotation system
        self._destroy_existing_annotations()
        self._enumerate_channel_settings()
        self._enroll_channel_sources()

        return (accepted, rejected, not_found)

    def start(self):
        pass

    def stop(self):
        pass
