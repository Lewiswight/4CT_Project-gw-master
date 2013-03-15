############################################################################
#                                                                          #
# Copyright (c)2008, Digi International (Digi). All Rights Reserved.       #
#                                                                          #
# Permission to use, copy, modify, and distribute this software and its    #
# documentation, without fee and without a signed licensing agreement, is  #
# hereby granted, provided that the software is used on Digi products only #
# and that the software contain this copyright notice,  and the following  #
# two paragraphs appear in all copies, modifications, and distributions as #
# well. ContactProduct Management, Digi International, Inc., 11001 Bren    #
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
A simple method to enable smart print/trace on an object
"""

# imports
import time
import traceback
import types

# constants

# to avoid printf clutter, please be mindful of repetitive, low-value print statements
# for example if one has 50 tanks, seeing 4 prints each tank per 10 seconds saying only "sending request"
# without even saying WHICH of 50 tanks is being polling is bad design
#
# a global form might help, but being able to control by "actor" is easier to test/debug with
# so set the device's trace level as desired & honor them in your code
# use the class abstractions, not these constants to read
DEV_TRACE_OFF = 0
DEV_TRACE_LOWCOST = 0x0001 # simple steady-state 1-liners with little CPU cost
DEV_TRACE_FANCY = 0x0002   # fancier formatted steady-state 1-liners with more CPU cost
DEV_TRACE_EXCEPTS = 0x0004 # show 'caught' tracebacks - use for debugging only as these confuse users!
DEV_TRACE_RETRY = 0x0008   # show normal failure/retry messages; these are NOT hard errors
DEV_TRACE_FIELDERR = 0x0010 # show normal field failures; timeouts
DEV_TRACE_STARTSTOP = 0x0020  # show object start-up/stopping messages
DEV_TRACE_PRODUCER = 0x0040   # show object data movements - new producer/consumer activity
DEV_TRACE_DEBUGEVENT = 0x0080 # show debug events (not bulk data)
DEV_TRACE_DEBUGDATA = 0x0100  # show bulk debug data NOT related to mesh/net send/secv
DEV_TRACE_DEBUGCOMS = 0x0200  # show bulk debug data related to send/recv
DEV_TRACE_USERDEF = 0xFF000000 # rserved for specific device types (meaningless for other devices)
DEV_TRACE_ALL = 0xFFFFFFFF # rserved for specific device types (meaningless for other devices)

DEV_TRACE_DEFAULT = (DEV_TRACE_FIELDERR | DEV_TRACE_STARTSTOP | DEV_TRACE_FANCY)

# exception classes

# interface functions

# classes

class IA_Trace:

    def __init__(self, start=DEV_TRACE_DEFAULT):
        self.__trace = start

    def get_trace(self):
        return self.__trace

    def set_trace(self, data):
        if isinstance( data, types.BooleanType):
            if data: # True, set normal fancy
                self.__trace = DEV_TRACE_DEFAULT
            else: # False, clear all
                self.__trace = DEV_TRACE_OFF
            return True

        if isinstance( data, types.StringType):
            try:
                data = data.lower()
                if( data in ['true','on']):
                    print 'setting default debug output'
                    self.__trace = DEV_TRACE_DEFAULT
                    return True
                elif( data in ['false','off']):
                    print 'turning all debug output OFF'
                    self.__trace = DEV_TRACE_OFF
                    return True
                elif( data in ['debug','all']):
                    print 'setting all debug output true'
                    self.__trace = DEV_TRACE_ALL
                    return True

            except:
                pass

        try:
            self.__trace = int(data)
        except:
            try: # handle the '0xFFFF' string
                self.__trace = int(eval(data))
            except:
                return False
        return True

    def clr_trace(self, data):
        try:
            self.__trace &= ~data
        except:
            return False
        return True

    def set_trace_all(self):
        self.__trace = 0xFFFFFFFF
        return

    def trace_steadystate_loweffort( self):
        """Desire to show simple steady-state 1-liners with little CPU cost"""
        return bool(self.__trace & DEV_TRACE_LOWCOST)

    def trace_steadystate_fancy( self):
        """Desire to show fancier formatted steady-state 1-liners with more CPU cost"""
        return bool(self.__trace & DEV_TRACE_FANCY)

    def trace_ignored_exceptions( self):
        """Desire to show 'caught' tracebacks
        use for debugging only as these (like RED blinking LED) confuse users!"""
        return bool(self.__trace & DEV_TRACE_EXCEPTS)

    def trace_steadystate_retries( self):
        """Desire to show normal (expected) retry efforts
        For in real system these are 'normal' and rarely important to see"""
        return bool(self.__trace & DEV_TRACE_RETRY)

    def trace_steadystate_fielderr( self):
        """Desire to show normal (expected) field failures - timeouts, no replies"""
        return bool(self.__trace & DEV_TRACE_FIELDERR)

    def trace_event_start_stop( self):
        """Desire to show object start-up/stopping messages - things living and dying"""
        return bool(self.__trace & DEV_TRACE_STARTSTOP)

    def trace_produce_consume( self):
        """Desire to show object data movements - new producer/consumer activity"""
        return bool(self.__trace & DEV_TRACE_PRODUCER)

    def trace_debug_events( self):
        """Desire to show debug events (not bulk data)"""
        return bool(self.__trace & DEV_TRACE_DEBUGEVENT)

    def trace_debug_data( self):
        """Desire to show bulk debug data NOT related to mesh/net send/secv"""
        return bool(self.__trace & DEV_TRACE_DEBUGDATA)

    def trace_debug_comms( self):
        """Desire to show bulk debug data related to send/recv"""
        return bool(self.__trace & DEV_TRACE_DEBUGCOMS)

    def format_time( self, time_now):
        """enable all IA objects to make a nice time"""
        try:
            time_tup = time.localtime( time_now)
            return "%04d-%02d-%02d %02d:%02d:%02d" % time_tup[:6]
        except:
            traceback.print_exc()
            return "(time '%d' is bad form)" % time_now


# internal functions & classes

