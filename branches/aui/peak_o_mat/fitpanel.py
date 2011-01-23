from math import ceil

import wx
import wx.lib.dialogs as dialogs
from wx import xrc

import pargrid
import weightsgrid
import controls

class FitPanel(wx.Panel):
    def __init__(self, parent):
        pre = wx.PrePanel()
        self.res = xrc.XmlResource.Get()
        self.res.LoadOnPanel(pre, parent, "fitpanel")
        self.PostCreate(pre)

        self.pargrid = pargrid.ParGrid(self)
        self.res.AttachUnknownControl('pargrid', self.pargrid)

        self.nb_fit = self.FindWindowByName('nb_fit')

        self.canvas = wx.FindWindowByName('canvas')
        
        self.weightsgrid = weightsgrid.WeightsGrid(self)
        self.res.AttachUnknownControl('weights_grid', self.weightsgrid)
        self.weightsgrid.GetParent().SetMinSize(self.weightsgrid.GetMinSize())
        
        self.txt_model = self.FindWindowByName('txt_model')
        self.lab_peakinfo = self.FindWindowByName('lab_peakinfo')
        self.pan_peakbtns = self.FindWindowByName('pan_peakbuttons')
        assert self.pan_peakbtns is not None
        self.btn_modelclear = self.FindWindowByName('btn_modelclear')
        self.btn_pickpars = self.FindWindowByName('btn_getpars')
        self.ch_pickpars = self.FindWindowByName('ch_getpars')
        self.pan_loadpeaks = self.FindWindowByName('pan_loadpeaks')
        self.btn_loadpeaks = self.FindWindowByName('btn_loadpeaks')
        self.ch_loadpeaks = self.FindWindowByName('ch_loadpeaks')
        self.pan_parexport = self.FindWindowByName('pan_parexport')
        self.btn_parexport = self.FindWindowByName('btn_parexport')
        self.ch_parexport = self.FindWindowByName('ch_parexport')
        self.btn_fit = self.FindWindowByName('btn_fit')
        self.btn_fit_quick = self.FindWindowByName('btn_fit_quick')
        self.txt_from = self.FindWindowByName('txt_from')
        self.txt_to = self.FindWindowByName('txt_to')
        self.txt_points = self.FindWindowByName('txt_points')
        self.cb_limitfitrange = self.FindWindowByName('cb_limitfitrange')
        self.cb_errors = self.FindWindowByName('cb_errors')
        self.txt_maxiter = self.FindWindowByName('txt_maxit')
        self.txt_stepsize = self.FindWindowByName('txt_stepsize')
        self.txt_fitlog = self.FindWindowByName('txt_fitlog')
        self.rd_fittype = self.FindWindowByName('rd_fittype')
        self.tab_parameters = self.FindWindowByName('tab_parameters') 
        self.tab_fit = self.FindWindowByName('tab_fit') 
        self.tab_weights = self.FindWindowByName('tab_weights')

        self.btn_placehandles = self.FindWindowByName('btn_placehandles')
        self.btn_storeweights = self.FindWindowByName('btn_storeweights')
        self.btn_clearweights = self.FindWindowByName('btn_clearweights')

        self.txt_from.SetValidator(controls.InputValidator(controls.FLOAT_ONLY))
        self.txt_to.SetValidator(controls.InputValidator(controls.FLOAT_ONLY))
        self.txt_points.SetValidator(controls.InputValidator(controls.DIGIT_ONLY))

        parent = self.GetParent()
        parent.InsertPage(0, self, 'Fit')
        parent.SetSelection(0)
        
    def _set_silent(self, state):
        self.SetEvtHandlerEnabled(not state)
    silent = property(fset=_set_silent)

    def _get_model(self):
        return self.txt_model.GetValue()
    def _set_model(self, value):
        ins = self.txt_model.GetInsertionPoint()
        self.txt_model.ChangeValue(value)
        self.txt_model.SetInsertionPoint(ins)
    model = property(_get_model, _set_model)
    
    def _get_nbpage(self):
        return self.nb_fit.GetPage()
    def _set_nbpage(self, num):
        self.nb_fit.SetSelection(num)
    nbpage = property(_get_nbpage, _set_nbpage)
    
    def _get_nbpages(self):
        return self.nb_fit.GetPageCount()
    nbpages = property(_get_nbpages)

    def _set_peakinfo(self, lab):
        self.lab_peakinfo.SetValue(lab)
    peakinfo = property(fset=_set_peakinfo)

    def _get_load_range(self):
        xmin, xmax = [float(x) for x in [i.GetValue() for i in [self.txt_from,self.txt_to]]]
        return xmin,xmax
    def _set_load_range(self, xr):
        xmin, xmax = xr
        self.txt_from.SetValue(unicode(xmin))
        self.txt_to.SetValue(unicode(xmax))
    loadrange = property(_get_load_range,_set_load_range)

    def _set_loadwhich_choice(self, items):
        self.ch_loadpeaks.Freeze()
        self.ch_loadpeaks.Clear()
        for item in items:
            self.ch_loadpeaks.Append(unicode(item))
        self.ch_loadpeaks.SetSelection(0)
        self.ch_loadpeaks.Thaw()
    loadwhich_choice = property(fset=_set_loadwhich_choice)

    def _get_loadwhich(self):
        return self.ch_loadpeaks.GetSelection()
    def _set_loadwhich(self, sel):
        self.ch_loadpeaks.SetSelection(sel)
    loadwhich = property(_get_loadwhich,_set_loadwhich)

    def _set_pickwhich_choice(self, items):
        self.ch_pickpars.Freeze()
        self.ch_pickpars.Clear()
        for item in items:
            self.ch_pickpars.Append(unicode(item))
        self.ch_pickpars.SetSelection(0)
        self.ch_pickpars.Thaw()
    pickwhich_choice = property(fset=_set_pickwhich_choice)

    def _get_pickwhich(self):
        return self.ch_pickpars.GetSelection()
    def _set_pickwhich(self, sel):
        self.ch_pickpars.SetSelection(sel)
    pickwhich = property(_get_pickwhich,_set_pickwhich)

    def _get_loadpts(self):
        return int(self.txt_points.GetValue())
    loadpts = property(_get_loadpts)

    def _get_exportwhich(self):
        return self.ch_parexport.GetStringSelection()
    def _set_exportwhich(self, sel):
        self.ch_parexport.SetStringSelection(sel)
    exportwhich = property(_get_exportwhich, _set_exportwhich)
    
    def _set_exportwhich_choice(self, items):
        self.ch_parexport.Freeze()
        self.ch_parexport.Clear()
        for item in items:
            self.ch_parexport.Append(unicode(item))
        self.ch_parexport.SetSelection(0)
        self.ch_parexport.Thaw()
    exportwhich_choice = property(fset=_set_exportwhich_choice)

    def _get_exporterrors(self):
        return self.cb_errors.IsChecked()
    exporterrors = property(_get_exporterrors)

    def _get_fittype(self):
        return self.rd_fittype.GetSelection()
    fittype = property(_get_fittype)

    def _get_limitfitrange(self):
        return self.cb_limitfitrange.IsChecked()
    def _set_limitfitrange(self, val):
        self.cb_limitfitrange.SetValue(bool(val))
    limitfitrange = property(_get_limitfitrange, _set_limitfitrange)
    
    def _get_maxiter(self):
        return int(self.txt_maxiter.GetValue())
    maxiter = property(_get_maxiter)
    
    def _get_stepsize(self):
        return float(self.txt_stepsize.GetValue())
    stepsize = property(_get_stepsize)

    def _set_fitlog(self, txt):
        self.txt_fitlog.AppendText(txt+'\n')
    log = property(fset=_set_fitlog)

    def enable_fit(self, state):
        self.btn_fit.Enable(state)
        self.btn_fit_quick.Enable(state)
        self.pan_loadpeaks.Enable(state)
        self.pan_parexport.Enable(state)
        
    def enable_pick(self, state):
        self.btn_pickpars.Enable(state)
        self.ch_pickpars.Enable(state)

    def drawModelButtons(self, peaks):
        """\
        draws buttons for each model function it encounteres in module 'specs' and in the
        per-user definitions. The buttons are grouped according to their type flag, e.g.
        BACKGROUND, PEAK, etc..
        """
        hor = wx.BoxSizer(wx.HORIZONTAL)
        panel = self.pan_peakbtns
        choices = []
        btns = []
        #hor.Add(wx.StaticText(panel, -1, 'available peaks'), 0, wx.EXPAND|wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
        for name,id in peaks.ptype:
            box = wx.BoxSizer(wx.VERTICAL)
            lab = wx.StaticText(panel,-1,name)
            lab.SetMinSize((5,-1))
            box.Add(lab, 0, wx.ALL|wx.EXPAND|wx.ALIGN_CENTER_HORIZONTAL, 3)
            tokens = peaks.functions.group(id)
            
            #ch = wx.Choice(panel, -1, choices=[name.lower()]+tokens)
            #ch.SetSelection(0)
            #choices.append(ch)
            #hor.Add(ch, 0, wx.EXPAND|wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
            
            cols = int(ceil(len(tokens)/4.0))
           
            grid = wx.FlexGridSizer(4,0,0,0)
            grid.SetFlexibleDirection(wx.HORIZONTAL)
            for i in range(cols):
                grid.AddGrowableCol(i)
            for name in tokens:
                btn = wx.Button(panel, -1, name, size=(10,-1), name='btn_%s'%name, style=wx.BU_EXACTFIT)
                btns.append(btn)
                grid.Add(btn, 0, wx.EXPAND)
            box.Add(grid, 1, wx.ALL|wx.EXPAND, 2)
            hor.Add(box, cols, wx.EXPAND)
        panel.SetSizer(hor)
        hor.SetSizeHints(panel)
        panel.GetParent().Layout()
        return btns
    
