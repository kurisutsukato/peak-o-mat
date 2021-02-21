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
Eval Module
"""

import sys

import wx
from pubsub import pub

import numpy as np
from scipy.special import comb as nOk
from scipy.interpolate import Akima1DInterpolator

from peak_o_mat import module,spec,controls,misc_ui

from peak_o_mat.symbols import pom_globals

#Mtk = lambda n, t, k: t**(k)*(1-t)**(n-k)*nOk(n,k)
Mtk = lambda n, t, k: np.power(t,k)*np.power(1-t,n-k)*nOk(n,k)
bezierM = lambda ts,l: np.array([[Mtk(l-1,t,k) for k in range(l)] for t in ts])


class DummyEvent:
    def __init__(self, obj):
        obj.SetValue(True)
        self.obj = obj
    def GetEventObject(self):
        return self.obj

class XRCModule(module.XRCModule):
    title = 'Evaluate'
    need_attention = True
    
    def __init__(self, *args):
        module.XRCModule.__init__(self, __file__, *args)
        self.plot = None
        self.has_attention = False

    def init(self):
        self.xrc_btn_bez_load.Disable()
        self.xrc_btn_bez_load.Bind(wx.EVT_BUTTON, self.OnAnchor)
        self.xrc_btn_place_handles.Bind(wx.EVT_TOGGLEBUTTON, self.OnBtnPlaceHandles)
        pub.subscribe(self.OnCanvasMode, ('canvas','newmode'))

        self.xrc_btn_eq_load.Bind(wx.EVT_BUTTON, self.OnLoad)

        self.xrc_txt_eq_range_from.SetValidator(controls.InputValidator(controls.FLOAT_ONLY))
        self.xrc_txt_eq_range_to.SetValidator(controls.InputValidator(controls.FLOAT_ONLY))
        #self.xrc_txt_eq.SetValidator(controls.InputValidator())

        self.handles = np.zeros((0,2))

    def sync_controls(self, plot):
        self.xrc_cmb_eq_fromset.Clear()
        self.xrc_cmb_bez_fromset.Clear()
        if plot is not None:
            l = len(self.project[plot])
            if l > 0:
                self.xrc_cmb_eq_fromset.AppendItems(['s%d'%x for x in range(len(self.project[plot]))])
                self.xrc_cmb_eq_fromset.SetSelection(0)
                self.xrc_cmb_eq_fromset.Enable(True)
                self.xrc_cb_eq_fromset.Enable(True)

                self.xrc_cmb_bez_fromset.AppendItems(['s%d'%x for x in range(len(self.project[plot]))])
                self.xrc_cmb_bez_fromset.SetSelection(0)
                self.xrc_cmb_bez_fromset.Enable(True)
                self.xrc_cb_bez_fromset.Enable(True)
            else:
                self.xrc_cmb_eq_fromset.Enable(False)
                self.xrc_cb_eq_fromset.Value = False
                self.xrc_cb_eq_range.Value = True
                self.xrc_cb_eq_fromset.Enable(False)

                self.xrc_cmb_bez_fromset.Enable(False)
                self.xrc_cb_bez_fromset.Value = False
                self.xrc_cb_bez_pts.Value = True
                self.xrc_cb_bez_fromset.Enable(False)
        else:
            self.xrc_cmb_eq_fromset.Enable(False)
            self.xrc_cb_eq_fromset.Value = False
            self.xrc_cb_eq_range.Value = True
            self.xrc_cb_eq_fromset.Enable(False)
            self.xrc_cmb_bez_fromset.Enable(False)
            self.xrc_cb_bez_fromset.Value = False
            self.xrc_cb_bez_pts.Value = True
            self.xrc_cb_bez_fromset.Enable(False)

    def obtain_focus(self):
        if not self._has_attention:
            pub.sendMessage((self.instid, 'module', 'focuschanged'), newfocus=self.title)

    def focus_changed(self, newfocus=None):
        if newfocus != self.title:
            self.plotme = None
            self.leave()
            pub.sendMessage((self.instid, 'updateplot'))
        else:
            self._has_attention = True

    def selection_changed(self):
        try:
            plot,sel = self.controller.selection
            if len(sel) == 0:
                raise Exception
        except:
            self.plot = None
        else:
            if plot != self.plot:
                self.leave()
            self.plot = plot
        self.sync_controls(self.plot)

    def leave(self):
        try:
            self.controller.view.canvas.Unbind(misc_ui.EVT_HANDLES_CHANGED)
        except KeyError:
            pass
        self.handles = np.zeros((0,2))
        self.controller.view.canvas.set_handles(self.handles)
        self.xrc_btn_bez_load.Disable()
        self.xrc_btn_place_handles.SetValue(False)
        self.controller.view.canvas.state.restore_last()
        pub.sendMessage((self.instid, 'updateplot'))

    def OnCanvasMode(self, mode):
        if mode != 'handle':
            self.xrc_btn_place_handles.SetValue(False)

    def OnBtnPlaceHandles(self, evt):
        self.obtain_focus()

        if self.xrc_btn_place_handles.GetValue():
            self.controller.view.canvas.set_handles(self.handles)
            self.controller.view.canvas.state.set('handle','xy')
            self.controller.view.canvas.Bind(misc_ui.EVT_HANDLES_CHANGED, self.OnHandles)
        else:
            self.handles = np.zeros((0,2))
            self.controller.view.canvas.set_handles(self.handles)
            self.controller.view.canvas.state.set(None)
            self.controller.update_plot()

    def OnHandles(self, evt):
        handles = evt.handles
        if handles.ndim < 2:
            return
        if handles.ndim == 2 and len(handles) > 1:
            v = np.linspace(0,1,20)
            M = bezierM(v, len(handles))
            points = M@handles
            evx, evy = points.T
            self.controller.plot(floating=spec.Spec(evx,evy,'{:d} pt. bezier'.format(len(handles))))
            self.xrc_btn_bez_load.Enable()

            #handles = handles.take(np.argsort(handles[:,0]),0)
            #xh,yh = np.transpose(handles)
            #evx = np.linspace(xh[0], xh[-1], 100)
            #if len(xh) > 2:
            #    aki = Akima1DInterpolator(xh,yh)
            #    evy = aki(evx)
            #else:
            #    a = (yh[1]-yh[0])/(xh[1]-xh[0])
            #    b = yh[1]-a*xh[1]
            #    evy = evx*a+b
            #self.controller.plot(floating=spec.Spec(evx,evy,'{:d} pt. bezier'.format(len(handles))))
            #self.xrc_btn_bez_load.Enable()

            #m = len(x)
            #sp = splrep(x, y, k=min(handles.shape[0]-1,3), s=m+np.sqrt(2*m))
            #evx = np.linspace(x[0],x[-1],100)
            #evy = splev(evx,sp)
            #self.spline = sp
            #self.controller.plot(floating=spec.Spec(evx,evy,'spline'))
        self.handles = handles

    def OnAnchor(self, evt):
        self.obtain_focus()
        pts = int(self.xrc_spn_bez_pts.GetValue())

        if self.xrc_cb_bez_pts.Value:
            v = np.linspace(0.0,1.0,pts)
        elif self.xrc_cb_bez_fromset.Value:
            s = self.controller.active_plot[self.xrc_cmb_bez_fromset.GetSelection()]
            #v = self.controller.active_plot[s].x
            v = np.linspace(0.0,1.0,len(s))

        M = bezierM(v, len(self.handles))
        points = M@self.handles
        x, y = points.T
        if self.xrc_cb_bez_pts.Value:
            set_bez = spec.Spec(x,y,'{:d} pt. Bezi\u00E9r'.format(len(self.handles)))
        elif self.xrc_cb_bez_fromset.Value:
            tmp = spec.Spec(x,y,'tmp')
            tmp = s*0+tmp
            set_bez = tmp
            set_bez.name = '{:d} pt. Bezi\u00E9r'.format(len(self.handles))

        self.controller.add_set(set_bez)
        self.xrc_btn_bez_load.Disable()
        self.handles = np.zeros((0,2))
        self.xrc_btn_place_handles.SetValue(False)
        self.controller.view.canvas.state.set(None)
        self.controller.update_plot()
        
    def OnLoad(self, evt):
        self.obtain_focus()

        mode = int(self.xrc_cb_eq_fromset.GetValue())

        if mode == 0 and not self.xrc_pan_eq.Validate():
            return

        eq = self.xrc_txt_eq.GetValue()
         
        if mode == 0:
            xmin = float(self.xrc_txt_eq_range_from.GetValue())
            xmax = float(self.xrc_txt_eq_range_to.GetValue())
            pts = int(self.xrc_spn_eq_range_pts.GetValue())
            x = np.linspace(xmin,xmax,pts)
        elif mode == 1:
            s = self.xrc_cmb_eq_fromset.GetSelection()
            x = self.controller.active_plot[s].x
        try:
            y = eval(eq,pom_globals,{'x':x})
        except:
            tp,val,tb = sys.exc_info()
            self.message(str(val))
            return
        if np.asarray(y).shape != x.shape:
            self.message('The expression\'s result must have shape %s. Probably \'x\' is missing in the expression.'%str(x.shape), blink=False)
        else:
            self.controller.add_set(spec.Spec(x,y,eq))
            self.controller.update_plot()
