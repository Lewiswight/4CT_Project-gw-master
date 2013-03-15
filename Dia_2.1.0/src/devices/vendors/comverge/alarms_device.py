############################################################################
#                                                                          #
# Copyright (c)2008, 2009, Digi International (Digi). All Rights Reserved. #
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
Driver implementing channel subscription and transforms.
"""

# imports
from devices.device_base import DeviceBase
from settings.settings_base import SettingsBase, Setting
from channels.channel_source_device_property import *
from channels.channel_manager import ChannelManager
import sys
import traceback
from pprint import pformat

# constants

# exception classes
class TransformInitError(Exception):
    pass


# interface functions

# classes

class Transform:
    #TODO: A transform should probably bind to the settings tree so
    #that we can let the settings code do some of the validation for
    #us.
    def __init__(self, parent, core_services, **kw):
        self.__parent = parent
        self.__core = core_services
        self.__name = kw['name']
        try:
            self.__unit = kw['unit']
        except:
            self.__unit = ""
        try:
            channels = kw['channels']
        except:
            raise TransformInitError("Missing required transform setting channels")
        try:
            self.on_expr = kw['on_expr']
        except:
            raise TransformInitError("Missing required transform setting on_expr")
        try:
            self.off_expr = kw['off_expr']
        except:
            raise TransformInitError("Missing required transform setting off_expr")

        cm = self.__core.get_service("channel_manager")
        cdb = cm.channel_database_get()

        self.__channel_names = []
        for chan in channels:
            try:
                parent.cdb.channel_get(chan)
            except:
                print "Transform(%s): WARNING: channel '%s' does not exist yet." % \
                    (self.__name, chan)
            self.__channel_names.append(chan)

        # subscribe to all the channels that drive our logic
        cp = cm.channel_publisher_get()
        for channel_name in self.__channel_names:
            #TODO: Might it be a good idea to have a worker thread to
            #queue transform updates to rather than directly in the
            #callback from each channels update function?
            cp.subscribe(channel_name, self.update)

        # try to create the device property with the proper type
        try:
            self.__create_property()
        except:
            print >> sys.stderr, \
                "Transform(%s): WARNING: failed to create property, will retry on update" \
                % self.__name
            exc = sys.exc_info()
            print >> sys.stderr, \
                "".join(traceback.format_exception_only(exc[0], exc[1]))


    def __create_property(self):
        val = self.eval()[0]

        # create the channel that this will service
        self.__parent.add_property(
            ChannelSourceDeviceProperty(
                name=self.__name, type=type(val),
                initial=Sample(timestamp=0, value=val, unit=self.__unit),
                perms_mask=DPROP_PERM_GET, options=DPROP_OPT_AUTOTIMESTAMP)
            )


    def eval(self):
        # Compute initial value of channel, also gives us the type
        cdb = self.__parent.cdb
        c = []
        try:
            for channel_name in self.__channel_names:
                chan = cdb.channel_get(channel_name)
                val = chan.get().value
                c.append(val)
        except:
            raise ValueError, \
                "Transform(%s): WARNING: failed to perform get on all channels" \
                % self.__name


        eval_ns = { }
        eval_ns.update(globals())
        eval_ns["c"] = c
        try:
            on_value = eval(self.on_expr, eval_ns)
        except:
            exc = sys.exc_info()
            raise ValueError, \
                "Transform(%s): ERROR: failed to evaluate expression:\n%s" \
                % (self.__name,
                    "".join(traceback.format_exception_only(exc[0], exc[1])))
        try:
            off_value = eval(self.off_expr, eval_ns)
        except:
            exc = sys.exc_info()
            raise ValueError, \
                "Transform(%s): ERROR: failed to evaluate expression:\n%s" \
                % (self.__name,
                    "".join(traceback.format_exception_only(exc[0], exc[1])))

        return (on_value, off_value)

    def update(self, channel):
        if not self.__parent.property_exists(self.__name):
            try:
                self.__create_property()
            except:
                print >> sys.stderr, \
                    "Transform(%s): WARNING: cannot update property, it may not exist yet" \
                    % self.__name
                return

        val = self.eval()
        #custom hysterisis handler
        if val[0] and not val[1]:  #alarm trigger condition
            new_sample = Sample(value=True, unit=self.__unit)
        elif not val[0] and val[1]:  #clear alarm condition
            new_sample = Sample(value=False, unit=self.__unit)
        else:  #in undefined hysterisis state
            old_sample = self.__parent.property_get(self.__name)
            new_sample = Sample(value=old_sample.value, unit=self.__unit)
        #print "updating channel",self.__name," to",new_sample.value
        self.__parent.property_set(self.__name, new_sample)

class AlarmsDevice(DeviceBase):
    def __init__(self, name, core_services):
        self.__name = name
        self.__core = core_services
        self.tlist = []

        cm = self.__core.get_service("channel_manager")
        self.cdb = cm.channel_database_get()

        ## Settings Table Definition:
        settings_list = [
            Setting(name='instance_list', type=list, required=True),
        ]

        ## Channel Properties Definition:
        ## Properties are added dynamically based on configured transforms
        property_list = []

        ## Initialize the Devicebase interface:
        DeviceBase.__init__(self, self.__name, self.__core,
                                settings_list, property_list)



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

        SettingsBase.commit_settings(self, accepted)

        return (accepted, rejected, not_found)

    def start(self):
        """Start the device driver.  Returns bool."""

        transforms = SettingsBase.get_setting(self, "instance_list")

        for t in transforms:

            try:
                self.tlist.append(Transform(self, self.__core, **t))
            except:
                print >> sys.stderr, "TransformsDevice(%s): error: %s" % \
                    (self.__name, sys.exc_info()[1])
                print >> sys.stderr, "TransformsDevice(%s): transform was %s" % \
                    (self.__name, pformat(t))

        return True

    def stop(self):
        """Stop the device driver.  Returns bool."""

        return True


    ## Locally defined functions:



# internal functions & classes

def main():
    pass

if __name__ == '__main__':
    import sys
    status = main()
    sys.exit(status)

