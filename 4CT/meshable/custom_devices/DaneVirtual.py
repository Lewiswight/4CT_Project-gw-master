############################################################################
#                                                                          #
# Copyright (c)2008, 2009, Digi International (Digi). All Rights Reserved. #
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

"""\
A template device driver for the iDigi Dia.  This device driver serves as a
starting point to learn about the structure of device drivers in the Dia as
well as to be used as a template in order to create new drivers.

The template device is a virtual device driver.  It connects to no hardware
peripheral. The driver is comprised of the following two features:

* A counter which updates at a configurable rate.
* A pair of two settable channel properties which when set are
  added together and output to a third, gettable channel property.

Settings:

* **count_init:** Defines what the initial value of the counter should be
  after the driver starts or after a reset.
* **update_rate:** Defines how fast the counter should update, in seconds.

"""

# imports
from devices.device_base import DeviceBase
from settings.settings_base import SettingsBase, Setting
from channels.channel_source_device_property import *

import threading
import time

# constants

# exception classes

# interface functions

# classes

class TemplateDevice(DeviceBase, threading.Thread):

    def __init__(self, name, core_services):
        self.__name = name
        self.__core = core_services

        ## Settings Table Definition:
        settings_list = [
            Setting(
                name='count_init', type=int, required=False, default_value=0,
                  verify_function=lambda x: x >= 0),
            Setting(
                name='update_rate', type=float, required=False, default_value=1.0,
                  verify_function=lambda x: x > 0.0),
        ]

        ## Channel Properties Definition:
        property_list = [
            # gettable properties
            ChannelSourceDeviceProperty(name="counter", type=int,
                initial=Sample(timestamp=0, value=0),
                perms_mask=DPROP_PERM_GET|DPROP_PERM_REFRESH, 
                options=DPROP_OPT_AUTOTIMESTAMP,
                refresh_cb = self.refresh_counter),

            ChannelSourceDeviceProperty(name="adder_total", type=float,
                initial=Sample(timestamp=0, value=0.0),
                perms_mask=DPROP_PERM_GET, 
                options=DPROP_OPT_AUTOTIMESTAMP),        

            # settable properties
            ChannelSourceDeviceProperty(name="counter_reset", type=int,
                perms_mask=DPROP_PERM_SET,
                set_cb=self.prop_set_counter_reset),

            ChannelSourceDeviceProperty(name="global_reset", type=int,
                perms_mask=DPROP_PERM_SET,
                set_cb=self.prop_set_global_reset),
                
            ChannelSourceDeviceProperty(name="user_defined_temp", type=int,
                perms_mask=DPROP_PERM_SET),

            # gettable & settable properties
            ChannelSourceDeviceProperty(name="adder_reg1", type=float,
                initial=Sample(timestamp=0, value=0.0),
                perms_mask=DPROP_PERM_GET|DPROP_PERM_SET,
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.prop_set_adder("adder_reg1", x)),

            ChannelSourceDeviceProperty(name="adder_reg2", type=float,
                initial=Sample(timestamp=0, value=0.0),
                perms_mask=DPROP_PERM_GET|DPROP_PERM_SET,
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.prop_set_adder("adder_reg2", x)),

        ]
                                            
        ## Initialize the DeviceBase interface:
        DeviceBase.__init__(self, self.__name, self.__core,
                                settings_list, property_list)

        ## Thread initialization:
        self.__stopevent = threading.Event()
        threading.Thread.__init__(self, name=name)
        threading.Thread.setDaemon(self, True)


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
            print ("%s(%s): settings rejected/not found: %s/%s" % 
                    (self.__class__.__name__, self.__name, rejected, not_found))

        SettingsBase.commit_settings(self, accepted)

        return (accepted, rejected, not_found)

    def start(self):
        """Start the device driver.  Returns bool."""
        threading.Thread.start(self)

        return True

    def stop(self):
        """Stop the device driver.  Returns bool."""
        self.__stopevent.set()
        
        return True
        
    def refresh_counter(self):
        """Refresh the counter by incrementing it by 1000 for demo purposes."""
        counter_value = self.property_get("counter").value
        self.property_set("counter", Sample(0, counter_value + 1000))
        return
        
    ## Locally defined functions:
    # Property callback functions:
    def prop_set_counter_reset(self, ignored_sample):
        self.property_set("counter",
            Sample(0, SettingsBase.get_setting(self, "count_init")))

    def prop_set_global_reset(self, ignored_sample):
        self.prop_set_counter_reset(ignored_sample=0)
        self.property_set("adder_total", Sample(0, 0.0))
        self.property_set("adder_reg1", Sample(0, 0.0))
        self.property_set("adder_reg2", Sample(0, 0.0))

    def prop_set_adder(self, register_name, float_sample):
        self.property_set(register_name, float_sample)
        # update total:
        adder_reg1 = self.property_get("adder_reg1").value
        adder_reg2 = self.property_get("adder_reg2").value
        self.property_set("adder_total", Sample(0, adder_reg1 + adder_reg2))

    # Threading related functions:
    def run(self):
        """run when our device driver thread is started"""

        self.prop_set_global_reset(0)

        while 1:
            if self.__stopevent.isSet():
                self.__stopevent.clear()
                break

            # increment counter property:
            counter_value = self.property_get("counter").value
            self.property_set("counter",
                Sample(0, counter_value + 1))
            time.sleep(SettingsBase.get_setting(self,"update_rate"))




# internal functions & classes

def main():
    pass

if __name__ == '__main__':
    import sys
    status = main()
    sys.exit(status)

