############################################################################
#                                                                          #
# Copyright (c)2008-2010, Digi International (Digi). All Rights Reserved.  #
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
Device that breaks out sub-totals from a non-resettable totalizer.

Settings:
* **total_source** is the channel to subscribe too, which is assumed the be
  the totalizer. int(value) is used to force it to be integer only.

* **delta** is an optional Boolean setting.  It defaults True.
  If true, then a channel named 'delta' is added to the device which holds
  the last cycle change in the totalizer. So if the totalizer updates every
  10 minutes, the device.delta shall be the change in the last 10 minutes.

* **hourly** is an optional Boolean setting.  It defaults False.
  If true, then a channel named 'hourly_last' is added to the device which
  holds the change over the clock hour. Note that a sample at 2:00:00pm
  will be counted in the next hour, not the last hour, while a sample at
  1:59:59pm will be counted in the last hour.

* **rollover_mask** is an optional long, which defaults to 0xFFFFFFFF.
  It detects when the totalizer 'rolls over'. If annotate is true, the
  first samples after rollover will have an 'other' string attached

* **annotate** is an optional Boolean setting.  It defaults True.
  If true, then Dia annotated samples are used for errors and warnings.

Channels:
* **.total** is an echo of the total in. It is type long.

* **.delta** exists ONLY if setting delta = True.  It contains the last
  change (delta) of the totals between updates.  It is type long.

* **.hourly_sub** exists ONLY if setting hourly = True.  It contains the
  accumulated delatas in the PREVIOUS clock hour. It is type long.

* **.hourly_total** exists ONLY if setting hourly = True.  It is a snapshot
  of the FIRST totalizer value of the CURRENT clock hour. It is type long.

* **.daily_sub** exists ONLY if setting daily = True.  It contains the
  accumulated delatas in the PREVIOUS calender day. It is type long.

* **.dialy_total** exists ONLY if setting daily = True.  It is a snapshot
  of the FIRST totalizer value of the CURRENT calender day. It is type long.

Example: YML

  - name: subtots
    driver: devices.vendors.comverge.subtotal:SubTotalizerDevice
    settings:
        total_source: pipe1.total_flow
        delta: True
        hourly: True

"""

#Imports
import sys
import traceback
import copy as dcopy
#print dir(copy)

from core.tracing import get_tracer
from devices.device_base import DeviceBase
from settings.settings_base import SettingsBase, Setting
from channels.channel_source_device_property import *
from channels.channel_manager import ChannelManager

from samples.sample import *
try:
    from samples.annotated_sample import *
except:
    print 'AnnotatedSample is not available'
    pass

#Constants

#Exception classes
class RunTimeInitError(Exception):
    pass

#Interface functions

#Classes
class SubTotalizerDevice( DeviceBase):

    TOTAL_SOURCE = 'total_source'        # adds time to totalizers
    ANNOTATE = 'annotate'
    ROLLOVER = 'rollover_mask'
    DELTA_ENB = 'delta'
    HOURLY_ENB = 'hourly'
    DAILY_ENB = 'daily'

    TOTAL_OUT = 'total'
    DELTA_OUT = 'delta'
    HOUR_SUB = 'hourly_sub'
    HOUR_START = 'hourly_start'
    DAILY_SUB = 'daily_sub'
    DAILY_START = 'daily_start'

    def __init__(self, name, core_services):
        self.__core = core_services
        self.__tracer = get_tracer("SubTot(%s)" % name)

        # hold last totalizer - start as invalid
        self.total_last = None
        self.delta_out = None
        self.hourly = None
        self.daily = None

        ##Settings Table Definition:
        settings_list = [
            # subscription to totalizer source
            Setting( name=self.TOTAL_SOURCE, type=str, required=True),

            # disable use of the annotated channels
            Setting( name=self.ANNOTATE, type=bool, required=False,
                default_value=True),

            # define the ROLL_OVER point
            Setting( name=self.ROLLOVER, type=long, required=False,
                default_value=0xFFFFFFFFL),

            # enable the delta output channel
            Setting( name=self.DELTA_ENB, type=bool, required=False,
                default_value=True),

            # enable the hourly output channel(s)
            Setting( name=self.HOURLY_ENB, type=bool, required=False,
                default_value=False),

            # enable the daily output channel(s)
            Setting( name=self.DAILY_ENB, type=bool, required=False,
                default_value=False),
        ]

        ##Channel Properties Definition:
        ##Properties are added dynamically based on configured transforms
        property_list = [
            # an input to RESET the totals
            ChannelSourceDeviceProperty(name=self.TOTAL_OUT, type=long,
                initial=Sample(timestamp=0, value=-1L),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP),

            ]

        ## Initialze the Devicebase interface:
        DeviceBase.__init__(self, name, self.__core,
                                settings_list, property_list)
        return

    ##Functions which must be implemented to conform to the DeviceBase
    ##interface:
    def apply_settings(self):
        """Called when new configuration settings are available."""

        SettingsBase.merge_settings(self)
        accepted, rejected, not_found = SettingsBase.verify_settings(self)

        if len(rejected) or len(not_found):
            # there were problems with settings, terminate early:
            self.__tracer.error("Settings rejected/not found: %s %s",
                                rejected, not_found)
        else:
            SettingsBase.commit_settings(self, accepted)
            self.__tracer.debug("Settings accepted: %s", accepted)

        return (accepted, rejected, not_found)

    def start(self):
        """Start the device driver. Returns bool."""

        self.__tracer.info("starting device")

        isam = Sample(timestamp=0, value=-1L)
        self.annotate = SettingsBase.get_setting(self, self.ANNOTATE)
        if self.annotate:
            # if annotate, replace with a non-init error
            try:
                isam = AnnotatedSample(isam)
                isam.errors.add(ERSAM_NOT_INIT)
                self.property_set(self.TOTAL_OUT, dcopy.copy(isam))

            except: # assume is NOT available, force False
                self.__tracer.error(traceback.format_exc())
                self.__tracer.error('annotation requested, but not available')
                self.annotate = False
                # SettingsBase.set_setting(self, self.ANNOTATE, False)

        # if not self.annotate, then isam remains Sample

        cm = self.__core.get_service("channel_manager")
        cp = cm.channel_publisher_get()
        # cdb = cm.channel_database_get()

        # get the totalizer source, fault is bad/missing
        x = SettingsBase.get_setting(self, self.TOTAL_SOURCE)
        try:
            cp.subscribe( x, self.prop_new_total )
            bTimeSource = True
            self.__tracer.info('totalizer source channel is %s', x)
        except:
            self.__tracer.error(traceback.format_exc())
            self.__tracer.error('source channel NOT found', x)
            # return False

        # see if we want the delta channel
        try:
            x = SettingsBase.get_setting(self, self.DELTA_ENB)
            self.__tracer.info('delta channel is %s', x)
            self.delta_out = x
            if self.delta_out:
                # then create them
                self.add_property(
                    ChannelSourceDeviceProperty(
                        name=self.DELTA_OUT, type=long,
                        initial=dcopy.copy(isam),
                        perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP)
                    )

        except:
            self.__tracer.error(traceback.format_exc())
            self.__tracer.error('delta channel creation failed')

        # see if we want the hourly channel
        try:
            x = SettingsBase.get_setting(self, self.HOURLY_ENB)
            self.__tracer.info('hourly channel is %s', x)

            if x:
                # then create the channels
                self.hourly = [-1,0]
                self.add_property(
                    ChannelSourceDeviceProperty(
                        name=self.HOUR_SUB, type=long,
                        initial=dcopy.copy(isam), perms_mask=DPROP_PERM_GET,
                        options=DPROP_OPT_AUTOTIMESTAMP)
                    )
                self.add_property(
                    ChannelSourceDeviceProperty(
                        name=self.HOUR_START, type=long,
                        initial=dcopy.copy(isam), perms_mask=DPROP_PERM_GET,
                        options=DPROP_OPT_AUTOTIMESTAMP)
                    )

        except:
            self.__tracer.error(traceback.format_exc())
            self.__tracer.error('hourly channel creation failed')

        # see if we want the daily channel
        try:
            x = SettingsBase.get_setting(self, self.DAILY_ENB)
            self.__tracer.info('daily channels are %s', x)

            if x:
                # then create the channels
                self.daily = [-1,0]
                self.add_property(
                    ChannelSourceDeviceProperty(
                        name=self.DAILY_SUB, type=long,
                        initial=dcopy.copy(isam), perms_mask=DPROP_PERM_GET,
                        options=DPROP_OPT_AUTOTIMESTAMP)
                    )
                self.add_property(
                    ChannelSourceDeviceProperty(
                        name=self.DAILY_START, type=long,
                        initial=dcopy.copy(isam), perms_mask=DPROP_PERM_GET,
                        options=DPROP_OPT_AUTOTIMESTAMP)
                    )

        except:
            self.__tracer.error(traceback.format_exc())
            self.__tracer.error('daily channel creation failed')

        return True

    def stop(self):
        """Stop the device driver. Returns bool."""

        self.__tracer.info("stopping device")
        return True

#Internal functions & classes

    def prop_new_total(self, sam):
        # someone pushing in new input

        try:
            if len(sam.error) > 0:
                # then is Annotated with an error, do not subtotal bad data
                return None

        except AttributeError:
            self.__tracer.debug('not annotated sample, assume okay & continue')
            pass

        except:
            self.__tracer.error(traceback.format_exc())

        if not isinstance( sam, Sample):
            # the publish/sub pushes in the channel
            sam = sam.get()

        if sam.unit == 'time':
            # then assume is alarm_clock device for testing as:
            # (1244544360.0, (2009, 6, 9, 10, 46, 0, 1, 160, -1))
            total_now = long(sam.value[0])
        else:
            total_now = long(sam.value)

        if total_now == 0:
            self.__tracer.debug('Skipping new total of zero - assume error?')
            return None

        return self.subtotal(total_now, sam.unit)

    def subtotal( self, total_now, uom=''):
        # the raw algorithm - here to enable bulk testing

        total_now = long(total_now) # force to long incase just INT
        self.__tracer.debug('subtotal: new total input %d', total_now)

        now = time.time()
        now_tup = None

        # chop down if roll-over is lower than field
        self.rollover = SettingsBase.get_setting(self, self.ROLLOVER)
        total_now &= self.rollover

        if self.total_last is None:
            # then is the first run, just save and return - no delta yet
            self.__tracer.debug('first run, take total as is')
            self.property_set(self.TOTAL_OUT, Sample(now, total_now, uom))
            self.total_last = total_now
            return True

        # we always calc delta to watch for garbage input
        if(self.total_last <= total_now):
            # then is normal, totalizer growing
            delta = total_now - self.total_last
            delta_other = None

        else: # else is roll-over?
            delta = (self.rollover - self.total_last) + total_now
            delta_other = 'totalizer rollover: previous:%d current:%d delta:%d' % \
                          (self.total_last, total_now, delta)
            print delta_other

        # echo the totalizer output sample
        total_sam = Sample(now, total_now, uom)
        if delta_other and self.annotate:
            # annotate is was roll-over
            total_sam = AnnotatedSample(total_sam)
            total_sam.other.add(delta_other)

        self.property_set(self.TOTAL_OUT, total_sam)
        self.total_last = total_now

        # update the delta output channel (if we have)
        if self.delta_out:
            self.__tracer.debug('Update channel.delta as:%d', delta)
            sam = Sample(now, delta, uom)
            if delta_other and self.annotate:
                # annotate is was roll-over
                sam = AnnotatedSample(sam)
                sam.other.add(delta_other)

            self.property_set( self.DELTA_OUT, sam)

        # update the hourly output channels (if we have)
        if self.hourly is not None:
            if now_tup is None:
                # since we just do hour-by-hour, time zone isn't important yet
                now_tup = time.localtime( now)

            try:
                accum = long(self.hourly[1])
                if self.hourly[0] != now_tup[3]:
                    # then a new hour, copy last accum to last hour

                    # save current hour (0-23)
                    self.hourly[0] = now_tup[3]

                    # update the hourly channels
                    self.__tracer.debug('Update hourly_last as:%d', accum)
                    self.property_set( self.HOUR_SUB, Sample(now, accum, uom))
                    self.property_set( self.HOUR_START, total_sam)

                    # 'next' hours starts at delta
                    self.hourly[1] = delta # reset to delta only

                else:
                    self.hourly[1] = long(accum + delta)
                    self.__tracer.debug('hourly builds to:%d', self.hourly[1])

            except:
                self.__tracer.error(traceback.format_exc())

        # update the daily output channels (if we have)
        if self.daily is not None:
            if now_tup is None:
                # since we just do hour-by-hour, time zone isn't important yet
                now_tup = time.localtime( now)

            try:
                accum = long(self.daily[1])
                if self.daily[0] != now_tup[2]:
                    # then a new day, copy last accum to last day

                    # save current day (1-31)
                    self.daily[0] = now_tup[2]

                    # update the daily channels
                    self.__tracer.debug('Update daily_sub as:%d', accum)
                    self.property_set( self.DAILY_SUB, Sample(now, accum, uom))
                    self.property_set( self.DAILY_START, total_sam)

                    # 'next' daily starts at delta
                    self.daily[1] = delta # reset to delta only

                else:
                    self.daily[1] = long(accum + delta)
                    self.__tracer.debug('Daily builds to:%d', self.daily[1])

            except:
                self.__tracer.error(traceback.format_exc())

        return True
