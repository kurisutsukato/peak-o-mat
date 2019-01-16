"""
'Data operations' can be either an operation between the y-values
of different sets or a transformation of either the x- or y-values
of one set. In the former case, a new set is created, in the
latter case the transformation is attached to the current set,
which can be undone via the 'remove trafos' popup menu item, which
opens upon pressing right-mouse on the tree items. The sets can be
referenced by the string 'sX', where X is the set number shown in
the tree view on the right side. Only operations between sets of
the same plot are possible.  The x-/y-transformation operations
are applied to every set of the current selection.

examples of valid expressions are:
x+10
1/y
log10(y)
(s0+s1)/2
sum([s1,s2,s3])
etc.
"""

import wx
from wx.lib.pubsub import pub
import wx.dataview as dv

import re
import sys
from operator import add

from peak_o_mat import module, controls, spec

import numpy as np
from scipy.interpolate import splrep, splev 

from peak_o_mat.symbols import pom_globals
from functools import reduce

class curry:
    def __init__(self, fun, *args, **kwargs):
        self.fun = fun
        self.pending = args[:]
        self.kwargs = kwargs.copy()

    def __call__(self, *args, **kwargs):
        if kwargs and self.kwargs:
            kw = self.kwargs.copy()
            kw.update(kwargs)
        else:
            kw = kwargs or self.kwargs

        return self.fun(*(self.pending + args), **kw)

trafomap = {'xrc_btn_A2eV' :'12398.52/x',
            'xrc_btn_A2cm' :'1.0/x*1e8',
            'xrc_btn_eV2cm' : 'x*8.065478*1000',
            'xrc_btn_cm2eV' : 'x/8.065478/1000'}

class Module(module.Module):
    title = 'Transformations'
    
    def __init__(self, *args):
        module.Module.__init__(self, __file__, *args)

        self.funcs = [self.op_general,
                      self.op_predef,
                      self.op_interpolate,
                      self.op_average,
                      self.op_waverage,
                      self.op_sgfilter,
                      self.op_splinesmooth,
                      self.op_derivate,
                      self.op_normalise,
                      self.op_avg_sel,
                      self.op_raman,
                      self.op_raman_inv]

        #assert self.parent_view is not None

    def init(self):
        self.xmlres.AttachUnknownControl('xrc_op', controls.HistTextCtrl(self.panel, -1, ''))
        self.xrc_op.GetParent().SetMinSize(self.xrc_op.GetMinSize())

        ctrls = ['xrc_op',
                 'xrc_pan_predef',
                 'xrc_btn_interpolate',
                 'xrc_btn_average',
                 'xrc_btn_waverage',
                 'xrc_btn_sg',
                 'xrc_btn_spl',
                 'xrc_btn_derivate',
                 'xrc_btn_normalise',
                 'xrc_btn_avg_sel',
                 'xrc_btn_nm2cm',
                 'xrc_btn_cm2nm']
        
        evts = [wx.EVT_TEXT_ENTER]+[wx.EVT_BUTTON]*(len(ctrls)-1)

        for c,e,f in zip(ctrls,evts,self.funcs):
            assert getattr(self, c) is not None
            getattr(self, c).Bind(e, curry(self.OnOp, f))
            
        self.xrc_txt_nm.SetValidator(controls.InputValidator(controls.FLOAT_ONLY))
        self.xrc_txt_cm.SetValidator(controls.InputValidator(controls.FLOAT_ONLY))
        self.xrc_txt_sgwindow.SetValidator(controls.InputValidator(controls.INT_ONLY))
        self.xrc_txt_sgorder.SetValidator(controls.InputValidator(controls.INT_ONLY))

        self.xrc_txt_wavg_step.SetValidator(controls.InputValidator(controls.FLOAT_ONLY))
        self.xrc_txt_wavg_width.SetValidator(controls.InputValidator(controls.FLOAT_ONLY))

        self.xrc_btn_repeat.Bind(wx.EVT_BUTTON, self.OnRepeat)

    def OnRepeat(self, evt):
        if self.do_op(self.xrc_op.last_op):
            pub.sendMessage((self.view_id, 'changed'))
            self.controller.update_plot()
    
    def OnOp(self, func, evt):
        self.controller._busy = True
        name = evt.GetEventObject().GetName()
        if func(name, *self.controller.selection):
            self.controller.update_plot()
            pub.sendMessage((self.view_id, 'changed'))
        self.controller._busy = False

    def op_raman(self, name, plot, sel):
        if not self.xrc_txt_nm.GetValidator().Validate(self.xrc_txt_nm):
            return
        for set in sel:
            self.controller.project[plot][set].trafo.append(('x', '1.0/x*1e7', 'raman shift (1/2)'))
            shift = 1/float(self.xrc_txt_nm.GetValue())*1e7
            self.controller.project[plot][set].trafo.append(('x', '-x+%.5f'%shift, 'raman shift (2/2)'))
        return True

    def op_raman_inv(self, name, plot, sel):
        if not self.xrc_txt_cm.GetValidator().Validate(self.xrc_txt_cm):
            return
        for set in sel:
            shift = 1/float(self.xrc_txt_cm.GetValue())*1e7
            self.project[plot][set].trafo.append(('x', '-x+%.5f'%shift, 'inverse raman shift (1/2)'))
            self.project[plot][set].trafo.append(('x', '1.0/x*1e7', 'inverse raman shift (2/2)'))
        return True

    def op_predef(self, name, plot, sel):
        for set in sel:
            self.project[plot][set].trafo.append(('x',trafomap[name],name))
        return True

    def op_interpolate(self, name, plot, sel):
        pts = int(self.xrc_txt_interpolate.GetValue())
        for set in sel:
            rng = self.project[plot][set].xrng
            x = np.linspace(rng[0],rng[1],pts)
            sp = self.project[plot][set].interpolate(x, cp=True)
            self.controller.add_set(sp)
        
    def op_sgfilter(self, name, plot, sel):
        window = int(self.xrc_txt_sgwindow.GetValue())
        order = int(self.xrc_txt_sgorder.GetValue())
        for set in sel:
            try:
                sp = self.project[plot][set].sg_filter(window, order, cp=True)
            except TypeError as er:
                self.message('error: %s'%er, blink=True)
                break
            self.controller.add_set(sp)

    def op_splinesmooth(self, name, plot, sel):
        pts = int(self.xrc_txt_splpts.GetValue())
        smooth = float(self.xrc_txt_spls.GetValue())
        
        for s in sel:
            pset = self.project[plot][s]
            if not all(x<y for x, y in zip(pset.x, pset.x[1:])):
                self.message('{}: X-values must be monotonously increasing.'.format(pset.name))
                continue
            try:
                t = np.linspace(pset.x.min(),pset.x.max(),pts+2)[1:-1]
                tcl = splrep(pset.x,pset.y,t=t,s=smooth)
            except TypeError as er:
                self.message('error: %s'%er, blink=True)
                break
            else:
                newy = splev(pset.x, tcl)
                sp = spec.Spec(pset.x, newy, pset.name+'_spline')
                self.controller.add_set(sp)

    def op_waverage(self, name, plot, sel):
        step = float(self.xrc_txt_wavg_step.Value)
        width = float(self.xrc_txt_wavg_width.Value)
        for set in sel:
            sp = self.project[plot][set].weighted_average(step, width, cp=True)
            self.controller.add_set(sp)

    def op_average(self, name, plot, sel):
        pts = int(self.xrc_txt_average.GetValue())
        for set in sel:
            sp = self.project[plot][set].average(pts, cp=True)
            self.controller.add_set(sp)

    def op_derivate(self, name, plot, sel):
        for set in sel:
            sp = self.project[plot][set].derivate(cp=True)
            self.controller.add_set(sp)

    def op_normalise(self, name, plot, sel):
        for set in sel:
            aset = self.project[plot][set]
            aset.trafo.append(('y','y/%s'%(aset.y.max()),'norm'))
            #sp = self.project[plot][set].norm(cp=True)
            #self.controller.add_set(sp)
        return True# self.controller.update_plot()

    def op_avg_sel(self, name, plot, sel):
        sp = reduce(add, [self.project[plot][q] for q in sel])/len(sel)
        sp.name = 'avg_of_'+'_'.join(['s%d'%q for q in sel])
        self.controller.add_set(sp)

    def op_general(self, name, plot, sel):
        trafo = self.xrc_op.GetValue()
        if self.do_op(trafo):
            self.xrc_op.Store()
            self.xrc_btn_repeat.Enable()
            #pub.sendMessage((self.view_id, 'changed'))
            return True
        else:
            self.xrc_op.SetMark(0,-1)
            return False

    def do_op(self, trafo):
        trafo_axis = None

        p = re.compile(r's(\d+)')
        if p.search(trafo) is not None:
            # inter set operation
            plot = self.controller.active_plot
            
            trafo = p.sub(r'plot[\1]',trafo)
           
            try:
                newspec = eval(trafo)
                if type(newspec) != spec.Spec:
                    raise TypeError('result is no set object')
            except Exception as msg:
                self.message('caught exception: %s'%msg)
                return False
            else:
                self.controller.add_set(newspec)
                #pub.sendMessage((self.view_id, 'changed'))
                return True

        else:
            mat = re.match(r'^([yx])=(.+)$',trafo,re.I)
            if mat is not None:
                trafo_axis = mat.groups()[0]
                trafo = trafo.split('=')[1]
            else:
                indep = re.findall(r"(?<![a-z0-9])x|y(?![a-z0-9])", trafo)
                if len(set(indep))==2:
                    self.message('Transformation axis has to be defined. Use e.g."y={}".'.format(trafo))
                    return False
                else:
                    try:
                        trafo_axis = list(set(indep))[0]
                    except IndexError:
                        self.message('Invalid expression.)')
                        return False

            #intra set operation
            plot,sel = self.controller.selection

            for s in sel:
                try:
                    res = eval(trafo,{'x':np.arange(3),'y':np.arange(3)},pom_globals)
                    if type(res) != np.ndarray:
                        raise TypeError('result is not a ndarray')
                except:
                    msg = sys.exc_info()[1]
                    self.message('caught exception: %s'%msg)
                    return False
                else:
                    self.controller.project[plot][s].trafo.append((trafo_axis, trafo, 'custom'))
            #pub.sendMessage((self.view_id, 'changed'))
            return True

        
