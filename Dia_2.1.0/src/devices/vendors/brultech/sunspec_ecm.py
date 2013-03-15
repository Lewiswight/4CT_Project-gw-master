# File: robust_ecm.py
# Desc: receive data from the Brultech ECM1240, uploading as if SunSpec Meter Data

"""\

"""

# imports
import traceback
import types
import time

from settings.settings_base import SettingsBase, Setting
from samples.sample import *
from core.tracing import get_tracer
from channels.channel_source_device_property import *

from devices.vendors.brultech.ecm_object import ECM1240
from devices.vendors.brultech.ecm_object_sunspec import ECM1240_SunSpec
from devices.vendors.brultech.robust_ecm import ECM1240_Xbee

from devices.vendors.brultech.sspec_upload import sunspec_upload

# constants

# exception classes

# interface functions

# classes
class ECM1240_Xbee_SunSpec(ECM1240_Xbee):

    SSPEC_DEF_SAMPLE_RATE = "1 min"
    SSPEC_DEF_SINGLE_CHANNEL = True

    def __init__(self, name, core_services, settings_in=None, properties_in=None):

        self.__tracer = get_tracer('EcmSSpec')
        self.__showname = name

        ## Local State Variables:
        self.__last_logger_sample = 0

        ## Settings Table Definition:
        settings_list = [

            Setting(
                name='sunspec_lid', type=str, required=False,
                default_value=ECM1240_SunSpec.SSPEC_DEF_LID),

            # format should be in set ('device', 'model', 'point')
            Setting(
                name='sunspec_format', type=str, required=False,
                default_value=ECM1240_SunSpec.SSPEC_DEF_LID),

            Setting(
                name='single_channel', type=bool, required=False,
                default_value=self.SSPEC_DEF_SINGLE_CHANNEL),

			# 'dev_poll_rate_sec' set to:
            #   0/None to disable polling callbacks
            #   set to numebr of secs, or tag with sec, min, hr such as '1 min', '3 hr' etc
            Setting(
                name='sunspec_sample_rate_sec', type=str, required=False,
                default_value=self.SSPEC_DEF_SAMPLE_RATE),

        ]
        settings_out = self._safely_merge_lists(settings_in, settings_list)

        ## Channel Properties Definition: assume ecm1240
        property_list = [
            ChannelSourceDeviceProperty( name='sunspec_logger', type=str,
                    initial=Sample(timestamp=0, value="", unit="not_init"),
                    perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP)
            ]
        properties_out = self._safely_merge_lists(properties_in, property_list)

        ## Initialize the DeviceBase interface:

        ECM1240_Xbee.__init__(self, name, core_services, settings_out, properties_out)

        # swap in an a SunSpec-aware ECM object
        self._ecm = ECM1240_SunSpec()
        self._ecm.trace = False

        return

    def start(self):
        """Start the device driver.  Returns bool."""

        ECM1240_Xbee.start(self)

        if self._import_settings():
            self.apply_settings()

        logger_id = SettingsBase.get_setting(self, 'sunspec_lid')
        if (logger_id is None) or (logger_id.lower == 'none'):
            self._ecm._lid = None
            self._lid_ns = None
        #elif logger_id.lower is in ['mac', 'auto']:
        #    self._ecm._lid = None
        #    self._lid_ns = 'mac'
        else:
            self._ecm._lid = logger_id
            self._lid_ns = 'mac'

        format = SettingsBase.get_setting(self, 'sunspec_format').lower()
        if format in ECM1240_SunSpec.XML_FORM_LIST:
            self._ecm._xml_form = format
            self.__tracer.debug('%s: Selecting XML format "%s".', self.__showname, format)
        else:
            self.__tracer.error('%s: Unknown XML format "%s".', self.__showname, format)

        self._ecm._single_channel = SettingsBase.get_setting(self, 'single_channel')
        if self._ecm._single_channel:
            self.__tracer.debug('%s: Forcing Single Channel Mode', self.__showname)

        return True

    def stop(self):
        """Stop the device driver.  Returns bool."""
        ECM1240_Xbee.stop(self)
        return True

    ## Locally defined functions:

    def _import_settings(self):
        """Handle the settings dependencies"""

        ## Handle the poll settings
        self._sample_rate,change = self._import_adjust_time_setting( \
                            "sunspec_sample_rate_sec", "SunSpec Log Sample Rate")
        return change

    def read_callback(self, buf, addr):

        if not ECM1240_Xbee.read_callback(self, buf, addr):
            # then parsing of data failed
            #self.__tracer.debug('%s: Skip Logging, ECM1240_Xbee.read_callback() failed to parse',
            #    self.__showname)
            return False

        now = time.time()
        delta = now - self.__last_logger_sample
        self.__tracer.debug('SunSpec Logger Sample time %dsec', self._sample_rate)
        if delta < self._sample_rate:
            self.__tracer.debug('%s: Skip Logging, is too early, only %d sec.', self.__showname, delta)
            return False

        self.__last_logger_sample = now

        st = self._ecm._dump_sunspec_xml_device(now)
        self.property_set("sunspec_logger", Sample(now, st, 'xml'))

        self.__tracer.info('%s: Logger Sample: %s', self.__showname, st)

        success,errcode,errmsg = sunspec_upload(st)
        if success:
            self.__tracer.info('%s: Logger Upload Successful', self.__showname)
        else:
            self.__tracer.warning('%s: Logger Upload Failed, cod:%d msg:%s',
                self.__showname, errcode, errmsg)

        return True
