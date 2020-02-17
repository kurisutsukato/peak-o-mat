import wx
import wx.grid
from pubsub import pub

import numpy as np

from ..misc_ui import WithMessage

class cbarray(np.ndarray):
    def __new__(subtype, data, cb=None, dtype=None, copy=False):
        subtype.__defaultcb = cb

        if copy:
            data = np.array(data,dtype=dtype)
        else:
            data = np.asarray(data,dtype=dtype)

        data = data.view(subtype)
        return data

    def _notify(self):
        if self.cb is not None:
            self.cb()
        
    def _get_shape(self):
        return super(cbarray, self).shape
    shape = property(_get_shape)

    def __setitem__(self, item, val):
        np.ndarray.__setitem__(self, item, val)
        self._notify()
        
    def __array_finalize__(self,obj):
        if not hasattr(self, "cb"):
            # The object does not yet have a `.cb` attribute
            self.cb = getattr(obj,'cb',self.__defaultcb)

    def __reduce__(self):
        object_state = list(np.ndarray.__reduce__(self))
        subclass_state = (self.cb,)
        object_state[2] = (object_state[2],subclass_state)
        return tuple(object_state)

    def __setstate__(self,state):
        nd_state, own_state = state
        np.ndarray.__setstate__(self,nd_state)
        
        cb, = own_state
        self.cb = cb

class TableBase(WithMessage, wx.grid.GridTableBase):
    def __init__(self):
        wx.grid.GridTableBase.__init__(self)

        self.tabledata = cbarray(np.zeros((15,4),float),cb=self.Update)
        self.currentRows, self.currentCols = self.tabledata.shape
        self.rowLabels = ['']*self.currentRows
        self.colLabels = ['']*self.currentCols

    def SetView(self, *args, **kwargs):
        wx.grid.GridTableBase.SetView(self, *args, **kwargs)
        WithMessage.__init__(self, self.GetView())

    def getdata(self):
        return self.tabledata
    def setdata(self, data):
        self.tabledata = cbarray(np.atleast_2d(data),cb=self.Update)
        rows,cols = self.tabledata.shape
        self.rowLabels.extend(['']*(rows-len(self.rowLabels)))
        self.colLabels.extend(['']*(cols-len(self.colLabels)))

        self.Update()
    data = property(getdata,setdata,doc='an assignment to data will send a grid update event')

    def transpose(self):
        rl = self.rowLabels
        self.rowLabels = self.colLabels
        self.colLabels = rl
        self.data = self.data.T

    def clear(self):
        self.data = np.zeros(self.data.shape,dtype=float)
        r,c = self.data.shape
        self.rowLabels = ['']*r
        self.colLabels = ['']*c

    def resize(self, shape):
        r,c = shape
        self.data = np.zeros(shape,dtype=float)
        self.rowLabels = ['']*r
        self.colLabels = ['']*c

    def getrowlabels(self):
        l = [x for x in zip(list(range(len(self.rowLabels))), self.rowLabels) if x[1] != '']
        return l
    def setrowlabels(self, val):
        self.rowLabels += ['']*(self.GetNumberRows()-len(self.rowLabels))
        if type(val) == dict:
            for k,v in val.items():
                self.rowLabels[k] = v
        elif type(val) == list:
            for n,v in enumerate(val):
                self.rowLabels[n] = v
        else:
            raise TypeError('arg must be dict or list type')
        self.Update()
    rowlabels = property(getrowlabels, setrowlabels)

    def getcollabels(self):
        cl = [x for x in zip(list(range(len(self.colLabels))), self.colLabels) if x[1] != '']
        return cl
    def setcollabels(self, val):
        self.colLabels += ['']*(self.GetNumberCols()-len(self.colLabels))
        if type(val) == dict:
            for k,v in val.items():
                self.colLabels[k] = v
        elif type(val) == list:
            for n,v in enumerate(val):
                self.colLabels[n] = v
        else:
            raise TypeError('arg must be dict or list type')
        self.Update()
    collabels = property(getcollabels, setcollabels)

    def DeleteCols(self, pos, num):
        rows, cols = self.tabledata.shape
        self.tabledata = np.take(self.tabledata,list(range(pos))+list(range(pos+num,cols,1)), 1)
        self.colLabels = self.colLabels[0:pos]+self.colLabels[pos+num:cols+1]
        self.Update()

    def DeleteRows(self, pos, num):
        rows, cols = self.tabledata.shape
        self.tabledata = np.take(self.tabledata,list(range(pos))+list(range(pos+num,rows,1)), 0)
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
            value = np.inf
        try:
            self.tabledata[row][col] = float(value)
        except IndexError as msg:
            print('should not happen: spreadsheet IndexError row %d, col %d'%(row,col))
        except ValueError:
            print('non scalar value ignored')

    def GetColLabelValue(self, col):
        lab = self.colLabels[col]
        if lab != '':
            out = '%d (%s)'%(col, lab)
        else:
            out = str(col)
        return out

    def GetRowLabelValue(self, row):
        lab = self.rowLabels[row]
        if lab != '':
            out = '%d (%s)'%(row, lab)
        else:
            out = str(row)
        return out

    def SetColLabelValue(self, col, val):
        self.colLabels[col] = val

    def SetRowLabelValue(self,row,val):
        self.rowLabels[row] = val

    def InsertRows(self, pos, num):
        concat = np.zeros((num, self.GetNumberCols()),float)
        self.rowLabels = self.rowLabels[0:pos] + ['']*num + self.rowLabels[pos:]
        self.data = np.concatenate((self.tabledata[0:pos], concat, self.tabledata[pos:]))
    
    def InsertCols(self, pos, num):
        concat = np.zeros((self.GetNumberRows(), num),float)
        self.colLabels = self.colLabels[0:pos] + ['']*num + self.colLabels[pos:]
        self.data = np.concatenate((self.tabledata[:,0:pos], concat, self.tabledata[:,pos:]),1)
    
    def AppendRows(self, num):
        if num >= 0:
            concat = np.zeros((num, self.GetNumberCols()),float)
            self.rowLabels += ['']*num
            self.data = np.concatenate((self.tabledata, concat))
    
    def AppendCols(self, num):
        if num >= 0:
            concat = np.zeros((self.GetNumberRows(), num),float)
            self.colLabels += ['']*num
            self.data = np.concatenate((self.tabledata, concat),1)
        
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
        pub.sendMessage((self.instid, 'changed'))

