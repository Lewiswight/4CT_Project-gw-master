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
The console presentation.

Provides a command line interface for the iDigi Dia.  All command line
command definitions are given in console_interface.py.  They follow
the standard Python library cmd module interface.  See the documentation
for the cmd module for more information.

When an instance of this console is started using the "type" setting to
be set to "tcp" the console may be connected to using a standard telnet
client by connecting the telnet client to the port given by the the
"port" setting.  The default port is 4146.


Settings:

* **type:** must be set to either "tcp" or "serial" (default value: "tcp")
* **port:** if type is set to "tcp", this is an integer value TCP port number
  that the console will start upon (default value: 4146).
* **device:** if type is set to "serial", this is the serial port device name
  that will be used. (default value: "/com/0").
* **baudrate:** if type is set to "serial", this is the baud rate that will
  be used. (default value: 115200).
"""

# imports
from settings.settings_base import SettingsBase, Setting
from presentations.presentation_base import PresentationBase
import threading
from presentations.console.console_tcp_server \
    import ConsoleTcpServer, ConsoleTcpRequestHandler
from presentations.console.console_serial_server import ConsoleSerialServer

# constants

# exception classes

# interface functions

# classes

class Console(PresentationBase, threading.Thread):
    def __init__(self, name, core_services):
        self.__name = name
        self.__core = core_services

        settings_list = [
            Setting(
                name='type', type=str, required=False, default_value="tcp"),
            Setting(
                name='port', type=int, required=False, default_value=4146),
            Setting(
                name='device', type=str, required=False, default_value="/com/0"),
            Setting(
                name='baudrate', type=int, required=False, default_value=115200),
        ]

        ## Initialize settings:
        PresentationBase.__init__(self, name=name,
                                    settings_list=settings_list)

        ## Thread initialization:
        self.__stopevent = threading.Event()
        threading.Thread.__init__(self, name=name)
        threading.Thread.setDaemon(self, True)

    def apply_settings(self):
        SettingsBase.merge_settings(self)
        accepted, rejected, not_found = SettingsBase.verify_settings(self)

        SettingsBase.commit_settings(self, accepted)

        return (accepted, rejected, not_found)

    def start(self):
        """Start the console instance.  Returns bool."""
        threading.Thread.start(self)
        self.apply_settings()
        return True

    def stop(self):
        """Stop the console instance.  Returns bool."""
        self.__stopevent.set()
        return True

    def run(self):
        """\
        Console thread method.
        
        This function is not intended to be called directly.
        """ 

        type = SettingsBase.get_setting(self, "type")
        if type == "serial":
            server = ConsoleSerialServer(
                                    SettingsBase.get_setting(self, "device"),
                                    SettingsBase.get_setting(self, "baudrate"),
                                    self.__core)
        else:
            server = ConsoleTcpServer(('', 
                                    SettingsBase.get_setting(self, "port")),
                                    ConsoleTcpRequestHandler, self.__core)
        try:
            server.serve_forever()
        except Exception, e:
            print ("%s(%s): WARNING console service terminated prematurely: %s"
                       % (self.__class__.__name__, self.__name, str(e)))



# internal functions & classes

def main():
    pass

if __name__ == '__main__':
    import sys
    status = main()
    sys.exit(status)

