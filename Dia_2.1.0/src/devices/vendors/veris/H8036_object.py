############################################################################
#                                                                          #
# Copyright (c)2008-2010, Digi International (Digi). All Rights Reserved.  #
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
The base Veris H8035/8036 object.

The various 'modes' define how much Modbus data it reads and how many channels
it manages.  Some are mutually exclusive, some can run in parallel:
- H8035 mode: only the basic 2 values (Watt-hours and Watts) are collected, other modes disabled.
- Default mode: all values collected, but no phase data (so current, but not current A/B/C)
- Phase Mode: adds in all of the phase data
- Statitics Mode: adds the last 3 min/max/avg values - workas with normal or phase mode

The 'phase' settings define if the phase data includes Phase A, A/B, or A/B/C 

VerisH8036.enable_channels([{list of terms}] defines the modes and other behavior.  You pass in 
a list of terms such as ['phase', 'split', 'minmax'] to define a 2-phase system with all phase A/B
data and the min/max/avg data.  The terms are not case sensitive, but are processed in order so 
a list of terms like ['two', 'three'] leave the object in 3-phase mode.

Valid terms:
* 'one' or 'single' = if 'phase' is true, shows only Phase A data
* 'two' or 'split' = if 'phase' is true, shows only Phase A and Phase B data
* 'three' = if 'phase' is true, shows all Phase A, Phase B and Phase C data
* 'phase' = adds support for the phase data as selected by 'one', 'two' or 'three'
* 'minmax' or 'statistics' = add the min/max/avg data from the meter
* 'model' = saves the meter Slave ID response, else it is checked but discarded
* 'h8035' = forces H8035 support, meter Slave ID is NOT checked, assumes min Modbus data
* 'h8036' = assumes H8036 support, but meter Slave ID is collected & may over-ride
* 'import' or 'export' = changes the name of total energy between 'M_Imported' and 'M_Exported'
* 'default' = ['three', 'h8036', /import'], which means 3-phase normal (no phase data, 
              no min/max/avg, total energy is called 'M_Imported')
              
Other notes:
* in two/split phase mode, the driver uses the phase data to repair the 'M_AC_Voltage_LL' and 
  'M_AC_Voltage_LN' data, which will be only 2/3 the correct value (H8036 assumes 3-phase)
  so 'M_AC_Voltage_LL' will be set to equal 'M_AC_Voltage_AB', and 'M_AC_Voltage_LN' will be
  set to equal the average of 'M_AC_Voltage_AN' and 'M_AC_Voltage_BN'
  
"""

# imports
import struct
import traceback
import types
import digitime

import crc16  # modbus CRC16

# constants

# exception classes

# interface functions

# classes
class VerisH8036(object):

    # Channel names
    ID_TIMESTAMP = 0
    ID_MODEL_DID = 1
    ID_ENERGY = 2
    # ID_ENERGY_KWH_OUT = 3
    ID_POWER = 3
    ID_REACTIVE_POWER = 4
    ID_APPARENT_POWER = 5
    ID_POWER_FACTOR = 6
    ID_VOLTAGE_LL = 7
    ID_VOLTAGE_LN = 8
    ID_CURRENT_AMP = 9
    ID_POWER_A = 10
    ID_POWER_B = 11
    ID_POWER_C = 12
    ID_POWER_FACTOR_A = 13
    ID_POWER_FACTOR_B = 14
    ID_POWER_FACTOR_C = 15
    ID_VOLTAGE_AB = 16
    ID_VOLTAGE_BC = 17
    ID_VOLTAGE_CA = 18
    ID_VOLTAGE_AN = 19
    ID_VOLTAGE_BN = 20
    ID_VOLTAGE_CN = 21
    ID_CURRENT_A = 22
    ID_CURRENT_B = 23
    ID_CURRENT_C = 24
    ID_POWER_AVG = 25
    ID_POWER_MIN = 26
    ID_POWER_MAX = 27

    CHAN_INFO_ID = 0
    CHAN_INFO_NAME = 1
    CHAN_INFO_OFS = 2
    CHAN_INFO_UNITS = 3
    CHAN_INFO_FORMAT = 4
    CHAN_INFO_STRUCT = 5
    CHAN_INFO_DESC = 6
    
    CHAN_INFO = (
       (ID_TIMESTAMP,           't',                None, None, "%d",   None,   "Data Time Stamp",      ),
       (ID_MODEL_DID,           'm',                None, None, "%d",   None,   "SunSpec Model Id",     ),
       
       (ID_ENERGY,              'M_Imported',       3,  "Watt-hours","%d",'>f', "Energy Comsumption",   ),
       (ID_POWER,               'M_AC_Power',       11, "Watts","%4d",  '>f',   "Power (Demand)",       ),
       (ID_REACTIVE_POWER,      'M_AC_VAR',         15, "VAR",  "%4d",  '>f',   "Reactive Power",       ),
       (ID_APPARENT_POWER,      'M_AC_VA',          19, "Volt-Amps","%4d",'>f', "Apparent Power",       ),
       (ID_POWER_FACTOR,        'M_AC_PF',          23, "%",    "%0.2f",'>f',   "Power Factor",         ),
       (ID_VOLTAGE_LL,          'M_AC_Voltage_LL',  27, "Volts","%4d",  '>f',   "Voltage Line-to-Line", ),
       (ID_VOLTAGE_LN,          'M_AC_Voltage_LN',  31, "Volts","%4d",  '>f',   "Voltage Line-to-Neutral", ),
       (ID_CURRENT_AMP,         'M_AC_Current',     35, "Amps", "%0.2f",'>f',   "Current",              ),

       (ID_POWER_A,             'M_AC_Power_A',     39, "Watts","%4d",  '>f',   "Power (Demand) Phase A", ),
       (ID_POWER_B,             'M_AC_Power_B',     43, "Watts","%4d",  '>f',   "Power (Demand) Phase B", ),
       (ID_POWER_C,             'M_AC_Power_C',     47, "Watts","%4d",  '>f',   "Power (Demand) Phase C", ),
       
       (ID_POWER_FACTOR_A,      'M_AC_PF_A',        51, "%",    "%0.2f",'>f',   "Power Factor Phase A", ),
       (ID_POWER_FACTOR_B,      'M_AC_PF_B',        55, "%",    "%0.2f",'>f',   "Power Factor Phase B", ),
       (ID_POWER_FACTOR_C,      'M_AC_PF_C',        59, "%",    "%0.2f",'>f',   "Power Factor Phase C", ),

       (ID_VOLTAGE_AB,          'M_AC_Voltage_AB',  63, "Volts","%4d",  '>f',   "Voltage Phase A to B", ),
       (ID_VOLTAGE_BC,          'M_AC_Voltage_BC',  67, "Volts","%4d",  '>f',   "Voltage Phase B to C", ),
       (ID_VOLTAGE_CA,          'M_AC_Voltage_CA',  71, "Volts","%4d",  '>f',   "Voltage Phase C to A", ),

       (ID_VOLTAGE_AN,          'M_AC_Voltage_AN',  75, "Volts","%4d",  '>f',   "Voltage Phase A to Neutral", ),
       (ID_VOLTAGE_BN,          'M_AC_Voltage_BN',  79, "Volts","%4d",  '>f',   "Voltage Phase B to Neutral", ),
       (ID_VOLTAGE_CN,          'M_AC_Voltage_CN',  83, "Volts","%4d",  '>f',   "Voltage Phase C to Neutral", ),
       
       (ID_CURRENT_A,           'M_AC_Current_A',   87, "Amps", "%0.2f",'>f',   "Current Phase A",      ),
       (ID_CURRENT_B,           'M_AC_Current_B',   91, "Amps", "%0.2f",'>f',   "Current Phase B",      ),
       (ID_CURRENT_C,           'M_AC_Current_C',   95, "Amps", "%0.2f",'>f',   "Current Phase C",      ),

       (ID_POWER_AVG,           'M_AC_Power_Average',  99, "Watts", "%4d", None, "Average Demand",      ),
       (ID_POWER_MIN,           'M_AC_Power_Minimum', 103, "Watts", "%4d", None, "Minimum Demand",      ),
       (ID_POWER_MAX,           'M_AC_Power_Maximum', 107, "Watts", "%4d", None, "Maximum Demand",      ),

    )

    CHAN_SUNSPEC_LIST = (ID_ENERGY, ID_POWER, ID_REACTIVE_POWER, ID_APPARENT_POWER, 
        ID_POWER_FACTOR, ID_VOLTAGE_LL, ID_VOLTAGE_LN, ID_CURRENT_AMP, ID_POWER_A, ID_POWER_B, 
        ID_POWER_C, ID_POWER_FACTOR_A, ID_POWER_FACTOR_B, ID_POWER_FACTOR_C, ID_VOLTAGE_AB, 
        ID_VOLTAGE_BC, ID_VOLTAGE_CA, ID_VOLTAGE_AN, ID_VOLTAGE_BN, ID_VOLTAGE_CN, ID_CURRENT_A, 
        ID_CURRENT_B, ID_CURRENT_C,
    )

    # Enable Channel Bits, use with self._chn_enabled
    ENB_CHN_SPLIT           = 0x00001 # Phase A and B Only (no C)
    ENB_CHN_THREE           = 0x00002 # Phase A/B/C
    ENB_CHN_NORMAL           = 0x00004 # More than Minimum
    ENB_CHN_PHASES          = 0x00008 # add the phase A/B/C channels
    ENB_CHN_AVGMINMAX       = 0x00010 # add the min/max/avg channels
    ENB_CHN_MODEL           = 0x00020 # add the Model channel

    ENB_CHN_DEFAULTS = ENB_CHN_THREE | ENB_CHN_NORMAL

    def __init__(self, name=None):

        ## local variables
        self.name = name
        self.__8035 = False
        self._model_str = "Unknown"
        self._model_sunspec = None
        self._last_timestamp = 0
        self.__import = True

        # Modbus values and cached Modbus requests
        self._addr = 1
        self._mbtcp = True
        self._seqno = 1
        self.__req_slaveid = None
        self.__req_data = None

        self._trace = True
        self.enable_channels('def')
        self.clear_data()

        return

    def get_name(self):
        return self.__name

    def enable_channels(self, chn_lst):

        if isinstance(chn_lst, types.StringType):
            chn_lst = [chn_lst]

        for chan in chn_lst:
            chn = chan.lower()
            if chn in ('def', 'default', 'defaults'):
                # restore defaults
                if self._trace: print "enable_channels('Defaults')"
                self._chn_enabled = self.ENB_CHN_DEFAULTS
                self.__8035 = False
                self.__import = True

            if chn in ('1', 'one', 'single'):
                # enable SINGLE form, disable 2 and 3-phase
                if self._trace: print "enable_channels('1-Phase')"
                self._chn_enabled &= ~(self.ENB_CHN_SPLIT | self.ENB_CHN_THREE)

            if chn in ('2', 'two', 'split'):
                # enable SPLIT form, disable 3-phase
                if self._trace: print "enable_channels('2-Phase')"
                self._chn_enabled |= self.ENB_CHN_SPLIT
                self._chn_enabled &= ~self.ENB_CHN_THREE

            if chn in ('3', 'three'):
                # enable 3-PHASE form, disable Split/2-phase
                if self._trace: print "enable_channels('3-Phase')"
                self._chn_enabled |= self.ENB_CHN_THREE
                self._chn_enabled &= ~self.ENB_CHN_SPLIT

            if chn in ('phase'):
                # enable the phase data
                if self._trace: print "enable_channels('Phase Data')"
                self._chn_enabled |= (self.ENB_CHN_PHASES | self.ENB_CHN_NORMAL)

            if chn in ('stats','minmax','statistics'):
                # enable the min/max/avg data
                if self._trace: print "enable_channels('MinMax')"
                self._chn_enabled |= self.ENB_CHN_AVGMINMAX

            if chn in ('model'):
                # enable the phase data
                if self._trace: print "enable_channels('Model')"
                self._chn_enabled |= self.ENB_CHN_MODEL

            if chn in ('h8035', '8035'):
                # demote to H8035 channels
                if self._trace: print "enable_channels('H8035')"
                self.__8035 = True
                self._chn_enabled &= ~(self.ENB_CHN_THREE | self.ENB_CHN_SPLIT)

            if chn in ('h8036', '8036'):
                # promote to H8036 channels
                if self._trace: print "enable_channels('H8036')"
                self.__8035 = False

            if chn in ('import'):
                # tag energy as M__imported
                if self._trace: print "enable_channels('import')"
                self.__import = True
                
            if chn in ('export'):
                # tag energy as M_Exported
                if self._trace: print "enable_channels('export')"
                self.__import = False
        return

    def get_channel_id_list(self):
        '''Based on the channel config, return a list of valid channel ids'''

        # first 2 always exist
        lst = [self.ID_ENERGY, self.ID_POWER]

        if not self.__8035:
            #these 2 always exist on the H8036
            lst.extend([self.ID_VOLTAGE_LN, self.ID_CURRENT_AMP])
            
            if self._chn_enabled & self.ENB_CHN_NORMAL:
                lst.extend([self.ID_REACTIVE_POWER, self.ID_APPARENT_POWER, 
                            self.ID_POWER_FACTOR, self.ID_VOLTAGE_LL])
                            
            if self._chn_enabled & self.ENB_CHN_PHASES:
                # add the phases - start with first Phase
                lst.extend([self.ID_POWER_A, self.ID_POWER_FACTOR_A, self.ID_VOLTAGE_AN,
                            self.ID_CURRENT_A]) 
                            
                if self._chn_enabled & (self.ENB_CHN_SPLIT | self.ENB_CHN_THREE):
                    # add the Second Phase
                    lst.extend([self.ID_POWER_B, self.ID_POWER_FACTOR_B, self.ID_VOLTAGE_AB, 
                                self.ID_VOLTAGE_BN, self.ID_CURRENT_B]) 
                    
                    if self._chn_enabled & self.ENB_CHN_THREE:
                        # add the Third Phase
                        lst.extend([self.ID_POWER_C, self.ID_POWER_FACTOR_C, self.ID_CURRENT_C, 
                                    self.ID_VOLTAGE_BC, self.ID_VOLTAGE_CA, self.ID_VOLTAGE_CN])
                    
        if self._chn_enabled & self.ENB_CHN_AVGMINMAX:
            # the add the min/max/avg channels
            lst.extend([self.ID_POWER_AVG, self.ID_POWER_MIN, self.ID_POWER_MAX])
            
        return lst

    def get_channel_name_list(self):
        '''Based on the channel config, return a list of valid channel names'''
        
        id_list = self.get_channel_id_list()
        names = []

        for id in id_list:
            if (id == self.ID_ENERGY) and not self.__import:
                # special for import/export
                names.append('M_Exported')
            else: # standard names
                names.append(self.CHAN_INFO[id][self.CHAN_INFO_NAME])

        return names
        
    def set_ModbusAddress(self, val=1):
        self._addr = val

    def set_ModbusTcp(self, val=True):
        self._mbtcp = val

    def set_ModbusRtu(self, val=False):
        self._mbtcp = val

    def get_data_request(self, seq_str=None):
        # if self._trace: print "get_data_request"
        
        if self.__req_data is None:
            req = chr(self._addr) + '\x03\x01\x00\x00'
            if  self.__8035:
                # then short request
                req += chr(6)

            elif self._chn_enabled & self.ENB_CHN_AVGMINMAX:
                # get all - even last 3 floats for avg/min/max
                req += chr(54)

            elif self._chn_enabled & (self.ENB_CHN_PHASES | self.ENB_CHN_SPLIT):
                # get up to last of phase data, no avg/min/max
                # note for split phase we need phase data to 'repair' the Volt_LL and LN values
                req += chr(48)

            else:
                # get up to Current, none of the phase data
                req += chr(18)

            if self._mbtcp:
                # we save missing the two bytes
                req = '\x00\x00\x00\x06' + req
            else:
                crc = crc16.calcString(req)
                req += chr(crc & 0xFF) + chr((crc >> 8) & 0xFF)
            self.__req_data = req
            
        if self._mbtcp:
            if seq_str is None:
                self.__last_seq = chr(self.get_next_seqno()) + '\x00'
            else:
                self.__last_seq = seq_str[:2]
            return self.__last_seq + self.__req_data
            
        else: # is modbus/RTU
            return self.__req_data

    def get_slave_id_request(self, mbtcp=True):
        if self._trace: print "get_slave_id_request"
        if self.__req_slaveid is None:
            # then refresh cache
            req = chr(self._addr) + '\x11'
            if self._mbtcp:
                req = chr(self.get_next_seqno()) + '\x00\x00\x00\x00\x02' + req
            else:
                crc = crc16.calcString(req)
                req += chr(crc & 0xFF) + chr((crc >> 8) & 0xFF)
            self.__req_slaveid = req
        return self.__req_slaveid

    def get_next_seqno(self):
        if self._seqno == 99:
            self._seqno = 1
        else:
            self._seqno += 1
        return self._seqno

    ## process the indications received
    def import_binary(self, buf):
        if self._trace: print "import_binary"

        # confirm the basic form of the packet
        if self._mbtcp:
            # confirm basic Modbus/TCP
            if len(buf) < 8:
                return { 'error':
                    'Error: Bad MB/TCP length, too short, was only %d bytes, need 8 or more' % \
                    len(buf) }
                    
            # check the sequence number
            if self.__last_seq != buf[:2]:
                return { 'error':
                    'Error: Bad MB/TCP seq no' }

            if buf[2:5] != '\x00\x00\x00':
                return { 'error':
                    'Error: Bad MB/TCP header zeros' }

            x = ord(buf[5])
            if x != (len(buf) - 6):
                return { 'error':
                    'Error: Bad MB/TCP header - len=%d does not match buffer len()=%d' % \
                        (x, (len(buf) - 6))}

            buf = buf[6:] # normalize to PDU only, remove header

        else:
            # confirm basic Modbus/RTU
            if len(buf) < 5:
                return { 'error':
                    'Error: Bad MB/RTU length, too short, was only %d bytes' % \
                    len(buf) }

            crcCalc = crc16.calcString(buf[:-2])
            crcRecv = ord(buf[-2]) + (ord(buf[-1]) * 256)

            if crcCalc != crcRecv:
                return { 'error':
                    'Error: Bad MB/RTU CRC16' }

            buf = buf[:-2] # normalize to PDU only, remove CRC16

        # we now have the response, which will be:
        # - an error/exception
        # - slave_id response
        # - reg response of 3 floats
        # - reg response of 26 floats

        x = ord(buf[0])
        if x != self._addr:
            return { 'error': 'Error: Bad Modbus Unit Id/Slave Address' }

        fnc = ord(buf[1])
        if fnc & 0x80:
            x = ord(buf[2])
            return { 'error': 'Error: Exception Response, code:%d' % x}

        # all of our good responses have byte-count in 3rd byte
        x = ord(buf[2])
        if x != (len(buf) - 3):
            return { 'error': 'Error: byte count of %d incorrect' % x}

        if fnc == 0x11:
            # then slave id response
            return self.import_slave_id(buf)

        elif fnc == 0x03:
            # then reg response
            self._last_timestamp = digitime.time()
            if self.__8035:
                return self.import_8035(buf)
            else:
                return self.import_8036(buf)

        else:
            return { 'error': 'Error: unexpected function code %d in response' % fnc }

    def import_slave_id(self, buf):
        if self._trace: print "import_slave_id"

        # buf[0] = slave id
        # buf[1] = 0x11
        # buf[2] = byte count
        # buf[3] = 'slave id', which is vendor specific
        # buf[4] = run status, 0x00 = Off, 0xFF = On
        # buf[5:] = model string

        self._running = bool(buf[4] == '\xFF')
        self._model_str = buf[5:]

        if self.__8035:
            # if this is true, we ignore model and act like 8035
            pass

        else: # we use model string to detect
            self.__8035 = self._model_str.find('8035')

        if not self.ENB_CHN_MODEL:
            # then we do NOT want a model channel
            self._model_str = None

        return { 'error': None }

    def import_8035(self, buf):
        if self._trace: print "import_8035"

        # buf[0] = slave id
        # buf[1] = 0x11
        # buf[2] = byte count
        # buf[3] = first reg upper
        # buf[4] = first reg upper

        if len(buf) < 15:
            return { 'error': 'Error: length of H8035 response wrong' }

        self.clear_data()
        self.import_base(buf)
        return { 'error': None }

    def import_base(self, buf):

        (self._data[self.ID_ENERGY], dummy, self._data[self.ID_POWER]) = \
                struct.unpack('>fff', buf[3:15])

        # convert kilo-watt to watt
        self._data[self.ID_ENERGY] *= 1000.0
        self._data[self.ID_POWER] *= 1000.0
                
        return
        
    def import_8036(self, buf):
        if self._trace: print "import_8036, len(buf) = %d, enb_chn=0x%02X" % (len(buf), self._chn_enabled)

        # buf[0] = slave id
        # buf[1] = 0x11
        # buf[2] = byte count
        # buf[3] = first reg upper
        # buf[4] = first reg upper

        if len(buf) < 40:
            return { 'error': 'Error: length %d of H8036 response wrong' % len(buf) }

        self.clear_data()

        # we always do the 2 basic channels
        self.import_base(buf)

        # plus the 'other' basics
        (self._data[self.ID_VOLTAGE_LN], self._data[self.ID_CURRENT_AMP]) = \
            struct.unpack('>ff', buf[31:39])

        if self._chn_enabled & self.ENB_CHN_NORMAL:
            (self._data[self.ID_REACTIVE_POWER], self._data[self.ID_APPARENT_POWER], \
             self._data[self.ID_POWER_FACTOR], self._data[self.ID_VOLTAGE_LL]) = \
             struct.unpack('>ffff', buf[15:31])
            self._data[self.ID_REACTIVE_POWER] *= 1000.0
            self._data[self.ID_APPARENT_POWER] *= 1000.0

            if self._chn_enabled & self.ENB_CHN_PHASES:
                if self._chn_enabled & (self.ENB_CHN_SPLIT | self.ENB_CHN_THREE):
                    if len(buf) >= 51:
                        (self._data[self.ID_POWER_A], self._data[self.ID_POWER_B], \
                         self._data[self.ID_POWER_C]) = struct.unpack('>fff', buf[39:51])
                        # convert kilo-watt to watt
                        self._data[self.ID_POWER_A] *= 1000.0
                        self._data[self.ID_POWER_B] *= 1000.0
                        self._data[self.ID_POWER_C] *= 1000.0

                    if len(buf) >= 63:
                        (self._data[self.ID_POWER_FACTOR_A], self._data[self.ID_POWER_FACTOR_B], \
                         self._data[self.ID_POWER_FACTOR_C]) = struct.unpack('>fff', buf[51:63])

                    if len(buf) >= 75:
                        (self._data[self.ID_VOLTAGE_AB], self._data[self.ID_VOLTAGE_BC], \
                         self._data[self.ID_VOLTAGE_CA]) = struct.unpack('>fff', buf[63:75])

                    if len(buf) >= 87:
                        (self._data[self.ID_VOLTAGE_AN], self._data[self.ID_VOLTAGE_BN], \
                         self._data[self.ID_VOLTAGE_CN]) = struct.unpack('>fff', buf[75:87])

                    if len(buf) >= 99:
                        (self._data[self.ID_CURRENT_A], self._data[self.ID_CURRENT_B], \
                         self._data[self.ID_CURRENT_C]) = struct.unpack('>fff', buf[87:99])

                if not self._chn_enabled & self.ENB_CHN_THREE:
                    self._data[self.ID_POWER_C] = None
                    self._data[self.ID_POWER_FACTOR_C] = None
                    self._data[self.ID_VOLTAGE_BC] = None
                    self._data[self.ID_VOLTAGE_CA] = None
                    self._data[self.ID_VOLTAGE_CN] = None
                    self._data[self.ID_CURRENT_C] = None

            if (self._chn_enabled & self.ENB_CHN_SPLIT):
                # repair the 2-phase miscalc without the third phase - use avg of volt_an and volt_bn
                if self._trace: print 'repair split phase LN and LL'
                x = [self._data[self.ID_VOLTAGE_AN], self._data[self.ID_VOLTAGE_BN]]
                if (x[0] is None) or (x[1] is None):
                    x = struct.unpack('>ff', buf[75:83])
                self._data[self.ID_VOLTAGE_LN] = (x[0] + x[1]) / 2.0
                    
                # avoid 2-phase miscalc without third phase - use volt_ab
                if self._data[self.ID_VOLTAGE_AB] is not None:
                    self._data[self.ID_VOLTAGE_LL] = self._data[self.ID_VOLTAGE_AB]
                else:
                    self._data[self.ID_VOLTAGE_LL] = struct.unpack('>f', buf[63:67])[0]
            
        if (self._chn_enabled & self.ENB_CHN_AVGMINMAX) and len(buf) >= 111:
            (self._data[self.ID_POWER_AVG], self._data[self.ID_POWER_MIN], self._data[self.ID_POWER_MAX]) = \
                struct.unpack('>fff', buf[99:111])
            # convert KW to W
            self._data[self.ID_POWER_AVG] *= 1000.0
            self._data[self.ID_POWER_MIN] *= 1000.0
            self._data[self.ID_POWER_MAX] *= 1000.0

        return { 'error': None }

    def clear_data(self):
        if  self.__8035:
            # then only first 2 data items
            self._data = [None] * (self.ID_POWER  + 1)

        elif self._chn_enabled & self.ENB_CHN_AVGMINMAX:
            # then we need all
            self._data = [None] * (self.ID_POWER_MAX + 1)

        elif self._chn_enabled & self.ENB_CHN_PHASES:
            # get up to last of phase data, no avg/min/max
            self._data = [None] * (self.ID_CURRENT_C + 1)

        else:
            # get up to Current, none of the phase data
            self._data = [None] * (self.ID_CURRENT_AMP + 1)

        # print 'clear', self._data
            
        return

    def report_text(self, nulls=False):
        st = []

        if self.__import:
            msg = '%20s = ' % 'M_Imported'
        else:
            msg = '%20s = ' % 'M_Exported'
        if self._data[self.ID_ENERGY] is not None:
            st.append('%s%d Watt-hours' % (msg, self._data[self.ID_ENERGY]))
        elif nulls:
            st.append('%sNone' % msg)
            
        id = self.ID_POWER
        while (id <= self.ID_POWER_MAX) and (id < len(self._data)):
            msg = '\n%20s = ' % self.CHAN_INFO[id][self.CHAN_INFO_NAME]
            if self._data[id] is not None:
                dat = self.CHAN_INFO[id][self.CHAN_INFO_FORMAT] % self._data[id]
                st.append('%s%s %s' % (msg, dat, self.CHAN_INFO[id][self.CHAN_INFO_UNITS]))
            elif nulls:
                st.append('%sNone' % msg)
            id += 1

    # CHAN_INFO_ID, CHAN_INFO_NAME, CHAN_INFO_OFS, CHAN_INFO_UNITS, CHAN_INFO_FORMAT, CHAN_INFO_STRUCT, CHAN_INFO_DESC
    # CHAN_INFO = (
    #  (ID_ENERGY_KWH_IN,       'M__imported',       3,  "KWH",  "%d",   '>f',   "Energy Comsumption",   ),
            
        st.append('\n')

        return "".join(st)

    def report_SunSpec(self):

        # start with model and ISO time-stamp
        if self._last_timestamp == 0:
            # then no data yet!
            return []

        if self._model_sunspec is not None:
            m = self._model_sunspec

        else: # guess
            if self._chn_enabled & self.ENB_CHN_SPLIT:
                m = 202
            elif self._chn_enabled & self.ENB_CHN_THREE:
                m = 203
            else:
                m = 201

        tm_utc = digitime.gmtime(self._last_timestamp)
        st = [ ('m',m), ('t', digitime.strftime("%Y-%m-%dT%H:%M:%SZ", tm_utc)) ]

        for id in self.CHAN_SUNSPEC_LIST:
            if (id < len(self._data)) and (self._data[id] is not None):
                if not self.__import and (id == self.ID_ENERGY):
                    st.append(('M_Export', self._data[id], \
                               self.CHAN_INFO[id][self.CHAN_INFO_UNITS]))
                else:
                    st.append((self.CHAN_INFO[id][self.CHAN_INFO_NAME], self._data[id], \
                               self.CHAN_INFO[id][self.CHAN_INFO_UNITS]))

        return st
