############################################################################
#                                                                          #
# Copyright (c)2008, 2009, Digi International (Digi). All Rights Reserved. #
#                                                                          #
# Permission to use, copy, modify, and distribute this software and its    #
# documentation, without fee and without a signed licensing agreement, is  #
# hereby granted, provided that the software is used on Digi products only #
# and that the software contain this copyright notice,  and the following  #
# two paragraphs appear in all copies, modifications, and distributions as #
# well. Contact Product Management, Digi International, Inc., 11001 Bren   #
# Road East, Minnetonka, MN, +1 952-912-3444, for commercial licensing     #
# opportunities for non-Digi products.                                     #
#                                                                          #
# DIGI SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED   #
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A          #
# PARTICULAR PURPOSE. THE SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, #
# PROVIDED HEREUNDER IS PROVIDED "AS IS" AND WITHOUT WARRANTY OF ANY KIND. #
# DIGI HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES,         #
# ENHANCEMENTS, OR MODIFICATIONS.                                          #
#                                                                          #
# IN NO EVENT SHALL DIGI BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT,      #
# SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS,   #
# ARISING OUT OF THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF   #
# DIGI HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.                #
#                                                                          #
############################################################################

"""\ 
An AnnotatedSample augments the Sample object with sets that user
configurable modules can add to qualify the data.  These are intended
to be strings that presentations may use to influence the way they
interpret or process data.

use sample.errors.add('err') to add an error to the set

use 'err' in sample.errors to test for membership

Suggested predefined errors
ERSAM_NOT_INIT = 'not_init'     # data has not yet been set
ERSAM_STALE_DATA = 'stale'      # data was valid, but is now old, device is not updating
ERSAM_OFFLINE = 'offline'       # data is garbage, device is gone/offline
ERSAM_BAD_DATA = 'bad_data'     # data is known bad
ERSAM_BAD_CALC = 'bad_calc'     # internal calc failed, data is bad
ERSAM_SUPPORT = 'no_support'    # Dia is proxy, end-device does not support this

"""

ERSAM_NOT_INIT = 'not_init'
ERSAM_STALE_DATA = 'stale'
ERSAM_OFFLINE = 'offline'
ERSAM_BAD_DATA = 'bad_data'
ERSAM_BAD_CALC = 'bad_calc'
ERSAM_SUPPORT = 'no_support'

from common.helpers.format_channels import iso_date
from samples.sample import Sample

class AnnotatedSample(Sample):
    # Using slots saves memory by keeping __dict__ undefined.
    __slots__ = ["errors", "other"]

    def __init__(self, sample):
        self.errors = set()
        self.other = set()

        Sample.__init__(self, sample.timestamp, sample.value, sample.unit)

    def __repr__(self):
        return '<AnnotatedSample: "%s" "%s" "%s" "%s" at "%s">' % \
            (self.value, self.unit, self.errors, self.other,
             iso_date(self.timestamp))
