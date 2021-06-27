##     Copyright (C) 2003 Christian Kristukat (ckkart@hoc.net)

##     This program is free software; you can redistribute it and/or modify
##     it under the terms of the GNU General Public License as published by
##     the Free Software Foundation; either version 2 of the License, or
##     (at your option) any later version.

##     This program is distributed in the hope that it will be useful,
##     but WITHOUT ANY WARRANTY; without even the implied warranty of
##     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##     GNU General Public License for more details.

##     You should have received a copy of the GNU General Public License
##     along with this program; if not, write to the Free Software
##     Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import sys
import os

import numpy as np
from numpy import inf, nan

import re

frozen_base = os.path.dirname(sys.executable)
source_base = os.path.split(os.path.dirname(__file__))[0]
darwin_base = os.path.join(frozen_base, '..', 'Resources')


def basepath(*joinwith):
    if hasattr(sys, "frozen") and sys.frozen in ['windows_exe', 'console_exe']:
        p = os.path.join(frozen_base, *joinwith)
    elif hasattr(sys, "frozen") and sys.platform == "darwin":
        p = os.path.join(darwin_base, *joinwith)
    else:
        p = os.path.join(source_base, *joinwith)
    return p


def wildcards():
    from .fio import loaders
    return loaders.wildcards


_cwd = None


def cwd():
    global _cwd
    if _cwd is not None:
        while True:
            if os.path.exists(_cwd):
                return _cwd
            _cwd = os.path.split(_cwd)[0]
    try:
        path = os.getcwd()
    except:
        path = os.path.expanduser('~')
    return path


def set_cwd(cwd):
    global _cwd
    if cwd is not None:
        _cwd = os.path.split(os.path.abspath(cwd))[0]


_special_numbers = dict([('-1.#INF', -inf), ('1.#INF', inf),
                         ('-1.#IND', nan), ('-1.#IND00', nan),
                         ('1.#QNAN', nan), ('1.#QNAN0', -nan)])


def atof(x):
    try:
        tmp = np.float32(x)
    except ValueError:
        tmp = np.nan
    return tmp


def str2array(arg):
    data = [re.split(r'\s+|;|,', line.strip()) for line in arg.strip().split('\n')]
    try:
        data = np.array(data, dtype=float)
    except ValueError:
        arg = arg.replace(',', '.')
        data = [re.split(r'\s+|;|,', line.strip()) for line in arg.strip().split('\n')]
        data = np.array(data, dtype=float)
    return None, data


class PomError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


if __name__ == '__main__':
    print(basepath('a', 'b'))
