__author__ = 'kristukat'

import wx
import wx.stc
import wx.dataview as dv
from . import view as ideview
import logging
from pubsub import pub
from datetime import datetime
import os

logger = logging.getLogger('pom')

class Interactor:

    def Install(self, controller, view):
        self.controller = controller
        self.view = view

        self.fsw = wx.FileSystemWatcher()
        self.fsw.SetOwner(self.view)
        if controller.script_path is not None:
            self.fsw.Add(controller.script_path)

        #self.view.Bind(wx.EVT_FSWATCHER, self.OnWatch)
        self.view.Bind(wx.EVT_TIMER, self.OnWatch)
        self.fsw_timer = wx.Timer(self. view)
        self.fsw_timer.Start(3000)

        self.view.Bind(dv.EVT_DATAVIEW_ITEM_EDITING_DONE, self.OnEditingDone)
        self.view.Bind(dv.EVT_DATAVIEW_ITEM_VALUE_CHANGED, self.OnItemChanged)

        self.view.btn_add_local.Bind(wx.EVT_BUTTON, self.OnAdd)
        self.view.btn_add_prj.Bind(wx.EVT_BUTTON, self.OnAdd)
        self.view.btn_delete_local.Bind(wx.EVT_BUTTON, self.OnDelete)
        self.view.btn_delete_prj.Bind(wx.EVT_BUTTON, self.OnDelete)
        self.view.btn_runcode.Bind(wx.EVT_BUTTON, self.OnExecute)

        self.view.btn_l2p.Bind(wx.EVT_BUTTON, self.OnUpDown)
        self.view.btn_p2l.Bind(wx.EVT_BUTTON, self.OnUpDown)

        self.view.Bind(ideview.EVT_CODELIST_SELECTION_LOST, self.OnSelectionLost)
        self.view.editor.Bind(wx.stc.EVT_STC_MODIFIED, self.OnEditorModified)

        #self.view.btn_delete.Bind(wx.EVT_BUTTON, self.OnDelete)

        #self.view.Bind(wx.EVT_IDLE, self.OnIdle)

        self.view.Bind(ideview.EVT_CODELIST_SELECTED, self.OnListSelect)

        self.view.Bind(wx.EVT_CLOSE, self.OnClose)

    def get_source(self, evt):
        scope = evt.GetEventObject().GetName().split('_')[1]
        ctrl = getattr(self.view, 'lst_{}'.format(scope))
        return scope, ctrl

    def OnItemChanged(self, evt):
        if evt.GetColumn() == 0:
            #row = evt.GetModel().GetRow(evt.GetItem())
            #if evt.GetModel().data[row][0]:
            #    pass
            pub.sendMessage((self.view.instid, 'codeeditor', 'newsymbols'))

    def OnWatch(self, evt):
        ret = self.controller.model['local'].reload(self.view.lst_local.selected)
        if ret is not None:
            need_reload, newsel = ret
            self.view.lst_local.select_row(newsel)

    def OnUpDown(self, evt):
        if self.controller.edit_mode is not None:
            emode = self.controller.edit_mode
            ctrl = getattr(self.view, 'lst_{}'.format(self.controller.edit_mode))
            sel = ctrl.selected
            if sel != -1:
                if evt.GetEventObject().GetName() == 'up' and emode == 'prj':
                    if self.controller.model['prj'].data[sel][1] in self.controller.model['local']:
                        retcode, newname = self.view.text_entry(self.controller.model['prj'].data[sel][1])
                        if not retcode:
                            return
                    else:
                        newname = None
                    self.view.lst_local.GetModel().append_from_embedded(self.view.lst_prj.GetModel(), sel, newname=newname)
                elif evt.GetEventObject().GetName() == 'down' and emode == 'local':
                    if self.controller.model['local'].data[sel][1] in self.controller.model['prj']:
                        retcode, newname = self.view.text_entry(self.controller.model['local'].data[sel][1])
                        if not retcode:
                            return
                    else:
                        newname = None
                    self.view.lst_prj.GetModel().append_from_local(self.view.lst_local.GetModel(), sel, newname)

    def OnExecute(self, evt):
        wx.BeginBusyCursor()
        self.view.txt_result.AppendText('Script execution started at {}\n'.format(datetime.now().strftime('%H:%M:%S')))
        val, errline = self.controller.run(self.view.editor.GetText())

        self.view.txt_result.AppendText('{}\nScript execution finished.\n'.format(val))

        if errline is not None:
            self.view.editor.SelectLine(errline)
        wx.EndBusyCursor()

    def OnClose(self, evt):
        pub.sendMessage((self.view.instid, 'editor', 'close'))

    def OnEditorModified(self, evt):
        if not self.controller.do_not_listen:
            if evt.GetModificationType()&(wx.stc.STC_MOD_INSERTTEXT|wx.stc.STC_MOD_DELETETEXT):
                self.controller.model_update()

    def OnListSelect(self, evt):
        evt.Skip()

        scope = evt.name.split('_')[1]
        if scope == 'local':
            self.view.btn_l2p.Enable()
            self.view.btn_p2l.Disable()
        else:
            self.view.btn_l2p.Disable()
            if self.view._local_enabled:
                self.view.btn_p2l.Enable()

        ctrl = getattr(self.view, evt.name)
        self.controller.edit_mode = scope
        self.controller.editor_push_file(scope, ctrl.selected)
        self.view.show_editor(True)

    def OnSelectionLost(self, evt):
        logger.debug('selection lost')
        self.view.show_editor(False)

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
        def sort_and_select(model, ctrl, row, oldval):
            val = model.data[row][1]
            try:
                base, ext = val.split('.')
            except ValueError:
                val = val.replace('.', '')+'.py'
            else:
                if ext != 'py':
                    val = base+'.py'
            model.data[row][1] = oldval
            if val in model:
                #model.Reset(len(model.data))
                ctrl.select_row(model.index(oldval))
                return
            else:
                model.data[row][1] = val
            if self.controller.rename(model, oldval, row):
                model.sort()
                row = model.index(val)
                ctrl.select_row(row)
            else:
                model.data[row][1] = oldval
                #model.Reset(len(model.data))
                ctrl.select_row(model.index(oldval))
        wx.CallAfter(sort_and_select, model, ctrl, row, oldval)

    def OnAdd(self, evt):
        scope, ctrl = self.get_source(evt)
        row = self.controller.add_entry(scope)
        logger.debug('add entry, row: {}'.format(row))
        self.controller.edit_mode = scope
        ctrl.select_row(row)
        self.view.show_editor(True)
        self.controller.editor_push_file(scope, ctrl.selected)

    def OnDelete(self, evt):
        scope, ctrl = self.get_source(evt)
        self.controller.delete_entry(scope, ctrl.selected)
        ctrl.select_row(max(0, ctrl.selected - 1))
        if ctrl.selected != -1:
            self.controller.editor_push_file(scope, ctrl.selected)



