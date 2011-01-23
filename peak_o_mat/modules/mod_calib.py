import wx
from wx.lib.pubsub import pub as Publisher

import numpy as N
from scipy import integrate,linalg

from peak_o_mat import module, spec, calib


class Module(module.Module):
    title = 'Calibration'
    lasttrafo = None
    _busy = False
    
    def __init__(self, *args):
        module.Module.__init__(self, __file__, *args)

    def init(self):
        self.calib = Calibration()
        self.xmlres.AttachUnknownControl('xrc_grid', CalibGrid(self.panel, self.calib))
        #self.xrc_grid.GetParent().SetMinSize(self.xrc_grid.GetMinSize())
        #self.xrc_grid.GetParent().Refresh()
        self.panel.Layout()

        self.initChoiceCtrls()
        
        self.Bind(wx.EVT_TEXT, self.OnTol, self.xrc_txt_tol)
        self.Bind(wx.EVT_CHOICE, self.OnElement, self.xrc_ch_elem)
        self.Bind(wx.EVT_CHOICE, self.OnUnit, self.xrc_ch_unit)
        self.Bind(wx.EVT_BUTTON, self.OnApply, self.xrc_btn_apply)
        self.Bind(wx.EVT_BUTTON, self.OnStore, self.xrc_btn_store)
        self.Bind(wx.EVT_BUTTON, self.OnApplyStored, self.xrc_btn_applystored)
        self.Bind(wx.EVT_BUTTON, self.OnDispersion, self.xrc_btn_dispersion)
        self.panel.Bind(wx.grid.EVT_GRID_CELL_CHANGE, self.OnCellChanged, self.xrc_grid)
                  
        self.Bind(wx.EVT_UPDATE_UI, self.OnReadyToImport, self.xrc_ch_unit)
        self.Bind(wx.EVT_UPDATE_UI, self.OnReadyToImport, self.xrc_ch_elem)
        self.Bind(wx.EVT_UPDATE_UI, self.OnReadyToApply, self.xrc_btn_apply)
        self.Bind(wx.EVT_UPDATE_UI, self.OnReadyToApply, self.xrc_btn_store)
        self.Bind(wx.EVT_UPDATE_UI, self.OnReadyToApply, self.xrc_btn_dispersion)
        self.Bind(wx.EVT_UPDATE_UI, self.OnReadyToApplyStored, self.xrc_btn_applystored)
        
        Publisher.subscribe(self.OnUpdate, ('setattrchanged'))

    def OnReadyToImport(self, evt):
        set = self.controller.active_set
        evt.Enable(set is not None and set.mod is not None and set.mod.is_filled())
        
    def OnReadyToApply(self, evt):
        evt.Enable(len(self.xrc_grid.selection) > 0)

    def OnReadyToApplyStored(self, evt):
        evt.Enable(self.lasttrafo is not None)

    def initChoiceCtrls(self):
        for e in self.calib.element_list():
            self.xrc_ch_elem.Append(e)
        self.xrc_ch_elem.SetStringSelection(self.calib.element)
        for u in self.calib.unit_list():
            self.xrc_ch_unit.Append(u)
        self.xrc_ch_unit.SetStringSelection(self.calib.unit)

    def OnCellChanged(self, evt):
        if self._busy: # Unbind(wx.grid.EVT_GRID_CELL_CHANGE) did not work
            return
        self._busy = True
        self.OnUpdate(None)
        
        self._busy = False
        
    def selection_changed(self):
        self.OnUpdate(None)
        #self.xrc_btn_update.Enable(self.controller.active_set is not None)

    def page_changed(self, me):
        if me:
            self.selection_changed()
            
    def OnDispersion(self, evt):
        lin,const = self.calib.regression(self.xrc_grid.selection)

        x, y = N.transpose(N.take(N.atleast_2d(self.calib), self.xrc_grid.selection, 0)[:,:2])
        data = spec.Spec(x,y,'data')
        a = x[0]-x[0]/1000.0
        b = x[-1]+x[-1]/1000.0
        x = N.linspace(a,b,50)
        y = (x-const)/lin
        regr = spec.Spec(x,y,'regression')
        plot = self.controller.add_plot()
        self.controller.add_set(data,plot)
        self.controller.add_set(regr,plot)
        
    def OnStore(self, evt):
        self.lasttrafo = ('x',self.calib.trafo(self.xrc_grid.selection),'calib, %d lines'%len(self.xrc_grid.selection))
        self.message('current calibration trafo has been stored for later use')
        
    def OnApplyStored(self, evt):
        if self.lasttrafo is not None:
            plot,sets = self.controller.selection
            for set in sets:
                self.project[plot][set].trafo.append(*self.lasttrafo)
            self.controller.update_plot()

    def OnUnit(self, evt):
        self.calib.unit = self.xrc_ch_unit.GetStringSelection()
        self.OnUpdate(None)

    def OnElement(self, evt):
        self.calib.element = self.xrc_ch_elem.GetStringSelection()
        self.xrc_grid.EnableEditing(self.calib.element == 'custom')
        self.OnUpdate(None)

    def OnTol(self, evt):
        try:
            self.calib.tol = float(self.xrc_txt_tol.GetValue())
        except:
            return
        else:
            self.OnUpdate(None)

    def OnUpdate(self, evt=None):
        aset = self.controller.active_set
        if aset is not None and aset.mod is not None:
            meas = N.array(aset.mod.get_parameter_by_name('pos'))
            self.calib.findmatch(meas)
        else:
            self.calib.findmatch(N.empty((0,)))
        self.xrc_grid.selection = []
        self.xrc_grid.update()

    def OnApply(self, evt):
        trafo = self.calib.trafo(self.xrc_grid.selection)
        plot,sets = self.controller.selection
        for set in sets:
            self.project[plot][set].trafo.append(('x',trafo,'calib, %d lines'%len(self.xrc_grid.selection)))
        self.controller.update_plot()

class dic(list):
    """\
    Class which behaves like a python dict but preserves the natural order of
    its elements. Feed with a list of 2-tuples
    """
    def __init__(self, data):
        self._keys = []
        self._vals = []
        for k,v in data:
            self._keys.append(k)
            self._vals.append(v)

    def keys(self):
        return self._keys

    def values(self):
        return self._vals

    def __getitem__(self, item):
        return self._vals[self._keys.index(item)]
    
class Calibration(list):
    unit = 'A'
    element = 'Ne'
    tol = 2.0
    
    element_map = dic([('Ne','neon'), ('Ar','argon'), ('Ne/Ar','near'), ('Hg','mercury'), ('Cd','cadmium'), ('Hg/Cad','merccad'), ('custom',None)])

    conversion_map = dic([('eV','12400.0/standard'),('nm','standard/10.0'),('A','standard'),('cm-1','1.0/standard*1e8')])
    
    def __init__(self):
        list.__init__(self, [])

    def unit_list(self):
        return self.conversion_map.keys()

    def element_list(self):
        return self.element_map.keys()
        
    def convert(self):
        standard = getattr(calib,self.element_map[self.element])[:,0]
        inten = getattr(calib,self.element_map[self.element])[:,1]
        standard = eval(self.conversion_map[self.unit])
        return standard
    
    standard = property(convert)
    
    def findmatch(self, measured):
        if self.element != 'custom':
            match_meas, match_std =  N.where((abs(measured[:,N.newaxis]-self.standard)) < self.tol)
            measured, match = measured[match_meas], self.standard[match_std]
        else:
            try:
                match = N.array(self)[:,1]
            except IndexError:
                match = measured*1
            
        while len(self) > 0:
            self.pop()
            
        for m in N.transpose([measured, match, measured-match]):
            self.append(m)

    def regression(self, selection):
        meas, std = N.transpose(N.take(N.atleast_2d(self), selection, 0)[:,:2])
        
        if len(std) == 1:
            return [std-meas]
        else:
            a = N.transpose([std,N.ones(std.shape)])
            b = N.transpose(meas)
            
            coeff = linalg.lstsq(a,b)[0]
            return coeff
    
    def trafo(self, selection):
        coeff = self.regression(selection)
        
        if len(coeff) == 1:
            trafo = 'x+%.10e'%(coeff[0])
        else:
            trafo = '(x-(%.10e))/%.10e'%(coeff[1],coeff[0])
        return trafo
        
class CalibTableBase(wx.grid.PyGridTableBase):
    def __init__(self, tabledata):
        wx.grid.PyGridTableBase.__init__(self)

        self.colLabels = ['measured', 'standard', 'difference']
        
        self.tabledata = tabledata #[[0.0,0.0,0.0]]

        self.currentRows = 0
        self.currentCols = 3

    def getdata(self):
        return self.tabledata

    def setdata(self, data):
        self.tabledata = data
        self.Update()

    data = property(getdata, setdata)
    
    def GetNumberRows(self):
        return max(20, len(self.tabledata))

    def GetNumberCols(self):
        return self.currentCols

    def IsEmptyCell(self, row, col):
        try:
            return not self.tabledata[row][col]
        except IndexError:
            return True

    def GetColLabelValue(self, col):
        return self.colLabels[col]

    def GetValue(self, row, col):
        try:
            return self.tabledata[row][col]
        except:
            return ''
        
    def SetValue(self, row, col, value):
        self.tabledata[row][col] = float(value)

    def AppendRows(self, num=1):
        self.tabledata += [0,0]*num
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

class CalibGrid(wx.grid.Grid):
    def __init__(self, parent, tabledata):
        wx.grid.Grid.__init__(self, parent, style=wx.SIMPLE_BORDER)
        table = CalibTableBase(tabledata)
        self.table = table
        self.SetTable(table, True)
        self.SetColLabelSize(20)
        self.Refresh()

        self.selection = []
        
        size = 0
        for c in range(self.GetNumberCols()):
            size += self.GetColSize(c)
        size += self.GetRowLabelSize()+10
        
        self.SetSizeHints(size, -1)
        self.SetMinSize((size, 10))

        self.Bind(wx.grid.EVT_GRID_LABEL_LEFT_CLICK, self.OnLabelLeftClick)
        self.GetGridRowLabelWindow().Bind(wx.EVT_PAINT, self.OnColumnHeaderPaint)

        self.ClearSelection()
        self.EnableEditing(False)
        
    def update(self):
        self.table.Update()
        self.AutoSizeColumns(True)
        for n in self.selection:
            if n not in range(self.table.GetNumberRows()):
                self.selection.remove(n)

    def OnColumnHeaderPaint(self, evt):
        w = self.GetGridRowLabelWindow()
        dc = wx.PaintDC(w)
        clientRect = w.GetClientRect()
        font = dc.GetFont()
        
        if font.IsOk():
            pts = font.GetPointSize()
        else:
            font = wx.SystemSettings_GetFont(wx.SYS_DEFAULT_GUI_FONT)
            pts = font.GetPointSize()
            
        totRowSize = -self.GetViewStart()[1]*self.GetScrollPixelsPerUnit()[1] # Thanks Roger Binns
        l,t,r,b = self.GetClientRect()
        width = self.GetRowLabelSize()
        for row in range(self.GetNumberRows()):
            if row >= len(self.table.tabledata):
                break
            rowSize = self.GetRowSize(row)
            if totRowSize > -10 and totRowSize < b+10:
                dc.SetTextForeground(wx.BLACK)
                rect = [0,totRowSize,width,rowSize]
                if row in self.selection:
                    txt = 'unselect'
                    dc.SetBrush(wx.Brush("RED", wx.SOLID))
                else:
                    txt = 'click to select'
                    dc.SetBrush(wx.Brush("WHEAT", wx.TRANSPARENT))

                dc.DrawRectangle(rect[0], rect[1] - (row<>0 and 1 or 0),
                                 rect[2], rect[3] + (row<>0 and 1 or 0))
                font.SetWeight(wx.BOLD)
                #font.SetPointSize(pts)
                
                dc.SetFont(font)
                rect[0] += 5
                dc.DrawLabel(txt, rect, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_TOP)
            totRowSize += rowSize

    def OnLabelLeftClick(self, evt):
        #evt.Skip()
        row = evt.GetRow()
        if row < 0:
            return
        if row in self.selection:
            self.selection.remove(row)
        else:
            self.selection.append(row)
        self.Refresh()
