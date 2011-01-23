import wx
import wx.grid

import sys
import csv, codecs
import os
from StringIO import StringIO
from copy import copy
import numpy as N

from io import UnicodeReader, PomDialect, asfloat

delimiters = [',',';',':',' ','\t']
choices = ['comma','semicolon','colon','space','tabulator']

class Dialog(wx.Dialog):
    def __init__(self, dialect):
        wx.Dialog.__init__(self, None, -1, 'csv wizard')
        self.dialect = dialect
        self.gui_init()

    def gui_init(self):
        self.grid = wx.grid.Grid(self)
        self.grid.SetMinSize((400,200))
        self.grid.SetRowLabelSize(0)
        self.grid.SetColLabelSize(0)
        self.grid.SetRowLabelAlignment(wx.ALIGN_LEFT, wx.ALIGN_CENTER)

        self.ch_delimiter = wx.Choice(self, -1, choices=choices)
        self.ch_delimiter.SetSelection(delimiters.index(self.dialect.delimiter))
        self.chkb_stripindices = wx.CheckBox(self, -1, 'strip row/col indices')
        self.chkb_collabels = wx.CheckBox(self, -1, 'first row contains column labels')
        self.chkb_rowlabels = wx.CheckBox(self, -1, 'first column contains row labels')
        self.chkb_rowlabels.SetValue(self.dialect.has_rl)
        self.chkb_collabels.SetValue(self.dialect.has_cl)
        self.btn_import = wx.Button(self, -1, 'import')

        outer = wx.BoxSizer(wx.VERTICAL)
        flexgrid = wx.FlexGridSizer(cols=3, vgap=2, hgap=2)
        flexgrid.Add(self.chkb_collabels, 0, wx.ALIGN_CENTER_VERTICAL)
        flexgrid.Add(wx.Window(self, size=(20,0)))
        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(wx.StaticText(self, -1, 'cell delimiter'), 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)
        box.Add(self.ch_delimiter, 0, wx.ALIGN_CENTER_VERTICAL|wx.EXPAND)
        flexgrid.Add(box)
        flexgrid.Add(self.chkb_rowlabels, 0, wx.ALIGN_CENTER_VERTICAL)
        flexgrid.Add(wx.Window(self,size=(20,0)))
        flexgrid.Add(self.chkb_stripindices, 0, wx.ALIGN_CENTER_VERTICAL)
        outer.Add(flexgrid, 0, wx.ALL|wx.EXPAND, 5)
        outer.Add(self.grid, 1, wx.ALL|wx.EXPAND, 5)
        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(wx.Window(self,size=(20,0)), 1)
        box.Add(self.btn_import)
        outer.Add(box, 0, wx.ALL|wx.EXPAND, 5)
        self.SetSizer(outer)
        self.Fit()

        self.show_labels(self.dialect.has_rl, self.dialect.has_cl)
        
    def enable_import(self, state=True):
        self.btn_import.Enable(state)

    def show_labels(self, rlabs, clabs):
        self.grid.SetRowLabelSize([0,120][int(rlabs)])
        self.grid.SetColLabelSize([0,20][int(clabs)])
        
    def update(self):
        return
        # this does not work when run from 'ipython -wthread'
        wx.CallAfter(self.grid.AutoSizeColumns)
        
class Table(wx.grid.PyGridTableBase):
    def __init__(self):
        wx.grid.PyGridTableBase.__init__(self)

        self.colLabels = [u'']*10
        self.rowLabels = [u'']*10
        self._data = [[0]*10]*10

        self.currentRows = 10
        self.currentCols = 10

    def _get_data(self):
        return self._data
    def _set_data(self, data):
        try:
            data[0][0]
        except IndexError:
            data = [data]
        self._data = data
        self.Update()
    data = property(_get_data, _set_data)

    def GetNumberRows(self):
        return len(self.data)

    def GetNumberCols(self):
        return len(self.data[0])

    def IsEmptyCell(self, row, col):
        try:
            return not self.data[row][col]
        except:
            return True

    def GetValue(self, row, col):
        try:
            return unicode(self.data[row][col])
        except IndexError:
            return ''

    def SetValue(self, row, col, value):
        self.data[row][col] = value

    def GetColLabelValue(self, col):
        try:
            return unicode(self.colLabels[col])
        except:
            return u''

    def GetRowLabelValue(self, row):
        try:
            return unicode(self.rowLabels[row])
        except:
            return u''

    def Update(self):
        self.GetView().BeginBatch() 
        for current, new, delmsg, addmsg in [ 
            (self.currentRows, self.GetNumberRows(), wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED), 
            (self.currentCols, self.GetNumberCols(), wx.grid.GRIDTABLE_NOTIFY_COLS_DELETED, wx.grid.GRIDTABLE_NOTIFY_COLS_APPENDED)]:
            if new < current: 
                msg = wx.grid.GridTableMessage(self, delmsg, new, current-new) 
                self.GetView().ProcessTableMessage(msg) 
            elif new > current: 
                msg = wx.grid.GridTableMessage(self, addmsg, new-current) 
                self.GetView().ProcessTableMessage(msg) 
        self.GetView().EndBatch() 
        self.currentRows = self.GetNumberRows()
        self.currentCols = self.GetNumberCols()

class Interactor:
    def Install(self, view, controller):
        self.controller = controller
        self.view = view
        self.view.Bind(wx.EVT_CHOICE, self.OnDelimiter, self.view.ch_delimiter)
        self.view.Bind(wx.EVT_CHECKBOX, self.OnStripIndices, self.view.chkb_stripindices)
        self.view.Bind(wx.EVT_CHECKBOX, self.OnRowLabels, self.view.chkb_rowlabels)
        self.view.Bind(wx.EVT_CHECKBOX, self.OnColLabels, self.view.chkb_collabels)

        self.view.Bind(wx.EVT_BUTTON, self.OnImport, self.view.btn_import)
        self.view.Bind(wx.EVT_CLOSE, self.OnClose)
        
    def OnImport(self, evt):
        self.view.EndModal(True)

    def OnClose(self, evt):
        self.view.EndModal(False)
        
    def OnStripIndices(self, evt):
        self.controller.strip_indices = self.view.chkb_stripindices.GetValue()
        self.controller.update_table()
        
    def OnDelimiter(self, evt):
        self.view.chkb_rowlabels.SetValue(False)
        self.view.chkb_collabels.SetValue(False)
        self.controller.labels(has_rl=False,has_cl=False)
        self.controller.delimiter(self.view.ch_delimiter.GetSelection())
        
    def OnRowLabels(self, evt):
        has_rl=self.view.chkb_rowlabels.GetValue()
        self.controller.labels(has_rl=has_rl)

    def OnColLabels(self, evt):
        has_cl=self.view.chkb_collabels.GetValue()
        self.controller.labels(has_cl=has_cl)

class CSVWizard:
    strip_indices = False
    dialect = PomDialect()
    
    def __init__(self, path):
        self.view = Dialog(self.dialect)
        Interactor().Install(self.view, self)
        self.table = Table()
        self.view.grid.SetTable(self.table, False)

        self.path = path

        self.update_table()

    def show(self):
        return self.view.ShowModal()

    def close(self):
        self.view.Destroy()
        del self.view
        del self

    def read(self, all=False):
        if not hasattr(self, 'rawdata') or all:
            self.rawdata = open(self.path).readlines()
            if not all:
                self.rawdata = self.rawdata[:10]
            self.rawdata = ''.join(self.rawdata)
        
        data = []
        csvr = UnicodeReader(StringIO(self.rawdata), dialect=self.dialect)

        try:
            for row in csvr:
                data.append(row)
        except UnicodeDecodeError, msg:
            wx.MessageBox(unicode(msg), 'Error', wx.ICON_ERROR)

        return data

    def parse(self, all=False):
        data = self.read(all)
        
        cl = data[0]
        rl = [list(x) for x in zip(*data)][0]

        if self.dialect.has_cl:
            rl = rl[1:]
            data = data[1:]
        if self.dialect.has_rl:
            cl = cl[1:]
            data = [list(x) for x in zip(*data)][1:]
            data = [list(x) for x in zip(*data)]

        if self.dialect.has_rl is not None and self.strip_indices:
            strip = False
            for n,r in enumerate(rl):
                if r.find(unicode(n)) != 0:
                    break
                strip = True
            if strip:
                rl = [r[len(unicode(n)):].strip() for n,r in enumerate(rl)]

        if self.dialect.has_cl is not None and self.strip_indices:
            strip = False
            for n,c in enumerate(cl):
                if c.find(unicode(n)) != 0:
                    break
                strip = True
            if strip:
                cl = [c[len(unicode(n)):].strip() for n,c in enumerate(cl)]

        if self.dialect.delimiter != ',':
            data = [[q.replace(',','.') for q in row] for row in data]
        
        rl = [None,rl][self.dialect.has_rl]
        cl = [None,cl][self.dialect.has_cl]
        return data, rl, cl

    def get_data(self):
        data, rl, cl = self.parse(all=True)
        data = [[asfloat(q) for q in row] for row in data]
        return data, rl, cl
        
    def delimiter(self, n):
        self.dialect.delimiter = delimiters[n]
        self.update_table()

    def labels(self, **kwargs):
        self.__dict__.update(kwargs)
        self.dialect.__dict__.update(kwargs)
        self.view.show_labels(self.dialect.has_rl, self.dialect.has_cl)
        self.update_table()

    def update_table(self):
        data, rl, cl = self.parse()

        try:
            data = [[asfloat(q) for q in row] for row in data]
        except:
            self.view.enable_import(False)
        else:
            self.view.enable_import(True)
        
        self.table.rowLabels = [None,rl][int(self.dialect.has_rl)]
        self.table.colLabels = [None,cl][int(self.dialect.has_cl)]

        self.table.data = data
        self.view.update()

class TestFrame(wx.Frame):
    def __init__(self, *args):
        wx.Frame.__init__(self, *args)
        btn = wx.Button(self, -1, 'show dialog')
        btn.Bind(wx.EVT_BUTTON, self.OnShow)
        self.Fit()
        self.Show()
        
    def OnShow(self, evt):
        dlg = wx.FileDialog(self, defaultDir=os.path.abspath(os.curdir), wildcard="csv files (*.csv)|*.csv")
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            dlg.Destroy()
            cr = CSVWizard(path)
            if cr.show():
                print cr.get_data()
            else:
                print 'canceled'
            cr.close()

    def OnClose(self, evt):
        print 'end'
        self.Destroy()

def test():
    import os
    
    app = wx.PySimpleApp(0)
    fr = TestFrame(None, -1, 'test frame')
    app.MainLoop()

if __name__ == '__main__':
    test()
    
