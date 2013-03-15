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
Driver for the MistAway unit.

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

#device_base import DeviceBase
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

# constants

# exception classes

# interface functions

# classes
class XBeeRCS(XBeeBase):

    # Define a set of endpoints that this device will send in on.
    ADDRESS_TABLE = [ [0xe8, 0xc105, 0x92], [0xe8, 0xc105, 0x11] ]
    
    SUPPORTED_PRODUCTS = [ RCS_THERMOSTAT ]
    
    def __init__(self, name, core_services):
        self.__name = name
        self.__core = core_services
        self.__event_timer = None
        self.__serial_lock = Lock()

        ## Local State Variables:
        self.__xbee_manager = None
        self.update_timer = None
        self.modes = {"off":0, "heat":1, "cool":2, "auto":3}

        ## Settings Table Definition:
        settings_list = [
            Setting(
                name='xbee_device_manager', type=str, required=True),
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
                set_cb=lambda x: self.set_spc("splt", x)),
            ChannelSourceDeviceProperty(name="mode", type=str,
                initial=Sample(timestamp=0, unit="o/h/c/a", value="Off"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_mode("mode", x)),
            ChannelSourceDeviceProperty(name="start", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(True, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_fan("start", x)),
            ChannelSourceDeviceProperty(name="stop", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(True, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_fan("stop", x)),
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
        XBeeBase.__init__(self, self.__name, self.__core,
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
            self.serial_send("A=1,Z=1,R=1\x0D")
            time.sleep(2)
            self.serial_send("A=1,Z=1,R=2\x0D")
            # We will process receive data when it arrives in the callback
        finally:
            #done with the serial
            self.__serial_lock.release()

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

    def set_spc(self, register_name, val):
        """ set point cool """
        
        self.property_set(register_name, val)
        
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

    def set_mode(self, register_name, val):
        """ set system mode.
            where mode is one of [Off, Heat, Cool, Auto]
        """
 #       self.property_set(register_name, val)
        self.property_set(register_name, Sample(0, val, "o/h/c/a"))
        
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

