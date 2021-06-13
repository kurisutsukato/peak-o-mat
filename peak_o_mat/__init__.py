# set version string here
# if run from svn checkout, the svn revision will be picked up instead
    
import sys
import types
import numpy as np
from numbers import Number
import configparser
import os
import logging

from .appdata import configdir
from .symbols import pom_globals

from .misc import frozen_base, source_base, darwin_base
from .version import __version__

#if hasattr(sys, 'frozen') and sys.frozen == "windows_exe":
#    revpath = path.join(frozen_base, 'SVNREVISION')
#elif hasattr(sys, 'frozen') and sys.platform == 'darwin':
#    revpath = path.join(darwin_base, 'SVNREVISION')
#else:
#    revpath = path.join(source_base, 'SVNREVISION')

# def svn_revision():
#     #log.debug('sys.frozen: %d'%hasattr(sys, "frozen"))
#     if hasattr(sys, "frozen"):
#         #log.debug(path.abspath(__file__))
#         try:
#             mom_dir = path.normpath(path.join(__file__,'../../..'))
#             #log.debug(mom_dir)
#             rev = int(open(path.join(mom_dir,'SVNREVISION')).read())
#             #log.debug(rev)
#         except IOError:
#             tp,val,trace = sys.exc_info()
#             tb.print_exception(tp,val,trace)
#             return None
#         else:
#             return rev
#     else:
#         if sys.platform == 'win32':
#             try:
#                 #chdir(path.dirname(path.abspath(__file__)))
#                 with open(os.devnull, 'w') as devnull:
#                     out = subprocess.check_output(['subwcrev',path.dirname(path.abspath(__file__))], stderr=devnull)
#                 out = out.decode(sys.getfilesystemencoding()).split('\n')
#             except:
#                 pass
#             else:
#                 mat = re.match(r'.*\s(\d+)$',out[1].strip(),flags=re.MULTILINE)
#                 if mat is not None:
#                     return int(mat.groups()[0])
#                 return None
#         else:
#             try:
#                 with open(os.devnull, 'w') as devnull:
#                     svn_info = subprocess.check_output(('svn','info'), stderr=devnull).decode(sys.getfilesystemencoding())
#                 rev = (re.search(r"Revision:\s(\d+)", svn_info)).groups()[0]
#             except subprocess.CalledProcessError:
#                 pass
#             else:
#                 return int(rev)
#
#         try:
#             mom_dir = path.normpath(path.join(path.dirname(__file__),'..'))
#             rev = int(open(path.join(mom_dir,'SVNREVISION')).read())
#         except IOError:
#             tp,val,trace = sys.exc_info()
#             tb.print_exception(tp,val,trace)
#             return None
#         else:
#             return rev
#
#
#     return int(999999)


from . import lineshapes, lineshapebase

logger = logging.getLogger('pom')

def load_peaks():
    pkg = __import__('peak_o_mat',fromlist=['lineshapes'])
    mod = getattr(pkg, 'lineshapes')
    for name in dir(mod):
        sym = getattr(mod, name)
        if type(sym) == types.FunctionType:
            pom_globals.update({name: sym})

def load_userfunc():
    sys.path.append(configdir())
    try:
        mod = __import__('userfunc', fromlist=[])
    except ImportError:
        #traceback.print_exc()
        logger.info('no userfunc.py')
    else:
        for name in dir(mod):
            sym = getattr(mod, name)
            if type(sym) in [types.FunctionType, np.ufunc] or isinstance(sym, Number):
                pom_globals.update({name: sym})

defaultconfig = {'general':{'floating_point_is_comma':False,
                            'default_encoding':'utf-8',
                           },
                 'display':{'fast_max_pts':200,
                           'fast_display':False,
                           },
                 'encodings':{'utf-8':'','iso8859-1':'','iso2022-jp-2':''}
                 }

class Config(configparser.RawConfigParser):
    def write(self):
        p = os.path.join(configdir(),'peak-o-mat.cfg')
        try:
            super(Config, self).write(open(p,'w'))
        except:
            print('Cannot write peak-o-mat.cfg at {}'.format(os.path.dirname(p)))

configfile = os.path.join(configdir(),'peak-o-mat.cfg')
config = Config(allow_no_value=True)
config.read_dict(defaultconfig)

if os.path.exists(configfile):
    try:
        config.read(configfile)
    except IOError:
        print('unable to read configfile at: {}'.format(configfile))
    except configparser.ParsingError:
        print('syntax error in peak-o-mat.cfg, skipping')
else:
    print('no peak-o-mat.cfg in \'%s\''%configdir())
    config.write()

load_userfunc()
load_peaks()

