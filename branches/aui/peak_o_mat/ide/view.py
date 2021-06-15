__author__ = 'kristukat'

import wx
import wx.dataview as dv
import wx.lib.agw.flatnotebook as fnb

from ..misc_ui import WithMessage
from ..controls import PythonSTC
import logging

logger = logging.getLogger('pom')

from wx.lib import newevent
SelectEvent, EVT_CODELIST_SELECTED = newevent.NewCommandEvent()
NoSelectionEvent, EVT_CODELIST_SELECTION_LOST = newevent.NewCommandEvent()

class CodeList(dv.DataViewCtrl):
    def __init__(self, parent, header, **kwargs):
        super(CodeList, self).__init__(parent, style=wx.BORDER_THEME|dv.DV_ROW_LINES, **kwargs)
        self._selected = -1

        col_chk = self.AppendToggleColumn('', 0, width=40, mode=dv.DATAVIEW_CELL_ACTIVATABLE)
        self.AppendTextColumn(header, 1, width=100, mode=dv.DATAVIEW_CELL_EDITABLE)

        self.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.OnSelect)
        parent.Bind(EVT_CODELIST_SELECTED, self.OnUnselect)

    def OnUnselect(self, evt):
        logger.debug('unselect event from {} received by {}'.format(evt.name, self.GetName()))
        if evt.name != self.GetName():
            self.SetEvtHandlerEnabled(False)
            self.UnselectAll()
            self.SetEvtHandlerEnabled(True)
        evt.Skip()

    def OnSelect(self, evt):
        logger.debug('select event at {}'.format(self.GetName()))
        item = evt.GetItem()
        model = evt.GetModel()
        if item.IsOk():
            self._selected = model.GetRow(item)
            event = SelectEvent(self.GetId(), name=self.GetName())
            wx.PostEvent(self, event)
        elif self._selected != -1:
            self.select_row(self._selected)

    def select_row(self, row):
        logger.debug('select row {}:{}'.format(self.GetName(), row))
        if len(self.GetModel().data) > 0:
            self.Select(self.GetModel().GetItem(row))
            self._selected = row
        else:
            self._selected = -1
            event = NoSelectionEvent(self.GetId(), name=self.GetName())
            wx.PostEvent(self, event)

class EditorContainer(wx.Panel):
    def __init__(self, parent):
        super(EditorContainer, self).__init__(parent, style=wx.BORDER_THEME)

        self.nb = fnb.FlatNotebook(self)

        b = wx.BoxSizer(wx.VERTICAL)
        b.Add(self.nb, 1, wx.EXPAND|wx.ALL, 0)
        self.SetSizer(b)

    def AddPage(self, *args, **kwargs):
        self.nb.AddPage(*args, **kwargs)

    def new_editor(self, title):
        self.nb.AddPage(CodeEditor(self.nb), title)

class View(wx.Frame, WithMessage):
    def __init__(self, parent):
        super(View, self).__init__(parent, size=(900,500))
        WithMessage.__init__(self)

        self.parent = parent
        self.setup_controls()
        self.layout()

    def set_model(self, scope, model):
        assert scope in ['local', 'prj']

        if scope == 'local':
            self.lst_local.AssociateModel(model)
        elif scope == 'prj':
            self.lst_prj.AssociateModel(model)

    def run(self):
        pass
        #self.Show()
        #wx.GetApp().MainLoop()

    def setup_controls(self):
        self.split_v = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        self.panel = p = wx.Panel(self.split_v)

        self.lst_local = CodeList(self.panel, 'Local', name='lst_local')
        self.lst_prj = CodeList(self.panel, 'Embedded', name='lst_prj')

        self.editor = CodeEditor(self.split_v)

        self.btn_l2p = wx.Button(self.panel, label='Down')
        self.btn_p2l = wx.Button(self.panel, label='Up')

        self.btn_add_local = wx.Button(p, label='New', name='new_local')
        self.btn_delete_local = wx.Button(p, label='Delete', name='del_local')
        self.btn_add_prj = wx.Button(p, label='New', name='new_prj')
        self.btn_delete_prj = wx.Button(p, label='Delete', name='del_prj')

    def layout(self):
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(self.lst_local, 1, wx.EXPAND|wx.ALL, 0)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.btn_add_local, 1, wx.EXPAND|wx.ALL, 2)
        hbox.Add(self.btn_delete_local, 1, wx.EXPAND|wx.ALL, 2)
        box.Add(hbox, 0, wx.EXPAND)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.btn_l2p, 0, wx.ALL, 2)
        hbox.Add(self.btn_p2l, 0, wx.ALL, 2)
        box.Add(hbox, 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 10)

        box.Add(self.lst_prj, 1, wx.EXPAND | wx.ALL, 0)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.btn_add_prj, 1, wx.EXPAND|wx.ALL|wx.BU_EXACTFIT, 2)
        hbox.Add(self.btn_delete_prj, 1, wx.EXPAND|wx.ALL, 2)
        box.Add(hbox, 0, wx.EXPAND)

        self.panel.SetSizer(box)
        #self.Fit()

        min_width = hbox.GetMinSize()[0]
        self.split_v.SplitVertically(self.panel, self.editor, int(min_width * 1.1))
        self.split_v.SetMinimumPaneSize(int(min_width*1.1))

class CodeEditor(PythonSTC):
    def __init__(self, parent, style=wx.BORDER_NONE):
        PythonSTC.__init__(self, parent, -1, style=style)

    # Some methods to make it compatible with how the wxTextCtrl is used
    def SetValue(self, value):
        val = self.GetReadOnly()
        self.SetReadOnly(False)
        self.SetText(value)
        self.EmptyUndoBuffer()
        self.SetSavePoint()
        self.SetReadOnly(val)

    def SetEditable(self, val):
        self.SetReadOnly(not val)

    def IsModified(self):
        return self.GetModify()

    def Clear(self):
        self.ClearAll()

    def SetInsertionPoint(self, pos):
        self.SetCurrentPos(pos)
        self.SetAnchor(pos)

    def ShowPosition(self, pos):
        line = self.LineFromPosition(pos)
        #self.EnsureVisible(line)
        self.GotoLine(line)

    def GetLastPosition(self):
        return self.GetLength()

    def GetPositionFromLine(self, line):
        return self.PositionFromLine(line)

    def GetRange(self, start, end):
        return self.GetTextRange(start, end)

    def GetSelection(self):
        return self.GetAnchor(), self.GetCurrentPos()

    def SetSelection(self, start, end):
        self.SetSelectionStart(start)
        self.SetSelectionEnd(end)

    def SelectLine(self, line):
        start = self.PositionFromLine(line)
        end = self.GetLineEndPosition(line)
        self.SetSelection(start, end)

    def RegisterModifiedEvent(self, eventHandler):
        self.Bind(wx.stc.EVT_STC_CHANGE, eventHandler)

if __name__ == '__main__':
    app = wx.App()
    f = View(None)
    f.Show()
    app.MainLoop()

