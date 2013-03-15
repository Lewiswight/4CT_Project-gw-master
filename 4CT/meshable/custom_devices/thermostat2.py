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
Dia Driver for the Digi XBee Wall Router:

Settings:

    xbee_device_manager: must be set to the name of an XBeeDeviceManager
                         instance.
    
    extended_address: the extended address of the XBee device you
                      would like to monitor.

    sample_rate_ms: the sample rate of the XBee Wall Router.
"""

# imports

from devices.device_base import DeviceBase
from devices.xbee.xbee_devices.xbee_base import XBeeBase
from settings.settings_base import SettingsBase, Setting
from channels.channel_source_device_property import *

from devices.xbee.xbee_config_blocks.xbee_config_block_ddo \
    import XBeeConfigBlockDDO,  DDO_GET_PARAM
from devices.xbee.xbee_device_manager.xbee_device_manager_event_specs \
    import *
from devices.xbee.common.addressing import *
from devices.xbee.common.io_sample import parse_is, sample_to_mv


import struct
import time
import threading
import thread
from devices.xbee.xbee_config_blocks.xbee_config_block_sleep \
    import CYCLIC_SLEEP_EXT_MAX_MS, SM_DISABLED, XBeeConfigBlockSleep
from common.types.boolean import Boolean, STYLE_ONOFF
from devices.xbee.common.io_sample import parse_is, sample_to_mv
from devices.xbee.common.prodid import MOD_XB_ZB, parse_dd, format_dd, product_name, \
    PROD_DIGI_XB_SENSOR_LTH, PROD_DIGI_XB_SENSOR_LT


# constants
initial_states = ["on", "off", "same"]


# exception classes

# interface functions

# classes
class XBeeSensor(XBeeBase):

    # Define a set of endpoints that this device will send in on.
    ADDRESS_TABLE = [ [0xe8, 0xc105, 0x92], [0xe8, 0xc105, 0x11] ]

    # The list of supported products that this driver supports.
    SUPPORTED_PRODUCTS = [  PROD_DIGI_XB_SENSOR_LTH, PROD_DIGI_XB_SENSOR_LT, ]

    def __init__(self, name, core_services):
        self.__name = name
        self.__core = core_services

        ## Local State Variables:
        self.__xbee_manager = None

        ## Settings Table Definition:
        settings_list = [
            Setting(
                name='sleep', type=bool, required=False,
                default_value=True),
            Setting(
                name='sample_rate_ms', type=int, required=False,
                default_value=10000,
                verify_function=lambda x: x >= 0 and x <= CYCLIC_SLEEP_EXT_MAX_MS), 
            Setting(
                name='awake_time_ms', type=int, required=False,
                default_value=1000,
                verify_function=lambda x: x >= 0 and x <= 0xffff),
            Setting(
                name='sample_predelay', type=int, required=False,
                default_value=125,
                verify_function=lambda x: x >= 0 and x <= 0xffff),           
            Setting(
                name='default_state1', type=str, required=False,
                default_value="same",
                parser=lambda s: s.lower(),
                verify_function=lambda s: s in initial_states),
            Setting(
                name='default_state2', type=str, required=False,
                default_value="off",
                parser=lambda s: s.lower(),
                verify_function=lambda s: s in initial_states),
            Setting(
                name='default_state3', type=str, required=False,
                default_value="off",
                parser=lambda s: s.lower(),
                verify_function=lambda s: s in initial_states),
            Setting(
                name='idle_off_seconds', type=int, required=False,
                default_value=0, verify_function=lambda x: x >= 0),
            Setting(name='power_on_source1', type=str, required=False),
            Setting(name='power_on_source2', type=str, required=False),
            Setting(name='power_on_source3', type=str, required=False),            
            Setting(name='device_profile', type=str, required=False),
            Setting(name='input_source', type=str, required=False, default_value=None),
        ]

        ## Channel Properties Definition:
        property_list = [
            # gettable properties
#            ChannelSourceDeviceProperty(name="input", type=tuple,
#                initial=Sample(timestamp=0, value=(0,None)),
#                perms_mask=DPROP_PERM_SET | DPROP_PERM_GET,
#                set_cb=self.prop_set_power_control1),
            ChannelSourceDeviceProperty(name="driving_temp", type=float,
                initial=Sample(timestamp=0, unit="F", value=0.0),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name="temp", type=float,
                initial=Sample(timestamp=0, unit="F", value=0.0),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name="aa", type=str,
                initial=Sample(timestamp=0, value="thermostat"),
                 perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET), options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name="red_light", type=float,
                initial=Sample(timestamp=0, unit="mv", value=0.0),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name="on", type=float,
                initial=Sample(timestamp=0, unit="mv", value=0.0),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name="heat", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=self.heat),
            ChannelSourceDeviceProperty(name="AC", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=self.ac),
            ChannelSourceDeviceProperty(name="heat_ac_on", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=self.hvac_cycle),
            ChannelSourceDeviceProperty(name="on_for_ac_off_for_heat_status", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(True, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=self.hvac_control),
            ChannelSourceDeviceProperty(name="fan_on", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=self.hvac_control),
            ChannelSourceDeviceProperty(name="fan", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=self.fan),
            ChannelSourceDeviceProperty(name="switch_to_old", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=self.old_thermostat),
            ChannelSourceDeviceProperty(name="old_thermostat_on", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=self.hvac_control),
            ChannelSourceDeviceProperty(name="user_input_1", type=str,
                initial=Sample(timestamp=0, value="TempLight.temperature"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.prop_set_adder("user_input_1", x)),
            ChannelSourceDeviceProperty(name="1_high", type=float,
                initial=Sample(timestamp=0, value=0.0),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.prop_set_adder("1_high", x)),
            ChannelSourceDeviceProperty(name="1_low", type=float,
                initial=Sample(timestamp=0, value=0.0),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.prop_set_adder("1_low", x)),
            ChannelSourceDeviceProperty(name="2_high", type=float,
                initial=Sample(timestamp=0, value=0.0),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.prop_set_adder("2_high", x)),
            ChannelSourceDeviceProperty(name="2_low", type=float,
                initial=Sample(timestamp=0, value=0.0),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.prop_set_adder("2_low", x)),
            ChannelSourceDeviceProperty(name="3_high", type=float,
                initial=Sample(timestamp=0, value=0.0),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.prop_set_adder("3_high", x)),
            ChannelSourceDeviceProperty(name="3_low", type=float,
                initial=Sample(timestamp=0, value=0.0),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.prop_set_adder("3_low", x)),
            ChannelSourceDeviceProperty(name="4_high", type=float,
                initial=Sample(timestamp=0, value=0.0),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.prop_set_adder("4_high", x)),
            ChannelSourceDeviceProperty(name="4_low", type=float,
                initial=Sample(timestamp=0, value=0.0),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.prop_set_adder("4_low", x)),                                                                                                                
            ChannelSourceDeviceProperty(name="desired_temp", type=float,
                initial=Sample(timestamp=0, value=0.0),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.prop_set_adder("desired_temp", x)),
            ChannelSourceDeviceProperty(name="user_input_2", type=str,
                initial=Sample(timestamp=0, value="TempLight.temperature"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.prop_set_adder("user_input_2", x)),
            ChannelSourceDeviceProperty(name="counter", type=int,
                initial=Sample(timestamp=0, value=0),
                perms_mask=DPROP_PERM_GET|DPROP_PERM_REFRESH, 
                options=DPROP_OPT_AUTOTIMESTAMP,
                refresh_cb = self.refresh_counter),
                
                
             # settable properties
 #           ChannelSourceDeviceProperty(name="counter_reset", type=int,
 #               perms_mask=DPROP_PERM_SET,
 #               set_cb=self.prop_set_counter_reset),


        ]

        ## Initialize the XBeeBase interface:
        XBeeBase.__init__(self, self.__name, self.__core,
                                settings_list, property_list) 


    ## Functions which must be implemented to conform to the XBeeBase
    ## interface:


    
    def refresh_counter(self):
        """Refresh the counter by incrementing it by 1000 for demo purposes."""
        counter_value = self.property_get("counter").value
        self.property_set("counter", Sample(0, counter_value + 1000))
        return
    
    def hvac_control(self):
        old = self.property_get("switch_to_old").value       
             
  
    def hvac_cycle(self):
        
        self.property_set("on", Sample(0, 23, "mv"))
        
        driving = self.property_get("driving_temp").value
        des_temp = self.property_get("desired_temp").value 
        on = self.property_get("heat_ac_on").value

        
    
        
 #       if ac and not on and driving > (des_temp + 0.5):
 #                    self.prop_set_power_control2_high(Sample(0, Boolean("on", STYLE_ONOFF)))
 #                    time.sleep(0.75)
 #                    self.prop_set_power_control2_high(Sample(0, Boolean("off", STYLE_ONOFF)))
 #       #    self.property_set("2_low", Sample(0, 1.0)) 
            
 #       if ac and on and driving < (des_temp - 0.5):
 #                   self.prop_set_power_control2_low(Sample(0, Boolean("on", STYLE_ONOFF)))
 #                   time.sleep(0.75)
 #                   self.prop_set_power_control2_low(Sample(0, Boolean("off", STYLE_ONOFF)))
         #   self.property_set("2_high", Sample(0, 1.0))
         
        temp_plus = des_temp + 0.5
        temp_minus = des_temp - 0.5
            
        if on and driving > temp_plus:
                    self.prop_set_power_control2_low(Sample(0, Boolean("on", STYLE_ONOFF)))
                    time.sleep(0.75)
                    self.prop_set_power_control2_low(Sample(0, Boolean("off", STYLE_ONOFF)))
       #     self.property_set("2_low", Sample(0, 1.0)) 
            
        if not on and driving < temp_minus:
                    self.prop_set_power_control2_high(Sample(0, Boolean("on", STYLE_ONOFF)))
                    time.sleep(0.75)
                    self.prop_set_power_control2_high(Sample(0, Boolean("off", STYLE_ONOFF)))
        
        
    def heat(self, bool_sample):
        
        self.property_set("heat",
            Sample(0, Boolean(bool_sample.value, style=STYLE_ONOFF)))
          
        heat = self.property_get("heat").value  
        red = self.property_get("red_light").value 
        ac = self.property_get("AC").value 
        fan = self.property_get("fan").value
        old = self.property_get("switch_to_old").value
        fan_on = self.property_get("fan_on").value
        ac_on_off_heat = self.property_get("on_for_ac_off_for_heat_status").value
        old_on = self.property_get("old_thermostat_on").value
        

                
                        
        
        if ac:
            self.property_set("AC",
            Sample(0, Boolean(False, style=STYLE_ONOFF)))
        
        
        if fan_on:
            self.prop_set_power_control4_low(Sample(0, Boolean("on", STYLE_ONOFF)))
            time.sleep(0.75)
            self.prop_set_power_control4_low(Sample(0, Boolean("off", STYLE_ONOFF)))
            self.property_set("fan",
            Sample(0, Boolean(False, style=STYLE_ONOFF)))
 #           self.property_set("4_low", Sample(0, 1.0))
        
        if old_on:
            self.prop_set_power_control1_high(Sample(0, Boolean("on", STYLE_ONOFF)))
            time.sleep(0.75)
            self.prop_set_power_control1_high(Sample(0, Boolean("off", STYLE_ONOFF)))
            self.property_set("switch_to_old",
            Sample(0, Boolean(False, style=STYLE_ONOFF)))
            self.property_set("old_thermostat_on",
            Sample(0, Boolean(False, style=STYLE_ONOFF)))
     #       self.property_set("1_high", Sample(0, 1.0))
        
        if red > 1000.0:
            self.prop_set_power_control1_high(Sample(0, Boolean("on", STYLE_ONOFF)))
            time.sleep(0.75)
            self.prop_set_power_control1_high(Sample(0, Boolean("off", STYLE_ONOFF)))
            self.property_set("switch_to_old",
            Sample(0, Boolean(False, style=STYLE_ONOFF)))
            self.property_set("old_thermostat_on",
            Sample(0, Boolean(False, style=STYLE_ONOFF)))
        
        if ac_on_off_heat:
            self.prop_set_power_control3_low(Sample(0, Boolean("on", STYLE_ONOFF)))
            time.sleep(0.75)
            self.prop_set_power_control3_low(Sample(0, Boolean("off", STYLE_ONOFF)))
       #     self.property_set("3_low", Sample(0, 1.0))
                    
        if not heat:
            self.prop_set_power_control2_low(Sample(0, Boolean("on", STYLE_ONOFF)))
            time.sleep(0.75)
            self.prop_set_power_control2_low(Sample(0, Boolean("off", STYLE_ONOFF)))
          #  self.property_set("2_low", Sample(0, 1.0))
 
                                                
            
    def ac(self, bool_sample):
        
        self.property_set("AC",
            Sample(0, Boolean(bool_sample.value, style=STYLE_ONOFF)))
        
        
        heat = self.property_get("heat").value  
        red = self.property_get("red_light").value 
        ac = self.property_get("AC").value 
        fan = self.property_get("fan").value
        old = self.property_get("switch_to_old").value
        fan_on = self.property_get("fan_on").value
        ac_on_off_heat = self.property_get("on_for_ac_off_for_heat_status").value
        old_on = self.property_get("old_thermostat_on").value
        
        if heat:
            self.property_set("heat",
            Sample(0, Boolean(False, style=STYLE_ONOFF)))
        
        if fan_on:
            self.prop_set_power_control4_low(Sample(0, Boolean("on", STYLE_ONOFF)))
            time.sleep(0.75)
            self.prop_set_power_control4_low(Sample(0, Boolean("off", STYLE_ONOFF)))
            self.property_set("fan",
            Sample(0, Boolean(False, style=STYLE_ONOFF)))
         #   self.property_set("4_low", Sample(0, 1.0))
        
        if old_on:
            self.prop_set_power_control1_high(Sample(0, Boolean("on", STYLE_ONOFF)))
            time.sleep(0.75)
            self.prop_set_power_control1_high(Sample(0, Boolean("off", STYLE_ONOFF)))
            self.property_set("switch_to_old",
            Sample(0, Boolean(False, style=STYLE_ONOFF)))
            self.property_set("old_thermostat_on",
            Sample(0, Boolean(False, style=STYLE_ONOFF)))
           # self.property_set("1_high", Sample(0, 1.0))
           
        if red > 1000.0:
            self.prop_set_power_control1_high(Sample(0, Boolean("on", STYLE_ONOFF)))
            time.sleep(0.75)
            self.prop_set_power_control1_high(Sample(0, Boolean("off", STYLE_ONOFF)))
            self.property_set("switch_to_old",
            Sample(0, Boolean(False, style=STYLE_ONOFF)))
            self.property_set("old_thermostat_on",
            Sample(0, Boolean(False, style=STYLE_ONOFF)))
        
        if not ac_on_off_heat:
            self.prop_set_power_control3_high(Sample(0, Boolean("on", STYLE_ONOFF)))
            time.sleep(0.75)
            self.prop_set_power_control3_high(Sample(0, Boolean("off", STYLE_ONOFF)))
       #     self.property_set("3_high", Sample(0, 1.0))
                    
        if not ac:
            self.prop_set_power_control2_low(Sample(0, Boolean("on", STYLE_ONOFF)))
            time.sleep(0.75)
            self.prop_set_power_control2_low(Sample(0, Boolean("off", STYLE_ONOFF)))
       #     self.property_set("2_low", Sample(0, 1.0))
        
    def setup(self, bool_sample):
        
        
        self.prop_set_power_control4_low(Sample(0, Boolean("on", STYLE_ONOFF)))
        time.sleep(0.75)
        self.prop_set_power_control4_low(Sample(0, Boolean("off", STYLE_ONOFF)))

        

        self.prop_set_power_control1_high(Sample(0, Boolean("on", STYLE_ONOFF)))
        time.sleep(0.75)
        self.prop_set_power_control1_high(Sample(0, Boolean("off", STYLE_ONOFF)))

           

        

        self.prop_set_power_control3_high(Sample(0, Boolean("on", STYLE_ONOFF)))
        time.sleep(0.75)
        self.prop_set_power_control3_high(Sample(0, Boolean("off", STYLE_ONOFF)))
       #     self.property_set("3_high", Sample(0, 1.0))
                    

        self.prop_set_power_control2_low(Sample(0, Boolean("on", STYLE_ONOFF)))
        time.sleep(0.75)
        self.prop_set_power_control2_low(Sample(0, Boolean("off", STYLE_ONOFF)))
       #     self.property_set("2_low", Sample(0, 1.0))
         
        
    def fan(self, bool_sample):
        
        self.property_set("fan",
            Sample(0, Boolean(bool_sample.value, style=STYLE_ONOFF)))
        
        heat = self.property_get("heat").value  
        red = self.property_get("red_light").value 
        ac = self.property_get("AC").value 
        fan = self.property_get("fan").value
        fan_on = self.property_get("fan_on").value
        ac_on_off_heat = self.property_get("on_for_ac_off_for_heat_status").value
        old_on = self.property_get("old_thermostat_on").value
        old = self.property_get("switch_to_old").value       
        
        self.property_set("heat",
            Sample(0, Boolean(False, style=STYLE_ONOFF)))
        
        self.property_set("AC",
            Sample(0, Boolean(False, style=STYLE_ONOFF))) 
        
        if fan: #  == "On":
            self.prop_set_power_control4_high(Sample(0, Boolean("on", STYLE_ONOFF)))
            time.sleep(0.75)
            self.prop_set_power_control4_high(Sample(0, Boolean("off", STYLE_ONOFF)))
   #         self.property_set("4_high", Sample(0, 1.0))
        
        if old: # == "On":
            self.prop_set_power_control1_high(Sample(0, Boolean("on", STYLE_ONOFF)))
            time.sleep(0.75)
            self.prop_set_power_control1_high(Sample(0, Boolean("off", STYLE_ONOFF)))
            self.property_set("switch_to_old",
            Sample(0, Boolean(False, style=STYLE_ONOFF)))
            self.property_set("old_thermostat_on",
            Sample(0, Boolean(False, style=STYLE_ONOFF)))
   #         self.property_set("1_high", Sample(0, 1.0))
            
        if red > 1000.0:
            self.prop_set_power_control1_high(Sample(0, Boolean("on", STYLE_ONOFF)))
            time.sleep(0.75)
            self.prop_set_power_control1_high(Sample(0, Boolean("off", STYLE_ONOFF)))
            self.property_set("switch_to_old",
            Sample(0, Boolean(False, style=STYLE_ONOFF)))
            self.property_set("old_thermostat_on",
            Sample(0, Boolean(False, style=STYLE_ONOFF)))
            
            
                            
        if not fan: # == "Off":
            self.prop_set_power_control4_low(Sample(0, Boolean("on", STYLE_ONOFF)))
            time.sleep(0.75)
            self.prop_set_power_control4_low(Sample(0, Boolean("off", STYLE_ONOFF)))
  #          self.property_set("4_low", Sample(0, 1.0))
            

        
    def old_thermostat(self, bool_sample):
        
        self.property_set("switch_to_old",
            Sample(0, Boolean(bool_sample.value, style=STYLE_ONOFF)))
        
        self.property_set("heat",
            Sample(0, Boolean(False, style=STYLE_ONOFF)))
        
        self.property_set("AC",
            Sample(0, Boolean(False, style=STYLE_ONOFF)))
        
        old = self.property_get("switch_to_old").value
        fan = self.property_get("fan").value
        fan_on = self.property_get("fan_on").value
        on = self.property_get("heat_ac_on").value
        
        if on:
            self.prop_set_power_control2_low(Sample(0, Boolean("on", STYLE_ONOFF)))
            time.sleep(0.75)
            self.prop_set_power_control2_low(Sample(0, Boolean("off", STYLE_ONOFF)))
            
        
        if fan:
            self.prop_set_power_control4_low(Sample(0, Boolean("on", STYLE_ONOFF)))
            time.sleep(0.75)
            self.prop_set_power_control4_low(Sample(0, Boolean("off", STYLE_ONOFF)))
            self.property_set("fan",
            Sample(0, Boolean(False, style=STYLE_ONOFF)))
            
        
        if old:
            self.prop_set_power_control1_low(Sample(0, Boolean("on", STYLE_ONOFF)))
            time.sleep(0.75)
            self.prop_set_power_control1_low(Sample(0, Boolean("off", STYLE_ONOFF)))
          #  self.property_set("1_low", Sample(0, 1.0))
            
        if not old:
            self.prop_set_power_control1_high(Sample(0, Boolean("on", STYLE_ONOFF)))
            time.sleep(0.75)
            self.prop_set_power_control1_high(Sample(0, Boolean("off", STYLE_ONOFF)))
            
            
          #  self.property_set("1_high", Sample(0, 1.0))
           # self.property_set("2_low", Sample(0, 1.0))
           # self.property_set("4_low", Sample(0, 1.0))            
            
        

    
        
    ## Locally defined functions:
    # Property callback functions:
    def prop_set_counter_reset(self, ignored_sample):
        self.property_set("counter",
            Sample(0, SettingsBase.get_setting(self, "count_init")))


    def prop_set_adder(self, register_name, float_sample):
        self.property_set(register_name, float_sample)
        # update total:
 #       adder_reg1 = self.property_get("adder_reg1").value
 #       adder_reg2 = self.property_get("adder_reg2").value
 #       self.property_set("adder_total", Sample(0, adder_reg1 + adder_reg2))

  #      extended_address = SettingsBase.get_setting(self, "extended_address")
        
   #     d4 = self.__xbee_manager.xbee_device_ddo_get_param(extended_address, "%V")
        


#        d4 = struct.unpack('B', d4)[0]
        
        
   #     self.property_set("user_input_2", Sample(0, d4, "F"))
        
        one_high = self.property_get("1_high").value  
        one_low = self.property_get("1_low").value
        two_high = self.property_get("2_high").value
        two_low = self.property_get("2_low").value
        three_high = self.property_get("3_high").value
        three_low = self.property_get("3_low").value
        four_high = self.property_get("4_high").value
        four_low = self.property_get("4_low").value  
#        temp = self.my_input    
        
        

        
    

        if one_high == 1:
            self.prop_set_power_control1_high(Sample(0, Boolean("on", STYLE_ONOFF)))
            time.sleep(0.75)
            self.prop_set_power_control1_high(Sample(0, Boolean("off", STYLE_ONOFF)))
        
        if one_low == 1:
            self.prop_set_power_control1_low(Sample(0, Boolean("on", STYLE_ONOFF)))
            time.sleep(0.75)
            self.prop_set_power_control1_low(Sample(0, Boolean("off", STYLE_ONOFF))) 
        
        if two_high == 1:
            self.prop_set_power_control2_high(Sample(0, Boolean("on", STYLE_ONOFF)))
            time.sleep(0.75)
            self.prop_set_power_control2_high(Sample(0, Boolean("off", STYLE_ONOFF))) 
        
        if two_low == 1:
            self.prop_set_power_control2_low(Sample(0, Boolean("on", STYLE_ONOFF)))
            time.sleep(0.75)
            self.prop_set_power_control2_low(Sample(0, Boolean("off", STYLE_ONOFF))) 
        
        if three_high == 1:
            self.prop_set_power_control3_high(Sample(0, Boolean("on", STYLE_ONOFF)))
            time.sleep(0.75)
            self.prop_set_power_control3_high(Sample(0, Boolean("off", STYLE_ONOFF)))
        
        if three_low == 1:
            self.prop_set_power_control3_low(Sample(0, Boolean("on", STYLE_ONOFF)))
            time.sleep(0.75)
            self.prop_set_power_control3_low(Sample(0, Boolean("off", STYLE_ONOFF)))        
        
        if four_high == 1:
            self.prop_set_power_control4_high(Sample(0, Boolean("on", STYLE_ONOFF)))
            time.sleep(0.75)
            self.prop_set_power_control4_high(Sample(0, Boolean("off", STYLE_ONOFF)))
        
        if four_low == 1:
            self.prop_set_power_control4_low(Sample(0, Boolean("on", STYLE_ONOFF)))
            time.sleep(0.75)
            self.prop_set_power_control4_low(Sample(0, Boolean("off", STYLE_ONOFF)))



 

    @staticmethod
    
    def probe():
        """\
            Collect important information about the driver.

            .. Note::

                * This method is a static method.  As such, all data returned
                  must be accessible from the class without having a instance
                  of the device created.

            Returns a dictionary that must contain the following 2 keys:
                    1) address_table:
                       A list of XBee address tuples with the first part of the
                       address removed that this device might send data to.
                       For example: [ 0xe8, 0xc105, 0x95 ]
                    2) supported_products:
                       A list of product values that this driver supports.
                       Generally, this will consist of Product Types that
                       can be found in 'devices/xbee/common/prodid.py'
        """
        probe_data = XBeeBase.probe()

        for address in XBeeXBR.ADDRESS_TABLE:
            probe_data['address_table'].append(address)
        for product in XBeeXBR.SUPPORTED_PRODUCTS:
            probe_data['supported_products'].append(product)

        return probe_data

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
            return (accepted, rejected, not_found)

        SettingsBase.commit_settings(self, accepted)

        return (accepted, rejected, not_found)

    def start(self):
        """Start the device driver.  Returns bool."""

        # Fetch the XBee Manager name from the Settings Manager:
        xbee_manager_name = SettingsBase.get_setting(self, "xbee_device_manager")
        dm = self.__core.get_service("device_driver_manager")
        self.__xbee_manager = dm.instance_get(xbee_manager_name)

        # Register ourselves with the XBee Device Manager instance:
        self.__xbee_manager.xbee_device_register(self)

        # Get the extended address of the device:
        extended_address = SettingsBase.get_setting(self, "extended_address")

        # Create a callback specification for our device address, endpoint
        # Digi XBee profile and sample cluster id:
        xbdm_rx_event_spec = XBeeDeviceManagerRxEventSpec()
        xbdm_rx_event_spec.cb_set(self.sample_indication)
        xbdm_rx_event_spec.match_spec_set(
            (extended_address, 0xe8, 0xc105, 0x92),
            (True, True, True, True))
        self.__xbee_manager.xbee_device_event_spec_add(self,
                                xbdm_rx_event_spec)

        # Create a DDO configuration block for this device:
        xbee_ddo_cfg = XBeeConfigBlockDDO(extended_address)

        # Get the gateway's extended address:
        gw_xbee_sh, gw_xbee_sl = gw_extended_address_tuple()

        # Set the destination for I/O samples to be the gateway:
        xbee_ddo_cfg.add_parameter('DH', gw_xbee_sh)
        xbee_ddo_cfg.add_parameter('DL', gw_xbee_sl)

        # Configure pins DI1 & DI2 & DI0 for analog input:

        
 #       xbee_ddo_cfg.add_parameter('SM', 4)
        
        
        xbee_ddo_cfg.add_parameter('D1', 2)
        
        xbee_ddo_cfg.add_parameter('D2', 2) 
        

        for io_pin in [ 'D0', 'D3', 'D4', 'D6', 'D7', 'D9', 'P0', 'P1', 'P2'  ]:
            xbee_ddo_cfg.add_parameter(io_pin, 4)

    
        
        # Configure the IO Sample Rate:
        sample_rate = SettingsBase.get_setting(self, "sample_rate_ms")
        xbee_ddo_cfg.add_parameter('IR', sample_rate)
        
        # Handle subscribing the devices output to a named channel,
        # if configured to do so:
 #       power_on_source1 = SettingsBase.get_setting(self, 'power_on_source1')
  #      if power_on_source1 is not None:
   #         cm = self.__core.get_service("channel_manager")
    #        cp = cm.channel_publisher_get()
     #       self.property_set("adder_reg2", Sample(0, float(power_on_source1)))
      #      cp.subscribe(power_on_source1, self.update_power_state1)
            
        
            
 #       power_on_source2 = SettingsBase.get_setting(self, 'power_on_source2')
 #       if power_on_source2 is not None:
 #W           cm = self.__core.get_service("channel_manager")
  #          cp = cm.channel_publisher_get()
  #          cp.subscribe(power_on_source2, self.update_power_state2)
            
 #       power_on_source3 = SettingsBase.get_setting(self, 'power_on_source3')
 #       if power_on_source3 is not None:
 #           cm = self.__core.get_service("channel_manager")
 #           cp = cm.channel_publisher_get()
 #           cp.subscribe(power_on_source3, self.update_power_state3)
            


        

        # Register this configuration block with the XBee Device Manager:
        self.__xbee_manager.xbee_device_config_block_add(self, xbee_ddo_cfg)
        
        
        # Setup the sleep parameters on this device:
        will_sleep = SettingsBase.get_setting(self, "sleep")
        sample_predelay = SettingsBase.get_setting(self, "sample_predelay")
        awake_time_ms = (SettingsBase.get_setting(self, "awake_time_ms") +
                         sample_predelay)
        
        if will_sleep:
            # Sample time pre-delay, allow the circuitry to power up and
            # settle before we allow the XBee to send us a sample:            
            xbee_ddo_wh_block = XBeeConfigBlockDDO(extended_address)
            xbee_ddo_wh_block.apply_only_to_modules((MOD_XB_ZB,))
            xbee_ddo_wh_block.add_parameter('WH', sample_predelay)
            self.__xbee_manager.xbee_device_config_block_add(self,
                                    xbee_ddo_wh_block)

        # The original sample rate is used as the sleep rate:
        sleep_rate_ms = SettingsBase.get_setting(self, "sample_rate_ms")
        xbee_sleep_cfg = XBeeConfigBlockSleep(extended_address)
        if will_sleep:
            xbee_sleep_cfg.sleep_cycle_set(awake_time_ms, sleep_rate_ms)
        else:
            xbee_sleep_cfg.sleep_mode_set(SM_DISABLED)
        self.__xbee_manager.xbee_device_config_block_add(self, xbee_sleep_cfg)
        
        
        
        self.setup(Sample(0, Boolean("off", STYLE_ONOFF)))




        # Indicate that we have no more configuration to add:
        self.__xbee_manager.xbee_device_configure(self)
        


        return True

    def stop(self):
        """Stop the device driver.  Returns bool."""
        # Unregister ourselves with the XBee Device Manager instance:
        self.__xbee_manager.xbee_device_unregister(self)

        return True
        

    ## Locally defined functions:
    def sample_indication(self, buf, addr):
        

        

               
                        # wire up any inputs
 #      input_source = SettingsBase.get_setting(self, 'input_source')
        cm = self.__core.get_service("channel_manager")
        cp = cm.channel_publisher_get()
        cdb = cm.channel_database_get()
 #       cp.subscribe(input_source, self.prop_set_input)
        
        

 #       try:
#        source_name = SettingsBase.get_setting(self, 'input_source')
        source_name = self.property_get("user_input_1").value
            
        if( source_name != None):
            source_chan = cdb.channel_get( source_name)
                # pre-load the starting value, which won't be published to us
            self.my_input = source_chan.get().value
   #             self.property_set("adder_reg2", Sample(0, my_input))
            self.property_set("driving_temp", Sample(0, self.my_input, "F"))              
#                self.property_set("input", Sample(0, self.my_input))      
         #       cp.subscribe(source_name, self.update_power_state1)
 #               cp.subscribe( source_name, self.prop_set_input )        
        
        
        
        # Parse the I/O sample:
        io_sample = parse_is(buf)

        # Calculate channel values:
       # upbutton_mv, onbutton_mv, downbutton_mv = \
           # map(lambda cn: sample_to_mv(io_sample[cn]), ("AD0", "AD1", "AD2"))

            
 # Calculate sensor channel values:
        if io_sample.has_key("AD1") and io_sample.has_key("AD0") and io_sample.has_key("AD3"):
            light_mv, temperature_mv, humidity_mv = \
                map(lambda cn: sample_to_mv(io_sample[cn]), ("AD1", "AD0", "AD3"))
       
            temp = (round(light_mv, 2)) / 10
            red_light = round(humidity_mv) 
           # on = round(temperature_mv, 2)
           # down = round(humidity_mv, 2)
       
 #       power_state = self.property_get("power_on").value

        # Update channels:
        self.property_set("temp", Sample(0, temp, "F"))
        self.property_set("red_light", Sample(0, red_light, "mv"))
 #       self.property_set("on", Sample(0, on, "mv"))
 #       self.property_set("down", Sample(0, down, "mv"))
        
        red = self.property_get("red_light").value
        heat = self.property_get("heat").value
        old = self.property_get("switch_to_old").value
        on = self.property_get("heat_ac_on").value
        old_on = self.property_get("old_thermostat_on").value
        
        if red_light > 100.0 and not old_on:
            self.old_thermostat(Sample(0, Boolean("on", STYLE_ONOFF)))
            
#        if red_light > 100.0 and not old_on:
 #           self.old_thermostat(Sample(0, Boolean("on", STYLE_ONOFF)))
       #     self.property_set("2_low", Sample(0, 1.0)) 
            
 #       if red_light < 100 and old:
 #           self.property_set("switch_to_old", Sample(0, Boolean(False, style=STYLE_ONOFF)))
 #           self.property_set("old_thermostat_on", Sample(0, Boolean(False, style=STYLE_ONOFF)))
 #           
 #       if red_light < 100 and old_on:
 #           self.property_set("switch_to_old", Sample(0, Boolean(False, style=STYLE_ONOFF)))
 #           self.property_set("old_thermostat_on", Sample(0, Boolean(False, style=STYLE_ONOFF)))
        
        driving = self.property_get("driving_temp").value
        des_temp = self.property_get("desired_temp").value    
        ac = self.property_get("AC").value

        
    
        temp_plus = des_temp + 0.5
        temp_minus = des_temp - 0.5
            
        if heat and on and driving > temp_plus:
                    self.prop_set_power_control2_low(Sample(0, Boolean("on", STYLE_ONOFF)))
                    time.sleep(0.75)
                    self.prop_set_power_control2_low(Sample(0, Boolean("off", STYLE_ONOFF)))
       #     self.property_set("2_low", Sample(0, 1.0)) 
            
        if heat and not on and driving < temp_minus:
                    self.prop_set_power_control2_high(Sample(0, Boolean("on", STYLE_ONOFF)))
                    time.sleep(0.75)
                    self.prop_set_power_control2_high(Sample(0, Boolean("off", STYLE_ONOFF)))
                     
        if ac and not on and driving > temp_plus:
                     self.prop_set_power_control2_high(Sample(0, Boolean("on", STYLE_ONOFF)))
                     time.sleep(0.75)
                     self.prop_set_power_control2_high(Sample(0, Boolean("off", STYLE_ONOFF)))
        #    self.property_set("2_low", Sample(0, 1.0)) 
            
        if ac and on and driving < temp_minus:
                    self.prop_set_power_control2_low(Sample(0, Boolean("on", STYLE_ONOFF)))
                    time.sleep(0.75)
                    self.prop_set_power_control2_low(Sample(0, Boolean("off", STYLE_ONOFF)))
         #   self.property_set("2_high", Sample(0, 1.0))
         
        
        
         

        

                #    self.property_set("2_high", Sample(0, 1.0))
                       

                
        
        
        
        
 
  #      except:
#            traceback.print_exc()
   #        self.my_input = True
        
        
  #  def prop_set_input( self, sam):
   #     # someone pushing in new input - is either sample or channel
 #
  #      if( not isinstance( sam, Sample)):
   #         # the publish/sub pushes in the channel, so convert to sample
    #        sam = sam.get()
 #
  #      self.process( sam.value)
   #     self.property_set("input", Sample(sam.timestamp, self.my_input))
    #    self.prop_set_power_control1(chan.get())        
     
        #return True
        

 
 # after 30 seconds, "hello, world" will be printed
 #       if temp > (user_temp + 0.5):    
 #           self.prop_set_power_control1(Sample(0,
 #                                              Boolean("on",
 #                                                      STYLE_ONOFF)))  
             
        
        
        
        
 #       if temp < (user_temp - 0.5):    
 #           self.prop_set_power_control1(Sample(0,
 #                                              Boolean("off",
 #                                                      STYLE_ONOFF)))  
     
        

    
 

    def update_power_state1(self, chan):
        # Perform power control:
        self.prop_set_power_control1(chan.get())
         


    def prop_set_power_control1_high(self, bool_sample):


        if bool_sample.value:
            ddo_io_value = 5 # on
            self.__power_on_time = time.time()
            self.property_set("1_high", Sample(0, 0.0))
            self.property_set("old_thermostat_on",
            Sample(0, Boolean(False, style=STYLE_ONOFF)))           
        else:
            ddo_io_value = 4 # off     
     
        
        extended_address = SettingsBase.get_setting(self, "extended_address")
        try:
            self.__xbee_manager.xbee_device_ddo_set_param(
                                    extended_address, 'D1', ddo_io_value,
                                    apply=True)
        except:
            pass


             

        




    def update_power_state2(self, chan):
        # Perform power control:
        self.prop_set_power_control2(chan.get())

    def prop_set_power_control1_low(self, bool_sample):

        if bool_sample.value:
            ddo_io_value = 5 # on
            self.__power_on_time = time.time()
            self.property_set("1_low", Sample(0, 0.0))
            self.property_set("old_thermostat_on",
            Sample(0, Boolean(True, style=STYLE_ONOFF)))
        else:
            ddo_io_value = 4 # off


        extended_address = SettingsBase.get_setting(self, "extended_address")
        try:
            self.__xbee_manager.xbee_device_ddo_set_param(
                                    extended_address, 'D3', ddo_io_value,
                                    apply=True)
        except:
            pass


        
    def update_power_state3(self, chan):
        # Perform power control:
        self.prop_set_power_control3(chan.get())

    def prop_set_power_control2_high(self, bool_sample):

        if bool_sample.value:
            ddo_io_value = 5 # on
            self.__power_on_time = time.time()
            self.property_set("2_high", Sample(0, 0.0))
            self.property_set("heat_ac_on",
            Sample(0, Boolean(True, style=STYLE_ONOFF)))
        else:
            ddo_io_value = 4 # off


        extended_address = SettingsBase.get_setting(self, "extended_address")
        try:
            self.__xbee_manager.xbee_device_ddo_set_param(
                                    extended_address, 'D6', ddo_io_value,
                                    apply=True)
        except:
            pass


        
    def prop_set_power_control2_low(self, bool_sample):

        if bool_sample.value:
            ddo_io_value = 5 # on
            self.__power_on_time = time.time()
            self.property_set("2_low", Sample(0, 0.0))
            self.property_set("heat_ac_on",
            Sample(0, Boolean(False, style=STYLE_ONOFF)))
        else:
            ddo_io_value = 4 # off


        extended_address = SettingsBase.get_setting(self, "extended_address")
        try:
            self.__xbee_manager.xbee_device_ddo_set_param(
                                    extended_address, 'P2', ddo_io_value,
                                    apply=True)
        except:
            pass



    def prop_set_power_control3_high(self, bool_sample):

        if bool_sample.value:
            ddo_io_value = 5 # on
            self.__power_on_time = time.time()
            self.property_set("3_high", Sample(0, 0.0))
            self.property_set("on_for_ac_off_for_heat_status",
            Sample(0, Boolean(True, style=STYLE_ONOFF)))
        else:
            ddo_io_value = 4 # off


        extended_address = SettingsBase.get_setting(self, "extended_address")
        try:
            self.__xbee_manager.xbee_device_ddo_set_param(
                                    extended_address, 'P0', ddo_io_value,
                                    apply=True)
        except:
            pass




    def prop_set_power_control3_low(self, bool_sample):

        if bool_sample.value:
            ddo_io_value = 5 # on
            self.__power_on_time = time.time()
            self.property_set("3_low", Sample(0, 0.0))
            self.property_set("on_for_ac_off_for_heat_status",
            Sample(0, Boolean(False, style=STYLE_ONOFF)))
        else:
            ddo_io_value = 4 # off


        extended_address = SettingsBase.get_setting(self, "extended_address")
        try:
            self.__xbee_manager.xbee_device_ddo_set_param(
                                    extended_address, 'P1', ddo_io_value,
                                    apply=True)
        except:
            pass




    def prop_set_power_control4_high(self, bool_sample):

        if bool_sample.value:
            ddo_io_value = 5 # on
            self.__power_on_time = time.time()
            self.property_set("4_high", Sample(0, 0.0))
            self.property_set("fan_on",
            Sample(0, Boolean(True, style=STYLE_ONOFF)))
        else:
            ddo_io_value = 4 # off


        extended_address = SettingsBase.get_setting(self, "extended_address")
        try:
            self.__xbee_manager.xbee_device_ddo_set_param(
                                    extended_address, 'D7', ddo_io_value,
                                    apply=True)
        except:
            pass


        
    def prop_set_power_control4_low(self, bool_sample):

        if bool_sample.value:
            ddo_io_value = 5 # on
            self.__power_on_time = time.time()
            self.property_set("4_low", Sample(0, 0.0))
            self.property_set("fan_on",
            Sample(0, Boolean(False, style=STYLE_ONOFF)))
        else:
            ddo_io_value = 4 # off


        extended_address = SettingsBase.get_setting(self, "extended_address")
        try:
            self.__xbee_manager.xbee_device_ddo_set_param(
                                    extended_address, 'D4', ddo_io_value,
                                    apply=True)
        except:
            pass



    
 


# internal functions & classes

def main():
    pass


if __name__ == '__main__':
    import sys
    status = main()
    sys.exit(status)
