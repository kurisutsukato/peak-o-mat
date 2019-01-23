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

import  wx
import  wx.grid
import os

from . import misc_ui

from . import gridlib

class ParDataTable(wx.grid.GridTableBase):
    def __init__(self):
        wx.grid.GridTableBase.__init__(self)

        self.colLabels = ['par', 'value', 'error', 'constr.', 'lower', 'upper']

        self.data = []

        self.currentRows = 0
        self.currentCols = len(self.colLabels)

    def GetAttr(self, *args):
        """\
        this sets the 'area' rows to readonly and blanks the last 3 columns
        """
        row, col = args[:2]
        if hasattr(self.data[row], '__const__'):
            attr = wx.grid.GridCellAttr()
            attr.SetReadOnly()
            if col > 1:
                attr.SetRenderer(gridlib.DumbRenderer())
            #elif col == 1:
            #    attr.SetRenderer(FloatRenderer())
            return attr
        return self.GetAttrProvider().GetAttr(*args)
    
    def GetNumberRows(self):
        return len(self.data)

    def GetNumberCols(self):
        return self.currentCols

    def IsEmptyCell(self, row, col):
        return not self.data[row][col]

    def GetValue(self, row, col):
        try:
            return '%.15g'%self.data[row][col]
        except:
            return self.data[row][col]

    def SetValue(self, row, col, value):
        self.data[row][col] = value

    def GetColLabelValue(self, col):
        return self.colLabels[col]

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

class ParGrid(wx.grid.Grid):
    """\
    A grid which displays the model parameters
    """
          
    def __init__(self, parent):
        wx.grid.Grid.__init__(self, parent, size=(1000,-1), style=wx.SIMPLE_BORDER)
        self.parent = parent
        self.selecting = False
        self.selection = None
        
        self.table = ParDataTable()
        self.SetTable(self.table, True)
        
        self.SetColLabelSize(20)

        varlist = ['free', 'fixed', 'bound']
        attr = wx.grid.GridCellAttr()
        attr.SetEditor(gridlib.ChoiceCellEditor(varlist))
        attr.SetRenderer(gridlib.ChoiceTextRenderer(varlist))
        self.SetColAttr(3, attr)
        
        attr = wx.grid.GridCellAttr()
        attr.SetReadOnly()
        self.SetColAttr(2, attr)
        
        attr = wx.grid.GridCellAttr()
        attr.SetReadOnly()
        self.SetColAttr(0, attr)
        
        self.SetRowLabelSize(0)
        self.SetMargins(0,0)

        self.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.OnSelect)
        self.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.OnEdited)
        self.Bind(wx.grid.EVT_GRID_RANGE_SELECT, self.OnSelectedRange)

        self.init_menus()
        
    def _set_silent(self, state):
        self.SetEvtHandlerEnabled(not state)
    silent = property(fset=_set_silent)
        
    def init_menus(self):
        self.menumap = [(-1,'copy',self.OnMenuCopy)]

        self.menu = wx.Menu()
        for id,text,act in self.menumap:
            item = wx.MenuItem(self.menu, id=id, text=text)
            item = self.menu.Append(item)
            self.Bind(wx.EVT_MENU, act, item)
        
        self.Bind(wx.grid.EVT_GRID_LABEL_RIGHT_CLICK, self.OnMenu)
        self.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.OnMenu)

    def selection2clipboard(self):
        text = ''

        t,l,b,r = self.selection
        data = self.table.data[t:b+1]#[l:r+1]
        data = [[row[n] for n in range(l,r+1)] for row in data]

        text = ''.join(['\t'.join(['%1.15g'%x for x in line])+os.linesep for line in data])
        
        do = wx.TextDataObject()
        do.SetText(text)
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(do)
            wx.TheClipboard.Close()
            #self.grid.ClearSelection()
        else:
            self.message('copy failed and I don\'t know why', blink=True)

    def OnMenu(self, evt):
        self.PopupMenu(self.menu, evt.GetPosition())

    def OnMenuCopy(self, evt):
        self.selection2clipboard()

    def OnSelectedRange(self, evt): 
        """Internal update to the selection tracking list"""
        if self.selecting:
            return
        top,bottom = evt.GetTopRow(),evt.GetBottomRow()
        left,right = evt.GetLeftCol(),evt.GetRightCol()
        rows,cols = self.table.data.shape
        if evt.Selecting():
            try:
                t,l,b,r = self.selection
                self.selection = min(t,top),min(l,left),max(b,bottom),max(r,right)
            except:
                self.selection = top,left,bottom,right
        else:
            if rows == bottom-top+1 and cols == right-left+1:
                self.selection = None

        if self.selection is not None:
            # this makes sure that the selection is always a continuous
            # rectangular area
            self.selecting = True
            self.SelectBlock(*self.selection)
            self.selecting = False
            t,l,b,r = self.selection
            
    def OnSelect(self, evt):
        if evt.GetCol() == 3:
            wx.CallAfter(self.EnableCellEditControl)
        evt.Skip()

    def OnEdited(self, evt):
        row, col = evt.GetRow(), evt.GetCol()
        if col in [3,4,5]:
            if int(self.GetCellValue(row, 3)) == 2:
                for col in [4,5]:
                    try:
                        float(self.GetCellValue(row, col))
                    except:
                        self.SetCellBackgroundColour(row, col, wx.RED)
                    else:
                        self.SetCellBackgroundColour(row, col, self.GetDefaultCellBackgroundColour())
            else:
                for col in [4,5]:
                    self.SetCellBackgroundColour(row, col, self.GetDefaultCellBackgroundColour())
        wx.CallAfter(self.ForceRefresh)
        event = misc_ui.ParEvent(self.GetId(), cmd=misc_ui.GOTPARS_EDIT)
        wx.PostEvent(self, event)

    def GetCellValue(self, row, col):
        """\
        overridden because the C++ method always returns str
        """
        return self.table.GetValue(row, col)
    
    def refresh(self):
        self.ForceRefresh()
        self.table.Update()
        self.AutoSizeColumns(False)

    def _set_data(self, data):
        self.table.data = data
        self.table.Update()
        self.AutoSizeColumns(False)
        self.FitInside()

    data = property(fset=_set_data)
