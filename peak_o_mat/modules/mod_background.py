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

"""New implementation based on SNIP algorithm"""

import wx
from pubsub import pub

from peak_o_mat import module, spec, misc

from scipy.sparse.linalg import spsolve
from scipy import sparse

from scipy.interpolate import splrep, splev
from scipy.optimize import fmin_cobyla, leastsq, fmin

import numpy as np

from ..spec import Spec


def roll(a, d):
    if d > 0:
        return np.pad(a, (d, 0), 'edge')[:-d]
    if d < 0:
        return np.pad(a, (0, abs(d)), 'edge')[abs(d):]


def onedigit(a):
    digits = abs(min(0, int(np.log10(a)) - 1))
    val = round(a, digits)
    return '{1:.{0}f}'.format(digits, val)


class XRCModule(module.XRCModule):
    title = 'Background'
    need_attention = True

    def __init__(self, *args):
        module.XRCModule.__init__(self, __file__, *args)

    def init(self):
        self.page = 0

        self.xrc_sl_SNIP_iteration.Bind(wx.EVT_SLIDER, self.OnSliderSNIP)
        self.xrc_btn_create.Bind(wx.EVT_BUTTON, self.OnBtn)
        self.xrc_btn_substract.Bind(wx.EVT_BUTTON, self.OnBtn)

        self.xrc_sl_ALQ_iter.Bind(wx.EVT_SLIDER, self.OnSliderALQ)
        self.xrc_sl_ALQ_lam.Bind(wx.EVT_SLIDER, self.OnSliderALQ)
        self.xrc_sl_ALQ_p.Bind(wx.EVT_SLIDER, self.OnSliderALQ)

        self.xrc_notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnNBChanged)

        self.update_values()

    def calc_background_ALQ(self, ds):
        niter = int(self.xrc_sl_ALQ_iter.Value)
        lam = np.power(10.0, self.xrc_sl_ALQ_lam.Value/10.0)
        p = np.power(10.0, self.xrc_sl_ALQ_p.Value/10.0)

        L = len(ds)
        w = np.ones(L)
        D = sparse.diags([1, -2, 1], [0, -1, -2], shape=(L, L-2))
        DTD = D.dot(D.T)
        W = sparse.spdiags(w, 0, L, L)

        for n in range(niter):
            W.setdiag(w)
            Z = W + lam * DTD
            z = spsolve(Z, w*ds.y)
            w = p * (ds.y > z) + (1-p) * (ds.y < z)

        return ds.x, z

    def calc_background_SNIP(self, dataset):
        niter = self.xrc_sl_SNIP_iteration.Value
        x, y = dataset.xy

        v = np.log(np.log(np.sqrt(y + 1) + 1) + 1)
        l = v.shape[0]

        # for p in range(1,self.niter+1):  # much better results with reverse indexing!!
        for p in range(niter, 0, -1):
            v[p:l - p] = np.minimum(v[p:l - p], (roll(v, -p)[p:l - p] + roll(v, +p)[p:l - p]) / 2)
        v = np.power(np.exp(np.exp(v) - 1) - 1, 2) - 1
        return x, v

    def update_background(self):
        sel = self.controller.selection
        if sel is not None:
            p, s = sel
            if len(s) == 1:
                dataset = self.controller.project[p][s[0]]
                if self.page == 0:
                    x, y = self.calc_background_SNIP(dataset)
                elif self.page == 1:
                    x, y = self.calc_background_ALQ(dataset)
                else:
                    return
                self.plotme = 'Line', spec.Spec(x, y, 'bg_{}'.format(dataset.name))
                pub.sendMessage((self.instid, 'updateplot'))

    def OnNBChanged(self, evt):
        self.page = evt.GetSelection()
        self.update_background()

    def OnBtn(self, evt):
        p, s = self.controller.selection
        if len(s) == 1:
            if self.xrc_chk_group.IsChecked():
                rng = list(range(len(self.controller.project[p])))
            else:
                rng = s
            for s in rng:
                dataset = self.controller.project[p][s]
                if self.page == 0:
                    x, y = self.calc_background_SNIP(dataset)
                elif self.page == 1:
                    x, y = self.calc_background_ALQ(dataset)
                else:
                    raise Exception('should not happen')
                if evt.GetEventObject() == self.xrc_btn_substract:
                    # TODO: das hatte mal nicht funktioniert im trunk
                    dataset -= y
                    pub.sendMessage((self.instid, 'updateplot'))
                else:
                    self.controller.add_set(spec.Spec(x, y, 'bg_{}'.format(dataset.name)))

    def update_values(self):
        self.xrc_lab_ALQ_iter.Label = str(self.xrc_sl_ALQ_iter.Value)
        val = float(self.xrc_sl_ALQ_lam.Value)/10.0
        self.xrc_lab_ALQ_lam.Label = onedigit(val)
        val = np.power(10.0, float(self.xrc_sl_ALQ_p.Value) / 10.0)
        self.xrc_lab_ALQ_p.Label = onedigit(val)

    def OnSliderSNIP(self, evt):
        self.update_background()

    def OnSliderALQ(self, evt):
        self.update_values()
        self.update_background()

    def selection_changed(self):
        if self.visible:
            self.update_background()

    def OnClose(self, evt):
        self.focus_changed()

    def focus_changed(self, newfocus=None):
        if newfocus != self:
            self.plotme = None
            pub.sendMessage((self.instid, 'updateplot'))
        else:
            self.update_background()
