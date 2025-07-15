# -*- coding: cp1252 -*-

import wx
import wx.grid

from io import StringIO

from .pomio import CSVReader, PomDialect, asfloat
from . import config

delimiters = [',',';',':',' ','\t']
choices = [',',';',':','space','tab']

class FormatExpection(Exception):
    pass

class Dialog(wx.Dialog):
    def __init__(self, parent, dialect):
        wx.Dialog.__init__(self, parent, -1, 'csv wizard', style=wx.DEFAULT_DIALOG_STYLE|wx.FRAME_FLOAT_ON_PARENT)
        self.dialect = dialect
        self.gui_init()
        self.CenterOnParent()

    def gui_init(self):
        self.grid = wx.grid.Grid(self)
        self.grid.SetMinSize((400,200))
        self.grid.SetRowLabelSize(0)
        self.grid.SetColLabelSize(0)
        self.grid.SetRowLabelAlignment(wx.ALIGN_LEFT, wx.ALIGN_CENTER)

        self.txt_raw = wx.TextCtrl(self, -1, size=(400,200), style=wx.TE_MULTILINE|wx.TE_DONTWRAP)
        self.sp_skip = wx.SpinCtrl(self, -1, '0', size=(50,-1))
        self.sp_skip.SetRange(0,200)
        self.ch_delimiter = wx.Choice(self, -1, choices=choices)
        self.ch_delimiter.SetSelection(delimiters.index(self.dialect.delimiter))
        self.chkb_stripindices = wx.CheckBox(self, -1, 'strip row/col indices')
        self.chkb_collabels = wx.CheckBox(self, -1, 'first row contains column labels')
        self.chkb_rowlabels = wx.CheckBox(self, -1, 'first column contains row labels')
        self.chkb_rowlabels.SetValue(self.dialect.has_rl)
        self.chkb_collabels.SetValue(self.dialect.has_cl)
        self.chkb_replacecomma = wx.CheckBox(self, -1, 'replace comma with decimal point')
        self.btn_import = wx.Button(self, -1, 'Import')
        self.btn_cancel = wx.Button(self, -1, 'Cancel')

        outer = wx.BoxSizer(wx.VERTICAL)
        flexgrid = wx.FlexGridSizer(cols=3, vgap=5, hgap=2)
        flexgrid.Add(self.chkb_collabels, 0, wx.ALIGN_CENTER_VERTICAL)
        flexgrid.Add(wx.Window(self, size=(20,0)))
        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(wx.StaticText(self, -1, 'cell delimiter'), 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)
        box.Add(self.ch_delimiter, 0, wx.EXPAND)
        flexgrid.Add(box)
        flexgrid.Add(self.chkb_rowlabels, 0, wx.ALIGN_CENTER_VERTICAL)
        flexgrid.Add(wx.Window(self,size=(20,0)))
        flexgrid.Add(self.chkb_stripindices, 0, wx.ALIGN_CENTER_VERTICAL)
        flexgrid.Add(self.chkb_replacecomma, 0, wx.ALIGN_CENTER_VERTICAL)
        outer.Add(self.txt_raw, 0, wx.EXPAND|wx.ALL, 5)
        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(wx.StaticText(self, -1, 'skip rows'), 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)
        box.Add(self.sp_skip, 0, wx.EXPAND)
        outer.Add(box, 0, wx.EXPAND|wx.ALL, 5)
        outer.Add(flexgrid, 0, wx.ALL|wx.EXPAND, 5)
        outer.Add(self.grid, 1, wx.ALL|wx.EXPAND, 5)
        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(wx.Window(self,size=(20,0)), 1)
        box.Add(self.btn_import)
        box.Add(self.btn_cancel,0,wx.LEFT,5)
        outer.Add(box, 0, wx.ALL|wx.EXPAND, 5)
        self.SetSizer(outer)
        self.Fit()

        self.show_labels(self.dialect.has_rl, self.dialect.has_cl)
        self.sp_skip.SetValue(self.dialect.skiplines)

    def update_from_dialect(self, dialect):
        self.dialect = dialect
        self.show_labels(self.dialect.has_rl, self.dialect.has_cl)
        self.sp_skip.SetValue(self.dialect.skiplines)

    def enable_import(self, state=True):
        self.btn_import.Enable(state)

    def show_labels(self, rlabs, clabs):
        self.grid.SetRowLabelSize([0,120][int(rlabs)])
        self.grid.SetColLabelSize([0,20][int(clabs)])
        
class Table(wx.grid.GridTableBase):
    def __init__(self):
        wx.grid.GridTableBase.__init__(self)

        self.colLabels = ['']*10
        self.rowLabels = ['']*200
        self._data = [[0]*10]*200

        self.currentRows = 200
        self.currentCols = 10

    def _get_data(self):
        return self._data
    def _set_data(self, data):
        #try:
        #    data[0][0]
        #except IndexError:
        #    data = [[]]
        self._data = data
        self.Update()
    data = property(_get_data, _set_data)

    def GetNumberRows(self):
        return len(self.data)

    def GetNumberCols(self):
        try:
            return len(self.data[0])
        except IndexError:
            return 0

    def IsEmptyCell(self, row, col):
        try:
            return not self.data[row][col]
        except:
            return True

    def GetValue(self, row, col):
        try:
            return str(self.data[row][col])
        except IndexError:
            return ''

    def SetValue(self, row, col, value):
        self.data[row][col] = value

    def GetColLabelValue(self, col):
        try:
            return str(self.colLabels[col])
        except:
            return ''

    def GetRowLabelValue(self, row):
        try:
            return str(self.rowLabels[row])
        except:
            return ''

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
        self.view.Bind(wx.EVT_CHECKBOX, self.OnReplaceComma, self.view.chkb_replacecomma)
        self.view.Bind(wx.EVT_SPINCTRL, self.OnSkip, self.view.sp_skip)

        self.view.Bind(wx.EVT_BUTTON, self.OnImport, self.view.btn_import)
        self.view.Bind(wx.EVT_CLOSE, self.OnClose)
        self.view.Bind(wx.EVT_BUTTON, self.OnClose, self.view.btn_cancel)

    def OnReplaceComma(self, evt):
        self.controller.replace_comma = self.view.chkb_replacecomma.GetValue()
        self.controller.update_table()

    def OnSkip(self, evt):
        self.controller.skip(int(self.view.sp_skip.GetValue()))

    def OnImport(self, evt):
        self.view.EndModal(True)

    def OnClose(self, evt):
        self.view.EndModal(False)
        
    def OnStripIndices(self, evt):
        self.controller.strip_indices = self.view.chkb_stripindices.GetValue()
        self.controller.update_table()
        
    def OnDelimiter(self, evt):
        #self.view.chkb_rowlabels.SetValue(False)
        #self.view.chkb_collabels.SetValue(False)
        #self.controller.labels(has_rl=False,has_cl=False)
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
    replace_comma = False

    def __init__(self, guiparent, path):
        self.view = Dialog(guiparent, self.dialect)
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
        class Found(Exception):
            pass

        if not hasattr(self, 'rawdata') or all:
            try:
                for enc in [None] + config.options('encodings'):
                    try:
                        with open(self.path, encoding=enc) as f:
                            if not all:
                                self.rawdata = '\n'.join([q.rstrip() for q in [f.readline() for q in range(20)] if len(q)>0])
                            else:
                                self.rawdata = '\n'.join([q.rstrip() for q in f.readlines()])
                    except UnicodeDecodeError:
                        continue
                    else:
                        raise Found
            except Found:
                pass
            else:
                msg = 'File with unkown encoding.\nChange the encoding settings in the preferences to force a specific encoding for reading.\n'
                raise FormatExpection(msg)

        data = []

        csvr = CSVReader(StringIO(self.rawdata), dialect=self.dialect)
        self.preview = self.rawdata
        for row in csvr:
            data.append(row)

        return data

    def parse(self, all=False):
        data = self.read(all)
        if self.dialect.skiplines >= len(data):
            self.dialect.skiplines = 0
        data = data[self.dialect.skiplines:]

        cl = data[0]
        try:
            rl = [list(x) for x in zip(*data)][0]
        except IndexError:
            rl = ['']*len(data)

        if self.dialect.has_cl:
            rl = rl[1:]
            data = data[1:]
        if self.dialect.has_rl:
            cl = cl[1:]
            data = [list(x) for x in zip(*data)][1:] #transpose
            data = [list(x) for x in zip(*data)] # and back

        if self.dialect.has_rl is not None and self.strip_indices:
            strip = False
            for n,r in enumerate(rl):
                if r.find(str(n)) != 0:
                    break
                strip = True
            if strip:
                rl = [r[len(str(n)):].strip() for n,r in enumerate(rl)]

        if self.dialect.has_cl is not None and self.strip_indices:
            strip = False
            for n,c in enumerate(cl):
                if c.find(str(n)) != 0:
                    break
                strip = True
            if strip:
                cl = [c[len(str(n)):].strip() for n,c in enumerate(cl)]

        if self.replace_comma and self.dialect.delimiter != ',':
            data = [[q.replace(',','.') for q in row] for row in data]
        
        rl = rl if self.dialect.has_rl else None
        cl = cl if self.dialect.has_cl else None
        return data, rl, cl

    def get_data(self):
        data, rl, cl = self.parse(all=True)
        out = []
        for row in data:
            try:
                #if self.replace_comma:
                #    out.append([asfloat(q.replace(',','.')) for q in row])
                #else:
                out.append([asfloat(q) for q in row])
            except ValueError: #catch trailing non-scalar data
                break

        return out, rl, cl
        
    def delimiter(self, n):
        self.dialect.delimiter = delimiters[n]
        self.update_table()

    def skip(self, n):
        self.dialect.skiplines = n
        self.update_table()

    def labels(self, **kwargs):
        self.__dict__.update(kwargs)
        self.dialect.__dict__.update(kwargs)
        self.view.show_labels(self.dialect.has_rl, self.dialect.has_cl)
        self.update_table()

    def update_table(self):
        data, rl, cl = self.parse()

        try:
            if self.replace_comma:
                data = [[asfloat(q.replace(',','.')) for q in row] for row in data]
            else:
                data = [[asfloat(q) for q in row] for row in data]
        except:
            self.view.enable_import(False)
        else:
            self.view.enable_import(True)

        self.table.rowLabels = rl
        self.table.colLabels = cl

        self.table.data = data
        self.view.txt_raw.SetValue(self.preview)
        self.view.update_from_dialect(self.dialect)

def mist():
    import io
    import csv

    csvr = csv.reader(io.open('data.csv', encoding='cp1252'))

    for row in csvr:
        print(row)

if __name__ == '__main__':
    app = wx.App()
    d = CSVWizard(None, 'data.csv')
    d.show()
    app.MainLoop()

    
