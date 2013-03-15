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
    HOUSE_LYNX_VENT


# constants
initial_states = ["on", "off", "same"]


# exception classes

# interface functions

# classes
class Vent(XBeeBase):

    # Define a set of endpoints that this device will send in on.
    ADDRESS_TABLE = [ [0xe8, 0xc105, 0x92], [0xe8, 0xc105, 0x11] ]

    # The list of supported products that this driver supports.
    SUPPORTED_PRODUCTS = [ HOUSE_LYNX_VENT ]

    def __init__(self, name, core_services):
        self.__name = name
        self.__core = core_services
        self.__event_timer = None

        ## Local State Variables:
        self.__xbee_manager = None
        self.update_timer = None

        ## Settings Table Definition:
        settings_list = [
            Setting(
                name='sleep', type=bool, required=False,
                default_value=True),
            Setting(
                name='sample_rate_sec', type=int, required=False,
                default_value=30,
                verify_function=lambda x: x >= 10 and x < 0xffff),
            Setting(
                name='sample_rate_ms', type=int, required=False,
                default_value=5000,
                verify_function=lambda x: x >= 0 and x <= CYCLIC_SLEEP_EXT_MAX_MS), 
            Setting(
                name='awake_time_ms', type=int, required=False,
                default_value=50,
                verify_function=lambda x: x >= 0 and x <= 0xffff),
            Setting(
                name='sample_predelay', type=int, required=False,
                default_value=50,
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
            Setting(name='input_source', type=str, required=False, default_value=None),
        ]

        ## Channel Properties Definition:
        property_list = [
            # gettable properties
#            ChannelSourceDeviceProperty(name="input", type=tuple,
#                initial=Sample(timestamp=0, value=(0,None)),
#                perms_mask=DPROP_PERM_SET | DPROP_PERM_GET,
#                set_cb=self.prop_set_power_control1),
            ChannelSourceDeviceProperty(name="open_close", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(True, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=self.open),
            ChannelSourceDeviceProperty(name="auto", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=self.auto),
            ChannelSourceDeviceProperty(name="aa", type=str,
                initial=Sample(timestamp=0, value="vent"),
                 perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET), options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name="zone_temperature", type=str,
                initial=Sample(timestamp=0, value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.prop_set_adder("zone_temperature", x)),
            ChannelSourceDeviceProperty(name="driving_thermostat", type=str,
                initial=Sample(timestamp=0, value="thermostat.on_for_ac_off_for_heat_status"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.prop_set_adder("driving_thermostat", x)),
            ChannelSourceDeviceProperty(name="battery", type=int,
                initial=Sample(timestamp=0, unit="V", value=0),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name="driving_temp", type=float,
                initial=Sample(timestamp=0, value=0.0),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.prop_set_adder("desired_temp", x)),
            ChannelSourceDeviceProperty(name="desired_temp", type=float,
                initial=Sample(timestamp=0, value=0.0),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.prop_set_adder("desired_temp", x)),
            ChannelSourceDeviceProperty(name="thermostat_mode", type=str,
                initial=Sample(timestamp=0, unit="N/A", value="Off"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP),
                
            
                
                
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


    def setup(self, bool_sample):
        
        self.vent_open(Sample(0, Boolean("on", STYLE_ONOFF)))
        time.sleep(.5)
        self.vent_open(Sample(0, Boolean("off", STYLE_ONOFF)))
        
    def prop_set_adder(self, register_name, float_sample):
        self.property_set(register_name, float_sample)
        

                                         
        
    def auto(self, bool_sample):
        
        self.property_set("auto",
            Sample(0, Boolean(bool_sample.value, style=STYLE_ONOFF)))
        
        self.update()
        
        
        
        

             
        
    
            
            
        
   
                                                
            
    def open(self, bool_sample):
        
        self.property_set("open_close",
            Sample(0, Boolean(bool_sample.value, style=STYLE_ONOFF)))
        
        if bool_sample.value:        
            self.vent_open(Sample(0, Boolean("on", STYLE_ONOFF)))
            time.sleep(.5)
            self.vent_open(Sample(0, Boolean("off", STYLE_ONOFF)))
            
        
        if not bool_sample.value:
            self.vent_close(Sample(0, Boolean("on", STYLE_ONOFF)))
            time.sleep(.5)
            self.vent_close(Sample(0, Boolean("off", STYLE_ONOFF)))
            
        

        
        
        
        
    
        
        


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

        for address in Vent.ADDRESS_TABLE:
            probe_data['address_table'].append(address)
        for product in Vent.SUPPORTED_PRODUCTS:
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

        
        xbee_ddo_cfg.add_parameter('D3', 2) 
        

        for io_pin in ['P0', 'P2' ]:
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
        
        
        
        self.setup(Sample(0, Boolean("on", STYLE_ONOFF)))
 




        # Indicate that we have no more configuration to add:
        self.__xbee_manager.xbee_device_configure(self)
        


        return True

    def stop(self):
        """Stop the device driver.  Returns bool."""
        # Unregister ourselves with the XBee Device Manager instance:
        self.__xbee_manager.xbee_device_unregister(self)

        return True
        

    ## Locally defined functions:
    
    
    def __upload_data(self):
        """
        Builds XML string of the channel state and pushes to iDigi
        """
        
        
#         print "idigi_db: Uploading to iDigi"

        cm = self.__core.get_service("channel_manager")
        cdb = cm.channel_database_get()
        channel_list = SettingsBase.get_setting(self, "channels")
        
        if len(channel_list) == 0:
            channel_list = cdb.channel_list()

        

        for channel_name in channel_list:
            try:
                channel = cdb.channel_get(channel_name)
                sample = channel.get()
                if sample.unit == "o/h/c/a":  
                    self.property_set("thermostat_mode", Sample(0, channel, "F"))
                    print channel_name
                    print channel
                    pass         
            except:
                pass
               

        xml.write("&lt;/idigi_data&gt;")

        if new_sample_count > 0:
            self.__last_upload_time = time.time()
            self.__send_to_idigi(xml.getvalue())

        xml.close()

#         print "idigi_db: I uploaded to iDigi"
    
    
    def update(self):
        
        
        desired = self.property_get("desired_temp").value
        auto = self.property_get("auto").value

        cm = self.__core.get_service("channel_manager")
        cp = cm.channel_publisher_get()
        cdb = cm.channel_database_get()


        source_name = self.property_get("zone_temperature").value
            
        if source_name != None:
            source_chan = cdb.channel_get(source_name)
                # pre-load the starting value, which won't be published to us
            self.my_input = source_chan.get().value
            self.property_set("driving_temp", Sample(0, self.my_input, "F"))
            
       
        source_name2 = "thermostat.mode"  
        source_chan1 = cdb.channel_get(source_name2)
                # pre-load the starting value, which won't be published to us
        mode = source_chan1.get().value 
        
        room_1 = self.my_input + 0.5
        room_2 = self.my_input - 0.5         
                
        if auto:
            if mode == "C":
                if room_2 < desired:
                    self.open(Sample(0, Boolean("off", STYLE_ONOFF)))
                if room_1 > desired:
                    self.open(Sample(0, Boolean("on", STYLE_ONOFF)))        
            if mode == "H":  
                if room_1 > desired:
                    self.open(Sample(0, Boolean("off", STYLE_ONOFF)))
                if room_2 < desired:
                    self.open(Sample(0, Boolean("on", STYLE_ONOFF)))
        
        
        
        

        #Reschedule this update method
        if self.__event_timer is not None:
            try:
                self.__xbee_manager.xbee_device_schedule_cancel(
                    self.__event_timer)
            except:
                pass
            
        self.__event_timer = self.__xbee_manager.xbee_device_schedule_after(
                SettingsBase.get_setting(self, "sample_rate_sec"),
                self.update)
    
    def sample_indication(self, buf, addr):


        # Parse the I/O sample:
        io_sample = parse_is(buf)
        
        # Calculate sensor channel values:
        if io_sample.has_key("AD3"):
            samp = Sample(0, value=int(io_sample["AD3"]), unit="V")
            self.property_set("battery", samp)
        
        
        return
    
    
            
            
                   

            
 
  
         


    def vent_close(self, bool_sample):


        if bool_sample.value:
            ddo_io_value = 5 # on
            self.__power_on_time = time.time()           
        else:
            ddo_io_value = 4 # off     
     
        
        extended_address = SettingsBase.get_setting(self, "extended_address")
        try:
            self.__xbee_manager.xbee_device_ddo_set_param(
                                    extended_address, 'P0', ddo_io_value,
                                    apply=True)
        except:
            pass


             

        

    def vent_open(self, bool_sample):

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


        

   




    
 


# internal functions & classes

def main():
    pass


if __name__ == '__main__':
    import sys
    status = main()
    sys.exit(status)
