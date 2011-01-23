import wx
from wx.lib.pubsub import pub as Publisher
from math import log10,exp,pow

from peak_o_mat import module, peaks, controls
from peak_o_mat import settings as config

import numpy as N

class Module(module.Module):
    title = 'Ruby Calibration'
    
    def __init__(self, *args):
        module.Module.__init__(self, __file__, *args)
        
    def init(self):
        self.Bind(wx.EVT_TEXT, self.OnTemp, self.xrc_txt_temp)
        self.Bind(wx.EVT_CHOICE, self.OnChoice)
        
        Publisher.subscribe(self.selection_changed, ('fitfinished'))
        self.panel.Layout()

        self.xrc_txt_temp.SetValidator(controls.InputValidator(controls.FLOAT_ONLY))
        
    def calculate(self):
        ne_line = 6929.47

        try:
            self.neon + self.r1
        except:
            return
        
        if log10(self.neon) < 3.0:
            self.neon *= 10
            self.r1 *= 10

        r1 = self.r1+(ne_line-self.neon)
        try:
            p = self.pressure(self.temp, r1)
        except:
            self.xrc_lab_press.SetLabel('???')
        else:
            self.xrc_lab_press.SetLabel('%.2f GPa'%p)
         
    def pressure(self, t, r1):
        """
        calculates the hydrostatic pressure from temperature and
        the wavelength of the r1 line in Angstroem
        parameters are taken from Ph.D. thesis of Clemens Ulrich
        """
        A = 1904
        B = 7.665
        alpha = 76.6
        theta =  482
        r1_0 = 14421.8

        e = 1/(r1*1e-8)

        r1_t = r1_0 - alpha/(exp(theta/t)-1)

        r1_t = 1/(1e-8*r1_t)

        p = A/B*(pow(1+(r1*1e-10-r1_t*1e-10)/(r1_t*1e-10),B)-1)

        return p

    def update_model(self):
        aset = self.controller.active_set
        if aset is not None and aset.mod is not None:
            self.model = aset.mod
            self.panel.Enable()
            self.update_choices()
        else:
            self.panel.Disable()

    def update_choices(self):
        components = self.model.tokens.split(' ')
        pks = filter(lambda q: q in peaks.functions.peak, components)

        r1 = self.xrc_ch_r1.GetStringSelection()
        self.xrc_ch_r1.Clear()
        self.xrc_ch_r1.AppendItems(pks)
        if not self.xrc_ch_r1.SetStringSelection(r1):
            self.xrc_ch_r1.SetSelection(0)
        
        neon = self.xrc_ch_neon.GetStringSelection()
        self.xrc_ch_neon.Clear()
        self.xrc_ch_neon.AppendItems(pks)
        if not self.xrc_ch_neon.SetStringSelection(neon):
            self.xrc_ch_neon.SetSelection(0)
            
        self.OnChoice()
            
    def OnChoice(self, evt=None):
        units = ['A','nm']
        sel = self.xrc_ch_r1.GetStringSelection()
        self.r1 = self.model[sel].pos.value
        unit = units[int(log10(self.r1) < 3.0)]
        self.xrc_lab_r1.SetLabel('%04.1f %s'%(self.r1,unit))
        sel = self.xrc_ch_neon.GetStringSelection()
        self.neon = self.model[sel].pos.value
        self.xrc_lab_neon.SetLabel('%04.1f %s'%(self.neon,unit))
        self.calculate()
        
    def OnTemp(self, evt):
        try:
            self.temp = float(self.xrc_txt_temp.GetValue())
        except ValueError:
            self.xrc_lab_melt.SetLabel('???')
            self.xrc_lab_press.SetLabel('???')
        else:
            self.calculate()
            melt = 1.6067e-3*N.power(self.temp,1.565)
            self.xrc_lab_melt.SetLabel('%1.2f GPa'%melt)
            
    def selection_changed(self, arg=None):
        self.update_model()
        
    def page_changed(self, me):
        if me:
            self.selection_changed()
