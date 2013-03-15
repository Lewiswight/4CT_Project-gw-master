

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
        self.local = 0
        self.hour_timer = 0
        self.source2 = None 
        self.source1 = None
        self.ud_once = 0
        self.sched = 0
        self.w_retry = 0
        self.timer_c = 0
        self.main_addr = "main_" + gw_extended_address()
        self.last_temp = 0
        


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
            
           
            
            ChannelSourceDeviceProperty(name="ST", type=str,
                initial=Sample(timestamp=0, unit="R,W,I", value="0"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP),
            
            ChannelSourceDeviceProperty(name="med", type=str,
                initial=Sample(timestamp=0, unit="med", value="0"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP),
            
            ChannelSourceDeviceProperty(name="w_t", type=str,
                initial=Sample(timestamp=0, unit="degF", value="60"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP),
            
            ChannelSourceDeviceProperty(name="w_h", type=str,
                initial=Sample(timestamp=0, unit="percent", value="O"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP),
            
          
            
            ChannelSourceDeviceProperty(name="sch", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_name("sch", x)),
            
            ChannelSourceDeviceProperty(name="err", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_name("err", x)),
            
            ChannelSourceDeviceProperty(name="hour", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_hour("hour", x)),
            
            
            
            ChannelSourceDeviceProperty(name="heat_4", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP),
            
            ChannelSourceDeviceProperty(name="heat_5", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP),
            
            ChannelSourceDeviceProperty(name="heat_7", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP),
                   
            ChannelSourceDeviceProperty(name="heat_6", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP),
            
            
            
            
           
            
            
            # setable channesls
            
            
            
            ChannelSourceDeviceProperty(name="f_count", type=int,
                initial=Sample(timestamp=0, unit="failed", value=0),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.send_failed("f_count", x)),
            
            ChannelSourceDeviceProperty(name="hd1_on1", type=str,
                initial=Sample(timestamp=0, unit="degF", value="4"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_name("hd1_on1", x)),
            
            ChannelSourceDeviceProperty(name="hd1_off1", type=str,
                initial=Sample(timestamp=0, unit="degF", value="4"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_name("hd1_off1", x)),
            
            ChannelSourceDeviceProperty(name="ot_on1", type=str,
                initial=Sample(timestamp=0, unit="degF", value="0"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_name("ot_on1", x)),
            
            ChannelSourceDeviceProperty(name="mode1", type=str,
                initial=Sample(timestamp=0, unit="o/h/c/a", value="O"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_name("mode1", x)),
                      
            ChannelSourceDeviceProperty(name="dev_h1", type=str,
                initial=Sample(timestamp=0, unit="dev", value="3"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_name("dev_h1", x)),
            
            ChannelSourceDeviceProperty(name="dev_l1", type=str,
                initial=Sample(timestamp=0, unit="dev", value="3"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_name("dev_l1", x)),         
                   
            ChannelSourceDeviceProperty(name="splt1", type=str,
                initial=Sample(timestamp=0, unit="degF", value="65"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_name("splt1", x)),
            
            ChannelSourceDeviceProperty(name="hd1_on2", type=str,
                initial=Sample(timestamp=0, unit="degF", value="4"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_name("hd1_on2", x)),
            
            ChannelSourceDeviceProperty(name="hd1_off2", type=str,
                initial=Sample(timestamp=0, unit="degF", value="4"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_name("hd1_off2", x)),
            
            ChannelSourceDeviceProperty(name="ot_on2", type=str,
                initial=Sample(timestamp=0, unit="degF", value="0"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_name("ot_on2", x)),
            
            ChannelSourceDeviceProperty(name="mode2", type=str,
                initial=Sample(timestamp=0, unit="o/h/c/a", value="O"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_name("mode2", x)),
                      
            ChannelSourceDeviceProperty(name="dev_h2", type=str,
                initial=Sample(timestamp=0, unit="dev", value="3"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_name("dev_h2", x)),
            
            ChannelSourceDeviceProperty(name="dev_l2", type=str,
                initial=Sample(timestamp=0, unit="dev", value="3"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_name("dev_l2", x)),         
                   
            ChannelSourceDeviceProperty(name="splt2", type=str,
                initial=Sample(timestamp=0, unit="degF", value="65"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_name("splt2", x)),
            
            
            ChannelSourceDeviceProperty(name="ot_on", type=str,
                initial=Sample(timestamp=0, unit="degF", value="0"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_name("ot_on", x)),
            
            
            ChannelSourceDeviceProperty(name="dev_h", type=str,
                initial=Sample(timestamp=0, unit="dev", value="3"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_name("dev_h", x)),
            
            ChannelSourceDeviceProperty(name="dev_l", type=str,
                initial=Sample(timestamp=0, unit="dev", value="3"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_name("dev_l", x)),         
                   
            
            ChannelSourceDeviceProperty(name="zip", type=str,
                initial=Sample(timestamp=0, unit="zip", value="10001"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_name("zip", x)),
            
            
            
            
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
                initial=Sample(timestamp=0, unit="degF", value=0),
                perms_mask=(DPROP_PERM_GET),
                options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name="spt", type=int,
                initial=Sample(timestamp=0, unit="fF", value=75),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_sp(x.value)),
            ChannelSourceDeviceProperty(name="spht", type=int,
                initial=Sample(timestamp=0, unit="fF", value=80),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_sph(x.value)),
            ChannelSourceDeviceProperty(name="splt", type=int,
                initial=Sample(timestamp=0, unit="fF", value=65),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_spc(x.value)),
            ChannelSourceDeviceProperty(name="mode", type=str,
                initial=Sample(timestamp=0, unit="o/h/c/a", value="Off"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_mode(x.value)),
            ChannelSourceDeviceProperty(name="fan", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(True, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_fan(x.value)),
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
                set_cb=lambda x: self.set_temp(x.value)),
            
            ChannelSourceDeviceProperty(name="outside_temp", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_outside(x.value)),
            
            ChannelSourceDeviceProperty(name="lock", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_lock(x.value)),
            
            ChannelSourceDeviceProperty(name="hd1_off", type=str,
                initial=Sample(timestamp=0, unit="", value="4"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_hd1_off(x.value)),
            
            ChannelSourceDeviceProperty(name="hd1_on", type=str,
                initial=Sample(timestamp=0, unit="", value="4"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_hd1_on(x.value)),
            
            ChannelSourceDeviceProperty(name="mrt", type=str,
                initial=Sample(timestamp=0, unit="", value="4"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_mrt(x.value)),
            
            ChannelSourceDeviceProperty(name="mot", type=str,
                initial=Sample(timestamp=0, unit="", value="4"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_mot(x.value)),
            
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
        
        self.apply_settings()

        self.reset_stored_values()

        self.update()
        
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

      #  self.snd.__upload_data()
        
       
        sch = self.property_get("sch").value
        
        sch = bool(sch)
        
        t = time.time()
     #   print "time function"
     #   print time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))
        hours = time.strftime("%H", time.localtime(t))
        minutes = time.strftime("%M", time.localtime(t))
        hours = int(hours)
        minutes = int(minutes)
        print hours
        print minutes
        
        if hours == 3 and self.sched == 0 and sch:
            print "block one turning on"
         #   try:
            self.schedule_event(1)
            #except:
             #   print "block one failed to set"
        if hours == 9 and self.sched == 0 and sch:
            print "block two turning on"
            #try:
            self.schedule_event(2)           
            #except:
             #   print "block two failed to set"
        
        if hours == 4 and self.sched == 1:
            print "sch restet"
            self.sched = 0
        if hours == 10 and self.sched == 1:
            print "sch restet"
            self.sched = 0
        
        
        #fetch weather data from hl_mail driver and set it to the current driver
        
        w_temp = self.globe_get(self.main_addr + ".w_t")
        w_hum = self.globe_get(self.main_addr + ".w_h")
        
        print "here are the global values I took in"
        print w_temp.value
        print w_hum.value
        
        
        self.property_set("w_t", Sample(w_temp.timestamp, value=str(w_temp.value), unit="dF"))
        self.property_set("w_h", Sample(w_hum.timestamp, value=str(w_hum.value), unit="pH"))
        
        #send the outside temp to the theromstat
        
        try:
            self.set_outside(str(w_temp.value))
        except:
            print "failed to send:"
        
        
        #old block of gets. This needs to be gone through and cleaned up
        
        sp = float(self.property_get("splt").value)
        dev_l = float(self.property_get("dev_l").value)  
        dev_h = float(self.property_get("dev_h").value)
        mode = self.property_get("mode").value
        hd1_off = float(self.property_get("hd1_off").value)
        hd1_on = float(self.property_get("hd1_on").value)
        ot_on = float(self.property_get("ot_on").value)
        
        current_temp = self.property_get("current_temp").value
        
        o_t = self.property_get("w_t").value
        
        
    
        hour_on = self.property_get("hour").value 
        
        # set the thermostat to off mode if too warm outside or heat mode if too cold outside
        # set ot_on to 0 to bypass this setting
        
        if ot_on != 0:
	        if o_t < ot_on and mode != "H":
	            self.set_mode("H")
	        
	        if o_t > ot_on and mode == "H":
	            self.set_mode("O")
	            
        
        # if mode is AUTO (A) then turn heat on for 1 hour. this can be done by turning the 
        #heating set point up really high for an hour then restoring the settings to where they were
        
        
        if mode == "A" and self.hour_timer == 0:
            
            self.hour_timer = 1
            thread.start_new_thread(self.set_hour_1, ())
            
        
            
        
        # get the count of how many times the upload failed
   # Move this to the main driver asap     
  #      fc = self.__core.get_service("fc")
  #      err_count = fc.count
  #      
  #      if err_count > 0:
  #          self.property_set("f_count", Sample(0, err_count, ""))
  #          fc.count = 0
            
        
        
        
        cm = self.__core.get_service("channel_manager")
        cdb = cm.channel_database_get()
        cp = cm.channel_publisher_get()
        
        
        channel_list = cdb.channel_list()

        temps=[]
        list2=[]
        list3=[]
        
        
        for channel_name in channel_list:
            try:
                channel = cdb.channel_get(channel_name) 
                sample1 = channel.get()
                if sample1.unit == "F": 
                    if sample1.timestamp < ( time.time() - 1800 ):
                        chan_name = channel_name[:-11] + "excl"
                        print chan_name
                        self.property_set_globe(chan_name, Sample(0, value=Boolean(bool(1), style=STYLE_ONOFF)))
                    else:
                        temps.append(sample1.value) 
            except:
                pass
        
      #  print temps 
      #  print len(temps) 
          
        if len(temps) > 0:           
            temps.sort() 
           # print temps
            for i in range(len(temps)):
                if temps[i] != 0:
                    list3.append(temps[i])
            temps = list3
            print "list without 0s"
            print temps           
            if temps:
                length = float(len(temps))
                medn = int(round(length / 2)) 
                med = temps[(medn - 1)]                
                for i in range(len(temps)):
                    if temps[i] < (med + dev_h) and temps[i] > (med - dev_l):
                        list2.append(temps[i])
                       # print "included:"
                       # print temps[i]
                                     
                
                average = float(sum(list2)) / len(list2) 
                
# set thermostst current temp here!!!
                self.set_temp(str(average))
                
                self.property_set("current_temp", Sample(0, value=int(average), unit="aF"))
                print "the average is"
                print average
                print "the med is"
                print med
                self.property_set("med", Sample(0, value=str(med), unit="med"))
            else:
                print "lenth of temps is less than 1"
        
        
   
            
         
       
            
                
        
        
    
        
        
        
      
            
        
    

                                                  

       
        
        
        
        
        
        if self.__event_timer2 is not None:
            try:
                self.__xbee_manager.xbee_device_schedule_cancel(
                    self.__event_timer2)
            except:
                pass
            
        self.__event_timer2 = self.__xbee_manager.xbee_device_schedule_after(
                SettingsBase.get_setting(self, "sample_rate_sec"),
                self.update)
    
    
    def set_hour_1(self):
        print "hour thread started"
        self.hour_timer = 1
        
#    I'm sure what this code was for
#        if self.timer_c == 0:
#            thread.start_new_thread(self.timer, ()) 
        
        print "turned heat on, starting timer"
        self.last_temp = self.property_get("spht").value
        self.set_sph(89)
        
        t = 0
        while t < 60:
             mode = self.property_get("mode").value
             if mode != "A":
                 break
             t += 1
             time.sleep(1)
        print "waking up from sleep"
        
        mode = self.property_get("mode").value
        
        if mode == "A":
            self.set_mode("H")
            time.sleep(3)
            self.set_sph(self.last_temp)
            
        self.hour_timer = 0
        
    
    
    def schedule_event(self, event):     
        
        if event == 1:
            try:
                sp = self.property_get("splt1").value
                dev_l = self.property_get("dev_l1").value
                dev_h = self.property_get("dev_h1").value
                mode = self.property_get("mode1").value
                hd1_off = self.property_get("hd1_off1").value
                hd1_on = self.property_get("hd1_on1").value
                ot_on = self.property_get("ot_on1").value
                self.property_set("splt", Sample(0, sp, "schedule"))
                self.set_spc(str(sp))
                self.property_set("dev_l", Sample(0, dev_l, "schedule"))
                self.property_set("dev_h", Sample(0, dev_h, "schedule"))
                self.property_set("mode", Sample(0, mode, "schedule"))
                self.set_mode(str(str(self.modes[mode.title()])))
                self.property_set("hd1_off", Sample(0, hd1_off, "schedule"))
                self.set_hd1_off(hd1_off)
                self.property_set("hd1_on", Sample(0, hd1_on, "schedule"))
                self.set_hd1_on(hd1_on)
                self.property_set("ot_on", Sample(0, ot_on, "schedule"))
                self.sched = 1
                print "done setting block one"
            except:
                 print "failed to set"
        
        
        if event == 2:
            try:
                sp = self.property_get("splt2").value
                dev_l = self.property_get("dev_l2").value
                dev_h = self.property_get("dev_h2").value
                mode = self.property_get("mode2").value
                hd1_off = self.property_get("hd1_off2").value
                hd1_on = self.property_get("hd1_on2").value
                ot_on = self.property_get("ot_on2").value       
                self.property_set("splt", Sample(0, sp, "schedule"))
                self.set_spc(str(sp))
                self.property_set("dev_l", Sample(0, dev_l, "schedule"))
                self.property_set("dev_h", Sample(0, dev_h, "schedule"))
                self.property_set("mode", Sample(0, mode, "schedule"))
                self.set_mode(str(str(self.modes[mode.title()])))
                self.property_set("hd1_off", Sample(0, hd1_off, "schedule"))
                self.set_hd1_off(hd1_off)
                self.property_set("hd1_on", Sample(0, hd1_on, "schedule"))
                self.set_hd1_on(hd1_on)
                self.property_set("ot_on", Sample(0, ot_on, "schedule"))
                self.sched = 1
                print "done setting block two"
            except:
                print"failed setting block 2"
            
        
    
    
    def stop(self):

        # Unregister ourselves with the XBee Device Manager instance:
        self.__xbee_manager.xbee_device_unregister(self)
        

        return True


    ## Locally defined functions:

    def set_temp(self, val):
        
        
        self.property_set("set_current_temp", Sample(0, value=val, unit="dF"))
        
        try:
            self.serial_send("A=1,Z=1,TtTt=" + str(val) + "\x0D")
        except:
            print "error setting thermostat"
        
        
    
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


    
    
    def set_outside(self, val):
        """ set point cool """
        
        self.property_set("outside_temp", Sample(0, value=val, unit="dF"))
        
        try:
            self.serial_send("A=1,Z=1,OT=" + str(val) + "\x0D")
        except:
            print "error setting thermostat"
        

        
    
    
    def set_spc(self, val):
        """ set point cool """
        
        self.property_set("splt", Sample(0, value=val, unit="dF"))
        
        try:
            self.serial_send("A=1,Z=1,SPH=" + str(val) + "\x0D")
        except:
            print "error setting thermostat"
        

        

    def set_sph(self, val):
        """ set point high """
        
        self.property_set("spht", Sample(0, value=val, unit="dF"))
        
        try:
            self.serial_send("A=1,Z=1,SPH=" + str(val) + "\x0D")
        except:
            print "error setting thermostat"
        
        
        
        

    def set_sp(self, val):
        """ Set the set-point temperature """
        
     
        self.property_set("spt", Sample(0, value=val, unit="dF"))
        
        try:
            self.serial_send("A=1,Z=1,SP=" + str(val) + "\x0D")
        except:
        	print "error setting thermostat"

        
        
    
    
    
    
    
    def set_mot(self, val):
       
 #       self.property_set(register_name, val)
        self.property_set("mot", Sample(0, value=val, unit="dF"))
        
        try:
            self.serial_send("A=1,Z=1,SV10=" + str(val) + "\x0D")
        except:
            print "error setting thermostat"
        

        
    
    def set_mrt(self, val):
       
 #       self.property_set(register_name, val)
        self.property_set("mrt", Sample(0, value=val, unit="dF"))
        
        try:
            self.serial_send("A=1,Z=1,SV11=" + str(val) + "\x0D")
        except:
            print "error setting thermostat"
        

        
    
    def set_hd1_off(self, val):
       
 #       self.property_set(register_name, val)
        self.property_set("hd1_off", Sample(0, value=val, unit="dF"))
        
        try:
            self.serial_send("A=1,Z=1,SV13=" + str(val) + "\x0D")
        except:
            print "error setting thermostat"
        

        
    
    def set_hd1_on(self, val):
       
 #       self.property_set(register_name, val)
        self.property_set("hd1_on", Sample(0, value=val, unit="dF"))
        
        try:
            self.serial_send("A=1,Z=1,SV12=" + str(val) + "\x0D")
        except:
            print "error setting thermostat"
        

        
    
    
    def set_lock(self, val):
        
 #       self.property_set(register_name, val)
        self.property_set("lock", Sample(0, value=val, unit="dF"))
        
        try:
            self.serial_send("A=1,Z=1,DL=" + str(val) + "\x0D")
        except:
            print "error setting thermostat"
        

        

    
    def set_mode(self, val):
        """ set system mode.
            where mode is one of [Off, Heat, Cool, Auto]
        """
 #       self.property_set(register_name, val)
        self.property_set("mode", Sample(0, value=val, unit="dF"))
        
        try:
            self.serial_send("A=1,Z=1,M=" + str(self.modes[val.title()]) + "\x0D")
        except:
            print "error setting thermostat"
        

        

    
    
    
    def set_fan(self, val):
        """ Set system fan.
            
            Value can be:
            
            * on
            * off
             
            Setting fan to off will only put the fan in auto mode, there is no
            way to force the fan totally off.  Also, even in auto mode there
            is no way to tell if the fan is actually spinning or not.
        """
        self.property_set("fan", Sample(0, value=val, unit="dF"))
        
        try:
            self.serial_send("A=1,Z=1,F=" + str(val) + "\x0D")
        except:
            print "error setting thermostat"

        


    def _config_done_cb(self):
        """ Indicates config is done. """
        print self.__name + " is done configuring, starting polling"
        self.test = 0
        
       
        
        

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
                                Sample(0, value=int(d1["T"]), unit="dF"))
        if d1.has_key("SP"):
        	if (d1["SP"]) != (self.d3["SP"]) or testing < 10:
                    self.property_set("spt", 
                                Sample(0, value=int(d1["SP"]), unit="dF"))
        if d1.has_key("SPH"):
        	if (d1["SPH"]) != (self.d3["SPH"]) or testing < 10:
                    self.property_set("spht",
                               Sample(0, value=int(d1["SPH"]), unit="dF"))
        if d1.has_key("SPC"):
        	if (d1["SPC"]) != (self.d3["SPC"]) or testing < 10:
                    samp = Sample(0, value=int(d1["SPC"]), unit="dF")
                    self.property_set("splt", samp)
        if d1.has_key("ST"):
            if (d1["ST"]) != (self.d3["ST"]) or testing < 10:
                    self.property_set("ST", \
                    Sample(0, value=d1["ST"], unit="o/h/c/a"))
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

    
    

    
    def update_name(self, register_name, val):
        
    

        
        self.property_set(register_name, val)
        
        
        val = self.property_get(str(register_name)).value      
        val = str(val)
        register_name = str(register_name)
        
                   
   #     if register_name == "zip":
   ##         self.weather()
    #    else:
        
    
    
    
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

