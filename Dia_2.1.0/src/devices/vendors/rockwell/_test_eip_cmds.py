#!/usr/bin/env python

# set trace state=on mask=ia:info+debug

# test the various EIP layer commands

import time

import cip          # CIP Object handling
import eip          # EIP encap layer

def test_nop_cmd( eipc, x_prm):
    prm = { "attach" : 0 }
    prm.update( x_prm)

    eipc.open()

    # attach = [ 0, 1, 2, 10, 25, 100, 1000, 5000, 65535 ]
    attach = [ 0, 1, 2, 10, 25, 100 ]
    for dat in attach:
        tst = "attach_%d" % dat
        st = "test with %d data bytes attached" % dat
        prm.update( { "attach" : dat } )

        st = eipc.buildNOP( dat, prm )
        eipc.printHeader( st)

        if( dat == 25):
            st = st + st

        eipc.send( st)
        # time.sleep( 0.1) # need to force send?

    eipc.close()

    return

def test_list_cmds( eipc, x_prm):
    prm = { }
    prm.update( x_prm)

    # This Command by UDP or TCP

    eipc.open()

    sTst = "list_tar"
    st = eipc.buildListTargets( prm )
    eipc.send( st)
    rtn = eipc.recv( 100)
    if( not rtn):
        print( "No response", "one was expected")
    else:
        nStat = eipc.n_ParseLE32( rtn[8:12]) # parse status
        if( nStat == 0):
            # note: will see this "expected error" for AB PLC since this
            # command is NOT part of the ODVA spec
            print( "return status was ok", "expected error")
        elif( nStat == 1):
            print( "return status was ok", "as expected")
        else:
            print( "return status not as expected", "Should be one (1)")
        eipc.printHeader( rtn)

    st = eipc.buildListInterfaces( prm )
    eipc.send( st)
    rtn = eipc.recv( 100)
    if( not rtn):
        print( "No response", "one was expected")
    else:
        nStat = eipc.n_ParseLE32( rtn[8:12]) # parse status
        nAttachedData = eipc.n_ParseLE16( rtn[2:4]) # parse attached data
        if( nStat != 0):
            print( "return status not as expected", "Should be zero (0)")
        else:
            if( nAttachedData == 2):
                print( "return status was ok", "attached data ok")
            else:
                print( "return status was ok", "attached data is wrong")
        eipc.printHeader( rtn)

    st = eipc.buildListServices( prm )
    eipc.send( st)
    rtn = eipc.recv( 100)
    if( not rtn):
        print( "No response", "one was expected")
    else:
        nStat = eipc.n_ParseLE32( rtn[8:12]) # parse status
        nAttachedData = eipc.n_ParseLE16( rtn[2:4]) # parse attached data
        if( nStat != 0):
            print( "return status not as expected", "Should be zero (0)")
        else:
            if( nAttachedData == 26):
                print( "return status was ok", "attached data ok")
            else:
                print( "return status was ok", "attached data is wrong")
        eipc.printHeader( rtn)

    st = eipc.buildListIdentity( prm )
    eipc.send( st)
    rtn = eipc.recv( 100)
    if( not rtn):
        print( "No response", "one was expected")
    else:
        nStat = eipc.n_ParseLE32( rtn[8:12]) # parse status
        nAttachedData = eipc.n_ParseLE16( rtn[2:4]) # parse attached data
        if( nStat != 0):
            print( "return status not as expected", "Should be zero (0)")
        else:
            if( nAttachedData > 40):
                print( "return status was ok", "attached data ok")
            else:
                print( "return status was ok", "attached data is wrong")
        eipc.printHeader( rtn)

    eipc.close()

    return

def test_session_cmds( eipc, x_prm):
    prm = { }
    prm.update( x_prm)

    eipc.open()

    st = eipc.buildRegisterSession( prm )
    eipc.printHeader( st)
    eipc.send( st)
    rtn = eipc.recv( 100)
    eipc.printHeader( rtn)
    rtn = eipc.parseRegisterSessionReply( rtn)

    st = eipc.buildRegisterSession( prm )
    eipc.printHeader( st)
    eipc.send( st)
    rtn = eipc.recv( 100)
    eipc.printHeader( rtn)
    rtn = eipc.parseRegisterSessionReply( rtn)

    st = eipc.buildUnregisterSession( prm )
    eipc.printHeader( st)
    eipc.send( st)
    rtn = eipc.recv( 100)
    print list( rtn)
    # eipc.printHeader( rtn)

    eipc.close()

    return

def test_sendrr_cmds( eipc, x_prm):
    prm = { }
    prm.update( x_prm)

    ## eipc.open()
    if( eipc.OpenSession( prm) == 0):
        # then error
        print "EIP RegSes failed!"
        return -1

    prm.update( cip.id_cls_getAttribAll)
    idreq = eipc.buildUCMM( prm)
    eip.print_bytes( "Id Request:", idreq)
    eipc.send( idreq)
    print

    idrsp = eipc.recv( 100)
    eip.print_bytes( "Id Reply:", idrsp)
    print

    eipc.close()

    return

if __name__ == '__main__':

    print
    print "This python script tests the basic EIP commands"

    prm = {}

    test_all = True

    # x.21 = CLgx, x.22 = SLC5/05, x.23 = uLgx1100
    # prm.update( { "port" : 44818, "ip" : "10.9.92.21" } )
    prm.update( { "port" : 44818, "ip" : "10.9.92.22" } )
    # prm.update( { "port" : 44818, "ip" : "10.9.92.23" } )

    eipc = eip.eip_client()
    eipc.updateFromDict( prm)

    lps = 999
    while( lps < 1000):
        lps += 1

        if False or test_all:
            test_nop_cmd(eipc, prm)

        if False or test_all:
            test_list_cmds(eipc, prm)

        if False or test_all:
            test_session_cmds(eipc, prm)

        if True or test_all:
            test_sendrr_cmds(eipc, prm)

        time.sleep( 1.0)

    # endwhile

    eipc.close()

