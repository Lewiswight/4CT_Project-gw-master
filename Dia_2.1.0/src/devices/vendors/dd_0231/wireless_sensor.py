############################################################################
#                                                                          #
#                                                                          #
############################################################################
import traceback

"""\
A Dia Driver for XBee wirelss sensors


"""

# imports
try:
    from devices.vendors.dd_0231.WirelessPacketParser import WirelessPacketParser
except:
    from WirelessPacketParser import WirelessPacketParser

from devices.device_base import DeviceBase
from devices.xbee.xbee_devices.xbee_base import XBeeBase
from settings.settings_base import SettingsBase, Setting
from channels.channel_source_device_property import *
from common.types.boolean import Boolean, STYLE_ONOFF

from devices.xbee.xbee_config_blocks.xbee_config_block_ddo \
    import XBeeConfigBlockDDO, DDO_GET_PARAM
from devices.xbee.xbee_config_blocks.xbee_config_block_sleep \
    import CYCLIC_SLEEP_EXT_MAX_MS, SM_DISABLED, XBeeConfigBlockSleep
from devices.xbee.xbee_device_manager.xbee_device_manager_event_specs \
    import *

from devices.xbee.xbee_config_blocks.xbee_config_block_sleep \
    import XBeeConfigNetworkSleep
    
# value should be 0x0231, so full DD = 0x00030231
from devices.xbee.common.prodid import PROD_DD0231_TEMPERATURE

import struct

# constants

# exception classes

# interface functions

# classes
class WirelessSensor(XBeeBase):
    KEY_ALARM = 'alarm'
    KEY_BATTERY_COUNT = 'battery_count'
    KEY_BATTERY_LOW = 'battery_low'
    KEY_CHANNEL = 'channel'
    KEY_DOOR_OPEN = 'doorOpen'
    KEY_ERROR = 'error'
    KEY_DEVICE_ID = 'device_id'
    KEY_GLOBAL = 'global'
    KEY_LINE_POWERED = 'line_powered'
    KEY_LOCALLY_CONFIGURED = 'locally_configured'
    KEY_LOG_PERIOD = 'log_period'
    KEY_PACKET_COUNT = 'packet_count'
    KEY_REMAINING_BATT_PCT = 'remaining_battery_pct'
    KEY_SAMPLE_RATE = 'sample_rate_sec'
    KEY_SERIAL_NO = 'serial_number'
    KEY_SERVICE_PRESSED = 'service_pressed'

    PACKET_LENGTH = 75

    # Define a set of endpoints that this device will send in on.  
    ADDRESS_TABLE = [ [0xe8, 0xc105, 0x11] ]

    # The list of supported products that this driver supports.
    SUPPORTED_PRODUCTS = [ PROD_DD0231_TEMPERATURE ]

    def __init__(self, name, core_services):
        self.__name = name
        self.__core = core_services
        self.parser = WirelessPacketParser()

        self.trace = True

        if self.trace:        
            print 'WirelessSensor(%s) init' % self.__name
        
        ## Local State Variables:
        self.__xbee_manager = None

        ## Settings Table Definition:
        settings_list = [
                Setting(name = self.KEY_SAMPLE_RATE, type = int, required = False,
                default_value = 60,
                verify_function = lambda x: \
                                  x >= 30 and \
                                  x <= 525600 * 60),
                Setting(name = self.parser.KEY_XMIT_PERIOD, type = dict, required = False,
                default_value = {}),
                Setting(name = self.parser.KEY_ALARM_EXIT, type = dict, required = False,
                default_value = {}),
                Setting(name = self.parser.KEY_TRIES, type = dict, required = False,
                default_value = {}),
                Setting(name = self.parser.KEY_HYSTERISIS, type = dict, required = False,
                default_value = {}),
                Setting(name = self.parser.KEY_LOG_PERIOD, type = dict, required = False,
                default_value = {}),
                Setting(name = self.parser.KEY_HI_VAL1, type = dict, required = False,
                default_value = {}),
                Setting(name = self.parser.KEY_HI_TIME1, type = dict, required = False,
                default_value = {}),
                Setting(name = self.parser.KEY_LO_VAL1, type = dict, required = False,
                default_value = {}),
                Setting(name = self.parser.KEY_LO_TIME1, type = dict, required = False,
                default_value = {}),
                Setting(name = self.parser.KEY_HI_VAL2, type = dict, required = False,
                default_value = {}),
                Setting(name = self.parser.KEY_HI_TIME2, type = dict, required = False,
                default_value = {}),
                Setting(name = self.parser.KEY_LO_VAL2, type = dict, required = False,
                default_value = {}),
                Setting(name = self.parser.KEY_LO_TIME2, type = dict, required = False,
                default_value = {}),
                                  ]

        ## Channel Properties Definition:
        property_list = [
            # gettable properties
            ChannelSourceDeviceProperty(name=self.KEY_CHANNEL + str(1), type=float,
                initial=Sample(timestamp=0, value=-9223372036854775808.0, unit="units"),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name=self.KEY_CHANNEL + str(2), type=float,
                initial=Sample(timestamp=0, value=-9223372036854775808.0, unit="units"),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name=self.KEY_CHANNEL + str(3), type=float,
                initial=Sample(timestamp=0, value=-9223372036854775808.0, unit="units"),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name=self.KEY_CHANNEL + str(4), type=float,
                initial=Sample(timestamp=0, value=-9223372036854775808.0, unit="units"),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),

            ChannelSourceDeviceProperty(name=self.KEY_ALARM, type=bool,
                initial=Sample(timestamp=0, value=False),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name=self.KEY_BATTERY_COUNT, type=int,
                initial=Sample(timestamp=0, value=0),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name=self.KEY_BATTERY_LOW, type=bool,
                initial=Sample(timestamp=0, value=False),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name=self.KEY_DEVICE_ID, type=str,
                initial=Sample(timestamp=0, value=''),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name=self.KEY_DOOR_OPEN, type=bool,
                initial=Sample(timestamp=0, value=False),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name=self.KEY_ERROR, type=list,
                initial=Sample(timestamp=0, value=[]),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name=self.KEY_LINE_POWERED, type=bool,
                initial=Sample(timestamp=0, value=False),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name=self.KEY_LOCALLY_CONFIGURED, type=bool,
                initial=Sample(timestamp=0, value=False),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name=self.KEY_PACKET_COUNT, type=int,
                initial=Sample(timestamp=0, value=0),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name=self.KEY_REMAINING_BATT_PCT, type=float,
                initial=Sample(timestamp=0, value=0.0),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name=self.KEY_SERIAL_NO, type=str,
                initial=Sample(timestamp=0, value=''),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name=self.KEY_SERVICE_PRESSED, type=bool,
                initial=Sample(timestamp=0, value=False),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
        ]

        #set up the parser
        self.parser = WirelessPacketParser()

        #initialize packet cache
        self.packetCache = None
        self.packetCacheTimestamp = 0

        ## Initialize the XBeeBase interface:
        XBeeBase.__init__(self, self.__name, self.__core,
                                settings_list, property_list)


    ## Functions which must be implemented to conform to the XBeeBase
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
        print 'WirelessSensor Probe called'
        probe_data = XBeeBase.probe()

        for address in WirelessSensor.ADDRESS_TABLE:
            probe_data['address_table'].append(address)
        for product in WirelessSensor.SUPPORTED_PRODUCTS:
            probe_data['supported_products'].append(product)

        return probe_data

    ## Functions which must be implemented to conform to the DeviceBase
    ## interface:

    def apply_settings(self):
        """\
            Called when new configuration settings are available.
       
            Must return tuple of three dictionaries: a dictionary of
            accepted settings, a dictionary of rejected settings,
            and a dictionary of required settings that were not
            found.
        """

        if self.trace:        
            print 'WirelessSensor(%s) apply_settings' % self.__name

        SettingsBase.merge_settings(self)
        accepted, rejected, not_found = SettingsBase.verify_settings(self)

        if len(rejected) or len(not_found):
            # there were problems with settings, terminate early:
            print "Settings rejected/not found: %s %s" % (rejected, not_found)
            return (accepted, rejected, not_found)

        SettingsBase.commit_settings(self, accepted)

        return (accepted, rejected, not_found)

    def start(self):
        """Start the device driver.  Returns bool."""

        if self.trace:        
            print 'WirelessSensor(%s) start' % self.__name

        # Fetch the XBee Manager name from the Settings Manager:
        xbee_manager_name = SettingsBase.get_setting(self, "xbee_device_manager")
        dm = self.__core.get_service("device_driver_manager")
        self.__xbee_manager = dm.instance_get(xbee_manager_name)

        # Register ourselves with the XBee Device Manager instance:
        self.__xbee_manager.xbee_device_register(self)

        # Get the extended address of the device:
        extended_address = SettingsBase.get_setting(self, "extended_address")
        self.addr = (extended_address, 0xe8, 0xc105, 0x11)

        # Retrieve the flag which tells us if we should sleep:

        # Create a callback specification for our device address, endpoint
        # Digi XBee profile and sample cluster id:
        xbdm_rx_event_spec = XBeeDeviceManagerRxEventSpec()
        xbdm_rx_event_spec.cb_set(self.sample_indication)
        xbdm_rx_event_spec.match_spec_set(
            (extended_address, 0xe8, 0xc105, 0x11),
            (True, True, True, True))
        self.__xbee_manager.xbee_device_event_spec_add(self,
                                xbdm_rx_event_spec)

        # Create a callback specification that calls back this driver when
        # our device has left the configuring state and has transitioned
        # to the running state:
        xbdm_running_event_spec = XBeeDeviceManagerRunningEventSpec()
        xbdm_running_event_spec.cb_set(self.running_indication)
        self.__xbee_manager.xbee_device_event_spec_add(self,
                                                        xbdm_running_event_spec)

        # Define a Network Sleep block.
        # This block will NOT send any sleep parameters to the device,
        # but instead, will provide a hint to the Dia about how long
        # we expect our device to sleep for.
        # This is required for long sleeping nodes, as the coordinator
        # and all routers on the network need to know these values.
        xbee_sleep_cfg = XBeeConfigNetworkSleep(extended_address)
        sleep_rate = SettingsBase.get_setting(self, self.KEY_SAMPLE_RATE)
        print('@@ pushing sleep config for %d seconds') % sleep_rate
        sleep_rate *= 1000
        xbee_sleep_cfg.sleep_cycle_set(1, sleep_rate)
        self.__xbee_manager.xbee_device_config_block_add(self, xbee_sleep_cfg)

        # see if there are sensor configurations
        print('loading configuration changes')
        #generate configurations as a dictionary of dictionaries, one for global and
        #one for each serial number as appropriate
        self.configurations = {}
        self.addConfiguration(self.parser.KEY_XMIT_PERIOD, SettingsBase.get_setting(self, self.parser.KEY_XMIT_PERIOD))
        self.addConfiguration(self.parser.KEY_ALARM_EXIT, SettingsBase.get_setting(self, self.parser.KEY_ALARM_EXIT))
        self.addConfiguration(self.parser.KEY_TRIES, SettingsBase.get_setting(self, self.parser.KEY_TRIES))
        self.addConfiguration(self.parser.KEY_HYSTERISIS, SettingsBase.get_setting(self, self.parser.KEY_HYSTERISIS))
        self.addConfiguration(self.parser.KEY_LOG_PERIOD, SettingsBase.get_setting(self, self.parser.KEY_LOG_PERIOD))
        self.addConfiguration(self.parser.KEY_HI_VAL1, SettingsBase.get_setting(self, self.parser.KEY_HI_VAL1))
        self.addConfiguration(self.parser.KEY_HI_TIME1, SettingsBase.get_setting(self, self.parser.KEY_HI_TIME1))
        self.addConfiguration(self.parser.KEY_LO_VAL1, SettingsBase.get_setting(self, self.parser.KEY_LO_VAL1))
        self.addConfiguration(self.parser.KEY_LO_TIME1, SettingsBase.get_setting(self, self.parser.KEY_LO_TIME1))
        self.addConfiguration(self.parser.KEY_HI_VAL2, SettingsBase.get_setting(self, self.parser.KEY_HI_VAL2))
        self.addConfiguration(self.parser.KEY_HI_TIME2, SettingsBase.get_setting(self, self.parser.KEY_HI_TIME2))
        self.addConfiguration(self.parser.KEY_LO_VAL2, SettingsBase.get_setting(self, self.parser.KEY_LO_VAL2))
        self.addConfiguration(self.parser.KEY_LO_TIME2, SettingsBase.get_setting(self, self.parser.KEY_LO_TIME2))

        # Indicate that we have no more configuration to add:
        print('completing configuration')
        self.__xbee_manager.xbee_device_configure(self)

        return True

    def addConfiguration(self, key, values):
        """Configurations are a dictionary of dictionaries with the outside dictionary
           being by serial number/global and the inside being the individual values"""
        for serNo, val in values.iteritems():
            if serNo in self.configurations:
                config = self.configurations[serNo]
            else:
                config = {}
                self.configurations[serNo] = config

            config[key] = val

    def stop(self):
        """Stop the device driver.  Returns bool."""
        if self.trace:        
            print 'WirelessSensor(%s) stopping device driver' % self.__name

        # Unregister ourselves with the XBee Device Manager instance:
        self.__xbee_manager.xbee_device_unregister(self)

        return True
        

    ## Locally defined functions:
    def running_indication(self):
        # request initial status here.
        print "WirelessSensor(%s): running indication" % (self.__name)

    def get_mbus_device_type(self):
        """Returns a string name of the type. No particular meaning is assigned - it can be the class name, but does not need to be."""
        return 'Wireless Sensor'

    def get_mbus_device_code(self):
        return self.SUPPORTED_PRODUCTS[0]

    def export_device_id( self):
        """Return the Device Id response strings"""
        dct = { 0:'Point Wireless', 1:'Xbee wireless sensor', 2:'1.0', 3:'',
                4:'XBee Sensor', 5:'/L/T', 6:'Dia' }
        return dct
    
    def export_base_regs(self,  req_dict) :
        """Return data fields as modbus registers"""
        print ("modbus request dictionary:" + str(req_dict))
        """Return the data"""
        function = req_dict['protfnc']
        if function not in [3, 6]:
            return ""
        offset = req_dict['iofs']
        count = req_dict['icnt']
    
        raw_data = []
        fields = self.parser.fields
        if offset <= len(fields):
            print ("modbus returning:" + str(fields))
            for val in fields:
                x = struct.pack(">f", val)
                raw_data.append(x[0:2])
                raw_data.append(x[2:])
                # values.append(struct.pack(">f", val))
            # raw_data = "".join(values)[offset * 2:count / 2]
    
        return raw_data

    def parseBeacon(self, values):
        print('parsing beacon')
        now = time.time()
        #convert the device ID to a hex string
        devId = values[self.parser.KEY_DEVICE_ID]
        self.property_set(self.KEY_DEVICE_ID, Sample(now, devId, ''))
        #convert the serial number to a hex string
        serNo = hex(values[self.parser.KEY_SER_NO])
        self.property_set(self.KEY_SERIAL_NO, Sample(now, serNo, ''))

        #set the values
        self.property_set(self.KEY_ALARM, Sample(now, bool(values['alarm'] != 0), ''))
        self.property_set(self.KEY_BATTERY_LOW, Sample(now, bool(values['lowBattery']), ''))
        self.property_set(self.KEY_DOOR_OPEN, Sample(now, bool(values[self.parser.KEY_DOOR_OPEN]), ''))
        self.property_set(self.KEY_LOCALLY_CONFIGURED, Sample(now, values['locallyConfigured'], ''))
        self.property_set(self.KEY_LINE_POWERED, Sample(now, values['linePowered'], ''))
        self.property_set(self.KEY_PACKET_COUNT, Sample(now, values['packetCount'], ''))
        self.property_set(self.KEY_SERVICE_PRESSED, Sample(now, values['service'], ''))

        #calculate the battery
        battCount = values['batteryCount']
        self.property_set(self.KEY_BATTERY_COUNT, Sample(now, battCount, ''))
        maxBattCount = values['maxBatteryCount']
        remBattPct = (1.0 - (float(battCount) / float(maxBattCount))) * 100
        if remBattPct < 0.0:
            remBattPct = 0.0;
        self.property_set(self.KEY_REMAINING_BATT_PCT, Sample(now, remBattPct, ''))

        #store the values from the I/O channels
        fields = values['fields']
        units = values['units']
        for idx in range(len(fields)):
            # print('Value:' + str(fields[idx]))
            sampleKey = self.KEY_CHANNEL + str(idx + 1)
            # print('Sample Key:' + sampleKey)
            self.property_set(sampleKey, Sample(now, float(fields[idx]), units[idx]))
            print 'Wireless Sample: %s = %0.3f %s' % \
                  (sampleKey, fields[idx], units[idx])

        #create the acknowledgement
        ack = self.buildAck(serNo)
        self.sendData(ack)

    def parseConfig(self, values):
        print('parsing config')
        #build the configuration from values loaded from the YML file.
        #if values are missing, default to the ones that came in on the
        #configuration record.
        ack = self.parser.buildConfig(
                self.parser.serialNo,
                self.configurations.get(self.parser.KEY_XMIT_PERIOD, values[self.parser.KEY_XMIT_PERIOD]),
                self.configurations.get(self.parser.KEY_ALARM_EXIT, values[self.parser.KEY_ALARM_EXIT]),
                self.configurations.get(self.parser.KEY_TRIES, values[self.parser.KEY_TRIES]),
                self.configurations.get(self.parser.KEY_HYSTERISIS, values[self.parser.KEY_HYSTERISIS]),
                self.configurations.get(self.parser.KEY_LOG_PERIOD, values[self.parser.KEY_LOG_PERIOD]),
                self.configurations.get(self.parser.KEY_HI_VAL1, values[self.parser.KEY_HI_VAL1]),
                self.configurations.get(self.parser.KEY_HI_TIME1, values[self.parser.KEY_HI_TIME1]),
                self.configurations.get(self.parser.KEY_LO_VAL1, values[self.parser.KEY_LO_VAL1]),
                self.configurations.get(self.parser.KEY_LO_TIME1, values[self.parser.KEY_LO_TIME1]),
                self.configurations.get(self.parser.KEY_HI_VAL2, values[self.parser.KEY_HI_VAL2]),
                self.configurations.get(self.parser.KEY_HI_TIME2, values[self.parser.KEY_HI_TIME2]),
                self.configurations.get(self.parser.KEY_LO_VAL2, values[self.parser.KEY_LO_VAL2]),
                self.configurations.get(self.parser.KEY_LO_TIME2, values[self.parser.KEY_LO_TIME2])
                          )
        self.sendData(ack)
        self.configurations = None

    def parsePacket(self, buf):
        print('parsing packet')
        # Parse the I/O sample:
        values = self.parser.parseExtendedPacket(buf)
        print('values:' + str(values))

        cmdId = values[self.parser.KEY_COMMAND]
        if cmdId == 2 or cmdId == 5:
            self.parseBeacon(values)
        elif cmdId == 0x10:
            if self.configurations is not None:
                self.parseConfig(values)

    def sendData(self, data):
        if data:
            self.__xbee_manager.xbee_device_xmit(0xe8, data, self.addr)

    def sample_indication(self, buf, addr):
        """process a sample received from the sensor"""
        try:
            print('sample')

            #create the timestamp for this interaction
            now = time.time()
    
            # set up error handling
            error = []
    
            parsingPacket = True
    
            if len(buf) < self.PACKET_LENGTH:
                print('received buffer of:' + str(len(buf)))
                if self.packetCache==None or self.packetCacheTimestamp + 100 < now:
                    #nothing in the cache or the cache has expired
                    self.packetCache = buf
                    self.packetCacheTimestamp = now
                    parsingPacket = False
                else:
                    #we're appending to the cache
                    self.packetCache = self.packetCache + buf
                    if len(self.packetCache) == self.PACKET_LENGTH:
                        print('Assembled full record')
                        #consume the cache
                        buf = self.packetCache
                        self.packetCache = None
                        self.packetCacheTimestamp = 0
                        parsingPacket = True
                    elif len(self.packetCache) > self.PACKET_LENGTH:
                        print('Discarding too long buffer')
                        #cache is too long, discard it
                        self.packetCache = None
                        self.packetCacheTimestamp = 0
                        parsingPacket = False
                        error.append(self.__name + ' blew cache packet length. Packet and cache discarded.')
                    else:
                        print('Short buffer. Waiting.')
                        #simply not enough to process
                        parsingPacket = False
            elif len(buf) > self.PACKET_LENGTH:
                print ('Packet too long. Discarding.:' + str(len(buf)))
                parsingPacket = False
                error.append(self.__name + ' received packet too long:' + str(len(buf)) + '. Packet discarded.')
    
            if parsingPacket:
                self.parsePacket(buf)
    
            if len(error) > 0:
                self.property_set(self.KEY_ERROR, Sample(now, error, ''))
    
            return
        except:
            print('error found processing sample')
            traceback.print_exc()

    def buildAck(self, serNo):
        """Build a config acknowledgement if there are configurations for the current sensor,
            otherwise return None"""
        if self.configurations is None or len(self.configurations) == 0:
            return None
        ack = None
        #are there global configurations?
        conf = {}
        if self.KEY_GLOBAL in self.configurations:
            #pull global configuration
            conf = self.configurations[self.KEY_GLOBAL]
        if serNo in self.configurations:
            #override with sensor specific configurations
            for key, value in self.configurations[self.KEY_GLOBAL].iterItems():
                conf[key] = value
        if len(conf) > 0:
            print('Building configuration for:' + serNo)
            #reset the configuration for later
            self.configurations = conf
            ack = self.parser.ACK_REQ_CONF

        if ack is None:
            print('Sending acknowledgment')
            ack = self.parser.ACK

        return ack

# internal functions & classes

def main():
    pass

if __name__ == '__main__':
    import sys
    status = main()
    sys.exit(status)

