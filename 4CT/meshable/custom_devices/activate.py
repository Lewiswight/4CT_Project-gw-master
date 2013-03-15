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
                default_value=10000,
                verify_function=lambda x: x > 0 and x < 0xffff),
            Setting(
                name='idle_off_seconds', type=int, required=False,
                default_value=0, verify_function=lambda x: x >= 0),
            Setting(name='input_source', type=str, required=False, default_value=None),
        ]

        ## Channel Properties Definition:
        property_list = [
            # gettable properties
            ChannelSourceDeviceProperty(name="adder_reg1", type=float,
                initial=Sample(timestamp=0, value=0.0),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.prop_set_adder("adder_reg1", x)),
            ChannelSourceDeviceProperty(name="power_on", type=Boolean,
                initial=Sample(timestamp=0,
                    value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=self.prop_set_power_control1),

        ]

        ## Initialize the XBeeBase interface:
        XBeeBase.__init__(self, self.__name, self.__core,
                                settings_list, property_list) 


    ## Functions which must be implemented to conform to the XBeeBase
    ## interface:


    

    def prop_set_adder(self, register_name, float_sample):
        self.property_set(register_name, float_sample)
        # update total:
        adder_reg1 = self.property_get("adder_reg1").value
   

        
        

        
    

        if adder_reg1 == 1:
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
             

        




    
 


# internal functions & classes

def main():
    pass


if __name__ == '__main__':
    import sys
    status = main()
    sys.exit(status)
