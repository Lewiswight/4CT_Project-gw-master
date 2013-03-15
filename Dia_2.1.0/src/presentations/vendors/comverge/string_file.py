############################################################################
#                                                                          #
# Copyright (c)2011 Digi International (Digi). All Rights Reserved.        #
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
Saves a Python object to NDS FS file by using str().

A string can be reloaded, then passed through eval() to recreate the object
"""

# imports
import traceback
import os
import sys
import time
import threading
import gc

import shutil


# constants
if( sys.platform.startswith('digi')):
    # for Digi, put in common python web folder
    ROOT_PATH = os.path.join("WEB", "python") + os.sep
else:
    # for PC/others, put in working directory
    ROOT_PATH = ""

# exception classes

# interface functions

# classes

def load_string_from_file(filename, print_fail=False):
    filename = ROOT_PATH + filename
    return _read_from_file(filename, print_fail)

def _read_from_file(filename, verbose=False):

    try:
        fn = file(filename,'rb')
        data = fn.read()
        fn.close()
        return data

    except:
        if verbose:
            traceback.print_exc()
            print '_read_from_file(%s) failed' % filename

    return None

def save_string_to_file(filename, data, print_fail=True):
    filename = ROOT_PATH + filename
    return _write_to_file(filename, data, print_fail)

def _write_to_file(filename, data, verbose=False):
    try:
        fn = file(filename,'wb')
        data = str(data)
        if verbose:
            print '>>> writing:', data
        fn.write(data)
        fn.close()
        return True

    except:
        if verbose:
            traceback.print_exc()
            print '_write_to_file(%s) failed' % filename

    return False

class string_flash_cache(object):

    CACHE_EXT = '.txt'
    BAK_EXT = '.bak.txt'
    MIN_HOLD_SECS = 5

    __cache_lock = None

    def __init__(self, name=None):
        self.attrib = {'hold_secs':60, 'max_bytes':50000, 'backup':True, \
                       'delimiter':'\n', 'locked':0 }
        if name is None:
            name = 'cache'
        self.reset_filenames(name)

        if self.__cache_lock is None:
            self.__cache_lock = threading.RLock()
        self.__cache_volitale = []
        return

    def reset_filenames(self, base=None):

        if base is not None:
            self.attrib.update({'basename':base})

        self.attrib.update({'cachename':\
                ROOT_PATH + self.attrib['basename'] + self.CACHE_EXT})
        self.attrib.update({'backupname':\
                ROOT_PATH + self.attrib['basename'] + self.BAK_EXT})

        if self.attrib['hold_secs'] < self.MIN_HOLD_SECS:
            self.attrib['hold_secs'] = self.MIN_HOLD_SECS

        return

    def set_max_bytes(self, max):
        self.attrib.update({'max_bytes':max})
        return

    def append(self, data, now=None, force_write=False):

        if data is None:
            return

        if now is None:
            now = time.time()

        if len(self.__cache_volitale) > 0:
            # then something in cache
            delta = now - self.__cache_start
        else:
            delta = 0

        if data is not None:
            if len(self.__cache_volitale) == 0:
                self.__cache_volitale = [str(data)]
                self.__cache_start = now
                print 'append() first data'

            else:
                self.__cache_volitale.append(str(data))
                print 'append() added data, age:%d secs' % delta

        if force_write or (delta > self.attrib['hold_secs']):
            print 'append() need to save to file'

            try:
                self.save_to_flash()
            except:
                traceback.print_exc

        return

    def lock_cache(self):
        data = None
        # flush the RAM to FLASH
        self.save_to_flash()

        if self.__cache_lock.acquire(False):
            try:
                data = self._read(self.attrib['cachename'])
                if data is None:
                    self.__cache_lock.release()
                    return None

            except:
                traceback.print_exc()

            print 'lock_cache(%s) lock acquired' % self.attrib['basename']
            self.attrib['locked'] = time.time()

        else:
            print 'lock_cache(%s) lock NOT acquired' % self.attrib['basename']
        return data

    def unlock_cache(self):
        print 'unlock_cache(%s) unlocked' % self.attrib['basename']
        self.__cache_lock.release()
        self.attrib['locked'] = 0
        return True

    def free_cache(self):
        self.unlock_cache()

        # save the data to bak
        # self.backup_cache()
        cacfil = self.attrib['cachename']
        if os.path.exists(cacfil):
            print 'deleting cache file %s' % cacfil
            os.remove(cacfil)
        return True

    def save_to_flash(self):

        if (self.__cache_volitale is None) or (len(self.__cache_volitale) <= 0):
            print 'save_to_flash() no volitale data to save'
            return True

        if not self.__cache_lock.acquire(False):
            print 'append() lock failed to acquire'
            return False

        print 'save_to_flash() lock acquired'
        self.attrib['locked'] = time.time()

        if self.attrib['backup']:
            # then optionally save a backup
            self.backup_cache()

        cacfil = self.attrib['cachename']
        if os.path.exists(cacfil):
            # load the old cache, the append to the new data below
            print 'save_to_flash() load from existing file %s' % cacfil
            data = [self._read(cacfil)]
            data.extend(self.__cache_volitale)
        else:
            print 'save_to_flash() no existing file %s' % cacfil
            data = self.__cache_volitale

        # we use the delimiter to prune over-sized file
        data.append(self.attrib['delimiter'])

        data = "".join(data)
        if len(data) > self.attrib['max_bytes']:
            # then file is too large, find appropriate
            chop = len(data) - self.attrib['max_bytes']
            ofs = data.find(self.attrib['delimiter'], chop)
            if ofs != -1:
                chop = ofs + 1
            print 'save_to_flash() too large: chop off %d bytes' % chop
            data = data[chop:]

        self._write(cacfil, data)

        self.__cache_volitale = []
        self.__cache_start = 0

        self.__cache_lock.release()
        self.attrib['locked'] = 0

        # do we need?  be safe, free up temp buffers
        del data
        gc.collect()

        return

    def backup_cache(self):

        cacfil = self.attrib['cachename']
        if os.path.exists(cacfil):
            # only touch backup if original exists
            bakfil = self.attrib['backupname']
            if os.path.exists(bakfil):
                print 'backup_cache() deleting old backup %s' % bakfil
                os.remove(bakfil)

            print 'backup_cache() backing up %s as %s' % (cacfil,bakfil)
            # copyfile(src, dst)
            shutil.copyfile(cacfil, bakfil)

        return

    def _read(self, infile):
        """The core RAM to FLASH dump routine"""
        return _read_from_file(infile)

    def _write(self, outfile, data):
        """The core RAM to FLASH dump routine"""
        return _write_to_file(outfile, data)

