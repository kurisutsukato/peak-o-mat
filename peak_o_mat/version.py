

# set version string here
# if run from svn checkout, the svn revision will be picked up instead

from os import path, chdir
import sys

import logging as log

import subprocess
import re

from .misc import frozen_base, source_base, darwin_base

if hasattr(sys, 'frozen') and sys.frozen == "windows_exe":
    revpath = path.join(frozen_base, 'SVNREVISION')
elif hasattr(sys, 'frozen') and sys.platform == 'darwin':
    revpath = path.join(darwin_base, 'SVNREVISION')
else:
    revpath = path.join(source_base, 'SVNREVISION')

def svn_revision():
    log.debug('sys.frozen: %d'%hasattr(sys, "frozen"))
    if hasattr(sys, "frozen"):
        log.debug(path.abspath(__file__))
        try:
            mom_dir = path.normpath(path.join(__file__,'../../..'))
            log.debug(mom_dir)
            rev = int(open(path.join(mom_dir,'SVNREVISION')).read())
            log.debug(rev)
        except IOError:
            log.debug('frozen SVNREVISION not found')
            return None
        else:
            return rev
    else:
        try:
            out = subprocess.check_output(['subwcrev',path.dirname(path.abspath(__file__))], shell=False)
            out = out.decode(sys.getdefaultencoding())
            out = out.split('\n')
        except (OSError,subprocess.CalledProcessError):
            log.debug('subwcrev exectable not found')
        else:
            mat = re.match(r'.*\s(\d+)$',out[1].strip(),flags=re.MULTILINE)
            if mat is not None:
                return int(mat.groups()[0])
            return None

        try:
            svn_info = subprocess.check_output(('svnversion')).decode('ascii')
        except (OSError,subprocess.CalledProcessError):
            log.debug('svn exectable not found')
            return None
        else:
            try:
                a = svn_info.strip().split(':')[-1]
                rev = re.match(r"(\d+).*", a).group(1)
            except AttributeError:
                return None
            return int(rev)
    return None

from os.path import exists, normpath, join, dirname

svnrevfile = normpath(join(dirname(__file__),'..','SVNREVISION'))

rev = svn_revision()
if rev is not None:
    __version__ = str(rev)
elif exists(svnrevfile):
    __version__ = open(svnrevfile).read()
else:
    __version__ = '2.0a1'



