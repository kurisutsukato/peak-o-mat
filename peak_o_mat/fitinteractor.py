
import wx
from wx.lib.pubsub import pub

from . import misc_ui
from . import lineshapebase as lb

class FitInteractor(object):
    nb_last_sel = 0
    
    def Install(self, controller, view):
        self.controller = controller
        self.view = view

        self.view.Bind(wx.EVT_TEXT, self.OnModelText, self.view.pan_model.txt_model)
        self.view.pan_model.btn_addfeature.Bind(wx.EVT_BUTTON, self.OnAddFeature)
        self.view.pan_model.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnFeatureSelected, self.view.pan_model.lst_features)
        self.view.pan_model.lst_features.Bind(wx.EVT_LIST_KEY_DOWN, self.OnFeatureKeyDown)
        self.view.pan_model.lst_features.Bind(wx.EVT_LEFT_DCLICK, self.OnAddFeature)
        self.view.Bind(wx.EVT_BUTTON, self.OnClearModel, self.view.pan_model.btn_modelclear)

        pub.subscribe(self.OnCanvasMode, (self.view.id, 'canvas','newmode'))
        pub.subscribe(self.OnPageChanged, (self.view.id, 'notebook','pagechanged'))
        pub.subscribe(self.pubOnFitFinished, (self.view.id, 'fitfinished'))

        self.view.Bind(wx.EVT_BUTTON, self.OnPickParameters, self.view.pan_pars.btn_pickpars)
        self.view.Bind(wx.EVT_BUTTON, self.OnLoadFromPars, self.view.pan_pars.btn_loadpeaks)
        self.view.Bind(wx.EVT_BUTTON, self.OnExportPars, self.view.pan_pars.btn_parexport)
        self.view.Bind(wx.EVT_CHOICE, self.OnExportParsChoice, self.view.pan_pars.ch_parexport)
        #self.view.Bind(wx.EVT_BUTTON, self.OnStartFit, self.view.btn_fit)
        self.view.Bind(wx.EVT_BUTTON, self.OnStartFit, self.view.pan_pars.btn_fit_quick)
        self.view.Bind(wx.EVT_CHECKBOX, self.OnLimitFitRange, self.view.pan_options.cb_limitfitrange)
        self.view.Bind(wx.EVT_CHECKBOX, self.OnAutostep, self.view.pan_options.cb_autostep)

        pub.subscribe(self.OnSelectionChanged, (self.view.id, 'selection','changed'))

        self.view.Bind(misc_ui.EVT_GOTPARS, self.OnGotPars)
        #TODO: ist das in Ordnung so?
        wx.GetTopLevelParent(self.view).Bind(misc_ui.EVT_GOTPARS, self.OnGotPars)
        self.view.Bind(misc_ui.EVT_RESULT, self.OnFitResult)

        self.view.pan_batch.btn_run.Bind(wx.EVT_BUTTON, self.OnRunBatchfit)

        self.view.pan_batch.btn_generate.Bind(wx.EVT_BUTTON, self.OnGenerateDataset)
        self.view.pan_batch.btn_export.Bind(wx.EVT_BUTTON, self.OnBatchExport)
        self.view.pan_batch.txt_xexpr.Bind(wx.EVT_TEXT, self.OnGenerateDatasetXExpr)


        self.view.Bind(wx.EVT_TOGGLEBUTTON, self.OnPlaceHandles, self.view.pan_weights.btn_placehandles)
        self.view.Bind(wx.EVT_BUTTON, self.OnAttachWeights, self.view.pan_weights.btn_storeweights)
        self.view.Bind(wx.EVT_BUTTON, self.OnClearWeightsRegion, self.view.pan_weights.btn_clearweights)
        self.view.pan_weights.weightsgrid.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.OnWeightsChanged)

        pub.subscribe(self.pubOnPlotAdded, (self.view.id, 'plot_added'))

    def listen_to_handles(self, listen=True):
        if listen:
            wx.GetTopLevelParent(self.view).Bind(misc_ui.EVT_HANDLES_CHANGED, self.OnHandles)
            #em.eventManager.Register(self.OnHandles, misc_ui.EVT_HANDLES_CHANGED, self.view.canvas)
        else:
            try:
                wx.GetTopLevelParent(self.view).Unbind(misc_ui.EVT_HANDLES_CHANGED)
                #em.eventManager.DeregisterListener(self.OnHandles)
            except KeyError:
                pass

    def pubOnPlotAdded(self, plotlist):
        sel = self.view.pan_batch.ch_target.GetStringSelection()
        self.view.pan_batch.ch_target.Clear()
        self.view.pan_batch.ch_target.AppendItems(['new']+plotlist)
        ind = self.view.pan_batch.ch_target.FindString(sel)
        if ind >= 0:
            self.view.pan_batch.ch_target.SetSelection(ind)

    def pubOnFitFinished(self):
        self.view.pan_batch.bf_update(self.controller._current_pl)

    def OnBatchExport(self, evt):
        yexpr = self.view.pan_batch.ch_component.GetStringSelection(),self.view.pan_batch.ch_parameter.GetStringSelection()
        errors = self.view.pan_batch.cb_errors.GetValue()
        res = self.controller.batch_export(self.view.pan_batch.txt_xexpr.Value, yexpr, errors)
        if not res:
            print('error')

    def OnGenerateDataset(self, evt):
        yexpr = self.view.pan_batch.ch_component.GetStringSelection(),self.view.pan_batch.ch_parameter.GetStringSelection()
        target = self.view.pan_batch.ch_target.GetSelection()
        res = self.controller.generate_dataset(self.view.pan_batch.txt_xexpr.Value, yexpr, target)
        if not res:
            print('error')

    def OnGenerateDatasetXExpr(self, evt):
        txt = evt.GetEventObject().GetValue()
        x,complete = self.controller.generate_dataset_check_xexpr(txt)
        self.view.pan_batch.txt_xpreview.SetValue(','.join(str(q) for q in x))
        self.view.pan_batch.btn_generate.Enable(complete)
        self.view.pan_batch.btn_export.Enable(complete)

    def OnRunBatchfit(self, evt):
        fitopts = dict([('fittype',self.view.fittype), ('maxiter',self.view.maxiter), \
                        ('stepsize',self.view.stepsize), ('autostep',self.view.autostep)])

        self.controller.batch_fit(self.view.pan_batch.ch_base.GetStringSelection(),
                                  self.view.pan_batch.ch_initial.GetSelection(),
                                  self.view.pan_batch.ch_order.GetSelection(),
                                  fitopts)

    def OnFitResult(self, evt):
        evt.Skip()
        print(evt)
        if hasattr(evt, 'name'):
            #self.view.progress_dialog(step=evt.name)
            # TODO
            pub.sendMessage((self.view.id,'message'),msg='Fitting {}'.format(evt.name))
        elif hasattr(evt, 'endbatch'):
            self.controller.fit_finished(evt.endbatch)
            # TODO
            #self.view.progress_dialog(step='Finished.')
            pub.sendMessage((self.view.id,'message'),msg='Batch fit finished.')
        elif hasattr(evt, 'end'):
            self.controller.fit_finished(evt.end)

    def OnFeatureKeyDown(self, evt):
        evt.Skip()
        if evt.GetKeyCode() == 13:
            self.OnAddFeature(None)

    def OnAddFeature(self, evt):
        newtoken = self._selected_feature
        self.controller.add_token(newtoken)

    def OnFeatureSelected(self, evt):
        idx = evt.Index
        feature = self.view.pan_model.lst_features.GetItem(idx, 1).GetText()
        self._selected_feature = feature
        self.view.pan_model.btn_addfeature.Enable(feature in list(lb.lineshapes.keys()))

        try:
            info = lb.lineshapes[feature].info
        except KeyError:
            self.view.pan_model.lab_peakinfo.Value = ''
        else:
            info += '\n\n'+lb.lineshapes[feature].func
            self.view.pan_model.lab_peakinfo.Value = info
            evt.Skip()

    def OnPageChanged(self, msg):
        if msg.GetName() == 'fitpanel':
            self.controller.page_changed(self.view.nb_fit.GetCurrentPage().GetName())
        else:
            self.controller.page_changed(msg.GetName())
    
    def OnCanvasMode(self, mode):
        if mode != 'handle':
            self.view.pan_weights.btn_placehandles.SetValue(False)
            self.view.canvas.set_handles([])

    def OnPlaceHandles(self, evt):
        if self.view.pan_weights.btn_placehandles.GetValue():
            self.controller.start_select_weights()
        else:
            self.view.canvas.state.set(None)

    def IsSelected(self):
        return self.view.GetParent().GetCurrentPage() == self.view

    def OnAutostep(self, evt):
        self.view.pan_options.txt_stepsize.Enable(not evt.IsChecked())
        
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
        if evt.cmd == misc_ui.GOTPARS_DOWN:
            wx.CallAfter(self.controller.got_pars)
        if evt.cmd == misc_ui.GOTPARS_EDIT:
            self.controller.changed_pars()
        evt.Skip()

    def OnStartFit(self, evt):
        fitopts = dict([('fittype',self.view.fittype), ('maxiter',self.view.maxiter), \
                        ('stepsize',self.view.stepsize), ('autostep',self.view.autostep)])

        self.controller.start_fit(self.view.limitfitrange, fitopts)

        #self.controller.start_fit()

    def OnExportParsChoice(self, evt):
        self.controller.exportwhich = self.view.exportwhich
                   
    def OnExportPars(self, evt):
        self.controller.export_pars(self.view.exportwhich, self.view.exporterrors)

    def OnLoadFromPars(self, evt):
        if self.view.pan_pars.Validate():
            self.controller.load_set_from_model(self.view.loadwhich, self.view.loadrange, self.view.loadpts)

    def OnSelectionChanged(self, plot, dataset):
        self.controller.selection_changed(plot, dataset)

    def OnPickParameters(self, evt):
        self.controller.start_pick_pars()

    def OnClearModel(self, evt):
        self.view.model = ''
        self.controller.new_tokens('')
        
    def OnModelTextFocus(self, evt):
        self.controller.analyze_model()
        
    def OnModelText(self, evt):
        self.controller.new_tokens(evt.GetString())
