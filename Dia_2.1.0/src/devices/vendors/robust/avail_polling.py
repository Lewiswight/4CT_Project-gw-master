'''
Created on Aug 9, 2011

@author: Lynn
'''

# Maintain availability stats, which is done by counting good and bad
# 'access' events - for example successful or failed reads
#
# Primary goal is to return a value such as 0.0% for no availability
# or 1.0 (for 100%) for perfect availability.

import time

from devices.vendors.robust.avail_base import Availability
from devices.vendors.robust.minmaxavg import MinMaxAvg

class Polling_Stats(Availability):

    STAT_GOOD = 0
    STAT_TIMEOUT = 1
    STAT_BAD_RSP_FORM = 2
    STAT_ERROR_RSP = 3

    STAT_NAMES = ['good', 'timeout', 'bad_form', 'error_rsp']

    def __init__(self):
        Availability.__init__(self)
        self.reset()
        self.__stats = MinMaxAvg()
        self._poll_starttime = 0
        return


    def reset(self):
        Availability.reset(self)
        # to keep availability meaningful, any response (even bad) is 'okay'
        # self.__event_bad = overload as any error response
        # self.__event_good = overload as good response
        self.__rsp_tout = 0L
        self.__rsp_bad = 0L
        self.__rsp_error = 0L
        return

    def signal_request_sent(self):
        self._poll_starttime = time.clock()
        return

    def signal_reponse_good(self):
        self.__event_good += 1
        self.__last_event_good = True
        return

    def signal_reponse_timeout(self):
        self.__rsp_tout += 1
        self.__event_bad += 1
        self.__last_event_good = False
        return

    def signal_reponse_bad_format(self):
        self.__rsp_bad += 1
        self.__event_bad += 1
        self.__last_event_good = False
        return

    def signal_reponse_error(self):
        self.__rsp_error += 1
        self.__event_bad += 1
        self.__last_event_good = False
        return


    # def report_availability(self):
    # def report_availability_xml_compact(self):
    # def report_availability_xml_full(self):
    # def report_uptime(self):
