"""
Digi Tank Kit presentation.

This presentation works over the XBib device toggling the status of the 
LED1 and LED2 (which represent the tank valves) when pressing Button 1 
and Button 2 of the device.

It will subscribe the XBib Button 1 and Button 2 channels to detect 
when they have been pressed, and, depending on the button pressed it 
will toggle the corresponding XBib LED:

    Button 1: Toggles XBib LED 1
    Button 2: Toggles XBib LED 2

Configuration settings:

xbib_board = Name of the XBib board Dia element

Presentation declaration example:

- name: digi_tank_kit0
    driver: custom_presentations.tank_kit_presentation:TankKitPresentation
    settings:
        xbib_board: xbib0
"""

# Imports
from settings.settings_base import SettingsBase, Setting
from presentations.presentation_base import PresentationBase
from samples.sample import Sample
import time

# Main class
class TankKitPresentation(PresentationBase):
    # Variables
    __channels = {}
    __led_values = {}

    def __init__(self, name, core_services):
        self.__name = name
        self.__core = core_services

        # Declare the settings list for the presentation
        settings_list = [
            Setting(name="xbib_board", type=str, required=True)]

        PresentationBase.__init__(self, name=name, 
                                  settings_list=settings_list)

    def apply_settings(self):
        """
            Apply settings as they are defined by the configuration file.
        """

        SettingsBase.merge_settings(self)
        accepted, rejected, not_found = SettingsBase.verify_settings(self)
        if len(rejected) or len(not_found):
            print "Settings rejected/not found: %s %s" % (rejected, not_found)

        SettingsBase.commit_settings(self, accepted)

        return (accepted, rejected, not_found)
    
    def start(self):
        """
            Starts the presentation object.
        """

        self.cm = self.__core.get_service("channel_manager")
        self.cp = self.cm.channel_publisher_get()
        self.cdb = self.cm.channel_database_get()

        # Get xbib and wallrouter names
        self.__xbib_name = SettingsBase.get_setting(self, 
                                                           'xbib_board')

        # Declare the channels we are going to work with
        # XBIB Serial Board
        self.chan_led1 = self.cdb.channel_get(
                        '.'.join((self.__xbib_name,"led1")))
        self.chan_led2 = self.cdb.channel_get(
                        '.'.join((self.__xbib_name,"led2")))

        # Generate the button names
        # XBIB Serial Board
        b1_name = '.'.join((self.__xbib_name,"sw1"))
        b2_name = '.'.join((self.__xbib_name,"sw2"))

        # Create a dictionary containing the leds channels and the channel 
        # name of the associated button as ID
        self.__channels[b1_name] = (self.chan_led1,)
        self.__channels[b2_name] = (self.chan_led2,)

        # Initialize the led_values dictionary
        self.__led_values = {self.chan_led1:False, 
                             self.chan_led2:False}

        # Update the value of each led channel
        self.update_led_values()

        # Subscribe to the XBIB boards button channels. Execute the 
        # 'button_status_changed' method as callback
        self.cp.subscribe(b1_name, self.button_status_changed)
        self.cp.subscribe(b2_name, self.button_status_changed)

    def stop(self):
        """
            Stop the presentation object.
        """

        return True

    def button_status_changed(self, channel):
        """
            Perform the corresponding tasks depending on the button that 
            has been pressed.
        """

        # Get the name of the channel which has changed its status
        ch = channel.name()
        # Obtain the value of the button channel
        value = channel.get().value

        # Perform the corresponding action only if the button has been 
        # pressed (avoiding release events)
        if not value:
            # Refresh the value of all the leds, they could have been 
            # changed externally
            self.update_led_values()
            # Toggle the LED/s corresponding to the pressed button
            for led in self.__channels[ch]:
                led.set(Sample(time.time(),not self.__led_values[led]))

    def update_led_values(self):
        """
            Save in the led_values dictionary the value of each led channel.
        """

        for led_channel in self.__led_values:
            self.__led_values[led_channel] = led_channel.get().value

