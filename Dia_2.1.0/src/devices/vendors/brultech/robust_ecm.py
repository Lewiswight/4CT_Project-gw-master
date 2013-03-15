# File: robust_ecm.py
# Desc: receive data from the Brultech ECM1240, uploading as if SunSpec Meter Data

"""\

"""

# imports
import struct
import traceback
import types
import time

from settings.settings_base import SettingsBase, Setting
from samples.sample import *
from core.tracing import get_tracer
from channels.channel_source_device_property import *
from devices.xbee.xbee_device_manager.xbee_device_manager_event_specs \
    import *
import devices.xbee.common.prodid as prodid

from devices.vendors.robust.robust_xserial import RobustXSerial
from devices.vendors.brultech.ecm_object import ECM1240

# constants

# exception classes

# interface functions

# classes
class ECM1240_Xbee(RobustXSerial):

    # Our base class defines all the addresses we care about.
    ADDRESS_TABLE = [ ]

    # The list of supported products that this driver supports.
    SUPPORTED_PRODUCTS = [ prodid.PROD_DIGI_XB_ADAPTER_RS232, prodid.PROD_ROBUSTMESH_232]

    # over-ride robust_xserial setting defaults
    XSER_DEFAULT_TYPE = '232'
    XSER_DEFAULT_BAUD = 19200


    # over-ride - disable all polling - brultech just sends to us
    RDB_DEF_POLL_RATE = 0
    RDB_DEF_RESPONSE_TIMEOUT = 0

    # set this to 0 and uncomment to disable HeartBeats
    # RXBEE_DEF_HEART_BEAT = 60

    # over-ride robustxbee - we want some IO added
    RXBEE_DEF_HEART_BEAT_IO = 'D1'

    # Enable Channel Bits
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

    #ENB_CHN_DEFAULTS = ENB_CHN_ABSWATT_CH1 + ENB_CHN_ABSWATT_CH2 + ENB_CHN_VOLTAGE + \
    #    ENB_CHN_CURRENT_CH1 + ENB_CHN_CURRENT_CH2
    ENB_CHN_DEFAULTS = 0x0FB13

    def __init__(self, name, core_services, settings_in=None, property_in=None):

        self.__tracer = get_tracer('BrulTech')
        self.__showname = 'ecm(%s)' % name

        ## Local State Variables:
        self._ecm = ECM1240()
        self._ecm.trace = False

        ## Settings Table Definition:
        settings_list = [
            # Setting( name='sample_rate_sec' is in Robust_Device

            #Setting(
            #    name='binary_format', type=bool, required=False,
            #    default_value=True),

            Setting(
                name='ac_voltage_adjust', type=float, required=False,
                default_value=1.0),

            Setting(
                name='ecm1220', type=bool, required=False,
                default_value=False),

            Setting(
                name='enable_channels', type=int, required=False,
                default_value=self.ENB_CHN_DEFAULTS),

        ]

        settings_out = self._safely_merge_lists(settings_in, settings_list)

        ## Channel Properties Definition: assume ecm1240
        # property_list = [ ]

        # Add our property_list entries to the properties passed to us.
        # properties = self._safely_merge_lists(properties, property_list)
        property_out = property_in

        ## Initialize the DeviceBase interface:
        RobustXSerial.__init__(self, name, core_services, settings_out, property_out)
        return

    ## Functions which must be implemented to conform to the XBeeBase
    ## interface:

    @staticmethod
    def probe():
        """\
        Collect important information about the driver.
        """

        probe_data = RobustXSerial.probe()

        for address in ECM1240_Xbee.ADDRESS_TABLE:
            probe_data['address_table'].append(address)

        # We don't care what devices our base class might support.
        # We JUST use ours instead.
        probe_data['supported_products'] = ECM1240_Xbee.SUPPORTED_PRODUCTS

        return probe_data

    ## Functions which must be implemented to conform to the DeviceBase
    ## interface:

    def start(self):
        """Start the device driver.  Returns bool."""

        RobustXSerial.start_pre(self)

        # create the Dia channels
        chns = SettingsBase.get_setting(self, "enable_channels")
        self._ecm.set_enabled_channels(chns)
        self.__chn_enabled = chns

        nam_list = []
        if chns & self.ENB_CHN_WATT_CH1:
            nam_list.append(self._ecm.get_chn_name_power(1))
            nam_list.append(self._ecm.get_chn_name_energy(1))
        if chns & self.ENB_CHN_WATT_CH2:
            nam_list.append(self._ecm.get_chn_name_power(2))
            nam_list.append(self._ecm.get_chn_name_energy(2))
        if chns & self.ENB_CHN_CURRENT_CH1:
            nam_list.append(self._ecm.get_chn_name_current(1))
        if chns & self.ENB_CHN_CURRENT_CH2:
            nam_list.append(self._ecm.get_chn_name_current(2))
        if chns & self.ENB_CHN_VOLTAGE:
            nam_list.append(self._ecm.get_chn_name_voltage())
        if chns & self.ENB_CHN_WATT_AUX1:
            nam_list.append(self._ecm.get_chn_name_power(3))
            nam_list.append(self._ecm.get_chn_name_energy(3))
        if chns & self.ENB_CHN_WATT_AUX2:
            nam_list.append(self._ecm.get_chn_name_power(4))
            nam_list.append(self._ecm.get_chn_name_energy(4))
        if chns & self.ENB_CHN_WATT_AUX3:
            nam_list.append(self._ecm.get_chn_name_power(5))
            nam_list.append(self._ecm.get_chn_name_energy(5))
        if chns & self.ENB_CHN_WATT_AUX4:
            nam_list.append(self._ecm.get_chn_name_power(6))
            nam_list.append(self._ecm.get_chn_name_energy(6))
        if chns & self.ENB_CHN_WATT_AUX5:
            nam_list.append(self._ecm.get_chn_name_power(7))
            nam_list.append(self._ecm.get_chn_name_energy(7))
    #ENB_CHN_SERIAL_NO       = 0x0020
    #ENB_CHN_FLAGS           = 0x0040
    #ENB_CHN_UNIT_ID         = 0x0080
    #ENB_CHN_SECONDS         = 0x0400

        for nam in nam_list:
            self.__tracer.debug("Adding Channel:%s ", nam)
            self.add_property(
                ChannelSourceDeviceProperty(name=nam,
                    type=float, initial=Sample(0, 0.0, 'not init'),
                    perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP))

        x = SettingsBase.get_setting(self, "ac_voltage_adjust")
        self._ecm.set_ac_voltage_adjust(x)
        if x != 1.0:
            self.__tracer.debug("Setting AC Voltage Adjust of %f", x)

        RobustXSerial.initialize_xbee_serial(self)
        RobustXSerial.start_post(self)

        return True

    def stop(self):
        """Stop the device driver.  Returns bool."""
        RobustXSerial.stop(self)
        return True


    ## Locally defined functions:

    def read_callback(self, buf, addr):

        # we have a response, so cancel the timeout
        self.cancel_response_timeout()

        # parse the indication - see if it's meaningful
        xdct = self._ecm.import_binary(buf)
        if xdct.get('error', None) is not None:
            # then import worked
            self.__tracer.warning("Data Import Failed:%s ", xdct['error'] )
            return False

        now = time.time()

        chns = SettingsBase.get_setting(self, "enable_channels")
        if self._ecm._power[0] is not None:
            self.property_set(self._ecm.get_chn_name_power(1),
                Sample(now, self._ecm._power[0], 'W'))
            self.property_set(self._ecm.get_chn_name_energy(1),
                Sample(now, self._ecm._kwh[0], 'KWh'))
            self.__tracer.info('CH1: Power:%0.2fW Current:%0.2f, Energy:%0.3fKWh',
                    self._ecm._power[0], self._ecm._current[0],
                    self._ecm._kwh[0])

        if self._ecm._power[1] is not None:
            self.property_set(self._ecm.get_chn_name_power(2),
                Sample(now, self._ecm._power[1], 'W'))
            self.property_set(self._ecm.get_chn_name_energy(2),
                Sample(now, self._ecm._kwh[1], 'KWh'))
            self.__tracer.info('CH2: Power:%0.2fW Current:%0.2f, Energy:%0.3fKWh',
                    self._ecm._power[1], self._ecm._current[1],
                    self._ecm._kwh[1])

        if chns & self.ENB_CHN_CURRENT_CH1 and \
                self._ecm._current[0] is not None:
            self.property_set(self._ecm.get_chn_name_current(1),
                Sample(now, self._ecm._current[0], 'A'))

        if chns & self.ENB_CHN_CURRENT_CH2 and \
                self._ecm._current[1] is not None:
            self.property_set(self._ecm.get_chn_name_current(2),
                Sample(now, self._ecm._current[1], 'A'))

        if chns & self.ENB_CHN_VOLTAGE and \
                self._ecm._voltage is not None:
            self.property_set(self._ecm.get_chn_name_voltage(),
                Sample(now, self._ecm._voltage, 'VAC'))

        if self._ecm._power[2] is not None:
            self.property_set(self._ecm.get_chn_name_power(3),
                Sample(now, self._ecm._power[2], 'W'))
            self.property_set(self._ecm.get_chn_name_energy(3),
                Sample(now, self._ecm._kwh[2], 'KWh'))
            self.__tracer.info('AUX1: Power:%0.2fW Energy:%0.3fKWh',
                    self._ecm._power[2], self._ecm._kwh[2])

        if self._ecm._power[3] is not None:
            self.property_set(self._ecm.get_chn_name_power(4),
                Sample(now, self._ecm._power[3], 'W'))
            self.property_set(self._ecm.get_chn_name_energy(4),
                Sample(now, self._ecm._kwh[3], 'KWh'))
            self.__tracer.info('AUX2: Power:%0.2fW Energy:%0.3fKWh',
                    self._ecm._power[3], self._ecm._kwh[3])

        if self._ecm._power[4] is not None:
            self.property_set(self._ecm.get_chn_name_power(5),
                Sample(now, self._ecm._power[4], 'W'))
            self.property_set(self._ecm.get_chn_name_energy(5),
                Sample(now, self._ecm._kwh[4], 'KWh'))
            self.__tracer.info('AUX3: Power:%0.2fW Energy:%0.3fKWh',
                    self._ecm._power[4], self._ecm._kwh[4])

        if self._ecm._power[5] is not None:
            self.property_set(self._ecm.get_chn_name_power(6),
                Sample(now, self._ecm._power[5], 'W'))
            self.property_set(self._ecm.get_chn_name_energy(6),
                Sample(now, self._ecm._kwh[5], 'KWh'))
            self.__tracer.info('AUX4: Power:%0.2fW Energy:%0.3fKWh',
                    self._ecm._power[5], self._ecm._kwh[5])

        if self._ecm._power[6] is not None:
            self.property_set(self._ecm.get_chn_name_power(7),
                Sample(now, self._ecm._power[6], 'W'))
            self.property_set(self._ecm.get_chn_name_energy(7),
                Sample(now, self._ecm._kwh[6], 'KWh'))
            self.__tracer.info('AUX5: Power:%0.2fW Energy:%0.3fKWh',
                    self._ecm._power[6], self._ecm._kwh[6])

        return True
