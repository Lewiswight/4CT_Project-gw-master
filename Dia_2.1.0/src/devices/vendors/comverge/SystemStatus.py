#SystemStatus driver for the iDigi Dia
#Monitors system stats for the connectport X4 and X8
#Author: Mike Esselman
#Company: Spectrum Design

#Typical configuration
#devices:
#  - name: systemMon
#    driver: devices.vendors.comverge.SystemStatus:SystemStatus
#    settings:
#        update_rate: 600

"""\
This is an driver iDigi Dia.  It creates channels in the Dia to display
critical system stats.  It will show Free Memory, CPU utilization as a percent,
mobile connectivity, and iDigi connectivity.
Settings:
    update_rate: defines how fast the counter should update, in seconds.

"""

# imports
from devices.device_base import DeviceBase
from settings.settings_base import SettingsBase, Setting
from channels.channel_source_device_property import ChannelSourceDeviceProperty, Sample, DPROP_PERM_GET, DPROP_OPT_AUTOTIMESTAMP
from common.types.boolean import Boolean, STYLE_ONOFF
import rci
import re
import digicli
import string
import sys
import zigbee
import struct


class SystemStatus(DeviceBase):

    def __init__(self, name, core_services):
        self.__name = name
        self.__core = core_services
        print "SystemStatus: initializing class"

        ## Settings Table Definition:
        settings_list = [
            Setting(name='update_rate', type=float, required=False, default_value=300.0),
            Setting(name='no_mobile', type=bool, required=False, default_value=False),
            Setting(name='no_zigbee', type=bool, required=False, default_value=False),
        ]

        ## Channel Properties Definition:
        property_list = [
            # gettable & settable properties
            ChannelSourceDeviceProperty(name="free_memory", type=int,
                initial=Sample(timestamp=0, unit="bytes", value=0),
                perms_mask=(DPROP_PERM_GET),options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name="cpu_utilization", type=int,
                initial=Sample(timestamp=0, unit="%", value=0),
                perms_mask=(DPROP_PERM_GET), options=DPROP_OPT_AUTOTIMESTAMP),
            #ChannelSourceDeviceProperty(name="mobile_status", type=str,
             #   initial=Sample(timestamp=0, value="N/A"),
             #   perms_mask=(DPROP_PERM_GET), options=DPROP_OPT_AUTOTIMESTAMP),
            #ChannelSourceDeviceProperty(name="mobile_rssi", type=int,
             #   initial=Sample(timestamp=0, value=0),
              #  perms_mask=(DPROP_PERM_GET), options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name="idigi_status", type=str,
                initial=Sample(timestamp=0, value="N/A"),
                perms_mask=(DPROP_PERM_GET), options=DPROP_OPT_AUTOTIMESTAMP),
        ]

        ## Initialize the DeviceBase interface:
        DeviceBase.__init__(self, self.__name, self.__core,
                                settings_list, property_list)

        print "Setting no_mobile:",SettingsBase.get_setting(self, "no_mobile")
        if not SettingsBase.get_setting(self,"no_mobile"):
            print "adding mobile properties"
            self.add_property(ChannelSourceDeviceProperty(name="mobile_rssi", type=int,
                initial=Sample(timestamp=0, value=0),
                perms_mask=(DPROP_PERM_GET), options=DPROP_OPT_AUTOTIMESTAMP))
            self.add_property(ChannelSourceDeviceProperty(name="mobile_status", type=str,
                initial=Sample(timestamp=0, value="N/A"),
                perms_mask=(DPROP_PERM_GET), options=DPROP_OPT_AUTOTIMESTAMP))
        self.apply_settings()

        print "Setting no_zigbee:",SettingsBase.get_setting(self, "no_zigbee")
        if not SettingsBase.get_setting(self,"no_zigbee"):
            print "adding zigbee properties"
            self.add_property(ChannelSourceDeviceProperty(name="zigbee_coord_rssi", type=int,
                initial=Sample(timestamp=0, value=0),
                perms_mask=(DPROP_PERM_GET), options=DPROP_OPT_AUTOTIMESTAMP))
        self.apply_settings()



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
        SettingsBase.merge_settings(self)
        accepted, rejected, not_found = SettingsBase.verify_settings(self)
        if len(rejected) or len(not_found):
            print "Settings rejected/not found: %s %s" % (rejected, not_found)

        SettingsBase.commit_settings(self, accepted)

        return (accepted, rejected, not_found)

    def start(self):
        """Start the System Status driver.  Schedules the first polling of stats"""
        self.schedule_polling()
        return True

    def stop(self):
        """Stop the device driver.  Returns bool."""
        print "SystemStatus: end polling thread"
        return True

    def poll_stats(self):
        """rci and cli requests for digi device stats"""
        print "SystemStatus:  Polling system stats"
        #find cpu utilization percent and free memory
        try:
            msg = "<rci_request version=\"1.1\"><query_state><device_stats/></query_state></rci_request>"
            resp = rci.process_request(msg)
            cpuPercent = re.search("<cpu>(\S+)</cpu>", resp).group(1)
            self.property_set("cpu_utilization", Sample(0, int(cpuPercent), "%"))
            freeMemory = re.search("<freemem>(\S+)</freemem>", resp).group(1)
            self.property_set("free_memory", Sample(0, int(freeMemory), "bytes"))
            self.schedule_polling()
        except: pass

        if not SettingsBase.get_setting(self,"no_zigbee"):
          try:
          # look for configure and read from all active XBee nodes
              node_list = []
              print 'Device discovery in progress. Please wait ...'
              nodes = zigbee.getnodelist(True)
              print '\nActive node list of extended addresses'
              for node in nodes:
                  print node.addr_short, ' ', node.addr_extended, ' ', node.label

              # now for each node try to retrieve a sample
              for node in nodes:
                  if node.type != "router":
                     xtn_addr = node.addr_extended
                     # store the active node extended addr for later use
                     node_list.append(xtn_addr)
                     # print the attributes of each active node
#                     print '\naddr_extended: %s' % node.addr_extended
#                     print 'addr_short: %s' % node.addr_short
#                     print 'addr_parent: %s' % node.addr_parent
#                     print 'profile_id: %s' % node.profile_id
#                     print 'manufacturer_id: %s' % node.manufacturer_id
#                     print 'label: %s' % node.label
#                     print 'type: %s' % node.type
#                      try:
#                          module_type, product_type = GetXBeeDeviceType(xtn_addr)
#                          print 'module_type: %s' % module_type
#                          print 'product_type: %s' % product_type
#                      except Exception, e:
#                          print 'GetXBeeDeviceType error: %s' % e
#
                      # get some node configuration info using ddo_get
                     try:
                         rssi_raw = zigbee.ddo_get_param(xtn_addr,'DB')
                         zb_rssi = 0-struct.unpack('=B',rssi_raw)[0]
                         print 'Zigbee Coordinator rssi : %s ' % zb_rssi
                         self.property_set("zigbee_coord_rssi", Sample(0, zb_rssi))
                         vr_raw = zigbee.ddo_get_param(xtn_addr,'VR')
                         #print 'firmware version: %s' % hex(struct.unpack('>H',vr_raw)[0])
                     except Exception, e:
                          print 'ddo_get error: %s' % e
          except: pass

        #find mobile connectivity status
        if not SettingsBase.get_setting(self,"no_mobile"):
            try:
                msg = "<rci_request version=\"1.1\"><query_state><mobile_stats/></query_state></rci_request>"
                resp = rci.process_request(msg)
                rssi = re.search("<rssi>(\S+)</rssi>", resp).group(1)
                try:
                    i_rssi = int(rssi)
                except ValueError:
                    i_rssi = 0
                self.property_set("mobile_rssi", Sample(0, i_rssi))
                statsIndex = re.search("<stats_index>(\S+)</stats_index>", resp).group(1)
                msg = "<rci_request version=\"1.1\"><query_state><ppp_stats index=\""+statsIndex+"\"/></query_state></rci_request>"
                resp = rci.process_request(msg)
                mobileStatus = re.search("<ppp_stats index=\""+statsIndex+"\"><state>(\S+)</state>", resp).group(1)
                self.property_set("mobile_status", Sample(0, mobileStatus))
            except: pass

        #find idigi connectivity status
        try:
            msg = "who"
            status, response = digicli.digicli(msg)
            if status:
                #response is a list of strings for each line.  Convert into single string.
                responseStr = string.join(response, "")
                #responseStr = ""
                #for line in response:
                #    responseStr += line
                if ((responseStr.find("connectware") == -1) and (responseStr.find("idigi") == -1)):
                    self.property_set("idigi_status", Sample(0, "disconnected"))
                else:
                    self.property_set("idigi_status", Sample(0, "connected"))
        except: pass

    def schedule_polling(self):
        """inserts a scheduled call for polling in Dia Scheduler"""
        sleepTime = SettingsBase.get_setting(self,"update_rate")
        sch = self.__core.get_service("scheduler")
        sch.schedule_after(sleepTime,self.poll_stats)

def main():
    pass
if __name__ == '__main__':
    import sys
    status = main()
    sys.exit(status)

