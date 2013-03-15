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
XMLRPC Server Presentation for iDigi Device Integration Application

Settings:

* **port:** tcp port number (default: 80)
* **use_default_httpserver:** True/False (default: True), if set to True
  the XMLRPC server will start on its own port number.  If false, XMLRPC 
  services will be available on the default webserver built in to the Digi 
  device.

The address of the XMLRPC server will be::

    http://<address of the device>/RPC2

The following methods are supported:

* ``device_instance_list()``: Receive a list of devices
* ``channel_list()``: Receive a list of all channels
* ``channel_get(channel_name)``: Get the current sample on a channel given
  by channel_name.
* ``channel_set(channel_name, timestamp, value, unit, autotimestamp = True)``:
  Set a channel with the values given by the arguments. If autotimestamp
  is being used set timestamp = 0.
* ``channel_info(channel_name)``: Get the channel permissions and options given
  by channel_name.
* ``channel_refresh(channel_name)``: Request that a channel given by channel_name 
  is refreshed.
* ``channel_dump()``: Dump all channels with their current values.
* ``logger_list()``: Receive a list of loggers running.
* ``logger_set(logger_name)``: Sets the logger database for the presentation 
  to use.
* ``logger_dump()``: Dump all channels for the current logger at the point of 
  the current sample in the log file.
* ``logger_next()``: Obtain the next record from current position.
* ``logger_prev()``: Obtain the previous record from current position.
* ``logger_rewind()``: Seek to the first logged record.
* ``logger_seek(self, offset, whence='set', record_number=0)``: Seek to the
  record specified by the arguments.

"""

# imports
import sys, traceback
from select import select
import threading
import time
import types
from SimpleXMLRPCServer import SimpleXMLRPCServer, \
                            SimpleXMLRPCRequestHandler, SimpleXMLRPCDispatcher

from settings.settings_base import SettingsBase, Setting
from channels.channel import \
    PERM_GET, PERM_SET, PERM_REFRESH, \
    OPT_AUTOTIMESTAMP, OPT_DONOTLOG, OPT_DONOTDUMPDATA    
from presentations.presentation_base import PresentationBase
from samples.sample import Sample
from common.helpers.format_channels import iso_date
from channels.channel_database_interface import \
    LOG_SEEK_SET, LOG_SEEK_CUR, LOG_SEEK_END, LOG_SEEK_REC
from common.types.boolean import Boolean

try:
    import digiweb
except:
    pass

# constants

# exception classes

# interface functions

# classes
class CustomXMLRPCRequestHandler(SimpleXMLRPCRequestHandler):
    """\
    This custom handler is only used when uses the SimpleXMLRPCServer
    instance, running as its own separate thread.

    It is implemented to allow for debugging of XMLRPC requests by
    uncommenting print statements.
    """

    def do_POST(self):
        clientIP, port = self.client_address
#        print 'Client IP: %s - Port: %s' % (clientIP, port)

        response = None
        try:
            # get arguments
            data = self.rfile.read(int(self.headers["content-length"]))
            # Log client request
#             print 'Client request: \n%s\n' % data
            response = self.server._marshaled_dispatch(
                                                       data, getattr(self, '_dispatch', None)
                                                       )
#             print 'Server response: \n%s\n' % (response)
        except:
            # This should only happen if the module is buggy
            # internal error, report as HTTP server error
            print "Exception occured during XMLRPC request:"
            print '-'*60
            traceback.print_exc(file=sys.stdout)
            print '-'*60
            self.send_response(500)
            self.end_headers()
            return
    
        # got a valid XML RPC response
        self.send_response(200)
        self.send_header("Content-type", "text/xml")
        self.send_header("Content-length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)
    
        # shut down the connection
        self.wfile.flush()
        self.connection.shutdown(1)


class DigiWebXMLRPCRequestHandler(SimpleXMLRPCDispatcher):
    def __init__(self):
        SimpleXMLRPCDispatcher.__init__(self)

class XMLRPCAPI:
    
    ERR_UNSELECTED_LOGGER = 'Error: No logger currently selected'
    ERR_UNKNOWN_LOGGER = 'Error: Unknown logger'
    
    __logger = None
    __logger_cdb = None
    
    def __init__(self, core_services):
        """
            Class initialization method.
        """
        self.__core = core_services
        self.__cdb = (self.__core.get_service("channel_manager")
                       .channel_database_get())

    def device_instance_list(self):
        """
            Returns a list with the Dia devices. Builds a response for a 
            'device_instance_list' request.
        """
        
        dm = self.__core.get_service("device_driver_manager")
        return dm.instance_list()

    def channel_list(self, startswith=""):
        """
            Returns all the Dia channels. Builds a response for a 
            'channel_list' request.
        """
        
        channel_list = self.__cdb.channel_list()
        if len(startswith) > 0:
            channel_list = filter(lambda li: li.startswith(startswith),
                                  channel_list)

        return channel_list

    def _marshal_sample(self, sample):
        """
        Marshal a :class:`Sample` object for XML-RPC representation.

        Returns a dictionary suitable for processing by the
        :class:`SimpleXMLRPCRequestHandler` class.

        This is an internal method which special-cases the attributes
        of the :class:`Sample` object.  Attributes on :class:`Sample`
        objects are type-mapped for representation in the following
        manner:

          * The internal type :class:`Boolean` will be mapped to its
            string value.
          * All other values shall be mapped to their string representation
            by calling the Python built-in :func:`repr` function.
        """
        return_dict = { }
        for member in filter(lambda m: not m.startswith('__'), dir(sample)):
            return_dict[member] = getattr(sample, member)
            # attempt to marshall complex instance types to their string reps:            
            try:
                if isinstance(return_dict[member], Boolean):
                    return_dict[member] = bool(return_dict[member])
                elif type(return_dict[member]) == types.InstanceType:
                    return_dict[member] = repr(return_dict[member])
            except:
                return_dict[member] = "unrepresentable object"
                    
        return return_dict
            
    def __write_channel_database(self, chdb, channel_prefix=""):
        """
            Returns a dictionary of channel dictionaries.
        """
        
        channel_list = filter(lambda c: c.startswith(channel_prefix),
                              chdb.channel_list())
        channels = { }
        for channel_name in channel_list:
            try:
                sample = chdb.channel_get(channel_name).get()
            except Exception, e:
                sample = Sample(value="(N/A)")
            channels[channel_name] = self._marshal_sample(sample)
            
        return channels

    def channel_get(self, channel_name):
        """
            Returns the information of specified channel. Builds a 
            response for a 'channel_get' request.
        """
        
        channel = self.__cdb.channel_get(channel_name)
        sample = channel.get()
        return_dict = self._marshal_sample(sample)

        return return_dict

    def channel_set(self, channel_name,
                    timestamp, value, unit = "", autotimestamp = False):
        """\
            Configures the given channel with specified information.
             
            Builds a response for a 'channel_set' request.
        """
        
        if autotimestamp:
            timestamp = time.time()
        channel = self.__cdb.channel_get(channel_name)
        try:
            sample = Sample(timestamp, channel.type()(value), unit)
        except Exception, e:
            raise Exception, "unable to coerce value '%s' to type '%s'" % \
                (value, repr(channel.type()))

        channel.set(sample)

        return True
    
    def channel_dump(self, channel_prefix=""):
        """\
            Returns all the channels with their information.
            
            Builds a response for a 'channel_dump' request.
        """
        
        return self.__write_channel_database(self.__cdb)

    def channel_info(self, channel_name):
        """\
            Returns the information of specified channel.
            
            Builds a response for a 'channel_info' request.
        """
        
        channel = self.__cdb.channel_get(channel_name)
        return_dict = {
            'permissions': {
                'get': False,
                'set': False,
                'refresh': False,
            },
            'options': {
                'auto_timestamp': False,
                'do_not_log_data': False,
            }
        }
        perms_table = {
            PERM_GET: "get",
            PERM_SET: "set",
            PERM_REFRESH: "refresh",
        }
        options_table = {
            OPT_AUTOTIMESTAMP: "auto_timestamp",
            OPT_DONOTLOG: "do_not_log_data",
            OPT_DONOTDUMPDATA: "do_not_dump_data",
        }
        for section, tbl, mask in (
                ('permissions', perms_table, channel.perm_mask()),
                ('options', options_table, channel.options_mask())):
           for k in tbl:
               if k & mask:
                   return_dict[section][tbl[k]] = True

        return return_dict


    def channel_refresh(self, channel_name):
        """
            Requests the the channel_name perform an immediate update of 
            its Sample.
        """
        
        channel = self.__cdb.channel_get(channel_name)
        channel.consumer_refresh()

        return True
    
    def logger_list(self):
        """\
            Returns a list of running Dia loggers.
        """
        
        # Obtain the list of loggers
        cm = self.__core.get_service("channel_manager")
        return cm.channel_logger_list()
    
    def logger_set(self, logger_name=''):
        """\
            Set the logger instance which the XML-RPC presentation will use.
            
            This initiates possible shared state between multiple XML-RPC
            clients.  If using multiple logging instances, this simple method
            may not be sufficient to provide access.
        """
        
        cm = self.__core.get_service("channel_manager")
        
        # Check if given logger exists, else return False
        if not cm.channel_logger_exists(logger_name):
            raise Exception, "Error: unknown logger '%s'" % logger_name

        # Set our local logger
        try:
            self.__logger = cm.channel_logger_get(logger_name)
            self.__logger_cdb = self.__logger.channel_database_get()
        except Exception, e:
            raise Exception, "Error: Can't set logger %s (%s)" % (
                logger_name, str(e))

        return True
        
    def logger_next(self):        
        """\
            Advance the current logger database instance to the next record.
        """      
        if self.__logger is None:
            raise Exception, ERR_UNSELECTED_LOGGER

        try:
            self.__logger_cdb.log_next()
        except Exception, e:
            raise Exception, "Error: Unable to proceed to next record: %s" \
                  % str(e)

        return True

    def logger_prev(self):        
        """\
            Advance the current logger database instance to the next record.
        """      
        if self.__logger is None:
            raise Exception, ERR_UNSELECTED_LOGGER

        try:
            self.__logger_cdb.log_prev()
        except Exception, e:
            raise Exception, "Error: Unable to proceed to previous record: %s" \
                  % str(e)

        return True

    def logger_rewind(self):        
        """\
            Seek to the first logged record.
        """
        
        if self.__logger is None:
            raise Exception, ERR_UNSELECTED_LOGGER

        try: 
            self.__logger_cdb.log_rewind()
        except Exception, e:
            raise Exception, "Error: Unable to rewind: %s" % str(e)

        return True

    def logger_seek(self, offset, whence="set", record_number=0):
        """\
            Seek the current logger to position.
            
            'offset' is an integer
            
            'whence' is given as a string and may be of the following values:
            
            * **set:** seek 'offset' records from the earliest record in the log
            * **cur:** seek 'offset' records from the current record in the log
            * **end:** seek 'offset' records from the last record in the log
            * **rec:** seek to an absolute record number given by
                       'record_number' and then seek 'offset' records from that
                       mark.
            
            The default value of 'whence' is 'set'
                     
            'record_number' is an absolute record number which only applies when
            'whence' is rec.
"""

        if self.__logger is None:
            raise Exception, ERR_UNSELECTED_LOGGER

        whence_map = { 'set': LOG_SEEK_SET,
                       'cur': LOG_SEEK_CUR,
                       'end': LOG_SEEK_END,
                       'rec': LOG_SEEK_REC, }
        if whence not in whence_map:
            raise Exception, \
                  "Error: Bad whence '%s', must be set, cur, end or rec" % (
                     repr(whence))
        try:
            self.__logger_cdb.log_seek(offset,
                                       whence_map[whence],
                                       record_number)
        except Exception, e:
            raise Exception, "Error: Unable to seek: %s" % str(e)

        return True
            
    def logger_dump(self):        
        """\
            Return a snapshot of the current logging channel database.
        """
        
        # Check if there is a logger set
        if self.__logger is None:
            return self.ERR_UNSELECTED_LOGGER
        else:
            return self.__write_channel_database(self.__logger_cdb)

    def logger_channel_get(self, channel_name):        
        """\
            Returns data for a single channel from the logger DB.
        """

        # Check if there is a logger set
        if self.__logger is None:
            return self.ERR_UNSELECTED_LOGGER

        channel = self.__logger_cdb.channel_get(channel_name)
        sample = channel.get()
        return self._marshal_sample(sample)

    def logger_pos(self):
        """\
           Return the currently active record number in the logger database
           instance.
        """
        # Check if there is a logger set
        if self.__logger is None:
            raise Exception, self.ERR_UNSELECTED_LOGGER

        position = self.__logger_cdb.log_position()
        if position == None:
            raise Exception, "Error: No currently active position"
        
        return position
        
class XMLRPC(PresentationBase, threading.Thread):
    def __init__(self, name, core_services):
        """Initialize XMLRPC presentation"""
        
        self.__name = name
        self.__core = core_services

        self.__digiweb_cb_handle = None
        self.__digiweb_xmlrpc = None

        settings_list = [
            Setting(
              name='port', type=int, required=False, default_value=80),
            Setting(
              name='use_default_httpserver', type=bool, required=False,
              default_value=True),
        ]


        ## Initialize settings:
        PresentationBase.__init__(self, name=name,
                                  settings_list=settings_list)

        ## Thread initialization:
        self.__stopevent = threading.Event()
        threading.Thread.__init__(self, name=name)
        threading.Thread.setDaemon(self, True)

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

        SettingsBase.commit_settings(self, accepted)

        return (accepted, rejected, not_found)

    def start(self):
        """Start the console instance.	Returns bool."""
        is_default = SettingsBase.get_setting(self, 'use_default_httpserver')
        # Always start a separate server on systems without digiweb's Callback
        if not globals().has_key('digiweb'):
            is_default = False
        if is_default:
            # Register digiweb callback:
            self.__digiweb_cb_handle = digiweb.Callback(self.digiweb_cb)
            self.__digiweb_xmlrpc = DigiWebXMLRPCRequestHandler()
            self.__digiweb_xmlrpc.register_introspection_functions()
            self.__digiweb_xmlrpc.register_instance(XMLRPCAPI(self.__core))
        else:
            # Only start a thread if the Python web-server is used:
            threading.Thread.start(self)
	return True

    def stop(self):
        """Stop the console instance.  Returns bool."""
        self.__stopevent.set()
        if self.__digiweb_cb_handle:
            self.__digiweb_cb_handle = None
        if self.__digiweb_xmlrpc:
            self.__digiweb_xmlrpc = None
        return True

    def digiweb_cb(self, http_req_type, path, headers, args):
        if not path.endswith('/RPC2'):
            return None

        response = None
        try:
            response = self.__digiweb_xmlrpc._marshaled_dispatch(
                         args,
                         getattr(self.__digiweb_xmlrpc, "_dispatch", None))
        except:
            print "Exception occured during XMLRPC request:"
            print '-'*60
            traceback.print_exc(file=sys.stdout)
            print '-'*60
            return (None, '')

        return (digiweb.TextXml, response)


    def run(self):
        """\
        Body of XML-RPC presentation thread

        This will be called as part of the execution of the Thread
        portion of the XML-RPC presentation.  Do not call this routine
        manually.
        """
        
        port = SettingsBase.get_setting(self, "port")
        print "XMLRPC(%s): starting server on port %d" % \
            (self.__name, port)
        xmlrpc_server = SimpleXMLRPCServer(
                                           addr=('', port),
                                           requestHandler=CustomXMLRPCRequestHandler,
                                           logRequests=0)
        xmlrpc_server.register_introspection_functions()
        xmlrpc_server.register_instance(XMLRPCAPI(self.__core))

        try:
            # Poll the stop event flag at a minimum of each second:
            while not self.__stopevent.isSet():
                rl, wl, xl = select([xmlrpc_server.socket], [], [], 1.0)
                if xmlrpc_server.socket in rl:
                    xmlrpc_server.handle_request()
        except:
            print "Exception occured during XMLRPC request:"
            print '-'*60
            traceback.print_exc(file=sys.stdout)
            print '-'*60


# internal functions & classes

def main():
    pass

if __name__ == '__main__':
    import sys
    status = main()
    sys.exit(status)

