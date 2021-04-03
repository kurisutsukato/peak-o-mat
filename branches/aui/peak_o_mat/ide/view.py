__author__ = 'kristukat'

import wx
import wx.dataview as dv
import wx.lib.agw.flatnotebook as fnb

from ..controls import PythonSTC
import os

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

class View(wx.Frame):
    def __init__(self, parent):
        super(View, self).__init__(parent, size=(900,500))
        self.parent = parent
        self.setup_controls()
        self.layout()

    def run(self):
        self.Show()
        wx.GetApp().MainLoop()

    def set_tree_model(self, model):
        self.tree.AssociateModel(model)

    def setup_controls(self):
        self.split = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        self.panel = p = wx.Panel(self.split)

        self.tree = dvtc = dv.DataViewCtrl(p, style=dv.DV_ROW_LINES|dv.DV_NO_HEADER| dv.DV_VERT_RULES)
        self.tree.AppendTextColumn("",   0, width=300, mode=dv.DATAVIEW_CELL_EDITABLE)

        self.editor_container = EditorContainer(self.split)
        self.editor_container.new_editor('title')

        self.btn_add = wx.Button(p, label='Add')
        self.btn_delete = wx.Button(p, label='Delete')


    def layout(self):
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(self.tree, 1, wx.EXPAND|wx.ALL, 0)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.btn_add, 1, wx.EXPAND|wx.ALL|wx.BU_EXACTFIT, 2)
        hbox.Add(self.btn_delete, 1, wx.EXPAND|wx.ALL, 2)
        box.Add(hbox, 0, wx.EXPAND)
        self.panel.SetSizer(box)
        #self.Fit()

        min_width = hbox.GetMinSize()[0]
        self.split.SplitVertically(self.panel, self.editor_container, min_width*1.1)
        self.split.SetMinimumPaneSize(min_width*1.1)

    def Hide(self):
        self.Show(False)

    def Show(self, state=True):
        #self.parent.menubar.FindItemById(menu_ids['Data Grid']).Check(state)
        super(View, self).Show(state)

class CodeEditor(PythonSTC):
    def __init__(self, parent, style=wx.BORDER_NONE):
        PythonSTC.__init__(self, parent, -1, style=style)

    # Some methods to make it compatible with how the wxTextCtrl is used
    def SetValue(self, value):
        if wx.USE_UNICODE:
            value = value.decode('iso8859_1')
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

