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
import re
import sys
from operator import add

from peak_o_mat import module, controls, spec

import numpy as N
from scipy import integrate
from scipy import signal

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

dftwindows = ['none','hamming','hann','barthann','triang',
              'blackman','blackmanharris']

class Module(module.Module):
    title = 'Data operations'
    
    def __init__(self, *args):
        module.Module.__init__(self, __file__, *args)

        self.funcs = [self.op_general,
                      self.op_predef,
                      self.op_interpolate,
                      self.op_average,
                      self.op_sgfilter,
                      self.op_derivate,
                      self.op_normalise,
                      self.op_avg_sel,
                      self.op_raman,
                      self.op_raman_inv]
        
    def init(self):
        self.xmlres.AttachUnknownControl('xrc_op', controls.HistTextCtrl(self.panel, -1, ''))
        self.xrc_op.GetParent().SetMinSize(self.xrc_op.GetMinSize())

        #for w in dftwindows:
        #    self.xrc_ch_dftwindow.Append(w)
        #self.xrc_ch_dftwindow.SetSelection(0)

        ctrls = ['xrc_op',
                 'xrc_pan_predef',
                 'xrc_btn_interpolate',
                 'xrc_btn_average',
                 'xrc_btn_sg',
                 'xrc_btn_derivate',
                 'xrc_btn_normalise',
                 'xrc_btn_avg_sel',
                 'xrc_btn_nm2cm',
                 'xrc_btn_cm2nm']
        
        evts = [wx.EVT_TEXT_ENTER]+[wx.EVT_BUTTON]*9

        for c,e,f in zip(ctrls,evts,self.funcs):
            assert getattr(self, c) is not None
            getattr(self, c).Bind(e, curry(self.OnOp, f))
            
        self.xrc_txt_nm.SetValidator(controls.InputValidator(controls.FLOAT_ONLY))
        self.xrc_txt_cm.SetValidator(controls.InputValidator(controls.FLOAT_ONLY))
        self.xrc_txt_sgwindow.SetValidator(controls.InputValidator(controls.INT_ONLY))
        self.xrc_txt_sgorder.SetValidator(controls.InputValidator(controls.INT_ONLY))

        self.xrc_btn_repeat.Bind(wx.EVT_BUTTON, self.OnRepeat)

    def OnRepeat(self, evt):
        self.do_op(self.xrc_op.last_op)
        self.controller.update_plot()
    
    def OnOp(self, func, evt):
        self.controller._busy = True
        name = evt.GetEventObject().GetName()
        func(name, *self.controller.selection)
        self.controller._busy = False
        self.controller.update_plot()

    def op_raman(self, name, plot, sel):
        if not self.xrc_txt_nm.GetValidator().Validate(self.xrc_txt_nm):
            return
        for set in sel:
            self.controller.project[plot][set].trafo.append(('x', '1.0/x*1e7', 'raman shift (1/2)'))
            shift = 1/float(self.xrc_txt_nm.GetValue())*1e7
            self.controller.project[plot][set].trafo.append(('x', '-x+%.5f'%shift, 'raman shift (2/2)'))

    def op_raman_inv(self, name, plot, sel):
        if not self.xrc_txt_cm.GetValidator().Validate(self.xrc_txt_cm):
            return
        for set in sel:
            shift = 1/float(self.xrc_txt_cm.GetValue())*1e7
            self.project[plot][set].trafo.append(('x', '-x+%.5f'%shift, 'inverse raman shift (1/2)'))
            self.project[plot][set].trafo.append(('x', '1.0/x*1e7', 'inverse raman shift (2/2)'))

    def op_predef(self, name, plot, sel):
        for set in sel:
            self.project[plot][set].trafo.append(('x',trafomap[name],name))

    def op_interpolate(self, name, plot, sel):
        pts = int(self.xrc_txt_interpolate.GetValue())
        for set in sel:
            rng = self.project[plot][set].xrng
            x = N.linspace(rng[0],rng[1],pts)
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
            sp = self.project[plot][set].norm(cp=True)
            self.controller.add_set(sp)

    def op_avg_sel(self, name, plot, sel):
        sp = reduce(add, [self.project[plot][q] for q in sel])/len(sel)
        sp.name = 'avg_of_'+'_'.join(['s%d'%q for q in sel])
        self.controller.add_set(sp)
            
    def op_dft(self, name, plot, sel):
        dftwin = self.xrc_ch_dftwindow.GetStringSelection()
        result_complex = self.xrc_ch_dftresult.GetStringSelection() == 'complex'
        if dftwin == 'none':
            win = lambda n: N.ones((n))
        else:
            win = getattr(signal, dftwin)
            
        for set in sel:
            s = self.project[plot][set]
            l = len(s.x)
            yf = N.fft.fft(s.y*win(l))[:l/2+1]
            lx = abs(s.x[-1]-s.x[0])
            max_freq = l/lx
            freq = N.linspace(0,max_freq,l)[:l/2+1]
            if result_complex:
                sp_real = spec.Spec(freq, yf.real, s.name+'_dftreal')
                sp_imag = spec.Spec(freq, yf.imag, s.name+'_dftimag')

                self.controller.add_set(sp_real)
                self.controller.add_set(sp_imag)
            else:
                sp = spec.Spec(freq, N.sqrt(yf.real**2+yf.imag**2), s.name+'_dftamp')
                self.controller.add_set(sp)

            
    def op_idft(self, name, plot, sel):
        if len(sel) != 2:
            self.message('select exactly two sets corresponding to real and imaginary part')
        else:
            dftwin = self.xrc_ch_dftwindow.GetStringSelection()
            if dftwin == 'none':
                win = lambda n: N.ones((n))
            else:
                win = getattr(signal, dftwin)
            sp_real = self.project[plot][sel[0]]
            sp_imag = self.project[plot][sel[1]]

            l = (len(sp_real)-1)*2
            y = N.zeros((l),dtype=N.complex)
            y.real = N.hstack((sp_real.y,sp_real.y[-2:0:-1]))
            y.imag = N.hstack((sp_imag.y,-sp_imag.y[-2:0:-1]))

            x = N.zeros((l),dtype=N.float)
            dx = N.mean(sp_real.x[:-1]-sp_real.x[1:])
            x = N.hstack((sp_real.x,sp_real.x+sp_real.x.max()+dx))
            yi = N.fft.ifft(y).real/win(l)
            max_t = l/x[-1]
            x = N.linspace(0, max_t, l)

            sp = spec.Spec(x, yi, 'idft_%sx%s'%(sp_real.name,sp_imag.name))
            self.controller.add_set(sp)
                
    def op_general(self, name, plot, sel):
        trafo = self.xrc_op.GetValue()
        if self.do_op(trafo):
            self.xrc_op.Store()
            self.xrc_btn_repeat.Enable()
        else:
            self.xrc_op.SetMark(0,-1)

    def do_op(self, trafo):
        trafo_axis = None
        yreg = re.compile(r'(^|.*[^a-z]+)y([^a-z]+.*|$)',re.I)
        xreg = re.compile(r'(^|.*[^a-z]+)x([^a-z]+.*|$)',re.I)

        p = re.compile(r's(\d+)')
        if p.search(trafo) is not None:
            # inter set operation
            plot = self.controller.active_plot
            
            trafo = p.sub(r'plot[\1]',trafo)
           
            def __sum__(a,b):
                return a+b

            def sum(vec):
                return reduce(__sum__, vec)

            def avg(vec):
                return reduce(__sum__, vec)/len(vec)
            
            try:
                newspec = eval(trafo)
                if type(newspec) != spec.Spec:
                    raise TypeError, 'result is no set object'
            except Exception, msg:
                self.message('caught exception: %s'%msg)
                return False
            else:
                self.controller.add_set(newspec)
                return True

        elif xreg.match(trafo) is not None:
            trafo_axis = 'x'
        elif yreg.match(trafo) is not None:
            trafo_axis = 'y'
        else:
            self.message('invalid operation')
            return False

        #intra set operation
        plot,sel = self.controller.selection

        for s in sel:
            try:
                glb = globals()
                glb.update(N.__dict__)
                #glb.update({'sum':sum,'avg':avg})
                res = eval(trafo,{trafo_axis:N.arange(10)},glb)
                if type(res) != N.ndarray:
                    raise TypeError, 'result is not a ndarray'
            except:
                msg = sys.exc_info()[1]
                self.message('caught exception: %s'%msg)
                return False
            else:
                self.controller.project[plot][s].trafo.append((trafo_axis, trafo, 'custom'))
        return True

    def wrap(self, text, width):
        """
        A word-wrap function that preserves existing line breaks
        and most spaces in the text. Expects that existing line
        breaks are posix newlines (\n).
        """
        return reduce(lambda line, word, width=width: '%s%s%s' %
                      (line,
                       ' \n'[(len(line)-line.rfind('\n')-1
                              + len(word.split('\n',1)[0]
                                    ) >= width)],
                       word),
                      text.split(' ')
                      )
    
        
