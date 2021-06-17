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

"""\
Shell module

This module provides a standard python shell with some of peak-o-mat's
data and control structure exposed.  It is easy to crash the
application when manipulating its internals, so be warned.

sync():   Sync   the  display   with   the   current   state  of   the
application. Not all changes which you can do through the shell access
are immediately  visible, e.g. changing set names,  adding set trafos,
etc. In order to update the view call 'sync()'.

add_set(spec, plotnum=None):  Add 'spec' as  a new set to  the current
plot or to plot number 'plotnum'.

   spec:    Instance of peak_o_mat.spec.Dataset.
   plotnum: Index of the plot to which the new set will be
            added. If omitted, the last plot will be used.

add_plot(): Create a new empty plot.

project: a reference to the project data, i.e. a list containing the
plots, which itselves are list objects containing the sets.

aset: a reference to the active set.

model: a reference to the current model.

Dataset(x,  y, name): class  (peak_o_mat.spec.Dataset)  representing a  peak_o_mat
dataset
   x: x-data
   y: y-data
   name: name of dataset

"""

from wx.py import shell
import wx
from pubsub import pub as Publisher

from tempfile import mkstemp
from os import unlink, fdopen


def intro():
    print(__doc__)

from peak_o_mat import module

class Locals(dict):
    autocall = []
    def __getitem__(self, name):
        #if type(dict.__getitem__(self, name)) == func:
        #    return dict.__getitem__(self, name)()
        if name in self.autocall:
            return dict.__getitem__(self, name)()
        else:
            return dict.__getitem__(self, name)

    def add(self, name, val, autocall=False):
        self[name] = val
        if autocall:
            self.autocall.append(name)

    def __setitem__(self, name, val):
        if name in self.autocall:
            raise Exception('overwriting \'%s\' not allowed'%name)
        else:
            dict.__setitem__(self,name,val)
            
class XRCModule(module.XRCModule):
    title = 'Shell'

    def __init__(self, *args):
        module.XRCModule.__init__(self, __file__, *args)
    
    def init(self):
        locs = Locals(locals())
        locs.add('add_plot', self.controller.add_plot)
        locs.add('add_set', self.controller.add_set)
        locs.add('project', self.project)
        locs.add('canvas', self.controller.view.canvas)
        def _get_model():
            return self.controller.fit_controller.model
        locs.add('model', _get_model, True)
        def _update_view():
            self.controller.update_tree()
            self.controller.update_plot()
        locs.add('sync', _update_view)
        def _get_active_set():
            return self.controller.active_set
        locs.add('aset', _get_active_set, True)
        locs.add('intro', intro, False)

        sh = shell.Shell(self.view, -1, introText='peak-o-mat - shell module\ntype intro() to read a short introduction', showInterpIntro=False, locals=locs)
        sh.push('from peak_o_mat.spec import Dataset', True)
        sh.push('import numpy as np', True)
        sh.autoCallTip = False
        sh.autoComplete = False
        self.sh = sh

        self.xmlres.AttachUnknownControl('xrc_win_shell', sh)

        self.view.GetParent().Fit()

