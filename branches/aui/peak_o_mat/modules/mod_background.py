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

"""New implementaion based on SNIP algorithm"""

import wx

from peak_o_mat import module,spec,misc

from scipy.interpolate import splrep,splev
from scipy.optimize import fmin_cobyla,leastsq,fmin

import numpy as np

from ..spec import Spec

def roll(a,d):
    if d>0:
        return np.pad(a,(d,0),'edge')[:-d]
    if d<0:
        return np.pad(a,(0,abs(d)),'edge')[abs(d):]

class Module(module.Module):
    title = 'Background'
    need_attention = True

    def __init__(self, *args):
        module.Module.__init__(self, __file__, *args)
    
    def init(self):
        self.niter = 1
        #self.xrc_cho_der.Bind(wx.EVT_UPDATE_UI, self.OnConstraintChecked)
        #self.xrc_cho_sign.Bind(wx.EVT_UPDATE_UI, self.OnConstraintChecked)

        #self.xrc_btn_find.Bind(wx.EVT_UPDATE_UI, self.OnSingleSelection)

        #self.xrc_btn_find.Bind(wx.EVT_BUTTON, self.OnFind)

        self.xrc_sl_iteration.Bind(wx.EVT_SLIDER, self.OnSlider)
        self.xrc_btn_create.Bind(wx.EVT_BUTTON, self.OnBtn)
        self.xrc_btn_substract.Bind(wx.EVT_BUTTON, self.OnBtn)

    def calc_background(self, dataset):
        x,y = dataset.xy

        v = np.log(np.log(np.sqrt(y+1)+1)+1)

        for p in range(1,self.niter+1):
            v = np.vstack((v, (roll(v,-p)+roll(v,+p))/2)).min(axis=0)
        tv = x,np.power(np.exp(np.exp(v)-1)-1,2)-1
        return tv

    def update_background(self):
        self.niter = self.xrc_sl_iteration.Value
        sel = self.controller.selection
        if sel is not None:
            p,s = sel
            if len(s) == 1:
                dataset = self.controller.project[p][s[0]]
                x,y = self.calc_background(dataset)
                self.plotme = 'Line', spec.Spec(x,y,'bg_{}'.format(dataset.name))
                self.controller.update_plot()

    def OnBtn(self, evt):
        p,s = self.controller.selection
        if len(s) == 1:
            if self.xrc_chk_group.IsChecked():
                rng = list(range(len(self.controller.project[p])))
            else:
                rng = s
            for s in rng:
                dataset = self.controller.project[p][s]
                x,y = self.calc_background(dataset)
                if evt.GetEventObject() == self.xrc_btn_substract:
                    dataset -= y
                    self.controller.update_plot()
                else:
                    self.controller.add_set(spec.Spec(x,y,'bg_{}'.format(dataset.name)))

    def OnSlider(self, evt):
        if self.xrc_sl_iteration.Value != self.niter:
            self.niter = self.xrc_sl_iteration.Value
            self.update_background()

    def selection_changed(self):
        print('mod_background.selection_changed')
        self.update_background()

    def page_changed(self, me):
        #TODO: hat nichts mehr mit "page changed" zu tun, sondern mit pane close
        if me:
            self.update_background()
        else:
            self.plotme = None
            self.controller.update_plot()

