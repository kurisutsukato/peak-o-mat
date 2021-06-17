__author__ = 'kristukat'

import wx
import wx.stc
import wx.dataview as dv
from . import view as ideview
import logging
from pubsub import pub
from datetime import datetime

logger = logging.getLogger('pom')

class Interactor:

    def Install(self, controller, view):
        self.controller = controller
        self.view = view

        #self.view.tree.Bind(dv.EVT_DATAVIEW_ITEM_CONTEXT_MENU, self.OnContextMenu)
        #self.view.tree.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.OnSelectionChanged)
        #self.view.tree.Bind(dv.EVT_DATAVIEW_ITEM_START_EDITING, self.OnStartEditing)
        self.view.Bind(dv.EVT_DATAVIEW_ITEM_EDITING_DONE, self.OnEditingDone)
        #self.view.lst_prj.Bind(dv.EVT_DATAVIEW_ITEM_EDITING_DONE, self.OnEditingDone)

        self.view.btn_add_local.Bind(wx.EVT_BUTTON, self.OnAdd)
        self.view.btn_add_prj.Bind(wx.EVT_BUTTON, self.OnAdd)
        self.view.btn_delete_local.Bind(wx.EVT_BUTTON, self.OnDelete)
        self.view.btn_delete_prj.Bind(wx.EVT_BUTTON, self.OnDelete)
        self.view.btn_runcode.Bind(wx.EVT_BUTTON, self.OnExecute)

        self.view.Bind(ideview.EVT_CODELIST_SELECTION_LOST, self.OnSelectionLost)
        self.view.Bind(wx.stc.EVT_STC_MODIFIED, self.OnEditorModified)

        #self.view.btn_delete.Bind(wx.EVT_BUTTON, self.OnDelete)

        #self.view.Bind(wx.EVT_IDLE, self.OnIdle)

        self.view.Bind(ideview.EVT_CODELIST_SELECTED, self.OnListSelect)

        self.view.Bind(wx.EVT_CLOSE, self.OnClose)


    def get_source(self, evt):
        scope = evt.GetEventObject().GetName().split('_')[1]
        ctrl = getattr(self.view, 'lst_{}'.format(scope))
        return scope, ctrl

    def OnExecute(self, evt):
        wx.BeginBusyCursor()
        self.view.txt_result.AppendText('Code execution started at {}\n'.format(datetime.now().strftime('%H:%M:%S')))
        val, errline = self.controller.run(self.view.editor.GetText())

        self.view.txt_result.AppendText('{}\nCode execution finished.\n'.format(val))

        if errline is not None:
            self.view.editor.SelectLine(errline)
        wx.EndBusyCursor()

    def OnClose(self, evt):
        pub.sendMessage((self.view.instid, 'editor', 'close'))

    def OnEditorModified(self, evt):
        if evt.GetModificationType()&(wx.stc.STC_MOD_INSERTTEXT|wx.stc.STC_MOD_DELETETEXT):
            self.controller.model_update()

    def OnListSelect(self, evt):
        evt.Skip()
        scope = evt.name.split('_')[1]
        ctrl = getattr(self.view, evt.name)
        self.controller.edit_mode = scope
        self.controller.editor_push_file(scope, ctrl._selected)
        self.view.dummy.Hide()
        self.view.editor.Show()
        self.view.panel_editor.Layout()

    def OnSelectionLost(self, evt):
        logger.debug('selection lost')
        self.view.dummy.Show()
        self.view.editor.Hide()
        self.view.panel_editor.Layout()

    def OnEditingDone(self, evt):
        scope, ctrl = self.get_source(evt)
        row = evt.GetModel().GetRow(evt.GetItem())
        #val = evt.GetValue()
        logger.debug('editing done, new val: "{}"'.format(evt.GetValue()))
        model = evt.GetModel()

        oldval = model.data[row][1]

        # evt.Veto() bringt nichts fuer OSX weil da der neue Wert noch nicht bekannt ist
        # und bevor der event handler nicht beendet wird, sind die Modell Daten noch die alten

        oldval = model.data[row][1]
        logger.debug(oldval)
        def sort_and_select(model, ctrl, row, oldval):
            val = model.data[row][1]
            try:
                base, ext = val.split('.')
            except ValueError:
                val = val.replace('.', '')+'.py'
                logger.debug('name without extension')
            else:
                if ext != 'py':
                    val = base+'.py'
            model.data[row][1] = oldval
            if val in model:
                model.Reset(len(model.data))
                return
            else:
                model.data[row][1] = val
            if self.controller.rename(model, oldval, row):
                model.sort()
                row = model.index(val)
                ctrl.select_row(row)
            else:
                model.data[row][1] = oldval
                model.Reset(len(model.data))
        wx.CallAfter(sort_and_select, model, ctrl, row, oldval)

    def OnAdd(self, evt):
        scope, ctrl = self.get_source(evt)
        row = self.controller.add_entry(scope)
        logger.debug('add entry, row: {}'.format(row))
        ctrl.select_row(row)
        self.controller.editor_push_file(scope, ctrl._selected)

    def OnDelete(self, evt):
        scope, ctrl = self.get_source(evt)
        self.controller.delete_entry(scope, ctrl._selected)
        ctrl.select_row(max(0, ctrl._selected-1))
        if ctrl._selected != -1:
            self.controller.editor_push_file(scope, ctrl._selected)



