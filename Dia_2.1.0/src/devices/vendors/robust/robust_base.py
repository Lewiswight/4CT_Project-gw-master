# File: robust_base.py
# Desc: the robust device base - includes status and other features required
#       by realworld devices

############################################################################
#                                                                          #
# Copyright (c)2008-2012, Digi International (Digi). All Rights Reserved.  #
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

'''


DERIVED CLASS routines you may want to provide:
    next_poll(trns_id), will be called each time-cycle, with trns_id being
        a new transaction id (see self.get_next_transaction_id()).  Your derived
        device should use this to initiate the next poll or cyclic-processing

    response_timeout(rsp_tout_count), where the rsp_tout_count is the
        number of consecutive time-outs, with 0 meaning the first.  You should
        call self.signal_end_of_poll(success=False) within your timeout handler.

DERIVED CLASS routines you may want to USE, but not replace:
    get_transaction_id() which returns the existing/last id without
        incrementing it.

    get_next_transaction_id() which increments, then returns an increasing
        id which varies from self.MIN_TRANS_ID to self.MAX_TRANS_ID,
        By default it is 1 to 254 (so will not be 0 or 255/-1)

    signal_end_of_poll(success=True), your derived class should call this to
        end (or close) the poll cycle, including whether the poll succeeded or
        failed.  This information is used to manage the devices' error channel,
        plus maintain the poll statistics.

    cancel_response_timeout() should be called ASAP when you obtain a response.

MISC Routines:
    self.show_bytes(szMsg, data, bNewLine=None)
        returns a formatted string of the binary buffer such as:

    def iso_date(self, t=None, use_local_time_offset=False):
        returns a formatted string of date such as:
        "2011-Nov-10T15:32:10Z"
'''

# imports
import types
import time
import traceback

from core.tracing import get_tracer
from settings.settings_base import SettingsBase, Setting
from channels.channel_source_device_property import *
from samples.sample import *
from common.helpers.format_channels import iso_date

from devices.vendors.robust.avail_base import Availability
from devices.vendors.robust.parse_duration import parse_time_duration
import devices.vendors.robust.sleep_aids as sleep_aids

# constants

# exception classes

# interface functions

# classes

class RobustBase(SettingsBase):
    """
    Base class that any ROBUST device driver must derive from.

    """

    # subclasses CAN change the following internal defaults
    RDB_INITIAL_POLL = 15

    MAX_TRANS_ID = 254
    MIN_TRANS_ID = 1

    # error channel sources:
    RDB_NOT_INIT = 0x01
    RDB_XBEE_ERROR = 0x02
    RDB_DRIVER_ERROR = 0x04

    ## subclasses CAN change the following SETTINGS defaults

    ## Control the device_error channel.
    # Set RDB_DEF_ERROR_CHAN to None to disable/remove this channel
    # RDB_DEF_ERROR_CHAN = 'dev_error'
    RDB_DEF_ERROR_CHAN = None

    ## Control the description channel.
    # Set RDB_DEF_DESC_CHAN to None to disable/remove this channel
    # Note you will also need to put a value into setting 'dev_desc' to create this channel
    RDB_DEF_DESC_CHAN = 'description'
    # RDB_DEF_DESC_CHAN = None

    # this is the default description, which your dirved class can over-ride
    RDB_DEF_DESC = ''

    RDB_DEF_POLL_RATE = '1 min'
    RDB_DEF_RESPONSE_TIMEOUT = 0
    RDB_DEF_POLL_CLEANLY = False
    RDB_DEF_TRACE = None

    def __init__(self, name, core_services, settings_in=None, properties_in=None):
        self.__name = name
        self.__settings = settings_in
        self.__core = core_services
        self.__sched = self.__core.get_service("scheduler")
        self.__properties = { }

        self._tracer = get_tracer('Robust')
        self.__showname = 'RBas(%s)' % name

        # local ERROR values - set to None to disable
        self.__err_chn_name = self.RDB_DEF_ERROR_CHAN

        # local polling
        self.__poll_timer = None
        self.__rsp_timer = None
        self._response_timeout_count = 0

        self._poll_rate = 0
        self._poll_starttime = 0
        self._last_poll_time = 0
        self._transaction_id = self.MIN_TRANS_ID

        # self._available = Availability()

        # temp variable - will be deleted after startup
        self._start_polling = True

        # Initialize settings:
        ## Settings Table Definition:
        settings_list = [
			# 'dev_enable_error' set to:
            #   'True' for support of error channel with default name
            #   'False' or None for removing support
            #   set to any other name to rename the error channel
            Setting(
                name='dev_enable_error', type=str, required=False,
                default_value=self.RDB_DEF_ERROR_CHAN),

			# 'dev_poll_rate_sec' set to:
            #   0/None to disable polling callbacks
            #   set to numebr of secs, or tag with sec, min, hr such as '1 min', '3 hr' etc
            Setting(
                name='dev_poll_rate_sec', type=str, required=False,
                default_value=self.RDB_DEF_POLL_RATE),

            Setting(
                name='dev_response_timeout_sec', type=str, required=False,
                default_value=self.RDB_DEF_RESPONSE_TIMEOUT),

            # The device description or comment channel.
            Setting(
                name='dev_desc', type=str, required=False,
                default_value=self.RDB_DEF_DESC),

            Setting(
                name='dev_poll_cleanly_min', type=bool, required=False,
                default_value=self.RDB_DEF_POLL_CLEANLY),

            Setting(
                name='dev_trace', type=str, required=False,
                default_value=self.RDB_DEF_TRACE),

        ]

        # Add our settings_list entries to the settings passed to us.
        settings = self._safely_merge_lists(settings_in, settings_list)
        SettingsBase.__init__(self, binding=("devices", (name,), "settings"),
                                    setting_defs=settings)

        property_list = []

        if self.__err_chn_name is not None:
            property_list = [
                ChannelSourceDeviceProperty( name=self.__err_chn_name, type=int,
                        initial=Sample(timestamp=0, value=self.RDB_NOT_INIT, unit="not_init"),
                        perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP)
                ]

        # Add our property_list entries to the properties passed to us.
        properties = self._safely_merge_lists(properties_in, property_list)

        # the buck stops here - we load the properties directly
        for property in properties:
            self.add_property(property)

        x = SettingsBase.get_setting(self, "dev_trace")
        if x is not None:
            # propogate tracer level from YML if set
            self._tracer.set_level(x)
            
        return

    ## These functions must be implemented by the sensor driver writer:

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
            # there were problems with settings, terminate early:
            self._tracer.error("Settings rejected/not found: %s %s", rejected, not_found)
            return (accepted, rejected, not_found)

        SettingsBase.commit_settings(self, accepted)

        return (accepted, rejected, not_found)

    def start_pre(self):
        """
        Start the device driver.  Returns bool.

        """

        self._tracer.calls("%s start_pre", self.__showname)

        x = SettingsBase.get_setting(self, "dev_desc")
        if (x is not None) and (len(x) > 0):
            self._tracer.debug("Adding Channel:%s=\"%s\"", self.RDB_DEF_DESC_CHAN, x)
            self.add_property(
                ChannelSourceDeviceProperty(name=self.RDB_DEF_DESC_CHAN,
                    type=str, initial=Sample(0, x, ''),
                    perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP))

        # if not SettingsBase.get_setting(self, "dev_enable_polling"):
        #    is handled in the import settings
        apply = self._import_settings()
        if apply:
            self.apply_settings()

        if self._start_polling:
            # then derived class didn't suppress fast-start
            self.schedule_first_poll()

        return True

    def start_post(self):

        return True

    def stop(self):
        """
        Stop the device driver.  Returns bool.

        """
        self._tracer.debug("%s Stopping Device", self.__showname)

        # cancel any out-standing events
        try:
            self.cancel_next_poll()
            self.cancel_response_timeout()
        except:
            pass

        return True

    def schedule_after(self, delay, action, *args):
        """\
        Schedule an action (a method) to be called with ``*args``
        after a delay of delay seconds.  Delay may be less than a second.

        """
        return self.__sched.schedule_after(delay, action, *args)

    def schedule_cancel(self, event_handle):
        """\
        Try and cancel a schedule event.

        """
        self.__sched.cancel(event_handle)

    ## These functions are inherited by derived classes and need not be changed:
    def get_core(self):
        """
        Returns the name of the device.
        """
        return self.__core

    def get_name(self):
        """
        Returns the name of the device.
        """
        return self.__name

    def get_next_transaction_id(self):
        """
        Returns the current transaction
        """
        if self._transaction_id >= self.MAX_TRANS_ID:
            self._transaction_id = self.MIN_TRANS_ID
        else:
            self._transaction_id += 1

        return self._transaction_id

    def get_transaction_id(self):
        """
        Returns the current transaction
        """
        return self._transaction_id

    def get_poll_rate_sec(self):
        if self._poll_rate is None:
            return 0
        return self._poll_rate

    def get_device_error(self):
        return self.get_error_channel_value()

    def __get_property_channel(self, name):
        """
        Returns channel designated by property *name*.

        """

        channel_db = \
            self.__core.get_service("channel_manager").channel_database_get()

        channel_db.channel_get(self.__name + '.' + name)
        if name not in self.__properties:
            raise DeviceBasePropertyNotFound, \
                "channel device property '%s' not found." % (name)

        return self.__properties[name]

    def add_property(self, channel_source_device_property):
        """
        Adds a channel to the set of device properties.

        """
        channel_db = \
            self.__core.get_service("channel_manager").channel_database_get()
        channel_name = "%s.%s" % \
                        (self.__name, channel_source_device_property.name)
        channel = channel_db.channel_add(
                                    channel_name,
                                    channel_source_device_property)
        self.__properties[channel_source_device_property.name] = channel

        return channel

    def property_get(self, name):
        """
        Returns the current :class:`~samples.sample.Sample` specified
        by *name* from the devices property list.

        """

        channel = self.__get_property_channel(name)
        return channel.producer_get()

    def property_set(self, name, sample):
        """
        Sets property specified by the string *name* to the
        :class:`~samples.sample.Sample` object *sample* and returns
        that value.

        """

        channel = self.__get_property_channel(name)
        return channel.producer_set(sample)

    def property_exists(self, name):
        """
        Determines if a property specified by *name* exists.

        """

        if name in self.__properties:
            return True
        return False

    def property_list(self):
        """
        Returns a list of all properties for the device.

        """

        return [name for name in self.__properties]

    def remove_one_property(self, chan):
        """
        Removes one named property from the set of device properties.

        """

        channel_db = \
            self.__core.get_service("channel_manager").channel_database_get()

        channel_name = "%s.%s" % (self.__name, chan)
        try:
            chan_obj = channel_db.channel_remove(channel_name)
            if chan_obj:
                del chan_obj
            self.__properties.pop(chan)
        except:
            self._tracer.debug(traceback.format_exc())
            pass
        return

    def remove_all_properties(self):
        """
        Removes all properties from the set of device properties.

        """
        self.remove_property_list(self.__properties)
        self.__properties = { }
        return

    def remove_list_of_properties(self, chan_list):
        """
        Removes a list of named properties from the set of device properties.

        """

        channel_db = \
            self.__core.get_service("channel_manager").channel_database_get()

        for chan in chan_list:
            channel_name = "%s.%s" % (self.__name, chan)
            try:
                chan_obj = channel_db.channel_remove(channel_name)
                if chan_obj:
                    del chan_obj
                self.__properties.pop(chan)
                self._tracer.debug("Delete Channel: %s", channel_name)
            except:
                self._tracer.debug(traceback.format_exc())
                self._tracer.debug("Delete of Channel %s failed", channel_name)
        return

    def _safely_merge_lists(self, org_list, add_list):

        # self._tracer() hasn't been created yet
        # self._tracer.debug('merge: orig_list is type: %s', type(org_list) )
        # self._tracer.debug('merge: add_list is type: %s', type(add_list) )

        if org_list is None:
            # self._tracer.debug('merge: orig_list is None, result is add_list')
            return add_list

        if add_list is not None:
            for add_one in add_list:
                for org_one in org_list:
                    if add_one.name == org_one.name:
                        # do NOT over-ride duplicate from derived classes
                        # use the derived classes value
                        break
                else: # is new, so merge add into original
                    org_list.append(add_one)
        # else: self._tracer.debug('merge: add_list is None, result is orig_list')
        return org_list

    ## Note: even if subclass suppresses error channel, we don't want any
    #        serious errors.  Just silently fail.
    def _next_poll_cb(self):
        self._poll_starttime = time.clock()

        self.schedule_next_poll()

        if self._rsp_tout > 0:
            # we start a response timeout - note this MUST be done before the
            # actual poll/request is sent or we risk the response arriving
            # before the response timer is started
            self.start_response_timeout()

        # call any derived class poll
        try:
            self.next_poll(self.get_next_transaction_id())
        except:
            self._tracer.debug(traceback.format_exc())
            self._tracer.debug("%s NEXT_POLL Failed", self.__showname)

        return

    def next_poll(self, trns_id=0):
        self._tracer.debug("%s Null Poll #%d - no work was defined or done.",
                    self.__showname, trns_id)
        self.cancel_response_timeout()
        return

    def disable_polling(self):
        # then disable all timing control
        self._tracer.debug("%s disabling all polling control", self.__showname)
        self._poll_rate = None
        self._rsp_tout = None
        return

    def signal_end_of_poll(self, success=True):
        if self.__rsp_timer is not None:
            self.cancel_response_timeout()

        if self._poll_starttime == 0:
            self._tracer.error("%s no starttime - ignore last poll cycle",
                self.__showname)
        elif success:
            delta = time.clock()
            if delta < self._poll_starttime:
                self._tracer.warning("time.clock() rollover - ignore last poll cycle")
            else:
                delta = delta - self._poll_starttime
                self._last_poll_time = delta
                self._tracer.debug("%s last poll cycle took %0.2f secs",
                        self.__showname, delta)
            self._response_timeout_count = 0
        # else it failed

        self._poll_starttime = 0
        return

    def _import_settings(self):
        """Handle the settings dependencies"""

        # assume no change
        apply = False

        ## Handle the error channel enable/disable/rename
        if self.__err_chn_name is not None:
            x = SettingsBase.get_setting(self, "dev_enable_error").lower()
            if x is None or x == 'none':
                # then disable/remove the dev_error channel
                self._tracer.debug("Base(%s) Disabling error channel per user-config",
                        self.__showname)
                self.remove_one_property(self.__err_chn_name)
                self.__err_chn_name = None

            elif x != self.__err_chn_name.lower():
                # then enabled, but use different name
                self._tracer.debug("Base(%s) Rename error channel from %s to %s",
                        self.__showname, self.__err_chn_name, x)

                # delete the old channel
                self.remove_one_property(self.__err_chn_name)
                self.__err_chn_name = x

                x = ChannelSourceDeviceProperty(name=self.__err_chn_name, type=bool,
                    initial=Sample(timestamp=0, value=True, unit="not_init"),
                    perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP,)
                self.add_property(x)

            else: # else unknown - just leave as is
                pass
                # self._tracer.warning("Base(%s) Unknown value of (%s)",
                #        self.__showname, x)
                #self._tracer.warning("Base(%s) Leaving error channel unchanged",
                #        self.__showname)
        # else self.__err_chn_name is None, so we never created error channel

        ## Handle the poll settings
        self._poll_rate,change = self._import_adjust_time_setting( \
                            "dev_poll_rate_sec", "Poll Rate")

        if self._poll_rate is None or (self._poll_rate == 0):
            # then disable all timing control
            self.disable_polling()

        else: # import/normalize the poll settings

            apply = change

            # import the poll_rate - how often to send a new poll
            self._rsp_tout,change = self._import_adjust_time_setting( \
                            "dev_response_timeout_sec", "Response TimeOut")
            if change:
                apply = True

            if SettingsBase.get_setting(self, "dev_poll_cleanly_min"):
                # then self._poll_rate must be 60 seconds or more,
                #      plus must be factor of 60
                mins = int(self._poll_rate/60)
                mins = mins % 60
                if mins not in sleep_aids.PERMITTED_VALUES:
                    self._tracer.error("Disabling '%s' because poll_rate of %d secs is incompatible", \
                                        'dev_poll_cleanly_min', self._poll_rate)
                    SettingsBase.set_pending_setting(self, "dev_poll_cleanly_min", False)
                    apply = True

        return apply

    def cancel_next_poll(self):
        """ Cancel any pending next_poll timer """
        try:
            if self.__poll_timer is not None:
                # then try to delete old one
                self.schedule_cancel(self.__poll_timer)
        except:
            self.__poll_timer = None
        return

    def schedule_first_poll(self):

        if self._poll_rate > 0:
            if self._poll_rate > self.RDB_INITIAL_POLL:
                x = self.RDB_INITIAL_POLL
            else:
                x = self._poll_rate

            self._tracer.info("%s initial poll to be after %d secs",
                            self.__showname, x)
            self.schedule_next_poll(x)

        else:
            self._tracer.debug("%s Polling will not start per user-config",
                            self.__showname)

        # no need of this variable anymore
        del self._start_polling

        return

    def schedule_next_poll(self, rate=None):
        """ Set the event callback for next poll """

        self.cancel_next_poll()

        if rate is None:
            rate = self._poll_rate
            if SettingsBase.get_setting(self, "dev_poll_cleanly_min"):
                # then we need to tweak to realign to real time
                rate = sleep_aids.secs_until_next_minute_period(
                            self._poll_rate/60, time.gmtime())

        # rate is our seconds until next poll

        # self._tracer.debug('%s: Schedule Next Poll in %d seconds', self.__showname, rate)

        self.__poll_timer = self.schedule_after(rate, self._next_poll_cb)
        return

    #
    ## RESPONSE TIMEOUT ROUTINES
    #
    def _rsp_tout_cb(self):

        self._response_timeout_count += 1
        # clear last poll time - we failed
        self._last_poll_time = 0

        # call any derived class poll
        try:
            self.response_timeout(self._response_timeout_count)
        except:
            self._tracer.error('%s: Response Timeout handler failed!', self.__showname)
            self._tracer.debug(traceback.format_exc())
        return

    def response_timeout(self, rsp_tout_count=0):
        self._tracer.warning('%s Response Timeout!', self.__showname)
        return

    def cancel_response_timeout(self):
        """ Cancel any pending next_poll timer """
        try:
            if self.__rsp_timer is not None:
                # then try to delete old one
                # self._tracer.debug('%s: Cancel Response Timeout', self.__showname)
                self.schedule_cancel(self.__rsp_timer)
            #else:
            #    self._tracer.debug('%s: No Response Timeout to Cancel', self.__showname)
        except:
            # print traceback.format_exc()
            pass

        self.__rsp_timer = None
        return

    def start_response_timeout(self, tout=None):
        """ Set the event callback for next poll """

        self.cancel_response_timeout()

        if tout is None:
            tout = self._rsp_tout
            # "dev_poll_cleanly_min" doesn't apply to response timeout

        self._tracer.debug('%s: Start Response Timeout of %d seconds',
                self.__showname, tout)

        self.__rsp_timer = self.schedule_after(tout, self._rsp_tout_cb)
        return

    def get_response_timeout_sec(self):
        return self._rsp_tout

# Error Channel Management

    def get_error_channel_name(self):
        '''Return name of error channel, or None if disabled'''
        return self.__err_chn_name

    def get_error_channel_value(self):
        if not self.__err_chn_name:
            # then error channel is disabled
            self._tracer.debug("Channel '%s' is disabled, so value = None",
                                self.__err_chn_name)
            return None
        return self.property_get(self.__err_chn_name).value

    def set_xbee_error(self, status=True, force=False):
        return self.set_error(status, force, self.RDB_XBEE_ERROR, 'XBee')

    def set_driver_error(self, status=True, force=False):
        return self.set_error(status, force, self.RDB_DRIVER_ERROR, 'Driver')

    def set_error(self, status, force, mask, msg):
        # update error channel only if changed
        if not self.__err_chn_name:
            # then error channel is disabled, do nothing
            return None

        old = self.property_get(self.__err_chn_name).value
        if old & self.RDB_NOT_INIT: # always clear the RDB_NOT_INIT
            old &= ~self.RDB_NOT_INIT # always clear the RDB_NOT_INIT
            force = True

        if force or (bool(old & mask) != status):
            now = time.time()
            if status:
                old |= mask
            else:
                old &= ~mask

            if not force:
                self._tracer.info("%s: channel '%s' going %s at %s",
                        msg, self.__err_chn_name, status, iso_date(now))
            else:
                self._tracer.debug("%s: channel '%s' forced to %s",
                        msg, self.__err_chn_name, status)
            self.property_set(self.__err_chn_name, Sample(now, old))
            return True

        return False

    def show_bytes(self, szMsg, data, bNewLine=None):
        if(not data):
            st = "%s[None]" % szMsg
        else:
            if(bNewLine==None):
                bNewLine = (len(data)>32)
            st = "%s[%d]" % (szMsg, len(data))
            nOfs = 0
            for by in data:
                if(bNewLine and ((nOfs%32)==0)):
                    st += '\n[%04d]:' % nOfs
                try:
                    st += " %02X" % ord(by)
                    nOfs += 1
                except:
                    st += ',bad type=' + str(by)
                    break
        return st

    def iso_date(self, t=None, use_local_time_offset=False):
        """
        Return an ISO-formatted date string from a provided date/time object.

        Arguments:

        * `t` - The time object to use.  Defaults to the current time.
        * `use_local_time_offset` - Boolean value, which will adjust
            the ISO date by the local offset if set to `True`. Defaults
            to `False`.

        """
        if t is None:
            t = time.time()

        tm_utc = time.gmtime(t)
        # lto = None
        if use_local_time_offset:
            tm_loc = time.localtime(t)
            time_str = time.strftime("%Y-%m-%dT%H:%M:%S", tm_loc)
            tz_hr = tm_loc[3]-tm_utc[3]
            tz_min = tm_loc[4]-tm_utc[4]
            if (tz_hr == 0) and (tz_min == 0):
                # is UTC/'Zulu Time' regardless of desire for LocalTime
                time_str += 'Z'
            else:
                # example 1994-11-05T08:15:30-05:00
                time_str += "%+03d:%02d" % (tz_hr, tz_min)

        else: # 1994-11-05T13:15:30Z - aka: Zulu Time
            time_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", tm_utc)

        return time_str

# internal functions & classes

    def _import_adjust_time_setting(self, set_name, print_name):
        """\
        read in a time-string, adjust to sec and tweak setting if required"""
        xset = SettingsBase.get_setting(self, set_name)
        if isinstance(xset, types.StringType):
            # parse out the time into seconds
            xadj = parse_time_duration(xset, in_type='sec', out_type='sec')

            if xset != str(xadj):
                # then we changed the value, update the setting
                self._tracer.debug("%s %s string '%s' adjusted to %d sec", \
                             self.__showname, print_name, xset, xadj)
                try:
                    SettingsBase.set_pending_setting(self, set_name, str(xadj))

                except:
                    self._tracer.error(traceback.print_exc())

            return xadj,True

        # else if IntType, use as it
        return xset,False
