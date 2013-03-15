############################################################################
#                                                                          #
# Copyright (c)2009, Digi International (Digi). All Rights Reserved.       #
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
Driver for TZB43 Xbee RCS Thermostat.

Settings:

* **xbee_device_manager:** Must be set to the name of an XBeeDeviceManager
  instance.
* **extended_address:** The extended address of the XBee device you
  would like to monitor.
* **sample_rate_sec:** Rate at which to sample the thermometer in seconds.
  Default rate is 5 min, but the minimum time is every 15 seconds.

To Use:

Issue channel_get (or channel_dump) to read the desired channel.  In
most cases the channel name is descriptive of its purpose.  When issued,
the thermostat device is queried and the channels are filled with the
returned data.  Actual use of serialSend and serialRecieve is discouraged,
instead use the specific channels.  

"""

# import
import time
from threading import Lock

from devices.device_base import DeviceBase
from devices.xbee.xbee_devices.xbee_base import XBeeBase
from settings.settings_base import SettingsBase, Setting
from channels.channel_source_device_property import *
from common.types.boolean import Boolean, STYLE_ONOFF
from devices.xbee.xbee_config_blocks.xbee_config_block_ddo \
    import XBeeConfigBlockDDO
from devices.xbee.xbee_device_manager.xbee_device_manager_event_specs \
    import *
from devices.xbee.common.addressing import *
from devices.xbee.common.io_sample import parse_is, sample_to_mv
from devices.xbee.common.prodid import RCS_THERMOSTAT

import sys
from presentations.presentation_base import PresentationBase
from samples.sample import Sample
from common.helpers.format_channels import iso_date

#import digi_smtplib
#from email.MIMEMultipart import MIMEMultipart
#from email.MIMEBase import MIMEBase
#from email.MIMEText import MIMEText
#from email import Encoders
import os

import threading
import Queue
import cStringIO
import httplib
import digicli

try:
    from rci import process_request
except:
    print "DEBUG RCI IN PLACE, are you running on a PC?"
    mem = 500000
    # For debugging on a PC
    def process_request(s):
        global mem
        print s
        mem -= 100000
        print mem
        return '''\
<rci_reply version="1.1">
    <query_state>
        <device_stats>
            <cpu>3</cpu>
            <uptime>3307</uptime>
            <datetime>Mon Sep 28 10:59:38 2009</datetime>
            <totalmem>16777216</totalmem>
            <freemem>%d</freemem>
        </device_stats>
    </query_state>
</rci_reply>''' % mem



# constants
SM_TEMPLATE1 = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <XMLparser xmlns="http://tempuri.org/">
      <XMLdump>"""

SM_TEMPLATE2 = """</XMLdump>
    </XMLparser>
  </soap:Body>
</soap:Envelope>"""

          # ("infobel", "test")
ADDRESS_A = """&lt;gateway&gt;"""
        
ADDRESS_B = """&lt;/gateway&gt;"""


        
        
        
        
status, output = digicli.digicli('show net')
        
 
if status:
    for line in output:
        if line.find('MAC Address') >= 0:
            l = line.split(':')
            st = "".join(l[1:]).strip()
                    
MAC = st 




# constants

# exception classes

# interface functions

# classes
class XBeeRCS(DeviceBase):

    # Define a set of endpoints that this device will send in on.
    ADDRESS_TABLE = [ [0xe8, 0xc105, 0x11] ]
  #  ADDRESS_TABLE = [ [0xe8, 0xc105, 0x92], [0xe8, 0xc105, 0x11] ]
    
    SUPPORTED_PRODUCTS = [ RCS_THERMOSTAT ]
    
    def __init__(self, name, core_services):
        self.__name = name
        self.__core = core_services
        self.__event_timer2 = None
        self.__serial_lock = Lock()

        ## Local State Variables:
        self._count = 0
        self.__xbee_manager = None
        self.update_timer = None
        self.modes = {"O":0, "H":1, "C":2, "A":3}

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
        ]

        ## Initialize the DeviceBase interface:
        DeviceBase.__init__(self, self.__name, self.__core,
                                settings_list, property_list)


    ## Functions which must be implemented to conform to the DeviceBase
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

        for address in XBeeRCS.ADDRESS_TABLE:
            probe_data['address_table'].append(address)
        for product in XBeeRCS.SUPPORTED_PRODUCTS:
            probe_data['supported_products'].append(product)

        return probe_data
    
    
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
            print self.__name, ": There was an error with the settings. ", \
                  "Attempting to continue."

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
        xbdm_rx_event_spec.cb_set(self.serial_receive)
        xbdm_rx_event_spec.match_spec_set(
            (extended_address, 0xe8, 0xc105, 0x11),
            (True, True, True, True))
        self.__xbee_manager.xbee_device_event_spec_add(self,
                                xbdm_rx_event_spec)

        #register a callback for when the config is done
        xb_rdy_state_spec = XBeeDeviceManagerRunningEventSpec()
        xb_rdy_state_spec.cb_set(self._config_done_cb)
        self.__xbee_manager.xbee_device_event_spec_add(self, xb_rdy_state_spec)
        

        # Create a DDO configuration block for this device:
        xbee_ddo_cfg = XBeeConfigBlockDDO(extended_address)

        # Get the gateway's extended address:
        gw_xbee_sh, gw_xbee_sl = gw_extended_address_tuple()

        # Set the destination for I/O samples to be the gateway:
        xbee_ddo_cfg.add_parameter('DH', gw_xbee_sh)
        xbee_ddo_cfg.add_parameter('DL', gw_xbee_sl)

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
    def update(self):
        """
            Request the latest data from the device.
        """

        print "acquiring update lock..."
        if not self.__serial_lock.acquire(False): #non blocking 
            #(update in progress)
            print "couldnt get update lock... try again later."
            return -1

        try:
            self.serial_send("A=1,Z=1,R=1 R=2\x0D")
            
          #  self.serial_send("A=1,Z=1,R=2\x0D")
            # We will process receive data when it arrives in the callback
        finally:
            #done with the serial
            self.__serial_lock.release()
        
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
        
        
        
        

    def _parse_return_message(self, msg):
        """ Take a status string from thermostat, and
            split it up into a dictionary::
            
                "A" "0" "T=74" -> {'A':0, 'T':74}
            
        """
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
        
        self.__serial_lock.acquire(1)
        try:
            self.serial_send("A=1,Z=1,SPC=" + str(val.value) + "\x0D")
        finally:
            self.__serial_lock.release()

        self.update()

    def set_sph(self, register_name, val):
        """ set point high """
        
        self.property_set(register_name, val)
        
        self.__serial_lock.acquire(1)
        try:
            self.serial_send("A=1,Z=1,SPH=" + str(val.value) + "\x0D")
        finally:
            self.__serial_lock.release()

        self.update()

    def set_sp(self, register_name, val):
        """ Set the set-point temperature """
        
        self.property_set(register_name, val)

        self.__serial_lock.acquire(1)
        try:
            self.serial_send("A=1,Z=1,SP=" + str(val.value) + "\x0D")
        finally:
            self.__serial_lock.release()

        self.update()

    def set_mode(self, val):
        """ set system mode.
            where mode is one of [Off, Heat, Cool, Auto]
        """
 #       self.property_set(register_name, val)
        self.property_set("mode", val)
        
        self.__serial_lock.acquire(1)
        try:
            self.serial_send("A=1,Z=1,M=" + \
                str(self.modes[val.value.title()]) + "\x0D")
        finally:
            self.__serial_lock.release()

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
        
        self.__serial_lock.acquire(1)
        try:
            self.serial_send("A=1,Z=1,F=" + str(int(val.value)) + "\x0D")
        finally:
            self.__serial_lock.release()

        self.update()


    def _config_done_cb(self):
        """ Indicates config is done. """
        print self.__name + " is done configuring, starting polling"
        self.update()


    def serial_receive(self, buf, addr):
        # Parse the I/O sample:
        print "%s.serialReceive:%s" % (self.__name, repr(buf))
    
        # Update channels:
        
        
        self.property_set("serialReceive", Sample(0, buf, ""))

        d = self._parse_return_message(buf)

        if d.has_key("T"):
            self.property_set("current_temp",
                                Sample(0, value=int(d["T"]), unit="F"))
        if d.has_key("SP"):
            self.property_set("spt", 
                                Sample(0, value=int(d["SP"]), unit="F"))
        if d.has_key("SPH"):
            self.property_set("spht",
                                Sample(0, value=int(d["SPH"]), unit="F"))
        if d.has_key("SPC"):
            samp = Sample(0, value=int(d["SPC"]), unit="F")
            self.property_set("splt", samp)
        if d.has_key("M"):
            self.property_set("mode", \
                Sample(0, value=d["M"], unit="o/h/c/a"))
        if d.has_key("FM"):
            self.property_set("fan", Sample(0, value=Boolean(bool(int(d["FM"])),
            style=STYLE_ONOFF)))
        if d.has_key("C1A"):
            self.property_set("ac_1", Sample(0, value=Boolean(bool(int(d["C1A"])),
            style=STYLE_ONOFF)))
        if d.has_key("C2A"):
            self.property_set("ac_2", Sample(0, value=Boolean(bool(int(d["C2A"])),
            style=STYLE_ONOFF)))
        if d.has_key("H1A"):
            self.property_set("heat_1", Sample(0, value=Boolean(bool(int(d["H1A"])),
            style=STYLE_ONOFF)))
        if d.has_key("H2A"):
            self.property_set("heat_2", Sample(0, value=Boolean(bool(int(d["H2A"])),
            style=STYLE_ONOFF)))
        if d.has_key("H3A"):
            self.property_set("heat_3", Sample(0, value=Boolean(bool(int(d["H3A"])),
            style=STYLE_ONOFF)))
            
        
            
        

       

    def __upload_data(self):
        """
        Builds XML string of the channel state and pushes to iDigi
        """
        
        self._count += 1
        
        xml = cStringIO.StringIO()
        
 #       xml.write("&lt;?xml version=\"1.0\"?&gt;")
        compact_xml = SettingsBase.get_setting(self, "compact_xml")    
        if compact_xml:
            xml.write("&lt;idigi_data compact=\"True\"&gt;")
        else:
            xml.write("&lt;idigi_data&gt;")
        
#         print "idigi_db: Uploading to iDigi"

        cm = self.__core.get_service("channel_manager")
        cdb = cm.channel_database_get()
        channel_list = SettingsBase.get_setting(self, "channels")
        
        if len(channel_list) == 0:
            channel_list = cdb.channel_list()

        new_sample_count = 0

        for channel_name in channel_list:
            try:
                channel = cdb.channel_get(channel_name)
                sample = channel.get()
                if sample.timestamp >= self.__last_upload_time:
#                     print "Channel %s was updated since last push" % channel_name
                    new_sample_count += 1
                    compact_xml = SettingsBase.get_setting(self, "compact_xml")    
                    if compact_xml:
                        xml.write(self.__make_compact_xml(channel_name, sample))
                    else:
                        xml.write(self.__make_xml(channel_name, sample))
#                else:
#                     print "Channel %s was not updated since last push" % channel_name
            except:
                # Failed to retrieve the data
                pass

        xml.write("&lt;/idigi_data&gt;")

        if self._count > 300 and new_sample_count == 0:
            self.reset()
        
        if new_sample_count > 0:
            self.__last_upload_time = time.time()
            self._count = 0
            self.__send_to_idigi(xml.getvalue())

        xml.close()

#         print "idigi_db: I uploaded to iDigi"


    def reset(self):
        process_request('<rci_request><reboot /></rci_request>')
        # Give us some time to reboot.  We should not return.
        while True:
            time.sleep(60)
    
    def __make_xml(self, channel_name, sample):
        """
        Converts a sample to XML. Returns String
        
        Keyword arguments:
        
        channel_name -- the name of the channel
        sample -- the corresponding sample
        """

        data = "&lt;sample&gt;"
        data += "&lt;name&gt;%s&lt;/name&gt;"
        data += "&lt;value&gt;%s&lt;/value&gt;"
        data += "&lt;unit&gt;%s&lt;/unit&gt;"
        data += "&lt;timestamp&gt;%s&lt;/timestamp&gt;"
        data += "&lt;/sample&gt;"

        return data % (channel_name, self.__escape_entities(sample.value),
                       sample.unit, iso_date(sample.timestamp))


    def __make_compact_xml(self, channel_name, sample):
        """
        Converts a sample to compact XML (using attributes instead of tags). Returns String
        
        Keyword arguments:
        
        channel_name -- the name of the channel
        sample -- the corresponding sample
        """

        data = "<sample name=\"%s\" value=\"%s\" unit=\"%s\" timestamp=\"%s\" />"

        return data % (channel_name, self.__escape_entities(sample.value),
                       sample.unit, iso_date(sample.timestamp))


    
    
    
    
    def __send_to_idigi(self, data):
        """
        Sends data to Dane
        
        Keyword arguments:
        
        data - the XML string to send
        """
        
        
   #     device_string = StringIO()
        
   #     device_string.write('&lt;channel_dump&gt;')
        
   #     cdb = (self.__core.get_service("channel_manager")
     #           .channel_database_get())
    #    device_string.write(self.__generate_channel_database(cdb))
    
     #   dump = device_string.getvalue()
        
     #   print dump

     #   dumptest = "\"<10>10</10>\""




     
        

          # ("infobel", "test")
        SoapMessage = SM_TEMPLATE1 + ADDRESS_A + MAC + data + ADDRESS_B + SM_TEMPLATE2 
        
        
    #    print SoapMessage 
        
     #print SoapMessage
       
        send_error1 = "error sending message to Dane's web service"


        try:
            webservice = httplib.HTTP("www.control.houselynx.co")
            webservice.putrequest(unicode("POST", "utf-8" ), unicode("/UploadDump.asmx", "utf-8" ), "HTTP/1.1")
    #        webservice.putheader("POST", "/NumericUpDown.asmx", "" )
            webservice.putheader(unicode("Host", "utf-8" ), unicode("www.control.houselynx.co", "utf-8" ))
    #        webservice.putheader("User-Agent: ", "Python Post")
            webservice.putheader(unicode("Content-Type", "utf-8" ), unicode("text/xml; charset=\"UTF-8\"", "utf-8" ))
            webservice.putheader(unicode("Content-Length", "utf-8" ), unicode("%d", "utf-8" ) % len(SoapMessage))
            webservice.putheader(unicode("SOAPAction", "utf-8" ), unicode("\"http://tempuri.org/XMLparser\"", "utf-8" ))
            webservice.endheaders()
            webservice.send(unicode(SoapMessage, "utf-8" ))
            statuscode, statusmessage, header = webservice.getreply()
            webservice.close()
        except:
            httplib.HTTP("www.control.houselynx.co").close()
            print send_error1
        
        
            
     #   print SoapMessage
     # get the response
        try:
            print "Response: ", statuscode, statusmessage
            print "headers: ", header 
          #  print SoapMessage       
        except:
            print "was not able to get response"
        
        
        
        
        
        





        
#        filename = SettingsBase.get_setting(self, "filename")    
#        filename = filename + "%i.xml" % self.__current_file_number
#        collection = SettingsBase.get_setting(self, "collection")    
#        secure = SettingsBase.get_setting(self, "secure")    
#        success, err, errmsg = idigi_data.send_idigi_data(data, filename, collection, secure)
    
#        self.__current_file_number += 1
    
#        max_files = SettingsBase.get_setting(self, "file_count")
    
#        if self.__current_file_number >= max_files + 1:
#            self.__current_file_number = 1


    def __escape_entities(self, sample_value):
        """
            Replace the existing entities of the sample value.
        """

        if not isinstance(sample_value, str):
            return sample_value
        for ch in ENTITY_MAP:
            sample_value = sample_value.replace(ch, ENTITY_MAP[ch])

        return sample_value
    
    def serial_send(self, serialString):
        """ Takes either a string or a Sample() """

        if not type(serialString) == type(''):
            serialString = serialString.value # type is Sample

        print "%s.serialString:%s" % (self.__name, repr(serialString))
        extended_address = SettingsBase.get_setting(self, "extended_address")
        addr = (extended_address, 0xe8, 0xc105, 0x11)
        buf = serialString + chr(0x0D)
        try:
            self.__xbee_manager.xbee_device_xmit(0xe8, buf, addr)
        except:
            print "Error writing to extended_address:%s" % extended_address

# internal functions & classes



# internal functions & classes

def main():
    pass

if __name__ == '__main__':
    import sys
    status = main()
    sys.exit(status)

