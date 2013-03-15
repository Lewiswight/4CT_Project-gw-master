

"""
Device that determines a change in state of a digital input latches it in the current state until it changes.

* **digital_source** is the channel to subscribe too, which is assumed the be
  digital input value

Example: YML

  - name: digital_latch
    driver: devices.vendors.comverge.digitallatch:DigitalLatchDevice
    settings:
        digital_source: digitalio.channel1_input
		latch: TRUE

"""

#Imports
from devices.device_base import DeviceBase
from settings.settings_base import SettingsBase, Setting
from channels.channel_source_device_property import *
from channels.channel_manager import ChannelManager
import sys
import traceback

#Constants

#Exception classes
class RunTimeInitError(Exception):
    pass

#Interface functions

#Classes
class DigitalLatchDevice( DeviceBase):

    DIGITAL_SOURCE = 'digital_source'        # adds time to totalizers
    #TOTAL_OUT = 'total'
    LATCH_OUT = 'latch'
    #HOURLY_OUT = 'hourly'
    #DAILY_OUT = 'daily'

    def __init__(self, name, core_services):
        self.__name = name
        self.__core = core_services
        self.show_name = 'DigLatch(%s)' % name

        # hold last totalizer - start as invalid
        self.input_last = None
        self.latch_out = None

        ##Settings Table Definition:
        settings_list = [
            # subscription to totalizer source
            Setting( name=self.DIGITAL_SOURCE, type=str, required=True),

            # enable the delta output channel
            Setting( name=self.LATCH_OUT, type=str, required=False,
                default_value='False'),

            # enable the hourly output channel(s)
            #Setting( name=self.HOURLY_OUT, type=str, required=False,
             #   default_value='False'),

            # enable the daily output channel(s)
            #Setting( name=self.DAILY_OUT, type=str, required=False,
            #    default_value='False'),

        ]

        ##Channel Properties Definition:
        ##Properties are added dynamically based on configured transforms
        property_list = [
            # an input to RESET the totals
            #ChannelSourceDeviceProperty(name=self.TOTAL_OUT, type=int,
            #    initial=Sample(timestamp=0, value=-1),
            #    perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),

            ]

        ## Initialze the Devicebase interface:
        DeviceBase.__init__(self, self.__name, self.__core,
                                settings_list, property_list)
        return

    ##Functions which must be implemented to conform to the DeviceBase
    ##interface:
    def apply_settings(self):
        """Called when new configuration settings are available."""

        SettingsBase.merge_settings(self)
        accepted, rejected, not_found = SettingsBase.verify_settings(self)

        if len(rejected) or len(not_found):
            # there were problems with settings, terminate early:
            print "%s: Settings rejected/not found: %s %s" % \
                (self.show_name, rejected, not_found)

        else:
            SettingsBase.commit_settings(self, accepted)
            # print "%s: Settings accepted: %s" % (self.show_name, accepted)

        return (accepted, rejected, not_found)

    def start(self):
        """Start the device driver. Returns bool."""

        cm = self.__core.get_service("channel_manager")
        cp = cm.channel_publisher_get()
        # cdb = cm.channel_database_get()

        # get the totalizer source, fault is bad/missing
        x = SettingsBase.get_setting(self, self.DIGITAL_SOURCE)
        try:
            cp.subscribe( x, self.prop_new_total )
            bTimeSource = True
            print '%s: digital source channel is %s' % (self.show_name, x)
        except:
            traceback.print_exc()
            print '%s: no %s Channel (is bad!)' % (self.show_name,x)
            # return False

        # see if we want the delta channel
        try:
            x = eval( SettingsBase.get_setting(self, self.LATCH_OUT))
            print '%s: latch channel is %s' % (self.show_name,x)

            self.latch_out = x
            if self.latch_out:
                # then create them
                self.add_property(
                    ChannelSourceDeviceProperty(
                        name='latch', type=bool,
                        initial=Sample(0, False, 'bool' ),
                        perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP)
                    )

        except:
            traceback.print_exc()
            print '%s: latch channel failed' % self.show_name

        # see if we want the hourly channel
       # try:
       #     x = eval( SettingsBase.get_setting(self, self.HOURLY_OUT))
       #     print '%s: hourly channel is %s' % (self.show_name,x)

        #    if x:
                # then create the channels
        #        self.hourly = [-1,0]
        #        self.add_property(
         #           ChannelSourceDeviceProperty(
         #               name='hourly_last', type=int,
         #               initial=Sample(0, -1, '' ),
         #               perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP)
          #          )

        #except:
        #    traceback.print_exc()
        #    print '%s: hourly channel failed' % self.show_name

            # Setting( name=self., type=str, required=False,
            # Setting( name=self.DAILY_OUT, type=str, required=False,

        return True

    def stop(self):
        """Stop the device driver. Returns bool."""
        return True

#Internal functions & classes

    def prop_new_total( self, sam):
        # someone pushing in new input

        if( not isinstance( sam, Sample)):
            # the publish/sub pushes in the channel
            sam = sam.get()

        now = time.time()
        now_tup = None

        if( sam.unit == 'time'):
            # then assume is alarm_clock device as:
            # (1244544360.0, (2009, 6, 9, 10, 46, 0, 1, 160, -1))
            input_now = bool(sam.value[0])
        else:
            input_now = bool(sam.value)

        if self.input_last is None:
            # then is the first run
            self.input_last = input_now
            return True

        # we always calc delta to watch for garbage input
        #delta = total_now - self.total_last

        if input_now == self.input_last:
            # then no transition occured
            self.input_last = input_now
            change = False

        else: # else a transition
            print '%s: Update latch channel as:%d' % (self.__name, input_now)
            self.property_set( self.LATCH_OUT, Sample(now, input_now, 'latch'))
            self.input_error = None
            self.input_last = input_now

        # update the delta output channel (if we have)
        #if self.delta_out:
         #   print '%s: Update delta channel as:%d' % (self.__name, delta)
          #  self.property_set( self.DELTA_OUT, Sample(now,
           #                 delta, 'total') )
        return True
