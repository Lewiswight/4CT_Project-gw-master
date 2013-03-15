Annotated Samples
=================

Overview
--------

This sample is a little bit different.  Dia as a framework is
something that most people add on to by extending it through new
presentations, devices and services.  The core is left alone.  It may
not even cross some people's minds that extending the core would be a
useful way to add their functionality to the system.  

While it may be a bit more daunting to extend the system in this way,
it can be useful.  For example, in the existing Dia the core central
concept around which much of the rest of the system hinges is the data
flow of a 'Sample' object from device drivers, into the channel
database for consumption by the presentations. However, there is no
defined way to carry much additional meta-data about the Samples
through the system with it.  

People have resorted to several mechanisms to provide data of this
sort; Using an additional channel to report errors and status, putting
non-conforming data into the value of a 'Sample' on error, rather than
values of the type expected, etc...

The code provided in this sample takes a new approach and adds on to
the core Sample object in order to 'annotate' it with simple
information about the validity and status of the value contained.  

Design
------

Taking advantage of the fact that Dia is designed in an
object-oriented fashion, we will extend the existing 'Sample' object to
add the information that we intend to pass through the system.

Take a look at 'annotated_sample.py' we introduce the
'AnnotatedSample' class.  This adds a two-tiered classification of
status information.  The information that we'll add here are sets of
tags.  Some tags may represent an error, while others will purely be
informative or passed through the system for some other purpose.

Because for our purposes the presence or potentially absence of a tag
contains enough for the data we want to ride along, we will store
these tags in Python built-in set objects.  This will give us easy
tools to test for the presence of a tag in an object and provide
unique-ness and other handy traits.  Because this is a simple
data-structure we've also decided not to create a new API for
interacting with each set, more complicated schemes would extend the
interface with new members as well.

Using AnnotatedSamples
----------------------

Due to sub-classing, With just this one simple new class, one could
begin to write device drivers that populated the system with
AnnotatedSample objects by passing them into 'property_set' rather
than a base Sample.  All existing presentations and the channel
database treat them as normal Samples with no knowledge of their
additional payload.  Extending the presentations to act on this new
potential source of information is as simple as performing an
'isinstance(sample, AnnotatedSample)` and taking appropriate action.  

Annotation Services
++++++++++++++++++++

Keeping with our theme of extending core functionality, these new
objects also add some unique additional ways to deal with data in the
system.  They provide a clean way to specify added constraints on a
system that may not depend on any particular device and its specifics.

To demonstrate this, we are providing two new services; the
'TimingService' and 'ValueService'.  Both of these insert themselves
into the normal chain of channel processing and provide new settings
that dictate when samples will be annotated and how particular tags
will be populated.

Each 'Channel' object in the channel database uses a 'ChannelSource'
object to provide the 'Sample' objects which live in the database.  By
default, this is a 'ChannelSourceDeviceProperty', which is created
automatically by device drivers to create the link between each
driver's properties and the entry in the database.  We do not want to
sever this link, but we do want to process it in a new way.
Therefore, we create a new ChannelSource that replaces the device
properties position in the channel database and yet maintains an
internal reference.

From that point, the key to each driver is to use the hooks provided
by the system to process the data.  The timing service interacts with
the scheduler, and the value service is able to make determinations
immediately. 

See Also
--------

For more information on the concepts being modified here, please make
sure you are familiar with the Developer's Guide section of the Dia
documentation. https://developer.idigi.com/edocs/documentation/index.html
The API reference section in particular documents the objects and
interfaces being used and modified in this sample.

The two services provided here are both heavily documented in comments
and docstrings as well.
