#####################################################################
# Automatically generated file
# Don't edit this file
# Created on: 11 March 2013
#####################################################################

import threading
import sys, os 

sys.path.insert(0, os.path.join(os.path.abspath('.'), 'dpdebug.zip'))

import pydevd
pydevd.settrace('172.16.4.0', stdoutToServer=False, stderrToServer=False, suspend=False, trace_only_current_thread=False)
threading.settrace(pydevd.GetGlobalDebugger().trace_dispatch)

print "Debugging Dia framework ...\r\n"

if not os.path.isdir('/Users/lewiswight/MistAway-Gateway/Dia_2.1.0/'):
    execfile(os.path.join(os.path.abspath('.'), 'dia.py'))
else:
    execfile('/Users/lewiswight/MistAway-Gateway/Dia_2.1.0/dia.py')

