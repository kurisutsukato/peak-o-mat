from pubsub import pub

import wx
import wx.aui as aui

from wx import xrc
import os

from . import misc_ui

from . import misc


# TODO: implement a 'set attribute changed' event

class Interactor(object):
    def Install(self, controller, view):
        self.controller = controller
        self.view = view

        menu_ids = self.view.menu_factory.menu_ids
        module_menu_ids = self.view.menu_factory.module_menu_ids

        def menuitem(name):
            return self.view.GetMenuBar().FindItemById(xrc.XRCID(name))

        self.view.Bind(wx.EVT_MENU, self.OnNew, id=menu_ids['New'])
        self.view.Bind(wx.EVT_MENU, self.OnOpen, id=menu_ids['Open project...'])
        self.view.Bind(wx.EVT_MENU, self.OnSaveAs, id=menu_ids['Save as...'])
        self.view.Bind(wx.EVT_MENU, self.OnSave, id=menu_ids['Save'])
        self.view.Bind(wx.EVT_MENU, self.OnMenuClose, id=menu_ids['Quit'])
        self.view.Bind(wx.EVT_MENU, self.OnImport, id=menu_ids['Import...'])
        self.view.Bind(wx.EVT_MENU, self.OnExport, id=menu_ids['Export...'])

        self.view.Bind(wx.EVT_MENU, self.OnShowCodeeditor, id=menu_ids['Code Editor'])
        self.view.Bind(wx.EVT_MENU, self.OnShowDatagrid, id=menu_ids['Data Grid'])
        self.view.Bind(wx.EVT_MENU, self.OnShowNotes, id=menu_ids['Notepad'])

        self.view.Bind(wx.EVT_MENU, self.OnAbout, id=menu_ids['About'])

        for mid, name in module_menu_ids.items():
            if type(name) == str:
                self.view.Bind(wx.EVT_MENU, lambda evt, mid=mid: self.OnMenuShowHideModule(evt, mid), id=mid)

        self.view.frame_annotations.Bind(wx.EVT_CLOSE, self.OnNotesClose)

        self.view.Bind(wx.EVT_MENU_RANGE, self.OnFileHistory, id=wx.ID_FILE1, id2=wx.ID_FILE9)

        self.view.canvas.Bind(misc_ui.EVT_RANGE, self.OnCanvasNewRange)

        self.view.tb_canvas.Bind(wx.EVT_BUTTON, self.OnCanvasButton)
        self.view.tb_canvas.Bind(wx.EVT_TOGGLEBUTTON, self.OnCanvasButton)

        self.view.Bind(wx.EVT_TEXT, self.OnEditAnnotations, self.view.txt_annotations)

        self.view._mgr.Bind(aui.EVT_AUI_PANE_CLOSE, self.OnModuleCloseButton)
        self.view._mgr.Bind(aui.EVT_AUI_PANE_ACTIVATED, self.OnModuleActivated)

        pub.subscribe(self.pubOnMessage, (self.view.instid, 'message'))
        pub.subscribe(self.OnTreeSelect, (self.view.instid, 'tree', 'select'))
        pub.subscribe(self.pubOnTreeDelete, (self.view.instid, 'tree', 'delete'))
        pub.subscribe(self.OnTreeRename, (self.view.instid, 'tree', 'rename'))
        pub.subscribe(self.OnTreeMove, (self.view.instid, 'tree', 'move'))
        pub.subscribe(self.OnTreeHide, (self.view.instid, 'tree', 'hide'))
        pub.subscribe(self.OnTreeDuplicate, (self.view.instid, 'tree', 'duplicate'))
        pub.subscribe(self.OnTreeNewFromVisArea, (self.view.instid, 'tree', 'newfromvisarea'))
        pub.subscribe(self.OnTreeInsert, (self.view.instid, 'tree', 'insert'))
        pub.subscribe(self.OnTreeCopyToGrid, (self.view.instid, 'tree', 'togrid'))
        pub.subscribe(self.OnTreeRemFit, (self.view.instid, 'tree', 'remfit'))
        pub.subscribe(self.OnTreeRemTrafo, (self.view.instid, 'tree', 'remtrafo'))
        pub.subscribe(self.OnTreeRemWeights, (self.view.instid, 'tree', 'remerror'))
        pub.subscribe(self.OnTreeUnmask, (self.view.instid, 'tree', 'unmask'))
        pub.subscribe(self.pubOnAddPlot, (self.view.instid, 'tree', 'addplot'))
        pub.subscribe(self.OnTreeCopy, (self.view.instid, 'tree', 'copy'))
        pub.subscribe(self.OnTreePaste, (self.view.instid, 'tree', 'paste'))

        pub.subscribe(self.OnSetFromGrid, (self.view.instid, 'grid', 'newset'))

        pub.subscribe(self.OnCanvasErase, (self.view.instid, 'canvas', 'erase'))

        self.view.canvas.Bind(misc_ui.EVT_GOTPARS, self.OnGotPars)

        pub.subscribe(self.OnLoadSetFromModel, (self.view.instid, 'fitctrl', 'loadset'))
        pub.subscribe(self.OnFitPars2DataGrid, (self.view.instid, 'fitctrl', 'parexport'))
        pub.subscribe(self.pubOnStartFit, (self.view.instid, 'fitctrl', 'fit'))
        pub.subscribe(self.OnStartPickPars, (self.view.instid, 'fitctrl', 'pickpars'))
        pub.subscribe(self.OnEditPars, (self.view.instid, 'fitctrl', 'editpars'))
        pub.subscribe(self.OnAttachWeights, (self.view.instid, 'fitctrl', 'attachweights'))
        pub.subscribe(self.OnLimitFitRange, (self.view.instid, 'fitctrl', 'limitfitrange'))
        pub.subscribe(self.OnPlot, (self.view.instid, 'fitctrl', 'plot'))

        pub.subscribe(self.OnProjectModified, (self.view.instid, 'changed'))

        self.view.Bind(wx.EVT_CLOSE, self.OnClose)

        pub.subscribe(self.OnEditCode, (self.view.instid, 'code', 'changed'))

        pub.subscribe(self.OnFigureShow, (self.view.instid, 'figurelist', 'show'))
        pub.subscribe(self.OnFigureShow, (self.view.instid, 'figurelist', 'create'))
        pub.subscribe(self.OnFigureDelete, (self.view.instid, 'figurelist', 'del'))
        pub.subscribe(self.OnFigureClone, (self.view.instid, 'figurelist', 'clone'))

        pub.subscribe(self.OnFigureClose, (self.view.instid, 'figure', 'discard'))
        pub.subscribe(self.OnFigureSave, (self.view.instid, 'figure', 'save'))

        pub.subscribe(self.pubOnAddSet, (self.view.instid, 'set', 'add'))

        pub.subscribe(self.pubOnUpdateView, (self.view.instid, 'updateview'))

        pub.subscribe(self.pubOnGenerateDataset, (self.view.instid, 'generate_dataset'))
        pub.subscribe(self.pubOnGenerateGrid, (self.view.instid, 'generate_grid'))

        pub.subscribe(self.pubOnStopAll, (self.view.instid, 'stop_all'))

        pub.subscribe(self.pubOnUpdatePlot, (self.view.instid, 'updateplot'))

        #pub.subscribe(self.pubOnCancelSpecialMode, (self.view.instid, 'canvasmode'))

    #def pubOnCancelSpecialMode(self):
    #    print('cancel')

    def pubOnStopAll(self):
        return
        self.view.Destroy()
        # TODO: muss hier noch mehr hin?

    def pubOnGenerateGrid(self, data, name):
        self.controller.new_datagrid(data, name=name)

    def pubOnGenerateDataset(self, spec, target):
        # print('interactor: gen dataset',spec,target)
        if target == 0:
            target = self.controller.add_plot()
        else:
            target -= 1
        if type(spec) == list:
            for s in spec:
                self.controller.add_set(s, target)
        else:
            self.controller.add_set(spec, target)

    def pubOnUpdatePlot(self):
        self.controller.update_plot()

    def pubOnUpdateView(self):
        self.controller.update_plot()
        self.controller.update_tree()

    def pubOnMessage(self, msg, blink=None):
        event = misc_ui.ShoutEvent(self.view.GetId(), msg=msg, target=1, blink=blink, forever=False)
        wx.PostEvent(self.view, event)

    def pubOnAddSet(self, spec):
        self.controller.add_set(spec)

    def OnModuleCloseButton(self, evt):
        m = evt.GetPane().name
        self.controller._modules[m].hide()
        for mid, name in self.view.menu_factory.module_menu_ids.items():
            if name == m:
                self.view.check_module_menu(mid, False)
        evt.Skip()

    def OnModuleActivated(self, evt):
        pub.sendMessage((self.view.instid, 'module', 'focuschanged'), newfocus=evt.GetPane().name)

    def OnMenuShowHideModule(self, evt, mid):
        auipane = self.view._mgr.GetPane(self.view.menu_factory.module_menu_ids[mid])
        if evt.IsChecked():
            auipane.Float()
        auipane.Show(evt.IsChecked())
        m = self.controller._modules[self.view.menu_factory.module_menu_ids[mid]]
        m.show(evt.IsChecked())
        self.view._mgr.Update()

    def OnFigureClose(self):
        self.controller.create_or_show_figure(False, discard=True)

    def OnFigureSave(self):
        self.controller.create_or_show_figure(False)

    def OnFigureClone(self, msg):
        self.controller.clone_figure(msg)

    def OnFigureDelete(self, msg):
        self.controller.delete_figure(msg)

    def OnFigureShow(self, msg):
        self.controller.create_or_show_figure(True, model=msg)

    def OnTreeCopy(self):
        self.controller.set2clipboard()

    def OnTreePaste(self):
        self.controller.clipboard2set()

    def OnProjectModified(self):
        self.controller.project_modified = True

    def OnAbout(self, evt):
        self.view.about_dialog()

    def OnFileHistory(self, evt):
        filenum = evt.GetId() - wx.ID_FILE1
        path = self.controller.open_recent(filenum)
        if path is not None and os.path.exists(path):
            if self.controller.virgin:
                self.controller.open_project(path)
            else:
                pub.sendMessage((self.view.instid, 'new'), path=path)
        else:
            self.view.msg_dialog('File not found: \'{}\''.format(path), 'Error')

    # TODO: obnsolete
    def OnNotebookPageChanged(self, evt):
        pub.sendMessage((self.view.instid, 'notebook', 'pagechanged'), msg=evt.GetEventObject().GetCurrentPage())

    def OnEditAnnotations(self, evt):
        self.controller.annotations_changed(self.view.annotations)

    def OnCanvasErase(self, msg):
        self.controller.delete_points(msg)

    def OnPlot(self, msg):
        self.controller.update_plot()

    def OnLimitFitRange(self, msg):
        self.controller.set_limit_fitrange(msg)

    def OnAttachWeights(self, msg):
        self.controller.attach_weights_to_set(msg)

    def pubOnStartFit(self, msg):
        self.controller.start_fit(*msg)

    def pubOnAddPlot(self, msg):
        self.controller.add_plot()

    def OnTreeUnmask(self):
        self.controller.rem_attr('mask', only_sel=True)

    def OnTreeRemWeights(self):
        self.controller.rem_attr('weights', only_sel=True)

    def OnTreeRemFit(self):
        self.controller.rem_attr('mod', only_sel=True)
        pub.sendMessage((self.view.instid, 'delmod'))

    def OnTreeRemTrafo(self):
        self.controller.rem_attr('trafo', only_sel=True)

    def OnFitPars2DataGrid(self, msg):
        self.controller.datagrid_append(msg)

    def OnLoadSetFromModel(self, msg):
        model, which, xr, pts = msg
        self.controller.load_set_from_model(model, which, xr, pts)

    def OnGotPars(self, evt):
        mapping = {misc_ui.GOTPARS_MOVE: 'edit',  # edit scheints nicht zu geben
                   misc_ui.GOTPARS_MOVE: 'move',
                   misc_ui.GOTPARS_DOWN: 'down',
                   misc_ui.GOTPARS_END: 'end'}
        self.controller.model_updated(action=mapping[evt.cmd])
        evt.Skip()

    def OnEditPars(self, msg):
        self.controller.model_updated()

    def OnStartPickPars(self, msg):
        pub.sendMessage((self.view.instid, 'canvas', 'newmode'), mode=None)
        self.controller.set_canvas_mode(None)
        self.controller.start_pick_pars(*msg)

    def OnSetFromGrid(self, data):
        self.controller.new_sets_from_grid(data)

    def OnTreeCopyToGrid(self, msg):
        self.controller.selection_to_grid()

    def OnTreeSelect(self, selection):
        self.controller.selection = selection

    def pubOnTreeDelete(self):
        self.controller.delete_selection()

    def OnTreeRename(self, msg):
        # TODO: wird vermutlich nicht mehr benutzt
        print('interactor:ontreerename')
        plot, set, name = msg
        wx.CallAfter(self.controller.rename_set, name, (plot, set))

    def OnTreeMove(self, msg):
        self.controller.move_set(*msg)

    def OnTreeHide(self):
        self.controller.hide_selection()

    def OnTreeDuplicate(self):
        self.controller.duplicate_selection()

    def OnTreeNewFromVisArea(self, msg):
        self.controller.crop_selection(msg)

    def OnTreeInsert(self, msg):
        self.controller.insert_plot(msg)

    def OnCanvasNewRange(self, evt):
        xr, yr = evt.range
        self.controller.set_plot_range(xr, yr)

    def OnCanvasButton(self, evt):
        callmap = {'btn_peaks': self.OnCanvasButtonPeaks,
                   'btn_logx': self.OnCanvasButtonLogX,
                   'btn_logy': self.OnCanvasButtonLogY,
                   'btn_style': self.OnCanvasButtonStyle,
                   'btn_zoom': self.OnCanvasButtonZoom,
                   'btn_drag': self.OnCanvasButtonDrag,
                   'btn_erase': self.OnCanvasButtonErase,
                   'btn_auto': self.OnCanvasButtonAuto,
                   'btn_autox': self.OnCanvasButtonAutoX,
                   'btn_autoy': self.OnCanvasButtonAutoY,
                   'btn_auto2fit': self.OnCanvasButtonAuto2Fit,
                   'btn_fast': self.OnCanvasButtonFast}

        tid = evt.GetEventObject().GetName()
        callmap[tid](evt.GetEventObject(), evt.GetId())


    def OnCanvasButtonFast(self, tb, id):
        state = tb.GetValue()
        self.controller.app_state.fast_display = state
        self.controller.update_plot()

    def OnCanvasButtonAuto(self, *args):
        self.controller.autoscale()

    def OnCanvasButtonAutoX(self, *args):
        self.controller.autoscale(X=True)

    def OnCanvasButtonAutoY(self, *args):
        self.controller.autoscale(Y=True)

    def OnCanvasButtonAuto2Fit(self, *args):
        self.controller.autoscale(fit=True)

    def OnCanvasButtonPeaks(self, tb, id):
        state = tb.GetValue()
        self.controller.app_state.show_peaks = state
        self.controller.update_plot()

    def OnCanvasButtonLogY(self, tb, id):
        state = tb.GetValue()
        self.controller.autoscale()
        self.view.canvas.setLogScale([None, state])
        self.controller.update_plot()

    def OnCanvasButtonLogX(self, tb, id):
        state = tb.GetValue()
        self.controller.autoscale()
        self.view.canvas.setLogScale([state, None])
        self.controller.update_plot()

    def OnCanvasButtonStyle(self, tb, id):
        state = tb.GetValue()
        self.controller.app_state.line_style = state
        self.controller.update_plot()

    def OnCanvasButtonZoom(self, tb, id):
        state = tb.GetValue()
        mode = [None, 'zoom'][state]
        self.controller.set_canvas_mode(mode)

    def OnCanvasButtonDrag(self, tb, id):
        state = tb.GetValue()
        mode = [None, 'drag'][state]
        self.controller.set_canvas_mode(mode)

    def OnCanvasButtonErase(self, tb, id):
        state = tb.GetValue()
        mode = [None, 'erase'][state]
        self.controller.set_canvas_mode(mode)

    def OnImport(self, evt):
        res = self.view.import_dialog(misc.cwd(), misc.wildcards())
        if res is not None:
            path, one_plot_each = res
            self.controller.import_data(path, one_plot_each)

    def OnExport(self, evt):
        self.controller.show_export_dialog()

    def OnShowDatagrid(self, evt):
        self.controller.show_datagrid(evt.IsChecked())

    def OnShowNotes(self, evt):
        self.controller.show_notes(evt.IsChecked())

    def OnShowCodeeditor(self, evt):
        self.controller.show_codeeditor(evt.IsChecked())

    def OnEditCode(self, msg):
        self.controller.code_changed()

    def OnMenuClose(self, evt):
        self.view.Close()

    def OnClose(self, evt):
        if self.controller.close():
            self.view._mgr.UnInit()
            evt.Skip()
        else:
            evt.Veto()

    def OnNotesClose(self, evt):
        self.controller.notes_close()

    def OnNew(self, evt):
        pub.sendMessage(('new'))

    def OnOpen(self, evt):
        path = self.view.load_file_dialog(misc.cwd())

        if path is not None:
            if os.path.exists(path):
                if self.controller.virgin:
                    self.controller.open_project(path)
                else:
                    pub.sendMessage((self.view.instid, 'new'), path=path)
                    print('send new message')
            else:
                self.view.msg_dialog('File not found: \'{}\''.format(path), 'Error')

    def OnSave(self, evt):
        if self.controller.project.path is None:
            self.OnSaveAs(None)
        else:
            self.controller.save_project()

    def OnSaveAs(self, evt):
        path = self.view.save_file_dialog(misc.cwd())
        if path is not None:
            self.controller.save_project(path)

    def OnPgSetup(self, evt):
        self.view.canvas.PageSetup()

    def OnPrint(self, evt):
        self.view.canvas.Printout()

    def OnExportBmp(self, evt):
        self.view.canvas.SaveFile()
