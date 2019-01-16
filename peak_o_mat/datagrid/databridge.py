import numpy as N
np = N
import re

rowre = re.compile(r'^_row(\d+)$')
colre = re.compile(r'^_col(\d+)$')

class DataBridge(dict):
    def __init__(self, controller, *args):
        self.controller = controller
        self._table = self.controller.table
        dict.__init__(self, *args)
        
    def __getitem__(self, name):
        if name == '_data':
            return getattr(self._table, 'data')
        elif name == '_name':
            return getattr(self.controller, 'name')
        elif name == '_selection':
            try:
                t,l,b,r = self.controller.selection
            except:
                return [],[]
            else:
                return N.atleast_2d(N.arange(t,b+1,1)).transpose(), N.atleast_2d(N.arange(l,r+1,1))
        elif colre.match(name) is not None:
            col = int(colre.match(name).groups()[0])
            return N.atleast_2d(self._table.data[:,col]).T
        elif rowre.match(name) is not None:
            row = int(rowre.match(name).groups()[0])
            return self._table.data[row,:]
        elif name == '_x':
            return N.atleast_2d(N.arange(self._table.data.shape[1],dtype=float))
        elif name == '_y':
            return N.atleast_2d(N.arange(self._table.data.shape[0],dtype=float)).transpose()
        else:
            return dict.__getitem__(self, name)

    def __setitem__(self, name, val):
        if name == '_data':
            val = N.array(val).astype(N.float32)
            if val.ndim != 2:
                raise TypeError('array must have rank 2')
            else:
                setattr(self._table, 'data', val)
        elif name == '_name':
            self.controller.name = val
        elif rowre.match(name) is not None:
            row = int(rowre.match(name).groups()[0])
            self._table.data[row,:] = np.asarray(val).flat
        elif colre.match(name) is not None:
            col = int(colre.match(name).groups()[0])
            self._table.data[:,col] = np.asarray(val).flat
        elif name in ['_x','_y','_selection']:
            raise AttributeError('%s not writable'%name)
        else:
            dict.__setitem__(self,name,val)
