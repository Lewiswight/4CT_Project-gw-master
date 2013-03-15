############################################################################
#                                                                          #
# Copyright (c)2008,2009 Digi International (Digi). All Rights Reserved.   #
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
The Alarm Clock device is a low-speed general resource which can help other devices
accomplish simple timed actions. It is designed to work with minutes or hours.  Users
who needed timed behavior faster than once per minute should use their own thread
and timer logic.

At present it only offers:

1. The ability to trigger a transform (or publish a set) every:
    * **minute:** Once per minute, when seconds = 0
    * **hour:** Once per hour, when minutes & seconds = 0
    * **six_hour:** Once per 6 hours, so at 00:05:00, 06:05:00, 12:05:00 and 18:05:00
    * **day:** Once per day, so at 00:00:00 / midnight
2. It can print the line "{name}: time is now 2009-05-31 10:47:00" at any of
   the above time intervales.

TODO:

* Add a cron-like ability for other devices to request publish/sets at times such
  at 3:27am each Tuesday.
* Move things like NTP time update and Dia periodic garbage collection to this device
* Consider adding a second 'helper' thread to run complex/long jobs

Settings:

* **tick_rate:** Is optional and in seconds.  Default is 60 seconds.  Changing this does NOT
  affect the minutes etc, as those are based the real time clock; this only affects
  how often the thread wakes.  Setting it to 15 means the thread wakes up 4 times for
  even 'minute' event.  Setting 300 means 4 of 5 minute events are missed.

* **printf:** Is optional and defaults to None. It defines how often the trace 'time is now'
  line prints, and can be set to one of ``['minute','hour','six_hour','day']``

Publishable outputs:
* **15_sec:** set/publish a sample once per 15 seconds
* **minute:** set/publish a sample once per minute
* **15_min:** set/publish a sample once per 15 minutes
* **hour:** set/publish a sample once per hour
* **six_hour:** set/publish a sample once per 6 hours
* **day:** set/publish a sample once per day

The SAMPLE is a tuple like this: ``(1244544360.0, (2009, 6, 9, 10, 46, 0, 1, 160, -1))``

* The first number is the ``time.time()`` response, so UNIX seconds since epoch.
* The second item is the ``time.localtime()`` converted to a tuple.

.. Note::
    You might MISS sets/publishes - for example another task might cause
    the alarm clock to be busy LONGER than 1 minute. So you device should examine the TIME
    value in the set/publish to determine how many seconds have really occured since the
    last event.

YML Example::

    This example shows the alarm clock device being named 'tick_tock', plus a second
    device which subscribes to tick_tock.minute, which allows the device to run once
    per minute without requiring a thread of it's own

      - name: tick_tock
        driver: devices.alarm_clock_device:AlarmClockDevice
        settings:
            printf: minute

      - name: motor_01_hours
        driver: devices.blocks.counter_device:HourMeterBlock
        settings:
            active_true: True
            input_source: motor_01.channel1_input
            tick_source: tick_tock.minute

"""

# imports
from devices.device_base import DeviceBase
from settings.settings_base import SettingsBase, Setting
from channels.channel_source_device_property import *

import threading
import sys
import time
import traceback
import types

# constants
# time tup from time module
TM_YEAR = 0     # year, 4-digit such as 2009
TM_MON = 1      # month, 1-12
TM_MDAY = 2     # day of month, 1-31
TM_HOUR = 3     # hour, 0-59
TM_MIN = 4      # minutes, 0-59
TM_SEC = 5      # seconds, 0-59
TM_WDAY = 6     # day of week, 0-6 with 0=Monday
TM_YDAY = 7     # day of year, Julian day, 1-366
TM_ISDST = 8    # DST (Daylight Savings Time) flag (-1, 0 or 1)

MIN_SLEEP = 2   # minimum sleep permited

PROP_15SEC = '15_sec'
PROP_MINUTE = 'minute'
PROP_15MIN = '15_min'
PROP_HOUR = 'hour'
PROP_SIXHR = 'six_hour'
PROP_DAY = 'day'
PROP_TICK_RATE = 'tick_rate'
PROP_PRINTF = 'printf'

# exception classes

# interface functions

# classes

class ClockEvent:
    """Handle a single on/off event"""

    # tuple settings
    OFS_NAME = 0
    OFS_PERIOD = 1
    OFS_TRUE = 2
    OFS_FALSE = 3

    # Period types
    PER_HOURLY = 0
    PER_DAILY = 0x7F # bit-map the 7 days of the week

    def __init__(self, parent, **kw):
        self.__parent = parent

        # test ['nam'] - should be unique?

        period = kw.get('per','daily')
        if( period == 'hourly'):
            # then is like '>f' etc
            period = self.PER_HOURLY
            self.next_period = self.next_hourly
            # time delays in minute AFTER the hour

        else: # else not found so assume daily
            period = self.PER_DAILY
            self.next_period = self.next_daily
            # time delays in minute AFTER midnight

        print 'kw', kw
        time_on = self.calc_minutes( kw['on'])
        time_off = self.calc_minutes( kw['off'])

        # just save as TUPLE to reduce size - things shouldn't change
        self.__tup = ( kw['nam'], period, time_on, time_off )
        self.last_sam = None
        self.trigger_time = 0
        self.trigger_value = False

        print ' >> Create ClockEvent =', self.__tup

        self.__parent.add_property(
            ChannelSourceDeviceProperty(
                name=self.get_name(), type=self.get_type(),
                initial=Sample(0, self.trigger_value, self.get_units() ),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP)
            )

        return

    def clear_links( self):
        self.__parent = None
        return

    def get_name( self):
        return self.__tup[self.OFS_NAME]

    def get_last_sample( self):
        return self.last_sam

    def get_period( self):
        return self.__tup[self.OFS_PERIOD]

    def get_type( self):
        return bool

    def get_units( self):
        return 'bool'

    def process(self, now):
        """see if I am to 'toggle' etc

        form of  now is (self.time_now, tuple(self.time_tup))"""

        if( self.trigger_time == 0):
            # print " >event(%s) initialize & update output to 'previous' level" % self.get_name()
            self.next_period( now)
            self.last_sam = Sample(now[0], not (self.trigger_value), self.get_units())
            self.__parent.property_set( self.get_name(), self.last_sam )

        elif( self.trigger_time <= now[0]):
            # print " >event(%s) hit trigger time" % self.get_name()
            self.last_sam = Sample(now[0], self.trigger_value, self.get_units())
            self.__parent.property_set( self.get_name(), self.last_sam )
            self.next_period( now)

        else:
            if self.__parent.trace:
                # this is always UTC since we want duration, not time
                x = time.gmtime(self.trigger_time - now[0])
                print " >event(%s) next trigger in %s" % (self.get_name(), \
                    ("%02d:%02d:%02d" % (x[TM_HOUR],x[TM_MIN],x[TM_SEC]) ) )

        return self.last_sam

    def next_hourly(self, now):
        """Calculate the next hourly trigger point"""
        # now is (self.time_now, tuple(self.time_tup))

        now_min = now[1][TM_MIN]

        # 60 minutes in a day, so add 60 if event next hour, 0=never add days
        return self.next_period_helper( now, now_min, 60, 0)

    def next_daily(self, now):
        """Calculate the next daily trigger point"""
        # now is (self.time_now, tuple(self.time_tup))

        # estimate number of days based on which days included
        add_days = 0 # so do tomorrow

        # calc the present minutes AFTER midnight
        now_min = (now[1][TM_HOUR] * 60) + now[1][TM_MIN]

        # 1440 minutes in a day, so add 1440 if event tomorrow
        return self.next_period_helper( now, now_min, 1440, add_days)

    def next_period_helper( self, now, now_min, add_if_minus, add_days):
        # a lower helper function used by many
        # now is the 'time' sample
        # now_minutes is how many minutes since 'start of period'
        # add_if_minus is extra minutes to push to NEXT period (next hour, next day etc)
        # add days if some days are being skipped

        # calc the minutes until next ON event
        delay_on = (self.__tup[self.OFS_TRUE] - now_min)
        if( delay_on <= 0):
            delay_on += add_if_minus

        # calc the minutes until next OFF event
        delay_off = (self.__tup[self.OFS_FALSE] - now_min)
        if( delay_off <= 0):
            delay_off += add_if_minus

        if self.__parent.trace:
            print " >event(%s) ON in %d min, OFF in %d min" % (self.get_name(), delay_on, delay_off)

        if( delay_on < delay_off):
            if self.__parent.trace:
                print " >event(%s) last event was %s, next event will be ON" % (self.get_name(), self.trigger_value)
            self.trigger_value = True
            self.trigger_time = delay_on

        else: # else False/Off is next event
            if self.__parent.trace:
                print " >event(%s) last event was %s, next event will be OFF" % (self.get_name(), self.trigger_value)
            self.trigger_value = False
            self.trigger_time = delay_off

        # estimate seconds-delay until next event
        # start with time NOW in seconds, add delay for any idle days (aka: weekend?)
        # convert minutes delay to seconds, then remove stray seconds, plus undershoot by 1 sec
        self.trigger_time = now[0] + (add_days * 86400) + \
                (self.trigger_time * 60) - (now[1][TM_SEC] - 5)

        return

    def calc_minutes( self, src):
        """Convert source into minutes"""
        if isinstance( src, types.IntType):
            # assume is ALREADY minutes
            return src

        if isinstance( src, types.StringType):
            # assume is "HH:MM" (ignore seconds if "HH:MM:SS")
            try:
                x = src.split(":")
                return (int(x[0]) * 60) + int(x[1])

            except:
                traceback.print_exc()

        return None

class AlarmClockDevice(DeviceBase, threading.Thread):

    # misc constants
    ACTION_LIST = 'action_list'
    TRACE_ENB = 'trace'
    TIME_MODE = 'use_time'

    def __init__(self, name, core_services):
        self.__name = name
        self.__core = core_services

        # these help us publish the pulses
        self.push_15sec = False
        self.push_min = False
        self.push_15min = False
        self.push_hr = False
        self.push_six = False
        self.push_day = False

        self.action_list = []
        self.trace = False

        ## Settings Table Definition:
        settings_list = [

            Setting(name=PROP_PRINTF, type=str, required=False, default_value=PROP_MINUTE),

            Setting( # how often to check for work
                name=PROP_TICK_RATE, type=int, required=False, default_value=60,
                  verify_function=lambda x: x > 0.0),

            # allow affecting the trace output
            Setting( name=self.TRACE_ENB, type=str, required=False, \
                default_value='False') ,

            # allow affecting the trace output
            Setting( name=self.TIME_MODE, type=str, required=False, \
                default_value='local') ,

            # the optional event/action list
            Setting( name=self.ACTION_LIST, type=list, required=False, \
                default_value=[]),
        ]

        ## Channel Properties Definition:
        property_list = [
            # gettable properties

            ChannelSourceDeviceProperty(name=PROP_15SEC, type=tuple,
                initial=Sample(timestamp=0, value=(0,None)),
                perms_mask=DPROP_PERM_GET),

            ChannelSourceDeviceProperty(name=PROP_MINUTE, type=tuple,
                initial=Sample(timestamp=0, value=(0,None)),
                perms_mask=DPROP_PERM_GET),

            ChannelSourceDeviceProperty(name=PROP_15MIN, type=tuple,
                initial=Sample(timestamp=0, value=(0,None)),
                perms_mask=DPROP_PERM_GET),

            ChannelSourceDeviceProperty(name=PROP_HOUR, type=tuple,
                initial=Sample(timestamp=0, value=(0,None)),
                perms_mask=DPROP_PERM_GET),

            ChannelSourceDeviceProperty(name=PROP_SIXHR, type=tuple,
                initial=Sample(timestamp=0, value=(0,None)),
                perms_mask=DPROP_PERM_GET),

            ChannelSourceDeviceProperty(name=PROP_DAY, type=tuple,
                initial=Sample(timestamp=0, value=(0,None)),
                perms_mask=DPROP_PERM_GET),

        ]

        ## Initialize the DeviceBase interface:
        DeviceBase.__init__(self, self.__name, self.__core,
                                settings_list, property_list)

        actions = SettingsBase.get_setting(self, self.ACTION_LIST)
        # print 'actions', actions
        for itm in actions:
            # each polls consists of a Modbus read
            # print 'item1', itm
            try:
                itm = itm['event']
                # print 'item2', itm
                act = ClockEvent(self, **itm)
                self.action_list.append( act)
            except:
                traceback.print_exc()

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
            print "Settings rejected/not found: %s %s" % (rejected, not_found)

        SettingsBase.commit_settings(self, accepted)

        return (accepted, rejected, not_found)

    def start(self):
        """Start the device driver.  Returns bool."""
        self.trace = SettingsBase.get_setting(self, self.TRACE_ENB)
        threading.Thread.start(self)
        return True

    def stop(self):
        """Stop the device driver.  Returns bool."""
        self.__stopevent.set()

        for act in self.action_list:
            act.clear_links()
            del act
        self.action_list = None

        return True

    ## Locally defined functions:
    # Property callback functions:

    def print_time_is_now( self):
        # then user wants the lines
        self.time_str = "%04d-%02d-%02d %02d:%02d:%02d" % self.time_tup[:TM_WDAY]
        print '\n%s: time is now %s' % (self.__name, self.time_str)
        return

    def get_time_tuple( self, now=None):
        """Return either local or UTC time"""
        if( SettingsBase.get_setting(self, self.TIME_MODE) == 'local'):
            return time.localtime( now)
        else:
            return time.gmtime( now)

    # Threading related functions:
    def run(self):
        """run when our device driver thread is started"""

        while 1:
            if self.__stopevent.isSet():
                self.__stopevent.clear()
                break

            self.time_now = time.time()
            self.time_tup = self.get_time_tuple(self.time_now)
            self.sample = (self.time_now, tuple(self.time_tup))

            rate = SettingsBase.get_setting(self, PROP_TICK_RATE)
            # print 'rate = %d, %s' % (rate,str(self.time_tup))
            want_print = SettingsBase.get_setting(self, PROP_PRINTF)

            # first, handle the odd 15-sec one
            if( rate <= 16):
                # print self.time_tup
                if (self.time_tup[TM_SEC] in [5,20,35,50]):
                    if( not self.push_15sec):
                        self.push_15sec = True
                        self.property_set(PROP_15SEC, Sample(self.time_now, self.sample, 'time'))
                else:
                    self.push_15sec = False

            # publish the pulses
            if( (rate == 60) or (self.time_tup[TM_SEC] == 0)):
                # publish minute pulse when see sec=zero
                # should never see twice in 1 minute, so no self.push_min
                if( want_print == PROP_MINUTE):
                    # print once only if desired
                    self.print_time_is_now()
                # print '.',
                self.property_set(PROP_MINUTE, Sample(self.time_now, self.sample, 'time'))

                if( self.time_tup[TM_MIN] in [1,16,31,46]):
                    # publish 15-minute pulse only first time we see
                    if( not self.push_15min):
                        self.push_15min = True
                        if( want_print == PROP_15MIN):
                            # print once only if desired
                            self.print_time_is_now()
                        # print '<Six>',
                        self.property_set(PROP_15MIN, Sample(self.time_now, self.sample, 'time'))
                else:
                    self.push_15min = False

                    if( self.time_tup[TM_MIN] == 0):
                        # publish hourly pulse only first time we see min=zero
                        if( not self.push_hr):
                            self.push_hr = True
                            if( want_print == PROP_HOUR):
                                # print once only if desired
                                self.print_time_is_now()
                            # print '<Hour>',
                            self.property_set(PROP_HOUR, Sample(self.time_now, self.sample, 'time'))

                        if( self.time_tup[TM_HOUR] == 0):
                            # publish daily pulse only first time we see hour=zero
                            if( not self.push_day):
                                self.push_day = True
                                if( want_print == PROP_DAY):
                                    # print once only if desired
                                    self.print_time_is_now()
                                # print '<Day>',
                                self.property_set(PROP_DAY, Sample(self.time_now, self.sample, 'time'))
                        else:
                            self.push_day = False

                    elif( (self.time_tup[TM_MIN] == 5) and (self.time_tup[TM_HOUR] in [0,6,12,18])):
                        # publish six-hourly pulse only first time we see min=five
                        if( not self.push_six):
                            self.push_six = True
                            if( want_print == PROP_SIXHR):
                                # print once only if desired
                                self.print_time_is_now()
                            # print '<Six>',
                            self.property_set(PROP_SIXHR, Sample(self.time_now, self.sample, 'time'))
                    else:
                        self.push_six = False
                        self.push_hr = False

            for acts in self.action_list:
                # handle any events waiting
                acts.process( self.sample)

            rate -= (self.time_tup[TM_SEC] % rate)
            if( rate < MIN_SLEEP):
                # if is too short, then push forward to 'next cycle'
                rate += SettingsBase.get_setting(self,PROP_TICK_RATE)

            time.sleep( rate)

        return

# internal functions & classes

def main():
    pass

if __name__ == '__main__':
    import sys
    status = main()
    sys.exit(status)

