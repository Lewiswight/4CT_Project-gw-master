# process/create Modbus/PDU (core cmd) packets
#
import copy
import traceback

from ecm_object import *
from ecm_object_sunspec import *

def test_import(chatty = False):

    print '\ntest import of ECM message',

    if( chatty):
        print ''

    data = "\xfe\xff\x03\x05\x43\x35\x9e\x01\x00\x00\x06\x64\x00\x00\x00\x8a\x75\x00\x00\x00\x6d\x29\x00\x00\x00\x43\x87"
    data += "\x0c\x00\x43\x87\x99\x03\x07\x00\x00\x00\x23\x4d\x04\x00\x00\x00"
    data += "\x00\x00\x00\x00\x00\x40\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\x01\xff\xfe\x13"
    print len(data)

    ecm = ECM1240()
    x = ecm.import_binary( data)
    print x

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

def test_sunspec_xml_dump(chatty = False):

    print '\ntest XML creation',

    if( chatty):
        print ''

    ecm = ECM1240_SunSpec()

    ecm._voltage = 124.5
    ecm._current = [10.1,20.2]
    ecm._power = [11.1,22.2,33.3,44.4,55.5,66.6,77.7]
    ecm._kwh = [101.1,202.2,303.3,404.4,505.5,606.6,707.7]

    print ecm._dump_sunspec_xml_power(0),
    print ecm._dump_sunspec_xml_energy(0),
    print ecm._dump_sunspec_xml_current(0),
    print ecm._dump_sunspec_xml_voltage(0),
    print

    p_index=''
    print ecm._dump_sunspec_xml_power(0, p_index),
    print ecm._dump_sunspec_xml_energy(0, p_index),
    print ecm._dump_sunspec_xml_current(0, p_index),
    print ecm._dump_sunspec_xml_voltage(0, p_index),
    print

    p_index=' x="1"'
    print ecm._dump_sunspec_xml_power(0, p_index),
    print ecm._dump_sunspec_xml_energy(0, p_index),
    print ecm._dump_sunspec_xml_current(0, p_index),
    print ecm._dump_sunspec_xml_voltage(0, p_index),
    print

    print '==============\r\n'

    for i in (0,1,2,3,4,5,6):
        st = ecm._dump_sunspec_xml_model_single([], i)
        # print st
        print "".join(st)

    print '==============\r\n'

    print
    for i in (0,1,2,3,4,5,6):
        st = ecm._dump_sunspec_xml_model_single([], i, p_index=False)
        # print st
        print "".join(st)

    ecm._voltage = None
    ecm._current = [10.1,None]
    ecm._power = [11.1,22.2,None,44.4,55.5,66.6,77.7]
    ecm._kwh = [101.1,202.2,303.3,None,505.5,606.6,707.7]

    print
    for i in (0,1,2,3,4,5,6):
        st = ecm._dump_sunspec_xml_model_single([], i, p_index=False)
        # print st
        print "".join(st)

    ecm._voltage = 124.5
    ecm._current = [10.1,20.2]
    ecm._power = [11.1,22.2,33.3,44.4,55.5,66.6,77.7]
    ecm._kwh = [101.1,202.2,303.3,404.4,505.5,606.6,707.7]

    print "\r\nNo units, model indexed"
    ecm._xml_add_units = False
    st = ecm._dump_sunspec_xml_model_all([], p_index=False)
    # print st
    print "".join(st)

    print "\r\nWith units, model indexed"
    ecm._xml_add_units = True
    st = ecm._dump_sunspec_xml_model_all([], p_index=False)
    # print st
    print "".join(st)

    print "\r\nNo units, point indexed"
    ecm._xml_add_units = False
    st = ecm._dump_sunspec_xml_model_all([], p_index=True)
    # print st
    print "".join(st)

    print "\r\nWith units, point indexed"
    ecm._xml_add_units = True
    st = ecm._dump_sunspec_xml_model_all([], p_index=True)
    # print st
    print "".join(st)

    print
    print '... Okay!'

    return

def test_sunspec_xml_full(chatty = False):

    print '\ntest Full XML creation',

    if( chatty):
        print ''

    ecm = ECM1240_SunSpec()

    ecm._voltage = 124.5
    ecm._current = [10.1,20.2]
    ecm._power = [11.1,22.2,33.3,44.4,55.5,66.6,77.7]
    ecm._kwh = [101.1,202.2,303.3,404.4,505.5,606.6,707.7]

    ecm._single_channel = False

    # set to 201 or 402
    ecm.select_sunspec_model(201)

    print "\r\nPoint indexed"
    ecm._xml_add_units = False
    ecm._xml_form = ecm.XML_FORM_POINT_INDEX
    st = ecm._dump_sunspec_xml_device()
    print st

    print "\r\nModel indexed"
    ecm._xml_add_units = False
    ecm._xml_form = ecm.XML_FORM_MODEL_INDEX
    st = ecm._dump_sunspec_xml_device()
    print st

    print "\r\nDevice 'spoofed'"
    ecm._xml_add_units = False
    ecm._xml_form = ecm.XML_FORM_DEVICE_INDEX
    st = ecm._dump_sunspec_xml_device()
    print st

    print '... Okay!'

    return

if __name__ == '__main__':

    test_all = False
    chatty = True

    if False or test_all:
        test_import(chatty)

    if False or test_all:
        test_sunspec_xml_dump(chatty)

    if True or test_all:
        test_sunspec_xml_full(chatty)
