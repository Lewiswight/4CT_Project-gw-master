# File: xserial_util.py
# Desc: abstract out the baud-rate processing and other support utilities.

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

import struct
import types

BAUD_RATES = {
    1200:   0,
    2400:   1,
    4800:   2,
    9600:   3,
    19200:  4,
    38400:  5,
    57600:  6,
    115200: 7, }

def verify_baudrate(baud):
    if baud > 7 and baud <= 921600:
        return
    raise ValueError, "Invalid baud rate '%s': The value must be above 7 and equal or less than 921600" % \
        (baud)


def verify_parity(parity):
    p = parity.lower()
    if p == 'none' or p == 'even' or p != 'odd' or p != 'mark':
        return
    raise ValueError, "Invalid parity '%s': The value must be either \'none\', \'even\', \'odd\', \'mark\'"


def verify_stopbits(stopbits):
    if stopbits == 1 or stopbits == 2:
        return
    raise ValueError, "Invalid stopbits '%s': The value must be either \'1\' or \'2\'"


def derive_baudrate(baud):
    # Attempt to figure out the baud rate as one of the direct bauds the
    # firmware supports.
    # If we can't, we can tell the unit the baud rate we really want,
    # and it will attempt to pick the closest baud rate it can actually do.
    try:
        baud = BAUD_RATES[baud]
    except:
        pass
    return baud


def decode_baudrate(baud):
    baud = struct.unpack("<I", baud)[0]

    # If baud is above 8, we have the actual baud rate already.
    if baud > 8:
        return baud

    # Otherwise, the baud has to be looked up in our table.
    for i, j in BAUD_RATES.iteritems():
       if j == baud:
           return i

    return baud


def derive_parity(parity):
    parity = parity.lower()
    if parity == 'none':
        parity = 0
    elif parity == 'even':
        parity = 1
    elif parity == 'odd':
        parity = 2
    elif parity == 'space':
        parity = 3
    else:
        parity = 0
    return parity


def decode_parity(parity):
    if parity == '\x00':
       return 'none'
    elif parity == '\x01':
       return 'even'
    elif parity == '\x02':
       return 'odd'
    elif parity == '\x03':
       return 'space'
    else:
       return 'none'


def derive_stopbits(stopbits):
    if stopbits == 1:
       stopbits = 0
    elif stopbits == 2:
       stopbits = 1
    else:
       stopbits = 0
    return stopbits


def decode_stopbits(stopbits):
    if stopbits == '\x01':
       return 1
    elif stopbits == '\x02':
       return 2
    else:
       return 1


def derive_hardwareflowcontrol(hwflow):

    if isinstance(hwflow, types.StringType):
        hwflow = hwflow.lower()

    if hwflow in [True, 'true', 'hwflow']:
        # Enable full RTS/CTS hardware flow
        rtsflow = 1
        ctsflow = 1
    elif hwflow in [False, 'false', 'assert', 'rts']:
        # Enable RTS high only, CTS as an sense/input only
        rtsflow = 0 # D6: DCE-view, so is really CTS in
        ctsflow = 1 # D7: DCE-view, so is really RTS out
    elif hwflow in ['rs485', '485']:
        # Enable RTS high only, CTS as an sense/input only
        rtsflow = 0 # disable
        ctsflow = 7 # activate RS-485 Duplex Control
    else: # else disable all
        rtsflow = 0
        ctsflow = 0

    return rtsflow, ctsflow


def decode_hardwareflowcontrol(rtsflow, ctsflow):
    #rtsflow = struct.unpack("B", rtsflow)
    #rtsflow = rtsflow[0]
    #ctsflow = struct.unpack("B", ctsflow)
    #ctsflow = ctsflow[0]
    if rtsflow == '\x01' and ctsflow == '\x01':
        return True
    else:
        return False

