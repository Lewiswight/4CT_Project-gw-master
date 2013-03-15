




from devices.device_base import DeviceBase 
from devices.xbee.xbee_devices.xbee_base import XBeeBase
from settings.settings_base import SettingsBase, Setting
from channels.channel_source_device_property import *
from devices.xbee.xbee_config_blocks.xbee_config_block_ddo \
    import XBeeConfigBlockDDO

from settings.settings_base import SettingsBase, Setting
from common.types.boolean import Boolean, STYLE_ONOFF
from samples.sample import Sample
from common.helpers.format_channels import iso_date
from common.digi_device_info import get_platform_name
from devices.xbee.xbee_device_manager.xbee_device_manager_event_specs \
    import *
import Queue
import thread
import urllib

import sys

import os

import time

# constants

# exception classes

# interface functions

# cla

class TemplateDevice(XBeeBase):
    """
    This class extends one of our base classes and is intended as an
    example of a concrete, example implementation, but it is not itself
    meant to be included as part of our developer API. Please consult the
    base class documentation for the API and the source code for this file
    for an example implementation.

    """

    
    
    def __init__(self, name, core_services):
        self.__name = name
        self.__core = core_services
    #    self.__event_timer = None
        self.__event_timer3 = None
        self.__event_timer4 = None
        self.__xbee_manager = None
        self.local = 0
        self.hour_timer = 0
        self.source2 = None 
        self.source1 = None
        self.ud_once = 0
        self.sched = 0
        self.w_retry = 0
        self.timer_c = 0
        
        

        
       # self.update_timer = None
   #     self.__stopevent = core_services
        

        ## Settings Table Definition:
        settings_list = [
            Setting(
                name='count_init', type=int, required=False, default_value=0,
                  verify_function=lambda x: x >= 0),
            Setting(
                name='xbee_device_manager', type=str, required=False, default_value="xbee_device_manager"),
            Setting(
                name='pin3_source', type=str, required=False,
                default_value=''),
            Setting(
                name='pin4_source', type=str, required=False,
                default_value=''),
            Setting(
                name='extended_address', type=str, required=False, default_value="00:00:a2:00:40:33:9b:f3!"),
            Setting(
                name='sample_rate_sec_w', type=int, required=False,
                default_value=600,
                verify_function=lambda x: x >= 1 and x < 0xffff),
            Setting(
                name='sample_rate_sec', type=int, required=False,
                default_value=30,
                verify_function=lambda x: x >= 1 and x < 0xffff),
            Setting(
                name='update_rate', type=float, required=False, default_value=10,
                  verify_function=lambda x: x > 0.0),
        ]

        ## Channel Properties Definition:
        property_list = [
            # gettable properties
            
            #driving io pins on DIO
            ChannelSourceDeviceProperty(name="heat_off", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
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
            
            #driving io pins on DIO
            ChannelSourceDeviceProperty(name="heat_on", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
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
            
            ChannelSourceDeviceProperty(name="pin_2", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_pin_2("pin_2", x)),
            
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
            
            ChannelSourceDeviceProperty(name="heat_1", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP),
            
            ChannelSourceDeviceProperty(name="ac_1", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),                
                options=DPROP_OPT_AUTOTIMESTAMP),
                      
            ChannelSourceDeviceProperty(name="current_temp", type=str,
                initial=Sample(timestamp=0, unit="apyF", value="0"),
                perms_mask=(DPROP_PERM_GET),
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
            
            ChannelSourceDeviceProperty(name="hd1_on", type=str,
                initial=Sample(timestamp=0, unit="degF", value="4"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_name("hd1_on", x)),
            
            ChannelSourceDeviceProperty(name="hd1_off", type=str,
                initial=Sample(timestamp=0, unit="degF", value="4"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_name("hd1_off", x)),
            
            ChannelSourceDeviceProperty(name="ot_on", type=str,
                initial=Sample(timestamp=0, unit="degF", value="0"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_name("ot_on", x)),
            
            ChannelSourceDeviceProperty(name="mode", type=str,
                initial=Sample(timestamp=0, unit="o/h/c/a", value="O"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_name("mode", x)),
                      
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
                   
            ChannelSourceDeviceProperty(name="splt", type=str,
                initial=Sample(timestamp=0, unit="degF", value="65"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_name("splt", x)),          
                     
            ChannelSourceDeviceProperty(name="zip", type=str,
                initial=Sample(timestamp=0, unit="zip", value="10001"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.update_name("zip", x)),          


        ]
                                            
        ## Initialize the XBeeBase interface:
        XBeeBase.__init__(self, self.__name, self.__core,
                                settings_list, property_list)
  
        self.start()

    def apply_settings(self):

        print "apply settings"
        SettingsBase.merge_settings(self)
        accepted, rejected, not_found = SettingsBase.verify_settings(self)

        if len(rejected) or len(not_found):
            # there were problems with settings, terminate early:
            return (accepted, rejected, not_found)

        SettingsBase.commit_settings(self, accepted)

        return (accepted, rejected, not_found)

    def run(self):
        print "hello"
    
    def get_settings(self):
        
        file = open("WEB/python/datafile.txt", "r")
        f = file.readlines()
        for i in range(len(f)):
            print f[i]  
            j = f[i].split("=")
            if str(j[0].strip()) == "mode" or str(j[0].strip()) == "zip" or str(j[0].strip()) == "mode1" or str(j[0].strip()) == "mode2":
                name1 = str(j[0].strip())
                val1 = str(j[1].strip())
                self.property_set(name1, Sample(0, val1, "restart"))
               # self.property_set(name1, val1)
                print "set from backup (mode):"
                print j[0]
            elif str(j[0].strip()) == "sch":
                name1 = str(j[0].strip())
                val1 = j[1].strip()
                if val1 == "True" or val1 == "On" or val1 == "on" or val1 == "true":
                	val1 = True
                if val1 == "False" or val1 == "Off" or val1 == "off" or val1 == "false":
                	val1 = False    
                self.property_set("sch", Sample(0, value=Boolean(bool(val1), style=STYLE_ONOFF)))
                print "set from backup (sch):"
                print val1
                print bool(val1)
                print j[0]             
            else:
                name1 = str(j[0].strip())
                val1 = str(j[1].strip())
                self.property_set(name1, Sample(0, val1, "restart"))
                print "set from backup:"
                print j[0]
            #print "unknown or failed setting on startup"
            #print j[0]
        # 
    
    
    def start(self):
    	
    	xbee_manager_name = SettingsBase.get_setting(self, "xbee_device_manager")
        dm = self.__core.get_service("device_driver_manager")
        self.__xbee_manager = dm.instance_get(xbee_manager_name)

        print "start"
        
        
 
        self.weather()
        self.update()
        
        
        
        
 
        
        return True

    
    

    
    def stop(self):

        self.__stopevent.set()
        
        return True
        

    
    def update_list(self, register_name, val):
        
        
        dict = {}
        file = open("WEB/python/datafile.txt", "r")
        f = file.readlines()
        for i in range(len(f)):
          #  print f[i]  
            j = f[i].split("=")
            dict[j[0]] = j[1].strip()
        file.close()
              
        
        dict[register_name] = val
        output = []
        keys = dict.keys() 
        i = 0
        
        for key in keys:
            output.append(keys[i] + "=" + dict[key])
            i += 1   
    
        file2 = open("WEB/python/datafile.txt", "w")
        
        for i in range(len(output)):
            file2.writelines(output[i] + "\n")
        file2.close()
    
        
    def send_failed(self, register_name, val):
        
        
        self.property_set(register_name, val)
    
    def update_name(self, register_name, val):
        
    

        
        self.property_set(register_name, val)
        
        
        val = self.property_get(str(register_name)).value      
        val = str(val)
        register_name = str(register_name)
        
        self.update_list(register_name, val)
              
    	if register_name == "zip":
            self.weather()
        else:
            self.update()
            
   #     self.snd.upload_data()
    
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
                self.property_set("dev_l", Sample(0, dev_l, "schedule"))
                self.property_set("dev_h", Sample(0, dev_h, "schedule"))
                self.property_set("mode", Sample(0, mode, "schedule"))
                self.property_set("hd1_off", Sample(0, hd1_off, "schedule"))
                self.property_set("hd1_on", Sample(0, hd1_on, "schedule"))
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
                self.property_set("dev_l", Sample(0, dev_l, "schedule"))
                self.property_set("dev_h", Sample(0, dev_h, "schedule"))
                self.property_set("mode", Sample(0, mode, "schedule"))
                self.property_set("hd1_off", Sample(0, hd1_off, "schedule"))
                self.property_set("hd1_on", Sample(0, hd1_on, "schedule"))
                self.property_set("ot_on", Sample(0, ot_on, "schedule"))
                self.sched = 1
                print "done setting block two"
            except:
            	print"pailed setting block 2"
            
        
            
            
    
    def update(self):
    	
    	if self.__event_timer3 is not None:
            try:
                self.__xbee_manager.xbee_device_schedule_cancel(
                    self.__event_timer3)
            except:
                pass
            
        self.__event_timer3 = self.__xbee_manager.xbee_device_schedule_after(
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
        
        

        
        sp = float(self.property_get("splt").value)
        dev_l = float(self.property_get("dev_l").value)  
        dev_h = float(self.property_get("dev_h").value)
        mode = self.property_get("mode").value
        hd1_off = float(self.property_get("hd1_off").value)
        hd1_on = float(self.property_get("hd1_on").value)
        ot_on = float(self.property_get("ot_on").value)
        
        current_temp = self.property_get("current_temp").value
        
        o_t = self.property_get("w_t").value
        
        
        heat = self.property_get("heat_on").value
        user_heat = self.property_get("heat_5").value   
        hour_on = self.property_get("hour").value 
        heat_1 = self.property_get("heat_1").value
        heat_4 = self.property_get("heat_4").value
        heat_5 = self.property_get("heat_5").value
        heat_7 = self.property_get("heat_7").value
        heat_6 = self.property_get("heat_6").value  

        
        # get the count of how many times the upload failed
        
        fc = self.__core.get_service("fc")
        err_count = fc.count
        
        if err_count > 0:
            self.property_set("f_count", Sample(0, err_count, ""))
            fc.count = 0
            
        
        
        
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
                self.property_set("current_temp", Sample(0, value=str(average), unit="aF"))
                print "the average is"
                print average
                print "the med is"
                print med
                self.property_set("med", Sample(0, value=str(med), unit="med"))
            else:
                print "lenth of temps is less than 1"
        
        
   
        	
         
        
        
        if mode == "O":
            if heat or heat_6:
                self.property_set("heat_6", Sample(0, value=Boolean(bool(0), style=STYLE_ONOFF)))
                self.property_set("heat_on", Sample(0, value=Boolean(bool(0), style=STYLE_ONOFF)))
            if hour_on:
                self.property_set("hour", Sample(0, value=Boolean(bool(0), style=STYLE_ONOFF)))
                
                         
        
        
        if not hour_on:
            
            if user_heat and not heat and mode == "H":
                self.property_set("heat_on", Sample(0, value=Boolean(bool(1), style=STYLE_ONOFF)))
                self.local = 1
                
            
            if not user_heat and self.local == 1:
                self.property_set("heat_on", Sample(0, value=Boolean(bool(0), style=STYLE_ONOFF)))
                self.local = 0
                    
            
            if not user_heat:
            
     
                
                
                
                
                if mode == "H" and ot_on == 0:
                    if float(current_temp) > 1:
                        if not heat:
                            if float(current_temp) < (float(sp) - float(hd1_on)):
                                self.property_set("heat_6", Sample(0, value=Boolean(bool(1), style=STYLE_ONOFF)))
          
                                self.property_set("heat_on", Sample(0, value=Boolean(bool(1), style=STYLE_ONOFF)))  
                                if self.timer_c == 0:
                                	thread.start_new_thread(self.timer, ())     	
                        if heat:
                            if float(current_temp) > (float(sp) + float(hd1_off)):
                                self.property_set("heat_6", Sample(0, value=Boolean(bool(0), style=STYLE_ONOFF)))
                                self.property_set("heat_on", Sample(0, value=Boolean(bool(0), style=STYLE_ONOFF)))
                                
                
                if float(current_temp) > 1 and int(o_t) < ot_on:
                    if mode == "H" and not heat:
                        if float(current_temp) < (float(sp) - float(hd1_on)):
                            self.property_set("heat_6", Sample(0, value=Boolean(bool(1), style=STYLE_ONOFF)))
                    
                            self.property_set("heat_on", Sample(0, value=Boolean(bool(1), style=STYLE_ONOFF)))
                            if self.timer_c == 0:
                                	thread.start_new_thread(self.timer, ())               
                    if mode == "H" and heat:
                        if float(current_temp) > (float(sp) + float(hd1_off)):
                            self.property_set("heat_6", Sample(0, value=Boolean(bool(0), style=STYLE_ONOFF)))
                            self.property_set("heat_on", Sample(0, value=Boolean(bool(0), style=STYLE_ONOFF)))
                
                if ot_on != 0:
                    if int(o_t) > ot_on:
                        self.property_set("heat_6", Sample(0, value=Boolean(bool(0), style=STYLE_ONOFF)))
                        self.property_set("heat_on", Sample(0, value=Boolean(bool(0), style=STYLE_ONOFF)))
                        
                
            
            
                
        
        
    
        
        
        
        if (self.source1 == None) or (self.source2 == None):
            for channel_name in channel_list:
                try:
                    channel = cdb.channel_get(channel_name) 
                    sample = channel.get()
                    if sample.unit == "s1": 
                        self.source1 = channel_name
                    if sample.unit =="s2":
                        self.source2 = channel_name
                except:
                    pass
            
            
        
    #    source2 = SettingsBase.get_setting(self, 'pin4_source') 
                                                  
        print self.source1
        print self.source2
            
        if( self.source2 != None):
            source_chan = cdb.channel_get(self.source2)
            pin4 = source_chan.get().value
            pin4 = bool(pin4)
            print "pin 4 is:"
            print pin4
            if self.ud_once == 0:
                self.ud_once = 1
                try:
                    self.get_settings()
                except:
                    print"unable to load settings from last startup"

                                                  
        
        if( self.source1 != None):
            source_chan = cdb.channel_get(self.source1)
            pin3 = source_chan.get().value
            pin3 = bool(pin3)
            print "pin 3 is:"
            print pin3

         
        if (self.source1 != None):   
                # SET UP TO TURN ON  HEAT 1 / THERMOSTAT HEAT
            if pin3 and heat:
                if not pin4 and not hour_on and not heat_1:
                    self.property_set("heat_1", Sample(0, value=Boolean(bool(1), style=STYLE_ONOFF)))
           
              # SET UP TO TURN Off HEAT 1 / THERMOSTAT HEAT      
            if heat_1:
                if not pin3:
                    self.property_set("heat_1", Sample(0, value=Boolean(bool(0), style=STYLE_ONOFF)))
           
             # SET UP TO TURN ON  HEAT 4 / DOMESTIC HOT WATER       
            if pin3:
                if not heat and not pin4 and not hour_on and not heat_4:
                    self.property_set("heat_4", Sample(0, value=Boolean(bool(1), style=STYLE_ONOFF)))
                    
            # SET UP TO TURN OFF  HEAT 4 / HOT WATER
            
            if heat_4:
                if heat or pin4 or hour_on or not pin3:
                    self.property_set("heat_4", Sample(0, value=Boolean(bool(0), style=STYLE_ONOFF)))
                    
                    
            # SET UP TO TURN ON  HEAT 5 / Local 1 Hour
            
            if pin4:
                self.property_set("heat_5", Sample(0, value=Boolean(bool(1), style=STYLE_ONOFF)))
                self.property_set("heat_1", Sample(0, value=Boolean(bool(0), style=STYLE_ONOFF)))
                self.property_set("heat_4", Sample(0, value=Boolean(bool(0), style=STYLE_ONOFF)))
                self.property_set("hour", Sample(0, value=Boolean(bool(0), style=STYLE_ONOFF)))
                
            # TURN OFF HEAT 5 / LOCAL 1 HOUR
            if heat_5 and not pin4:
                self.property_set("heat_5", Sample(0, value=Boolean(bool(0), style=STYLE_ONOFF)))
                
            self.property_set("heat_7", Sample(0, value=Boolean(pin3, style=STYLE_ONOFF)))
                
            
                
            
                
        if self.__event_timer3 is not None:
            try:
                self.__xbee_manager.xbee_device_schedule_cancel(
                    self.__event_timer3)
            except:
                pass
            
        self.__event_timer3 = self.__xbee_manager.xbee_device_schedule_after(
                SettingsBase.get_setting(self, "sample_rate_sec"),
                self.update)         
                
        
        
                
        
                
                
        
    
     


    def set_pin_2(self, register_name, val):
        
        thread.start_new_thread(self.pin_2p, ())
    
      
        
    def timer(self):
        self.timer_c = 1
        t = 0
        while t < 240:
            t += 1
            time.sleep(1) 
        
        heat = self.property_get("heat_on").value
        heat_7 = self.property_get("heat_7").value
        mode = self.property_get("mode").value
        
        if heat and mode == "H" and not heat_7:
            self.property_set("err", Sample(0, value=Boolean(bool(1), style=STYLE_ONOFF)))
        else:
            self.property_set("err", Sample(0, value=Boolean(bool(0), style=STYLE_ONOFF)))
            
        self.timer_c = 0
            
                
        
    
    def pin_2p(self):
        self.property_set("heat_off", Sample(0, value=Boolean(bool(1), style=STYLE_ONOFF)))
        time.sleep(15)
        self.property_set("heat_off", Sample(0, value=Boolean(bool(0), style=STYLE_ONOFF)))
        self.property_set("pin_2", Sample(0, value=Boolean(bool(0), style=STYLE_ONOFF)))
    
    def update_heat5(self, pin4):
        
        new_val = bool(pin4)

        self.property_set("heat_5", Sample(0, value=Boolean(new_val, style=STYLE_ONOFF)))
    
    
    def update_heat1(self, pin3):
        
        
        new_val = bool(pin3)
        
        self.property_set("heat_1", Sample(0, value=Boolean(new_val, style=STYLE_ONOFF)))
        
      
    
    def set_hour(self, register_name, val):
        
        
        self.property_set(register_name, val)
        mode = self.property_get("mode").value 
        
        if mode == "O":
            self.property_set("hour", Sample(0, value=Boolean(bool(0), style=STYLE_ONOFF)))
        
   #     self.snd.upload_data()
        
        if val and self.hour_timer == 0 and mode == "H":             
            print "starting hour thread"
            thread.start_new_thread(self.set_hour_1, ())
        
    def set_hour_1(self):
        print "hour thread started"
        self.hour_timer = 1
        
        self.property_set("heat_on", Sample(0, value=Boolean(bool(1), style=STYLE_ONOFF)))
        self.property_set("heat_1", Sample(0, value=Boolean(bool(0), style=STYLE_ONOFF)))
        self.property_set("heat_4", Sample(0, value=Boolean(bool(0), style=STYLE_ONOFF)))
        self.property_set("heat_5", Sample(0, value=Boolean(bool(0), style=STYLE_ONOFF)))
        
        if self.timer_c == 0:
        	thread.start_new_thread(self.timer, ()) 
        
        print "turned heat on, starting timer"
        on = self.property_get("hour").value
        t = 0
        while on and t < 3600:
             on = self.property_get("hour").value
             t += 1
             time.sleep(1)
        print "waking up from sleep"
        
        self.hour_timer = 0
        
         
        
        if on:
            print "timer was not turned off during hour, will now turn heat off"
            self.property_set("heat_on", Sample(0, value=Boolean(bool(0), style=STYLE_ONOFF)))
            self.property_set("hour", Sample(0, value=Boolean(bool(0), style=STYLE_ONOFF)))
            self.property_set("heat_6", Sample(0, value=Boolean(bool(0), style=STYLE_ONOFF)))
               
        
    
    def weather(self):
        
        
       
    
        
       
        
        print "weather"
        zip = self.property_get("zip").value
        
        url = "http://www.google.com/ig/api?weather=" + str(zip)
       
        try: 
       
            f = urllib.urlopen(url)
        except:
            self.w_retry += 1
            print "Error opening url"
        
        try:
            s = f.read()
            h = s
            # extract weather condition data from xml string
            
            
            weather_temp = s.split("<temp_f data=\"")[-1].split("\"")[0]
            weather_hum = h.split("<humidity data=\"")[-1].split("\"")[0]
            
            if len(weather_temp) == 2:
            	self.w_retry = 0
            
            if weather_temp == "<?xml version=" or weather_hum == "<?xml version=":
            	self.w_retry += 1
            else:
                self.property_set("w_t", Sample(0, weather_temp, "degF"))
                self.property_set("w_h", Sample(0, weather_hum[10:12], "percent"))
              
        
            print weather_temp
            print weather_hum
        except:
        	self.w_retry += 1
        
        repeat_val = SettingsBase.get_setting(self, "sample_rate_sec_w")
        
        if self.w_retry > 8:
        	self.property_set("ot_on", Sample(0, 0, "degF"))
        	self.property_set("w_h", Sample(0, "broken", "percent"))
        	self.w_retry = 0
        
        if self.w_retry > 1 and self.w_retry < 9:
        	self.update_update(30)
        	self.property_set("w_h", Sample(0, "retry mode", "percent"))
        else:
        	self.update_update(repeat_val)
        	
        
        	
        
        
    
       
    def update_update(self, repeat_val):    
       
        
        if self.__event_timer4 is not None:
            try:
                self.__xbee_manager.xbee_device_schedule_cancel(
                    self.__event_timer4)
            except:
                pass
            
        self.__event_timer4 = self.__xbee_manager.xbee_device_schedule_after(
                repeat_val,
                self.weather)
    
    

       

       