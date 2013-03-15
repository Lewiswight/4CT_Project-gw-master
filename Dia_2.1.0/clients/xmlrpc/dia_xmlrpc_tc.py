#!/usr/bin/python

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


import sys
import cmd
import xmlrpclib
import re
import time
import shlex

sys.path.insert(0, "./lib")

from format_channels import dump_channel_dict_as_text, iso_date
from sample import Sample


#from format_channels import dump_channel_dict_as_text, iso_date
#from sample import Sample


class DiaCmd(cmd.Cmd):
    def __init__(self, xmlrpc_server):
        self.prompt = '=>> '
        self.intro = \
            'Welcome to the iDigi Device Integration Application XMLRPC CLI.'
        cmd.Cmd.__init__(self)

        self.__server = xmlrpc_server

    def __parse_args(self, arg):
        return shlex.split(arg)

    def __print_list(self, list_obj, sort=False):
        if sort:
            list_obj.sort()

        for obj in list_obj:
            print obj

    ## cmd.Cmd Hooks:
    def emptyline(self):
        """Do nothing on an empty line."""
        pass
   
    def do_channel_dump(self, arg):
        args = self.__parse_args(arg)
        startswith = ""
        if len(args):
            startswith = args[0]
        
        channel_dict = self.__server.channel_dump(startswith)
        for channel_name in channel_dict:
            sample_dict = channel_dict[channel_name]
            new_sample = Sample()
            for key in sample_dict:
                try:
                    setattr(new_sample, key, sample_dict[key])
                except:
                    pass
            channel_dict[channel_name] = new_sample
                        
        print dump_channel_dict_as_text(channel_dict, "")

    def do_channel_list(self, arg):
        args = self.__parse_args(arg)

        startswith = ""

        if len(args):
            startswith = args[0]

        self.__print_list(self.__server.channel_list(startswith), sort=True)

    def do_channel_get(self, arg):
        args = self.__parse_args(arg)

        if len(args) != 1:
            print "channel_get: must only be supplied with channel name."
            return 0

        channel_name = args[0]
        sample_dict = None
        try:
            sample_dict = self.__server.channel_get(channel_name)
        except Exception, e:
            print "channel_get: error fetching sample '%s'" % (str(e))
            return 0

        value_str = "(unprintable)"
        try:
            value_str = str(sample_dict["value"])
        except:
            pass

        print "\t%s: %s (%s) @ %s" % (
            channel_name, sample_dict["value"], sample_dict["unit"],
            iso_date(sample_dict["timestamp"]))

        return 0

    def do_channel_set(self, arg):
        """\
channel_set channel_name timestamp value [unit autotimestamp_bool]

timestamp must be given as in the ISO date format.
        """

        args = self.__parse_args(arg)

        if len(args) < 3 or len(args) > 5:
            print "channel_set: invalid argument(s) given."
            return 0

        channel_name = args[0]
        timestamp = args[1]
        value = args[2]
        unit = ""
        if len(args) > 3:
            unit = args[3]
        autotimestamp_str = ""
        if len(args) > 4:
            autotimestamp_str = args[4].lower()
        autotimestamp = False

        if autotimestamp_str == "t" or autotimestamp_str == "true" or \
            autotimestamp_str == "1" or autotimestamp_str == "y" or \
            autotimestamp_str == "yes" or timestamp == "0":
            autotimestamp = True

        if not autotimestamp:
            timestamp = time.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            timestamp = time.mktime(timestamp)
        else:
            timestamp = time.time()

        try:
            self.__server.channel_set(channel_name,
                                        timestamp, value, unit, autotimestamp)
        except Exception, e:
            print "channel_set: %s" % (str(e))
            return 0

        print "\t%s: %s (%s) @ %s (approx.)" % (
            channel_name, value, unit, iso_date(timestamp))

        return 0
        

    def do_device_instance_list(self, arg):
        self.__print_list(self.__server.device_instance_list(), sort=True)

    def do_channel_info(self, arg):
        args = self.__parse_args(arg)

        if len(args) != 1:
            print "channel_info: must only be supplied with channel name."
            return 0

        channel_name = args[0]
        return_dict = None
        try:
            return_dict = self.__server.channel_info(channel_name)
        except Exception, e:
            print "channel_info: error fetching channel information: '%s'" % (str(e))
            return 0

        print ""
        print "Channel Information:"
        print ""

        if return_dict is None:
            print "    Result is None"
            print ""
            return 0

        for sect in return_dict:
            print "    %s:" % sect.capitalize()
            for item in return_dict[sect]:
                if return_dict[sect][item]:
                    print "        * %s" % item
        print ""
        
        return 0

    def do_quit(self, arg):
        return -1

    def do_channel_refresh(self, arg):
        self.__server.channel_refresh(arg)

    def help_channel_refresh(self):
        print "syntax:channel_refresh channel_name"
        print "-- refreshes channel property value"

    ## Help:
    def help_quit(self):
        print "syntax: quit"
        print " -- terminates the application\r\n"

    def help_q(self):
        self.help_quit()

    # shortcuts
    do_q = do_quit

def usage():
    print "usage: %s host port" % sys.argv[0]

def print_list(node_list):
    for node in node_list:
	print node

def main():
    print "iDigi Dia XML-RPC Test Client"
    print "----------------------------"

    if len(sys.argv) < 2 or len(sys.argv) > 3:
	usage()
	sys.exit(-1)

    host = sys.argv[1]
    port = 80
    if len(sys.argv) == 3:
        port = int(sys.argv[2])

    url = "http://%s:%d" % (host,port)
    print "using url: %s" % (url)

    server = xmlrpclib.ServerProxy(url)
    cmd_line = DiaCmd(xmlrpc_server=server)
    cmd_line.cmdloop()


if __name__ == '__main__':
    import sys
    status = main()
    sys.exit(status)

