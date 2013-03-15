# process/create Modbus/PDU (core cmd) packets
#
import copy
import traceback

from pccc_util import *

def test_tns(chatty = False):
    print '\ntest pccc_util TNS routines',

    if chatty:
        print ''

    xdct = {}

    tns = getTNS(xdct)

    if not xdct.has_key('tns'):
        print 'error, tns key not properly added to xdct(%s)' % str(xdct)
        return

    if tns < TNS_MIN:
        print 'error, tns:%d returned is less than TNS_MIN:%d' % (tns,TNS_MIN)
        return

    if tns > TNS_MAX:
        print 'error, tns:%d returned is greater than TNS_MAX:%d' % (tns,TNS_MAX)
        return
    elif chatty:
        print '  tns initialized okay'

    xdct['tns'] = 100
    tns = getTNS(xdct)
    if tns != 100:
        print 'error, tns:%d returned is not as expected:100' % tns
        return

    tns = getNextTNS(xdct)
    if xdct['tns'] != 101:
        print 'error, tns:%d not properly incr as expected:101' % xdct['tns']
        return
    elif chatty:
        print '  next_tns incremented okay'

    tns = getNextTNS_str(xdct)
    if tns != '\x65\x00':
        print 'error, next_tns_str:%s returned is not as expected:"\x65\x00"' % show_bytes('',tns)
        return
    elif chatty:
        print '  next_tns_str was okay'

    xdct['tns'] = TNS_MAX
    tns = getNextTNS(xdct)
    if xdct['tns'] != TNS_MIN:
        print 'error, tns:%d failed to roll over as expected:%d' % (xdct['tns'],TNS_MIN)
        return
    elif chatty:
        print '  next_tns rolled-over okay'

    if chatty:
        'test pccc_util TNS routines',
    print '... Okay!'
    return

def test_element_parse(chatty = False):

    print '\ntest Element parsing pccc_util.getFileType()',

    if( chatty):
        print ''

    tsts = [
        ( None, None ),
        ( '', None ),
        ( 'A', None ),
        ( 12, None ),
        ( 'N', 'N' ),
        ( 'n', 'N' ),
        ( 'N7', 'N' ),
        ( 'N7:', None ),
        ( 'N7:0', 'N' ),
        ( 'N7:0.', None ),
        ( 'N7:10.0', 'N' ),
        ( 'B', 'B' ),
        ( 'b', 'B' ),
        ( 'B7', 'B' ),
        ( 'B7:', None ),
        ( 'B7:0', 'B' ),
        ( 'B7:0.', None ),
        ( 'B7:10.0', 'B' ),
        ( 'F', 'F' ),
        ( 'f', 'F' ),
        ( 'F7', 'F' ),
        ( 'F7:', None ),
        ( 'F7:0', 'F' ),
        ( 'F7:0.', None ),
        ( 'F7:10.0', 'F' ),
        ( 'S', None ),
        ( 's', None ),
        ( 'ST', 'ST' ),
        ( 'st', 'ST' ),
        ( 'ST7', 'ST' ),
        ( 'ST7:', None ),
        ( 'ST7:0', 'ST' ),
        ( 'ST7:0.', None ),
        ( 'ST7:10.0', 'ST' ),
        ]

    for tst in tsts:
        data = tst[0]
        expect = tst[1]

        if chatty:
            print 'tst=%s' % str(tst)

        rtn = getFileType(data)
        if expect != rtn:
            print 'error, (%s) returned NOT as expected (%s), tst=%s' % (rtn,expect,str(tst))
            return

    if( chatty):
        print 'finished Element parsing pccc_util.getFileType()',
    print '... Okay!'

    print '\ntest Element parsing pccc_util.getSlc5FileTypeCode()',

    if( chatty):
        print ''

    tsts = [
        ( None, None ),
        ( '', None ),
        ( 'A', None ),
        ( 12, None ),
        ( 'N', 0x89 ),
        ( 'B', 0x85 ),
        ( 'F', 0x8A ),
        ( 'ST', 0x8D ),
        ]

    for tst in tsts:
        data = tst[0]
        expect = tst[1]

        if chatty:
            print 'tst=%s' % str(tst)

        rtn = getSlc5FileTypeCode(data)
        if expect != rtn:
            print 'error, (%s) returned NOT as expected (%s), tst=%s' % (rtn,expect,str(tst))
            return

    if( chatty):
        print 'finished Element parsing pccc_util.getSlc5FileTypeCode()',

    print '... Okay!'

    msg_typ_size = { 'B' : 2, 'N' : 2, 'F' : 4, 'ST' : 84 }

    print '\ntest Element parsing pccc_util.getFileTypeSize()',

    if( chatty):
        print ''

    tsts = [
        ( None, None ),
        ( 'N', 2 ),
        ( 'B', 2 ),
        ( 'F', 4 ),
        ( 'ST', 84 ),
        ]

    for tst in tsts:
        data = tst[0]
        expect = tst[1]

        if chatty:
            print 'tst=%s' % str(tst)

        rtn = getFileTypeSize(data)
        if expect != rtn:
            print 'error, (%s) returned NOT as expected (%s), tst=%s' % (rtn,expect,str(tst))
            return

    if( chatty):
        print 'finished Element parsing pccc_util.getFileTypeSize()',

    print '... Okay!'

    print '\ntest Element parsing pccc_util.getFileNumber()',

    if( chatty):
        print ''

    tsts = [
        ( None, None ),
        ( '', None ),
        ( 'A', None ),
        ( 12, 12 ),
        ( 'N', None ),
        ( 'n', None ),
        ( 'N7', 7 ),
        ( 'N7:', None ),
        ( 'N7:0', 7 ),
        ( 'N7:0.', None ),
        ( 'N7:10.0', 7 ),
        ( 'B', None ),
        ( 'b', None ),
        ( 'B3', 3 ),
        ( 'B3:', None ),
        ( 'B3:0', 3 ),
        ( 'B3:0.', None ),
        ( 'B3:10.0', 3 ),
        ( 'F', None ),
        ( 'f', None ),
        ( 'F9', 9 ),
        ( 'F9:', None ),
        ( 'F9:0', 9 ),
        ( 'F9:0.', None ),
        ( 'F9:10.0', 9 ),
        ( 'S', None ),
        ( 's', None ),
        ( 'ST', None ),
        ( 'st', None ),
        ( 'ST20', 20 ),
        ( 'ST20:', None ),
        ( 'ST20:0', 20 ),
        ( 'ST20:0.', None ),
        ( 'ST20:10.0', 20 ),
        ]

    for tst in tsts:
        data = tst[0]
        expect = tst[1]

        if chatty:
            print 'tst=%s' % str(tst)

        rtn = getFileNumber(data)
        if expect != rtn:
            print 'error, (%s) returned NOT as expected (%s), tst=%s' % (rtn,expect,str(tst))
            return

    if( chatty):
        print 'finished Element parsing pccc_util.getFileNumber()',
    print '... Okay!'

    print '\ntest Element parsing pccc_util.getElemOffset()',

    if( chatty):
        print ''

    tsts = [
        ( None, None ),
        ( '', None ),
        ( 'A', None ),
        ( 12, 12 ),
        ( 'N', None ),
        ( 'n', None ),
        ( 'N7', 0 ),
        ( 'N7:', None ),
        ( 'N7:0', 0 ),
        ( 'N7:1.', None ),
        ( 'N7:10.0', 10 ),
        ( 'B', None ),
        ( 'b', None ),
        ( 'B3', 0 ),
        ( 'B3:', None ),
        ( 'B3:0', 0 ),
        ( 'B3:1.', None ),
        ( 'B3:10.0', 10 ),
        ( 'F', None ),
        ( 'f', None ),
        ( 'F9', 0 ),
        ( 'F9:', None ),
        ( 'F9:99', 99 ),
        ( 'F9:100.', None ),
        ( 'F9:13.0', 13 ),
        ( 'S', None ),
        ( 's', None ),
        ( 'ST', None ),
        ( 'st', None ),
        ( 'ST20', 0 ),
        ( 'ST20:', None ),
        ( 'ST20:0', 0 ),
        ( 'ST20:0.', None ),
        ( 'ST20:10.0', 10 ),
        ]

    for tst in tsts:
        data = tst[0]
        expect = tst[1]

        if chatty:
            print 'tst=%s' % str(tst)

        rtn = getElemOffset(data)
        if expect != rtn:
            print 'error, (%s) returned NOT as expected (%s), tst=%s' % (rtn,expect,str(tst))
            return

    if( chatty):
        print 'finished Element parsing pccc_util.getElemOffset()',
    print '... Okay!'

    print '\ntest Element parsing pccc_util.getSubElemOffset()',

    if( chatty):
        print ''

    tsts = [
        ( None, None ),
        ( '', None ),
        ( 'A', None ),
        ( 12, 12 ),
        ( 'N', None ),
        ( 'n', None ),
        ( 'N7', 0 ),
        ( 'N7:', None ),
        ( 'N7:0', 0 ),
        ( 'N7:1.', None ),
        ( 'N7:10.2', 2 ),
        ( 'N7:10.2', 2 ),
        ( 'ST20:0.', None ),
        ( 'ST20:10.0', 0 ),
        ]

    for tst in tsts:
        data = tst[0]
        expect = tst[1]

        if chatty:
            print 'tst=%s' % str(tst)

        rtn = getSubElemOffset(data)
        if expect != rtn:
            print 'error, (%s) returned NOT as expected (%s), tst=%s' % (rtn,expect,str(tst))
            return

    if( chatty):
        print 'finished Element parsing pccc_util.getSubElemOffset()',
    print '... Okay!'

    return

def test_slc_clean(chatty = False):

    print '\ntest pccc_util.prepareSlcClean()',

    if( chatty):
        print ''

    xdct = None
    try:
        prepareSlcClean(xdct)
        print "error, didn't throw exception with no xdct"
        return
    except:
        pass

    xdct = {}
    try:
        prepareSlcClean(xdct)
        print "error, didn't throw exception with xdct( %s )" % xdct
        return
    except:
        pass

    xdct = {'slc_clean':False}
    try:
        prepareSlcClean(xdct)
        print "error, didn't throw exception with xdct( %s )" % xdct
        return
    except:
        pass

    xdct = {'slc_clean':True}
    try:
        prepareSlcClean(xdct)
        # this should pass

    except:
        traceback.print_exc()
        print "error, threw expected exception with xdct( %s )" % xdct
        return
        pass

    xdct = {'elm':'N7'}
    if( chatty):
        print 'try %s' % str(xdct)

    prepareSlcClean(xdct)
    # this should pass

    if xdct['slc_clean'] != True:
        print "error, expected xdct['slc_clean'] wasn't True as expected"
        return

    if xdct['typ'] != 'N':
        print "error, expected xdct['typ'] wasn't 'N' as expected"
        return

    if xdct['typ_siz'] != 2:
        print "error, expected xdct['typ_siz'] wasn't 2 as expected"
        return

    if xdct['ofs'] != 0:
        print "error, expected xdct['ofs'] wasn't 0 as expected"
        return

    if xdct['sub_elm'] != 0:
        print "error, expected xdct['sub_elm'] wasn't 0 as expected"
        return

    if xdct['num'] != 7:
        print "error, expected xdct['num'] wasn't 7 as expected"
        return

    if xdct['cnt'] != 1:
        print "error, expected xdct['cnt'] wasn't 1 as expected"
        return

    if xdct['dst'] != 1:
        print "error, expected xdct['dst'] wasn't 1 as expected"
        return

    if xdct['src'] != 0:
        print "error, expected xdct['src'] wasn't 0 as expected"
        return

    if not xdct.has_key('tns'):
        print "error, expected xdct['tns'] to exist - did not"
        return

    xdct = {'elm':'F3:10.3', 'cnt':5, 'src':99, 'tns':1001}
    if( chatty):
        print 'try %s' % str(xdct)

    prepareSlcClean(xdct)
    # this should pass

    if xdct['slc_clean'] != True:
        print "error, expected xdct['slc_clean'] wasn't True as expected"
        return

    if xdct['typ'] != 'F':
        print "error, expected xdct['typ'] wasn't 'F' as expected"
        return

    if xdct['typ_siz'] != 4:
        print "error, expected xdct['typ_siz'] wasn't 4 as expected"
        return

    if xdct['ofs'] != 10:
        print "error, expected xdct['ofs'] wasn't 10 as expected"
        return

    if xdct['sub_elm'] != 3:
        print "error, expected xdct['sub_elm'] wasn't 3 as expected"
        return

    if xdct['num'] != 3:
        print "error, expected xdct['num'] wasn't 7 as expected"
        return

    if xdct['cnt'] != 5:
        print "error, expected xdct['cnt'] wasn't 5 as expected"
        return

    if xdct['dst'] != 1:
        print "error, expected xdct['dst'] wasn't 1 as expected"
        return

    if xdct['src'] != 99:
        print "error, expected xdct['src'] wasn't 99 as expected"
        return

    if xdct['tns'] != 1001:
        print "error, expected xdct['tns'] wasn't 1001 as expected"
        return

    if( chatty):
        print 'finished pccc_util.prepareSlcClean()',
    print '... Okay!'

    return

def test_make_slc_address(chatty = False):

    print '\ntest pccc_util.makeSlcAddress() with three-addresses',

    if( chatty):
        print ''

    tsts = [
        ( {'elm':'N7'},   "\x02\x07\x89\x00\x00" ),
        ( {'elm':'B3'},   "\x02\x03\x85\x00\x00" ),
        ( {'elm':'F9'},   "\x04\x09\x8A\x00\x00" ),
        ( {'elm':'ST12'}, "\x54\x0C\x8D\x00\x00" ),
        ( {'elm':'N7:1'},   "\x02\x07\x89\x01\x00" ),
        ( {'elm':'B3:1'},   "\x02\x03\x85\x01\x00" ),
        ( {'elm':'F9:1'},   "\x04\x09\x8A\x01\x00" ),
        ( {'elm':'ST12:1'}, "\x54\x0C\x8D\x01\x00" ),
        ( {'elm':'N7:1.0'},   "\x02\x07\x89\x01\x00" ),
        ( {'elm':'B3:1.1'},   "\x02\x03\x85\x01\x01" ),
        ( {'elm':'F9:1.2'},   "\x04\x09\x8A\x01\x02" ),
        ( {'elm':'ST12:1.3'}, "\x54\x0C\x8D\x01\x03" ),
        ( {'elm':'N7:9', 'cnt':2},    "\x04\x07\x89\x09\x00" ),
        ( {'elm':'B3:9', 'cnt':2},    "\x04\x03\x85\x09\x00" ),
        ( {'elm':'F9:09', 'cnt':2},   "\x08\x09\x8A\x09\x00" ),
        ( {'elm':'ST12:9', 'cnt':2},  "\xA8\x0C\x8D\x09\x00" ),
        ]

    for tst in tsts:
        data = copy.copy(tst[0])
        expect = tst[1]

        if chatty:
            print 'tst=%s' % str(tst)

        rtn = makeSlcAddress(data)
        if expect != rtn:
            print 'error, (%s) returned NOT as expected (%s), tst=%s' % \
            (show_bytes('returned',rtn),show_bytes('expected',expect),str(tst))
            print 'error, processed xdct was ( %s )' % str(data)
            return

    if( chatty):
        print 'finished Element parsing pccc_util.makeSlcAddress() with three-addresses',
    print '... Okay!'

    print '\ntest pccc_util.makeSlcAddress() with two-addresses',

    if( chatty):
        print ''

    tsts = [
        ( {'elm':'N7', '2adr':False},  "\x02\x07\x89\x00\x00" ),
        ( {'elm':'N7', '2adr':True},   "\x02\x07\x89\x00" ),
        ( {'elm':'B3', '2adr':True},   "\x02\x03\x85\x00" ),
        ( {'elm':'F9', '2adr':True},   "\x04\x09\x8A\x00" ),
        ( {'elm':'ST12', '2adr':True}, "\x54\x0C\x8D\x00" ),
        ( {'elm':'N7:1', '2adr':True},   "\x02\x07\x89\x01" ),
        ( {'elm':'B3:1', '2adr':True},   "\x02\x03\x85\x01" ),
        ( {'elm':'F9:1', '2adr':True},   "\x04\x09\x8A\x01" ),
        ( {'elm':'ST12:1', '2adr':True}, "\x54\x0C\x8D\x01" ),
        ( {'elm':'N7:1.0', '2adr':True},   "\x02\x07\x89\x01" ),
        ( {'elm':'B3:1.1', '2adr':True},   "\x02\x03\x85\x01" ),
        ( {'elm':'F9:1.2', '2adr':True},   "\x04\x09\x8A\x01" ),
        ( {'elm':'ST12:1.3', '2adr':True}, "\x54\x0C\x8D\x01" ),
        ( {'elm':'N7:9', '2adr':True, 'cnt':2},    "\x04\x07\x89\x09" ),
        ( {'elm':'B3:9', '2adr':True, 'cnt':2},    "\x04\x03\x85\x09" ),
        ( {'elm':'F9:09', '2adr':True, 'cnt':2},   "\x08\x09\x8A\x09" ),
        ( {'elm':'ST12:9', '2adr':True, 'cnt':2},  "\xA8\x0C\x8D\x09" ),
        ]

    for tst in tsts:
        data = copy.copy(tst[0])
        expect = tst[1]

        if chatty:
            print 'tst=%s' % str(tst)

        rtn = makeSlcAddress(data)
        if expect != rtn:
            print 'error, (%s) returned NOT as expected (%s), tst=%s' % \
            (show_bytes('returned',rtn),show_bytes('expected',expect),str(tst))
            print 'error, processed xdct was ( %s )' % str(data)
            return

    if( chatty):
        print 'finished Element parsing pccc_util.makeSlcAddress() with two-addresses',
    print '... Okay!'

    return

def test_make_slc_typed_read(chatty = False):

    print '\ntest pccc_util.makeSlcProtectedTypesLogicalRead()',

    if( chatty):
        print ''

    tsts = [
        ( {'elm':'N7', 'tns':0x1199},       "\x0F\x00\x99\x11\xA2\x02\x07\x89\x00\x00" ),
        ( {'elm':'B3:1', 'tns':0x1198},     "\x0F\x00\x98\x11\xA2\x02\x03\x85\x01\x00" ),
        ( {'elm':'F9:1.2', 'tns':0x1197},   "\x0F\x00\x97\x11\xA2\x04\x09\x8A\x01\x02" ),
        ( {'elm':'ST12:9.1', 'tns':0x1196}, "\x0F\x00\x96\x11\xA2\x54\x0C\x8D\x09\x01" ),
        ( {'elm':'N7', 'tns':0x1599, '2adr':False},      "\x0F\x00\x99\x15\xA2\x02\x07\x89\x00\x00" ),
        ( {'elm':'N7', 'tns':0x1699, '2adr':True},       "\x0F\x00\x99\x16\xA1\x02\x07\x89\x00" ),
        ( {'elm':'B3:1', 'tns':0x1799, '2adr':True},     "\x0F\x00\x99\x17\xA1\x02\x03\x85\x01" ),
        ( {'elm':'F9:1.2', 'tns':0x1899, '2adr':True},   "\x0F\x00\x99\x18\xA1\x04\x09\x8A\x01" ),
        ( {'elm':'ST12:9.1', 'tns':0x1999, '2adr':True}, "\x0F\x00\x99\x19\xA1\x54\x0C\x8D\x09" ),
        ]

    for tst in tsts:
        data = copy.copy(tst[0])
        expect = tst[1]

        if chatty:
            print 'tst=%s' % str(tst)

        rtn = makeSlcProtectedTypesLogicalRead(data)
        if expect != rtn:
            print 'error, (%s) returned NOT as expected (%s), tst=%s' % \
            (show_bytes('returned',rtn),show_bytes('expected',expect),str(tst))
            return

    if( chatty):
        print 'finished Element parsing pccc_util.makeSlcProtectedTypesLogicalRead()',
    print '... Okay!'

    return

if __name__ == '__main__':

    test_all = False
    chatty = True

    if False or test_all:
        test_tns(chatty)

    if False or test_all:
        test_element_parse(chatty)

    if False or test_all:
        test_slc_clean(chatty)

    if False or test_all:
        test_make_slc_address(chatty)

    if True or test_all:
        test_make_slc_typed_read(chatty)
