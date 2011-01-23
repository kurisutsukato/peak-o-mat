import numpy as N
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
        elif name == '_selection':
            try:
                t,l,b,r = self.controller.selection
            except:
                return [],[]
            else:
                return N.atleast_2d(N.arange(t,b+1,1)).transpose(), N.atleast_2d(N.arange(l,r+1,1))
        elif colre.match(name) is not None: #name.find('col') == 0:
            col = int(name[3:])
            return N.atleast_2d(self._table.data[:,col]).T
        elif rowre.match(name) is not None: #name.find('row') == 0:
            row = int(name[3:])
            return self._table.data[row]
        elif name == '_x':
            return N.atleast_2d(N.arange(self._table.data.shape[1],dtype=float))
        elif name == '_y':
            return N.atleast_2d(N.arange(self._table.data.shape[0],dtype=float)).transpose()
        #elif name == 'help':
        #    print __doc__
        #    return lambda x=None: None
        else:
            return dict.__getitem__(self, name)

    def __setitem__(self, name, val):
        if name == '_data':
            setattr(self._table, 'data', val)
        elif rowre.match(name) is not None: #name.find('row') == 0:
            row = int(name[3:])
            # if not N.isscalar(val) and len(val.shape) > 1 and val.shape[0] == 1:
                # val = val[0]
            self._table.data[row] = val
        elif colre.match(name) is not None: #name.find('col') == 0:
            col = int(name[3:])
            # if not N.isscalar(val) and len(val.shape) > 1 and val.shape[1] == 1:
                # val = val[:,0]
            self._table.data[:,col] = val
        else:
            dict.__setitem__(self,name,val)
