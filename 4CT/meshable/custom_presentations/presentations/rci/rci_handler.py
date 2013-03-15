############################################################################
#                                                                          #
# Copyright (c)2009, Digi International (Digi). All Rights Reserved.       #
#                                                                          #
# Permission to use, copy, modify, and distribute this software and its    #
# documentation, without fee and without a signed licensing agreement, is  #
# hereby granted, provided that the software is used on Digi products only #
# and that the software contain this copyright notice, and the following   #
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
The RCIHandler presentation layer allows for interaction with the
iDigi Dia through RCI.

The only configurable option is the target_name, which is the target you
specify in your RCI request so that it gets forwarded to this handler.

An example configuration::

    presentations:
      - name: rci_handler
        driver: presentations.rci.rci_handler:RCIHandler
        settings:
            target_name: idigi_dia

##########################################################################

The RCIHandler allows for channel dumps, querying a channel, and setting
a channel. It also includes several requests to interact with the logging 
sub-system to read and move inside of a determined log file. 

The RCIHandler parses an incoming XML formatted message
to determine what you wish to do.  The messages are shown below.  If
an error is encountered, the request you sent will have a child error
element specifying the error information.

Channel Dump
------------
**Request** code::

    <channel_dump/>

**Response** code::

    <channel_dump>
        <device name="...">
            <channel name="..." value="..." units="..." timestamp="..."/>
            ...
        </device>
        ...
    </channel_dump>

Channel Get
-----------
**Request** code::

    <channel_get name="..."/>

**Response** code::

    <channel_get name="..." value="..." units="..." timestamp="..."/>

Channel Refresh
-----------
**Request** code::

    <channel_refresh name="..."/>

**Response** code::

    <channel_refresh name="..." />

Channel Set
-----------
**Request** code::

    <channel_set name="..." value="..."/>

**Response** code::

    <channel_set name="..." value="..." units="..." timestamp="..."/>

Channel Info
------------
**Request** code::

    <channel_info name="..."/>

**Response** code::

    <channel_info name="...">
        <permissions>
            <get/>
            <set/>
            <refresh/>
        <permissions>
        <options>
            <auto_timestamp/>
            <do_not_log_data/>
        <options>
    </channel_info>

Logger List
-----------
**Request** code::

    <logger_list/>

**Response** code::

    <logger_list>
        <logger name="..."/>
        ...
    </logger_list>

Logger Set
----------
**Request** code::

    <logger_set name"...">

**Response** code::

    <logger_set name="...">
    </logger_set>

Logger Dump
-----------
**Request** code::

    <logger_dump/>

**Response** code::

    <logger_dump name="...">
        <device name="...">
            <channel name="..." value="..." units="..." timestamp="..."/>
            ...
        </device>
        ...
    </logger_dump>

Logger Next
-----------
**Request** code::

    <logger_next/>

**Response** code::

    <logger_next name="...">
    </logger_next>

Logger Previous
---------------
**Request** code::

    <logger_prev/>

**Response** code::

    <logger_prev name="...">
    </logger_prev>

Logger Rewind
-------------
**Request** code::

    <logger_rewind/>

**Response** code::

    <logger_rewind name="...">
    </logger_rewind>

Logger Seek
-----------
**Request** code::

    <logger_seek offset="0" whence="end" />

**Response** code::

    <logger_seek name="...">
    </logger_seek>
"""

# imports
import xml.parsers.expat
import threading
import time
import rci
import sys, traceback

from settings.settings_base import SettingsBase, Setting
from presentations.presentation_base import PresentationBase
from channels.channel import \
    PERM_GET, PERM_SET, PERM_REFRESH, \
    OPT_AUTOTIMESTAMP, OPT_DONOTLOG, OPT_DONOTDUMPDATA
from samples.sample import Sample
from StringIO import StringIO
from common.helpers.format_channels import iso_date
from channels.channel_database_interface import \
    LOG_SEEK_SET, LOG_SEEK_CUR, LOG_SEEK_END, LOG_SEEK_REC

# constants
ENTITY_MAP = {
    "<": "&lt;",
    ">": "&gt;",
    "&": "&amp;",
}

# classes

class RCIHandler(PresentationBase):
    ERR_PARSE_ERROR = '<error>Parse Error</error>'
    ERR_MISSING_ATTRIBUTE = '<error>Missing Attribute</error>'
    ERR_MISSING_ELEMENT = '<error>Missing Element</error>'
    ERR_UNKNOWN_CHANNEL = '<error>Unknown Channel</error>'
    ERR_INVALID_SAMPLE_VALUE = '<error>Invalid Sample Value</error>'
    ERR_SET_FAILED = '<error>Unable To Set Channel</error>'
    ERR_UNKNOWN_LOGGER = '<error>Unknown Logger</error>'
    ERR_UNSELECTED_LOGGER = '<error>No Logger Selected</error>'
    ERR_REFRESH = '<error>Refresh Error</error>'

    __logger = None
    __logger_cdb = None

    def __init__(self, name, core_services):
        """Create an instance of the RCIHandler"""
    
        self.__name = name
        self.__core = core_services
    
        settings_list = [
                         Setting(
                                 name='target_name', type=str, 
                                 required=False, default_value='idigi_dia'),
                        ]
    
        ## Initialize settings:
        PresentationBase.__init__(self, name=name,
                                  settings_list=settings_list)

    def apply_settings(self):
        """\
        Call down inheritance tree to :class:`SettingsBase` implementation

        For some reason :class:`PresentationBase` re-implements suitable
        default functionality from :class:`SettingsBase` as a
        `NotImplementedError`.
        """
        return SettingsBase.apply_settings(self)

    def start(self):
        """Start listening for messages on the specified target"""
    
        target_name = SettingsBase.get_setting(self, 'target_name')
    
        add_callback = lambda name=target_name: rci.add_rci_callback(
                            name, self.__rci_callback)
    
        threading.Thread(target=add_callback).start()

    def stop(self):
        """Stop listening for messages"""
    
        target_name = SettingsBase.get_setting(self, 'target_name')
    
        rci.stop_rci_callback(target_name)

    def __escape_entities(self, sample_value):      
        if not isinstance(sample_value, str):
            return sample_value
        for ch in ENTITY_MAP:
            sample_value = sample_value.replace(ch, ENTITY_MAP[ch])

        return sample_value

    def __unescape_entities(self, sample_value):      
        if not isinstance(sample_value, str):
            return sample_value
        inv_entity_map = dict(zip(ENTITY_MAP.values(), ENTITY_MAP.keys()))
        for pat in inv_entity_map:
            sample_value = sample_value.replace(pat, inv_entity_map[pat])

        return sample_value

    def __rci_callback(self, message):
        """
            Called whenever there is an incoming RCI message with
            our specified target.
        
            Keyword arguments:
            message -- the value that is intended for us from RCI
        """
    
        self.__parser = xml.parsers.expat.ParserCreate()
        self.__parser.StartElementHandler = self.__handle_start_element
        self.__parser.EndElementHandler = self.__handle_end_element
        self.__reply = ""
    
        try:
            self.__parser.Parse(message)
        except xml.parsers.expat.ExpatError:
            self.__reply = RCIHandler.ERR_PARSE_ERROR
        except Exception, e:
            print "-" * 60
            print "%s(%s): exception during RCI processing: %s" % (
                self.__class__.__name__, self.__name, str(e))
            traceback.print_exc(file=sys.stdout)
            print "-" * 60
    
        #print "Reply is: ", str(self.__reply)
   
        return str(self.__reply)

    def __handle_start_element(self, name, attrs):
        """
            Called whenever we encounter the start of an XML element
        
            Keyword arguments:
            name -- the name of the element
            attrs -- dictionary of attributes
        """
    
        if name == "channel_dump":
            self.__reply += self.__do_channel_dump(attrs)
        elif name == "channel_get":
            self.__reply += self.__do_channel_get(attrs)
        elif name == "channel_set":
            self.__reply += self.__do_channel_set(attrs)
        elif name == "channel_refresh":
            self.__reply += self.__do_channel_refresh(attrs)
        elif name == "channel_info":
            self.__reply += self.__do_channel_info(attrs)
        elif name == "logger_list":
            self.__reply += self.__do_logger_list(attrs)
        elif name == "logger_set":
            self.__reply += self.__do_logger_set(attrs)
        elif name == "logger_dump":
            self.__reply += self.__do_logger_dump(attrs)
        elif name == "logger_next":
            self.__reply += self.__do_logger_next(attrs)
        elif name == "logger_prev":
            self.__reply += self.__do_logger_prev(attrs)
        elif name == "logger_rewind":
            self.__reply += self.__do_logger_rewind(attrs)
        elif name == "logger_seek":
            self.__reply += self.__do_logger_seek(attrs)
        elif name == "logger_pos":
            self.__reply += self.__do_logger_pos(attrs)
        else:
            self.__reply += "<" + name + ">"

    def __handle_end_element(self, name):
        """
            Called whenever we encounter an ending XML element
        
            Keyword arguments:
            name -- the name of the end element
        """

        self.__reply += "</" + name + ">"

    def __do_channel_dump(self, attrs):
        """
            Builds a response for a channel dump request
        
            Keyword arguments:
            attrs - Any attributes that might be passed in
        """
        
        # Variables
        device_string = StringIO()
        
        device_string.write('<channel_dump>')
        
        cdb = (self.__core.get_service("channel_manager")
                .channel_database_get())
        device_string.write(self.__generate_channel_database(cdb))
    
        return device_string.getvalue()

    def __do_channel_get(self, attrs):
        """
            Builds a response for a channel get request
        
            Keyword arguments:
            attrs -- dictionary of attributes, should have 'name'
        """
    
        try:
            channel_name = attrs['name']
        except KeyError:
            return '<channel_get>' + RCIHandler.ERR_MISSING_ATTRIBUTE
    
        cdb = self.__core.get_service("channel_manager").\
        channel_database_get()
    
        if not cdb.channel_exists(channel_name):
            return ('<channel_get name="%s">' % channel_name + 
                    RCIHandler.ERR_UNKNOWN_CHANNEL)
    
        channel = cdb.channel_get(channel_name)
        value = "(n/a)"
        units = ""
        timestamp = ""
        try:
            sample = channel.get()
            value = self.__escape_entities(sample.value)
            units = sample.unit
            timestamp = time.asctime(time.localtime(sample.timestamp))
        except:
            pass
        
        return ('<channel_get name="%s" value="%s" units="%s"'
                 ' timestamp="%s">' % (channel_name, value, units, timestamp))
        
    def __do_channel_refresh(self, attrs):
        """
            Builds a response for a channel refresh request
        
            Keyword arguments:
            attrs -- dictionary of attributes, should have 'name'
        """
    
        try:
            channel_name = attrs['name']
        except KeyError:
            return '<channel_refresh>' + RCIHandler.ERR_MISSING_ATTRIBUTE
    
        cdb = self.__core.get_service("channel_manager").\
        channel_database_get()
    
        if not cdb.channel_exists(channel_name):
            return ('<channel_refresh name="%s">' % channel_name + 
                    RCIHandler.ERR_UNKNOWN_CHANNEL)
    
        channel = cdb.channel_get(channel_name)

        try:
            sample = channel.refresh()
        except:
            return '<channel_refresh>' + RCIHandler.ERR_REFRESH
        
        return '<channel_refresh name="%s">' % (channel_name)        
    
    def __do_channel_info(self, attrs):
        """
            Builds a response for a channel info request
        
            Keyword arguments:
            attrs -- dictionary of attributes, should have 'name'
        """
    
        try:
            channel_name = attrs['name']
        except KeyError:
            return '<channel_info>' + RCIHandler.ERR_MISSING_ATTRIBUTE
    
        cdb = self.__core.get_service("channel_manager").channel_database_get()
    
        if not cdb.channel_exists(channel_name):
            return ('<channel_info name="%s">' % channel_name + 
                    RCIHandler.ERR_UNKNOWN_CHANNEL)
    
        channel = cdb.channel_get(channel_name)
        perms_table = {
            PERM_GET: "<get/>",
            PERM_SET: "<set/>",
            PERM_REFRESH: "<refresh/>",
        }
        options_table = {
            OPT_AUTOTIMESTAMP: "<auto_timestamp/>",
            OPT_DONOTLOG: "<do_not_log_data/>",
            OPT_DONOTDUMPDATA: "<do_not_dump_data/>",
        }

        resp = '<channel_info name="%s">' % channel_name
        for tag, tbl, mask in (
                ("permissions", perms_table, channel.perm_mask()),
                ("options", options_table, channel.options_mask()) ):
            if not mask:
                resp += "<%s/>" % tag
                continue
            keys = tbl.keys()
            keys.sort()
            resp += "<%s>" % tag
            for k in keys:
                if k & mask:
                    resp += tbl[k]
            resp += "</%s>" % tag
    
        return resp

    def __do_channel_set(self, attrs):
        """
            Builds a response for a channel set request
        
            Keyword arguments:
            attrs -- dictionary of attributes, should have 'name' and 'value'
        """
        
        try:
            channel_name = attrs['name']
            value = self.__unescape_entities(attrs['value'])
        except KeyError:
            return '<channel_set>' + RCIHandler.ERR_MISSING_ATTRIBUTE
    
        cdb = self.__core.get_service("channel_manager").\
        channel_database_get()
    
        if not cdb.channel_exists(channel_name):
            return ('<channel_set name="%s">' % channel_name + 
                    RCIHandler.ERR_UNKNOWN_CHANNEL)
    
        channel = cdb.channel_get(channel_name)
    
        sample = None
        try:
            sample = Sample(time.time(), channel.type()(str(value)))
        except Exception, e:
            print "unable to parse '%s': %s\r\n" % (value, str(e))
            print "type expected: %s\r\n" % (channel.type())
            return '<channel_set name="%s"/>' % channel_name \
            + RCIHandler.ERR_INVALID_SAMPLE_VALUE
    
        try:
            channel.set(sample)
        except Exception, e:
            return ('<channel_set name="%s">' % channel_name + 
                    RCIHandler.ERR_SET_FAILED)
    
        value = "(n/a)"
        units = ""
        timestamp = ""
        try:
            value = channel.get().value
            units = sample.unit
            timestamp = time.asctime(time.localtime(sample.timestamp))
        except:
            pass
    
        return ('<channel_set name="%s" value="%s" units="%s" timestamp="%s">'
                % (channel_name, value, units, timestamp))
    
    def __do_logger_list(self, attrs):
        """
            Builds a response for a 'logger_list' request.
        """
        
        cm = self.__core.get_service("channel_manager")
        logger_list = cm.channel_logger_list()
        
        list_response = StringIO()
        
        list_response.write('<logger_list>')
        
        for logger_name in logger_list:
            list_response.write('<logger name="%s"/>' % logger_name)
        
        return list_response.getvalue()
    
    def __do_logger_set(self, attrs):
        """
            Builds a response for a 'logger_set' request.
        """
        
        try:
            logger_name = attrs['name']
        except KeyError:
            return '<logger_set>' + RCIHandler.ERR_MISSING_ATTRIBUTE
        
        cm = self.__core.get_service("channel_manager")

        if not cm.channel_logger_exists(logger_name):
            return '<logger_set name="%s">%s' % (
                logger_name, RCIHandler.ERR_UNKNOWN_LOGGER)

        try:
            self.__logger = cm.channel_logger_get(logger_name)
            self.__logger_cdb = self.__logger.channel_database_get()
        except Exception, e:
            return '<logger_set name="%s"><error>Exception: %s</error>' % (
                logger_name, str(e))

        return '<logger_set name="%s">' % logger_name
    
    def __do_logger_dump(self, attrs):
        """
            Builds a response for a 'logger_dump' request
        """
        
        # Variables
        dump_response = StringIO()
        
        if self.__logger is None:
            dump_response.write('<logger_dump>')
            dump_response.write(RCIHandler.ERR_UNSELECTED_LOGGER)
        else:
            logger_name = self.__logger.get_name()
            dump_response.write('<logger_dump name="%s">' 
                                % (logger_name))
            dump_response.write(self.__generate_channel_database
                                (self.__logger_cdb))
        
        return dump_response.getvalue()
        
    def __do_logger_next(self, attrs):
        """
            Builds a response for a 'logger_next' request
        """
        
        if self.__logger is None:
            return '<logger_next>%s' % RCIHandler.ERR_UNSELECTED_LOGGER

        logger_name = self.__logger.get_name()

        try:
            self.__logger_cdb.log_next()
        except Exception, e:
            return '<logger_next name="%s"><error>Exception: %s</error>' % (
                logger_name, str(e))

        return '<logger_next name="%s">' % logger_name
    
    def __do_logger_prev(self, attrs):
        """
            Builds a response for a 'logger_prev' request
        """
        
        if self.__logger is None:
            return '<logger_prev>%s' % RCIHandler.ERR_UNSELECTED_LOGGER

        logger_name = self.__logger.get_name()

        try:
            self.__logger_cdb.log_prev()
        except Exception, e:
            return '<logger_prev name="%s"><error>Exception: %s</error>' % (
                logger_name, str(e))

        return '<logger_prev name="%s">' % logger_name

    def __do_logger_rewind(self, attrs):
        """
            Builds a response for a 'logger_rewind' request
        """
        
        if self.__logger is None:
            return '<logger_rewind>%s' % RCIHandler.ERR_UNSELECTED_LOGGER

        logger_name = self.__logger.get_name()

        try:
            self.__logger_cdb.log_rewind()
        except Exception, e:
            return '<logger_rewind name="%s"><error>Exception: %s</error>' % (
                logger_name, str(e))

        return '<logger_rewind name="%s">' % logger_name

    def __do_logger_seek(self, attrs):        
        """\
        Builds a response for a 'logger_seek' request
            
        **Request** code::
            
            <logger_seek offset={num] whence={cur, set, end, rec} [record={num]>
            
        **Response** code::
            
            <logger_seek name={name}>[<error></error>]</logger_seek>                    
        """
        
        whence_map = { 'set': LOG_SEEK_SET,
                       'cur': LOG_SEEK_CUR,
                       'end': LOG_SEEK_END,
                       'rec': LOG_SEEK_REC, }

        if self.__logger is None:
            return '<logger_seek>%s' % RCIHandler.ERR_UNSELECTED_LOGGER

        logger_name = self.__logger.get_name()

        try:
            offset = int(attrs['offset'])
            whence = attrs['whence']
        except KeyError:
            return '<logger_seek name="%s">%s' % (
                logger_name, RCIHandler.ERR_MISSING_ATTRIBUTE)

        if whence not in whence_map:
            return ('<logger_seek name="%s"><error>Bad whence "%s", '
                      'must be set, cur, end or rec</error>') % (
                logger_name, str(whence))

        try: 
            record_number = int(attrs['record_number'])
        except KeyError:
            record_number = 0

        try:
            self.__logger_cdb.log_seek(offset,
                                       whence_map[whence],
                                       record_number)
        except Exception, e:
            return '<logger_seek name="%s"><error>Exception: %s</error>' % (
                logger_name, str(e))

        return '<logger_seek name="%s">' % logger_name

    def __do_logger_pos(self, attrs):
        """
            Builds a response for a 'logger_next' request
        """
        
        if self.__logger is None:
            return '<logger_pos>%s' % RCIHandler.ERR_UNSELECTED_LOGGER

        logger_name = self.__logger.get_name()

        try:
            pos = self.__logger_cdb.log_position()
            if pos == None:
                raise Exception, "Position not set"
        except Exception, e:
            return '<logger_pos name="%s"><error>Exception: %s</error>' % (
                logger_name, str(e))

        return '<logger_pos name="%s">%s' % (logger_name, pos)
    
    def __generate_channel_database(self, cdb):
        
        channel_list = cdb.channel_list()
        channel_list.sort()
    
        devices = {}
    
        for entry in channel_list:
            device, channel_name = entry.split('.')
            channel = cdb.channel_get(entry)
    
            if not devices.has_key(device):
                devices[device] = []
    
            try:
                if (not (channel.perm_mask() & PERM_GET) or
                    channel.options_mask() & OPT_DONOTDUMPDATA):
                    raise Exception
                sample = channel.get()
                devices[device].append((channel_name,
                                        sample.value,
                                        sample.unit,
                                        time.asctime(
                                                     time.localtime
                                                     (sample.timestamp)),
                                        str(channel.type().__name__)))
            except Exception, e:
                devices[device].append((channel_name, "(N/A)", "", "", ""))
    
        device_string = StringIO()
    
        for device in devices.keys():
            device_string.write('<device name="%s">' % device)
            for channel in devices[device]:
                value = self.__escape_entities(channel[1])
                device_string.write('<channel name="%s" value="%s"'
                    ' units="%s" timestamp="%s"'
                    ' type="%s"/>' % (channel[0], value, channel[2], 
                                        channel[3], channel[4]))
            device_string.write('</device>')
        
        return device_string.getvalue()
    
