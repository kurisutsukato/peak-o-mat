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
BAtchfit
"""

import sys

import wx
from wx.lib.pubsub import pub as Publisher

from peak_o_mat import module,spec,misc,controls

from scipy.interpolate import splrep,splev
from scipy.optimize import fmin_cobyla,leastsq,fmin
import numpy as np
from peak_o_mat.symbols import pom_globals

class Module(module.Module):
    title = 'Batch Fit'

    def __init__(self, *args):
        module.Module.__init__(self, __file__, *args)
    
    def init(self):
        self.update_from_model(self.controller)

    def update_from_model(self, controller):
        sel = controller.selection
        if sel is not None:
            pl,ds = sel
            p = controller.project

            self.xrc_cho_base.Clear()
            self.xrc_cho_base.AppendItems(['none'])


    def page_changed(self, state):
        print(state)

    def selection_changed(self):
        pass
