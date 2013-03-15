
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

        ## Channel Properties Definition
        property_list = [
            # gettable properties
            ChannelSourceDeviceProperty(name="serialReceive", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name="serialSend", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=self.serial_send),
            ChannelSourceDeviceProperty(name="current_temp", type=int,
                initial=Sample(timestamp=0, unit="F", value=0),
                perms_mask=(DPROP_PERM_GET),
                options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name="spt", type=int,
                initial=Sample(timestamp=0, unit="F", value=75),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_sp("spt", x)),
            ChannelSourceDeviceProperty(name="spht", type=int,
                initial=Sample(timestamp=0, unit="F", value=80),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_sph("spht", x)),
            ChannelSourceDeviceProperty(name="splt", type=int,
                initial=Sample(timestamp=0, unit="F", value=65),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=self.set_spc),
            ChannelSourceDeviceProperty(name="mode", type=str,
                initial=Sample(timestamp=0, unit="o/h/c/a", value="Off"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=self.set_mode),
            ChannelSourceDeviceProperty(name="fan", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(True, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_fan("fan", x)),
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
            ChannelSourceDeviceProperty(name="set_current_temp", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_temp("set_current_temp", x.value)),
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

    
    def update(self):
        """
            Request the latest data from the device.
        """

        try:
            self.serial_send("A=1,Z=1,R=1 R=2\x0D")
        #    self.serial_send("00!\x0D")
            
          #  self.serial_send("A=1,Z=1,R=2\x0D")
            # We will process receive data when it arrives in the callback
        except:
        	print "error sending request to thermostat"
        
   #     try:    
   #         self.__upload_data()
   #     except:
   #         pass

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
    
    def stop(self):

        # Unregister ourselves with the XBee Device Manager instance:
        self.__xbee_manager.xbee_device_unregister(self)
        

        return True


    ## Locally defined functions:

    def set_temp(self, register_name, val):
        
        
  #      self.property_set(register_name, val)
        print val
        
        self.property_set("set_current_temp", Sample(0, value=val, unit="dF"))
        
        self.serial_send("A=1,Z=1," + str(val) + "\x0D")
        
        
        
    
    def _parse_return_message(self, msg):
        """ Take a status string from thermostat, and
            split it up into a dictionary::
            
                "A" "0" "T=74" -> {'A':0, 'T':74}
            
        """
   #     msg.replace('$', '')
        msg = msg.strip()
        
        try:
            if not msg:
                return {}
            
            ret = {}
            split_msg = msg.split(" ") #tokenize
            
            for i in split_msg:
                i = i.split("=")
                ret[i[0]] = i[1]

            return ret

        except:
            print "Error parsing return message: " + repr(msg)
            return {}

    def set_spc(self, val):
        """ set point cool """
        
        self.property_set("splt", val)
        
        try:
            self.serial_send("A=1,Z=1,SPC=" + str(val.value) + "\x0D")
        except:
        	print "error setting thermostat"

        self.update()

    def set_sph(self, register_name, val):
        """ set point high """
        
        self.property_set(register_name, val)
        
        try:
            self.serial_send("A=1,Z=1,SPH=" + str(val.value) + "\x0D")
        except:
        	print "error setting thermostat"

        self.update()

    def set_sp(self, register_name, val):
        """ Set the set-point temperature """
        
        self.property_set(register_name, val)

        try:
            self.serial_send("A=1,Z=1,SP=" + str(val.value) + "\x0D")
        except:
        	print "error setting thermostat"

        self.update()

    def set_mode(self, val):
        """ set system mode.
            where mode is one of [Off, Heat, Cool, Auto]
        """
 #       self.property_set(register_name, val)
        self.property_set("mode", val)
        
        try:
            self.serial_send("A=1,Z=1,M=" + \
                str(self.modes[val.value.title()]) + "\x0D")
        except:
        	print "error setting thermostat"

        self.update()

    def set_fan(self, register_name, val):
        """ Set system fan.
            
            Value can be:
            
            * on
            * off
             
            Setting fan to off will only put the fan in auto mode, there is no
            way to force the fan totally off.  Also, even in auto mode there
            is no way to tell if the fan is actually spinning or not.
        """
        self.property_set(register_name, val)
        
        try:
            self.serial_send("A=1,Z=1,F=" + str(int(val.value)) + "\x0D")
        except:
        	print "error setting thermostat"

        self.update()


    def _config_done_cb(self):
        """ Indicates config is done. """
        print self.__name + " is done configuring, starting polling"
        self.test = 0
        self.update()
        

    def fan_cycle(self):
    #	self.serial_send("A=1,Z=1,F=1\x0D")
    	time.sleep(60)
    	self.serial_send("A=1,Z=1,F=0\x0D")
    
            
    
    def serial_read(self, buf):
        print "XBeeSerialTerminal: Read Data: %s" % (buf)
     

        d1 = self._parse_return_message(buf)
        
        testing = self.test
        

        
        if testing < 10:
            if d1.has_key("SPC") and d1.has_key("T"):
        	    self.d3 = d1      # d3 is the previous value for d1 
            if d1.has_key("C1A"):
                self.d4 = d1
            
        
            	
        
        if d1.has_key("T"):
            if (d1["T"]) != (self.d3["T"]) or testing < 10: 
                self.property_set("current_temp",
                                Sample(0, value=int(d1["T"]), unit="F"))
        if d1.has_key("SP"):
        	if (d1["SP"]) != (self.d3["SP"]) or testing < 10:
                    self.property_set("spt", 
                                Sample(0, value=int(d1["SP"]), unit="F"))
        if d1.has_key("SPH"):
        	if (d1["SPH"]) != (self.d3["SPH"]) or testing < 10:
                    self.property_set("spht",
                               Sample(0, value=int(d1["SPH"]), unit="F"))
        if d1.has_key("SPC"):
        	if (d1["SPC"]) != (self.d3["SPC"]) or testing < 10:
                    samp = Sample(0, value=int(d1["SPC"]), unit="F")
                    self.property_set("splt", samp)
        if d1.has_key("M"):
        	if (d1["M"]) != (self.d3["M"]) or testing < 10:
                    self.property_set("mode", \
                    Sample(0, value=d1["M"], unit="o/h/c/a"))
        if d1.has_key("FM"):
        	if (d1["FM"]) != (self.d3["FM"]) or testing < 10:
                    self.property_set("fan", Sample(0, value=Boolean(bool(int(d1["FM"])),
            						style=STYLE_ONOFF)))
        
        	            
                        
                    
        if d1.has_key("C2A"):
        	if (d1["C2A"]) != (self.d4["C2A"]) or testing < 10: # or (int(d1["C2A"])) == 1:
                    self.property_set("ac_2", Sample(0, value=Boolean(bool(int(d1["C2A"])),
            							style=STYLE_ONOFF)))
        if d1.has_key("H1A"):
        	if (d1["H1A"]) != (self.d4["H1A"]) or testing < 10: # or (int(d1["H1A"])) == 1:
                    self.property_set("heat_1", Sample(0, value=Boolean(bool(int(d1["H1A"])),
            								style=STYLE_ONOFF)))
        if d1.has_key("H2A"):
        	if (d1["H2A"]) != (self.d4["H2A"]) or testing < 10: # or (int(d1["H2A"])) == 1:
                    self.property_set("heat_2", Sample(0, value=Boolean(bool(int(d1["H2A"])),
            								style=STYLE_ONOFF)))
        if d1.has_key("H3A"):
        	if (d1["H3A"]) != (self.d4["H3A"]) or testing < 10: # or (int(d1["H3A"])) == 1:
                    self.property_set("heat_3", Sample(0, value=Boolean(bool(int(d1["H3A"])),
            								style=STYLE_ONOFF)))
        
        if d1.has_key("C1A"):
        	if (d1["C1A"]) != (self.d4["C1A"]) or testing < 10: # or (int(d1["C1A"])) == 1:
                    self.property_set("ac_1", Sample(0, value=Boolean(bool(int(d1["C1A"])),
            							style=STYLE_ONOFF)))    
                    if (d1["C1A"]) == "1" and  (self.d4["C1A"]) == "0" and testing == 10:
                    	self.serial_send("A=1,Z=1,F=1\x0D")
                    if (d1["C1A"]) == "0" and  (self.d4["C1A"]) == "1" and testing == 10:
                    	thread.start_new_thread(self.fan_cycle, ())
                                                      	            	                    
        
        if testing < 10:
        	testing += 1
        	self.test = testing
            
        
        if d1.has_key("SPC") and d1.has_key("T"):
        	self.d3 = d1
        	
        
        if d1.has_key("C1A"):
            self.d4 = d1

    def serial_write(self, data):
        print "XBeeSerialTerminal: Write Data: %s" % (data.value)
        #buf = data.value + chr(0x0D)
        buf = data.value
        try:
            ret = self.write(buf + chr(13))
            if ret == False:
                raise Exception, "write failed"
        except:
            print "XBeeSerialTerminal: Error writing data: %s" % (buf)
    
    def serial_send(self, data):
        print "XBeeSerialTerminal: Write Data: %s" % (data)
        #buf = data.value + chr(0x0D)
  #      buf = data.value
        try:
            ret = self.write(data)
            if ret == False:
                raise Exception, "write failed"
        except:
            print "XBeeSerialTerminal: Error writing data:" 

# internal functions & classes

