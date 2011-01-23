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

"""\
In addtion to the features of a standard python shell
the following symbols are available:

data:      The ndarray displayed in the table above.
selection: The indices of the current selection such
           that data[selection] retrieves the selected
           data.
colX:      Column X as 2d column vector. 
rowX:      Row X as 2d row vector.
x:         The row indices as 2d row vector.
y:         The column indices as 2d column vector.

cstack((a, b, ...))
Returns a new array where all arguments are stacked along
axis=1 (along the rows).

rstack((a, b, ...))
Returns a new array where all arguments are stacked along
axis=0 (along the cols).

data, colX and rowX are readable *and* writable. In order to
write to the latter two, the shapes have to match exactly.

The numpy array broadcasting mechanism allows to create 2d
data writing expression like, e.g.

data = x+y

"""

import wx
import wx.grid
import wx.lib.dialogs
from wx import xrc
from wx.lib.pubsub import pub as Publisher
from wx.lib import flatnotebook as fnb

import numpy as N
    
import os
import re

from peak_o_mat import misc, io, csvwizard, settings as config

import locale

from interactor import GridContainerInteractor, GridInteractor
from view import GridContainer, GridPanel
from tablebase import TableBase
from databridge import DataBridge

class Controller(object):
    gridcontrollers = []
    current = None
    the_grid = None
    
    def __init__(self, parent_controller, view, interactor):
        self.view = view
        self.parent_controller = parent_controller
    
        interactor.Install(self, self.view)

    def new(self, data=None, name=None, the_grid=False):
        if name is None:
            name = 'grid %c'%chr(len(self.gridcontrollers)-int(self.the_grid is not None)+65)

        gc = GridController(self, GridPanel(self.view.nb), GridInteractor(), name, data=data, the_grid=the_grid)
        if self.the_grid is None and the_grid:
            self.the_grid = gc
        self.gridcontrollers.append(gc)
        self.view.nb.AddPage(gc.view, gc.name)
        locs = DataBridge(gc, self.view.shell.interp.locals)
        self.view.shell.interp.locals = locs
        self.view.Show()
        return gc
    
    def page_changed(self, view):
        for gc in self.gridcontrollers:
            if view == gc.view:
                break
        locs = DataBridge(gc, self.view.shell.interp.locals)
        self.view.shell.interp.locals = locs
        self.current = gc

    def transpose(self):
        self.current.table.transpose()

    def clear(self):
        if self.current.the_grid:
            self.current.rowtoadd = 0
        self.current.table.clear()

    def resize(self, shape):
        self.current.table.resize(shape)

    def close_gridcontroller(self, selection):
        view = self.view.nb.GetCurrentPage()
        
        for gc in self.gridcontrollers:
            if view == gc.view:
                break
        if gc.the_grid:
            self.the_grid = None
        self.gridcontrollers.remove(gc)
        return True

    def hide(self):
        self.parent_controller.show_datagrid(False)
        
class GridController(object):
    def __init__(self, parent_controller, view, interactor, name, data=None, the_grid=False):
        self.parent_controller = parent_controller
        self.view = view
        self.the_grid = the_grid
        
        self._busy = False
        self.selection = None
        self.rowtoadd = 0

        self.col0_is_x = False
        self.can_create_set = 0 # 0: selection does not match
                                # 1: selection is 1d
                                # 2: selection is 2d
        self.can_copy = False
        
        self.table = TableBase()
        self.view.grid.SetTable(self.table, True)

        if data is not None:
            try:
                data,rl,cl = data
            except:
                self.table.data = data
            else:
                self.table.data = data
                self.table.rowlabels = rl
                self.table.collabels = cl
            self.view.grid.Update()

        self.name = name
        
        interactor.Install(self, self.view, the_grid)

        self.selection_changed(None)

    def __getattr__(self, attr):
        if attr in ['data','rowlabels','collabels']:
            return getattr(self.table, attr)
        else:
            raise AttributeError, attr

    def __setattr__(self, attr, val):
        if attr in ['data','rowlabels','collabels']:
            setattr(self.table, attr, val)
        else:
            object.__setattr__(self, attr, val)

    def set_name(self, name):
        self._name = name
        if hasattr(self, 'view') and self.view is not None:
            self.view.name = name
    def get_name(self):
        return self._name
    name = property(get_name, set_name)

    def show_rename_dialog(self, row, col):
        if row > -1:
            val = self.view.grid.GetRowLabelValue(row)
        elif col > -1:
            val = self.view.grid.GetColLabelValue(col)
        mat = re.match(r'\d+\s+(.*)', val)
        if mat:
            val = mat.group(1)
        else:
            val = ''
        res = self.view.show_rename_dialog(val)
        if res is not None:
            self.rename_rowcol_label(row, col, res)

    def rename_rowcol_label(self, row, col, val):
        if col >= 0:
            self.view.grid.SetColLabelValue(col, val)
        elif row >= 0:
            self.view.grid.SetRowLabelValue(row, val)

    def import_data(self, path):
        cr = csvwizard.CSVWizard(path)
        if cr.show():
            data, rlab, clab = cr.get_data()

            self.table.data = data

            rows,cols = self.table.data.shape
            self.table.rowLabels = [['']*self.table.data.shape[0],rlab][int(rlab is not None)]
            self.table.colLabels = [['']*self.table.data.shape[1],clab][int(clab is not None)]
            self.table.rowLabels.extend(['']*(rows-len(self.table.rowLabels)))
            self.table.colLabels.extend(['']*(cols-len(self.table.colLabels)))
            
            if self.the_grid:
                self.rowtoadd = len(data)
                self.table.AppendRows(1)

            self.name = os.path.basename(path)
            misc.set_cwd(path)
            
        cr.close()
        
        
    def export_data(self, path, ext='csv'):
        ncols = self.table.data.shape[1]
        nrows = self.table.data.shape[0]
        cl = [self.table.GetColLabelValue(q) for q in range(ncols)]
        rl = [self.table.GetRowLabelValue(q) for q in range(nrows)]

        if re.match(r'.+\.%s$'%ext, path) is None:
            path ='%s.%s'%(path,ext)

        if ext == 'csv':
            io.write_csv(path, self.table.data, rl, cl)
        elif ext == 'tex':
            io.write_tex(path, self.table.data, rl, cl)

        misc.set_cwd(path)
        self.message('wrote %s'%path)
            
    def create_set(self, col0isX):
        self.col0_is_x = col0isX
        Publisher.sendMessage(('grid','newset'), self.get_selected_data)

    #def resize(self, shape):
    #    r,c = shape
    #    self.table.data = N.zeros(shape,dtype=float)
    #    self.table.rowLabels = ['']*r
    #    self.table.colLabels = ['']*c

    #def transpose(self):
    #    rl = self.table.rowLabels
    #    self.table.rowLabels = self.table.colLabels
    #    self.table.colLabels = rl
    #    self.table.data = N.transpose(self.table.data)

    #def clear(self):
    #    self.rowtoadd = 0
    #    self.table.data = N.zeros(self.table.data.shape,dtype=float)
    #    r,c = self.table.data.shape
    #    self.table.rowLabels = ['']*r
    #    self.table.colLabels = ['']*c

    def selection_changed(self, sel):
        self.selection = sel
        try:
            t,l,b,r = self.selection
        except:
            #self.view.btn_copy.Disable()
            self.can_copy = False
            self.can_create_set = 0
        else:
            #self.view.btn_copy.Enable()
            self.can_copy = True
            #self.view.btn_unselect.Enable()
            if  b-t >= 1:
                self.can_create_set = 1
                if r-l >= 1:
                    self.can_create_set = 2
            else:
                self.can_create_set = 0
        self.check_clipboard()
        
    def clear_selection(self):
        self.view.grid.ClearSelection()

    def check_clipboard(self):
        state = False
        if wx.TheClipboard.Open():
            do = wx.TextDataObject()
            state = wx.TheClipboard.GetData(do)
            wx.TheClipboard.Close()

        #self.view.btn_paste.Enable(state and self.selection is not None)
        #self.view.btn_pastereplace.Enable(state)
        
    def read_clipboard(self):
        if wx.TheClipboard.Open():
            do = wx.TextDataObject()
            success = wx.TheClipboard.GetData(do)
            wx.TheClipboard.Close()
            if success:
                text = do.GetText().strip()
                if text != '':
                    data = misc.str2array(text)
                    return data
        return None
    
    def write_clipboard(self, text):
        if wx.TheClipboard.Open():
            do = wx.TextDataObject()
            do.SetText(text)
            wx.TheClipboard.SetData(do)
            wx.TheClipboard.Close()
            self.view.grid.ClearSelection()
            return True
        else:
            return False
        
    def selection2clipboard(self):
        text = ''
        linesep = os.linesep

        t,l,b,r = self.selection
        data = self.table.data[t:b+1,l:r+1]
        text = ''.join(['\t'.join([locale.str(x) for x in line])+linesep for line in data]).strip()
        if self.write_clipboard(text):
            self.message('copied to clipboard: %d row(s), %d column(s)'%(b-t+1,r-l+1))
        else:
            self.message('copy failed and I don\'t know why', blink=True)

    def clipboard2grid(self):
        data = self.read_clipboard()
        if data is not None:
            rows,cols = data.shape
            self.table.data = data
            self.table.rowLabels = ['']*rows
            self.table.colLabels = ['']*cols
        else:
            self.message('clipboard content is no numeric 2d array', blink=True)
            
    def clipboard2selection(self):
        data = self.read_clipboard()
        if data is None:
            return
        shape = data.shape
        if data is not None:
            rows, cols = self.table.data.shape
            try:
                t,l,b,r = self.selection
            except:
                return
            if (t,l) == (0,0) and (r+1,b+1) == (cols, rows):
                self.table.data = data
            else:
                if b-t+1 == shape[0] and r-l+1 == shape[1]:
                    self.table.data[t:b+1,l:r+1] = data
                    #self.table.Update() # should work automatically when using a cbarray
                else:
                    self.message('unable to paste - selected area has different shape than clipboard content (%dx%d)'%shape, blink = True)
        else:
            self.message('paste failed and I don\'t know why', blink=True)

    def _selection_size(self):
        t,l,b,r = self.selection
        w = abs(r-l)+1
        h = abs(b-t)+1
        return (w,h)
    
    def modify_and_shift(self, cmd):
        t,l,b,r = self.selection
        w,h = self._selection_size()
        
        h = abs(b-t)+1
        rows,cols = self.table.data.shape

        def isr():
            cleararea = list(N.meshgrid(range(t,b+1),range(l,r+1)))
            fromarea = list(N.meshgrid(range(t,b+1),range(l,cols)))
            toarea = [fromarea[0],fromarea[1]+w]
            self.table.AppendCols(w)
            return fromarea,toarea,cleararea
        def isd():
            cleararea = list(N.meshgrid(range(t,b+1),range(l,r+1)))
            fromarea = list(N.meshgrid(range(t,rows),range(l,r+1)))
            toarea = [fromarea[0]+h,fromarea[1]]
            self.table.AppendRows(h)
            self.rowtoadd += h
            return fromarea,toarea,cleararea
        def dsl():
            cleararea = list(N.meshgrid(range(t,b+1),range(cols-w,cols)))
            fromarea = list(N.meshgrid(range(t,b+1),range(r+1,cols)))
            toarea = [fromarea[0],fromarea[1]-w]
            return fromarea,toarea,cleararea
        def dsu():
            cleararea = list(N.meshgrid(range(rows-h,rows),range(l,r+1)))
            fromarea = list(N.meshgrid(range(b+1,rows),range(l,r+1)))
            toarea = [fromarea[0]-h,fromarea[1]]
            return fromarea,toarea,cleararea

        mapping = {'insert shift right':isr,
                   'insert shift down':isd,
                   'delete shift left':dsl,
                   'delete shift up':dsu}

        fromarea,toarea,cleararea = mapping[cmd]()

        fromdata = self.table.tabledata[fromarea].copy()
        self.table.tabledata[toarea] = fromdata
        self.table.tabledata[cleararea] *= 0.0
        self.table.Update()
        self.view.grid.FitInside()
        self.view.grid.ClearSelection()

    def delete_rowscols(self):
        t,l,b,r = self.selection
        w,h = self._selection_size()
        rows,cols = self.table.data.shape
        
        if rows == h:
            self.table.DeleteCols(l, w)
        elif cols == w:
            self.table.DeleteRows(t, h)
        rows,cols = self.table.data.shape
        self.rowtoadd = min(rows-1, self.rowtoadd)
        
        self.view.grid.FitInside()
        self.view.grid.ClearSelection()
        
    def insert_rowscols(self, row_menu, col_menu):
        t,l,b,r = self.selection
        w,h = self._selection_size()
        rows,cols = self.table.data.shape
        if row_menu:
            n = abs(b-t)+1
            self.table.InsertRows(t, n)
            self.rowtoadd += n
        if col_menu:
            n = abs(r-l)+1
            self.table.InsertCols(l, n)
        self.view.grid.ClearSelection()
        self.view.grid.FitInside()

    def append_rowscols(self, row_menu, col_menu):
        t,l,b,r = self.selection
        w,h = self._selection_size()
        rows,cols = self.table.data.shape
        if row_menu:
            n = abs(b-t)+1
            self.table.AppendRows(n)
        if col_menu:
            n = abs(r-l)+1
            self.table.AppendCols(n)
        self.view.grid.ClearSelection()
        self.view.grid.FitInside()

    def get_selected_data(self):
        out = []
        t,l,b,r = self.selection
        if self.col0_is_x:
            x = self.table.data[t:b+1,0]
            if l > 0:
                l -= 1
        else:
            x = self.table.data[t:b+1,l]
            
        for n,y in enumerate(N.transpose(self.table.data[t:b+1,l+1:r+1])):
            name = self.table.colLabels[n+l+1]
            if name == '':
                name = 'col '+self.table.GetColLabelValue(n+l+1)
            out.append([[x,y], name])
        return self.name,out
        
    def add_par_row(self, data, setname):
        data = map(list,zip(*data))
        tokens = data.pop(0)
        vars = data.pop(0)
        dcol = len(vars)-self.table.data.shape[1]
        rows, cols = N.array(N.atleast_2d(data)).shape
        
        if dcol > 0:
            self.table.data = N.hstack((self.table.data, N.atleast_2d(N.zeros((self.table.data.shape[0],dcol)))))
        else:
            data = N.hstack((data, N.zeros((rows,-dcol))))
        if self.rowtoadd == 0:
            lab = ['%s:%s'%(t,v) for t,v in zip(tokens,vars)]
            self.table.colLabels[:len(lab)] = lab
        for row in data:
            self.table.SetRowLabelValue(self.rowtoadd, setname)
            self.table.data[self.rowtoadd] = row
            self.rowtoadd += 1
            if self.rowtoadd == self.table.GetNumberRows():
                self.table.AppendRows(1)
               
        self.table.Update()
        self.view.grid.FitInside()

    def message(self, msg, target=1, blink=False):
        event = misc.ShoutEvent(self.view.GetId(), msg=msg, target=target, blink=blink)
        wx.PostEvent(self.view, event)

def new_datagrid(parent_controller, main_view):
    c = Controller(parent_controller, GridContainer(main_view), GridContainerInteractor())
    return c

if __name__ == '__main__':
    dg = Datagrid(show_shell=True)
    a = cbarray([[1,2,3,4,5],[2,3,4,5,6]])
    
