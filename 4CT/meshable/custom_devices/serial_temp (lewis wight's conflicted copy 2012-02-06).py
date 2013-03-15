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
Dia XBee Serial Terminal Driver 

To Use:

	Issue web services channel_set call to send data to serial device
		 <data><channel_set name="serial-name.serialSend" value="string to send"/></data>

	Issue web services channel_get (or channel_dump) call to read serial device
		 <data><channel_get name="serial-name.serialReceive"/></data>
		 or
		 <data><channel_dump/></data>

"""

# imports
import struct

from devices.device_base import DeviceBase
from devices.xbee.xbee_devices.xbee_base import XBeeBase
from devices.xbee.xbee_devices.xbee_serial import XBeeSerial
from settings.settings_base import SettingsBase, Setting
from channels.channel_source_device_property import *


from devices.xbee.xbee_device_manager.xbee_ddo_param_cache import XBeeDDOParamCache 


from common.types.boolean import Boolean, STYLE_ONOFF

from devices.xbee.xbee_config_blocks.xbee_config_block_ddo \
    import XBeeConfigBlockDDO, DDO_GET_PARAM
from devices.xbee.xbee_config_blocks.xbee_config_block_sleep \
    import CYCLIC_SLEEP_EXT_MAX_MS, SM_DISABLED, XBeeConfigBlockSleep
from devices.xbee.xbee_device_manager.xbee_device_manager_event_specs \
    import *
from devices.xbee.common.addressing import *
from devices.xbee.common.io_sample import parse_is, sample_to_mv
from devices.xbee.common.prodid \
    import MOD_XB_ZB, parse_dd, format_dd, product_name, \
    SERIAL_TEMP
# constants

# exception classes

# interface functions

# classes
class XBeeSerialTerminal(XBeeSerial):
    """\
        This class extends one of our base classes and is intended as an
        example of a concrete, example implementation, but it is not itself
        meant to be included as part of our developer API. Please consult the
        base class documentation for the API and the source code for this file
        for an example implementation.

    """
    SUPPORTED_PRODUCTS = [ SERIAL_TEMP ]
    
    def __init__(self, name, core_services):
        self.__name = name
        self.__core = core_services
        self.string = ""
        self.signals = 0
        self.include_unit = "F"
        self.sleeping = 0
        self.count = 700

        ## Local State Variables:
        self.__xbee_manager = None

        ## Settings Table Definition:
        settings_list = [
            Setting(
                name='sleep', type=bool, required=False,
                default_value=True),
            Setting(
                name='sample_rate_ms', type=int, required=False,
                default_value=5000),
            # These settings are provided for advanced users, they
            # are not required:
            Setting(
                name='awake_time_ms', type=int, required=False,
                default_value=700,
                verify_function=lambda x: x >= 0 and x <= 0xffff),
            Setting(
                name='sample_predelay', type=int, required=False,
                default_value=0,
                verify_function=lambda x: x >= 0 and x <= 0xffff)

        ]

        ## Channel Properties Definition:
        property_list = [
            # gettable properties
             ChannelSourceDeviceProperty(name="excl", type=Boolean,
                initial=Sample(timestamp=1315351550.0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.exclude("excl", x)),
             ChannelSourceDeviceProperty(name="signal", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
             ChannelSourceDeviceProperty(name="volts", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
             ChannelSourceDeviceProperty(name="get_signal", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(True, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
               set_cb=lambda x: self.set_sig_update()),
             ChannelSourceDeviceProperty(name="incl", type=Boolean,
                initial=Sample(timestamp=1315351550.0,
                value=Boolean(True, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.include("incl", x)),
            ChannelSourceDeviceProperty(name="temperature", type=float,
                initial=Sample(timestamp=0, value=0.0, unit="F"),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name="low_battery", type=bool,
                initial=Sample(timestamp=0, value=False),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name="read", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name="write", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=self.serial_write),
        ]

        ## Initialize the XBeeSerial interface:
        XBeeSerial.__init__(self, self.__name, self.__core,    
                                settings_list, property_list)


    ## Functions which must be implemented to conform to the XBeeSerial
    ## interface:
                
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

        for address in XBeeSerialTerminal.ADDRESS_TABLE:
            probe_data['address_table'].append(address)
        for product in XBeeSerialTerminal.SUPPORTED_PRODUCTS:
            probe_data['supported_products'].append(product)

        return probe_data

    ## Functions which must be implemented to conform to the DeviceBase
    ## interface:
    
    def read_callback(self, buf):
       finish = self.serial_read(buf)
       print finish


    ## Functions which must be implemented to conform to the DeviceBase
    ## interface:

    def apply_settings(self):

        SettingsBase.merge_settings(self)
        accepted, rejected, not_found = SettingsBase.verify_settings(self)

        if len(rejected) or len(not_found):
            # there were problems with settings, terminate early:
            return (accepted, rejected, not_found)

        SettingsBase.commit_settings(self, accepted)

        return (accepted, rejected, not_found)

    def start(self):

        # Fetch the XBee Manager name from the Settings Manager:
        xbee_manager_name = SettingsBase.get_setting(self, "xbee_device_manager")
        dm = self.__core.get_service("device_driver_manager")
        self.__xbee_manager = dm.instance_get(xbee_manager_name)

        # Register ourselves with the XBee Device Manager instance:
        self.__xbee_manager.xbee_device_register(self)

        # Get the extended address of the device:
        extended_address = SettingsBase.get_setting(self, "extended_address")

        # Create a DDO configuration block for this device:
        xbee_ddo_cfg = XBeeConfigBlockDDO(extended_address)

        # Call the XBeeSerial function to add the initial set up of our device.
        # This will set up the destination address of the devidce, and also set
        # the default baud rate, parity, stop bits and flow control.
        XBeeSerial.initialize_xbee_serial(self, xbee_ddo_cfg)

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
            xbee_sleep_cfg.sleep_cycle_set(awake_time_ms, sleep_rate_ms, enable_pin_wake=True)
        else:
            xbee_sleep_cfg.sleep_mode_set(SM_DISABLED)
        self.__xbee_manager.xbee_device_config_block_add(self, xbee_sleep_cfg)
        
          
            
        self.property_set("incl", Sample(0, value=Boolean(bool(1), style=STYLE_ONOFF)))
        self.property_set("excl", Sample(0, value=Boolean(bool(0), style=STYLE_ONOFF)))

        # Indicate that we have no more configuration to add:
        self.__xbee_manager.xbee_device_configure(self)

        
        
        
        return True

    def stop(self):

        # Unregister ourselves with the XBee Device Manager instance:
        self.__xbee_manager.xbee_device_unregister(self)

        return True


    ## Locally defined functions:

   
    
    def set_sig_update(self):
    	
    	
    	self.count = 720
    
    def exclude(self, register_name, val):
        
        
        self.property_set(register_name, val)
    
    def get_signal(self):
    	
    	extended_address = SettingsBase.get_setting(self, "extended_address")
        
        
        
        try:
        
	        db = self.__xbee_manager.xbee_device_ddo_get_param(extended_address,
	                                                                  "DB", use_cache=True)
	  #      sv = self.__xbee_manager.xbee_device_ddo_get_param(extended_address,
	   #                                                               "%V", use_cache=True)
	        
	        
	        
	        try:
	            dd = struct.unpack(">B", db)
	            #print dd
	        except:
	        	self.property_set("signal", Sample(0, value="disconnected", unit=""))
	        	print "failed 4"     
	        
	     #   try:
	      #  	sv = struct.unpack(">H", sv)
	      #  except:
	        #	self.property_set("volts", Sample(0, value="failed", unit=""))
	       # print sv
	
	        dd = str(dd)
	        dd = dd[1:3]
	        dd = "-" + dd + " dB"
	      #  print "signal strength ="
	      #  print dd
	        self.property_set("signal", Sample(0, value=str(dd), unit=""))
	        
	        
	        
	    #    sv = str(sv)
	    #    sv = sv[1:5]
	     #   sv = int(sv)
	    #    print sv
	    #    volts = (sv * 1.1719) / 1000
	     #   print "volts ="
	     #   print volts
	      #  self.property_set("volts", Sample(0, value=str(volts), unit=""))

	    

        
        
        except:
        
        #	self.property_set("signal", Sample(0, value="disconnected", unit=""))
        	print "failed to get signal and voltage"
        
        
    
            
    def serial_read(self, buf):
        
        if self.count == 720:
                self.get_signal()
        	
        
            
        if self.count == 720:
            self.count = 0
        
        
        if self.count < 722:
            self.count += 1
        
        
        print "XBeeSerialTerminal: Read Data: %s" % (buf)
    	
    	buf = str(buf)
    	
    	
    	if not buf.endswith("$"):
        	self.string = self.string + buf
        	
        if buf.endswith("$"):
        	self.signals = 0
	    	self.string = self.string + buf
	    	self.string = self.string[:-1]
	    	print self.string 
	    	try:
	    		self.string = float(self.string)
	    	except:
	    		self.string = ""
	    		return False
	    		
    	
	    	try:
	    		self.property_set("temperature", Sample(0, value=float(self.string), unit=self.include_unit))
	    	except:
	    		self.string = ""
    		self.string = ""
    		
    	excl = self.property_get("excl").value
        
        if excl:
            self.property_set("excl", Sample(0, value=Boolean(bool(0), style=STYLE_ONOFF)))
        
        return True
    	

    def include(self, register_name, val):
    
         self.property_set(register_name, val)
         incl = self.property_get("incl").value
         temperature = self.property_get("temperature").value
         date = self.property_get("temperature").timestamp 
         
         if incl:
             self.include_unit = "F"
         else:
             self.include_unit = "uF"
             
         self.property_set("temperature", Sample(date, temperature, self.include_unit))
    
    def serial_write(self, data):
        print "XBeeSerialTerminal: Write Data: %s" % (data.value)
        #buf = data.value + chr(0x0D)
        buf = data.value
        try:
            ret = self.write(buf)
            if ret == False:
                raise Exception, "write failed"
        except:
            print "XBeeSerialTerminal: Error writing data: %s" % (buf)

# internal functions & classes

