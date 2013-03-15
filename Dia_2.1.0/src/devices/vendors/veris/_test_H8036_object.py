# process/create Modbus/PDU (core cmd) packets
#
import copy
import traceback

from H8036_object import *

def show_import(chatty = False):

    print '\nShow import of H8036 message - default',

    data = "\x01\x00\x00\x00\x00\x6F\x01\x03\x6C\x45\xB2\x28\x00\x45\xB2\x28" + \
           "\x00\x3F\x70\x00\x00\x3F\x04\x00\x00\x3F\x88\x80\x00\x3F\x60\x5E" + \
           "\x00\x43\x23\x98\x00\x42\xA4\xE8\x00\x40\x39\x40\x00\x3E\xA4\x00" + \
           "\x00\x3F\x1D\x00\x00\x00\x00\x00\x00\x3F\x68\xBE\x00\x3F\x5B\x5A" + \
           "\x00\x00\x00\x00\x00\x43\x75\x40\x00\x42\xF5\x90\x00\x42\xF5\x80" + \
           "\x00\x42\xF5\x10\x00\x42\xF6\x18\x00\x3F\xE6\x00\x00\x40\x38\x40" + \
           "\x00\x40\xB9\xC0\x00\x00\x00\x00\x00\x3F\x34\x00\x00\x00\x00\x00" + \
           "\x00\x40\x2E\xC0\x00"

    mtr = VerisH8036()
    mtr._seqno = 2 # we want 2-1 = 0x01
    if( chatty):
        print ''
        mtr._trace = True
    else:
        mtr._trace = False

    print mtr.import_binary(data)
    print mtr.report_text(nulls=chatty)

    print '\nShow import of H8036 message - add phases',
    enb = ['Phase', 'split']
    mtr.enable_channels(enb)
    print mtr.import_binary(data)
    print mtr.report_text(nulls=chatty)

    print '\nShow import of H8036 message - add 3-phase/phase-C',
    enb = ['3']
    mtr.enable_channels(enb)
    print mtr.import_binary(data)
    print mtr.report_text(nulls=chatty)

    print '\nShow import of H8036 message - add minmax',
    enb = ['minmax']
    mtr.enable_channels(enb)
    print mtr.import_binary(data)
    print mtr.report_text(nulls=chatty)

    print '\nShow import of H8036 message - add minmax',
    enb = ['split', 'minmax']
    mtr.enable_channels(enb)
    print mtr.import_binary(data)
    print mtr.report_text(nulls=chatty)

    print '\nShow import of H8036 message - add model',
    enb = ['model']
    mtr.enable_channels(enb)
    print mtr.import_binary(data)
    print mtr.report_text(nulls=chatty)

    print '\nShow import of H8036 message - demote to 8035',
    enb = ['H8035']
    mtr.enable_channels(enb)
    print mtr.import_binary(data)
    print mtr.report_text(nulls=chatty)

    return

def show_import_sunspec(chatty = False):

    print '\nShow SunSpec import of H8036 message - default',

    data = "\x01\x00\x00\x00\x00\x6F\x01\x03\x6C\x45\xB2\x28\x00\x45\xB2\x28" + \
           "\x00\x3F\x70\x00\x00\x3F\x04\x00\x00\x3F\x88\x80\x00\x3F\x60\x5E" + \
           "\x00\x43\x23\x98\x00\x42\xA4\xE8\x00\x40\x39\x40\x00\x3E\xA4\x00" + \
           "\x00\x3F\x1D\x00\x00\x00\x00\x00\x00\x3F\x68\xBE\x00\x3F\x5B\x5A" + \
           "\x00\x00\x00\x00\x00\x43\x75\x40\x00\x42\xF5\x90\x00\x42\xF5\x80" + \
           "\x00\x42\xF5\x10\x00\x42\xF6\x18\x00\x3F\xE6\x00\x00\x40\x38\x40" + \
           "\x00\x40\xB9\xC0\x00\x00\x00\x00\x00\x3F\x34\x00\x00\x00\x00\x00" + \
           "\x00\x40\x2E\xC0\x00"

    mtr = VerisH8036()
    mtr._seqno = 2 # we want 2-1 = 0x01
    if( chatty):
        print ''
        mtr._trace = True
    else:
        mtr._trace = False

    print mtr.import_binary(data)
    lst = mtr.report_SunSpec()
    for itm in lst: print itm

    print '\nShow import of H8036 message - add phases'
    enb = ['Phase', 'split']
    mtr.enable_channels(enb)
    print mtr.import_binary(data)
    lst = mtr.report_SunSpec()
    for itm in lst: print itm

    print '\nShow import of H8036 message - add 3-phase/phase-C'
    enb = ['3']
    mtr.enable_channels(enb)
    print mtr.import_binary(data)
    lst = mtr.report_SunSpec()
    for itm in lst: print itm

    print '\nShow import of H8036 message - demote to 8035'
    enb = ['H8035']
    mtr.enable_channels(enb)
    print mtr.import_binary(data)
    lst = mtr.report_SunSpec()
    for itm in lst: print itm

    return

def test_get_channels(chatty = False):

    print '\nTest get_channels',

    mtr = VerisH8036()
    mtr._seqno = 2 # we want 2-1 = 0x01
    if( chatty):
        print ''
        mtr._trace = True
    else:
        mtr._trace = False

    print '\nTest get_channels for H8035 Export'
    mtr.enable_channels(['H8035', 'export'])
    lst = mtr.get_channel_name_list()
    print lst

    print '\nTest get_channels for H8035 Import'
    mtr.enable_channels(['H8035', 'import'])
    lst = mtr.get_channel_name_list()
    print lst

    print '\nTest get_channels for Default'
    mtr.enable_channels(['def'])
    lst = mtr.get_channel_name_list()
    print lst

    print '\nTest get_channels for H8036 - add 2-phase'
    mtr.enable_channels(['Phase','2'])
    lst = mtr.get_channel_name_list()
    print lst

    print '\nTest get_channels for H8036 - add 3-phase'
    mtr.enable_channels(['phase','3'])
    lst = mtr.get_channel_name_list()
    print lst

    print '\nTest get_channels for H8036 - add min/max'
    mtr.enable_channels('minmax')
    lst = mtr.get_channel_name_list()
    print lst

    return

    tsts = [
        ( None, None ),
        ( '', None ),
        ( 'A', None ),
        ( 12, None ),
        ( 'N', 'N' ),
        ( 'n', 'N' ),
        ( 'N7', 'N' ),
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

    return

if __name__ == '__main__':

    test_all = False
    chatty = False

    if False or test_all:
        show_import(chatty)

    if False or test_all:
        show_import_sunspec(chatty)

    if True or test_all:
        test_get_channels(chatty)

