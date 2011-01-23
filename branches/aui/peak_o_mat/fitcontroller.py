import wx
from wx.lib.pubsub import pub as Publisher
import wx.lib.dialogs as dialogs

import time
from operator import add
import sys
from math import ceil
import copy
import re

import numpy as N

import misc
import pargrid
import settings as config

import spec
import fit
import model
import peaks
from peaks import functions

import controls
import weights 

class FitInteractor(object):
    nb_last_sel = 0
    
    def Install(self, controller, view, modelbuttons=None):
        self.controller = controller
        self.view = view
        
        self.view.Bind(wx.EVT_TEXT, self.OnModelText, self.view.txt_model)
        #self.view.pan_peakbtns.Bind(wx.EVT_BUTTON, self.OnFuncButton)
        self.view.pan_peakbtns.Bind(wx.EVT_BUTTON, self.OnFuncButton)
        self.view.Bind(wx.EVT_BUTTON, self.OnClearModel, self.view.btn_modelclear)

        if modelbuttons is not None:
            for btn in modelbuttons:
                btn.Bind(wx.EVT_ENTER_WINDOW, self.OnFuncButtonFocus)

        self.view.Bind(wx.EVT_BUTTON, self.OnPickParameters, self.view.btn_pickpars)
        self.view.Bind(wx.EVT_BUTTON, self.OnLoadFromPars, self.view.btn_loadpeaks)
        self.view.Bind(wx.EVT_BUTTON, self.OnExportPars, self.view.btn_parexport)
        self.view.Bind(wx.EVT_CHOICE, self.OnExportParsChoice, self.view.ch_parexport)
        self.view.Bind(wx.EVT_BUTTON, self.OnStartFit, self.view.btn_fit)
        self.view.Bind(wx.EVT_BUTTON, self.OnStartFit, self.view.btn_fit_quick)
        self.view.Bind(wx.EVT_CHECKBOX, self.OnLimitFitRange, self.view.cb_limitfitrange)

        Publisher.subscribe(self.OnSelectionChanged, ('selection','changed'))

        #em.eventManager.Register(self.OnGotPars, misc.EVT_GOTPARS, self.view.canvas)
        #em.eventManager.Register(self.OnGotPars, misc.EVT_GOTPARS, self.view.pargrid)
        self.view.canvas.Bind(misc.EVT_GOTPARS, self.OnGotPars)
        self.view.pargrid.Bind(misc.EVT_GOTPARS, self.OnGotPars)
        
        self.view.Bind(wx.EVT_TOGGLEBUTTON, self.OnPlaceHandles, self.view.btn_placehandles)
        self.view.Bind(wx.EVT_BUTTON, self.OnAttachWeights, self.view.btn_storeweights)
        self.view.Bind(wx.EVT_BUTTON, self.OnClearWeightsRegion, self.view.btn_clearweights)
        self.view.weightsgrid.Bind(wx.grid.EVT_GRID_CELL_CHANGE, self.OnWeightsChanged)

        Publisher.subscribe(self.OnCanvasMode, ('canvas','newmode'))
        Publisher.subscribe(self.OnPageChanged, ('notebook','pagechanged'))

    def listen_to_handles(self, listen=True):
        if listen:
            self.view.canvas.Bind(misc.EVT_HANDLES_CHANGED, self.OnHandles)
            #em.eventManager.Register(self.OnHandles, misc.EVT_HANDLES_CHANGED, self.view.canvas)
        else:
            try:
                self.view.canvas.Unbind(misc.EVT_HANDLES_CHANGED)
                #em.eventManager.DeregisterListener(self.OnHandles)
            except KeyError:
                pass

    def OnPageChanged(self, msg):
        if msg.data.GetName() == 'fitpanel':
            self.controller.page_changed(self.view.nb_fit.GetCurrentPage().GetName())
        else:
            self.controller.page_changed(msg.data.GetName())
    
    def OnCanvasMode(self, msg):
        if msg.data != 'handle':
            self.view.btn_placehandles.SetValue(False)

    def OnPlaceHandles(self, evt):
        if self.view.btn_placehandles.GetValue():
            self.controller.start_select_weights()
        else:
            self.view.canvas.SetMode(None)

    def IsSelected(self):
        """\
        Checks if this page is visible
        """
        return self.view.GetParent().GetCurrentPage() == self.view

    def OnLimitFitRange(self, evt):
        self.controller.set_limit_fitrange(evt.IsChecked())

    def OnHandles(self, evt):
        self.controller.set_weights_regions(evt.handles)
        
    def OnAttachWeights(self, evt):
        self.controller.attach_weights()

    def OnWeightsChanged(self, evt):
        self.controller.weights_changed()

    def OnClearWeightsRegion(self, evt):
        self.controller.clear_weights()

    def OnGotPars(self, evt):
        if evt.cmd == misc.GOTPARS_DOWN:
            wx.CallAfter(self.controller.got_pars)
        if evt.cmd == misc.GOTPARS_EDIT:
            self.controller.changed_pars()
        evt.Skip()

    def OnStartFit(self, evt):
        self.controller.start_fit()

    def OnExportParsChoice(self, evt):
        self.controller.exportwhich = self.view.exportwhich
                   
    def OnExportPars(self, evt):
        self.controller.export_pars(self.view.exportwhich, self.view.exporterrors)

    def OnLoadFromPars(self, evt):
        if self.view.pan_loadpeaks.Validate():
            self.controller.load_set_from_model(self.view.loadwhich, self.view.loadrange, self.view.loadpts)

    def OnSelectionChanged(self, msg):
        self.controller.set_selection_changed(msg.data)

    def OnPickParameters(self, evt):
        self.controller.start_pick_pars()

    def OnClearModel(self, evt):
        self.view.model = ''
        self.controller.new_tokens('')
        
    def OnFuncButtonFocus(self, evt):
        """\
        displays the description and function string of the selected token button
        """
        name = evt.GetEventObject().GetName().split('_')[1]
        try:
            info = peaks.functions[name].info
        except KeyError:
            pass
        else:
            info += '\n'+peaks.functions[name].func
            self.view.peakinfo = info
            evt.Skip()
        
    def OnFuncButton(self, evt):
        """\
        adds the function token associated with the current button to the model text control.
        Equal tokens are numbered automatically.
        """
        btn = evt.GetEventObject().GetName()
        newtoken = btn.split('_')[-1]
        self.controller.add_token(newtoken)
        
    def OnModelText(self, evt):
        self.controller.new_tokens(evt.GetString())

class FitController(object):
    def __init__(self, view, interactor):
        self.view = view
        self._model = None
        self._weights = None
        self.exportwhich = 'all'
        self._last_page = None
        self._current_page = None
        self._current_set = None
        self._fit_in_progress = False
        
        self.interactor = interactor
        
        btns = self.view.drawModelButtons(peaks)
        interactor.Install(self, self.view, btns)
        
        self.weights = weights.Weights([weights.WeightsRegion(-N.inf,N.inf, 0.1, 0.5, 1)])

    def _set_weights(self, w):
        self._weights = w
        self.view.weightsgrid.table.data = self._weights
    def _get_weights(self):
        if self._current_page != 'tab_weights':
            return None
        else:
            return self._weights
    weights = property(_get_weights,_set_weights)

    def _set_model(self, m):
        if self._model is not None:
            self._model.listener = None
        self._model = m
        if self._model is not None:
            self._model.listener = self.refresh_pargrid
        self.view.pargrid.data = model.ModelTableProxy(self._model)
    def _get_model(self):
        return self._model
    model = property(_get_model,_set_model)

    def refresh_pargrid(self):
        print 'fitcontroller:refresh_pragrid'
        self.view.pargrid.refresh()
    
    def set_limit_fitrange(self, state):
        self.view.silent = True
        self.view.limitfitrange = state
        Publisher.sendMessage(('fitctrl','limitfitrange'),state)
        self.view.silent = False
        
    def page_changed(self, name):
        self._current_page = name
        if name == 'tab_parameters':
            if self.model is not None:
                if not self.model.parsed:
                    self.model.parse()
                    self.model = self.model
                    self.update_parameter_panel()
        if self._last_page == 'tab_weights':
            self.stop_select_weights()
        self._last_page = name
        wx.CallAfter(self.sync_gui)

    def sync_gui(self, **kwargs):
        if kwargs.has_key('fit_in_progress'):
            self._fit_in_progress = kwargs['fit_in_progress']
        self.view.enable_fit(not self._fit_in_progress and self.model is not None and self.model.is_filled() and self._current_set is not None)
        self.view.enable_pick(not self._fit_in_progress and self.model is not None and self._current_set is not None and self.model.is_autopickable())
        self.view.tab_parameters.Enable(self.model is not None and not self.model.is_empty())

    def set_selection_changed(self, set):
        self._current_set = set
        if set is not None:
            if set.weights is not None:
                self.weights = set.weights
                if self._current_page == 2:
                    self.canvas.set_handles(self._weights.getBorders())
            else:
                self.weights = copy.deepcopy(self._weights)
            if set.mod is not None:
                old_model = self.model
                self.model = copy.deepcopy(set.mod)
                self.view.silent = True
                self.view.model = set.mod.get_model_unicode()
                if old_model != set.mod:
                    self.update_parameter_panel()
                self.view.silent = False
            self.view.loadrange = set.xrng
            self.view.limitfitrange = (set.limits is not None or set.mod is None)
        wx.CallAfter(self.sync_gui)

    def update_parameter_panel(self):
        self.view.loadwhich_choice = ['all']+self.model.tokens.split(' ')
        self.view.pickwhich_choice = ['all']+self.model.tokens.split(' ')
        self.view.exportwhich_choice = ['all']+self.model.get_parameter_names()
        self.view.exportwhich = self.exportwhich
        self.exportwhich = self.view.exportwhich

    def clear_weights(self):
        self.weights = weights.Weights([weights.WeightsRegion(-N.inf,N.inf, 0.1, 0.5, 1)])
        self.view.canvas.set_handles(self._weights.getBorders())
        self.weights_changed()

    def set_weights_regions(self, borders):
        regions = []
        for region in [-N.inf]+borders:
            regions.append(region)
        for n,region in enumerate(borders+[N.inf]):
            regions[n] = [regions[n],region]

        self.weights.newRegions(regions)
        self.view.weightsgrid.table.Update()
        self.weights_changed()
        
    def start_select_weights(self):
        handles = self._weights.getBorders()
        self.view.canvas.set_handles(handles)
        self.view.canvas.SetMode('handle')
        self.interactor.listen_to_handles()

    def stop_select_weights(self):
        self.interactor.listen_to_handles(False)
        self.view.canvas.set_handles(N.zeros((0,1)))
        self.weights_changed()
        self.view.canvas.RestoreLastMode()

    def attach_weights(self):
        Publisher.sendMessage(('fitctrl','attachweights'),(self.view.weightsgrid.table.data))
    
    def weights_changed(self):
        Publisher.sendMessage(('fitctrl','plot'))

    def new_tokens(self, tokens):
        self.view.silent = True
        try:
            mod = model.Model(tokens)
        except:
            self.message('invalid model')
            self.model = None
        else:
            if mod.func is not None:
                self.message('custom model')
            else:
                self.message('')
            self.model = mod
            self.view.model = tokens
        self.view.silent = False

    def add_token(self, newtoken):
        try:
            oldtokens = re.split(r'[\s\+\-\*]+',self.model.tokens)
        except:
            oldtokens = ['']
        if newtoken not in peaks.functions.background:
            tokens = {}
            for i in oldtokens:
                i = re.sub(r'[0-9]','',i)
                if i not in tokens.keys():
                    tokens[i] = 1
                else:
                    tokens[i] += 1
            if newtoken in tokens:
                num = (tokens[newtoken])+1
            else:
                num = 1
            newtoken += '%d'%num
        oldtokens.append(newtoken)
        tokens = ' '.join(oldtokens).strip()
        self.new_tokens(tokens)

    def load_set_from_model(self, which, xr, pts):
        Publisher.sendMessage(('fitctrl','loadset'),(self.model,which,xr,pts))

    def export_pars(self, which, witherrors):
        Publisher.sendMessage(('fitctrl','parexport'),(self.model.parameters_as_table(which,witherrors)))

    def start_pick_pars(self):
        self.model = copy.deepcopy(self.model)
        self.view.enable_fit(False)
        self.pickers = []
        if self.view.pickwhich != 0:
            component = self.model[self.view.pickwhich-1]
            component.clear()
            picker = functions[component.name].picker(component,self.model.background)
            self.pickers.append(picker)
        else:
            self.model.clear()
            for component in self.model:
                picker = functions[component.name].picker(component,self.model.background)
                self.pickers.append(picker)
        tmp = [len(p) for p in self.pickers]
        cumtmp = tmp[:]
        for i in range(1,len(tmp)):
            cumtmp[i] = cumtmp[i]+cumtmp[i-1]
        Publisher.sendMessage(('fitctrl','pickpars'), (tmp, reduce(add, self.pickers)))

    def got_pars(self):
        self.view.pargrid.refresh()
        self.view.enable_fit(self.model.is_filled())
        
    def changed_pars(self):
        self.view.enable_fit(self.model.is_filled())
        Publisher.sendMessage(('fitctrl','editpars'))

    def log(self, msg):
        self.view.log = msg

    def start_fit(self):
        Publisher.sendMessage(('fitctrl','fit'),
                                (self.model,
                                 self.view.limitfitrange,
                                 self.view.fittype,
                                 self.view.maxiter,
                                 self.view.stepsize))

    def message(self, msg, target=1, blink=False):
        event = misc.ShoutEvent(self.view.GetId(), msg=msg, target=target, blink=blink)
        wx.PostEvent(self.view, event)

