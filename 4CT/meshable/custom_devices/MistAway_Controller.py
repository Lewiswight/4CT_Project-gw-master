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

from common.types.boolean import Boolean, STYLE_ONOFF
from devices.xbee.xbee_config_blocks.xbee_config_block_ddo \
    import XBeeConfigBlockDDO
from devices.xbee.xbee_device_manager.xbee_device_manager_event_specs \
    import *
from devices.xbee.common.addressing import *
from devices.xbee.common.prodid import MISTAWAY_CONTROLLER











# constants
TABLE = (
		0x0000, 0xC0C1, 0xC181, 0x0140, 0xC301, 0x03C0, 0x0280, 0xC241,
		0xC601, 0x06C0, 0x0780, 0xC741, 0x0500, 0xC5C1, 0xC481, 0x0440,
		0xCC01, 0x0CC0, 0x0D80, 0xCD41, 0x0F00, 0xCFC1, 0xCE81, 0x0E40,
		0x0A00, 0xCAC1, 0xCB81, 0x0B40, 0xC901, 0x09C0, 0x0880, 0xC841,
		0xD801, 0x18C0, 0x1980, 0xD941, 0x1B00, 0xDBC1, 0xDA81, 0x1A40,
		0x1E00, 0xDEC1, 0xDF81, 0x1F40, 0xDD01, 0x1DC0, 0x1C80, 0xDC41,
		0x1400, 0xD4C1, 0xD581, 0x1540, 0xD701, 0x17C0, 0x1680, 0xD641,
		0xD201, 0x12C0, 0x1380, 0xD341, 0x1100, 0xD1C1, 0xD081, 0x1040,
		0xF001, 0x30C0, 0x3180, 0xF141, 0x3300, 0xF3C1, 0xF281, 0x3240,
		0x3600, 0xF6C1, 0xF781, 0x3740, 0xF501, 0x35C0, 0x3480, 0xF441,
		0x3C00, 0xFCC1, 0xFD81, 0x3D40, 0xFF01, 0x3FC0, 0x3E80, 0xFE41,
		0xFA01, 0x3AC0, 0x3B80, 0xFB41, 0x3900, 0xF9C1, 0xF881, 0x3840,
		0x2800, 0xE8C1, 0xE981, 0x2940, 0xEB01, 0x2BC0, 0x2A80, 0xEA41,
		0xEE01, 0x2EC0, 0x2F80, 0xEF41, 0x2D00, 0xEDC1, 0xEC81, 0x2C40,
		0xE401, 0x24C0, 0x2580, 0xE541, 0x2700, 0xE7C1, 0xE681, 0x2640,
		0x2200, 0xE2C1, 0xE381, 0x2340, 0xE101, 0x21C0, 0x2080, 0xE041,
		0xA001, 0x60C0, 0x6180, 0xA141, 0x6300, 0xA3C1, 0xA281, 0x6240,
		0x6600, 0xA6C1, 0xA781, 0x6740, 0xA501, 0x65C0, 0x6480, 0xA441,
		0x6C00, 0xACC1, 0xAD81, 0x6D40, 0xAF01, 0x6FC0, 0x6E80, 0xAE41,
		0xAA01, 0x6AC0, 0x6B80, 0xAB41, 0x6900, 0xA9C1, 0xA881, 0x6840,
		0x7800, 0xB8C1, 0xB981, 0x7940, 0xBB01, 0x7BC0, 0x7A80, 0xBA41,
		0xBE01, 0x7EC0, 0x7F80, 0xBF41, 0x7D00, 0xBDC1, 0xBC81, 0x7C40,
		0xB401, 0x74C0, 0x7580, 0xB541, 0x7700, 0xB7C1, 0xB681, 0x7640,
		0x7200, 0xB2C1, 0xB381, 0x7340, 0xB101, 0x71C0, 0x7080, 0xB041,
		0x5000, 0x90C1, 0x9181, 0x5140, 0x9301, 0x53C0, 0x5280, 0x9241,
		0x9601, 0x56C0, 0x5780, 0x9741, 0x5500, 0x95C1, 0x9481, 0x5440,
		0x9C01, 0x5CC0, 0x5D80, 0x9D41, 0x5F00, 0x9FC1, 0x9E81, 0x5E40,
		0x5A00, 0x9AC1, 0x9B81, 0x5B40, 0x9901, 0x59C0, 0x5880, 0x9841,
		0x8801, 0x48C0, 0x4980, 0x8941, 0x4B00, 0x8BC1, 0x8A81, 0x4A40,
		0x4E00, 0x8EC1, 0x8F81, 0x4F40, 0x8D01, 0x4DC0, 0x4C80, 0x8C41,
		0x4400, 0x84C1, 0x8581, 0x4540, 0x8701, 0x47C0, 0x4680, 0x8641,
		0x8201, 0x42C0, 0x4380, 0x8341, 0x4100, 0x81C1, 0x8081, 0x4040 )
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
    
    
    
    
    
 
    
			
    ADDRESS_TABLE = [ [0xe8, 0xc105, 0x11] ]
    
    SUPPORTED_PRODUCTS = [ MISTAWAY_CONTROLLER ]
    
    def __init__(self, name, core_services):
        self.__name = name
        self.__core = core_services
        self.__event_timer2 = None


        ## Local State Variables:
        self._count = 0
        self.__xbee_manager = None
        self.update_timer = None
        self.modes = {"O":0, "H":1, "C":2, "A":3}
        self.count = 0
        

        ## Settings Table Definition:
        settings_list = [
            Setting(
                name='xbee_device_manager', type=str, required=True),
            Setting(
                name='compact_xml', type=bool, required=False, default_value=False),
            Setting(
                name="channels", type=list, required=False, default_value=[]),
            Setting(
                name='extended_address', type=str, required=True),
            Setting(
                name='sample_rate_sec', type=int, required=False,
                default_value=300,
                verify_function=lambda x: x >= 10 and x < 0xffff),
        ]

        ## Channel Properties Definition:
        property_list = [
            # gettable properties
            ChannelSourceDeviceProperty(name="mist_cycle", type=str,
                initial=Sample(timestamp=0, unit="F", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name="status", type=str,
                initial=Sample(timestamp=0, unit="F", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name="serialReceive", type=str,
                initial=Sample(timestamp=0, unit="F", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name="serialSend", type=str,
                initial=Sample(timestamp=0, unit="F", value=" "),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=self.serial_write),
            ChannelSourceDeviceProperty(name="stop_mist", type=int,
                initial=Sample(timestamp=0, unit="F", value=1),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.stop_mist("stop_mist", x)),
            ChannelSourceDeviceProperty(name="update", type=int,
                initial=Sample(timestamp=0, unit="F", value=1),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.new_update("update", x)),
            ChannelSourceDeviceProperty(name="mist", type=int,
                initial=Sample(timestamp=0, unit="F", value=1),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.mist("mist", x)),
            ChannelSourceDeviceProperty(name="cartridge_remaining_volume", type=int,
                initial=Sample(timestamp=0, unit="F", value=1),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP),
           #     set_cb=lambda x: self.set_sph("cartridge_remaining_volume", x)),
            ChannelSourceDeviceProperty(name="cartridge_full_volume", type=int,
                initial=Sample(timestamp=0, unit="F", value=1),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP),
        #        set_cb=lambda x: self.set_sph("cartridge_full_volume", x)),
            ChannelSourceDeviceProperty(name="crc", type=int,
                initial=Sample(timestamp=0, unit="F", value=1),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP),
        #        set_cb=lambda x: self.set_sph("crc", x)),
                
            
        ]

        ## Initialize the XBeeSerial interface:
        XBeeSerial.__init__(self, self.__name, self.__core,    
                                settings_list, property_list)


    
    
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
       ## Functions which must be implemented to conform to the XBeeSerial
    ## interface:
              
    
    
    def read_callback(self, buf):
        self.serial_read(buf)


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

        #register a callback for when the config is done
        xb_rdy_state_spec = XBeeDeviceManagerRunningEventSpec()
        xb_rdy_state_spec.cb_set(self._config_done_cb)
        self.__xbee_manager.xbee_device_event_spec_add(self, xb_rdy_state_spec)
        
        # Create a DDO configuration block for this device:
        xbee_ddo_cfg = XBeeConfigBlockDDO(extended_address)

        # Call the XBeeSerial function to add the initial set up of our device.
        # This will set up the destination address of the devidce, and also set
        # the default baud rate, parity, stop bits and flow control.
        XBeeSerial.initialize_xbee_serial(self, xbee_ddo_cfg)

        # Register this configuration block with the XBee Device Manager:
        self.__xbee_manager.xbee_device_config_block_add(self, xbee_ddo_cfg)

        # Indicate that we have no more configuration to add:
        self.__xbee_manager.xbee_device_configure(self)

        return True

    def calcByte(self, ch, crc):
	    """Given a new Byte and previous CRC, Calc a new CRC-16"""
	    if type(ch) == type("c"): 
	        by = ord(ch)
	    else:
	        by = ch
	    crc = (crc >> 8) ^ TABLE[(crc ^ by) & 0xFF]
	    return (crc & 0xFFFF)
	 
    def calcString(self, st, crc):
	    """Given a bunary string and starting CRC, Calc a final CRC-16 """
	    for ch in st:
	        crc = (crc >> 8) ^ TABLE[(crc ^ ord(ch)) & 0xFF]
	    return crc  
    
    def update(self):
        """
            Request the latest data from the device.
        """

       
        
        try:
            self.serial_send("r=1,")
 
        except:
        	print "error sending request to mistaway controller"
        
        

        #Reschedule this update method
        if self.__event_timer2 is not None:
            try:
                self.__xbee_manager.xbee_device_schedule_cancel(
                    self.__event_timer2)
            except:
                pass
            
        self.__event_timer2 = self.__xbee_manager.xbee_device_schedule_after(
                SettingsBase.get_setting(self, "sample_rate_sec"),
                self.update)
    
      #  self.property_set("update",
       #                         Sample(0, value="0", unit=""))
    
    
    def stop(self):

        # Unregister ourselves with the XBee Device Manager instance:
        self.__xbee_manager.xbee_device_unregister(self)
        

        return True


    ## Locally defined functions:

    def _parse_return_message(self, msg):
        """ Take a status string from thermostat, and
            split it up into a dictionary::
            
                "A" "0" "T=74" -> {'A':0, 'T':74}
            
        """
       # msg.replace(",$", " ")
      #  msg.replace(",", " ")
        
        
        msg = msg.strip()
        
        msg = msg + "=1"
        print msg
        try:
            if not msg:
                return {}
            
            ret = {}
            split_msg = msg.split(",") #tokenize
            print split_msg
            for i in split_msg:
                i = i.split("=")
                ret[i[0]] = i[1]

            print ret
            return ret

        except:
            print "Error parsing return message: " + repr(msg)
            return {}

    def new_update(self, register_name, val):
    	
    	self.property_set(register_name, val)
    	self.update()
    
    def mist(self, register_name, val):
        """ start mist cycle """
        
        self.property_set(register_name, val)
        
        try:
            self.serial_send("r=m,")
        except:
        	print "error setting thermostat"

        self.update()

    def stop_mist(self, register_name, val):
        """ stop mist cycle """
        
        self.property_set(register_name, val)
        
        
        try:
            self.serial_send("r=s,")
        except:
        	print "error setting thermostat"

        self.update()

    


    def _config_done_cb(self):
        """ Indicates config is done. """
        print self.__name + " is done configuring, starting polling"
        self.test = 0
        self.update()
        


    
            
    
    def serial_read(self, buf):
        print "XBeeSerialTerminal: Read Data: %s" % (buf)
        
        
      
      
      
      
      #  crc = crc16xmodem(buf) 
      #  print crc
       
        
        self.property_set("serialReceive", Sample(0, buf, ""))    

        d = self._parse_return_message(buf)
        
        sample1 = buf[:-11]
        print sample1
        
        if d.has_key("st") and d["st"] != "ACK":   
	        if d.has_key("crc") :
	        	print "found crc"
	        	if int(d["crc"]) == int(self.calcString(sample1, 0)):
	        	#	self.serial_send("r=ACK,")
	        		print "crc's matched, request finished"
	        	else:
	        		self.serial_send("r=NAK,")
	        		print "crc mis match, send NAK"
	        else:
	        	#self.serial_send("r=NAK,")
	        	print "no crc found in dictionary"
        else:
            pass		
        	   
        	
        if d.has_key("mc"):
            self.property_set("mist_cycle",
                                Sample(0, value=d["mc"], unit=""))
            self.serial_send("r=ACK,")
        if d.has_key("st") and d["st"] != "ACK":
            self.property_set("status",
                                Sample(0, value=d["st"], unit=""))
        if d.has_key("cfv"):
            self.property_set("cartridge_full_volume", 
                                Sample(0, value=int(d["cfv"]), unit=""))
        if d.has_key("cr"):
            self.property_set("cartridge_remaining_volume",
                                Sample(0, value=int(d["cr"]), unit="F"))   
        if d.has_key("crc"):
            self.property_set("crc",
                                Sample(0, value=int(d["crc"]), unit="F"))
        
        
        
        
        
        
        
        
        
        
        
        
        

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
    
    
    
    def serial_send(self, data):
        print "XBeeSerialTerminal: Write Data: %s" % (data)
        #buf = data.value + chr(0x0D)
  #      buf = data.value
        
        data1 = data  + "crc=" + str(self.calcString(data, 0)) + ",$"
        
        try:
            ret = self.write(str(data1)) 
          #  ret = self.write("r=1,crc=63902,$")
            print data1
  #          print self.calcByte( "r=1", INITIAL_DF1)
            if ret == False:
                raise Exception, "write failed"
        except:
            print "XBeeSerialTerminal: Error writing data: %s" % (buf)

# internal functions & classes

