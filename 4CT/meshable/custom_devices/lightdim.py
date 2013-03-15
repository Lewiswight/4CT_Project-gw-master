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
    import XBeeConfigBlockDDO
from devices.xbee.xbee_device_manager.xbee_device_manager_event_specs \
    import *
from devices.xbee.common.addressing import *
from devices.xbee.common.io_sample import parse_is, sample_to_mv
from devices.xbee.common.prodid import PROD_DIGI_XB_WALL_ROUTER

import struct
import time
import threading
import thread

from common.types.boolean import Boolean, STYLE_ONOFF
from devices.xbee.common.io_sample import parse_is, sample_to_mv
from devices.xbee.common.prodid import PROD_DIGI_XB_RPM_SMARTPLUG


# constants
initial_states = ["on", "off", "same"]


# exception classes

# interface functions

# classes
class XBeeXBR(XBeeBase):

    # Define a set of endpoints that this device will send in on.
    ADDRESS_TABLE = [ [0xe8, 0xc105, 0x92], [0xe8, 0xc105, 0x11] ]

    # The list of supported products that this driver supports.
    SUPPORTED_PRODUCTS = [ PROD_DIGI_XB_WALL_ROUTER, PROD_DIGI_XB_RPM_SMARTPLUG, ]

    def __init__(self, name, core_services):
        self.__name = name
        self.__core = core_services


        ## Local State Variables:
        self.__xbee_manager = None

        ## Settings Table Definition:
        settings_list = [
            Setting(
                name='sample_rate_ms', type=int, required=False,
                default_value=1000,
                verify_function=lambda x: x > 0 and x < 0xffff),
            Setting(
                name='default_state1', type=str, required=False,
                default_value="off",
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
            ChannelSourceDeviceProperty(name="input", type=tuple,
                initial=Sample(timestamp=0, value=(0,None)),
                perms_mask=DPROP_PERM_SET | DPROP_PERM_GET,
                set_cb=self.prop_set_power_control1),
            ChannelSourceDeviceProperty(name="utemp", type=float,
                initial=Sample(timestamp=0, unit="F", value=0.0),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name="up", type=float,
                initial=Sample(timestamp=0, unit="mv", value=0.0),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name="aa", type=str,
                initial=Sample(timestamp=0, value="thermostat_switch"),
                 perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET), options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name="down", type=float,
                initial=Sample(timestamp=0, unit="mv", value=0.0),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name="on", type=float,
                initial=Sample(timestamp=0, unit="mv", value=0.0),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name="power_on", type=Boolean,
                initial=Sample(timestamp=0,
                    value=Boolean(True, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=self.prop_set_power_control1),
            ChannelSourceDeviceProperty(name="dim_up", type=Boolean,
                initial=Sample(timestamp=0,
                    value=Boolean(True, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=self.prop_set_power_control2),
            ChannelSourceDeviceProperty(name="dim_down", type=Boolean,
                initial=Sample(timestamp=0,
                    value=Boolean(True, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=self.prop_set_power_control3),
            ChannelSourceDeviceProperty(name="user_input_1", type=str,
                initial=Sample(timestamp=0, value="TempLight.temperature"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.prop_set_adder("user_input_1", x)),
            ChannelSourceDeviceProperty(name="adder_reg1", type=float,
                initial=Sample(timestamp=0, value=0.0),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.prop_set_adder("adder_reg1", x)),
            ChannelSourceDeviceProperty(name="adder_reg2", type=float,
                initial=Sample(timestamp=0, value=0.0),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.prop_set_adder("adder_reg2", x)),
            ChannelSourceDeviceProperty(name="adder_total", type=float,
                initial=Sample(timestamp=0, value=0.0),
                perms_mask=DPROP_PERM_GET, 
                options=DPROP_OPT_AUTOTIMESTAMP, set_cb=self.prop_set_power_control1),  
            ChannelSourceDeviceProperty(name="counter", type=int,
                initial=Sample(timestamp=0, value=0),
                perms_mask=DPROP_PERM_GET|DPROP_PERM_REFRESH, 
                options=DPROP_OPT_AUTOTIMESTAMP,
                refresh_cb = self.refresh_counter),
                
             # settable properties
            ChannelSourceDeviceProperty(name="counter_reset", type=int,
                perms_mask=DPROP_PERM_SET,
                set_cb=self.prop_set_counter_reset),

            ChannelSourceDeviceProperty(name="global_reset", type=int, 
                perms_mask=DPROP_PERM_SET, 
                set_cb=self.prop_set_global_reset),
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

        user_temp = self.property_get("adder_reg1").value    
#        temp = self.my_input    
        
        

        
    

        if user_temp == 1:
            self.prop_set_power_control1(Sample(0, Boolean("on", STYLE_ONOFF)))
            time.sleep(1.5)
            self.prop_set_power_control1(Sample(0, Boolean("off", STYLE_ONOFF)))
 
 
 

        





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
        for io_pin in [ 'D1', 'D2', 'D3' ]:
            xbee_ddo_cfg.add_parameter(io_pin, 2)

        # Get the extended address of the device:
        default_state1 = SettingsBase.get_setting(self, "default_state1")

        if default_state1 != "same":
            # Configure pin DI4 for digital output, default state setting:
            self.prop_set_power_control1(Sample(0,
                                               Boolean(default_state1,
                                                       STYLE_ONOFF)))
        else:
            # Retrieve current state from device for channel
            d4 = self.__xbee_manager.xbee_device_ddo_get_param(extended_address,
                                                               "d4")

            d4 = struct.unpack('B', d4)[0]
            
            if d4 == 5:
                state = True

                # Treat as having just been turned on for shut-off
                self.__power_on_time = time.time()
            elif d4 == 4:
                state = False
            else:
                raise Exception, "Unrecognized initial power_on state"

            self.property_set("power_on",
                              Sample(0,
                                     Boolean(state,
                                             style=STYLE_ONOFF)))  
             
             # Get the extended address of the device:
        default_state2 = SettingsBase.get_setting(self, "default_state2")

        if default_state2 != "same":
            # Configure pin P1 for digital output, default state setting:
            self.prop_set_power_control2(Sample(0,
                                               Boolean(default_state2,
                                                       STYLE_ONOFF)))
        else:
            # Retrieve current state from device for channel
            p1 = self.__xbee_manager.xbee_device_ddo_get_param(extended_address,
                                                               "p1")

            p1 = struct.unpack('B', p1)[0]
            
            if p1 == 5:
                state = True

                # Treat as having just been turned on for shut-off
                self.__power_on_time = time.time()
            elif p1 == 4:
                state = False
            else:
                raise Exception, "Unrecognized initial power_on state"

            self.property_set("dim_up",
                              Sample(0,
                                     Boolean(state,
                                             style=STYLE_ONOFF))) 
            
             # Get the extended address of the device:
        default_state3 = SettingsBase.get_setting(self, "default_state3")

        if default_state3 != "same":
            # Configure pin P2 for digital output, default state setting:
            self.prop_set_power_control3(Sample(0,
                                               Boolean(default_state3,
                                                       STYLE_ONOFF)))
        else:
            # Retrieve current state from device for channel
            p2 = self.__xbee_manager.xbee_device_ddo_get_param(extended_address,
                                                               "p2")

            p2 = struct.unpack('B', p2)[0]
            
            if p2 == 5:
                state = True

                # Treat as having just been turned on for shut-off
                self.__power_on_time = time.time()
            elif p2 == 4:
                state = False
            else:
                raise Exception, "Unrecognized initial power_on state"

            self.property_set("dim_down",
                              Sample(0,
                                     Boolean(state,
                                             style=STYLE_ONOFF)))     
        
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
            
        
            
        power_on_source2 = SettingsBase.get_setting(self, 'power_on_source2')
        if power_on_source2 is not None:
            cm = self.__core.get_service("channel_manager")
            cp = cm.channel_publisher_get()
            cp.subscribe(power_on_source2, self.update_power_state2)
            
        power_on_source3 = SettingsBase.get_setting(self, 'power_on_source3')
        if power_on_source3 is not None:
            cm = self.__core.get_service("channel_manager")
            cp = cm.channel_publisher_get()
            cp.subscribe(power_on_source3, self.update_power_state3)
            


        

        # Register this configuration block with the XBee Device Manager:
        self.__xbee_manager.xbee_device_config_block_add(self, xbee_ddo_cfg)

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
        
        # Parse the I/O sample:
        io_sample = parse_is(buf)

        # Calculate channel values:
       # upbutton_mv, onbutton_mv, downbutton_mv = \
           # map(lambda cn: sample_to_mv(io_sample[cn]), ("AD0", "AD1", "AD2"))

            
 # Calculate sensor channel values:
        if io_sample.has_key("AD1") and io_sample.has_key("AD2") and io_sample.has_key("AD3"):
            light_mv, temperature_mv, humidity_mv = \
                map(lambda cn: sample_to_mv(io_sample[cn]), ("AD1", "AD2", "AD3"))
       
            up = round(light_mv, 2)
            on = round(temperature_mv, 2)
            down = round(humidity_mv, 2)
       
        power_state = self.property_get("power_on").value

        # Update channels:
        self.property_set("up", Sample(0, up, "mv"))
        self.property_set("on", Sample(0, on, "mv"))
        self.property_set("down", Sample(0, down, "mv")) 
        
                        # wire up any inputs
        input_source = SettingsBase.get_setting(self, 'input_source')
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
                self.property_set("utemp", Sample(0, self.my_input, "F"))               
#                self.property_set("input", Sample(0, self.my_input))      
         #       cp.subscribe(source_name, self.update_power_state1)
 #               cp.subscribe( source_name, self.prop_set_input )
 
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
         


    def prop_set_power_control1(self, bool_sample):


        if bool_sample.value:
            ddo_io_value = 5 # on
            self.__power_on_time = time.time()
            self.property_set("adder_reg1", Sample(0, 0.0))
        else:
            ddo_io_value = 4 # off     
     
        
        extended_address = SettingsBase.get_setting(self, "extended_address")
        try:
            self.__xbee_manager.xbee_device_ddo_set_param(
                                    extended_address, 'D4', ddo_io_value,
                                    apply=True)
        except:
            pass

        self.property_set("power_on",
            Sample(0, Boolean(bool_sample.value, style=STYLE_ONOFF)))
             

        




    def update_power_state2(self, chan):
        # Perform power control:
        self.prop_set_power_control2(chan.get())

    def prop_set_power_control2(self, bool_sample):

        if bool_sample.value:
            ddo_io_value = 5 # on
            self.__power_on_time = time.time()
        else:
            ddo_io_value = 4 # off


        extended_address = SettingsBase.get_setting(self, "extended_address")
        try:
            self.__xbee_manager.xbee_device_ddo_set_param(
                                    extended_address, 'P1', ddo_io_value,
                                    apply=True)
        except:
            pass

        self.property_set("dim_up",
            Sample(0, Boolean(bool_sample.value, style=STYLE_ONOFF)))
        
    def update_power_state3(self, chan):
        # Perform power control:
        self.prop_set_power_control3(chan.get())

    def prop_set_power_control3(self, bool_sample):

        if bool_sample.value:
            ddo_io_value = 5 # on
            self.__power_on_time = time.time()
        else:
            ddo_io_value = 4 # off


        extended_address = SettingsBase.get_setting(self, "extended_address")
        try:
            self.__xbee_manager.xbee_device_ddo_set_param(
                                    extended_address, 'P2', ddo_io_value,
                                    apply=True)
        except:
            pass

        self.property_set("dim_down",
            Sample(0, Boolean(bool_sample.value, style=STYLE_ONOFF)))


    
 


# internal functions & classes

def main():
    pass


if __name__ == '__main__':
    import sys
    status = main()
    sys.exit(status)
