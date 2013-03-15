# File: robust_xbee.py
# Desc: the robust XBEE device base - includes heartbeat, robust network
#       settings and other features required by realworld devices

############################################################################
#                                                                          #
# Copyright (c)2008-2012, Digi International (Digi). All Rights Reserved. #
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
    The XBee sensor interface base class.

    All XBee sensor drivers in Dia should derive from this class.

"""

# imports
import types
import traceback

from settings.settings_base import SettingsBase, Setting
from samples.sample import *
from channels.channel_source_device_property import *
from devices.xbee.xbee_device_manager.xbee_device_manager_event_specs \
    import *
from devices.xbee.xbee_config_blocks.xbee_config_block_ddo \
    import XBeeConfigBlockDDO
import devices.xbee.common.prodid as prodid

from devices.vendors.robust.avail_base import Availability
from devices.vendors.robust.robust_base import RobustBase

# constants

# exception classes

# interface functions

# classes

class RobustXBee(RobustBase):

    """\
        Defines the XBee Interface base class.
    """
    # Define a set of default endpoints that devices will send in on.
    # This is for the I/O productions used as heart-beat
    RXBEE_ADDRESS_TABLE = [ [ 0xe8, 0xc105, 0x95 ], [0xe8, 0xc105, 0x92] ]

    # Empty list of supported products.
    RXBEE_SUPPORTED_PRODUCTS = []

    # how many seconds to set HB - since is IR in XBee, limited to 65 sec
    RXBEE_DEF_HEART_BEAT = 60

    # set to a string (like "D3" to force a pin to be input)
    RXBEE_DEF_HEART_BEAT_IO = None

    # how many seconds between HB status diplays as INFO instead of DEBUG
    # default to one message per hour
    RXBEE_DEF_HEART_BEAT_INFO = 60 * 60

    # set this to None to disable, or if RXBEE_DEF_HEART_BEAT = 0, then disabled
    RXBEE_DEF_AVAIL_CHAN = 'availability'
    RXBEE_DEF_ENB_AVAILABILITY = False

    # only update channel with change > deadband
    RXBEE_AVAIL_DEADBAND = 0.5

    RXBEE_DEF_FORCE_WPAN = True
    RXBEE_DEF_FORCE_NAME = False
    RXBEE_DEF_ROBUST_ROUTER = False
    RXBEE_AR_NW_BASE = 5

    # Add 10 seconds to timeout for heart-beat
    HEART_BEAT_ADDER = 10

    # which channel to signal for online/offline
    HB_STATUS_CHAN = 'online'

    # delay going offline until this many missed heart-beats in a row
    OFFLINE_AFTER_BAD = 3

    # For rotary dial, the bits in order from LSB (P2) to MSB (D3)
    RXBEE_DEF_ENB_ROTARY = False
    ROTARY = ['P2', 'P1', 'D4', 'D3']

    # default for sleep setting
    RXBEE_DEF_SLEEP = False

    def __init__(self, name, core_services, settings=None, properties=None):

        # these will be set via RobustBase.__init__()
        # self.__name = name
        # self.__core = core_services
        # self.__settings = ...
        # self.__sched = ...
        # self.__properties = ...
        # self._tracer = ...

        ## Local State Variables:
        self.__showname = 'XBee(%s)' % name

        self.__xbee_manager = None
        self.__extended_address = None

        self._availability = Availability()
        self.__bad_count = 0
        self.__hb_info = 0
        self.__heartbeat_active = False

        ## Settings Table Definition:
        settings_list = [
            Setting(
                name = 'xbee_device_manager', type = str, required = True),

            Setting(
                name = 'extended_address', type = str, required = True),

            # setting to 0 disables ONLINE channels
            Setting(
                name='heart_beat_sec', type=int, required=False,
                default_value=self.RXBEE_DEF_HEART_BEAT,
                verify_function=lambda x: x >= 0 and x <= 65),

            # setting to None disables updating any IO
            Setting(
                name='heart_beat_io', type=str, required=False,
                default_value=self.RXBEE_DEF_HEART_BEAT_IO),

			# force PAN ID
            Setting(
                name='force_wpan_id', type=bool, required=False,
                default_value=self.RXBEE_DEF_FORCE_WPAN),

			# force PAN ID
            Setting(
                name='force_node_name', type=bool, required=False,
                default_value=self.RXBEE_DEF_FORCE_NAME),

			# force network settings for robust router behavior
            Setting(
                name='robust_router', type=bool, required=False,
                default_value=self.RXBEE_DEF_ROBUST_ROUTER),

            # setting to False disables ROTARY_ID channels
            Setting(
                name='enable_rotary_id', type=bool, required=False,
                default_value=self.RXBEE_DEF_ENB_ROTARY),

            # setting to False remove the availability channel
            Setting(
                name='enable_availability', type=bool, required=False,
                default_value=self.RXBEE_DEF_ENB_AVAILABILITY),

            # setting True causes the
            Setting(
                name='sleep', type=bool, required=False,
                default_value=self.RXBEE_DEF_SLEEP),

        ]

        # Add our settings_list entries to the settings passed to us.
        settings = self._safely_merge_lists(settings, settings_list)

        ## Channel Properties Definition:
        property_list = [

            ChannelSourceDeviceProperty(name=self.HB_STATUS_CHAN, type=bool,
                initial=Sample(timestamp=0, value=False, unit="not init"),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP,),

            ChannelSourceDeviceProperty(name="node_id", type=int,
                initial=Sample(timestamp=0, value=-1, unit="not init"),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP,),
        ]

        # set this to None to disable, or if RXBEE_DEF_HEART_BEAT = 0, then disabled
        if self.RXBEE_DEF_AVAIL_CHAN is not None:
            property_list.append(
                ChannelSourceDeviceProperty(name=self.RXBEE_DEF_AVAIL_CHAN, type=float,
                    initial=Sample(timestamp=0, value=0.0, unit="not init"),
                    perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP,)
                )

        # Add our property_list entries to the properties passed to us.
        properties = self._safely_merge_lists(properties, property_list)

        ## Initialize the RobustBase interface:
        RobustBase.__init__(self, name, core_services, settings, properties)
        return

    @staticmethod
    def probe():
        probe_data = { 'address_table':self.RXBEE_ADDRESS_TABLE,
                       'supported_products':self.RXBEE_SUPPORTED_PRODUCTS}

        return probe_data

    def get_xbee_manager(self):
        return self.__xbee_manager

    def get_extended_address(self):
        return self.__extended_address

    def get_ddo_block(self):
        return XBeeConfigBlockDDO(self.__extended_address)


    ## These functions must be implemented by the sensor driver writer:
    # def apply_settings(self):

    def start(self):
        """Start the device driver.  Returns bool."""
        self._tracer.debug("Starting xbee device")
        self.start_pre()
        self.start_post()
        return True

    def start_pre(self):
        """\
            Start the device driver.
        """

        self._tracer.debug("RobustXBee:Start_Pre")

        # suppress the Robust_Device start of polling until XBee config is done
        self._start_polling = False
        RobustBase.start_pre(self)

        # Fetch the XBee Manager name from the Settings Manager:
        xbee_manager_name = SettingsBase.get_setting(self, "xbee_device_manager")
        dm = self.get_core().get_service("device_driver_manager")
        self.__xbee_manager = dm.instance_get(xbee_manager_name)

        # Register ourselves with the XBee Device Manager instance:
        self.__xbee_manager.xbee_device_register(self)

        # Get the extended address of the device:
        self.__extended_address = SettingsBase.get_setting(self, "extended_address")

        # Create a callback to tell this driver when our device has left the
        # configuring state, transitioning to the running state
        x = XBeeDeviceManagerRunningEventSpec()
        x.cb_set(self.running_indication)
        self.__xbee_manager.xbee_device_event_spec_add(self, x)

        self.initialize_robust_xbee()

        return True

    def start_post(self):

        self._tracer.debug("RobustXBee:Start_Post")

        hb = SettingsBase.get_setting(self, "heart_beat_sec")
        if (hb is not None) and (hb > 0):
            # then enable the periodic intake of data productions
            self.__xbee_manager.register_sample_listener(self,
                self.get_extended_address(), self._heart_beat_indication)

            hb = SettingsBase.get_setting(self, "heart_beat_io")
            if (hb is not None) and (len(hb) > 0):
                # then set a dummy IO to input, but only if HeartBeat active
                cfg = self.get_ddo_block()
                cfg.add_parameter(hb, 3)
                self.get_xbee_manager().xbee_device_config_block_add(
                        self, cfg)

        else: # no heart_beat
            try:
                # remove the availability channel
                self.remove_one_property(self.RXBEE_DEF_AVAIL_CHAN)
                # remove the online channel
                self.remove_one_property(self.HB_STATUS_CHAN)
            except:
                pass

        # Indicate that we have no more configuration to add:
        self.get_xbee_manager().xbee_device_configure(self)

        return RobustBase.start_post(self)

    def stop(self):

        # cancel any out-standing events
        try:
            self.__cancel_hb_watchdog()
        except:
            pass

        # Unregister ourselves with the XBee Device Manager instance:
        if self.get_xbee_manager() is not None:
            self.get_xbee_manager().xbee_device_unregister(self)

        return RobustBase.stop(self)

    def initialize_robust_xbee(self, param=None):

        self._tracer.debug("RobustXBee:Start_Initialize")

        # see if our xbee_manager
        if self.get_xbee_manager().is_digimesh():
            self._tracer.debug("We are Running DigiMesh")
            sm = ord(self.get_xbee_manager().xbee_device_ddo_get_param(None, 'SM'))
            self._tracer.debug("DM_Man has SM of %d", sm)

        hb = SettingsBase.get_setting(self, "heart_beat_sec")
        if hb is None:
            self._tracer.info("%s Heart-Beat is disabled: Xbee settings ignored",
                                self.__showname)
            self._availability = None
            self.__heartbeat_active = False
            hb = 0

        elif hb == 0:
            self._tracer.info("%s Heart-Beat is disabled: Clearing Xbee settings",
                                self.__showname)
            self._availability = None
            self.__heartbeat_active = False

        else: # hb should be seconds 1 to 60

            self._tracer.info("%s Heart-Beat is enabled every %d sec",
                                self.__showname, hb)

            # enable the IR productions of IS data
            hb *= 1000
            # xbee_ddo_cfg.add_parameter('IR', hb)
            self.__heartbeat_active = True

        xbee_sleep_cfg = self.__xbee_manager.get_sleep_block(
                    self.__extended_address,
                    SettingsBase.get_setting(self, "sleep"),
                    sleep_rate_ms=hb)
        self.__xbee_manager.xbee_device_config_block_add(self, xbee_sleep_cfg)

        xbee_ddo_cfg = self.get_ddo_block()

        if SettingsBase.get_setting(self, "force_wpan_id"):
            ## then force a fixed PAN ID
            pan_id = self.get_xbee_manager().xbee_device_ddo_get_param(None, 'ID')
            self._tracer.debug('%s: Forcing Fixed WPAN ID of %s',
                                self.__showname, self.show_bytes('', pan_id))
            xbee_ddo_cfg.add_parameter('ID', pan_id)

        if SettingsBase.get_setting(self, "robust_router"):
            # based on technology, do things to increase robustness
            if self.get_xbee_manager().is_zigbee():
                #     use AR/NW/JV to force router to seek/chase coordinator
                agg_rte = self.get_xbee_manager().xbee_device_ddo_get_param(None, 'AR')
                if agg_rte == 0:
                    self._tracer.warning('Gateway/Coordinator AR set to 0/disabled - not robust')
                # what is formula to match AR to NW?

                self._tracer.debug('%s: Forcing Robust Router settings: JV, NW',
                                    self.__showname)
                xbee_ddo_cfg.add_parameter('NW', int(self.RXBEE_AR_NW_BASE))
                xbee_ddo_cfg.add_parameter('JV', 1)

            # for both ZB and DM
            xbee_ddo_cfg.add_parameter('NO', 0x01) # node options, append DD

        if SettingsBase.get_setting(self, "force_node_name"):
            # then send the xbee ID/name down
            #self._tracer.debug('%s: Forcing XNee Name to \"%s\"',
            #                        self.__showname, self.get_name())
            xbee_ddo_cfg.add_parameter('NI', self.get_name())

        if SettingsBase.get_setting(self, "enable_rotary_id"):
            # then enable the rotary inputs
            for pin in self.ROTARY:
                # enable our rotary pins as input/3
                xbee_ddo_cfg.add_parameter(pin, 3)

        else: # else delete the 'rotary_id' channel
			self.remove_one_property("node_id")

        if len(xbee_ddo_cfg) > 0:
            # Register configuration blocks with the XBee Device Manager:
            self.get_xbee_manager().xbee_device_config_block_add(self, xbee_ddo_cfg)

        return

    #def probe():

    def ddo_get_param(self, param):
        return self.get_xbee_manager().xbee_device_ddo_get_param(
                    self.__extended_address, param)

    def ddo_set_param(self, param, value):
        return self.get_xbee_manager().xbee_device_ddo_set_param(
                    self.__extended_address, param, value)

# internal functions & classes
    def running_indication(self):
        """\
            Dia will call this function when it has finished sending the
            preliminary DDO command blocks to the M300 device.
            At this point, the M300 is correctly configured at the XBee level
            to be able to accept data from us.
        """
        self._tracer.info("%s Configuration complete - device is now running",
                        self.__showname)

        if not self.__heartbeat_active and \
                        SettingsBase.get_setting(self, "enable_rotary_id"):
            # no heart-beat, so force a single read of IS/xbee DIO
            buf = self.ddo_get_param('IS')
            if (buf is not None) and (len(buf) > 2):
                self.refresh_rotary_id(buf)

        # Scheduling first request and watchdog:
        self.schedule_first_poll()
        self.restart_heartbeat_watchdog()
        return

    ## heart-beat routines
    def _heart_beat_indication(self, buf, addr):
        """\
        Dia calls this function when IS-like data arrives.
        """
        try:
            self._availability.signal_good_event()
            self.__bad_count = 0 # clear all

            # IS: 0x01 18 1c 00 08 1c
            if buf is None or (len(buf) < 6):
                self._tracer.error("%s Heart-Beat data is too short", self.__showname)
                return

            x = time.clock()
            if (x - self.__hb_info) > self.RXBEE_DEF_HEART_BEAT_INFO or \
               (x < self.__hb_info):
                # then trace as INFO, not DEBUG
                self.__hb_info = x
                self._tracer.info("%s Heart-Beat: %s",
                        self.__showname, self._availability.report_uptime() )
            else:
                self._tracer.debug("%s Heart-Beat: %s",
                        self.__showname, self._availability.report_uptime() )

            # save the digital mask and digital info - is LittleEndian
            self._digital_mask = (ord(buf[1]) * 256) + ord(buf[2])
            self._digital_data = (ord(buf[4]) * 256) + ord(buf[5])

            # handle the heart_beat timeout
            self.restart_heartbeat_watchdog()
            self._update_availability_channel()
            self._update_online(True)

            # allow derived classes to see the IR/IS data
            self.ir_is_sample_update(buf, addr)
        except:
            print traceback.format_exc()

        try:
            if SettingsBase.get_setting(self, "enable_rotary_id"):
            # then enable the rotary inputs
                self.refresh_rotary_id()
        except:
            print traceback.format_exc()


        try:
			# allow derived classes to see the IR/IS data
            self.ir_is_sample_update(buf, addr)
        except:
            print traceback.format_exc()

        return True

    def ir_is_sample_update(self, buf, addr):
        # may be over-riden by derived classes
        return

    def _heart_beat_timeout(self):
        self._availability.signal_bad_event()
        self.restart_heartbeat_watchdog()
        self._tracer.warning("%s Heart-Beat Missed!",
                    self.__showname)
        if self.__bad_count >= self.OFFLINE_AFTER_BAD:
            self._update_online(False)
        else: # else not bad/offline yet
            self.__bad_count += 1

        x = time.clock()
        if (x - self.__hb_info) > self.RXBEE_DEF_HEART_BEAT_INFO or \
           (x < self.__hb_info):
            # then trace as WARNING, not DEBUG
            self.__hb_info = x
            self._tracer.warning("%s Heart-Beat Missed: %s",
                    self.__showname, self._availability.report_uptime() )
        else:
            self._tracer.debug("%s Heart-Beat Missed: %s",
                    self.__showname, self._availability.report_uptime() )

        self._update_availability_channel()

        return

    def _update_online(self, status=False, force=False):
        # update online channel only if changed
        old = self.property_get(self.HB_STATUS_CHAN).value
        #self._tracer.debug("%s Node Online is %s, want %s",
        #                  self.__showname, old, status)
        if (old != status) or force:
            now = time.time()
            if status:
                self._tracer.info("%s Node going ONLINE at %s",
                               self.__showname, self.iso_date(now))
            else:
                self._tracer.info("%s Node going OFFLINE at %s",
                               self.__showname, self.iso_date(now))
            self.property_set(self.HB_STATUS_CHAN, Sample(now, status))
            # chain - allow child to overload
            self.go_online(status)

            # update the general device error channel by inverting,
            # online = not error, while not online = error
            self.set_xbee_error(not status)

        return

    def _update_availability_channel(self, force=False):
        # update online channel only if changed
        if self.RXBEE_DEF_AVAIL_CHAN is not None:
            # then we have a channel, so update

            new_val = self._availability.get_percentage()
            if self.RXBEE_AVAIL_DEADBAND > 0.0:
                # then see if enough change to update
                old_val = self.property_get(self.RXBEE_DEF_AVAIL_CHAN).value
                if (abs(old_val - new_val) < self.RXBEE_AVAIL_DEADBAND):
                    # no update yet
                    return

            #self._tracer.debug("%s Node Availability is %s, want %s",
            #                  self.__showname, old, status)

            self.property_set(self.RXBEE_DEF_AVAIL_CHAN, Sample(0, new_val, '%'))

        return

    def go_online(self, status=True):
        return

    def __cancel_hb_watchdog(self):
        """ Cancel any pending next_poll timer """
        try:
            if self.__hb_timer is not None:
                # then try to delete old one
                self.schedule_cancel(self.__hb_timer)
        except:
            self.__hb_timer = None
        return

    def restart_heartbeat_watchdog(self):
        """ Set the event callback for next poll """

        # heart_beat should be seconds
        rate = SettingsBase.get_setting(self, "heart_beat_sec")
        if rate == 0:
            self._tracer.debug('%s: Heart Beat Timeout is disabled', self.__showname)
            try:
                del self.__hb_timer
            except AttributeError: # it may NOT exist
                pass

        else:
            self.__cancel_hb_watchdog()
            rate += self.HEART_BEAT_ADDER
            # self._tracer.debug('Sched Next HeartBeat Timeout in %d sec', rate)
            self.__hb_timer = self.schedule_after(rate, self._heart_beat_timeout)
        return

    def refresh_rotary_id(self, buf=None):
        """\
        Read the 4 inputs of the rotary dial
        """

        # bit 1, pin 04,  DIO12 (P2)
        # bit 2, pin 07,  DIO11 (P1)
        # bit 3, pin 11,  DIO4  (D4)
        # bit 4, pin 17,  DIO3  (D3)

        try:
            old = self.property_get("node_id").value
        except:
            self._tracer.warning("%s Rotary Inputs are not configured",
                    self.__showname)
            # then no node_id property
            return

        # IS: 0x01181c00081c

        if buf is not None:
            # this is 1-shot refresh
            # save the digital mask and digital info - is LittleEndian
            self._digital_mask = (ord(buf[1]) * 256) + ord(buf[2])
            self._digital_data = (ord(buf[4]) * 256) + ord(buf[5])
        # else assume already broken out like this

        # confirm our bits are valid
        if (self._digital_mask & 0x1818) != 0x1818:
            # then at least 1 of our ROTARY bits is missing
            self._tracer.error("%s Rotary Inputs are not configured correctly", self.__showname)
            self.property_set("node_id", Sample(0, None))
            return

        nib = 0
        # get first 2 bits
        if self._digital_data & 0x1000:
            # print "then LSB/bit 1 is high"
            nib |= 0x01

        if self._digital_data & 0x0800:
            # print "then bit 2 is high"
            nib |= 0x02

        if self._digital_data & 0x0010:
            # print "then bit 3 is high"
            nib |= 0x04

        if self._digital_data & 0x0008:
            # print "then MSB/bit 4 is high"
            nib |= 0x08

        # invert since rotary pulls signals low so 0xF means 0, 0x0 means 15
        nib = (~nib) & 0x0F

        # update rotary id channel only if changed
        # self._tracer.debug("Rotary Input seen:%d previous:%d", nib, old)

        if old != nib:
            now = time.time()
            self._tracer.info("%s Rotary Input updated to be %d, at %s",
                                self.__showname, nib, self.iso_date(now))
            self.property_set("node_id", Sample(now, nib))

        if buf is not None:
            # since this is one-shot, remove the saved data
            del self._digital_mask
            del self._digital_data

        return
