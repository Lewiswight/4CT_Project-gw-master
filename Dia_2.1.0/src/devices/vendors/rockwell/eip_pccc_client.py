############################################################################
#                                                                          #
# Copyright (c)2008-2011 Digi International (Digi). All Rights Reserved.   #
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

"""
Base Driver to create Rockwell PCCC requests & parse response.

Note: it does NOT poll - you'll need the EIP, CSP or DF1 sub-class
      to actually cause polls to be sent and responses received.
"""

#Imports
import sys
import traceback
import threading
import time
import struct
import types
import gc

from core.tracing import get_tracer
from devices.device_base import DeviceBase
from settings.settings_base import SettingsBase, Setting
from channels.channel_source_device_property import *
from channels.channel_manager import ChannelManager
from common.helpers.format_channels import iso_date
from core.tracing import get_tracer

# import routines used to clean up sleep time to sync with RTC
import devices.vendors.rockwell.sleep_aids as sleep_aids
import devices.vendors.rockwell.pccc_util as pccc_util
import devices.vendors.rockwell.eip as eip
import devices.vendors.rockwell.cip as cip

#Constants

#Exception classes

#Interface functions

#Classes
class EipPcccPoll:

    # the stats values tracked
    REQ_CNT = 'request_count'
    EXCP_CNT = 'exception_count'
    NORSP_CNT = 'no_response_count'
    TIME_MIN = 'rsp_time_min'
    TIME_AVG = 'rsp_time_avg'
    TIME_MAX = 'rsp_time_max'
    TIME_AVG_RATIO = 0.9

    def __init__(self, parent, **kw):
        """\
        Generate a single poll to read/write a block of data per YML config

        Expected tags in kw:
        kw['poll'] = str, user-friendly name for this poll block
        kw['pollinfo'] = dict, the poll block details
        pollinfo['elm'] = str, the PCCC element info, like 'N7:0'
        pollinfo['cnt'] = int, number of data elements
        """

        self._parent = parent
        self.__tracer = self._parent._tracer

        self.__name = kw.get( 'pollname', 'default')

        self.attrib = kw['pollinfo']
        self.__tracer.debug('Create PollInfo: %s', str(self.attrib))

        now = time.time()
        self.parse_list = []

        for itm in kw['channels']:
            # add each parse+channel to the list
            p = itm['parse'] # this is kind of a dummy tag
            parse = EipPcccParse( self, **p)
            self.parse_list.append( parse)

            # add the channel to the device object
            # self.last_sam = parse.set_error( ERSAM_NOT_INIT, now)
            self.last_sam = parse.get_last_sample()
            my_name = parse.get_channel_name()
            # else is read, so we create a GET-ONLY channel in our device
            self._parent.add_property(
                ChannelSourceDeviceProperty(
                    name=my_name, type=parse.get_type(),
                    initial=self.last_sam,
                    perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP)
                )

        # maintain the stats values
        self.init_stats_channel( )

        return

    def prop_set_write(self, channel_name, int_sample):
        self._parent._tracer.debug('call_back channel=%s, sample=%s\r\n', channel_name, int_sample)
        self._parent.property_set(channel_name, int_sample)

    def clear_links( self):
        for parse in self.parse_list:
            parse.clear_links()

        self.parse_list = None
        self._parent = None
        return

    def get_core(self):
        return self._parent.get_core()

    def get_name( self):
        return self.__name

    def make_request(self):
        # must remake each time since TNS/seq number MUST change
        pccc = pccc_util.makeSlcProtectedTypesLogicalRead(self.attrib)
        return pccc

    def round_floats( self, fp):
        if self._parent.round_floats < 12:
            return round( fp, self._parent.round_floats)
        return fp

    def pre_process(self):
        """Change the value of the new channel with the linked channel one."""

        req = self.make_request()
        self.__tracer.debug(pccc_util.show_bytes('pccc_req', req))

        # assume no error this poll
        self.attrib.update({ 'error':False })

        return req

    def post_process(self, rsp, delta_clock):
        """Change the value of the new channel with the linked channel one."""

        self.__tracer.debug(pccc_util.show_bytes('pccc_rsp', rsp))

        #if self.__tracer.debug():
        #    st = '> Poll(%s) rsp in %0.3f secs' % (self.get_name(), delta_clock)
        #    print_bytes( st, rsp )

        # self.req = self._parent.mbus.cli_response_parse( rsp, self.req)

        now = time.time()
        now_st = iso_date(now)

        data = pccc_util.getData_SlcProtectedTypesLogicalRead( rsp)

        for parse in self.parse_list:
            try:
                sam = parse.process_read( data, now )
                # self.__tracer.info('chn(%s) = %s', parse.get_name(),sam)

            except:
                self.__tracer.error('parse %s failed', parse.get_name())
                self.__tracer.error(traceback.format_exc())
                continue

            self.__set_parse_channel( parse, sam)
            self.__tracer.info(' chan:%s', str(parse.show_value(now_st)))

        if self._stats_chan is not None:
            if( delta_clock != 0):
                # then delta_clock 0 means time.clock() roll-over

                # update the CYCLE TIME stats
                if( (self.attrib[ self.TIME_MIN] <= 0) or (self.attrib[ self.TIME_MIN] > delta_clock) ):
                    # then a NEW min_time
                    self.attrib.update({ self.TIME_MIN:delta_clock })

                if( (self.attrib[ self.TIME_MAX] <= 0) or (self.attrib[ self.TIME_MAX] < delta_clock) ):
                    # then a NEW max_time
                    self.attrib.update({ self.TIME_MAX:delta_clock })

                if( self.attrib[ self.TIME_AVG] <= 0):
                    # then first update of average
                    avg = delta_clock
                else:
                    avg = self.attrib[ self.TIME_AVG] * self.TIME_AVG_RATIO
                    avg += delta_clock * (1.0 - self.TIME_AVG_RATIO)

                self.attrib.update({ self.TIME_AVG:avg })

                self.__tracer.info('poll(%s) reqs:%d rsp_min:%0.2f avg:%0.2f max:%0.2f (in secs)', \
                        self.attrib['name'], self.attrib[ self.REQ_CNT],\
                        self.attrib[ self.TIME_MIN], \
                        self.attrib[ self.TIME_AVG], self.attrib[ self.TIME_MAX] )

            else: # some error occured
                self.__tracer.error('clock roll-over')
        return

    def init_stats_channel( self):
        # maintain the stats values
        self.attrib.update({ 'error':False, 'name':self.__name,
                        self.REQ_CNT:0, self.EXCP_CNT:0, self.NORSP_CNT:0,
                        self.TIME_MIN:0, self.TIME_AVG:0, self.TIME_MAX:0,
                        })

        if self._parent.get_setting('enable_statistics'):
            # these channels only exist if enable_statistics = True

            self.__tracer.debug('Initializing Statistics Channels')
            self._err_chan = '%s_error' % self.__name
            self._stats_chan = '%s_statistics' % self.__name

            self._parent.add_property(
                ChannelSourceDeviceProperty(
                    name=self._err_chan, type=bool, initial=Sample(0, True, ''),
                    perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP)
                )

            self._parent.add_property(
                ChannelSourceDeviceProperty(
                    name=self._stats_chan, type=list,
                    initial=Sample(0, [0,0,0,0,0,0], 'req,no_rsp,err,min,avg.max'),
                    perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP)
                )

        else: # we disable stats
            self.__tracer.debug('Disabling Statistics Channels')
            self._stats_chan = None
        return

    def update_stats_channel( self, now=None):

        if self._stats_chan is not None:
            # these channels only exist if enable_statistics = True

            if not now:
                now = time.time()

            if( self.attrib['error'] != self._parent.property_get(self._err_chan) ):
                # then need to update the output channel
                self._parent.property_set( self._err_chan, Sample( now, self.attrib['error'], "" ))

            # update the stats any time new request count
            sam = [ self.attrib[self.REQ_CNT], self.attrib[self.NORSP_CNT],
                    self.attrib[self.EXCP_CNT], self.attrib[self.TIME_MIN],
                    self.attrib[self.TIME_AVG], self.attrib[self.TIME_MAX] ]

            self._parent.property_set( self._stats_chan, \
                    Sample( now, sam, 'req,no_rsp,err,min,avg.max'))

        return

    def __set_parse_channel( self, parse, sam):

        try:
            self._parent.property_set( parse.get_channel_name(), sam )
            #if not isinstance( sam, AnnotatedSample):
            return True
            # else continue below and set error channels

        except:
            # some error occured
            self.__tracer.debug(traceback.format_exc())

        # self.__tracer.error('was AnnotatedSample or other error')
        self.attrib.update({ 'error':True })
        self._parent.attrib.update({ 'error':True })
        return False

    def show_value(self, fmt, show_time=''):
        """Return string of sample"""

        for parse in self.parse_list:
            self.__tracer.info(fmt % parse.show_value( show_time))
        return

class EipPcccParse:
    """Parse a single channel out of the raw data"""

    # tuple settings
    OFS_NAME = 0
    OFS_OFFSET = 1
    OFS_FORMAT = 2
    OFS_UNITS = 3
    OFS_TYPE = 4
    OFS_EVAL = 5
    OFS_SRC = 6
    PRS_BITS = [0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80]

    def __init__(self, parent, **kw):
        self._parent = parent

        # test ['nam'] - should be unique?

        # just save as TUPLE to reduce size - things shouldn't change
        self.__tup = ( kw['nam'], kw.get('ofs',0), kw.get('frm','h'), \
                       kw.get('unt',''), kw.get('typ',None), \
                       kw.get('expr',None), kw.get('src',None),)

        self.__tracer = self._parent._parent._tracer

        self.__tracer.debug('Create EipPcccParse = %s', str(self.__tup))

        if( self.__tup[self.OFS_TYPE] == None):
            # then GUESS based on format

            if( self.__tup[self.OFS_FORMAT] == '?'):
                # then is '?' for boolean
                self.my_type = types.BooleanType

            elif( self.__tup[self.OFS_FORMAT].find('f') > -1):
                # then is like '>f' etc
                self.my_type = types.FloatType

            else: # else not found so like '<h' etc
                self.my_type = types.IntType

        elif( self.__tup[self.OFS_TYPE] == 'float'):
            self.my_type = types.FloatType

        elif( self.__tup[self.OFS_TYPE] == 'int'):
            self.my_type = types.IntType

        elif( self.__tup[self.OFS_TYPE] == 'long'):
            self.my_type = types.LongType

        else:
            try:
                self.my_type = eval( self.__tup[self.OFS_TYPE])
            except:
                self.my_type = types.IntType

        # allow importing from another channel for WRITES ONLY
        src_nam = self.get_source_channel_name()
        if src_nam is None:
            self.src_dev = None
            self.src_chn = None

        else:
            self.__tracer.debug('src_nam = %s', src_nam)
            try:
                x = src_nam.split('.')
                # x[0] = device, x[1] = chann
                self.src_dev = x[0]
                self.src_chn = x[1]
                self.__tracer.debug('src.split = %s and %s', self.src_dev, self.src_chn)

            except:
                self.__tracer.debug(traceback.format_exc())
                self.src_dev = None
                self.src_chn = None

        self.last_sam = Sample(0, self.cast_my_type(0))
        return

    def clear_links( self):
        self._parent = None
        return

    def get_channel_name( self):
        return '%s_%s' % (self._parent.get_name(), self.get_name())

    def get_format( self):
        return self.__tup[self.OFS_FORMAT]

    def get_name( self):
        return self.__tup[self.OFS_NAME]

    def get_last_sample( self):
        return self.last_sam

    def get_source_channel_name( self):
        return self.__tup[self.OFS_SRC]

    def get_source_channel_value( self):
        dm = self._parent.get_core().get_service("channel_manager")
        # self.src_dev = x[0]
        # self.src_chn = x[1]

    def get_type( self):
        return self.my_type

    def cast_my_type(self, src):
        return self.my_type(src)

    def get_units( self):
        return self.__tup[self.OFS_UNITS]

    def process_read(self, bytes, now):
        """Return sample parsed from bytes."""

        if not bytes:
            self.__tracer.error('no bytes, no data received')
            val = None
            self.last_sam = Sample( now, self.my_type(0), self.get_units() )

        else:

            ofs = self.__tup[self.OFS_OFFSET]
            if self.my_type == types.BooleanType:
                # special for Boolean bits, so offset is bit offset Modbus style
                by_ofs = (self.__tup[self.OFS_OFFSET] / 8)
                bit_ofs = (self.__tup[self.OFS_OFFSET] % 8)
                try:
                    val = bool( ord(bytes[by_ofs]) & self.PRS_BITS[bit_ofs])
                except:
                    # self.__tracer.error(traceback.format_exc())
                    self.__tracer.error('bit offset %d out of range 0-%d', \
                          self.__tup[self.OFS_OFFSET], len(bytes) * 8)
                    val = None # will set as bad data

            else:
                if self.my_type == types.IntType:
                    # then 2 byte word
                    try:
                        val = struct.unpack(self.__tup[self.OFS_FORMAT], bytes[ofs:ofs+2])[0]

                    except:
                        self.__tracer.error(traceback.format_exc())
                        val = None # will set as bad data

                elif self.my_type in (types.FloatType, types.LongType):
                    # then 4 byte word
                    try:
                        val = struct.unpack(self.__tup[self.OFS_FORMAT], bytes[ofs:ofs+4])[0]

                    except:
                        self.__tracer.error(traceback.format_exc())
                        val = None # will set as bad data

                else: # handle the normal int/floats
                    self.__tracer.error('Bad format type')
                    val = None

                if self.__tup[self.OFS_EVAL] and val is not None:
                    # then have an eval/conversion function - find any 'c'
                    x = self.__tup[self.OFS_EVAL]
                    self.__tracer.debug('pre-expr(%s), input is %s', str(x),str(val)),
                    try:
                        val = eval(x % val)
                    except:
                        self.__tracer.error(traceback.format_exc())
                    self.__tracer.debug('pst-expr, output was %s', str(val))

                if val and self.my_type == types.FloatType:
                    # try to round floats to 'clean up' system - no one wants an
                    # integer like 523 turned into 3.141592653589793 ... 3.14 is fine
                    val = self._parent.round_floats(val)

            # start with a normal sample, casting value to expected type
            val = self.my_type(val)
            self.last_sam = Sample( now, val, self.get_units() )

        #if val is None:
        #    if not bytes: # then error 'given' to us
        #        self.set_error( ERSAM_BAD_DATA, now)
        #    else: # we created/detected error
        #        self.set_error( ERSAM_BAD_CALC, now)

        return self.last_sam

    def set_error(self, err, now):
        """Return sample parsed from bytes."""

        return self.last_sam

    def show_value(self, show_time=False):
        """Return string of sample"""

        st = ['%s = ' % self.get_channel_name()]
        if( self.my_type == float):
            st.append( '%0.4f %s' % (self.last_sam.value, self.last_sam.unit) )
        else:
            st.append( '%s %s' % (self.last_sam.value, self.last_sam.unit) )

        if( show_time):
            st.append(' at ')
            st.append(show_time)

        #if isinstance( self.last_sam, AnnotatedSample):
        #    st.append( ', error(%s)' % self.last_sam.errors)

        return "".join( st)

class EipPcccDevice(DeviceBase, threading.Thread):

    POLL_RATE = 'poll_rate_sec'     # cause all blocks to poll
    POLL_MINUTE = 'poll_clean_minutes' # example: poll every 5min, at sec=00
    UDP_PEER = 'udp_peer'           # change default peer to talk to
    POLL_LIST = 'poll_list'
    TRACE_ENB = 'trace'
    FP_ROUND = 'round'
    POLL_MIN = 5 # 5 seconds
    RESET_STATS_AT = 9999999

    def __init__(self, name, core_services):
        self.__name = name
        self.__core = core_services
        self._tracer = get_tracer(name)

        self.poll_list = []
        self.time_start = 0
        self.round_floats = 999 # we only update occassionally

        self.eipc = eip.eip_client()

        self.attrib = { 'error':False,
                        }

        ##Settings Table Definition:
        settings_list = [
            # the source channel to cause polling
            Setting(name='poll_rate_sec', type=int, required=False, \
                default_value=15, verify_function=lambda x: x >= self.POLL_MIN),

            Setting(name='poll_clean_minutes', type=int, required=False, \
                default_value=0),

            # allow affecting the trace output
            Setting(name='target', type=str, required=True),

            # allow affecting the trace output
            Setting(name='trace', type=str, required=False, \
                default_value='info') ,

            # clean up floats if not 'greater than 11'
            Setting( name='round', type=int, required=False, \
                default_value=999),

            # allow affecting the trace output
            Setting(name='enable_statistics', type=bool, required=False, \
                default_value=True) ,

            Setting( name='poll_list', type=list, required=True),

        ]

        ##Channel Properties Definition:
        ##Properties are added dynamically based on configured transforms
        property_list = [
            # we start in error, since NO polls have succeeded
            ChannelSourceDeviceProperty(name='error', type=bool,
                initial=Sample(timestamp=0, unit="bool", value=True),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),
            ]

        ## Initialze the Devicebase interface:
        DeviceBase.__init__(self, self.__name, self.__core,
                                settings_list, property_list)

        ## Thread initialization:
        self.__stopevent = threading.Event()
        threading.Thread.__init__(self, name=self.__name)
        threading.Thread.setDaemon(self, True)

        return

    ##Functions which must be implemented to conform to the DeviceBase
    ##interface:
    def apply_settings(self):
        """Called when new configuration settings are available."""

        SettingsBase.merge_settings(self)
        accepted, rejected, not_found = SettingsBase.verify_settings(self)

        if len(rejected) or len(not_found):
            # there were problems with settings, terminate early:
            self._tracer.error("Settings rejected/not found: %s %s", \
                rejected, not_found)

        else:
            SettingsBase.commit_settings(self, accepted)
            # self._tracer.info("%s: Settings accepted: %s", self.show_name, accepted)

        return (accepted, rejected, not_found)

    def start(self):
        """Start the device driver. Returns bool."""

        # update the trace settings
        # self.set_trace( SettingsBase.get_setting(self, self.TRACE_ENB) )

        self._tracer.info('Starting Thread')

        cm = self.__core.get_service("channel_manager")
        cp = cm.channel_publisher_get()

        polls = SettingsBase.get_setting(self, 'poll_list')
        # self._tracer.debug('polls: %s', str(polls))
        for itm in polls:
            # each polls consists of a remote read
            poll = EipPcccPoll(self, **itm)
            self.poll_list.append( poll)

        # update the client from YML
        self.eipc.updateFromDict({ "port":44818,
            "ip":SettingsBase.get_setting(self, 'target')})

        threading.Thread.start(self)
        return True

    def stop(self):
        """Stop the device driver. Returns bool."""
        self._tracer.info('Stopping Thread')
        self.__stopevent.set()
        return True

    # Threading related functions:
    def run(self):
        """run when our device driver thread is started"""

        while 1:
            if self.__stopevent.isSet():
                self.__stopevent.clear()
                break

            # confirm we have a valid EIP_ENCAP session
            if not self.eipc.isOpen():
                self._tracer.info("Try to open EIP Encap Session to %s:%d", \
                    self.eipc.getIp(), self.eipc.getPort())
                if( self.eipc.OpenSession({}) == 0):
                    # then error, clean up garbage, sleep to retry
                    self._tracer.warning("EIP RegSes failed! Retry in 1 minute.")
                    gc.collect()
                    time.sleep(60.0)
                    continue

            if not self.eipc.ping():
                self._tracer.warning("EIP Session closed - will retry to open.")
                time.sleep(5.0)
                continue

            self.time_start = time.time()
            self.attrib.update({ 'error':False })
            # self.time_tup = time.localtime(self.time_start)

            self._tracer.debug('Cyclic Process at %s',
                               iso_date(self.time_start))

            # we only update occassionally - don't do for every poll item
            self.round_floats = SettingsBase.get_setting(self, self.FP_ROUND)

            for poll in self.poll_list:
                # issue each poll
                # poll.show_value( '  >>%s', True)
                self.send_poll( poll)
                # self._tracer.info('poll_stats', poll.attrib)

            # save end of cycle - how long the process took
            self.time_end = time.time()

            # handle the global detect error in at least 1 block
            self.__update_stats_channel()

            rate = SettingsBase.get_setting(self, self.POLL_MINUTE)
            if( rate == 0):
                # then use the older cycle design, not clean-minute design
                real_rate = SettingsBase.get_setting(self, self.POLL_RATE)

            else:
                # else we use the 'clean minutes' algorithm
                real_rate = sleep_aids.secs_until_next_minute_period(
                                rate, time.gmtime(self.time_end))

            if real_rate < self.POLL_MIN:
                real_rate = self.POLL_MIN

            time.sleep(real_rate)

        # stopping - clean up
        try:
            self.sock.close()
        except:
            pass

        self.sock = None

        for poll in self.poll_list:
            poll.clear_links()

        self.poll_list = None

        return

#Internal functions & classes

    def __verify_clean_minutes(self, period):
        if period in sleep_aids.PERMITTED_VALUES:
            return

        # then is not a factor of 60
        raise ValueError("Minute period of %d is not a factor of 60" % period)

    def get_core(self):
        return self.__core

    def __update_stats_channel( self):
        '''See if any of your stats channels changed'''

        if( self.attrib['error'] != self.property_get('error') ):
            # then need to update the output channel
            self.property_set( 'error', Sample( self.time_end, self.attrib['error'], "" ))
        return

    def send_poll( self, poll):
        '''Send the actual poll off'''

        pccc = poll.pre_process()
        if not pccc:
            self.attrib.update({ 'error':True })
            rsp = None
            return False

        pc3_cip = self.eipc.cip_obj.buildServPath({"service" : 0x4B, \
            "class" : 0x67, "instance" : 0x01}) + \
            pccc_util.makeCipHeader({}) + pccc
        # print pccc_util.show_bytes('pc3_cip', pc3_cip)

        self.attrib.update({"cip":pc3_cip})
        idreq = self.eipc.buildUCMM(self.attrib)
        self._tracer.debug(pccc_util.show_bytes('cip_req', idreq))

        poll_start_clock = time.clock()

        # try sending
        try:
            x = self.eipc.send(idreq)
            if( x != len(idreq)):
                self._tracer.error('Send Error')
                self.attrib.update({ 'error':True })
                rsp = None

            else:
                if poll.attrib[poll.REQ_CNT] >= self.RESET_STATS_AT:
                    # then reset the counts to 0
                    self._tracer.warning('Resetting poll statistics since above %d',
                            self.RESET_STATS_AT)
                    poll.attrib.update({
                        poll.REQ_CNT:0, poll.EXCP_CNT:0, poll.NORSP_CNT:0,
                        poll.TIME_MIN:0, poll.TIME_AVG:0, poll.TIME_MAX:0,
                        })

                poll.attrib.update( { poll.REQ_CNT: poll.attrib[poll.REQ_CNT] + 1 } )
                rsp = self.eipc.recv(1024)

        except:
            self._tracer.error(traceback.format_exc())
            rsp = None

        if rsp is None or (len(rsp) == 0):
            # then NO response
            poll.attrib.update( { poll.NORSP_CNT: poll.attrib[poll.NORSP_CNT] + 1 } )
            self._tracer.error('Poll failed!')
            self.attrib.update({ 'error':True })
            self.eipc.close()

        else:
            poll_end_time = time.time()
            self._tracer.debug( pccc_util.show_bytes('cip_rsp', rsp))
            encap,addr,data,pccc = self.eipc.breakupCPF(rsp)

            poll_end_clock = time.clock()
            delta_clock = poll_end_clock - poll_start_clock
            # handle roll-over?
            if( delta_clock < 0):
                delta_clock = 0

            poll.post_process(pccc, delta_clock)

        poll.update_stats_channel( )

        return True
