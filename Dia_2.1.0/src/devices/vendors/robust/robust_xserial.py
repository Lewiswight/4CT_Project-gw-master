# File: robust_xserial.py
# Desc: Add serial functions on top of base xbee driver

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

"""\
A Generic Dia XBee Serial Driver


To Use:
-------

This XBee Serial class is intended to be used by deriving a new class based
on this class.

This driver attempts to shield the user from the low level details
on how to set various serial settings that use cryptic AT commands.

The function calls that are intended to be used by the driver writer are:

* :py:func:`~XBeeSerial.initialize_xbee_serial`
* :py:func:`~XBeeSerial.write`
* :py:func:`~XBeeSerial.set_baudrate`
* :py:func:`~XBeeSerial.get_baudrate`
* :py:func:`~XBeeSerial.set_parity`
* :py:func:`~XBeeSerial.get_parity`
* :py:func:`~XBeeSerial.set_stopbits`
* :py:func:`~XBeeSerial.get_stopbits`
* :py:func:`~XBeeSerial.set_hardwareflowcontrol`
* :py:func:`~XBeeSerial.get_hardwareflowcontrol`

When deriving from this class, the user should be aware of 2 things:

1. During your 'start' function, you should declare a ddo config block,
   then pass that config block into the
   :py:func:`~XBeeSerial.initialize_xbee_serial` function.

   This class will add commands to your config block to set up the
   serial parameters.

   For example::

       xbee_ddo_cfg = self.get_ddo_block()
       XBeeSerial.initialize_xbee_serial(self, xbee_ddo_cfg)
       self.get_xbee_manager().xbee_device_config_block_add(self, xbee_ddo_cfg)

2. The user needs to declare a 'read_callback' function.
   Whenever serial data is received, this driver will forward this data
   to the derived class that has this function declared.


Settings:
---------

* **baudrate:** Optional parameter. Acceptable integer baud rates are from
  8 through 921600. If not set, the default value of 9600 will be used.
* **parity:** Optional parameter. Acceptable parity values are the follow
  strings:

    * none
    * even
    * odd
    * mark

    If not set, the default value of 'none' will be used.
* **stopbits:** Optional parameter. Acceptable stopbit values are:

    * 1
    * 2

    If not set, the default value of 1 will be used.

    .. Note::
        Not all XBee/ZigBee Serial firmware supports setting the stop bit
        value. In these cases, the stop bit will always be 1.

* **hardwareflowcontrol:** Optional parameter. Acceptable hardware flow
  control values are:

    * **True:** Will set RTS/CTS flow control.
    * **False:** Will turn OFF RTS/CTS flow control.

    If not set, the default value of False will be used.

"""

# imports
import struct
import traceback

from settings.settings_base import SettingsBase, Setting
from samples.sample import *
from channels.channel_source_device_property import *
from devices.xbee.xbee_device_manager.xbee_device_manager_event_specs \
    import *

try:
    from devices.xbee.common.prodid import PROD_ROBUSTMESH
    # if above was okay, import the entire thing as namespace
    import devices.xbee.common.prodid as prodid
except:
    # if the RobustMesh codes aren't in the std ProdId, import private one
    import devices.vendors.robust.prodid as prodid

# from devices.vendors.robust.robust_base import RobustBase
from devices.vendors.robust.robust_xbee import RobustXBee
import devices.vendors.robust.xserial_util as xserial_util

# constants

# exception classes

# interface functions

# classes
class RobustXSerial(RobustXBee):
    """\
    A Robust XBee Serial base class
    """

    # Define a set of endpoints that this device will send in on.
    ADDRESS_TABLE = [ [0xe8, 0xc105, 0x11], ]

    # The list of supported products that this driver supports.
    SUPPORTED_PRODUCTS = [
        prodid.PROD_DIGI_XB_ADAPTER_RS232,
        prodid.PROD_DIGI_XB_ADAPTER_RS485,
        prodid.PROD_ROBUSTMESH,
        prodid.PROD_ROBUSTMESH_232, prodid.PROD_ROBUSTMESH_485,
        ]

    # types for this driver
    # 'oem'  means do NOT make any changes in the XBee
    # 'auto' means try to use DD to determine type
    # '232'  means assume RS-232
    # '485'  means assume RS-485
    TYPE_VALUES = ['oem', 'auto', '232', '485', ]

    XSER_DEFAULT_TYPE = 'auto'
    XSER_DEFAULT_BAUD = 9600
    XSER_DEFAULT_PARITY = 'none'
    XSER_DEFAULT_STOP_BITS = 1
    XSER_DEFAULT_HWFLOW = 'assert'

    XSER_DEFAULT_ENDPOINT = 0xE8

    # manage debug trace - allow derived classes to over-ride
    XSER_IS_ASCII = False
    XSER_STRING_CRNL = True # applies to ASCII only
    XSER_SHOW_BYTES = True

    def __init__(self, name, core_services, settings=None, properties=None):

        ## Local State Variables
        self.__showname = 'RbXSer(%s)' % name
        self.__xbee_init = False

        ## Settings Table Definition:
        settings_list = [
            Setting(
                name='type', type=str, required=False,
                default_value=self.XSER_DEFAULT_TYPE,
                verify_function=self.__verify_type),

            Setting(
                name='baudrate', type=int, required=False,
                default_value=self.XSER_DEFAULT_BAUD,
                verify_function=xserial_util.verify_baudrate),
            Setting(
                name='parity', type=str, required=False,
                default_value=self.XSER_DEFAULT_PARITY,
                verify_function=xserial_util.verify_parity),
            Setting(
                name='stopbits', type=int, required=False,
                default_value=self.XSER_DEFAULT_STOP_BITS,
                verify_function=xserial_util.verify_stopbits),
            Setting(
                name='hardwareflowcontrol', type=str, required=False,
                default_value=self.XSER_DEFAULT_HWFLOW),
            # incoming end-point
            Setting(
                name='endpoint', type=int, required=False,
                default_value=self.XSER_DEFAULT_ENDPOINT,
                verify_function=lambda x: 0x00 <= x <= 0xFF),
        ]

        # Add our settings_list entries to the settings passed to us.
        settings = self._safely_merge_lists(settings, settings_list)

        ## Channel Properties Definition:
        # property_list = None

        # Add our property_list entries to the properties passed to us.
        # (we have none to add)
        # properties = self._safely_merge_lists(properties, property_list)

        ## Initialize the XBeeBase interface:
        RobustXBee.__init__(self, name, core_services, settings,
                          properties)

        # rename our tracer
        self._tracer.name = self.__showname

        return

    ## Functions which must be implemented to conform to the XBeeSerial
    ## interface:

    def read_callback(self):
        raise NotImplementedError, "virtual function"


    ## Functions which must be implemented to conform to the XBeeBase
    ## interface:

    ## Functions which must be implemented to conform to the DeviceBase
    ## interface:

    def start(self):
        """Start the device driver.  Returns bool."""

        # confirm the incoming end-point
        endpoint = SettingsBase.get_setting(self, "endpoint")
        if endpoint != 0xE8:
            self._tracer.debug("Incoming serial EndPoint changed to 0x%02d",
                            endpoint)
        self.ADDRESS_TABLE = [ [endpoint, 0xc105, 0x11], ]
        return RobustXBee.start(self)

    def start_pre(self):
        self._tracer.debug("RobustXSerial:Start_Pre")
        rtn = RobustXBee.start_pre(self)
        return rtn

    def start_post(self):
        if not self.__xbee_init:
            # derived class may have classed for some specific reason
            self.initialize_xbee_serial()

        self._tracer.debug("RobustXSerial:Start_Post")
        return RobustXBee.start_post(self)

    def stop(self):
        """Stop the device driver.  Returns bool."""
        return RobustXBee.stop(self)

    ## Locally defined functions:

    def initialize_xbee_serial(self, param=None):
        """\
        Creates a DDO command sequence of the user selected serial settings. Forces an
        adapter to enable support for battery-monitor pin, too. It is only enabled if
        adapter is using internal batteries.

        .. Note::
            * During your 'start' function, you should declare a ddo config block,
              then pass that config block into this function.
            * This function will add commands to your config block to set up the
              serial parameters and to enable support for battery-monitor pin if only
              adapter is using internal batteries.

        Returns True if successful, False on failure.
        """

        if self.__xbee_init:
            self._tracer.error("duplicate call to RobustXSerial.initialize_xbee_serial")
            return

        self.__xbee_init = True

        self._tracer.debug("RobustXSerial.initialize_xbee_serial called")

        # RobustXBee.initialize_robust_xbee(self)

        # Create a DDO configuration block for this device:
        xbee_ddo_cfg = self.get_ddo_block()

        # Create a callback specification for our device address, endpoint
        # Digi XBee profile and sample cluster id:
        self.get_xbee_manager().register_serial_listener(self,
                self.get_extended_address(), self._read_callback)


        # Get the product type  ['oem', 'auto', '232', '485', ]
        dev_type = SettingsBase.get_setting(self, "type")

        if dev_type == 'oem':
            self._tracer.debug("Adapter is OEM - skip all XBee changes")

        else:

            # Set up the baud rate for the device.
            try:
                baud = SettingsBase.get_setting(self, "baudrate")
            except:
                baud = 9600
            baud = xserial_util.derive_baudrate(baud)
            xbee_ddo_cfg.add_parameter('BD', baud)

            # Set up the parity for the device.
            try:
                parity = SettingsBase.get_setting(self, "parity")
            except:
                parity = 'none'
            parity =  xserial_util.derive_parity(parity)
            xbee_ddo_cfg.add_parameter('NB', parity)

            # Set up the stop bits for the device.
            if self.get_xbee_manager().is_zigbee():
                # only valid for Zigbee?
                try:
                    stopbits = SettingsBase.get_setting(self, "stopbits")
                except:
                    stopbits = 1
                stopbits = xserial_util.derive_stopbits(stopbits)
                # The SB command is new.
                # It may or may not be supported on the XBee Serial Device/Adapter.
                # If its not supported, then we know the device
                # is simply at 1 stop bit, and we can ignore the failure.
                xbee_ddo_cfg.add_parameter('SB', stopbits,
                                           failure_callback=self.__ignore_if_fail)
            # else skip SB, DigiMesh doesn't support

            if dev_type == '485':
                # RS-485 requires D7 set to 7
                xbee_ddo_cfg.add_parameter('D6', 0)
                xbee_ddo_cfg.add_parameter('D7', 7)

            else:
                # Set up the hardware flow control mode for the device.
                try:
                    hwflow = SettingsBase.get_setting(self, "hardwareflowcontrol")
                except:
                    hwflow = False
                rtsflow, ctsflow = xserial_util.derive_hardwareflowcontrol(hwflow)
                xbee_ddo_cfg.add_parameter('D6', rtsflow)
                xbee_ddo_cfg.add_parameter('D7', ctsflow)

        # Register configuration blocks with the XBee Device Manager:
        if len(xbee_ddo_cfg) > 0:
            self.get_xbee_manager().xbee_device_config_block_add(self, xbee_ddo_cfg)

        return True

    def write(self, data):
        """\
        Writes a buffer of data out the XBee.

        Returns True if successful, False on failure.
        """
        if self.XSER_SHOW_BYTES and self._tracer.debug():
            # only show bytes if derived class doesn't want this suppressed
            if self.XSER_IS_ASCII:
                if self.XSER_STRING_CRNL:
                    self._tracer.debug('send:%s', data.rstrip('\r\n'))
                else:
                    self._tracer.debug('send:%s', data)
            else:
                self._tracer.debug('%s', self.show_bytes("Send", data))

        try:
            addr = (self.get_extended_address(), 0xe8, 0xc105, 0x11)
            self.get_xbee_manager().xbee_device_xmit(0xe8, data, addr)
            ret = True
        except:
            ret = False
            pass
        return ret

    def set_baudrate(self, baud):
        """\
        Sets the baud rate.

        .. Note::
            * Acceptable values are 8 through 921600.
            * Direct values are the following:

                * 1200
                * 2400
                * 4800
                * 9600
                * 19200
                * 38400
                * 57600
                * 115200
            * If a baud rate is specified that is NOT in the above list,
              the XBee firmware will pick the closest baud rate that it
              is able to support.
            * A call to get_baudrate() will allow the caller to determine
              the real value the firmware was able to support.

        Returns True if successful, False on failure.
        """

        if SettingsBase.get_setting(self, "type") == 'oem':
            self._tracer.warning("Adapter Type is OEM - skipping set_baudrate()")

        else: # only set if adapter type is NOT OEM

            try:
                self.ddo_set_param('BD', xserial_util.derive_baudrate(baud))
            except:
                self._tracer.error(traceback.format_exc())
                return False

        return True

    def get_baudrate(self):
        """\
        Returns the baud rate the device is currently set to, 0 on failure.
        """

        try:
            baud = xserial_util.decode_baudrate(self.ddo_get_param('BD'))
        except:
            self._tracer.error("Failed to retrieve baudrate from device.")
            baud = 0
        return baud

    def set_parity(self, parity):
        """\
        Sets the parity.

        .. Note::
            Acceptable parity values are:
            * none
            * even
            * odd
            * mark

        Returns True if successful, False on failure.
        """

        if SettingsBase.get_setting(self, "type") == 'oem':
            self._tracer.warning("Adapter Type is OEM - skipping set_parity()")

        else: # only set if adapter type is NOT OEM

            try:
                self.ddo_set_param('NB', xserial_util.derive_parity(parity))
            except:
                self._tracer.error(traceback.format_exc())
                return False

        return True

    def get_parity(self):
        """\
        Returns the parity value the device is currently set to.
        """

        try:
            par = xserial_util.decode_parity(self.ddo_get_param('NB'))
        except:
            self._tracer.error(traceback.format_exc())
            self._tracer.error("Failed to retrieve parity value from device.")
            par = 'none'
        return par

    def set_stopbits(self, stopbits):
        """\
        Sets the number of stop bits.

        .. Note::
            * Acceptable parity values are 1 or 2.
            * The SB command is new.
            * It may or may not be supported on the XBee Serial Device/Adapter.
            * If its not supported, then we know the device is simply at
              1 stop bit, and we can ignore the failure.

        Returns  True if successful, False on failure.
        """

        if SettingsBase.get_setting(self, "type") == 'oem':
            self._tracer.debug("Adapter Type is OEM - skipping set_stopbits()")

        else: # only set if adapter type is NOT OEM

            try:
                self.ddo_set_param('SB',
                        xserial_util.derive_stopbits(stopbits))
            except:
                return False

        return True

    def get_stopbits(self):
        """\
        Returns the number of stop bits the device is currently set to.

        .. Note::
            * The SB command is new.
            * It may or may not be supported on the XBee Serial Device/Adapter.
            * If its not supported, then we know the device is simply at
              1 stop bit, and we can ignore the failure.

        Returns 1 or 2 on success, 1 on failure.
        """

        try:
            sb = xserial_util.decode_stopbits( self.ddo_get_param('SB'))
        except:
            self._tracer.error("Failed to retrieve stopbits "+
                                "value from device.")
            sb = 1
        return sb

    def set_hardwareflowcontrol(self, hwflow):
        """\
        Sets whether hardware flow control (RTS and CTS) should be set.

        .. Note::
            Acceptable hardware flow values are:
            * True
            * False

        Returns True if successful, False on failure.
        """

        # Get the product type  ['oem', 'auto', '232', '485', ]
        dev_type = SettingsBase.get_setting(self, "type")

        if dev_type != '232':
            self._tracer.warning(
                "Adapter Type is '%s' - skipping set_hardwareflowcontrol()",
                dev_type)

        else:
        # if dev_type == '232':
            # only set flow_control if adapter type is 232

            rtsflow, ctsflow = xserial_util.derive_hardwareflowcontrol(hwflow)
            try:
                self.ddo_set_param('D6', rtsflow)
            except:
                return False

            try:
                self.ddo_set_param('D7', ctsflow)
            except:
                return False

        return True

    def get_hardwareflowcontrol(self):
        """\
        Returns whether the device is currently set to do hardware flow
        control, False on failure
        """

        try:
            rts = self.ddo_get_param('D6')
            cts = self.ddo_get_param('D7')
            hwflow = xserial_util.decode_hardwareflowcontrol(rts, cts)
        except:
            self._tracer.error("Failed to retrieve hardware flowcontrol " +
                                "value from device.")
            hwflow = False
        return hwflow


    # Internal class functions - Not to be used outside of this class.

    def __verify_type(self, new_type):
        if new_type in self.TYPE_VALUES:
            return
        raise ValueError, "Invalid type '%s': The value must be in %s" % \
            (new_type, self.TYPE_VALUES)


    def _read_callback(self, buf, addr):
        if self.XSER_SHOW_BYTES and self._tracer.debug():
            # only show bytes if derived class doesn't want this suppressed
            if self.XSER_IS_ASCII:
                if self.XSER_STRING_CRNL:
                    self._tracer.debug('recv:%s', buf.rstrip('\r\n'))
                else:
                    self._tracer.debug('recv:%s', buf)
            else:
                self._tracer.debug('%s', self.show_bytes("Recv", buf))
        try:
            self.read_callback(buf, addr)
        except:
            self._tracer.debug(traceback.print_exc())

        return

    def __ignore_if_fail(self, mnemonic, value):
        return True



# internal functions & classes

