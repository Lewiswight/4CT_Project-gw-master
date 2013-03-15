# Test the filter_sample
#
# must from from root, so this is file:
#  python devices\experimental\_test_filter_sample.py

# imports
import traceback
import types
import time

from string_file import *

class Sample(object):
    __slots__ = ["timestamp", "value", "unit"]

    def __init__(self, timestamp=0, value=0, unit=""):
        self.timestamp = timestamp
        self.value = value
        self.unit = unit

    def __repr__(self):
        try:
            return '<Sample: "%s" "%s" at "%s">' % (self.value, self.unit,
                                              iso_date(self.timestamp))
        except:
            return '<Sample: "%s" "%s" at "%s">' % (self.value, self.unit,
                                                      self.timestamp)

# internal functions & classes

# test routines follow!

def test_basic( chatty):
    print 'test filter_sample simple change',
    if chatty:
        print

    tsts = [
        ( 23.0, 0, True, 1),
        ( 23.0, 1, False, 0),
        ( 24.0, 1, True, 5),
        ]

    cac = string_flash_cache('ziggy')
    start = time.time()

    for tst in tsts:
        if chatty: print '\ntest (%s) ' % str(tst)
        val = tst[0]

        sam = Sample(timestamp=start, value=val)
        cac.append(str(sam), start, force_write=False)

    cac.save_to_flash()

    print '... Okay!'
    return True

def test_timed( chatty):
    print 'test filter_sample simple change',
    if chatty:
        print

    tsts = [
        ( 22.0, 0, True, 1),
        ( 33.0, 3, False, 0),
        ( 44.0, 6, True, 5),
        ( 55.0, 6, True, 5),
        ( 66.0, 11, True, 5),
        ]

    cac = string_flash_cache('ziggy')
    start = time.time()

    for tst in tsts:
        if chatty: print '\ntest (%s) ' % str(tst)
        val = tst[0]
        timofs = tst[1]

        sam = Sample(timestamp=start+timofs, value=val)
        cac.append(str(sam), start+timofs, force_write=False)

    cac.save_to_flash()
    print cac.attrib

    print '... Okay!'
    return True

def test_unlock( chatty):
    print 'test filter_sample simple change',
    if chatty:
        print

    tsts = [
        ( 22.0, 0, True, 1),
        ( 33.0, 3, False, 0),
        ( 44.0, 6, True, 5),
        ( 55.0, 6, True, 5),
        ( 66.0, 11, True, 5),
        ]

    cac = string_flash_cache('ziggy')
    start = time.time()

    for tst in tsts:
        if chatty: print '\ntest (%s) ' % str(tst)
        val = tst[0]
        timofs = tst[1]

        sam = Sample(timestamp=start+timofs, value=val)
        cac.append(str(sam), start+timofs, force_write=False)

    cac.save_to_flash()
    print cac.attrib

    data = cac.lock_cache()
    print 'data = ', data
    print
    cac.free_cache()

    print '... Okay!'
    return True

if __name__ == '__main__':

    test_all = False
    chatty = False

    if(False or test_all):
        test_basic(chatty)

    if(False or test_all):
        test_timed(chatty)

    if(True or test_all):
        test_unlock(chatty)
