# File: robust_ecm.py
# Desc: receive data from the Brultech ECM1240, uploading as if SunSpec Meter Data

"""\
Use Modbus/TCP to query the Veris H8036 meter
"""

# imports
import struct
import traceback
import types
import digitime

import threading
import socket
from select import select
import gc

from settings.settings_base import SettingsBase, Setting
from samples.sample import *
from core.tracing import get_tracer
from channels.channel_source_device_property import *

from devices.vendors.veris.H8036_object import VerisH8036
from devices.vendors.veris.robust_H8036_sec import MBus_VerisH8036_secondary

# constants

# exception classes

# interface functions

# classes
class MBus_VerisH8036(MBus_VerisH8036_secondary, threading.Thread):

    # over-ride the defaults
    RDB_DEF_POLL_RATE = 15
    RDB_DEF_RESPONSE_TIMEOUT = 0

    DEF_HOST = '("127.0.0.1", 502)'
    
    def __init__(self, name, core_services, settings_in=None, property_in=None):

        ## Local State Variables:
        self.__sock = None

        ## Settings Table Definition:
        settings_list = [
            # Setting( name='sample_rate_sec' is in Robust_Device

            Setting(
                name='host', type=str, required=False,
                default_value=self.DEF_HOST),

        ]

        settings_out = self._safely_merge_lists(settings_in, settings_list)

        ## Channel Properties Definition: assume ecm1240
        # property_list = [ ]

        # Add our property_list entries to the properties passed to us.
        # properties = self._safely_merge_lists(properties, property_list)
        property_out = property_in

        MBus_VerisH8036_secondary.__init__(self, name, core_services, settings_out, property_out)
        
        return

    ## Functions which must be implemented to conform to the DeviceBase
    ## interface:

    def start(self):
        """Start the device driver.  Returns bool."""

        # we only support Modbus/TCP
        self._H8036.set_ModbusTcp()
        
        MBus_VerisH8036_secondary.start(self)
        
        # handle the Primary Gang-Member logic
        if not self.i_am_gang_master():
            # then only do the following for first instance
            raise "Fault: Primary MBus_VerisH8036 must be first instance defined (index=0)"
            
        self._my_tracer.debug("Start - I am Master Driver Instance")
        
        ## Thread initialization
        self.__stopevent = threading.Event()
        threading.Thread.__init__(self, name=self.get_name())
        threading.Thread.setDaemon(self, True)
        
        # start ourself
        threading.Thread.start(self)
        
        return True

    def stop(self):
        """Stop the device driver.  Returns bool."""
        
        # stop our thread
        self.__stopevent.set()

        RobustBase.stop(self)
        return True

    # Threading related functions:
    def run(self):
        """run when our device driver thread is started"""

        self._my_tracer.debug("Thread Started")
        
        while 1:
            if self.__stopevent.isSet():
                self.__stopevent.clear()
                break

            # check if socket is open
            if self.__sock is None:
                if not self.open_socket():
                    continue

            # wait up to 30 seconds for data
            ready = select([self.__sock], [], [], 1.0)
            # ready = select([self.__sock], [], [])
            # self._my_tracer.debug("Select Returned")
            
            if self.__sock in ready[0]:
                data = None
                try:
                    data = self.__sock.recv(1024)
                    if True:
                        print self.show_bytes('recv', data)
                    
                    index = ord(data[1])
                    self._my_tracer.debug("response for gang_member index %d", index)
                    rtn = self.get_gang_memeber(index).parse_response(data)
                    
                except:
                    traceback.print_exc()
                    self.__sock = None
            
        # stopping - clean up
        try:
            self.__sock.close()
        except:
            pass

        self.__sock = None

        return
        
    ## Locally defined functions:
    def next_poll(self, trns_id=0):
        self._my_tracer.debug("Next Poll Prim #%d", trns_id)
        # self.cancel_response_timeout()
        
        # check if socket is open
        if self.__sock is None:
            # say the poll failed - let the thread 'own'
            self._my_tracer.debug("Abort Poll - socket isn't open")
            self.signal_end_of_poll(False)
            return False
                
        # sequence is (random_byte) plus (self._my_gang_index)
        req = self._H8036.get_data_request( chr(self._H8036.get_next_seqno()) + \
                                            chr(self._my_gang_index))
        self.__sock.send(req)
        if True:
            print self.show_bytes('send', req)

        return True

    def open_socket(self):
    
        if self.__sock is not None:
            del self.__sock
            gc.collect()
            
        try:
            host = SettingsBase.get_setting(self, 'host')
            self._my_tracer.debug("See Host %s", host)
            host = eval(host)
            if len(host) < 2:
                raise 'Host needs to be tuple like ("127.0.0.1", 502)'
        
            # open our Modbus/TCP socket
            self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.__sock.setsockopt( socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self.__sock.settimeout( 20.0)
            self.__sock.connect(host)
            
        except socket.error:
            self._my_tracer.warning('Socket connect failed! Loop up and try socket again')
            traceback.print_exc()
            self.__sock = None

        except:
            traceback.print_exc()
            self.__sock = None

        if self.__sock is None:
            self._my_tracer.debug("Open Socket Failed, sleep 60 seconds")
            gc.collect()
            digitime.sleep( 60)
            return False
            
        self._my_tracer.debug("Open Socket Succeeded")
        return True
            