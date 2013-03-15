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
TCPCSV Presentation - a simple TCP client which transmits CSV channel data

Each row of the CSV data is given as:

``channel_name,timestamp,value,unit``

Where timestamp is adjusted to GMT and given in the format

``YYYY-mm-dd HH:MM:SS``

.. Note:: 
    Be careful!  String samples are not escaped for commas at this time.

Configurable settings:

* **server:** The IP address or hostname to connect to.
* **port:** The TCP port number to connect to.
* **interval:** How often (in seconds) to emit CSV data (default: 60 seconds).
* **channels:** A list of channels to include in the data set. If this setting
  is not given, all channels will be included.
"""

# imports
import threading
import time
from StringIO import StringIO
from socket import *

from settings.settings_base import SettingsBase, Setting
from presentations.presentation_base import PresentationBase
from channels.channel import PERM_GET, OPT_DONOTDUMPDATA
from channels.channel_publisher import ChannelDoesNotExist

# constants
RECONNECT_DELAY = 10.0

STATE_NOTCONNECTED = 0x0
STATE_CONNECTED    = 0x1

# classes
class TCPCSV(PresentationBase, threading.Thread):
    def __init__(self, name, core_services):
        self.__name = name
        self.__core = core_services
     
        self.__stopevent = threading.Event()
        
        settings_list = [
                Setting(name="server", type=str, required=True),
                Setting(name="port", type=int, required=True),
                Setting(name='interval', type=int, required=False, default_value=60),
                Setting(name="channels", type=list, required=False, default_value=[]),
        ]
                                                 
        PresentationBase.__init__(self, name=name, settings_list=settings_list)

        threading.Thread.__init__(self, name=name)
        threading.Thread.setDaemon(self, True)
    
    
    def apply_settings(self):
        """Apply settings."""
        
        SettingsBase.merge_settings(self)
        accepted, rejected, not_found = SettingsBase.verify_settings(self)
        SettingsBase.commit_settings(self, accepted)

        return (accepted, rejected, not_found)
    
    def start(self):
        """Starts the presentation object."""
        threading.Thread.start(self)
        return True
 
    def stop(self):
        """Stop the presentation object."""
        self.__stopevent.set()
        return True

    def run(self):
        """Worker thread for the TCPCSV client.""" 

        state = STATE_NOTCONNECTED
        sd = None

        while not self.__stopevent.isSet():
            if state == STATE_NOTCONNECTED:
                server = SettingsBase.get_setting(self, "server")
                port = SettingsBase.get_setting(self, "port")
                sd = socket(AF_INET, SOCK_STREAM)
                try:
                    sd.connect((server, port))
                except Exception, e:
                    print "TCPCSV(%s): error connecting to %s:%d: %s" % \
                        (self.__name, server, port, str(e))
                    time.sleep(RECONNECT_DELAY)
                    continue
                state = STATE_CONNECTED

            if state == STATE_CONNECTED:
                sio = StringIO()
                self._write_channels(sio)
                try:
                        sd.sendall(sio.getvalue())
                except:
                        try:
                                sd.close()
                        except:
                                pass
                        state = STATE_NOTCONNECTED
                        continue
                del(sio)
                time.sleep(SettingsBase.get_setting(self, "interval"))

    def _write_channels(self, sio):
        cm = self.__core.get_service("channel_manager")
        cdb = cm.channel_database_get()
        channel_list = SettingsBase.get_setting(self, "channels")

        if len(channel_list) == 0:
            channel_list = cdb.channel_list()

        for channel_name in channel_list:
            try:
                channel = cdb.channel_get(channel_name)
                if not channel.perm_mask() & PERM_GET:
                    raise Exception, "Does not have GET permission"
                elif channel.options_mask() & OPT_DONOTDUMPDATA:
                    raise Exception, "Do not dump option set on channel"
                sample = channel.get()
                row_data = (channel_name,
                            time.strftime("%Y-%m-%d %H:%M:%S",
                                    time.gmtime(sample.timestamp)),
                            sample.value,
                            sample.unit)
                row_data = map(lambda d: str(d), row_data)
                sio.write(','.join(row_data) + "\r\n")
            except Exception, e:
                print "TCPCSV(%s): error formatting '%s': %s" % \
                        (self.__name, channel_name, str(e))
                pass
