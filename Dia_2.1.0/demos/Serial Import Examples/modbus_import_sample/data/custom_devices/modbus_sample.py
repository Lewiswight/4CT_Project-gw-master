############################################################################
#                                                                          #
# Copyright (c)2008-2011, Digi International (Digi). All Rights Reserved.  #
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
Sample code for the Digi Connect SP, Digi Connect WAN and other products with
a serial port.

It polls a serial device for 1 data value, which is converted to a Dia data
channel. It issues a single fixed request, and expects a single dynamic
response. In this sample, the serial protocol used is Modbus/RTU, however the
user should be able to easily implement a new protocol of their choosing.

It assumes:
* you attach a Modbus/RTU serial slave to the serial port of the Digi product.
* that the Modbus/RTU slave address is 1.
* that the Modbus/RTU device supports holding register 4x00001.
* RS-232 or RS-485 must be set correctly in the Digi product
* the serial profile of the Digi product should be set to TCP Sockets

Settings:

    sample_rate_sec: the sample rate for polling in seconds, default = 60

    port: which serial port, numbers 1 to N, default = 1

    timeout; how many seconds to wait for a slave response, default = 1 sec

    baudrate: integer baud rate, such as 1200, 9600, 115200, default = 9600

    parity: in ['N', 'E', 'O'], default = 'N' or no parity

    trace: set True to display debug info, such as all data bytes sent,
           default = False

Channels:

    error: True/False; True if the device is not functioning as expected -
           probably means init failed or no responses are being received

    status: String in set ['unknown','active','stale','offline','exception']
      unknown = system has just started, or unexpected error, all data = 0
      active  = responses are arriving, data is valid
      stale   = last few responses did NOT arrive, data was valid, but is old
      offline = many responses did NOT arrive, data = 0 and is invalid
      exception = slave device is returning exception response, data is invalid

    data: Integer value of register 4x00001

Real-World example:
To help you understand how to 'port' this sample to your own Modbus device,
a complete alternative is embedded. If you set the constant MBUS_FIRST = False,
then it assumes a Veris H8035 or H8036 RS-485 meter is attached to the serial
port.  The channel named 'data' will NOT be created, instead these 2 channels
will be created:
* consumption: float of KWH, Energy Consumption from 4x00257/258, big-word first
* power: float of KW, Demand or Power from registers 4x00261/262, big-word first
"""

# imports
import struct
import traceback
import types
import time
import sys

# support running on both a Windows PC and Digi
if sys.platform.startswith('digi'):
    from lib.serial.serialdigi import *

else:
    from lib.serial.serialwin32 import *

from devices.device_base import DeviceBase
from devices.device_base import *
from settings.settings_base import SettingsBase, Setting
from channels.channel_source_device_property import *

import dia_extensions.common.modbus.crc16 as crc16

from dia_extensions.samples.annotated_sample import *


# constants
# set MBUS_FIRST = True to poll 1 register at 4x00001
# set MBUS_FIRST = False to poll 6 registers at 4x00257
MBUS_FIRST = True

MBUS_UNITID = 1
if MBUS_FIRST:
    # Modbus constants - register 4x00001 = offset 0
    MBUS_OFFSET = 0
    MBUS_COUNT = 1
else:
    # For the Veris H8035/H8036 Meter, 3 floats at 2 registers each
    MBUS_OFFSET = 256
    MBUS_COUNT = 6

# exception classes

# interface functions

# classes
class SerialPoller(DeviceBase, Serial):

    # first poll sent after these seconds - not sample_rate_sec setting
    # some delay tends to make your start-up cleaner
    INITIAL_POLL_SEC = 5.0

    # after 'X' missed responses, tag last data as stale
    # (Note: disable by setting to zero, which means never go stale)
    STALE_AFTER_MISSED = 3

    # after 'X' missed responses, clear data to 0 & go offline
    # (Note: disable by setting to zero, which means never go offline)
    OFFLINE_AFTER_MISSED = 10

    # when offline, poll more slowly, OFFLINE_BACK_OFF * sample_rate_sec
    # (Note: disable by setting to zero, which means no backoff)
    OFFLINE_BACK_OFF = 6

    # state information
    STATE_UNKNOWN = 0
    STATE_ACTIVE = 1
    STATE_STALE = 2
    STATE_OFFLINE = 3
    STATE_EXCEPTION = 4
    STATE_NAMES = ('unknown','active','stale','offline','exception')
    
    def __init__(self, name, core_services):
        self.__name = name
        self.__core = core_services

        ## Local State Variables:
        # hold our active/offline state
        self.__state = self.STATE_UNKNOWN

        # time and buffer for last request sent
        self.__last_request = 0
        self.__request_buffer = None
        # length is auto-adjusted when self.__request_buffer is formed
        self.__response_expected_length = None

        # time and buffer for last response seen
        self.__last_response = 0
        self.__response_buffer = None

        # hold our next scheduled time event
        self.__next_event = None

        ## Settings Table Definition:
        settings_list = [
            # how often to poll, defined as seconds
            Setting(
                name='sample_rate_sec', type=int, required=False,
                default_value=60),

            # which port to poll (1-based, so 1st port is 1)
            Setting(
                name='port', type=int, required=False,
                default_value=1),

            # slave timeout
            Setting(
                name='timeout', type=int, required=False,
                default_value=1),

            # baud rate, such as 2400, 9600, 115200 and so on
            Setting(
                name='baudrate', type=int, required=False,
                default_value=9600,
                verify_function=self.__verify_baudrate),

            # parity such as 'N' or 'none'            
            Setting(
                name='parity', type=str, required=False,
                default_value='none',
                verify_function=self.__verify_parity),

            # trace, set to False to 'quiet' the chattiness
            Setting(
                name='trace', type=bool, required=False,
                default_value=False),

        ]

        ## Channel Properties Definition:
        property_list = []

        # init ERROR channel
        sam = AnnotatedSample(Sample(0, True, 'not init'))
        sam.errors.add(ERSAM_NOT_INIT)
        property_list.append(ChannelSourceDeviceProperty(name='error',
                type=bool, initial=sam,
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP)
            )

        # init STATUS channel
        sam = AnnotatedSample(Sample(0,
                self.STATE_NAMES[self.STATE_UNKNOWN], 'not init'))
        sam.errors.add(ERSAM_NOT_INIT)
        property_list.append(ChannelSourceDeviceProperty(name='status',
                type=str, initial=sam,
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP)
            )

        if MBUS_FIRST:
            # init data channel, assume int from 4x00001
            sam = AnnotatedSample(Sample(0, 0, 'not init'))
            sam.errors.add(ERSAM_NOT_INIT)
            property_list.append(ChannelSourceDeviceProperty(name='data',
                    type=int, initial=sam,
                    perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP)
                )
        else:
            # else assume Veris H8035/H8036

            # KWH, Energy Consumption from 4x00257/258, big-word first
            sam = AnnotatedSample(Sample(0, 0.0, 'not init'))
            sam.errors.add(ERSAM_NOT_INIT)
            property_list.append(ChannelSourceDeviceProperty(name='consumption',
                    type=float, initial=sam,
                    perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP)
                )

            # KW, Demand or Power from registers 4x00261/262, big-word first
            sam = AnnotatedSample(Sample(0, 0.0, 'not init'))
            sam.errors.add(ERSAM_NOT_INIT)
            property_list.append(ChannelSourceDeviceProperty(name='power',
                    type=float, initial=sam,
                    perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP)
                )

        ## Initialize the DeviceBase interface:
        DeviceBase.__init__(self, self.__name, self.__core,
                                settings_list, property_list)

        return

    ## Functions which must be implemented to conform to the DeviceBase
    ## interface:

    def start(self):
        """Start the device driver.  Returns bool."""

        print '%s: Starting Device' % self.__name

        ## Initialize the serial interface:
        # pyserial expects ports base 0, not 1
        xport = SettingsBase.get_setting(self, "port") - 1
        xbaud = SettingsBase.get_setting(self, "baudrate")
        xpar = self.__derive_parity(SettingsBase.get_setting(self, "parity"))
        xtimout = SettingsBase.get_setting(self, "timeout")
        
        if sys.platform.startswith('digi'):
            msg = '//com//%d' % xport
        else: # is PC
            msg = 'COM%d' % (xport+1)
            
        print '%s: Opening serial port %s as %d,8,%s,1' % \
              (self.__name, msg, xbaud, xpar)

        Serial.__init__(self, port=xport, baudrate=xbaud, parity=xpar,
            timeout=xtimout)

        self.__sched = self.__core.get_service("scheduler")

        # Scheduling first request
        self.__schedule_poll_cycle(self.INITIAL_POLL_SEC)

        return True

    def stop(self):
        """Stop the device driver.  Returns bool."""

        print '%s: Stopping Device' % self.__name

        Serial.close(self)
        
        # cancel any out-standing events
        try:
            self.__sched.cancel(self.__next_event)
        except:
            pass

        self.__state = self.STATE_UNKNOWN
        self.__last_request = 0
        self.__request_buffer = None
        self.__response_buffer = None
        self.__next_event = None
            
        return True

    ## Locally defined functions:
    def next_poll_cycle(self):
        """Callback for our timed poll event.  This triggers the next
        poll of the attached device"""

        trace = SettingsBase.get_setting(self, "trace")

        self.__next_event = None

        if self.__request_buffer is None:
            # then recreate the request
            self.__make_request_buffer()

        # do we need to check for a failed serial port?

        self.__last_request = time.time()

        if trace:
            print_bytes('  request', self.__request_buffer)

        # clear any old data waiting in receive buffer
        self.flushInput()
        self.__response_buffer = None

        # send the request
        self.write(self.__request_buffer)

        # see if we have a response & reschedule next poll
        self.message_indication()

        return

    def __make_request_buffer(self):
        """Called to create the cached request buffer"""

        # this creates a list with a 6-byte binary string
        req = [chr(MBUS_UNITID) + '\x03' + \
            # for Modbus, words are big-endian 16-bit unsigned 'short'
                struct.pack('>H', MBUS_OFFSET) + \
                struct.pack('>H', MBUS_COUNT)]

        crc = crc16.calcString(req[0], 0xFFFF)
        # note: Modbus CRC16 travels as-if little-endian!
        req.append(struct.pack('<H', crc))
                   
        # Tutorial: The append/join method shown below is not important
        # for a one-time event with 2 strings, but is shown here because
        # repeatedly creating strings by concatenation puts a large load
        # upon data cleanup.
        #
        # So instead of:
        # x = 'abc'
        # x += 'cde'  (this creates a 2nd and 3rd string)
        # x += 'fgh'  (this creates a 4th and 5th string)
        # use the join method
        self.__request_buffer = "".join(req)

        # Modbus func 3 response is 5 bytes overhead plus data
        self.__response_expected_length = (MBUS_COUNT * 2) + 5

        return
    
    def __schedule_poll_cycle(self, delay=None):
        """Setup the callback event for the next poll cycle"""

        if delay is None:
            # none passed in, so use configured poll rate setting
            delay = SettingsBase.get_setting(self, "sample_rate_sec")

            if (self.__state == self.STATE_OFFLINE) and \
               (self.OFFLINE_BACK_OFF > 0):
                # then offline back-off, delay longer than normal
                delay = delay * self.OFFLINE_BACK_OFF
            
        print "%s: schedule next poll cycle in %d sec" % (self.__name, delay)

        # Cancel all/any pending request events waiting to run
        if self.__next_event is not None:
            try:
                self.__sched.cancel(self.__next_event)
            except:
                pass

        # Request a new event at our poll rate in the future.
        self.__next_event = self.__sched.schedule_after( \
                            delay, self.next_poll_cycle)
        return

    def message_indication(self, buf=None):
        """Received a response, process it"""

        trace = SettingsBase.get_setting(self, "trace")

        if buf is None:
            # then get response from serial port
            self.__response_buffer = self.read(self.__response_expected_length)
        else:
            # else assume our caller passed it in for us
            self.__response_buffer = buf

        now = time.time()

        if (self.__response_buffer is None) or \
           (len(self.__response_buffer) <= 0):
            # then no response, perhaps change to offline
            self.__handle_no_response(now)
            self.__schedule_poll_cycle()
            return

        # else we have something        
        self.__last_response = now

        if trace:
            print_bytes('  response', self.__response_buffer)

        if len(self.__response_buffer) <= 5:
            # then is Modbus exception response or garbage

            # set out status to exception responses
            self.set_status(self.STATE_EXCEPTION, None, self.__last_response)
            self.__schedule_poll_cycle()
            return
            
        # calc the expected CRC16 for response
        exp_crc = crc16.calcString(self.__response_buffer[:-2], 0xFFFF)
        see_crc = struct.unpack('<H', self.__response_buffer[-2:])[0]
        if exp_crc != see_crc:
            if trace:
                print 'S5: bad CRC, expected=0x%04X, saw=0x%04X' % \
                      (self.__name, exp_crc, see_crc)

            # set the errors, preserving the old data        
            self.__set_bad_data(None,'bad crc', self.__last_response)
            self.__schedule_poll_cycle()
            return

        try:
            if MBUS_FIRST:
                data = struct.unpack('>H', self.__response_buffer[3:5])
                # note that data is a list, so data[0] is our data
                
            else: # the two floats for Veris H8035/H8036, big-word first
                cons = struct.unpack('>f', self.__response_buffer[3:7])
                # we need to skip 4-bytes, registers 4x00259/260
                power = struct.unpack('>f', self.__response_buffer[11:15])
                data = [cons[0], power[0]] # repack as a list
                
            self.set_status(self.STATE_ACTIVE, data, self.__last_response)

        except:
            traceback.print_exc()
            self.set_status(self.STATE_EXCEPTION, None, self.__last_response)

        self.__schedule_poll_cycle()
        return

    def set_status(self, status, data, now=0):
        '''Update the status (& error) channel - if they changed

        status = int
        data = [] or None
        '''

        # fetch the old status
        status_old = self.property_get('status').value
        if status_old == status:
            # if no change, we just exit
            return

        if (status < self.STATE_UNKNOWN) or (status > self.STATE_EXCEPTION):
            #print 'trying to set bad status'
            raise ValueError, "Invalid state value %s" % status

        ## So we are changing state

        # now = 0 is okay, but if None, replace with time.time()
        if now is None:
            now = time.time()
            
        # then we are changing status
        self.__state = status
        self.property_set('status', \
                    Sample(now, self.STATE_NAMES[status]))

        # STATE_UNKNOWN = 0
        # STATE_ACTIVE = 1
        # STATE_STALE = 2
        # STATE_OFFLINE = 3
        # STATE_EXCEPTION = 4

        if status == self.STATE_ACTIVE:
            # the one GOOD state - every perfect
            error = False
            self.__set_good_data(data, now)

        elif status == self.STATE_STALE:
            # we leave data as is, but tag as doubtful
            error = True
            self.__set_bad_data(data, ERSAM_STALE_DATA, now)
            
        elif status == self.STATE_OFFLINE:
            # we leave data as is, but tag as doubtful
            error = True
            self.__set_bad_data(None, ERSAM_OFFLINE, now)
            
        else: # all others are bad/errors
            error = True
            self.__set_bad_data(None, ERSAM_BAD_DATA, now)

        if error != self.property_get('error').value:
            # then we are changing ERROR status
            self.property_set('error', Sample(now, error))
            
        return

    def __set_good_data(self, data, now):
        '''Generic good data seen, force status to ACTIVE'''

        if MBUS_FIRST:
            # we always print the good result
            print '%s: new data is %d (0x%04X) at %s' % \
                (self.__name, data[0], data[0], time.ctime())
            self.property_set('data', Sample(now, data[0], 'register'))
            
        else: # for Veris H8035/H8036 meter
            print '%s: new data, %0.2fKW, %dKWH at %s' % \
                (self.__name, data[1], int(data[0]), time.ctime())
            self.property_set('consumption', Sample(now, data[0], 'KWH'))
            self.property_set('power', Sample(now, data[1], 'KW'))

        return

    def __set_bad_data(self, data, msg, now):
        '''Generic bad data seen'''

        if MBUS_FIRST:
            if data is None:
                data = [0]
            self.__set_one_bad('data', data[0], msg, now)

        else:            
            if data is None:
                data = [0.0,0.0]
            self.__set_one_bad('consumption', data[0], msg, now)
            self.__set_one_bad('power', data[1], msg, now)
        return

    def __set_one_bad(self, tag, data, msg, now):
        if data is None:
            # then preserve the old value
            data = self.property_get(tag).value

        sam = AnnotatedSample(Sample(now, data, msg))
        sam.errors.add(ERSAM_BAD_DATA)
        self.property_set(tag, sam)
        return

    def __handle_no_response(self, now=0):
        '''We had no response, update our channels'''

        trace = SettingsBase.get_setting(self, "trace")

        # calc how many seconds since last response seen
        delta = now - self.__last_response
        rate = SettingsBase.get_setting(self, "sample_rate_sec")

        ## test if we are going offline due to this timeout
        if (self.OFFLINE_AFTER_MISSED > 0) and \
            ((self.OFFLINE_AFTER_MISSED * rate) < delta):
            # then go to offline state, force data to 0
            if trace:
                if self.__state != self.STATE_OFFLINE:
                    print '%s: going OFFLINE, clearing data' % (self.__name)
                else:
                    print '%s: no response, remain in OFFLINE state' % (self.__name)
                    
            self.set_status(self.STATE_OFFLINE, None, now)

        ## test if we are just stale - recently lost comms
        elif (self.STALE_AFTER_MISSED > 0) and \
           ((self.STALE_AFTER_MISSED * rate) < delta):
            # then go stale, but leave data unchanged
            if trace:
                if self.__state != self.STATE_STALE:
                    print '%s: going STALE, data unchanged' % (self.__name)
                else:
                    print '%s: no response, remain in STALE state' % (self.__name)
                    
            self.set_status(self.STATE_STALE, None, now)

        else:
            # just set an error, leave status = active
            if trace:
                print '%s: ignoring no response' % (self.__name)

            self.set_status(self.STATE_EXCEPTION, None, now)
            # leave status and channel data as is

        return

    def __verify_baudrate(self, baud):
        if baud > 300 and baud <= 921600:
            return
        raise ValueError, "Invalid baud rate '%s': The value must be above 300 and equal or less than 921600" % \
            (baud)

    def __verify_parity(self, parity):
        p = parity.lower()
        if p in ['none','n','even','e','odd','o']:
            return
        raise ValueError, "Invalid parity '%s': The value must be either \'none\', \'even\', \'odd\'"

    def __derive_parity(self, parity):
        parity = parity.upper()
        if parity == 'NONE':
            parity = 'N'
        elif parity == 'EVEN':
            parity = 'E'
        elif parity == 'ODD':
            parity = 'O'
        # else just leave as is
        return parity

# internal functions & classes
def print_bytes(szMsg, data, bNewLine=None):
    print show_bytes(szMsg,data,bNewLine)
    return

def show_bytes(szMsg, data, bNewLine=None):
    if(not data):
        st = "%s[None]" % szMsg
    else:
        if(bNewLine==None):
            bNewLine = (len(data)>32)
        st = "%s[%d]" % (szMsg, len(data))
        nOfs = 0
        for by in data:
            if(bNewLine and ((nOfs%32)==0)):
                st += '\n[%04d]:' % nOfs
            try:
                st += " %02X" % ord(by)
                nOfs += 1
            except:
                st += ',bad type=' + str(by)
                break
    return st

