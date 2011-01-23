import wx
import wx.grid
from wx.lib.pubsub import pub as Publisher

import numpy as N

class cbarray(N.ndarray):
    def __new__(subtype, data, cb=None, dtype=None, copy=False):
        subtype.__defaultcb = cb

        if copy:
            data = N.array(data,dtype=dtype)
        else:
            data = N.asarray(data,dtype=dtype)

        data = data.view(subtype)
        return data

    def _notify(self):
        if self.cb is not None:
            self.cb()
        Publisher.sendMessage(('changed'))
        
    def _get_shape(self):
        return super(cbarray, self).shape
    shape = property(_get_shape)

    def __setitem__(self, item, val):
        N.ndarray.__setitem__(self, item, val)
        self._notify()
        
    def __array_finalize__(self,obj):
        if not hasattr(self, "cb"):
            # The object does not already have a `.cb` attribute
            self.cb = getattr(obj,'cb',self.__defaultcb)

    def __reduce__(self):
        object_state = list(N.ndarray.__reduce__(self))
        subclass_state = (self.cb,)
        object_state[2] = (object_state[2],subclass_state)
        return tuple(object_state)

    def __setstate__(self,state):
        nd_state, own_state = state
        N.ndarray.__setstate__(self,nd_state)
        
        cb, = own_state
        self.cb = cb

class TableBase(wx.grid.PyGridTableBase):
    def __init__(self):
        wx.grid.PyGridTableBase.__init__(self)
        
        self.tabledata = cbarray(N.zeros((4,8),float),cb=self.Update)
        self.currentRows, self.currentCols = self.tabledata.shape
        self.rowLabels = ['']*self.currentRows
        self.colLabels = ['']*self.currentCols

    def getdata(self):
        return self.tabledata
    def setdata(self, data):
        self.tabledata = cbarray(N.atleast_2d(data),cb=self.Update)
        rows,cols = self.tabledata.shape
        self.rowLabels.extend(['']*(rows-len(self.rowLabels)))
        self.colLabels.extend(['']*(cols-len(self.colLabels)))
        self.Update()
        Publisher.sendMessage(('changed'))
    data = property(getdata,setdata,doc='an assignment to data will send a grid update event')

    def transpose(self):
        rl = self.rowLabels
        self.colLabels = self.rowLabels
        self.colLabels = rl
        self.data = self.data.T

    def clear(self):
        self.data = N.zeros(self.data.shape,dtype=float)
        r,c = self.data.shape
        self.rowLabels = ['']*r
        self.colLabels = ['']*c

    def resize(self, shape):
        r,c = shape
        self.data = N.zeros(shape,dtype=float)
        self.rowLabels = ['']*r
        self.colLabels = ['']*c

    def getrowlabels(self):
        l = filter(lambda x: x[1] != '', zip(range(len(self.rowLabels)), self.rowLabels))
        return l
    def setrowlabels(self, val):
        self.rowLabels += ['']*(self.GetNumberRows()-len(self.rowLabels))
        if type(val) == dict:
            for k,v in val.iteritems():
                self.rowLabels[k] = v
        elif type(val) == list:
            for n,v in enumerate(val):
                self.rowLabels[n] = v
        else:
            raise TypeError, 'arg must be dict or list type'
        self.Update()
    rowlabels = property(getrowlabels, setrowlabels)

    def getcollabels(self):
        cl = filter(lambda x: x[1] != '', zip(range(len(self.colLabels)), self.colLabels))
        return cl
    def setcollabels(self, val):
        self.colLabels += ['']*(self.GetNumberCols()-len(self.colLabels))
        if type(val) == dict:
            for k,v in val.iteritems():
                self.colLabels[k] = v
        elif type(val) == list:
            for n,v in enumerate(val):
                self.colLabels[n] = v
        else:
            raise TypeError, 'arg must be dict or list type'
        self.Update()
    collabels = property(getcollabels, setcollabels)

    def DeleteCols(self, pos, num):
        rows, cols = self.tabledata.shape
        self.tabledata = N.take(self.tabledata,range(pos)+range(pos+num,cols,1), 1)
        self.colLabels = self.colLabels[0:pos]+self.colLabels[pos+num:cols+1]
        self.Update()

    def DeleteRows(self, pos, num):
        rows, cols = self.tabledata.shape
        self.tabledata = N.take(self.tabledata,range(pos)+range(pos+num,rows,1), 0)
        self.rowLabels = self.rowLabels[0:pos]+self.rowLabels[pos+num:rows+1]
        self.Update()

    def GetNumberRows(self):
        return self.tabledata.shape[0]

    def GetNumberCols(self):
        return self.tabledata.shape[1]
    
    def IsEmptyCell(self, row, col):
        return False

    def GetValue(self, row, col):
        return '%.15g'%self.tabledata[row][col]

    def SetValue(self, row, col, value):
        dr = row - (self.GetNumberRows()-1)
        if dr > 0 :
            self.AppendRows(dr)
        dc = col - (self.GetNumberCols()-1)
        if dc > 0 :
            self.AppendCols(dc)
        if value == 'inf':
            value = N.inf
        try:
            self.tabledata[row][col] = float(value)
        except IndexError, msg:
            print 'should not happen: spreadsheet IndexError row %d, col %d'%(row,col)
            
    def GetColLabelValue(self, col):
        lab = self.colLabels[col]
        out = '%d %s'%(col, lab)
        return out

    def GetRowLabelValue(self, row):
        lab = self.rowLabels[row]
        out = '%d %s'%(row, lab)
        return out

    def SetColLabelValue(self, col, val):
        self.colLabels[col] = val

    def SetRowLabelValue(self,row,val):
        self.rowLabels[row] = val

    def InsertRows(self, pos, num):
        concat = N.zeros((num, self.GetNumberCols()),float)
        self.rowLabels = self.rowLabels[0:pos] + ['']*num + self.rowLabels[pos:]
        self.data = N.concatenate((self.tabledata[0:pos], concat, self.tabledata[pos:]))
    
    def InsertCols(self, pos, num):
        concat = N.zeros((self.GetNumberRows(), num),float)
        self.colLabels = self.colLabels[0:pos] + ['']*num + self.colLabels[pos:]
        self.data = N.concatenate((self.tabledata[:,0:pos], concat, self.tabledata[:,pos:]),1)
    
    def AppendRows(self, num):
        concat = N.zeros((num, self.GetNumberCols()),float)
        self.rowLabels += ['']*num
        self.data = N.concatenate((self.tabledata, concat))
    
    def AppendCols(self, num):
        concat = N.zeros((self.GetNumberRows(), num),float)
        self.colLabels += ['']*num
        self.data = N.concatenate((self.tabledata, concat),1)

    def GetTypeName(self, col, row):
        return wx.grid.GRID_VALUE_STRING

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

