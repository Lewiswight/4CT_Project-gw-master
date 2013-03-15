Digi ConnectPort X3
====================

Many of the demos in this directory assume that the primary
communications interface available to communicate with the device
running Dia will be through an IP based network connection.  However,
in certain circumstances primarily involving the Digi ConnectPort X3,
the type of cellular connection provided is not suitable for running
server-style services such as the 'web' and tcp 'console'
sessions. Or, you may not know in advance the IP address that is
assigned to the device.

If you are running the Dia in one of these environments, you should
modify the given example .yml files accordingly.  This will not only
save resources, but also give you additional options for connecting.  

Console Presentation
--------------------

The console presentation is by default configured to present its CLI
through a TCP based network socket.  However, the presentation is also
capable of operation using a serial port.  In any of the given example
YML files, change the 'type' setting to 'serial' and optionally
configure the 'baud' and 'device' settings to be correct for your
serial connection.  The default parameters of 115200 and '/com/0' are
appropriate for a Digi ConnectPort X3 without modification.
