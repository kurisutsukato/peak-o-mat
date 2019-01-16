#from wx.lib.pubsub import setupkwargs
from wx.lib.pubsub import pub

import wx
from wx import xrc
import os

from . import misc_ui
from .menu import menu_ids

from . import misc

class Interactor(object):
    def __init__(self, id):
        self.view_id = id

    def Install(self, controller, view):
        self.controller = controller
        self.view = view

        def menuitem(name):
            return self.view.GetMenuBar().FindItemById(xrc.XRCID(name))

        self.view.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnNotebookPageChanged)

        self.view.Bind(wx.EVT_MENU, self.OnNew, id=menu_ids['New'])
        self.view.Bind(wx.EVT_MENU, self.OnOpen, id=menu_ids['Open project...'])
        self.view.Bind(wx.EVT_MENU, self.OnSaveAs, id=menu_ids['Save as...'])
        self.view.Bind(wx.EVT_MENU, self.OnSave, id=menu_ids['Save'])
        self.view.Bind(wx.EVT_MENU, self.OnClose, id=menu_ids['Quit'])
        self.view.Bind(wx.EVT_MENU, self.OnImport, id=menu_ids['Import...'])
        self.view.Bind(wx.EVT_MENU, self.OnExport, id=menu_ids['Export...'])
        
        self.view.Bind(wx.EVT_MENU, self.OnShowCodeeditor, id=menu_ids['Code Editor'])
        self.view.Bind(wx.EVT_MENU, self.OnShowDatagrid, id=menu_ids['Data Grid'])
        self.view.Bind(wx.EVT_MENU, self.OnShowNotes, id=menu_ids['Notepad'])
        self.view.Bind(wx.EVT_MENU, self.OnStartServer, id=menu_ids['Start plot server'])

        self.view.Bind(wx.EVT_MENU, self.OnAbout, id=menu_ids['About'])

        self.view.frame_annotations.Bind(wx.EVT_CLOSE, self.OnNotesClose)

        self.view.Bind(wx.EVT_MENU_RANGE, self.OnFileHistory, id=wx.ID_FILE1, id2=wx.ID_FILE9)

        self.view.canvas.Bind(misc_ui.EVT_RANGE, self.OnCanvasNewRange)

        self.view.tb_canvas.Bind(wx.EVT_BUTTON, self.OnCanvasButton)
        self.view.tb_canvas.Bind(wx.EVT_TOGGLEBUTTON, self.OnCanvasButton)

        self.view.Bind(wx.EVT_TEXT, self.OnEditAnnotations, self.view.txt_annotations)

        pub.subscribe(self.pubOnMessage, (self.view_id, 'message'))
        pub.subscribe(self.OnTreeSelect, (self.view_id, 'tree', 'select'))
        pub.subscribe(self.pubOnTreeDelete, (self.view_id, 'tree', 'delete'))
        pub.subscribe(self.OnTreeRename, (self.view_id, 'tree', 'rename'))
        pub.subscribe(self.OnTreeMove, (self.view_id, 'tree', 'move'))
        pub.subscribe(self.OnTreeHide, (self.view_id, 'tree', 'hide'))
        pub.subscribe(self.OnTreeDuplicate, (self.view_id, 'tree', 'duplicate'))
        pub.subscribe(self.OnTreeNewFromVisArea, (self.view_id, 'tree', 'newfromvisarea'))
        pub.subscribe(self.OnTreeInsert, (self.view_id, 'tree', 'insert'))
        pub.subscribe(self.OnTreeCopyToGrid, (self.view_id, 'tree', 'togrid'))
        pub.subscribe(self.OnTreeRemFit, (self.view_id, 'tree', 'remfit'))
        pub.subscribe(self.OnTreeRemTrafo, (self.view_id, 'tree', 'remtrafo'))
        pub.subscribe(self.OnTreeRemWeights, (self.view_id, 'tree', 'remerror'))
        pub.subscribe(self.OnTreeUnmask, (self.view_id, 'tree', 'unmask'))
        pub.subscribe(self.pubOnAddPlot, (self.view_id, 'tree', 'addplot'))
        pub.subscribe(self.OnTreeCopy, (self.view_id, 'tree', 'copy'))
        pub.subscribe(self.OnTreePaste, (self.view_id, 'tree', 'paste'))
        
        pub.subscribe(self.OnSetFromGrid, (self.view_id, 'grid', 'newset'))

        pub.subscribe(self.OnCanvasErase, (self.view_id, 'canvas', 'erase'))
        #em.eventManager.Register(self.OnGotPars, misc_ui.EVT_GOTPARS, self.view.canvas)
        self.view.canvas.Bind(misc_ui.EVT_GOTPARS, self.OnGotPars)
        
        pub.subscribe(self.OnLoadSetFromModel, (self.view_id, 'fitctrl', 'loadset'))
        pub.subscribe(self.OnFitPars2DataGrid, (self.view_id, 'fitctrl', 'parexport'))
        pub.subscribe(self.pubOnStartFit, (self.view_id, 'fitctrl', 'fit'))
        pub.subscribe(self.OnStartPickPars, (self.view_id, 'fitctrl', 'pickpars'))
        pub.subscribe(self.OnEditPars, (self.view_id, 'fitctrl', 'editpars'))
        pub.subscribe(self.OnAttachWeights, (self.view_id, 'fitctrl', 'attachweights'))
        pub.subscribe(self.OnLimitFitRange, (self.view_id, 'fitctrl', 'limitfitrange'))
        pub.subscribe(self.OnPlot, (self.view_id, 'fitctrl', 'plot'))

        pub.subscribe(self.OnPageChanged, (self.view_id, 'notebook', 'pagechanged'))

        pub.subscribe(self.OnProjectModified, (self.view_id, 'changed'))

        self.view.Bind(wx.EVT_CLOSE, self.OnClose)

        pub.subscribe(self.OnEditCode, (self.view_id, 'code', 'changed'))

        pub.subscribe(self.OnFigureShow, (self.view_id, 'figurelist', 'show'))
        pub.subscribe(self.OnFigureShow, (self.view_id, 'figurelist', 'create'))
        pub.subscribe(self.OnFigureDelete, (self.view_id, 'figurelist', 'del'))
        pub.subscribe(self.OnFigureClone, (self.view_id, 'figurelist', 'clone'))

        pub.subscribe(self.OnFigureClose, (self.view_id, 'figure', 'discard'))
        pub.subscribe(self.OnFigureSave, (self.view_id, 'figure', 'save'))

        pub.subscribe(self.pubOnAddSet, (self.view_id, 'set', 'add'))

        pub.subscribe(self.pubOnUpdateView, (self.view_id, 'updateview'))

        pub.subscribe(self.pubOnGenerateDataset, (self.view_id, 'generate_dataset'))
        pub.subscribe(self.pubOnGenerateGrid, (self.view_id, 'generate_grid'))

        pub.subscribe(self.pubOnStopAll, (self.view_id, 'stop_all'))

    def pubOnStopAll(self):
        self.view.Destroy()
        # TODO: muss hier noch mehr hin?

    def pubOnGenerateGrid(self, data, name):
        self.controller.new_datagrid(data, name=name)

    def pubOnGenerateDataset(self, spec, target):
        print('interactor: gen dataset',spec,target)
        if target == 0:
            target = self.controller.add_plot()
        else:
            target -= 1
        if type(spec) == list:
            for s in spec:
                self.controller.add_set(s, target)
        else:
            self.controller.add_set(spec, target)

    def pubOnUpdateView(self):
        self.controller.update_plot()
        self.controller.update_tree()

    def pubOnMessage(self, msg):
        event = misc_ui.ShoutEvent(self.view.GetId(), msg=msg, target=1, blink=0, forever=False)
        wx.PostEvent(self.view, event)

    def pubOnAddSet(self, spec):
        self.controller.add_set(spec)

    def OnStartServer(self, evt):
        menu = self.view.GetMenuBar().GetMenu(3)
        mi = menu.FindItemByPosition(0)
        if self.controller.start_plot_server():
            menu.SetLabel(mi.GetId(), 'Stop plot server')
        else:
            menu.SetLabel(mi.GetId(), 'Start plot server')

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

    def OnTreeCopy(self, msg):
        self.controller.set2clipboard()

    def OnTreePaste(self, msg):
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
                pub.sendMessage(('new'),path=path)
        else:
            self.view.msg_dialog('File not found: \'{}\''.format(path), 'Error')

    def OnNotebookPageChanged(self, evt):
        pub.sendMessage((self.view_id, 'notebook', 'pagechanged'), msg=evt.GetEventObject().GetCurrentPage())

    def OnPageChanged(self, msg):
        self.controller.page_changed(msg.GetName())

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
        
    def OnTreeUnmask(self, msg):
        self.controller.rem_attr('mask', only_sel=True)

    def OnTreeRemWeights(self, msg):
        self.controller.rem_attr('weights', only_sel=True)

    def OnTreeRemFit(self, msg):
        self.controller.rem_attr('mod', only_sel=True)

    def OnTreeRemTrafo(self, msg):
        self.controller.rem_attr('trafo', only_sel=True)

    def OnFitPars2DataGrid(self, msg):
        self.controller.datagrid_append(msg)

    def OnLoadSetFromModel(self, msg):
        model, which, xr, pts = msg
        self.controller.load_set_from_model(model, which, xr, pts)

    def OnGotPars(self, evt):
        mapping = {misc_ui.GOTPARS_MOVE: 'edit',
                   misc_ui.GOTPARS_MOVE: 'move',
                   misc_ui.GOTPARS_DOWN: 'down',
                   misc_ui.GOTPARS_END: 'end'}
        
        self.controller.model_updated(action = mapping[evt.cmd])
        evt.Skip()

    def OnEditPars(self, msg):
        self.controller.model_updated()
        
    def OnStartPickPars(self, msg):
        self.controller.start_pick_pars(*msg)

    def OnSetFromGrid(self, data):
        self.controller.new_sets_from_grid(data)

    def OnTreeCopyToGrid(self, msg):
        self.controller.selection_to_grid()
        
    def OnTreeSelect(self, selection):
        self.controller.selection = selection

    def pubOnTreeDelete(self, msg):
        self.controller.delete_selection(msg)

    def OnTreeRename(self, msg):
        plot, set, name = msg
        wx.CallAfter(self.controller.rename_set, name, (plot, set))

    def OnTreeMove(self, msg):
        self.controller.move_set(*msg)

    def OnTreeHide(self, msg):
        self.controller.hide_selection()

    def OnTreeDuplicate(self, msg):
        self.controller.duplicate_selection(msg)

    def OnTreeNewFromVisArea(self, msg):
        self.controller.crop_selection(msg)

    def OnTreeInsert(self, msg):
        self.controller.insert_plot(msg)

    def OnCanvasNewRange(self, evt):
        xr, yr = evt.range
        self.controller.set_plot_range(xr,yr)

    def OnCanvasButton(self, evt):
        callmap = {'btn_peaks':self.OnCanvasButtonPeaks,
                   'btn_logx':self.OnCanvasButtonLogX,
                   'btn_logy':self.OnCanvasButtonLogY,
                   'btn_style':self.OnCanvasButtonStyle,
                   'btn_zoom':self.OnCanvasButtonZoom,
                   'btn_drag':self.OnCanvasButtonDrag,
                   'btn_erase':self.OnCanvasButtonErase,
                   'btn_auto':self.OnCanvasButtonAuto,
                   'btn_autox':self.OnCanvasButtonAutoX,
                   'btn_autoy':self.OnCanvasButtonAutoY,
                   'btn_auto2fit':self.OnCanvasButtonAuto2Fit}

        tid = evt.GetEventObject().GetName()
        callmap[tid](evt.GetEventObject(), evt.GetId())
        evt.Skip()

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
        self.controller.set_logscale(None,state)
        self.controller.update_plot()
        
    def OnCanvasButtonLogX(self, tb, id):
        state = tb.GetValue()
        self.controller.autoscale()
        self.controller.set_logscale(state, None)
        self.controller.update_plot()
        
    def OnCanvasButtonStyle(self, tb, id):
        state = tb.GetValue()
        self.controller.app_state.line_style = state
        self.controller.update_plot()
        
    def OnCanvasButtonZoom(self, tb, id):
        state = tb.GetValue()
        mode = [None,'zoom'][state]
        self.controller.set_canvas_mode(mode)
        
    def OnCanvasButtonDrag(self, tb, id):
        state = tb.GetValue()
        mode = [None,'drag'][state]
        self.controller.set_canvas_mode(mode)
                
    def OnCanvasButtonErase(self, tb, id):
        state = tb.GetValue()
        mode = [None,'erase'][state]
        self.controller.set_canvas_mode(mode)

    def OnImport(self, evt):
        res = self.view.import_dialog(misc.cwd(),misc.wildcards())
        if res is not None:
            path,one_plot_each = res
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

    def OnClose(self, evt):
        if self.controller.close():
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
                    pub.sendMessage(('new'),path=path)
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
