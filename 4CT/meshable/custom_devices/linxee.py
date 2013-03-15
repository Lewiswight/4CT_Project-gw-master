
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

#from devices.device_base import DeviceBase
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
from devices.xbee.common.prodid import RCS_THERMOSTAT
import time
import thread
 
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
    
    SUPPORTED_PRODUCTS = [ RCS_THERMOSTAT ]
    
    def __init__(self, name, core_services):
        self.__name = name
        self.__core = core_services
        self.__event_timer2 = None
        self.string = ""


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
                default_value=30,
                verify_function=lambda x: x >= 10 and x < 0xffff),
        ]

        ## Channel Properties Definition:
        property_list = [
            # gettable properties
			            
			
            ChannelSourceDeviceProperty(name="hd1_on", type=str,
                  initial=Sample(timestamp=0, unit="", value="O"),
                  perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                  options=DPROP_OPT_AUTOTIMESTAMP,
                  set_cb=lambda x: self.update("hd1_on", x)),
            
            ChannelSourceDeviceProperty(name="cd1_on", type=str,
                  initial=Sample(timestamp=0, unit="", value="O"),
                  perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                  options=DPROP_OPT_AUTOTIMESTAMP,
                  set_cb=lambda x: self.update("cd1_on", x)),
            
            ChannelSourceDeviceProperty(name="hd1_off", type=str,
                  initial=Sample(timestamp=0, unit="", value="O"),
                  perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                  options=DPROP_OPT_AUTOTIMESTAMP,
                  set_cb=lambda x: self.update("hd1_off", x)),
            
            ChannelSourceDeviceProperty(name="cd1_off", type=str,
                  initial=Sample(timestamp=0, unit="", value="O"),
                  perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                  options=DPROP_OPT_AUTOTIMESTAMP,
                  set_cb=lambda x: self.update("cd1_off", x)),
                  
            ChannelSourceDeviceProperty(name="hd2_on", type=str,
                  initial=Sample(timestamp=0, unit="", value="O"),
                  perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                  options=DPROP_OPT_AUTOTIMESTAMP,
                  set_cb=lambda x: self.update("hd2_on", x)), 
            
            ChannelSourceDeviceProperty(name="hd2_off", type=str,
                  initial=Sample(timestamp=0, unit="", value="O"),
                  perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                  options=DPROP_OPT_AUTOTIMESTAMP,
                  set_cb=lambda x: self.update("hd2_off", x)),
            
            ChannelSourceDeviceProperty(name="hd3_on", type=str,
                  initial=Sample(timestamp=0, unit="", value="O"),
                  perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                  options=DPROP_OPT_AUTOTIMESTAMP,
                  set_cb=lambda x: self.update("hd3_on", x)),
            
            ChannelSourceDeviceProperty(name="hd3_off", type=str,
                  initial=Sample(timestamp=0, unit="", value="O"),
                  perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                  options=DPROP_OPT_AUTOTIMESTAMP,
                  set_cb=lambda x: self.update("hd3_off", x)),
            
            ChannelSourceDeviceProperty(name="cd2_on", type=str,
                  initial=Sample(timestamp=0, unit="", value="O"),
                  perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                  options=DPROP_OPT_AUTOTIMESTAMP,
                  set_cb=lambda x: self.update("cd2_on", x)),
                  
            
            ChannelSourceDeviceProperty(name="cd2_off", type=str,
                  initial=Sample(timestamp=0, unit="", value="O"),
                  perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                  options=DPROP_OPT_AUTOTIMESTAMP,
                  set_cb=lambda x: self.update("cd2_off", x)),
            
            ChannelSourceDeviceProperty(name="tm", type=str,
                  initial=Sample(timestamp=0, unit="", value="O"),
                  perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                  options=DPROP_OPT_AUTOTIMESTAMP,
                  set_cb=lambda x: self.update("tm", x)),
            
            ChannelSourceDeviceProperty(name="mont", type=str,
                  initial=Sample(timestamp=0, unit="", value="O"),
                  perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                  options=DPROP_OPT_AUTOTIMESTAMP,
                  set_cb=lambda x: self.update("mont", x)),
            
            ChannelSourceDeviceProperty(name="mofft", type=str,
                  initial=Sample(timestamp=0, unit="", value="O"),
                  perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                  options=DPROP_OPT_AUTOTIMESTAMP,
                  set_cb=lambda x: self.update("mofft", x)),
            
            ChannelSourceDeviceProperty(name="cs", type=str,
			      initial=Sample(timestamp=0, unit="", value="O"),
			      perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
			      options=DPROP_OPT_AUTOTIMESTAMP,
			      set_cb=lambda x: self.update("cs", x)),
			
            ChannelSourceDeviceProperty(name="ht1on", type=str,
			      initial=Sample(timestamp=0, unit="", value="O"),
			      perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
			      options=DPROP_OPT_AUTOTIMESTAMP,
			      set_cb=lambda x: self.update("ht1on", x)),
			
            ChannelSourceDeviceProperty(name="ht2on", type=str,
			      initial=Sample(timestamp=0, unit="", value="O"),
			      perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
			      options=DPROP_OPT_AUTOTIMESTAMP,
			      set_cb=lambda x: self.update("ht2on", x)),
			
            ChannelSourceDeviceProperty(name="ht3on", type=str,
			      initial=Sample(timestamp=0, unit="", value="O"),
			      perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
			      options=DPROP_OPT_AUTOTIMESTAMP,
			      set_cb=lambda x: self.update("ht3on", x)),
			      
			ChannelSourceDeviceProperty(name="ht1off", type=str,
                  initial=Sample(timestamp=0, unit="", value="O"),
                  perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                  options=DPROP_OPT_AUTOTIMESTAMP,
                  set_cb=lambda x: self.update("ht1off", x)),
            
            ChannelSourceDeviceProperty(name="ht2off", type=str,
                  initial=Sample(timestamp=0, unit="", value="O"),
                  perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                  options=DPROP_OPT_AUTOTIMESTAMP,
                  set_cb=lambda x: self.update("ht2off", x)),
            
            ChannelSourceDeviceProperty(name="ht3off", type=str,
                  initial=Sample(timestamp=0, unit="", value="O"),
                  perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                  options=DPROP_OPT_AUTOTIMESTAMP,
                  set_cb=lambda x: self.update("ht3off", x)),
            
            ChannelSourceDeviceProperty(name="ct1on", type=str,
                  initial=Sample(timestamp=0, unit="", value="O"),
                  perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                  options=DPROP_OPT_AUTOTIMESTAMP,
                  set_cb=lambda x: self.update("ct1on", x)),
            
            ChannelSourceDeviceProperty(name="ct2on", type=str,
                  initial=Sample(timestamp=0, unit="", value="O"),
                  perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                  options=DPROP_OPT_AUTOTIMESTAMP,
                  set_cb=lambda x: self.update("ct2on", x)),
            
            
            ChannelSourceDeviceProperty(name="ct1off", type=str,
                  initial=Sample(timestamp=0, unit="", value="O"),
                  perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                  options=DPROP_OPT_AUTOTIMESTAMP,
                  set_cb=lambda x: self.update("ct1off", x)),
            
            ChannelSourceDeviceProperty(name="ct2off", type=str,
                  initial=Sample(timestamp=0, unit="", value="O"),
                  perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                  options=DPROP_OPT_AUTOTIMESTAMP,
                  set_cb=lambda x: self.update("ct2off", x)),
            
            ChannelSourceDeviceProperty(name="t", type=str,
                  initial=Sample(timestamp=0, unit="", value="O"),
                  perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                  options=DPROP_OPT_AUTOTIMESTAMP,
                  set_cb=lambda x: self.update("t", x)),
            
            ChannelSourceDeviceProperty(name="d", type=str,
                  initial=Sample(timestamp=0, unit="", value="O"),
                  perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                  options=DPROP_OPT_AUTOTIMESTAMP,
                  set_cb=lambda x: self.update("d", x)),
            
            
            
            
            
            
            ChannelSourceDeviceProperty(name="serialReceive", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            
            ChannelSourceDeviceProperty(name="serialSend", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=self.serial_send),
            
            ChannelSourceDeviceProperty(name="current_temp", type=float,
                initial=Sample(timestamp=0, unit="F", value=0.0),
                perms_mask=(DPROP_PERM_GET),
                options=DPROP_OPT_AUTOTIMESTAMP),
            
            
            ChannelSourceDeviceProperty(name="splt", type=str,
                  initial=Sample(timestamp=0, unit="", value="65"),
                  perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                  options=DPROP_OPT_AUTOTIMESTAMP,
                  set_cb=lambda x: self.update("splt", x)),
            
            
            ChannelSourceDeviceProperty(name="mode", type=str,
                  initial=Sample(timestamp=0, unit="", value="O"),
                  perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                  options=DPROP_OPT_AUTOTIMESTAMP,
                  set_cb=lambda x: self.update("mode", x)),
            
            
            ChannelSourceDeviceProperty(name="cot", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_bool("cot", x)),
            
            
            ChannelSourceDeviceProperty(name="hp", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_bool("hp", x)),
            
            ChannelSourceDeviceProperty(name="tfoh", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_bool("tfoh", x)),
            
            ChannelSourceDeviceProperty(name="essh", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_bool("essh", x)),
            
            ChannelSourceDeviceProperty(name="eahp", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_bool("eahp", x)),
            
            ChannelSourceDeviceProperty(name="essc", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_bool("essc", x)),
            
            ChannelSourceDeviceProperty(name="tsm", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_bool("tsm", x)),
            
            
            ChannelSourceDeviceProperty(name="fan", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_bool("fan", x)),
            
            ChannelSourceDeviceProperty(name="ac_1", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),                
                options=DPROP_OPT_AUTOTIMESTAMP),
            
            ChannelSourceDeviceProperty(name="ac_2", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP),
            
            ChannelSourceDeviceProperty(name="heat_1", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP),
            
            ChannelSourceDeviceProperty(name="heat_2", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP),
            
            ChannelSourceDeviceProperty(name="heat_3", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP),
            
            
            
            
            
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

    

     
    def update(self, register_name, val):
        
        
        self.property_set(register_name, val)   
        print register_name 
        
        
        val = self.property_get(register_name).value
        
        
        
        
        if register_name == "current_temp":
            register_name = "ct"
        if register_name == "mode":
            register_name = "tm"
        if register_name == "splt":
            register_name = "spt"
            
        register_name = register_name.replace("_", "")
        
        
        data = register_name + "=" + str(val)
        
        try:
            self.serial_send(data)
        except:
            print "error sending request to thermostat"
    
    
    def update_bool(self, register_name, val):

        
        self.property_set(register_name, val)   
        print register_name 
        
        
        val = self.property_get(register_name).value
        
        if register_name == "fan":
            register_name = "fm"
        
        if val:
            data = "=1"
        else:
            data = "=0"
            
        
        data = register_name + data
        
        try:
            self.serial_send(data)
        except:
            print "error sending request to thermostat"
            
     
    
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
   #     msg.replace('$', '')
        msg = msg.strip()
        print msg
        try:
            if not msg:
               # print "not message"
                return {}
            
            ret = {}
            split_msg = msg.split(",") #tokenize
            
            for i in split_msg:
                i = i.split("=")
                ret[i[0]] = i[1]
              

          #  print "returning"
          #  print ret
            return ret

        except:
            print "Error parsing return message: " + repr(msg)
            return {}

    

  


    def _config_done_cb(self):
        """ Indicates config is done. """
        print self.__name + " is done configuring, starting polling"
        self.test = 0
        
        time.sleep(15)
        try:
            self.serial_send(R=2)
        except:
            print "error sending request to thermostat"
   
        

    
            
    
    def serial_read(self, buf):
        
    #    print "XBeeSerialTerminal: Read Data: %s" % (buf)
     
        buf = str(buf)
        print "string"
        print self.string
		
        
        buf = buf.strip()
        
        
        if not buf.endswith("$"):
            self.string = self.string + buf
          #  print "part added and now looks like this:"
          #  print self.string
		
        
        if buf.endswith("$"):
            self.string = self.string + buf
            self.string = self.string[:-1]
          #  print "string without %"
          #  print self.string
            d1 = self._parse_return_message(self.string)
            self.string = ""
            
            testing = self.test
            
                
            if testing == 0:
                self.d3 = self._parse_return_message("D=1901/01/01,T=00:15:53,V=041,TM=H,F=1,AC1=0,AC2=0,H1=1,H2=0,H3=0,CT=074,SPT=080,TSM=0,FM=0,COT=0,HP=0,TFOH=1,ESSH=0,EAHP=0,ESSC=0,CD1ON=1,CD1OFF=0,CD2ON=4,CD2OFF=0,HD1ON=1,HD1OFF=0,HD2ON=4,HD2OFF=0,HD3ON=6,HD3OFF=0,MONT=6,MOFFT=6,CS=J,CT1ON=0,CT1OFF=0,CT2ON=0,CT2OFF=0,HT1ON=160,HT1OFF=0,HT2ON=160,HT2OFF=0,HT3ON=160,HT3OFF=0,OUTPUT=0x11")
                
            
            
            
     
	        
            
            if d1.has_key("CD1ON"):
                if (d1["CD1ON"]) != (self.d3["CD1ON"]) or testing < 10: 
                    self.property_set("cd1_on",
                                    Sample(0, value=str(d1["CD1ON"]), unit="aF"))
            
            if d1.has_key("CD1OFF"):
                if (d1["CD1OFF"]) != (self.d3["CD1OFF"]) or testing < 10: 
                    self.property_set("cd1_off",
                                    Sample(0, value=str(d1["CD1OFF"]), unit="aF"))
            
            
            if d1.has_key("CD2ON"):
                if (d1["CD2ON"]) != (self.d3["CD2ON"]) or testing < 10: 
                    self.property_set("cd2_on",
                                    Sample(0, value=str(d1["CD2ON"]), unit="aF"))
            
            
            if d1.has_key("CD2OFF"):
                if (d1["CD2OFF"]) != (self.d3["CD2OFF"]) or testing < 10: 
                    self.property_set("cd2_off",
                                    Sample(0, value=str(d1["CD2OFF"]), unit="aF"))
            
            
            if d1.has_key("HD3ON"):
                if (d1["HD3ON"]) != (self.d3["HD3ON"]) or testing < 10: 
                    self.property_set("hd3_on",
                                    Sample(0, value=str(d1["HD3ON"]), unit="aF"))
            
            if d1.has_key("HD3OFF"):
                if (d1["HD3OFF"]) != (self.d3["HD3OFF"]) or testing < 10: 
                    self.property_set("hd3_off",
                                    Sample(0, value=str(d1["HD3OFF"]), unit="aF"))
            
            if d1.has_key("HD1ON"):
                if (d1["HD1ON"]) != (self.d3["HD1ON"]) or testing < 10: 
                    self.property_set("hd1_on",
                                    Sample(0, value=str(d1["HD1ON"]), unit="aF"))
                       
            
            if d1.has_key("HD1OFF"):
                if (d1["HD1OFF"]) != (self.d3["HD1OFF"]) or testing < 10: 
                    self.property_set("hd1_off",
                                    Sample(0, value=str(d1["HD1OFF"]), unit="aF"))
            
            if d1.has_key("HD2ON"):
                if (d1["HD2ON"]) != (self.d3["HD2ON"]) or testing < 10: 
                    self.property_set("hd2_on",
                                    Sample(0, value=str(d1["HD2ON"]), unit="aF"))
            
            
            if d1.has_key("HD2OFF"):
                if (d1["HD2OFF"]) != (self.d3["HD2OFF"]) or testing < 10: 
                    self.property_set("hd2_off",
                                    Sample(0, value=str(d1["HD2OFF"]), unit="aF"))
            
            
            if d1.has_key("MONT"):
                if (d1["MONT"]) != (self.d3["MONT"]) or testing < 10: 
                    self.property_set("mont",
                                    Sample(0, value=str(d1["MONT"]), unit="aF"))
            
            
            if d1.has_key("HT1ON"):
                if (d1["HT1ON"]) != (self.d3["HT1ON"]) or testing < 10: 
                    self.property_set("ht1on",
                                    Sample(0, value=str(d1["HT1ON"]), unit="aF"))
            
            if d1.has_key("HT1OFF"):
                if (d1["HT1OFF"]) != (self.d3["HT1OFF"]) or testing < 10: 
                    self.property_set("ht1off",
                                    Sample(0, value=str(d1["HT1OFF"]), unit="aF"))
            
            if d1.has_key("HT2ON"):
	            if (d1["HT2ON"]) != (self.d3["HT2ON"]) or testing < 10: 
	                self.property_set("ht2on",
	                                Sample(0, value=str(d1["HT2ON"]), unit="aF"))
            
            
            if d1.has_key("HT2OFF"):
                if (d1["HT2OFF"]) != (self.d3["HT2OFF"]) or testing < 10: 
                    self.property_set("ht2off",
                                    Sample(0, value=str(d1["HT2OFF"]), unit="aF"))
            
            
            if d1.has_key("HT3OFF"):
                if (d1["HT3OFF"]) != (self.d3["HT3OFF"]) or testing < 10: 
                    self.property_set("ht3off",
                                    Sample(0, value=str(d1["HT3OFF"]), unit="aF"))
            
            
            if d1.has_key("HT3ON"):
                if (d1["HT3ON"]) != (self.d3["HT3ON"]) or testing < 10: 
                    self.property_set("ht3on",
                                    Sample(0, value=str(d1["HT3ON"]), unit="aF"))
            
            
            if d1.has_key("CT1ON"):
                if (d1["CT1ON"]) != (self.d3["CT1ON"]) or testing < 10: 
                    self.property_set("ct1on",
                                    Sample(0, value=str(d1["CT1ON"]), unit="aF"))
            
            
            if d1.has_key("CT1OFF"):
                if (d1["CT1OFF"]) != (self.d3["CT1OFF"]) or testing < 10: 
                    self.property_set("ct1off",
                                    Sample(0, value=str(d1["CT1OFF"]), unit="aF"))
            
            if d1.has_key("CT2ON"):
                if (d1["CT2ON"]) != (self.d3["CT2ON"]) or testing < 10: 
                    self.property_set("ct2on",
                                    Sample(0, value=str(d1["CT2ON"]), unit="aF"))
            
            
            
            if d1.has_key("CT2OFF"):
                if (d1["CT2OFF"]) != (self.d3["CT2OFF"]) or testing < 10: 
                    self.property_set("ct2off",
                                    Sample(0, value=str(d1["CT2OFF"]), unit="aF"))
            
            
            
            
            
            if d1.has_key("T"):
                if (d1["T"]) != (self.d3["T"]) or testing < 10: 
                    self.property_set("t",
                                    Sample(0, value=str(d1["T"]), unit="aF"))
            
            if d1.has_key("D"):
                if (d1["D"]) != (self.d3["D"]) or testing < 10: 
                    self.property_set("d",
                                    Sample(0, value=str(d1["D"]), unit="aF"))
            
            
            if d1.has_key("MOFFT"):
                if (d1["MOFFT"]) != (self.d3["MOFFT"]) or testing < 10: 
                    self.property_set("mofft",
                                    Sample(0, value=str(d1["MOFFT"]), unit="aF"))
            
            
            if d1.has_key("CS"):
                if (d1["CS"]) != (self.d3["CS"]) or testing < 10: 
                    self.property_set("cs",
                                    Sample(0, value=str(d1["CS"]), unit="aF"))
            
            
            
            if d1.has_key("CT"):
                if (d1["CT"]) != (self.d3["CT"]) or testing < 10: 
                    self.property_set("current_temp",
                                    Sample(0, value=float(d1["CT"]), unit="aF"))
            
            
            
            if d1.has_key("FM"):
                if (d1["FM"]) != (self.d3["FM"]) or testing < 10:
                        self.property_set("fan", Sample(0, value=Boolean(bool(int(d1["FM"])),
                                        style=STYLE_ONOFF)))
                        
                        
            if d1.has_key("COT"):
                if (d1["COT"]) != (self.d3["COT"]) or testing < 10:
                        self.property_set("cot", Sample(0, value=Boolean(bool(int(d1["COT"])),
                                        style=STYLE_ONOFF)))
                        
                        
            if d1.has_key("TSM"):
                if (d1["TSM"]) != (self.d3["TSM"]) or testing < 10:
                        self.property_set("tsm", Sample(0, value=Boolean(bool(int(d1["TSM"])),
                                        style=STYLE_ONOFF)))
                        
            if d1.has_key("HP"):
                if (d1["HP"]) != (self.d3["HP"]) or testing < 10:
                        self.property_set("hp", Sample(0, value=Boolean(bool(int(d1["HP"])),
                                        style=STYLE_ONOFF)))
                        
                        
            if d1.has_key("TFOH"):
                if (d1["TFOH"]) != (self.d3["TFOH"]) or testing < 10:
                        self.property_set("tfoh", Sample(0, value=Boolean(bool(int(d1["TFOH"])),
                                        style=STYLE_ONOFF)))
            
            
            if d1.has_key("ESSH"):
                if (d1["ESSH"]) != (self.d3["ESSH"]) or testing < 10:
                        self.property_set("essh", Sample(0, value=Boolean(bool(int(d1["ESSH"])),
                                        style=STYLE_ONOFF)))
                        
            if d1.has_key("EAHP"):
                if (d1["EAHP"]) != (self.d3["EAHP"]) or testing < 10:
                        self.property_set("eahp", Sample(0, value=Boolean(bool(int(d1["EAHP"])),
                                        style=STYLE_ONOFF)))
                        
                        
            if d1.has_key("ESSC"):
                if (d1["ESSC"]) != (self.d3["ESSC"]) or testing < 10:
                        self.property_set("essc", Sample(0, value=Boolean(bool(int(d1["ESSC"])),
                                        style=STYLE_ONOFF)))
                        
            
            if d1.has_key("TM"):
                if (d1["TM"]) != (self.d3["TM"]) or testing < 10: 
                    self.property_set("mode",
                                    Sample(0, value=str(d1["TM"]), unit="aF"))
                    
            if d1.has_key("SPT"):
                if (d1["SPT"]) != (self.d3["SPT"]) or testing < 10: 
                    self.property_set("splt",
                                    Sample(0, value=str(d1["SPT"]), unit="aF"))
                    
           	                    
	        
            
            if d1.has_key("AC1"):
                if (d1["AC1"]) != (self.d3["AC1"]) or testing < 10:
                        self.property_set("ac_1", Sample(0, value=Boolean(bool(int(d1["AC1"])),
                                        style=STYLE_ONOFF)))
                        
            if d1.has_key("AC2"):
                if (d1["AC2"]) != (self.d3["AC2"]) or testing < 10:
                        self.property_set("ac_2", Sample(0, value=Boolean(bool(int(d1["AC2"])),
                                        style=STYLE_ONOFF)))
                        
            if d1.has_key("H1"):
                if (d1["H1"]) != (self.d3["H1"]) or testing < 10:
                        self.property_set("heat_1", Sample(0, value=Boolean(bool(int(d1["H1"])),
                                        style=STYLE_ONOFF)))
            
            
            if d1.has_key("H2"):
                if (d1["H2"]) != (self.d3["H2"]) or testing < 10:
                        self.property_set("heat_2", Sample(0, value=Boolean(bool(int(d1["H2"])),
                                        style=STYLE_ONOFF)))
                        
            if d1.has_key("H3"):
                if (d1["H3"]) != (self.d3["H3"]) or testing < 10:
                        self.property_set("heat_3", Sample(0, value=Boolean(bool(int(d1["H3"])),
                                        style=STYLE_ONOFF)))
                        
            if d1.has_key("ESSC"):
                if (d1["ESSC"]) != (self.d3["ESSC"]) or testing < 10:
                        self.property_set("essc", Sample(0, value=Boolean(bool(int(d1["ESSC"])),
                                        style=STYLE_ONOFF)))


	        
            
            self.d3 = dict(self.d3.items() + d1.items())
            
            if testing < 10:
	        	testing += 1
	        	self.test = testing
	            
	        
	        
            
            

    def serial_write(self, data):
        print "XBeeSerialTerminal: Write Data: %s" % (data.value)
        #buf = data.value + chr(0x0D)
        buf = data.value
        try:
            ret = self.write(buf + "\r")
            print "part 2"
            ret = self.write(buf + chr(0x0D))
            if ret == False:
                raise Exception, "write failed"
        except:
            print "XBeeSerialTerminal: Error writing data: %s" % (buf)
    
    def serial_send(self, data):
        print "XBeeSerialTerminal: Write Data: %s" % (data)

        try:
            ret = self.write(data + chr(13))
            if ret == False:
                raise Exception, "write failed"
        except:
            print "XBeeSerialTerminal: Error writing data: %s" % (buf)

# internal functions & classes

