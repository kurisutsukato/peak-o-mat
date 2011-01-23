#!/usr/bin/python

##     Copyright (C) 2003 Christian Kristukat (ckkart@hoc.net)     
##     This program is free software; you can redistribute it and modify
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

#import odr
# this has to be the first import due to some strange error on
# windows with cygwin-mingw32 built odr package

import wx

import sys, os
import imp
import traceback

from controller import Controller, Interactor
from project import Project
from mainframe import MainFrame

def load_userfunc():
    pomdir = os.path.join(os.path.expanduser('~'),'.peak-o-mat')
    sys.path.append(pomdir)
    if os.path.exists(os.path.join(pomdir,'userfunc.py')):
        print 'loading user funcs from %s/userfunc.py'%pomdir
        try:
            f,fname,descr = imp.find_module('userfunc')
            mod = imp.load_module('userfunc', f, fname, descr)
        except:
            tpe, val, tb = sys.exc_info()
            traceback.print_tb(tb)
            print tpe, val
        else:
            print dir(mod)
            import __builtin__
            for name in dir(mod):
                if name[0] != '_' and name != 'peaks':
                    # ugly hack to allow custom functions in userfunc.py
                    setattr(__builtin__, name, getattr(mod,name))

def run():
    load_userfunc()
    
    Controller(Project(),MainFrame(),Interactor())
        
if __name__ == '__main__':
    run()

