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
from wx.lib.pubsub import pub as Publisher

from peak_o_mat import module,spec,misc,controls

from scipy.interpolate import splrep,splev
from scipy.optimize import fmin_cobyla,leastsq,fmin
import numpy as N

class DummyEvent:
    def __init__(self, obj):
        obj.SetValue(True)
        self.obj = obj
    def GetEventObject(self):
        return self.obj

class Module(module.Module):
    title = 'Evaluate'

    def __init__(self, *args):
        module.Module.__init__(self, __file__, *args)
    
    def init(self):
        self.xrc_btn_anchor.Disable()
        self.xrc_btn_anchor.Bind(wx.EVT_BUTTON, self.OnAnchor)
        self.xrc_btn_place_handles.Bind(wx.EVT_TOGGLEBUTTON, self.OnPlaceHandles)
        Publisher.subscribe(self.OnCanvasMode, ('canvas','newmode'))

        self.xrc_btn_load.Bind(wx.EVT_BUTTON, self.OnLoad)
        self.xrc_cb_range.Bind(wx.EVT_CHECKBOX, self.OnCheck)
        self.xrc_cb_fromset.Bind(wx.EVT_CHECKBOX, self.OnCheck)

        self.xrc_txt_range_from.SetValidator(controls.InputValidator(controls.FLOAT_ONLY))
        self.xrc_txt_range_to.SetValidator(controls.InputValidator(controls.FLOAT_ONLY))
        self.xrc_txt_range_pts.SetValidator(controls.InputValidator(controls.DIGIT_ONLY))
        self.xrc_txt_eq.SetValidator(controls.InputValidator())

        self.xrc_txt_spline_pts.SetValidator(controls.InputValidator(controls.DIGIT_ONLY))

        self.OnCheck(DummyEvent(self.xrc_cb_range))
        
        self.handles = N.zeros((0,2))

    def sync_controls(self, plot):
        self.xrc_cmb_fromset.Clear()
        if plot is not None:
            l = len(self.project[plot])
            if l > 0:
                self.xrc_cb_fromset.Enable()
                self.xrc_cmb_fromset.AppendItems(['s%d'%x for x in range(len(self.project[plot]))])
                self.xrc_cmb_fromset.SetSelection(0)
        else:
            self.xrc_cb_range.SetValue(True)
            print self.xrc_cb_range.GetValue()
            if not self.xrc_cb_range.GetValue():
                self.OnCheck(DummyEvent(self.xrc_cb_range))
            self.xrc_cb_fromset.Disable()
        
    def OnCheck(self, evt):
        source = evt.GetEventObject()
        
        panels = [self.xrc_pan_range, self.xrc_pan_fromset]
        cbs = [self.xrc_cb_range, self.xrc_cb_fromset]
        enable = source.GetValue()
        idx = cbs.index(source)

        if enable:
            panels[idx].Enable()
            panels[1-idx].Disable()
            cbs[1-idx].SetValue(False)
            self.xrc_btn_load.Enable()
        else:
            panels[idx].Disable()
            self.xrc_btn_load.Disable()
        self.panel.Refresh()
        
    def page_changed(self, state):
        if not state:
            self.leave()
        else:
            try:
                self.plot,sel = self.controller.selection
            except:
                self.plot = None
            self.sync_controls(self.plot)
                
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
            self.controller.view.canvas.Unbind(misc.EVT_HANDLES_CHANGED)
        except KeyError:
            pass
        self.handles = N.zeros((0,2))
        self.controller.view.canvas.set_handles(self.handles)
        self.xrc_btn_anchor.Disable()
        self.xrc_btn_place_handles.SetValue(False)
        self.controller.view.canvas.RestoreLastMode()
        self.controller.update_plot()

    def OnCanvasMode(self, msg):
        mode = msg.data
        if mode != 'handle':
            self.xrc_btn_place_handles.SetValue(False)

    def OnPlaceHandles(self, evt):
        if self.xrc_btn_place_handles.GetValue():
            self.controller.view.canvas.set_handles(self.handles)
            self.controller.view.canvas.SetMode('handle')
            self.controller.view.canvas.Bind(misc.EVT_HANDLES_CHANGED, self.OnHandles)
        else:
            self.controller.view.canvas.SetMode(None)
            
    def OnHandles(self, evt):
        handles = N.asarray(evt.handles)
        if handles.shape[0] < 2:
            return
        if handles.shape[0] > 1:
            self.xrc_btn_anchor.Enable()
            handles = handles.take(N.argsort(handles[:,0]),0)
            x,y = N.transpose(handles)
            sp = splrep(x, y, k=min(handles.shape[0]-1,3), s=10)
            evx = N.linspace(x[0],x[-1],100)
            evy = splev(evx,sp)
            self.spline = sp
            self.controller.plot(floating=spec.Spec(evx,evy,'spline'))
        self.handles = handles

    def OnAnchor(self, evt):
        if self.xrc_pan_spline.Validate():
            pts = int(self.xrc_txt_spline_pts.GetValue())
            x = N.linspace(self.handles[0,0],self.handles[-1,0],pts)
            y = splev(x,self.spline)
            self.controller.add_set(spec.Spec(x,y,'%dpts_spline'%pts))
            self.xrc_btn_anchor.Disable()
            self.handles = N.zeros((0,2))
            self.xrc_btn_place_handles.SetValue(False)
            self.controller.view.canvas.SetMode(None)
            self.controller.update_plot()
        
    def OnLoad(self, evt):
        mode = int(self.xrc_cb_fromset.GetValue())
        pan = [self.xrc_pan_range, self.xrc_pan_fromset][mode]

        if not pan.Validate():
            return

        eq = self.xrc_txt_eq.GetValue()
        glb = globals()
        glb.update({'N':N})
        glb.update(N.__dict__)
        
        if mode == 0:
            xmin = float(self.xrc_txt_range_from.GetValue())
            xmax = float(self.xrc_txt_range_to.GetValue())
            pts = int(self.xrc_txt_range_pts.GetValue())
            x = N.linspace(xmin,xmax,pts)
        elif mode == 1:
            set = self.xrc_cmb_fromset.GetSelection()
            x = self.controller.active_plot[set].x
        try:
            y = eval(eq,glb,locals())
        except:
            tp,val,tb = sys.exc_info()
            self.message(str(val))
            return
        self.controller.add_set(spec.Spec(x,y,eq))
        self.controller.update_plot()
            
        
        
