"""\
Tank Demo Control Driver
"""

# imports
from devices.device_base import DeviceBase
from settings.settings_base import SettingsBase, Setting
from channels.channel_source_device_property import *

from common.types.boolean import Boolean, STYLE_ONOFF

# constants
LEFT_VOLUME_CHANNEL = 'left_volume_channel'
RIGHT_VOLUME_CHANNEL = 'right_volume_channel'

STATE_PUMP_OUT_LEFT = 0
STATE_PUMP_OUT_RIGHT = 1

# classes
class TankDemoControl(DeviceBase):

    def __init__(self, name, core_services):
        self.__name = name
        self.__core = core_services

        ## Local State Variables:
        self.__state = STATE_PUMP_OUT_LEFT

        ## Settings Table Definition:
        settings_list = [
            Setting(name=LEFT_VOLUME_CHANNEL, type=str, required=True),
            Setting(name=RIGHT_VOLUME_CHANNEL, type=str, required=True),
            Setting(
                name='transition_threshold', type=float, required=False,
                default_value=5.0,
                verify_function=lambda x: x > 0),
        ]

        ## Channel Properties Definition:
        property_list = [
            # gettable properties
            ChannelSourceDeviceProperty(name="left_pump_on",
                type=Boolean,
                initial=Sample(0, Boolean(False, STYLE_ONOFF)),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name="right_pump_on",
                type=Boolean,
                initial=Sample(0, Boolean(False, STYLE_ONOFF)),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
        ]
                                            
        ## Initialize the DeviceBase interface:
        DeviceBase.__init__(self, self.__name, self.__core,
                                settings_list, property_list)


    ## Functions which must be implemented to conform to the DeviceBase
    ## interface:

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
            # there were problems with settings, terminate early:
            print "Settings rejected/not found: %s/%s" % (rejected, not_found)
            return (accepted, rejected, not_found)

        SettingsBase.commit_settings(self, accepted)

        return (accepted, rejected, not_found)

    def start(self):
        """Start the device driver.  Returns bool."""

        cm = self.__core.get_service("channel_manager")
        cp = cm.channel_publisher_get()
        cdb = cm.channel_database_get()

        left_channel_name = SettingsBase.get_setting(self, LEFT_VOLUME_CHANNEL)
        left_channel = cdb.channel_get(left_channel_name)
        right_channel_name = SettingsBase.get_setting(self, RIGHT_VOLUME_CHANNEL)
        right_channel = cdb.channel_get(right_channel_name)

        # Determine initial state:
        if left_channel.get().value >= right_channel.get().value:
            print "INIT LEFT: volume is %f" % (left_channel.get().value)
            self.__state = STATE_PUMP_OUT_LEFT
            self.property_set("left_pump_on",
                Sample(0, Boolean(True, STYLE_ONOFF)))
        else:
            print "INIT RIGHT: volume is %f" % (right_channel.get().value)
            self.__state = STATE_PUMP_OUT_RIGHT
            self.property_set("right_pump_on",
                Sample(0, Boolean(True, STYLE_ONOFF)))

        # Perform channel subscriptions:
        cp.subscribe(left_channel_name,
            lambda chan: self.tank_volume_update(chan, LEFT_VOLUME_CHANNEL))
        cp.subscribe(right_channel_name,
            lambda chan: self.tank_volume_update(chan, RIGHT_VOLUME_CHANNEL))


        return True

    def stop(self):
        """Stop the device driver.  Returns bool."""

        return True
        

    ## Locally defined functions:
    def tank_volume_update(self, channel, which):

        transition_threshold = \
            SettingsBase.get_setting(self, 'transition_threshold')

        if which == LEFT_VOLUME_CHANNEL and \
            self.__state == STATE_PUMP_OUT_LEFT:
            new_volume = channel.get().value
            if new_volume <= transition_threshold:
                self.__state = STATE_PUMP_OUT_RIGHT
                self.property_set("left_pump_on",
                    Sample(0, Boolean(False, STYLE_ONOFF)))
                self.property_set("right_pump_on",
                    Sample(0, Boolean(True, STYLE_ONOFF)))

        elif which == RIGHT_VOLUME_CHANNEL and \
            self.__state == STATE_PUMP_OUT_RIGHT:
            new_volume = channel.get().value
            if new_volume <= transition_threshold:
                self.__state = STATE_PUMP_OUT_LEFT
                self.property_set("left_pump_on",
                    Sample(0, Boolean(True, STYLE_ONOFF)))
                self.property_set("right_pump_on",
                    Sample(0, Boolean(False, STYLE_ONOFF)))

        return


# internal functions & classes

def main():
    pass

if __name__ == '__main__':
    import sys
    status = main()
    sys.exit(status)

