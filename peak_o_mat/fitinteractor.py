
import wx
from pubsub import pub
import re

from . import misc_ui
from . import lineshapebase as lb
from .fitpanel import dlg_set_from_model, dlg_export_parameters

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

        self.view.nb_fit.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnNotebookPageChanged)

        pub.subscribe(self.OnCanvasMode, (self.view.instid, 'canvas','newmode'))
        #pub.subscribe(self.OnPageChanged, (self.view.instid, 'notebook','pagechanged'))
        pub.subscribe(self.pubOnFitFinished, (self.view.instid, 'fitfinished'))

        self.view.Bind(wx.EVT_BUTTON, self.OnPickParameters, self.view.pan_pars.btn_pickpars)
        self.view.Bind(wx.EVT_BUTTON, self.OnBtnGenerateSetDialog, self.view.pan_pars.btn_generateset)
        self.view.Bind(wx.EVT_BUTTON, self.OnGuessParameters, self.view.pan_pars.btn_guesspars)
        self.view.Bind(wx.EVT_BUTTON, self.OnBtnExportDialog, self.view.pan_pars.btn_parexport)

        #self.view.Bind(wx.EVT_BUTTON, self.OnStartFit, self.view.btn_fit)
        self.view.Bind(wx.EVT_BUTTON, self.OnStartFit, self.view.pan_pars.btn_fit_quick)
        self.view.Bind(wx.EVT_CHECKBOX, self.OnLimitFitRange, self.view.pan_options.cb_limitfitrange)
        self.view.Bind(wx.EVT_CHECKBOX, self.OnAutostep, self.view.pan_options.cb_autostep)

        pub.subscribe(self.OnSelectionChanged, (self.view.instid, 'selection','changed'))

        self.view.Bind(misc_ui.EVT_GOTPARS, self.OnGotPars)
        #TODO: ist das in Ordnung so?
        wx.GetTopLevelParent(self.view).Bind(misc_ui.EVT_GOTPARS, self.OnGotPars)

        self.view.Bind(misc_ui.EVT_RESULT, self.OnFitResult)
        self.view.Bind(misc_ui.EVT_BATCH_STEP, self.OnBatchfitStep)

        self.view.pan_batch.btn_run.Bind(wx.EVT_BUTTON, self.OnBatchfitStart)
        self.view.pan_batch.btn_stop.Bind(wx.EVT_BUTTON, self.OnBatchfitStop)

        self.view.pan_batch.btn_generate.Bind(wx.EVT_BUTTON, self.OnGenerateDataset)
        self.view.pan_batch.btn_export.Bind(wx.EVT_BUTTON, self.OnBatchExport)
        self.view.pan_batch.txt_xexpr.Bind(wx.EVT_TEXT, self.OnGenerateDatasetXExpr)


        self.view.Bind(wx.EVT_TOGGLEBUTTON, self.OnPlaceHandles, self.view.pan_weights.btn_placehandles)
        self.view.Bind(wx.EVT_BUTTON, self.OnAttachWeights, self.view.pan_weights.btn_storeweights)
        self.view.Bind(wx.EVT_BUTTON, self.OnClearWeightsRegion, self.view.pan_weights.btn_clearweights)
        self.view.pan_weights.weightsgrid.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.OnWeightsChanged)

        pub.subscribe(self.pubOnPlotAdded, (self.view.instid, 'plot_added'))
        pub.subscribe(self.pubDelmod, (self.view.instid, 'delmod'))

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

    def pubDelmod(self):
        self.controller.sync_gui(batch=True)

    def pubOnPlotAdded(self, plotlist):
        sel = self.view.pan_batch.ch_target.GetStringSelection()
        self.view.pan_batch.ch_target.Clear()
        self.view.pan_batch.ch_target.AppendItems(['new']+plotlist)
        ind = self.view.pan_batch.ch_target.FindString(sel)
        if ind >= 0:
            self.view.pan_batch.ch_target.SetSelection(ind)

    def pubOnFitFinished(self):
        #print('fitinteractor: fit finished')
        self.view.pan_batch.bf_update(self.controller._current_pl)

    def OnBatchExport(self, evt):
        yexpr = self.view.pan_batch.ch_component.GetStringSelection(),self.view.pan_batch.ch_parameter.GetStringSelection()
        errors = self.view.pan_batch.cb_errors.GetValue()
        res = self.controller.batch_export(self.view.pan_batch.txt_xexpr.Value, yexpr, errors)
        if not res:
            print('error')

    def OnBtnExportDialog(self, evt):
        pars = self.controller.model.get_parameter_names()+['area']
        self.export_dlg = dlg_export_parameters(self.view, pars)
        self.export_dlg.btn_export.Bind(wx.EVT_BUTTON, self.OnExportPars)
        self.export_dlg.Show()

    def OnExportPars(self, evt):
        if self.export_dlg.p.Validate() and self.export_dlg.p.TransferDataFromWindow():
            self.controller.export_pars(self.export_dlg.chk_pars.CheckedStrings,
                                        self.export_dlg.chk_error.IsChecked())
            self.export_dlg.Close()
            del self.export_dlg

    def OnBtnGenerateSetDialog(self, evt):
        tokens =  re.split(r'\s+', self.controller.model.tokens.strip())
        rng = self.controller.selection[1][0].xrng
        self.genset_dlg = dlg_set_from_model(self.view, tokens, rng)
        self.genset_dlg.btn_loadpeaks.Bind(wx.EVT_BUTTON, self.OnLoadFromPars)
        self.genset_dlg.Show()

    def OnLoadFromPars(self, evt):
        if self.genset_dlg.p.Validate() and self.genset_dlg.p.TransferDataFromWindow():
            loadrange = float(self.genset_dlg.txt_from.Value),\
                        float(self.genset_dlg.txt_to.Value)
            loadpts = int(self.genset_dlg.txt_pts.Value)
            self.controller.load_set_from_model(self.genset_dlg.chk_comp.CheckedStrings,
                                                loadrange, loadpts)
            self.genset_dlg.Close()
            del self.genset_dlg

    def OnGenerateDataset(self, evt):
        yexpr = self.view.pan_batch.ch_component.GetStringSelection(),self.view.pan_batch.ch_parameter.GetStringSelection()
        target = self.view.pan_batch.ch_target.GetSelection()
        res = self.controller.generate_dataset(self.view.pan_batch.txt_xexpr.Value, yexpr, target)
        if not res:
            print('error FITINTERACTOR:ONGERNERATEDATASET')

    def OnGenerateDatasetXExpr(self, evt):
        txt = evt.GetEventObject().GetValue()
        x,complete = self.controller.generate_dataset_check_xexpr(txt)
        self.view.pan_batch.txt_xpreview.SetValue(','.join(str(q) for q in x))
        self.view.pan_batch.btn_generate.Enable(complete)
        self.view.pan_batch.btn_export.Enable(complete)

    def OnBatchfitStep(self, evt):
        _,msg = evt.result
        self.controller.batch_step_result(evt.ds, evt.result)

    def OnBatchfitStop(self, evt):
        self.view.pan_batch.btn_stop.Disable()
        self.view.pan_batch.btn_run.Enable()
        self.controller.stop_batch_fit()

    def OnBatchfitStart(self, evt):
        fitopts = dict([('fittype',self.view.fittype), ('maxiter',self.view.maxiter), \
                        ('stepsize',self.view.stepsize), ('autostep',self.view.autostep)])


        self.view.pan_batch.btn_stop.Enable()
        self.view.pan_batch.btn_run.Disable()
        self.controller.start_batchfit(self.view.pan_batch.ch_base.GetStringSelection(),
                                       self.view.pan_batch.ch_initial.GetSelection(),
                                       self.view.pan_batch.ch_order.GetSelection(),
                                       fitopts)

    def OnFitResult(self, evt):
        evt.Skip()
        if hasattr(evt, 'name'):
            #self.view.progress_dialog(step=evt.name)
            # TODO
            pub.sendMessage((self.view.instid,'message'),msg='Fitting {}'.format(evt.name))
        elif hasattr(evt, 'endbatch'):
            self.controller.sync_gui(fit_in_progress=False, batch=True)
            self.view.pan_batch.btn_stop.Disable()
            pub.sendMessage((self.view.instid,'message'),msg='Batch fit finished.')
            pub.sendMessage((self.view.instid,'updateview'))
        elif hasattr(evt, 'end'):
            self.controller.fit_finished(evt.end)
        elif hasattr(evt, 'cancel'):
            self.controller.fit_cancelled(evt.cancel)
        elif hasattr(evt, 'iteration'):
            it, info, res_var = evt.iteration
            pub.sendMessage((self.view.instid,'message'), msg='Fit in progress: iteration {}'.format(it))

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

    def OnNotebookPageChanged(self, evt):
        evt.Skip()
        #pagename = evt.GetEventObject().GetCurrentPage().GetName()
        #print('fitineractor, page changed',msg.GetName())
        #if msg.GetName() == 'fitpanel':
        #    self.controller.page_changed(self.view.nb_fit.GetCurrentPage().GetName())
        #else:
        self.controller.page_changed(evt.GetSelection())


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
        if self.controller._fit_in_progress:
            self.controller.cancel_fit()
        else:
            fitopts = dict([('fittype',self.view.fittype), ('maxiter',self.view.maxiter), \
                            ('stepsize',self.view.stepsize), ('autostep',self.view.autostep)])

            self.controller.start_fit(self.view.limitfitrange, fitopts)

    def OnSelectionChanged(self, plot, dataset):
        self.controller.selection_changed(plot, dataset)

    def OnGuessParameters(self, evt):
        self.controller.find_peaks()

    def OnPickParameters(self, evt):
        self.controller.start_pick_pars()

    def OnClearModel(self, evt):
        self.view.model = ''
        self.controller.new_tokens('')
        
    def OnModelTextFocus(self, evt):
        self.controller.analyze_model()
        
    def OnModelText(self, evt):
        self.controller.new_tokens(evt.GetString())
