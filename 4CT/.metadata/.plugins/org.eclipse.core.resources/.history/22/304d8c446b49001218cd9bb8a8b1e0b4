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
import types
import traceback
import binascii
import threading
# imports
import struct

import thread

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

import time

from common.abstract_service_manager import AbstractServiceManager


from custom_presentations.presentations.idigi_db.idigi_dbM import iDigi_DB




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

# interface setions

# classes

class f_counter:

      
    def __init__(self, time):
        self.time = time
        
    def timeout(self):
        
        while self.time_o > 1:
            self.time_o -= 1
            time.sleep(.1)
            
        if self.line == 200:
            print "update success"
        else:
            print "restarting, device timed out"
            self.firm_update("a", 1)
    



class XBeeSerialTerminal(XBeeSerial):
    """\
        This class extends one of our base classes and is intended as an
        example of a concrete, example implementation, but it is not itself
        meant to be included as part of our developer API. Please consult the
        base class documentation for the API and the source code for this file
        for an example implementation.

    """
    
    
    
    
    
 
    
			
    ADDRESS_TABLE = [ [0xe8, 0xc105, 0x92], [0xe8, 0xc105, 0x11] ]
    
    SUPPORTED_PRODUCTS = [ MISTAWAY_CONTROLLER, ]
    
    def __init__(self, name, core_services):
        self.__name = name
        self.__core = core_services
        self.__event_timer2 = None
        self.__event_timer3 = None
        self.fwu = 0
        self.m_mode = 0 # 0 = not misting, 1=user initiated, 2=user cancelled, 3=success
        self.list = 0


        ## Local State Variables:
        self._count = 0
        self.__xbee_manager = None
        self.update_timer = None
        self.modes = {"O":0, "H":1, "C":2, "A":3}
        self.count = 0
        self.retry_count = 0
        self.filename = None
        self.error = ""
        self.data = None
        self.file = None
        self.time_o = 0
        self.line = 0
        self.retry = 0
        
        self.getting_all_values = 0 # true or false for if I'm looking for an r=6 return
        
        

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
                default_value=300),
        ]

        ## Channel Properties Definition:
        property_list = [
						 
			#gettable only channles:
			
			
			ChannelSourceDeviceProperty(name="VL", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
			
			ChannelSourceDeviceProperty(name="DM", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
			
			ChannelSourceDeviceProperty(name="TMH", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
			
			ChannelSourceDeviceProperty(name="PRH", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
			
			ChannelSourceDeviceProperty(name="SPD", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
			
			ChannelSourceDeviceProperty(name="FL", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
			
			ChannelSourceDeviceProperty(name="AFR", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
			
			ChannelSourceDeviceProperty(name="TF", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
			
			
			ChannelSourceDeviceProperty(name="CF", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
			
			ChannelSourceDeviceProperty(name="CR", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
			
			ChannelSourceDeviceProperty(name="DS", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
			
			ChannelSourceDeviceProperty(name="DUE", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
			
			ChannelSourceDeviceProperty(name="ST", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
			
			ChannelSourceDeviceProperty(name="SS", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
			
			ChannelSourceDeviceProperty(name="CFV", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
			
			ChannelSourceDeviceProperty(name="LD", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
			
			ChannelSourceDeviceProperty(name="FS", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
			
			ChannelSourceDeviceProperty(name="ZK", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
			
			
						
						
						
						
			# settable channels:
			
			ChannelSourceDeviceProperty(name="TMC", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("TMC", x)),
			
			ChannelSourceDeviceProperty(name="TMM", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("TMM", x)),
						 
			ChannelSourceDeviceProperty(name="MMC", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("MMC", x)),			 
						 
			ChannelSourceDeviceProperty(name="RMC", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("RMC", x)),
						
			ChannelSourceDeviceProperty(name="NFR", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("NFR", x)),			 
						
			ChannelSourceDeviceProperty(name="TOL", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("TOL", x)),
						 
			ChannelSourceDeviceProperty(name="J", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("J", x)),			 
						 
			ChannelSourceDeviceProperty(name="K", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("K", x)),
						
			ChannelSourceDeviceProperty(name="L", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("L", x)),
						
			ChannelSourceDeviceProperty(name="Hld", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("Hld", x)),
						
			ChannelSourceDeviceProperty(name="DST", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("DST", x)),		 
			
			ChannelSourceDeviceProperty(name="DOW", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("DOW", x)),
						 
			ChannelSourceDeviceProperty(name="TOD", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_time("TOD", x)),			 
			
			
			ChannelSourceDeviceProperty(name="CT0", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CT0", x)),			 
			
			ChannelSourceDeviceProperty(name="CT1", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CT1", x)),
			
			ChannelSourceDeviceProperty(name="CT2", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CT2", x)),
			
			
			ChannelSourceDeviceProperty(name="CT3", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CT3", x)),
			
			ChannelSourceDeviceProperty(name="CT4", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CT4", x)),
			
			
			ChannelSourceDeviceProperty(name="CT5", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CT5", x)),			 
			
			ChannelSourceDeviceProperty(name="CT6", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CT6", x)),
			
			ChannelSourceDeviceProperty(name="CT7", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CT7", x)),
			
			
			ChannelSourceDeviceProperty(name="CT8", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CT8", x)),
			
			ChannelSourceDeviceProperty(name="CT9", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CT9", x)),			 
			
			ChannelSourceDeviceProperty(name="CT10", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CT10", x)),
			
			ChannelSourceDeviceProperty(name="CT11", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CT11", x)),
			
			
			ChannelSourceDeviceProperty(name="CT12", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CT12", x)),
			
			ChannelSourceDeviceProperty(name="CT13", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CT13", x)),
			
			
			ChannelSourceDeviceProperty(name="CT14", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CT14", x)),			 
			
			ChannelSourceDeviceProperty(name="CT15", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CT15", x)),
			
			ChannelSourceDeviceProperty(name="CT16", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CT16", x)),
			
			
			ChannelSourceDeviceProperty(name="CT17", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CT17", x)),
			
			ChannelSourceDeviceProperty(name="CT18", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CT18", x)),
			
			
			ChannelSourceDeviceProperty(name="CT19", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CT19", x)),			 
			
			ChannelSourceDeviceProperty(name="CT20", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CT20", x)),
			
			ChannelSourceDeviceProperty(name="CT21", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CT21", x)),
			
			
			ChannelSourceDeviceProperty(name="CT22", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CT22", x)),
			
			ChannelSourceDeviceProperty(name="CT23", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CT23", x)),
						
			
			ChannelSourceDeviceProperty(name="CY0", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_time("CY0", x)),	
			
			ChannelSourceDeviceProperty(name="CY1", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_time("CY1", x)),	
			
			ChannelSourceDeviceProperty(name="CY2", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_time("CY2", x)),	
			
			ChannelSourceDeviceProperty(name="CY3", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_time("CY3", x)),	
			
			ChannelSourceDeviceProperty(name="CY4", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_time("CY4", x)),	
			
			ChannelSourceDeviceProperty(name="CY5", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_time("CY5", x)),
						
			ChannelSourceDeviceProperty(name="CY6", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_time("CY6", x)),	
			
			ChannelSourceDeviceProperty(name="CY7", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_time("CY7", x)),	
			
			ChannelSourceDeviceProperty(name="CY8", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_time("CY8", x)),	
			
			ChannelSourceDeviceProperty(name="CY9", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_time("CY9", x)),	
			
			ChannelSourceDeviceProperty(name="CY10", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_time("CY10", x)),	
			
			ChannelSourceDeviceProperty(name="CY11", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_time("CY11", x)),
			
			ChannelSourceDeviceProperty(name="CY12", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_time("CY12", x)),	
			
			ChannelSourceDeviceProperty(name="CY13", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_time("CY13", x)),	
			
			ChannelSourceDeviceProperty(name="CY14", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_time("CY14", x)),	
			
			ChannelSourceDeviceProperty(name="CY15", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_time("CY15", x)),	
			
			ChannelSourceDeviceProperty(name="CY16", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_time("CY16", x)),	
			
			ChannelSourceDeviceProperty(name="CY17", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_time("CY17", x)),
						
			ChannelSourceDeviceProperty(name="CY18", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_time("CY18", x)),	
			
			ChannelSourceDeviceProperty(name="CY19", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_time("CY19", x)),	
			
			ChannelSourceDeviceProperty(name="CY20", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_time("CY20", x)),	
			
			ChannelSourceDeviceProperty(name="CY21", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_time("CY21", x)),	
			
			ChannelSourceDeviceProperty(name="CY22", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_time("CY22", x)),	
			
			ChannelSourceDeviceProperty(name="CY23", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_time("CY23", x)),
			
			
			ChannelSourceDeviceProperty(name="CD1", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CD1", x)),
						 
			ChannelSourceDeviceProperty(name="CD2", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CD2", x)),			 
						 
			ChannelSourceDeviceProperty(name="CD3", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CD3", x)),
						
			ChannelSourceDeviceProperty(name="CD4", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CD4", x)),
						
			ChannelSourceDeviceProperty(name="CD5", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CD5", x)),
						
			ChannelSourceDeviceProperty(name="CD6", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CD6", x)),
			
			ChannelSourceDeviceProperty(name="CD7", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("CD7", x)),
						 
			ChannelSourceDeviceProperty(name="REM", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("REM", x)),			 
						 
			ChannelSourceDeviceProperty(name="RMZ", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("RMZ", x)),
						
			ChannelSourceDeviceProperty(name="MAN", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("MAN", x)),			 
						
			ChannelSourceDeviceProperty(name="MNZ", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("MNZ", x)),
						 
			ChannelSourceDeviceProperty(name="ZNC", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("ZNC", x)),			 
						 
			ChannelSourceDeviceProperty(name="NOZ", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("NOZ", x)),
						
			ChannelSourceDeviceProperty(name="NZ1", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("NZ1", x)),
						
			ChannelSourceDeviceProperty(name="NZ2", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("NZ2", x)),
						
			ChannelSourceDeviceProperty(name="AGTT", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set_time("AGTT", x)),
			
			
			ChannelSourceDeviceProperty(name="AGTD", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("AGTD", x)),
						 
			ChannelSourceDeviceProperty(name="RAG", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("RAG", x)),			 
						 
			ChannelSourceDeviceProperty(name="TNK", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("TNK", x)),
						
			ChannelSourceDeviceProperty(name="SEN", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("SEN", x)),			 
						
			ChannelSourceDeviceProperty(name="WND", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("WND", x)),
						 
			ChannelSourceDeviceProperty(name="ALT", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET), 
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("ALT", x)),			 
						 
			ChannelSourceDeviceProperty(name="ER0", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("ER0", x)),
						
			ChannelSourceDeviceProperty(name="ER2", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("ER2", x)),
						
			ChannelSourceDeviceProperty(name="ER3", type=str,     
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("ER3", x)),
						
			ChannelSourceDeviceProperty(name="ER6", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("ER6", x)),
			
			ChannelSourceDeviceProperty(name="FM", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("FM", x)),
						 
			ChannelSourceDeviceProperty(name="LVL", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("LVL", x)),			 
						 
			ChannelSourceDeviceProperty(name="MIX", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("MIX", x)),
						
			ChannelSourceDeviceProperty(name="BOT", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("BOT", x)),			 
						
			ChannelSourceDeviceProperty(name="FLT", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("FLT", x)),
						 
			ChannelSourceDeviceProperty(name="MX", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("MX", x)),			 
						 
			ChannelSourceDeviceProperty(name="MD", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.set("MD", x)),
						
			
            # gettable properties
            
            
            
            
            ChannelSourceDeviceProperty(name="pause", type=float,
                initial=Sample(timestamp=0, unit="pause", value=.005),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.f_name("pause", x)),
            
            ChannelSourceDeviceProperty(name="block_size", type=int,
                initial=Sample(timestamp=0, unit="degF", value=1),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.f_name("block_size", x)),
            
            ChannelSourceDeviceProperty(name="file_name", type=str,
                initial=Sample(timestamp=0, unit="degF", value="output.txt"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.f_name("file_name", x)),
            
            
            ChannelSourceDeviceProperty(name="update_settings", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.replace_all_settings("update_settings", x)),
            
            
            ChannelSourceDeviceProperty(name="update_file", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.get_all_settings("update_file", x)),
            
            
            ChannelSourceDeviceProperty(name="fw_update", type=Boolean,
                initial=Sample(timestamp=0,
                value=Boolean(False, style=STYLE_ONOFF)),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.firm_update("fw_update", x)),
            
            ChannelSourceDeviceProperty(name="signal", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            
            ChannelSourceDeviceProperty(name="mc", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            
            ChannelSourceDeviceProperty(name="pm", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            
            ChannelSourceDeviceProperty(name="est", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            
            ChannelSourceDeviceProperty(name="serialReceive", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            
            ChannelSourceDeviceProperty(name="serialSend", type=str,
                initial=Sample(timestamp=0, unit="F", value=" "),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.serial_write("serialSend", x)),
            
            
            ChannelSourceDeviceProperty(name="g", type=str,
                initial=Sample(timestamp=0, unit="", value="not_set"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.get("g", x)),
            
           
            
            ChannelSourceDeviceProperty(name="r", type=str,
                initial=Sample(timestamp=0, unit="", value="not_set"),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP,
                set_cb=lambda x: self.new_update("r", x)),
            
            ChannelSourceDeviceProperty(name="cr", type=str,
                initial=Sample(timestamp=0, unit="", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP),
           #     set_cb=lambda x: self.set_sph("cartridge_remaining_volume", x)),
            
            ChannelSourceDeviceProperty(name="cfv", type=str,
                initial=Sample(timestamp=0, unit="F", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP),
        #        set_cb=lambda x: self.set_sph("cartridge_full_volume", x)),
            
            ChannelSourceDeviceProperty(name="line_number", type=int,
                initial=Sample(timestamp=0, unit="line", value=0),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP),
            
            ChannelSourceDeviceProperty(name="test", type=int,
                initial=Sample(timestamp=0, unit="T_O", value=0),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP),
            
            ChannelSourceDeviceProperty(name="crc", type=str,
                initial=Sample(timestamp=0, unit="F", value=""),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP),
            
            ChannelSourceDeviceProperty(name="error", type=str,
                initial=Sample(timestamp=0, unit="E", value=" "),
                perms_mask=(DPROP_PERM_GET|DPROP_PERM_SET),
                options=DPROP_OPT_AUTOTIMESTAMP),
        #        set_cb=lambda x: self.set_sph("crc", x)),
                
            
        ]

        ## Initialize the XBeeSerial interface:
        XBeeSerial.__init__(self, self.__name, self.__core,    
                                settings_list, property_list)


    
    
    @staticmethod
    def probe():
        
        probe_data = XBeeBase.probe()

        for address in XBeeSerialTerminal.ADDRESS_TABLE:
            probe_data['address_table'].append(address)
        for product in XBeeSerialTerminal.SUPPORTED_PRODUCTS:
            probe_data['supported_products'].append(product)

        return probe_data
       ## setions which must be implemented to conform to the XBeeSerial
    ## interface:
              
    
    
    def read_callback(self, buf):
        self.serial_read(buf)


    ## setions which must be implemented to conform to the DeviceBase
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

        # Call the XBeeSerial setion to add the initial set up of our device.
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
        extended_address = SettingsBase.get_setting(self, "extended_address")
        
        try:
        
	        db = self.__xbee_manager.xbee_device_ddo_get_param(extended_address,
	                                                                  "DB", use_cache=True)
	        sv = self.__xbee_manager.xbee_device_ddo_get_param(extended_address,
	                                                                  "%V", use_cache=True)
	        
	        
	        
	        try:
	            dd = struct.unpack(">B", db)
	            #print dd
	        except:
	        	print "failed 4"     
	        
	        sv = struct.unpack(">H", sv)
	       # print sv
	
	        dd = str(dd)
	        dd = dd[1:3]
	        dd = "-" + dd + " dB"
	        print "signal strength ="
	        print dd
	        self.property_set("signal", Sample(0, value=str(dd), unit=""))
	        
	        
	        sv = str(sv)
	        sv = sv[1:5]
	        sv = int(sv)
	        print sv
	        volts = (sv * 1.1719) / 1000
	        print "volts ="
	        print volts
	    

        
        
        except:
        	self.property_set("signal", Sample(0, value="disconnected", unit=""))
        	print "failed to get signal and voltage"
       
       
        
        if self.fwu == 0:
	        try:
	        	
	            self.serial_send("r=1,")
	            time.sleep(3)
	            self.serial_send("g=6,")
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


    ## Locally defined setions:

    def _parse_return_message(self, msg):
        """ Take a status string from thermostat, and
            split it up into a dictionary::
            
                "A" "0" "T=74" -> {'A':0, 'T':74}
            
        """
       # msg.replace(",$", " ")
      #  msg.replace(",", " ")
        
        
        msg = msg.strip()
        
        if msg.startswith("1"):
            msg = msg[1:]
           
       
		#take off ,$ from end
        msg = msg[:-2]

        try:
            if not msg:
                return {}
            
            ret = {}
            split_msg = msg.split(",") #tokenize
    #        print split_msg
            for i in split_msg:
            	try:
	                i = i.split("=")
	                ret[i[0]] = i[1]
                except:
	            	continue
                

          #  print ret
            return ret

        except:
            print "Error parsing return message: " + repr(msg)
            return {}

    
    def get_all_settings (self, register_name, val):
    	
    	self.getting_all_values = 1
    	
    	self.serial_send("g=6,")
    	
    	
    
    
    def set_settings_to_file (self, d):
    	
    	
    	file = open("WEB/python/datafile.txt", "w")
    	
    	for i in d:
		        	
			try:
				file.writelines(str(i) + "=" + str(d[i]) + ",")
			except:
				continue
    	
    	file.close()
    
    
    
    def replace_all_settings (self, register_name, val):
    	
    	file = open("WEB/python/datafile.txt", "r")
    	
    	f = file.readlines()
    	
    	print f
    	
    	
    	
    	'''msg = msg.strip()
        
        if msg.startswith("1"):
            msg = msg[1:]
           
       
		#take off ,$ from end
        msg = msg[:-2]

        try:
            if not msg:
                return {}
            
            ret = {}
            split_msg = msg.split(",") #tokenize
    #        print split_msg
            for i in split_msg:
            	try:
	                i = i.split("=")
	                ret[i[0]] = i[1]
                except:
	            	continue
                

          #  print ret
            return ret

        except:
            print "Error parsing return message: " + repr(msg)
            return {}'''
    
    
    def get(self, register_name, val):
    	
    	self.property_set(register_name, val)
    	
    	data = "g=" + str(val.value) + ","
    	
    	self.serial_send(data)
    
    
    
    def set_time(self, register_name, val):
    	
    	self.list += 1
    	
    	time.sleep(self.list)
    	
    	self.property_set(register_name, val)
    	value = val.value
    	
    	new_val = value.split(":")
    	
    	print new_val[0]
    	print new_val[1]
    	# multiply hours by 3600 for seconds in the hours
    	hours_in_seconds = int(new_val[0]) * 3600
    	
    	#mulitply minutes by 60 to get seconds in the minutes
    	minutes_in_seconds = int(new_val[1]) * 60
    	
    	seconds = hours_in_seconds + minutes_in_seconds
    	
    	
    	data = "s(" + register_name + "=" + str(seconds) + ")"
     	
     	print data
     	
     	self.serial_send(str(data))
     	
     	
     	self.list -= 1
    
    
    def set(self, register_name, val):
    	
    	self.list += 1
    	
    	time.sleep(self.list)
    	
     	self.property_set(register_name, val)
     	print val.value
     	data = "s(" + register_name + "=" + str(val.value) + ")"
     	
     	self.serial_send(data)
     	
     	self.list -= 1
     	
     	
     	
    
    def new_update(self, register_name, val):
    	
    	self.property_set(register_name, val)
    	
    	r = self.property_get("r").value
    	
    	
    	
    	r = r.strip()
    	
    	print r
    	
    	if self.fwu == 0:
    		
			if r == "M":
				self.serial_send("r=M,")
				time.sleep(2)
				self.serial_send("r=1,")
			elif r == "6":
				self.serial_send("g=6,")
			elif r == "1":
				self.update()
				#self.upload.upload_data()
			elif r == "S":
				self.serial_send("r=S,")
				time.sleep(.5)
				self.serial_send("r=1,")
			elif r == "I":
				self.serial_send("r=I,")
			elif r == "CE":
				self.serial_send("r=CE,")
				time.sleep(.5)
				self.serial_send("r=S,")
			elif r == "CH":
				self.serial_send("r=CH,")
			elif r == "SM":
				self.serial_send("r=SM,")
			elif r == "CS":
				self.serial_send("r=CS,")
			elif r == "IZ1":
				self.serial_send("r=IZ1,")
			elif r == "IZ2":
				self.serial_send("r=IZ2,")
			elif r == "FT":
				self.serial_send("r=FT,")
				
    def _config_done_cb(self):
        """ Indicates config is done. """
        print self.__name + " is done configuring, starting polling"
  #      self.test = 0 #previous cr value
        self.test2 = 0 #previous status
        self.count = 0
        self.string = "1"
        
        upld = self.__core.get_service("presentation_manager")
       # self.upload = upld.driver_get("upload")
        #self.upload = iDigi_DB("uploader", self.__core, )
       
        
        self.update()
        


    
            
    
    def serial_read(self, buf):
        print "XBeeSerialTerminal: Read Data: %s" % (buf)
        
       
        
        	
      	
    
        
        self.property_set("serialReceive", Sample(0, buf, ""))
        
       
        
        
        if self.fwu == 1:
            if buf == "O":
                self.retry_count = 0
                line = self.line + 1 
                self.line = line
                self.send_next_line(line)
            elif buf == "CE" or buf == "?":
                self.retry_count += 1
                print "retry count ="
                print self.retry_count
                ere = "retry count =" + str(self.retry_count) + " on line number:" + str(self.line)
                self.property_set("error", Sample(0, ere, "E"))
                if self.retry_count > 15:
                	self.line = 300
                	self.retry_count = 0
                	self.error = "error updating firmware. Program quitting"
                	self.property_set("error", Sample(0, self.error, "E"))
                	self.property_set("line_number", Sample(0, 300, "line"))
            	else:
					self.send_repeat()
        elif self.fwu == 2:
        	if buf == "O":
        		self.fwu = 0
        		self.execute()
    		else:
    			print "failed to validate file"
        			
        else:
        
	        if buf == "?":
	        	return
	        
	        if not buf.endswith("$"):
	        	self.string = self.string + buf
	        
	        if buf.endswith("$"):        
		        self.string = self.string + buf
		        
		        d = self._parse_return_message(self.string)   
		        if self.getting_all_values == 1:
		         	self.set_settings_to_file(d)
		         	self.string = ""
		         	self.getting_all_values = 0
		         	return
		            
		        self.string = ""
		        
		        
		        
		        for i in d:
		        	
					try:
						self.property_set(i, Sample(0, value=d[i], unit=""))
					except:
						continue
		        	
		        
		        
		        
		        
		        
		        '''sample1 = buf[:-11]
		    #    print sample1       
		        if d.has_key("st") and d["st"] != "ACK":  
		        	
		       # 	print "status"
		        #	print d["st"] 
		        	
		        	if d.has_key("crc") :
		        		pass
		        		#print "found crc"
		        	else:
		        		print "no crc found in dictionary"
		        	if int(d["crc"]) == int(self.calcString(sample1, 0)):
		  	            pass
		        	#	self.serial_send("r=ACK,")
		       # 		print "crc's matched, request finished"
		        	else:
		        		self.serial_send("r=NAK,")
		        		print "crc mis match, send NAK"
		        		return
		        else:
		            print "status = ACK or no status"
		            			        	          	
		        
		        
		        if d.has_key("mc"):
		        	self.property_set("mc", Sample(0, value=d["mc"], unit=""))
		     #   	print "mist cycle"
		     #   	print d["mc"]
					
					
	
		 
	
		        if d.has_key("st") and d["st"] != "ACK":
		            self.property_set("st",
		                                Sample(0, value=d["st"], unit=""))
		          
		            
		            ## send status on recieve
		            
		            
		            
		        if d.has_key("cfv"):
		            self.property_set("cfv", 
		                                Sample(0, value=int(d["cfv"]), unit=""))
		        if d.has_key("cr"):
		            self.property_set("cr",
		                                Sample(0, value=int(d["cr"]), unit="F")) 
		        if d.has_key("crc"):
		            self.property_set("crc",
		                                Sample(0, value=int(d["crc"]), unit="F"))
		        self.test2 = self.property_get("st").value        	
		        
		        if self.count < 4:
		        	self.update()
		        	self.count += 1'''
	
    def f_name(self, register_name, val):
    	
    	self.property_set(register_name, val)
    	
    	fname = self.property_get("file_name").value
    	
    	self.filename = "WEB/python/" + fname
    	
    	
    
    def execute(self):
    	
    
    	print "starting program"
    	self.send("XX")
    
    def firm_update(self, register_name, val):
        
        self.fwu = 0
    	
    	if self.file is not None:
	    	try:
	    		self.file.close()
	    	except:
	    		print "file did not need to be closed"
	        
        
        self.line = 0
        line = self.line
        
        if register_name != "a":
            self.property_set(register_name, val)
        
        
        if self.filename == None:
        	self.filename = "WEB/python/output.txt"
        
        
        
        print "sending q"
        self.send("q")
        
        
        time.sleep(2)
        
        
        
        
        print "puttng device in bootloader mode"
        self.send("r=F,crc=63902,$")
        
        
        time.sleep(10)
        self.fwu = 1
         
        print "sending N"
        
        
        
        self.send("N")
        time.sleep(3)
        
        
        
        
        
        try:
        	self.file = open(self.filename, "r")
        except:
        	print "could not open file"
        	self.error = "file could not open"
        	self.property_set("error", Sample(0, self.error, "E"))
        	return
        
        
        
        data1 = self.file.readline()
        data1 = data1.strip()
        self.data = data1[1:]
        
        
        #for i in range(len(self.f)):         
         #   self.f[i] = self.f[i][1:]
          #  self.f[i] = self.f[i].strip()
        
        self.send("MM")
        print "sending M, clearing memory"
        
        print "sleeping 10 sec"
        
        time.sleep(10)
        
        self.last_line = 0
    	self.check = 0
        
        self.timeout()
     
        try:
        	lst = self.chunks(self.data, 20)
        except:
        	self.error = "could not break up line:" + str(self.line) + " into pieces"
        	self.property_set("error", Sample(0, self.error, "E"))
        	print self.error
        	return
        
        print lst
        
        try:
	        self.send("@")
	        time.sleep(1)
	        
	        for i in range(len(lst)):
	        	self.send(lst[i])
	        	time.sleep(.1)
	        	
	        	
	        	
        
        
        except:
        	self.error = "error sending line:" + str(self.line)
        	self.property_set("error", Sample(0, self.error, "E"))
        	print self.error

    def send_repeat(self):
    	
        
    	lst = self.chunks(self.data, 20)
    	self.send(chr(64))
    	time.sleep(.1)
    	for i in range(len(lst)):
    		self.send(lst[i])
    		time.sleep(.1)
    	
    	
    	
    	
    	
    
    def send_next_line(self, line):
        print "sending line number:"
        print line
        
        if line == 71:
            time.sleep(5)
        
        if line == 73:
        	time.sleep(5)
        
        if line == 74:
        	time.sleep(5)
        
        if line == 72:
        	time.sleep(5)
        
        if line == 84:
        	time.sleep(8)
        	
        	
        pause1 = self.property_get("pause").value
        size = self.property_get("block_size").value
        
        
        self.property_set("line_number", Sample(0, line, "line"))
        
        if line < 50:
        	time.sleep(2)
        else:
        	time.sleep(2)
        
        try:
            data1 = self.file.readline()
            if len(data1) < 2:
                print "ending upload"
                self.fwu = 2
                time.sleep(10)
                self.property_set("line_number", Sample(0, 200, "line"))
		    #	self.file.close()
                self.send("YY")
                time.sleep(10)
                self.update()
                self.line = 200
            if len(data1) > 2:
                data1 = data1.strip()
                self.data = data1[1:]
                lst = self.chunks(self.data, size)
                self.send(chr(64))
                time.sleep(.1)
                for i in range(len(lst)):
                    self.send(lst[i])
                    print lst[i]
                    time.sleep(pause1)
                    
              

        except:
        	self.error = "error sending line:" + str(self.line)
        	self.property_set("error", Sample(0, self.error, "E"))
        	print self.error
	    
	    
	    
	    
	    	
	      
        	
        
        
    
    def timeout(self):
    	
    	
    	
    	
    		
    	self.check += 1
    	print "number of times timeout has ran:"
    	print self.check
    	
    	
    	if self.check > 1:	
	    	if self.line == self.last_line:
	    		print "restarting, device timed out"
	    		self.property_set("error", Sample(0, "restarting, device timed out", "E"))
	    		self.retry += 1
	    		
	    		if self.retry < 5:
	    			self.firm_update("a", 1)
    			else:
    				self.send("q")
    				self.line = 300
    				self.fwu = 0
    				self.retry = 0
    				self.error = "error updating firmware. Program quitting"
        	        self.property_set("error", Sample(0, self.error, "E"))
        	        self.property_set("line_number", Sample(0, 300, "line"))
    				
    				
	    		
    			
    		
       
    	
    	self.last_line = self.line
    	
    	if self.__event_timer3 is not None:
            try:
                self.__xbee_manager.xbee_device_schedule_cancel(
                    self.__event_timer3)
            except:
                pass
        
        if self.line == 200 or self.line == 300:
        	pass    
        else:
        	
        	self.__event_timer3 = self.__xbee_manager.xbee_device_schedule_after(
	                30,
	                self.timeout)
        	
	        	
        
        
        
        
        
  
    
    
    
    
    def chunks(self, seq, length):
    	return [seq[i:i+length] for i in range(0, len(seq), length)]
    
    
    def serial_write(self, register_name, val):
    	
    	self.property_set(register_name, val)
    	
    	buf = self.property_get("serialSend").value
        buf = buf.strip()
        try:
            ret = self.write(buf)
            if ret == False:
                raise Exception, "write failed"
        except:
            print "XBeeSerialTerminal: Error writing data:"
    
    
    def send(self, data):
      #  print "XBeeSerialTerminal: Write Data: %s" % (data)
        #buf = data.value + chr(0x0D)
  #      buf = data.value
        

        
        try:
            ret = self.write(str(data)) 
          #  ret = self.write("r=1,crc=63902,$")
         #   print data1
  #          print self.calcByte( "r=1", INITIAL_DF1)
            if ret == False:
                raise Exception, "write failed"
        except:
            print "XBeeSerialTerminal: Error writing data:"
    
    
    def serial_send(self, data):
     #   print "XBeeSerialTerminal: Write Data: %s" % (data)
        #buf = data.value + chr(0x0D)
  #      buf = data.value
        
        data1 = data  + "crc=" + str(self.calcString(data, 0)) + ",$"
        
        try:
            ret = self.write(str(data1)) 
          #  ret = self.write("r=1,crc=63902,$")
         #   print data1
  #          print self.calcByte( "r=1", INITIAL_DF1)
            if ret == False:
                raise Exception, "write failed"
        except:
            print "XBeeSerialTerminal: Error writing data: %s" % (buf)

# internal setions & classes

