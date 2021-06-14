__author__ = 'kristukat'

import wx
import wx.stc
import wx.dataview as dv
from . import view as ideview
import logging

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

        self.view.Bind(ideview.EVT_CODELIST_SELECTION_LOST, self.OnSelectionLost)
        self.view.Bind(wx.stc.EVT_STC_MODIFIED, self.OnEditorModified)

        #self.view.btn_delete.Bind(wx.EVT_BUTTON, self.OnDelete)

        #self.view.Bind(wx.EVT_IDLE, self.OnIdle)

        self.view.Bind(ideview.EVT_CODELIST_SELECTED, self.OnListSelect)

    def get_source(self, evt):
        scope = evt.GetEventObject().GetName().split('_')[1]
        ctrl = getattr(self.view, 'lst_{}'.format(scope))
        return scope, ctrl

    def OnEditorModified(self, evt):
        if evt.GetModificationType()&(wx.stc.STC_MOD_INSERTTEXT|wx.stc.STC_MOD_DELETETEXT):
            self.controller.model_update()

    def OnListSelect(self, evt):
        evt.Skip()
        scope = evt.name.split('_')[1]
        ctrl = getattr(self.view, evt.name)
        self.controller.edit_mode = scope
        self.controller.editor_push_file(scope, ctrl._selected)

    def OnSelectionLost(self, evt):
        logger.warning('selection lost')
        self.view.editor.SetValue('lost!')

    def OnEditingDone(self, evt):
        scope, ctrl = self.get_source(evt)
        row = evt.GetModel().GetRow(evt.GetItem())
        val = evt.GetValue()
        logger.warning('editing done, new val: {}'.format(val))
        model = evt.GetModel()

        if val is not None and val in model:
            evt.Veto()
        else:
            oldval = model.data[row][1]
            def sort_and_select(model, ctrl, val, row, oldval):
                if val is None:
                    val = model.data[row][1]
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

            wx.CallAfter(sort_and_select, model, ctrl, val, row, oldval)

    def OnStartEditing(self, evt):
        obj = self.controller.model.ItemToObject(self.view.tree.Selection)
        if not obj.isentry:
            evt.Veto()
        else:
            evt.Skip()

    def OnAdd(self, evt):
        scope = evt.GetEventObject().GetName().split('_')[1]
        ctrl = getattr(self.view, 'lst_{}'.format(scope))
        row = self.controller.add_entry(scope)
        ctrl.select_row(row)
        self.controller.editor_push_file(scope, ctrl._selected)

    def OnDelete(self, evt):
        scope = evt.GetEventObject().GetName().split('_')[1]
        ctrl = getattr(self.view, 'lst_{}'.format(scope))
        self.controller.delete_entry(scope, ctrl._selected)
        ctrl.select_row(max(0, ctrl._selected-1))
        if ctrl._selected != -1:
            self.controller.editor_push_file(scope, ctrl._selected)

    def OnIdle(self, evt):

        self.view.Freeze()

        self.view.Thaw()

    def OnSelectionChanged(self, evt):
        ctrl = evt.GetEventObject()
        print(ctrl.HasSelection())

        #print self.controller.model.ItemToObject(ctrl.Selection).label

    def OnContextMenu(self, event):
        event.Skip()
        obj = self.controller.model.ItemToObject(self.view.tree.Selection)

        if not obj.isentry:
            return

        if not hasattr(self, "_id1"):
            self._id1 = wx.NewId()
            self._id2 = wx.NewId()
            self.view.Bind(wx.EVT_MENU, self.OnTransfer, id=self._id1)
            self.view.Bind(wx.EVT_MENU, self.OnRename, id=self._id2)

        islocal = obj.type[0] == 'local'

        # make a menu
        menu = wx.Menu()
        if islocal:
            menu.Append(self._id1, "Embed in project file")
        else:
            menu.Append(self._id1, "Move to local storage")
        menu.Append(self._id2, "Rename")

        self.view.split.PopupMenu(menu)
        menu.Destroy()

    def OnTransfer(self, evt):
        print(evt)

    def OnRename(self, evt):
        self.view.tree.EditItem(self.view.tree.Selection, self.view.tree.GetColumn(0))


