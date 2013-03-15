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
The base ECM object
"""

# imports

# constants

# exception classes

# interface functions

# classes
class ECM1240(object):

    # Channel names
    CHN_CURRENT_AMP = 'M_AC_Current'
    CHN_POWER_W = 'M_AC_Power'
    CHN_ENERGY_WH = 'M_Imported'
    CHN_VOLTAGE = 'M_AC_Voltage'
    CHN_EVENTS = 'M_Events'
    CHN_INDEX_LABEL = ('CH1', 'CH2', 'AUX1', 'AUX2', 'AUX3', 'AUX4', 'AUX5')

    # Enable Channel Bits, use with self._chn_enabled
    ENB_CHN_ABSWATT_CH1     = 0x00001
    ENB_CHN_ABSWATT_CH2     = 0x00002
    ENB_CHN_POLWATT_CH1     = 0x00004
    ENB_CHN_POLWATT_CH2     = 0x00008
    ENB_CHN_WATT_CH1        = 0x00005
    ENB_CHN_WATT_CH2        = 0x0000A
    ENB_CHN_VOLTAGE         = 0x00010
    ENB_CHN_SERIAL_NO       = 0x00020
    ENB_CHN_FLAGS           = 0x00040
    ENB_CHN_UNIT_ID         = 0x00080
    ENB_CHN_CURRENT_CH1     = 0x00100
    ENB_CHN_CURRENT_CH2     = 0x00200
    ENB_CHN_SECONDS         = 0x00400
    ENB_CHN_WATT_AUX1       = 0x00800
    ENB_CHN_WATT_AUX2       = 0x01000
    ENB_CHN_WATT_AUX3       = 0x02000
    ENB_CHN_WATT_AUX4       = 0x04000
    ENB_CHN_WATT_AUX5       = 0x08000
    ENB_CHN_DC_INPUT        = 0x10000

    ENB_CHN_DEFAULTS = ENB_CHN_ABSWATT_CH1 + ENB_CHN_ABSWATT_CH2 + ENB_CHN_VOLTAGE + \
        ENB_CHN_CURRENT_CH1 + ENB_CHN_CURRENT_CH2

    CHN_ENABLED_INDEXES = (ENB_CHN_WATT_CH1, ENB_CHN_WATT_CH2, ENB_CHN_WATT_AUX1, \
        ENB_CHN_WATT_AUX2, ENB_CHN_WATT_AUX3, ENB_CHN_WATT_AUX4, ENB_CHN_WATT_AUX5)

    def __init__(self, name=None):

        ## local variables
        self.__binary = True
        self.__model = 1240
        self.__use_polarized = [False, False]
        self.__load_channel_names()
        self.__voltage_adjust = 0.906

        self._chn_enabled = self.ENB_CHN_DEFAULTS
        self._single_channel = False

        self.__seconds = 0
        self.__last_seconds = 0
        self.__wattsec = [None,None,None,None,None,None,None]

        self._voltage = 0
        self._current = [None,None]
        self._power = [None,None,None,None,None,None,None]
        self._kwh = [None,None,None,None,None,None,None]

        self.trace = True

        return

    def get_name(self):
        return self.__name

    def set_enabled_channels(self, chns):
        self._chn_enabled = chns

    def set_ac_voltage_adjust(self, adj):
        self.__voltage_adjust = adj

    ## process the indications received
    def import_binary(self, buf):

        # confirm the basic form of the packet
        if len(buf) != 65:
            return { 'error':
                'Error: Bad length, should be 65 bytes, was only %d bytes' % \
                len(buf) }

        if (buf[:2] != '\xFE\xFF'):
            return { 'error':
                'Error: Bad form - missing the starting header' }

        if (buf[-3:-1] != '\xFF\xFE'):
            return { 'error':
                'Error: Bad form - missing the ending trailer' }

        bcc = 0
        for by in buf[:-1]:
            bcc += ord(by)
        bcc &= 0xFF
        # print 'bcc is 0x%02X' % bcc
        if bcc != ord(buf[-1]):
            return { 'error':
                'Error: Bad BCC' }

        if buf[2] == '\x01':
            if self.__model != 1220:
                print "Warning: changing to Model 1220"
            self.__model = 1220
        else:
            if self.__model != 1240:
                print "Warning: changing to Model 1240"
            self.__model = 1240

        # add the seconds counter - little-endian 3-byte
        self.__seconds = self.str_to_le24(buf[37:40])
        delta_sec = float(self.__seconds - self.__last_seconds)

		# extract the voltage - big-endian (?)
        if self._chn_enabled & self.ENB_CHN_VOLTAGE:
            self._voltage = (self.str_to_be16(buf[3:5]) / 10.0) * \
                              self.__voltage_adjust
            if self.trace:
                st = 'Voltage: %0.1fVAC' % self._voltage
        else:
            self._voltage = None

        if self.trace:
            print 'Seconds:%d (delta:%d) %s' % (self.__seconds, delta_sec, st)

        # add the CH1 & Ch2 Watt Counters - little-endian 5-byte
        if self._chn_enabled & self.ENB_CHN_WATT_CH1:
            # we ignore: ENB_CHN_CURRENT_CH1 and always do
            self._current[0] = self.str_to_le16(buf[33:35]) / 100.0

            if self.__use_polarized[0]:
                wattsec = self.str_to_le40(buf[15:20])
            else:
                wattsec = self.str_to_le40(buf[5:10])
            self.calc_power_energy(0, wattsec, delta_sec)

        if self._chn_enabled & self.ENB_CHN_WATT_CH2:
            # we ignore: ENB_CHN_CURRENT_CH2 and always do
            self._current[1] = self.str_to_le16(buf[35:37]) / 100.0

            if self.__use_polarized[1]:
                wattsec = self.str_to_le40(buf[20:25])
            else:
                wattsec = self.str_to_le40(buf[10:15])
            self.calc_power_energy(1, wattsec, delta_sec)

        # reserved bytes
        # buf[25:29]

        # add the serial_number
        if self._chn_enabled & (self.ENB_CHN_SERIAL_NO | self.ENB_CHN_FLAGS | \
                                 self.ENB_CHN_UNIT_ID):

            self.__serial_number = self.str_to_le16(buf[29:31])
            self.__flags = ord(buf[31])
            self.__unit_id = ord(buf[32])

            if self.trace:
                print 'serial: %d, flags:0x%02X Unit_Id:%d' % \
                   (self.__serial_number, self.__flags, self.__unit_id)
        else:
            self.__serial_number = None
            self.__flags = None
            self.__unit_id = None

        if self.__model == 1220:
            # then shortened form
            pass

        else: # is long form

            # add the AUX watt-seconds - little-endian 4-byte
            if self._chn_enabled & self.ENB_CHN_WATT_AUX1:
                self.calc_power_energy(2, self.str_to_le32(buf[40:44]), delta_sec)

            if self._chn_enabled & self.ENB_CHN_WATT_AUX2:
                self.calc_power_energy(3, self.str_to_le32(buf[44:48]), delta_sec)

            if self._chn_enabled & self.ENB_CHN_WATT_AUX3:
                self.calc_power_energy(4, self.str_to_le32(buf[48:52]), delta_sec)

            if self._chn_enabled & self.ENB_CHN_WATT_AUX4:
                self.calc_power_energy(5, self.str_to_le32(buf[52:56]), delta_sec)

            if self._chn_enabled & self.ENB_CHN_WATT_AUX5:
                self.calc_power_energy(6, self.str_to_le32(buf[56:60]), delta_sec)

            # DC input
            if self._chn_enabled & self.ENB_CHN_DC_INPUT:
                self._dc_input = self.str_to_le16(buf[60:62])
                if self.trace:
                    print 'dc_input: %d' % self._dc_input

        # save the current seconds for next time
        self.__last_seconds = self.__seconds

        return { 'error': None }

    def calc_power_energy(self, index, wattsec, delta_sec):
        if self.__wattsec[index] is None:
            # then first time through just do little
            self.__wattsec[index] = wattsec

        else:
            delta_wattsec = (wattsec - self.__wattsec[index])
            if delta_wattsec != 0:
                self._power[index] = delta_wattsec / delta_sec
                self.__wattsec[index] = wattsec
                self._kwh[index] = wattsec / 3600000.0

                if self.trace:
                    if index <= 1:
                        print '%s: wattsec:%d Power:%0.2fW Current:%0.2f, Energy:%0.3fKWh' % \
                            (self.CHN_INDEX_LABEL[index], self.__wattsec[index],
                             self._power[index], self._current[index], self._kwh[index])
                    else:
                        print '%s: wattsec:%d Power:%0.2fW Energy:%0.3fKWh' % \
                            (self.CHN_INDEX_LABEL[index], self.__wattsec[index],
                             self._power[index], self._kwh[index])

                return True # it changed

        return False # no change

    def export_binary(self):

		if self.__model == 1220:
			buf = ['\xFE\xFF\x01']
		else:
			buf = ['\xFE\xFF\x03']

		# add the voltage - big-endian (?)
		buf.append(self.int_to_be_str2(self.__voltage * 10))

		# add the CH1 & Ch2 Watt Counters - little-endian 5-byte
		buf.append(self.int_to_str2(self.__abs_wattsec[0]))
		buf.append(self.int_to_str2(self.__abs_wattsec[1]))
		buf.append(self.int_to_str2(self.__pol_wattsec[0]))
		buf.append(self.int_to_str2(self.__pol_wattsec[1]))

		# reserved bytes
		buf.append('\x00\x00\x00\x00')

		# add the serial_number
		buf.append(self.int_to_be_str2(self.__serial_number))
		buf.append(self.int_to_str1(self.__flags))
		buf.append(self.int_to_str1(self.__unit_id))

		# add the CH1 & CH2 Current - little-endian 2-byte
		buf.append(self.int_to_str2(self._current[0]))
		buf.append(self.int_to_str2(self._current[1]))

		# add the seconds counter - little-endian 3-byte
		buf.append(self.int_to_str3(self.__seconds))

		if self.__model == 1220:
			# then shortened form
			pass

		else: # is long form

			# add the AUX watt-seconds - little-endian 4-byte
			buf.append(self.int_to_str4(self.__wattsec[0]))
			buf.append(self.int_to_str4(self.__wattsec[1]))
			buf.append(self.int_to_str4(self.__wattsec[2]))
			buf.append(self.int_to_str4(self.__wattsec[3]))
			buf.append(self.int_to_str4(self.__wattsec[4]))

			# DC input
			buf.append('\x00\x00')

		buf.append('\xFF\xFE')
		buf = "".join(buf)
		print 'length of buffer is %d' % len(buf)

		bcc = 0
		for by in buf:
			bcc += ord(by)
		bcc &= 0xFF
		print 'bcc is 0x%02X' % bcc

		return buf + chr(bcc)

    def get_chn_name_current(self, index):
		if (index >= 1) and (index <= 2):
			return self.__chn_current[index-1]
		raise ValueError,"Invalid index for accessing AC_Current channel names"

    def get_chn_name_power(self, index):
		if (index >= 1) and (index <= self.__get_max_channels()):
			return self.__chn_power[index-1]
		raise ValueError,"Invalid index for accessing AC_Power channel names"

    def get_chn_name_energy(self, index):
		if (index >= 1) and (index <= self.__get_max_channels()):
			return self.__chn_energy[index-1]
		raise ValueError,"Invalid index for accessing AC_Energy channel names"

    def get_chn_name_voltage(self, index=1):
		if (index == 1):
			return self.CHN_VOLTAGE
		raise ValueError,"Invalid index for accessing AC_Volatge channel names"

    def get_chn_name_events(self, index):
		# we ignore the index
		return self.__chn_events[0]

    def __get_max_channels(self):
		if self.__model == 1220:
			return 2
		else:
			return 7

    def __load_channel_names(self, ecm1220=False):
        '''To avoid string thrashing, just save the names'''
        self.__chn_current = []
        self.__chn_power = []
        self.__chn_energy = []
        self.__chn_events = [ self.CHN_EVENTS ]
        for id in (1,2):
            # both ecm1220 and ecm1240 have first 2 channels
            self.__chn_current.append( '%s_%d' % (self.CHN_CURRENT_AMP, id))
            self.__chn_power.append( '%s_%d' % (self.CHN_POWER_W, id))
            self.__chn_energy.append( '%s_%d' % (self.CHN_ENERGY_WH, id))

        if self.__model == 1240:
            for id in (3,4,5,6,7):
                # only ecm1240 has 5 more power/energy readings
                # TODO: support voltage on AUX5
                self.__chn_power.append( '%s_%d' % (self.CHN_POWER_W, id))
                self.__chn_energy.append( '%s_%d' % (self.CHN_ENERGY_WH, id))

        return

    def int_to_str1(self, u):
        # given byte, return as binary string
        return chr((int(u) & 0xFF))

    def int_to_be_str2(self, u):
        # given word, return as binary string
        u = int(u)
        return chr((u>>8)&0xFF) + chr(u&0xFF)

    def int_to_str2(self, u):
        # given word, return as binary string
        u = int(u)
        return chr(u&0xFF) + chr((u>>8)&0xFF)

    def int_to_str3(self, u):
        # given word, return as binary string
        u = int(u)
        return chr(u&0xFF) + chr((u>>8)&0xFF) + chr((u>>16)&0xFF)

    def int_to_str4(self, u):
        # given word, return as binary string
        u = long(u)
        return chr(u&0xFF) + chr((u>>8)&0xFF) + chr((u>>16)&0xFF) + \
               chr((u>>24)&0xFF)

    def int_to_str5(self, u):
        # given word, return as binary string
        u = long(u)
        return chr(u&0xFF) + chr((u>>8)&0xFF) + chr((u>>16)&0xFF) + \
               chr((u>>24)&0xFF) + chr((u>>32)&0xFF)

    def be32_to_str(self, u, bend=True):
        # given long/dword, return as binary string
        u = ( int(u) & 0xFFFFFFFF)
        if( bend): # big word first
            return( be16_to_str( u>>16) + be16_to_str( u&0xFFFF))
        else: # little word first
            return(be16_to_str( u&0xFFFF) + be16_to_str( u>>16))

    def str_to_be8(self, st):
        # given binary string, return bytes[0] as int
        return ord(st[0])

    def str_to_be16(self, st):
        # given binary string, return bytes[0-1] as int
        return (ord(st[0])<<8) + ord(st[1])

    def str_to_le16(self, st):
        # given binary string, return bytes[0-1] as int
        return ord(st[0]) + (ord(st[1])<<8)

    def str_to_le24(self, st):
        # given binary string, return bytes[0-2] as int
        return ord(st[0]) + (ord(st[1])<<8) + (ord(st[2])<<16)

    def str_to_le32(self, st):
        # given binary string, return bytes[0-3] as int
        return ord(st[0]) + (ord(st[1])<<8) + (ord(st[2])<<16) + (ord(st[3])<<24)

    def str_to_le40(self, st):
        return long(ord(st[0]) + (ord(st[1])<<8) + (ord(st[2])<<16)) + \
               long(ord(st[3])<<24) + long(ord(st[4])<<32)
