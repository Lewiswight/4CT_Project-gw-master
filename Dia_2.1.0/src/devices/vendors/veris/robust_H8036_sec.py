# File: robust_ecm.py
# Desc: receive data from the Brultech ECM1240, uploading as if SunSpec Meter Data

"""\
Use Modbus/TCP to query the Veris H8036 meter
"""

# imports
import struct
import traceback
import types

from settings.settings_base import SettingsBase, Setting
from samples.sample import *
from core.tracing import get_tracer
from channels.channel_source_device_property import *

from devices.vendors.robust.robust_base import RobustBase
from devices.vendors.veris.H8036_object import VerisH8036

# constants

# exception classes

# interface functions

# classes
class MBus_VerisH8036_secondary(RobustBase):


    # over-ride - disable all polling - brultech just sends to us
    RDB_DEF_POLL_RATE = 0

    ENB_CHN_DEFAULTS = ['phase', 'minmax', 'model']
    DEF_UNIT_ID = 1

    # Singletons for My-Gang logic
    _my_gang = []
    _next_gang_index = None
    
    def __init__(self, name, core_services, settings_in=None, property_in=None):

        self._my_tracer = get_tracer('MBusH8036(%s)' % name)

        ## Local State Variables:
        self._H8036 = VerisH8036()

        # init the My-Gang logic - chain multiple 
        self.init_gang()

        ## Settings Table Definition:
        settings_list = [
            # Setting( name='sample_rate_sec' is in Robust_Device

            Setting(
                name='channels', type=list, required=False,
                default_value=self.ENB_CHN_DEFAULTS),

            Setting(
                name='unit_id', type=int, required=False,
                default_value=self.DEF_UNIT_ID),
        ]

        settings_out = self._safely_merge_lists(settings_in, settings_list)

        ## Channel Properties Definition: assume ecm1240
        # property_list = [ ]

        # Add our property_list entries to the properties passed to us.
        # properties = self._safely_merge_lists(properties, property_list)
        property_out = property_in

        ## Initialize the DeviceBase interface:
        RobustBase.__init__(self, name, core_services, settings_out, property_out)
        return

    ## Functions which must be implemented to conform to the DeviceBase
    ## interface:

    def start(self):
        """Start the device driver.  Returns bool."""

        RobustBase.start_pre(self)

        # copy the Modbus Unit ID (slave id) to our Veris H8036 object
        x = SettingsBase.get_setting(self, "unit_id")
        self._my_tracer.debug("Setting Modbus Unit-ID:%d ", x)
        self._H8036.set_ModbusAddress(x)
        
        # create the Dia channels
        x = SettingsBase.get_setting(self, "channels")
        self._my_tracer.debug("Setting H8036 Mode:%s ", x)
        self._H8036.enable_channels(x)

        nam_list = self._H8036.get_channel_name_list()

        for nam in nam_list:
            self._my_tracer.debug("Adding Channel:%s ", nam)
            self.add_property(
                ChannelSourceDeviceProperty(name=nam,
                    type=float, initial=Sample(0, 0.0, 'not init'),
                    perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP))

        RobustBase.start_post(self)

        return True

    def stop(self):
        """Stop the device driver.  Returns bool."""
        RobustBase.stop(self)
        return True

    ## Locally defined functions:
    def next_poll(self, trns_id=0):
        self._my_tracer.debug("Next Poll Sec #%d", trns_id)
        self.cancel_response_timeout()
        return

    def parse_response(self, data):
        rtn = self._H8036.import_binary(data)
        print rtn
        lst = self._H8036.report_SunSpec()
        for itm in lst: print itm
        return
    
#  class RobustGang(object):

	# derivered classes need to define these two as class data so all instances share them
    # _my_gang = []
    # _next_gang_index = None

	# the RobustGang will define this value for the use
    # self._my_gang_index

    def init_gang(self):

        # create the shared singletons, appending ourself onto the end
        self._my_gang_index = len(MBus_VerisH8036_secondary._my_gang)
        MBus_VerisH8036_secondary._my_gang.append(self)
        # RobustGang._my_gang.append(self)
        self._my_tracer.debug('driver count = %d, my index = %d',
            len(MBus_VerisH8036_secondary._my_gang), self._my_gang_index)

        self._next_gang_index = 0
        return

    def my_gang_index(self):
        '''Return my index within gang instance list
        '''
        return self._my_gang_index

    def incr_next_gang_index(self):
        '''Move to next peer in the gang
        '''
        if self._next_gang_index < (len(self._my_gang) - 1):
            # then more peers
            self._next_gang_index += 1
            self._my_tracer.debug('incr to next gang member = %d', self._next_gang_index)
            
        else:
            # no more, we are done iterating
            self._next_gang_index = 0
            self._my_tracer.debug('reset next gang member to 0/master')
            
        return self._next_gang_index

    def get_active_gang_index(self):
        '''Return my index within gang instance list
        '''
        return self._next_gang_index

    def get_gang_memeber(self, index=0):
        '''Return instance object which is Master
        '''
        try:
            return MBus_VerisH8036_secondary._my_gang[index]
        except:
            return None

    def active_gang_memeber(self):
        '''Return instance object which is 'Active'
        '''
        # self._my_tracer.debug('get ActiveMember(%d)', self._next_gang_index)
        return self._my_gang[self._next_gang_index]

    def previous_gang_memeber(self):
        '''Return instance object which was active previously
        '''
        #self._my_tracer.debug('get previous of ActiveMember(%d)', self._next_gang_index)
        # this works even if self._next_gang_index==0, since -1 is 'last in list'
        return self._my_gang[self._next_gang_index - 1]
        
        #if self._next_gang_index == 0:
        #    # then want the last one in the gang
        #    return self._my_gang[-1]
        #    
        #else:
        #    return self._my_gang[self._next_gang_index - 1]
        
    def get_gang_list(self):
        '''Return instance object which is Master
        '''
        return self._my_gang

    def get_gang_size(self):
        '''Return my index within driver list
        '''
        return len(self._my_gang)

    def gang_master(self):
        '''Return instance object which is Master
        '''
        return MBus_VerisH8036_secondary._my_gang[0]

    def i_am_gang_master(self):
        '''Return T/F is this is the master/resource controlling instance
        '''
        return self._my_gang_index == 0
