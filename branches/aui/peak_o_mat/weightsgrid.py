import  wx
import wx.grid

import copy

from . import gridlib

class WeightsTableBase(wx.grid.GridTableBase):
    def __init__(self):
        wx.grid.GridTableBase.__init__(self)

        self.colLabels = ['xmin','xmax','rel.', 'abs.', 'type']
        self.types = ['rel.','abs.', 'rel.+abs.']
        
        self.dataTypes = [wx.grid.GRID_VALUE_FLOAT,
                          wx.grid.GRID_VALUE_FLOAT,
                          wx.grid.GRID_VALUE_STRING
                          ]

        self.tabledata = []

        self.currentRows = 0
        self.currentCols = 5

    def getdata(self):
        return self.tabledata

    def setdata(self, data):
        self.tabledata = data
        self.Update()

    data = property(getdata, setdata)
    
    def GetNumberRows(self):
        return len(self.tabledata)

    def GetNumberCols(self):
        return 5

    def IsEmptyCell(self, row, col):
        try:
            return not self.tabledata[row]
        except IndexError:
            return True

    def GetColLabelValue(self, col):
        return self.colLabels[col]

    def GetValue(self, row, col):
        if col == 4:
            val = self.types[self.tabledata[row][4]]
        else:
            val = self.tabledata[row][col]
        return val

    def SetValue(self, row, col, value):
        if col == 4:
            value = int(value)
        else:
            value = float(value)
        self.tabledata[row][col] = value

    def AppendRows(self, num=1):
        self.tabledata += copy.copy(self.data[-1])*num
        self.Update()

    def DeleteRows(self, num=1):
        self.tabledata = self.tabledata[:-num]
        self.Update()

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

class WeightsGrid(wx.grid.Grid):
    def __init__(self, parent):
        wx.grid.Grid.__init__(self, parent, style=wx.SIMPLE_BORDER)
        self.table = WeightsTableBase()
        self.SetTable(self.table, True)
        self.SetRowLabelSize(0)
        self.SetColLabelSize(20)
        self.SetSizeHints(200,-1)

        self.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.OnSelect)
        
        size = 0
        for c in range(self.GetNumberCols()):
            size += self.GetColSize(c)
        size += self.GetRowLabelSize()+1

        self.SetSizeHints(size,-1)
        self.SetMinSize((size, -1))

        varlist = ['relative', 'absolute', 'both']
        attr = wx.grid.GridCellAttr()
        attr.SetEditor(gridlib.ChoiceCellEditor(varlist))
        self.SetColAttr(4, attr)

        for i in range(2):
            attr = wx.grid.GridCellAttr()
            attr.SetReadOnly()
            self.SetColAttr(i, attr)


    def SetCellValue(self, row, col, val):
        """\
        overriden because the C++ method accepts only string arguments
        """
        self.table.SetValue(row, col, val)

    def OnSelect(self, evt):
        """\
        show the editor upon cell selection
        """
        evt.Skip()
        if evt.GetCol() == 2:
            wx.CallAfter(self.EnableCellEditControl)
            
