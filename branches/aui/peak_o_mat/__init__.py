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

from . import lineshapes, lineshapebase

logger = logging.getLogger('pom')


def load_peaks():
    pkg = __import__('peak_o_mat', fromlist=['lineshapes'])
    mod = getattr(pkg, 'lineshapes')
    for name in dir(mod):
        sym = getattr(mod, name)
        if isinstance(sym, types.FunctionType):
            pom_globals.update({name: sym})

def aa_load_userfunc():
    #TODO: remove
    sys.path.append(configdir())
    try:
        mod = __import__('userfunc', fromlist=[])
    except ImportError:
        # traceback.print_exc()
        logger.info('no userfunc.py')
    else:
        for name in dir(mod):
            sym = getattr(mod, name)
            if type(sym) in [types.FunctionType, np.ufunc] or isinstance(sym, Number):
                pom_globals.update({name: sym})


defaultconfig = {'general': {'floating_point_is_comma': False,
                             'default_encoding': 'utf-8',
                             'userfunc_dir': os.path.join(configdir(), 'userfunc')
                             },
                 'display': {'fast_max_pts': 200,
                             'fast_display': False,
                             },
                 'encodings': {'utf-8': '', 'iso8859-1': '', 'iso2022-jp-2': ''}
                 }


class Config(configparser.RawConfigParser):
    def write(self):
        p = os.path.join(configdir(), 'peak-o-mat.cfg')
        try:
            super(Config, self).write(open(p, 'w'))
        except:
            print('Cannot write peak-o-mat.cfg at {}'.format(os.path.dirname(p)))


configfile = os.path.join(configdir(), 'peak-o-mat.cfg')
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
    print('no peak-o-mat.cfg in \'%s\'' % configdir())
    config.write()

#load_userfunc()
load_peaks()

pom_tmp = {}

def add_ls(name, **kwargs):
    pom_tmp.update({name: lineshapebase.LineShape(**kwargs)})

