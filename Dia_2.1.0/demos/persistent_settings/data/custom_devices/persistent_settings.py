############################################################################
#                                                                          #
# Copyright (c)2008-2011, Digi International (Digi). All Rights Reserved.  #
#                                                                          #
# Permission to use, copy, modify, and distribute this software and its    #
# documentation, without fee and without a signed licensing agreement, is  #
# hereby granted, provided that the software is used on Digi products only #
# and that the software contain this copyright notice,  and the following  #
# two paragraphs appear in all copies, modifications, and distributions as #
# well. Contact Product Management, Digi International, Inc., 11001 Bren   #
# Road East, Minnetonka, MN, +1 952-912-3444, for commercial licensing     #
# opportunities for non-Digi products.                                     #
#                                                                          #
# DIGI SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED   #
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A          #
# PARTICULAR PURPOSE. THE SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, #
# PROVIDED HEREUNDER IS PROVIDED "AS IS" AND WITHOUT WARRANTY OF ANY KIND. #
# DIGI HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES,         #
# ENHANCEMENTS, OR MODIFICATIONS.                                          #
#                                                                          #
# IN NO EVENT SHALL DIGI BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT,      #
# SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS,   #
# ARISING OUT OF THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF   #
# DIGI HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.                #
#                                                                          #
############################################################################

# This sample demonstrates a driver which provides a means to modify
# and save its settings.  It does this by modifying its settings and
# using the CoreServices provided 'save_settings' routine.

# Settings:
#       sample_rate_sec: How often to update counter
#       alarm_level: counter level that will trigger alarm channel 

# The driver exposes channels for two purposes Demonstration
# functionality and to expose a means to set the channels

# Demonstration functionality
#       alarm: boolean output channel, True if counter is greater than
#              the alarm_level setting.
#       counter: counter value for comparison

# Setting access: (settable channels)
#       config_level: Change the alarm_level
#       config_sample_rate: Change sample_rate_sec setting
#
# When running this sample, these channels can be set via remote RCI calls
# or the embedded_web presentation.


# imports
from devices.device_base import DeviceBase
from settings.settings_base import SettingsBase, Setting
from channels.channel_source_device_property import *

import time

# constants

# exception classes

# interface functions

# classes

class PersistentSettingsSampleDevice(DeviceBase):
    """
    This class extends one of our base classes and is intended as an
    example of a concrete, example implementation, but it is not itself
    meant to be included as part of our developer API. 

    """

    def __init__(self, name, core_services):
        self.__name = name
        self.__core = core_services
        self.__sched = self.__core.get_service('scheduler')

        self.__scheduled_event = None

        from core.tracing import get_tracer
        self.__tracer = get_tracer(name)
        
        ## Settings Table Definition:
        settings_list = [
            Setting(
                name='alarm_level', type=int, required=False, default_value=5,
                  verify_function=lambda x: x >= 0),
            Setting(
                name='sample_rate_sec', type=float, required=False,
                default_value=15.0, verify_function=lambda x: x > 0.0),
        ]

        ## Channel Properties Definition:
        property_list = [
            # gettable properties
            ChannelSourceDeviceProperty(name="counter", type=int,
                initial=Sample(timestamp=0, value=0),
                perms_mask=DPROP_PERM_GET, 
                options=DPROP_OPT_AUTOTIMESTAMP),

            ChannelSourceDeviceProperty(name="alarm", type=bool,
                initial=Sample(timestamp=0, value=False),
                perms_mask=DPROP_PERM_GET,
                options=DPROP_OPT_AUTOTIMESTAMP),

            # gettable & settable properties
            ChannelSourceDeviceProperty(name="config_level", type=int,
                perms_mask=DPROP_PERM_SET|DPROP_PERM_GET,
                set_cb=self.prop_set_alarm_level),

            ChannelSourceDeviceProperty(name="config_sample_rate", type=float,
                initial=Sample(0,5.0),
                perms_mask=DPROP_PERM_SET|DPROP_PERM_GET,
                set_cb=self.prop_set_sample_rate),

        ]
                                            
        ## Initialize the DeviceBase interface:
        DeviceBase.__init__(self, self.__name, self.__core,
                                settings_list, property_list)



    ## Functions which must be implemented to conform to the DeviceBase
    ## interface:

    def start(self):
        # We expose our settings, so, to ensure we have correct
        # values, we can't rely on the initial value members of the
        # ChannelSourceDeviceProperty objects, set those channels
        # here.
        self.property_set('config_level',
                          Sample(0, self.get_setting('alarm_level')))
        self.property_set('config_sample_rate',
                          Sample(0, self.get_setting('sample_rate_sec')))

        self._reschedule()
        return True

    def stop(self):
        # Cancel any pending scheduled event
        if self.__scheduled_event is not None:
            try:
                self.__sched.cancel(self.__scheduled_event)
                self.__scheduled_event = None
            except:
                pass
        return True

    ## Locally defined functions:

    def _reschedule(self):
        # Cancel any pending event and schedule a new one, potentially
        # picking up any settings changes made in the process
        self.stop()
        self.__scheduled_event = self.__sched.schedule_after(
            SettingsBase.get_setting(self, 'sample_rate_sec'),
            self._update_counter)
        
    def _update_alarm(self):
        alarm = self.property_get('alarm').value
        counter = self.property_get('counter').value

        should_alarm = counter > self.get_setting('alarm_level')

        if alarm != should_alarm:
            self.property_set('alarm',
                              Sample(0, should_alarm))

        
    def _update_counter(self):
        # Increment 'counter'
        counter = self.property_get('counter').value + 1
        self.property_set('counter',
                          Sample(0, counter))
        self.__tracer.info('Incrementing the counter to %d', counter)

        # Check and potentially update alarm channel
        self._update_alarm()

        # Reschedule
        self._reschedule()

    # Property callback functions:
    def prop_set_sample_rate(self, sample):
        if self.get_setting('sample_rate_sec') != sample.value:
            # then value is changing, save it permanently
            self.__tracer.info('Updating the sample rate to %0.1f secs', 
                               sample.value)
            self.set_pending_setting('sample_rate_sec', sample.value)
            self.apply_settings()
            self.__core.save_settings() # Re-writes settings file

            # Since we have a callback, we need to update internally
            self.property_set('config_sample_rate',
                          Sample(0, self.get_setting('sample_rate_sec')))
        self._reschedule()

    def prop_set_alarm_level(self, sample):
        if self.get_setting('alarm_level') != sample.value:
            # then value is changing, save it permanently
            self.__tracer.info('Updating the alarm level to %d', sample.value)
            self.set_pending_setting('alarm_level', sample.value)
            self.apply_settings()
            self.__core.save_settings() # Re-writes settings file

            # Since we have a callback, we need to update internally
            self.property_set('config_level',
                              Sample(0, self.get_setting('alarm_level')))

        # Check the new value
        self._update_alarm()

# internal functions & classes
