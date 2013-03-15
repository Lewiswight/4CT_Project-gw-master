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

class Availability(object):

    def __init__(self):
        self.reset()
        return

    def __repr__(self):
        return self.report_availability()

    def get_availability(self):
        if self.__event_good == 0:
            return 0.0
        else:
            return float(self.__event_good) / float(self.__event_bad + self.__event_good)

    def get_percentage(self):
        return self.get_availability() * 100.0

    def get_event_count_bad(self):
        return self.__event_bad

    def get_event_count_good(self):
        return self.__event_good

    def get_event_count_total(self):
        return self.__event_bad + self.__event_good

    def reset(self):
        self.__event_bad = 0L
        self.__event_good = 0L
        self.__last_event_good = False
        self.__timestamp = time.time()
        return

    def signal_bad_event(self):
        self.__event_bad += 1
        self.__last_event_good = False
        return

    def signal_good_event(self):
        self.__event_good += 1
        self.__last_event_good = True
        return

    def report_availability(self):
        return 'Availability: %0.1f%%' % self.get_percentage()

    def report_availability_xml_compact(self):
        return 'availability="%0.1f%"' % self.get_percentage()

    def report_availability_xml_full(self):
        return '<availability>%0.1f%</availability>' % self.get_percentage()

    def report_uptime(self):
        if(self.__last_event_good):
            last = ''
        else:
            last = '(Last Event Bad!)'
        delta = int(time.time() - self.__timestamp)
        if delta < 3600:
            return '%s over time of %d min %s' % \
                    (self.report_availability(),
                    int(time.time() - self.__timestamp) / 60, last)
        else:
            return '%s over time of %0.1fhr %s' % \
                    (self.report_availability(),
                    int(time.time() - self.__timestamp) / 3600.0, last)
