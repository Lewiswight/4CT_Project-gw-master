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
import time
try:
    from ecm_object import ECM1240
except:
    from devices.vendors.brultech.ecm_object import ECM1240

# constants

# exception classes

# interface functions

# classes
class ECM1240_SunSpec(ECM1240):

    SSPEC_DEF_LID =  "00:23:14:81:C9:B8"
    SSPED_DEF_LID_NS = "mac"
    SSPEC_DEF_MAN =  "brultech"
    SSPEC_DEF_MOD =  "ECM-1240"
    SSPEC_DEF_SN =  "34567"

    SSPEC_METER_MODEL = 201
    SSPEC_STRING_MODEL = 402
    SSPEC_DEF_MODEL = SSPEC_METER_MODEL

    MODEL201_CURRENT_NAME = 'M_AC_Current'
    MODEL201_POWER_NAME = 'M_AC_Power'
    MODEL201_ENERGY_NAME = 'M_Imported'
    MODEL201_VOLTAGE_NAME = 'M_AC_Voltage'

    MODEL402_CURRENT_NAME = 'SC_Input_DC_Current'
    MODEL402_POWER_NAME = 'SC_Input_DC_Power'
    MODEL402_ENERGY_NAME = 'SC_Input_DC_Energy'
    MODEL402_VOLTAGE_NAME = 'SC_Input_DC_Voltage'

    MODELALL_CURRENT_UNITS = 'Amps'
    MODELALL_POWER_UNITS = 'Watts'
    MODELALL_ENERGY_UNITS = 'Watt-hours'
    MODELALL_VOLTAGE_UNITS = 'Volts'

    XML_DEF_WHITESPACE_D = '\r\n'
    XML_DEF_WHITESPACE_M = '\r\n '
    XML_DEF_WHITESPACE_P = '\r\n  '

    XML_DEF_ADD_UNITS = False

    XML_FORM_DEVICE_INDEX = 'device'
    XML_FORM_MODEL_INDEX = 'model'
    XML_FORM_POINT_INDEX = 'point'
    XML_DEF_FORM_DEVICE_INDEX = XML_FORM_POINT_INDEX
    XML_FORM_LIST = (XML_FORM_DEVICE_INDEX, XML_FORM_MODEL_INDEX, XML_FORM_POINT_INDEX)

    def __init__(self, name=None):

        ECM1240.__init__(self, name)

        ## local variables
        self._xml_form = self.XML_DEF_FORM_DEVICE_INDEX

        self._xml_white_space_d = self.XML_DEF_WHITESPACE_D
        self._xml_white_space_m = self.XML_DEF_WHITESPACE_M
        self._xml_white_space_p = self.XML_DEF_WHITESPACE_P
        self._xml_add_units = self.XML_DEF_ADD_UNITS

        self._lid = self.SSPEC_DEF_LID
        self._lid_ns = self.SSPED_DEF_LID_NS
        self._man = self.SSPEC_DEF_MAN
        self._mod = self.SSPEC_DEF_MOD
        self._sn = self.SSPEC_DEF_SN
        self._sn_deco = ''

        self.select_sunspec_model(self.SSPEC_DEF_MODEL)

        return

    def select_sunspec_model(self, model):

        if model == self.SSPEC_METER_MODEL:
            self.__curnam = self.MODEL201_CURRENT_NAME
            self.__pownam = self.MODEL201_POWER_NAME
            self.__enenam = self.MODEL201_ENERGY_NAME
            self.__vltnam = self.MODEL201_VOLTAGE_NAME

        elif model == self.SSPEC_STRING_MODEL:
            self.__curnam = self.MODEL402_CURRENT_NAME
            self.__pownam = self.MODEL402_POWER_NAME
            self.__enenam = self.MODEL402_ENERGY_NAME
            self.__vltnam = self.MODEL402_VOLTAGE_NAME

        else:
            raise ValueError, "SunSpec Model %d is not supported" % model

        self.__model = model

        return

    def _dump_sunspec_xml_device(self, tim=None, cid=None):

        if tim is None:
            tim = time.time()

        if self._xml_form == self.XML_FORM_DEVICE_INDEX:
            st = self._dump_sunspec_xml_device_as_many(tim, cid)
        else:
            st = self._dump_sunspec_xml_device_as_one(tim, cid)
        return "".join(st)
        #XML_FORM_DEVICE_INDEX = 'd_idx'
        #XML_FORM_MODEL_INDEX = 'm_idx'
        #XML_FORM_POINT_INDEX = 'p_idx'

    def _dump_sunspec_xml_device_as_one(self, tim, cid):

        # since no serial_number decoration, force to ''
        self._sn_deco = ''

        # get the '<d ns="mac" lid= ... >
        st = self._dump_sunspec_xml_device_header(tim, cid)

        st.extend(self._dump_sunspec_xml_model_all([],
            self._xml_form == self.XML_FORM_POINT_INDEX))

        st.append(self._xml_white_space_d + '</d>')
        return st

    def _dump_sunspec_xml_device_as_many(self, tim, cid):

        st = ['']

        if self._single_channel:
            self._sn_deco = ''
            st.extend(self._dump_sunspec_xml_device_header(tim, cid))
            st.extend(self._dump_sunspec_xml_model_single([], 0, p_index=None))
            st.append(self._xml_white_space_d + '</d>')

        else:
            for idx in (0,1,2,3,4,5,6):
                if self._chn_enabled & self.CHN_ENABLED_INDEXES[idx]:
                    self._sn_deco = '_%d' % (idx+1)

                    # get the '<d ns="mac" lid= ... >
                    mod = self._dump_sunspec_xml_model_single([], idx, p_index=None)
                    if mod is None:
                        # then skip this one
                        continue
                    else:
                        st.extend(self._dump_sunspec_xml_device_header(tim, cid))
                        st.extend(mod)
                        st.append(self._xml_white_space_d + '</d>')

        return st

    def _dump_sunspec_xml_device_header(self, tim, cid):
        # form just the header, such as
        #  <d ns="mac" lid="11:22:33:44:55:66" man="gsc" mod="r300"
        #     sn="123456" t="2011-05-12T09:21:49Z" cid="2">

        st = [self._xml_white_space_d + '<d']

        if self._lid is not None:
            # logger id info is optional
            if self._lid_ns is not None:
                st.append(' ns="%s"' % self._lid_ns)
            st.append( ' lid="%s"' % self._lid)

        st.append( ' man="%s"' % self._man)
        if self._mod is not None:
            st.append( ' mod="%s"' % self._mod)
        # add serial number and possible decoration for mulitple virtual devs
        st.append( ' sn="%s%s"' % (self._sn, self._sn_deco))

        st.append( ' t="%s"' % time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(tim)))

        if cid is not None:
            st.append( ' cid"%s"' % cid)

        st.append( '>')

        return st

    def _dump_sunspec_xml_model_all(self, st, p_index=True):
        if p_index:
            # then a single model entry
            st.append(self._xml_white_space_m + '<m id="%d">' % self.__model)

        if self._single_channel:
            st.extend(self._dump_sunspec_xml_model_single([], 0, p_index))

        else:
            for idx in (0,1,2,3,4,5,6):
                if self._chn_enabled & self.CHN_ENABLED_INDEXES[idx]:
                    mod = self._dump_sunspec_xml_model_single([], idx, p_index)
                    if mod is not None:
                        st.extend(mod)

        if p_index:
            # then a single model entry
            st.append(self._xml_white_space_m + '</m>')
        return st

    def _dump_sunspec_xml_model_single(self, st, index, p_index=True):
        pi = ''
        if (p_index is None):
            st.append(self._xml_white_space_m + '<m id="%d">' % self.__model)

        elif p_index:
            pi = ' x="%d"' % (index+1)

        else:
            if self._single_channel:
                st.append(self._xml_white_space_m + '<m id="%d">' % self.__model)
            else:
                st.append(self._xml_white_space_m + '<m id="%d" x="%d">' % \
                    (self.__model, index+1))

        active = False

        p = self._dump_sunspec_xml_power(index, pi)
        if p is not None:
            active = True
            st.append(p)

        p = self._dump_sunspec_xml_energy(index, pi)
        if p is not None:
            active = True
            st.append(p)

        if index in [0,1]:
            p = self._dump_sunspec_xml_current(index, pi)
            if p is not None:
                active = True
                st.append(p)

        if index == 0:
            p = self._dump_sunspec_xml_voltage(index, pi)
            if p is not None:
                active = True
                st.append(p)

        if not active:
            # print 'nothing added'
            st = None
        elif not p_index:
            st.append(self._xml_white_space_m + '</m>')
        return st

    def _dump_sunspec_xml_power(self, index, p_index=''):
        if self._xml_add_units:
            units = ' u="W"'
        else:
            units = ''
        try:
            if self._power[index] is not None:
                return self._xml_white_space_p + '<p id="%s"' % self.__pownam + \
                            p_index + units + '>' + '%0.2f' % self._power[index] + '</p>'
        except:
            pass
        return None

    def _dump_sunspec_xml_energy(self, index, p_index=''):
        if self._xml_add_units:
            units = ' u="KWh"'
        else:
            units = ''
        try:
            if self._kwh[index] is not None:
                return self._xml_white_space_p + '<p id="%s"' % self.__enenam + \
                            p_index + units + '>' + '%0.2f' % self._kwh[index] + '</p>'
        except:
            pass
        return None

    def _dump_sunspec_xml_current(self, index, p_index=''):
        if self._xml_add_units:
            units = ' u="A"'
        else:
            units = ''
        try:
            if self._current[index] is not None:
                return self._xml_white_space_p + '<p id="%s"' % self.__curnam + \
                        p_index + units + '>' + '%0.2f' % self._current[index] + '</p>'
        except:
            pass
        return None

    def _dump_sunspec_xml_voltage(self, index, p_index=''):
        if index < 0 or index > 6 or self._voltage is None:
            return None
        if self._xml_add_units:
            units = ' u="V"'
        else:
            units = ''
        return self._xml_white_space_p + '<p id="%s"' % self.__vltnam + \
                    p_index + units + '>' + '%0.2f' % self._voltage + '</p>'
