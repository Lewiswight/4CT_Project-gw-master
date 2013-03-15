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
