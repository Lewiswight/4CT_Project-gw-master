############################################################################
#                                                                          #
# Copyright (c)2010 Poi. All Rights Reserved. #
#                                                                          #
# Everyone can use this awesome driver!                                    #
#                                                                          #
# POI SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED    #
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A          #
# PARTICULAR PURPOSE. THE SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, #
# PROVIDED HEREUNDER IS PROVIDED "AS IS" AND WITHOUT WARRANTY OF ANY KIND. #
# DIGI HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES,         #
# ENHANCEMENTS, OR MODIFICATIONS.                                          #
#                                                                          #
# IN NO EVENT SHALL POI OR BLAKE BE LIABLE TO ANY PARTY FOR DIRECT,        #
# SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS,   #
# ARISING OUT OF THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF   #
# POI HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES OR IT HAPPPENS   #
# TO BE THURSDAY.                                                          #
############################################################################

"""\
A device driver for the ConnectPort X4 that gathers RSSI and G3RSSI data on run

Settings:

* **update_rate:** Defines how often the rssi data should be updated, in seconds.

"""

# imports
from devices.device_base import DeviceBase
from settings.settings_base import SettingsBase, Setting
from channels.channel_source_device_property import *

import digi_ElementTree as etree
import threading
import time

# optional imports
try:
    from rci import process_request as process_rci_request
except:
    pass

def simple_rci_query(query_string):
    """\
    Perform an RCI query and return raw RCI response.

    This query uses only socket operations to POST the HTTP request,
    it does not rely on any other external libraries.
    """

    return process_rci_request(query_string)

# constants

# exception classes

# interface functions

# classes

class ConnectportX4(DeviceBase, threading.Thread):

    def __init__(self, name, core_services):
        self.__name = name
        self.__core = core_services

        ## Settings Table Definition:
        settings_list = [
          Setting(
              name='update_rate', type=float, required=False, default_value=60.0,
                verify_function=lambda x: x > 0.0),
        ]

        ## Channel Properties Definition:
        property_list = [
            # gettable properties
            ChannelSourceDeviceProperty(name="rtt", type=float,
                initial=Sample(timestamp=0, value=0.0, unit="dBm"),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ChannelSourceDeviceProperty(name="evdo", type=float,
                initial=Sample(timestamp=0, value=0.0, unit="dBm"),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP)
        ]

        ## Initialize the DeviceBase interface:
        DeviceBase.__init__(self, self.__name, self.__core,
                                settings_list, property_list)

        ## Thread initialization:
        self.__stopevent = threading.Event()
        threading.Thread.__init__(self, name=name)
        threading.Thread.setDaemon(self, True)


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
            print ("%s(%s): settings rejected/not found: %s/%s" %
                    (self.__class__.__name__, self.__name, rejected, not_found))

        SettingsBase.commit_settings(self, accepted)

        return (accepted, rejected, not_found)

    def start(self):
        """Start the device driver.  Returns bool."""
        threading.Thread.start(self)

        return True

    def stop(self):
        """Stop the device driver.  Returns bool."""
        self.__stopevent.set()

        return True

    # Threading related functions:
    def run(self):
        """run when our device driver thread is started"""

        while 1:
            if self.__stopevent.isSet():
                self.__stopevent.clear()
                break

            query_string = """\
              <rci_request version="1.1">
                <query_state><mobile_stats/></query_state>
              </rci_request>"""
            xml = simple_rci_query(query_string)
            print "XML>>>"
            print xml
            response = etree.XML(xml)
            if not response.find('warning'): # check for cellular gateway
              rtt = response.find('rssi').text
              evdo = response.find('g3rssi').text
              self.property_set("rtt", Sample(0, float(rtt), "dBm"))
              self.property_set("evdo", Sample(0, float(evdo), "dBm"))
            time.sleep(SettingsBase.get_setting(self,"update_rate"))

# internal functions & classes

def main():
    pass

if __name__ == '__main__':
    import sys
    status = main()
    sys.exit(status)

