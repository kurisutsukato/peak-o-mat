##     Copyright (C) 2003 Christian Kristukat (ckkart@hoc.net)     

##     This program is free software; you can redistribute it and/or modify
##     it under the terms of the GNU General Public License as published by
##     the Free Software Foundation; either version 2 of the License, or
##     (at your option) any later version.

##     This program is distributed in the hope that it will be useful,
##     but WITHOUT ANY WARRANTY; without even the implied warranty of
##     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##     GNU General Public License for more details.

##     You should have received a copy of the GNU General Public License
##     along with this program; if not, write to the Free Software
##     Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import wx
import wx.grid
import wx.lib.agw.flatnotebook as fnb

from wx.py import shell
from wx.lib.splitter import MultiSplitterWindow

from .. import images
from .. import controls
from ..misc_ui import WithMessage


ID_LOAD = wx.NewId()
ID_SAVE = wx.NewId()
ID_NEW = wx.NewId()
ID_EXPORT = wx.NewId()
ID_COPY = wx.NewId()
ID_CUT = wx.NewId()
ID_DELETE = wx.NewId()
ID_PASTE = wx.NewId()
ID_INSERTPASTE = wx.NewId()
ID_INSERT = wx.NewId()
ID_APPEND = wx.NewId()
ID_SETVALUES = wx.NewId()
ID_PLOTY = wx.NewId()
ID_PLOTXY = wx.NewId()

def intro():
    from ..datagrid import __doc__
    print(__doc__)

class GridContainer(WithMessage,wx.Frame):
    def __init__(self, parent, onwin=False):
        wx.Frame.__init__(self, parent, -1, 'Data Grid', size=(700,400), style=wx.DEFAULT_FRAME_STYLE)
        WithMessage.__init__(self)
        self.parent = parent

        self.init_menu()

        pan = wx.Panel(self, -1)

        splitter = MultiSplitterWindow(pan, style=wx.SP_LIVE_UPDATE)
        splitter.SetOrientation(wx.VERTICAL)
        self.nb = fnb.FlatNotebook(splitter, -1, name='grid_notebook', agwStyle=fnb.FNB_NODRAG|fnb.FNB_X_ON_TAB)

        shellpanel = wx.Panel(splitter, -1)

        self.sh = sh = shell.Shell(shellpanel, -1, introText='peak-o-mat - datagrid shell', showInterpIntro=True)
        sh.push('import numpy as np', True)
        #sh.push('_data=np.arange(24).reshape((6,4))')

        sh.SetMinSize((-1,200))
        self.shell = sh

        splitter.AppendWindow(self.nb, 250)
        splitter.AppendWindow(shellpanel, 140)

        self.btn_transpose = wx.Button(shellpanel, -1, '&Transpose')
        self.btn_clear = wx.Button(shellpanel, -1, 'Clear')
        self.btn_rename = wx.Button(shellpanel, -1, 'Rename')
        self.btn_export_excel = wx.Button(shellpanel, label='Transfer to Excel', style=wx.BU_EXACTFIT)
        self.btn_export_excel.Enable(False)
        self.btn_export_excel.Show(onwin)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.btn_transpose, 0, wx.ALL|wx.EXPAND, 5)
        hbox.Add(self.btn_clear, 0, wx.ALL|wx.EXPAND, 5)
        hbox.Add(self.btn_rename, 0, wx.ALL|wx.EXPAND, 5)
        hbox.Add(wx.Window(shellpanel, size=(50,-1)),1)
        hbox.Add(self.btn_export_excel, 0, wx.ALL|wx.EXPAND, 5)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.Add(sh, 1, wx.EXPAND)
        shellpanel.SetSizer(vbox)
        
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(splitter, 1, wx.EXPAND)
        #box.Add(sh, 1, wx.EXPAND)
        pan.SetSizer(box)
        self.SetSize((-1,500))
        
        ico = wx.Icon()
        ico.CopyFromBitmap(images.get_bmp('logosmall.png'))
        self.pom_ico = ico
        self.SetIcon(ico)

        self.statusbar = controls.Status(self)
        self.SetStatusBar(self.statusbar)

        self.CenterOnParent()

    def init_menu(self):
        menubar = wx.MenuBar()
        menu = wx.Menu()
        menu.Append(ID_NEW, "New Grid\tCTRL-n", "Create an empty data grid", wx.ITEM_NORMAL)
        menu.Append(ID_LOAD, "Import...", "Import tabular data", wx.ITEM_NORMAL)
        menu.Append(ID_SAVE, "Export...", "Export tabular data", wx.ITEM_NORMAL)
        menubar.Append(menu, 'Data')

        menu = wx.Menu()
        menu.Append(ID_INSERT, "Insert", "Insert rows/cols according to selection", wx.ITEM_NORMAL)
        menu.Append(ID_APPEND, "Append", "Append rows/cols according to selection", wx.ITEM_NORMAL)
        menu.Append(wx.MenuItem(menu, id=wx.ID_SEPARATOR, text=''))
        menu.Append(ID_DELETE, "Delete", "Delete selection", wx.ITEM_NORMAL)
        menu.Append(ID_CUT, "Cut\tCTRL-x", "Cut selection", wx.ITEM_NORMAL)
        menu.Append(ID_COPY, "Copy\tCTRL-c", "Copy selection", wx.ITEM_NORMAL)
        menu.Append(ID_PASTE, "Paste\tCTRL-p", "Paste selection", wx.ITEM_NORMAL)
        menu.Append(ID_INSERTPASTE, "Insert && paste\tSHIFT-CTRL-p", "Insert and paste selection", wx.ITEM_NORMAL)
        menu.Append(wx.MenuItem(menu, id=wx.ID_SEPARATOR, text=''))
        menu.Append(ID_SETVALUES, 'Set values...','Set cell values', wx.ITEM_NORMAL)
        menubar.Append(menu, 'Selection')

        self.selection_menu = {}
        for mi in menu.GetMenuItems():
            self.selection_menu[mi.GetItemLabelText()] = mi

        menu = wx.Menu()
        menu.Append(ID_PLOTY, "Plot Y", "Create dataset from selected column and x-values from column 0", wx.ITEM_NORMAL)
        menu.Append(ID_PLOTXY, "Plot XY", "Create dataset from selected columns and x-values from leftmost column of selection", wx.ITEM_NORMAL)
        menubar.Append(menu, 'Create dataset')

        self.plot_menu = {}
        for mi in menu.GetMenuItems():
            self.plot_menu[mi.GetItemLabelText()] = mi

        self.SetMenuBar(menubar)

    def Hide(self):
        self.Show(False)

    def Show(self, state=True):
        self.parent.menubar.FindItemById(self.parent.menu_factory.menu_ids['Data Grid']).Check(state)
        super(GridContainer, self).Show(state)

    def export_excel_dialog(self, choices):
        dlg = ExportView(self, choices)
        if dlg.ShowModal() == wx.ID_OK:
            return dlg.wb
        else:
            return None

class GridPanel(WithMessage,wx.Panel):
    def __init__(self, parent, show_shell=False):
        if show_shell:
            raise Exception('should not happen')
        wx.Panel.__init__(self, parent)
        WithMessage.__init__(self)

        self.grid = Grid(self)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.grid, 1, wx.EXPAND)

        self.SetSizer(vbox)

        self.Layout()

    def set_name(self, name):
        nb = self.GetParent()
        if type(nb) in [wx.Notebook,fnb.FlatNotebook]:
            for p in range(nb.GetPageCount()):
                if nb.GetPage(p) == self:
                    nb.SetPageText(p, name)

    def get_name(self):
        nb = self.GetParent()
        if type(nb) in [wx.Notebook,fnb.FlatNotebook]:
            for p in range(nb.GetPageCount()):
                if nb.GetPage(p) == self:
                    return nb.GetPageText(p)
    name = property(fset=set_name)
        
    def close(self):
        self.SetEvtHandlerEnabled(False)
        nb = self.GetParent()
        for n in range(nb.GetPageCount()):
            if nb.GetPage(n) == self:
                nb.RemovePage(n) #does not delete the panel
                break

    def show_rename_dialog(self, val):
        dlg = wx.TextEntryDialog(self, 'Enter new label:',
            'Rename label', val)

        if dlg.ShowModal() == wx.ID_OK:
            ret = dlg.GetValue()
        else:
            ret = None

        dlg.Destroy()

        return ret

class Grid(wx.grid.Grid):
    def __init__(self, parent):
        wx.grid.Grid.__init__(self, parent, -1, style=wx.SUNKEN_BORDER)
        self.instid = parent.instid
        self.SetColLabelSize(20)
        self.SetDefaultCellOverflow(False)
        self.SetRowLabelSize(120)
        self.SetRowLabelAlignment(wx.ALIGN_LEFT, wx.ALIGN_CENTER)
        self.SetDefaultColSize(100)
        self.FitInside()

        self.selection_type = None

    def paint_row_header(self, rowtoadd):
        w = self.GetGridRowLabelWindow()
        dc = wx.PaintDC(w)
        clientRect = w.GetClientRect()
        font = dc.GetFont()

        totRowSize = -self.GetViewStart()[1]*self.GetScrollPixelsPerUnit()[1]
        l,t,r,b = self.GetClientRect()
        width = self.GetRowLabelSize()
        for row in range(self.GetNumberRows()):
            rowSize = self.GetRowSize(row)
            if totRowSize > -10 and totRowSize < b+10:
                dc.SetTextForeground(wx.BLACK)
                rect = [0,totRowSize,width,rowSize]
                if row == rowtoadd:
                    dc.SetBrush(wx.Brush("RED", wx.SOLID))
                else:
                    dc.SetBrush(wx.Brush("WHEAT", wx.TRANSPARENT))

                dc.DrawRectangle(rect[0], rect[1] - (row!=0 and 1 or 0),
                                 rect[2], rect[3] + (row!=0 and 1 or 0))
                font.SetWeight(wx.BOLD)

                dc.SetFont(font)
                rect[0] += 5
                dc.DrawLabel("%s" % self.GetTable().GetRowLabelValue(row),
                             rect, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_TOP)
            totRowSize += rowSize

class ExportView(wx.Dialog):
    def __init__(self, parent, choices=['New Workbook']):
        super(ExportView, self).__init__(parent)
        self.SetTitle('Choose Excel workbook to export to')

        self.cho_workbook = wx.Choice(self, choices=choices, size=(200,-1))
        self.cho_workbook.SetSelection(0)
        self.btn_cancel = wx.Button(self, label='Cancel')
        self.btn_export = wx.Button(self, label='Export')

        vbox = wx.BoxSizer(wx.VERTICAL)
        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(wx.StaticText(self, label='Export to'), 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
        box.Add(self.cho_workbook, 0, wx.ALL|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, 5)
        vbox.Add(box, 0, wx.EXPAND|wx.ALL, 10)

        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(wx.Window(self),1)
        box.Add(self.btn_cancel, 0, wx.ALL|wx.EXPAND, 2)
        box.Add(self.btn_export, 0, wx.ALL|wx.EXPAND, 2)
        vbox.Add(box, 0, wx.EXPAND|wx.ALL, 10)
        self.SetSizer(vbox)

        self.btn_cancel.Bind(wx.EVT_BUTTON, self.OnCancel)
        self.btn_export.Bind(wx.EVT_BUTTON, self.OnExport)

        self.Fit()

    def OnCancel(self, evt):
        self.EndModal(wx.ID_CANCEL)

    def OnExport(self, evt):
        self.wb = self.cho_workbook.GetSelection()
        self.EndModal(wx.ID_OK)
