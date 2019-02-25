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


try:
    import win32com.client
    WIN32 = True
except ImportError:
    WIN32 = False

import wx
from wx.lib.pubsub import pub as Publisher

import numpy as np
    
import os
import re
import traceback

from .. import misc_ui, misc, csvwizard, pomio

from .interactor import GridContainerInteractor, GridInteractor
from .view import GridContainer, GridPanel
from .tablebase import TableBase
from .databridge import DataBridge

class Controller(object):
    def __init__(self, parent_controller, view, interactor):
        self.view = view
        self.parent_controller = parent_controller

        self.gridcontrollers = []
        self.current = None
        self.the_grid = None

        interactor.Install(self, self.view)

    def __len__(self):
        return len(self.gridcontrollers)

    def new(self, data=None, name=None, the_grid=False):
        if name is None:
            name = 'grid %c'%chr(len(self.gridcontrollers)-int(self.the_grid is not None)+65)

        gc = GridController(self, GridPanel(self.view.nb), GridInteractor(), name, data=data, the_grid=the_grid)
        if self.the_grid is None and the_grid:
            self.the_grid = gc
        self.gridcontrollers.append(gc)
        self.view.nb.AddPage(gc.view, gc.name)

        self.view.nb.SetSelection(self.view.nb.GetPageCount()-1)
        locs = DataBridge(gc, self.view.shell.interp.locals)
        self.view.shell.interp.locals = locs
        self.current = gc
        return gc
    
    def page_changed(self, view):
        for gc in self.gridcontrollers:
            if view == gc.view:
                break
        locs = DataBridge(gc, self.view.shell.interp.locals)
        self.view.shell.interp.locals = locs
        self.current = gc

    def show_rename_dialog(self):
        newname = self.current.view.show_rename_dialog(self.current.name)
        if newname is not None:
            self.current.name = newname

    def transpose(self):
        self.current.view.grid.ClearSelection()
        self.current.table.transpose()

    def clear(self):
        self.view.nb.DeleteAllPages()
        del self.gridcontrollers[:]

    def clear_current(self):
        if self.current.the_grid:
            self.current.rowtoadd = 0
        self.current.table.clear()

    def resize(self, shape):
        self.current.table.resize(shape)

    def export_to_excel(self):
        try:
            wx.BeginBusyCursor()
            app = win32com.client.Dispatch('Excel.Application')
            wb_names = ['New Workbook']+[q.Name for q in app.Workbooks]
        except:
            return
        else:
            wx.EndBusyCursor()
            wb = self.view.export_excel_dialog(wb_names)
            if wb is not None:
                if wb == 0:
                    wb = app.Workbooks.Add()
                else:
                    wb = app.Workbooks.Item(wb)
                ws = wb.Worksheets.Add()
                #ws.Name = self.current.name.encode('ascii','ignore')
                #macht zu viel Aerger
                app.ScreenUpdating = False
                for y,row in enumerate(self.current.table.data):
                    for x,val in enumerate(row):
                        ws.Cells(y+1,x+1).Value = float(val)
                app.ScreenUpdating = True
                app.Visible = True

    def close_gridcontroller(self, selection):
        view = self.view.nb.GetCurrentPage()
        
        for gc in self.gridcontrollers:
            if view == gc.view:
                break
        if gc.the_grid:
            self.the_grid = None
        self.gridcontrollers.remove(gc)
        return True
        
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
            except IOError:
                self.table.data = data
            else:
                self.table.data = data
                self.table.rowlabels = rl
                self.table.collabels = cl
            self.view.grid.Update()

        self.name = name
        
        interactor.Install(self, self.view, the_grid)

        self.selection_changed(None)

    def none__getattr__(self, attr):
        if attr in ['data','rowlabels','collabels']:
            return getattr(self.table, attr)
        else:
            raise AttributeError(attr)

    def none__setattr__(self, attr, val):
        if attr in ['data','rowlabels','collabels']:
            setattr(self.table, attr, val)
        else:
            object.__setattr__(self, attr, val)

    @property
    def has_row_selection(self):
        return self.selection is not None and self._selection_size()[0] == self.table.data.shape[1] and self.view.selection_type == 'row'

    @property
    def has_col_selection(self):
        return self.selection is not None and self._selection_size()[1] == self.table.data.shape[0] and self.view.selection_type == 'col'

    def set_name(self, name):
        self._name = name
        if hasattr(self, 'view') and self.view is not None:
            self.view.name = name
    def get_name(self):
        return self._name
    name = property(get_name, set_name)

    def show_rename_dialog(self, row, col):
        if row > -1:
            val = self.table.rowLabels[row]
        elif col > -1:
            val = self.table.colLabels[col]

        res = self.view.show_rename_dialog(val)
        if res is not None:
            self.rename_rowcol_label(row, col, res)

    def rename_rowcol_label(self, row, col, val):
        if col >= 0:
            self.view.grid.SetColLabelValue(col, val)
        elif row >= 0:
            self.view.grid.SetRowLabelValue(row, val)

    def import_data(self, path):
        try:
            cr = csvwizard.CSVWizard(self.view, path)
        except csvwizard.FormatExpection as fe:
            wx.MessageBox(str(fe))
            return

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
        cl = self.table.colLabels
        rl = self.table.rowLabels

        if len([x for x in cl if x != '']) == 0:
            cl = None
        if len([x for x in rl if x != '']) == 0:
            rl = None

        if re.match(r'.+\.%s$'%ext, path) is None:
            path ='%s.%s'%(path,ext)

        if ext == 'csv':
            pomio.write_csv(path, self.table.data, rl, cl)
        elif ext == 'tex':
            pomio.write_tex(path, self.table.data, rl, cl)
        elif ext == 'txt':
            pomio.write_txt(path, self.table.data)

        misc.set_cwd(path)
        self.message('wrote %s'%path)
            
    def create_set(self, col0isX):
        self.col0_is_x = col0isX
        Publisher.sendMessage((self.view.id, 'grid', 'newset'), data=self.get_selected_data)

    def selection_changed(self, sel):
        self.selection = sel
        try:
            t,l,b,r = self.selection
        except:
            self.can_copy = False
            self.can_cut = False
            self.can_create_set = 0
        else:
            self.can_copy = True
            self.can_cut = r-l+1 == self.table.data.shape[1] or b-t+1 == self.table.data.shape[0]
            self.selection1d = (r==l) != (b==t)
            if  b-t >= 1:
                self.can_create_set = 1
                if r-l >= 1:
                    self.can_create_set = 2
            else:
                self.can_create_set = 0
        self.can_paste = self.check_clipboard() and self.selection is not None
        
    def clear_selection(self):
        self.view.grid.ClearSelection()

    def check_clipboard(self):
        state = False
        if wx.TheClipboard.Open():
            do = wx.TextDataObject()
            state = wx.TheClipboard.GetData(do)
            wx.TheClipboard.Close()
        return state

    def read_clipboard(self):
        if wx.TheClipboard.Open():
            do = wx.TextDataObject()
            success = wx.TheClipboard.GetData(do)
            wx.TheClipboard.Close()
            if success:
                text = do.GetText().strip()
                if text != '':
                    header, data = misc.str2array(text)
                    return header, data
        return None
    
    def write_clipboard(self, text):
        if wx.TheClipboard.Open():
            do = wx.TextDataObject()
            do.SetText(text)
            wx.TheClipboard.SetData(do)
            wx.TheClipboard.Close()
            #self.view.grid.ClearSelection()
            return True
        else:
            return False
        
    def selection2clipboard(self):
        text = ''
        linesep = os.linesep

        t,l,b,r = self.selection
        data = self.table.data[t:b+1,l:r+1]
        text = ''.join(['\t'.join([repr(x) for x in line])+linesep for line in data]).strip()
        if self.write_clipboard(text):
            self.message('copied to clipboard: %d row(s), %d column(s)'%(b-t+1,r-l+1))
        else:
            self.message('copy failed and I don\'t know why', blink=True)

    def clipboard2grid(self):
        try:
            header,data = self.read_clipboard()
        except:
            self.message('unable to parse clipboard data')
            traceback.print_exc()
            return
        else:
            if data is None:
                self.message('no numeric data found in clipboard')
                return

        if data is not None:
            rows,cols = data.shape
            self.table.data = data
            self.table.rowLabels = ['']*rows
            try:
                self.table.colLabels = header
            except:
                self.table.colLabels = ['']*cols
        else:
            self.message('clipboard content is no numeric 2d array', blink=True)

    @property
    def clipboard_data(self):
        try:
            header,data = self.read_clipboard()
        except:
            return None
        else:
            return data # may be None in case it's content is non numeric

    def clipboard2selection(self):
        try:
            header,data = self.read_clipboard()
        except:
            self.message('unable to parse clipboard data')
            #traceback.print_exc()
            return
        else:
            if data is None:
                self.message('no numeric data found in clipboard')
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

                if header is not None:
                    self.table.colLabels = header

            elif t == b and l == r:
                self.table.AppendCols(l+shape[1]-cols)
                self.table.AppendRows(t+shape[0]-rows)
                self.table.data[t:t+shape[0],l:l+shape[1]] = data
            else:
                if b-t+1 == shape[0] and r-l+1 == shape[1]:
                    self.table.data[t:b+1,l:r+1] = data
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
            cleararea = list(np.meshgrid(list(range(t,b+1)),list(range(l,r+1))))
            fromarea = list(np.meshgrid(list(range(t,b+1)),list(range(l,cols))))
            toarea = [fromarea[0],fromarea[1]+w]
            self.table.AppendCols(w)
            return fromarea,toarea,cleararea
        def isd():
            cleararea = list(np.meshgrid(list(range(t,b+1)),list(range(l,r+1))))
            fromarea = list(np.meshgrid(list(range(t,rows)),list(range(l,r+1))))
            toarea = [fromarea[0]+h,fromarea[1]]
            self.table.AppendRows(h)
            self.rowtoadd += h
            return fromarea,toarea,cleararea
        def dsl():
            cleararea = list(np.meshgrid(list(range(t,b+1)),list(range(cols-w,cols))))
            fromarea = list(np.meshgrid(list(range(t,b+1)),list(range(r+1,cols))))
            toarea = [fromarea[0],fromarea[1]-w]
            return fromarea,toarea,cleararea
        def dsu():
            cleararea = list(np.meshgrid(list(range(rows-h,rows)),list(range(l,r+1))))
            fromarea = list(np.meshgrid(list(range(b+1,rows)),list(range(l,r+1))))
            toarea = [fromarea[0]-h,fromarea[1]]
            return fromarea,toarea,cleararea

        mapping = {'insert shift right':isr,
                   'insert shift down':isd,
                   'delete shift left':dsl,
                   'delete shift up':dsu}

        fromarea,toarea,cleararea = mapping[cmd.lower()]()

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

    def insert_rowscols_paste(self):
        data = self.clipboard_data
        if data is not None:
            t,l,b,r = self.selection
            w,h = self._selection_size()
            clip_rows, clip_cols = data.shape
            rows,cols = self.table.data.shape

            if rows == clip_rows:
                self.table.InsertCols(l, clip_cols)
                self.selection = t,l,b,r+clip_cols-1
            if cols == clip_cols:
                self.table.InsertRows(t, clip_rows)
                self.rowtoadd += clip_rows
                self.selection = t,l,b+clip_rows-1,r
            self.clipboard2selection()
            self.view.grid.ClearSelection()
            self.view.grid.FitInside()
        else:
            self.message('Unable to parse clipboard data')

    def insert_rowscols(self, where = None):
        t,l,b,r = self.selection
        w,h = self._selection_size()
        rows,cols = self.table.data.shape
        if where is not None:
            row_menu, col_menu = where
        else:
            row_menu = cols==w
            col_menu = rows==h
        if row_menu:
            n = abs(b-t)+1
            self.table.InsertRows(t, n)
            self.rowtoadd += n
        if col_menu:
            n = abs(r-l)+1
            self.table.InsertCols(l, n)
        #self.view.grid.ClearSelection()
        self.view.grid.FitInside()

    def append_rowscols(self, where=None):
        t,l,b,r = self.selection
        w,h = self._selection_size()
        rows,cols = self.table.data.shape
        if where is not None:
            row_menu, col_menu = where
        else:
            row_menu = cols==w
            col_menu = rows==h
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
            
        for n,y in enumerate(np.transpose(self.table.data[t:b+1,l+1:r+1])):
            name = self.table.colLabels[n+l+1]
            if name == '':
                name = 'col '+self.table.GetColLabelValue(n+l+1)
            out.append([[x,y], name])
        return self.name,out
        
    def add_par_row(self, data, setname):
        data = list(map(list,list(zip(*data))))
        tokens = data.pop(0)
        vars = data.pop(0)
        dcol = len(vars)-self.table.data.shape[1]
        rows, cols = np.array(np.atleast_2d(data)).shape
        
        if dcol > 0:
            self.table.data = np.hstack((self.table.data, np.atleast_2d(np.zeros((self.table.data.shape[0],dcol)))))
        else:
            data = np.hstack((data, np.zeros((rows,-dcol))))
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
        event = misc_ui.ShoutEvent(self.view.GetId(), msg=msg, target=target, blink=blink)
        wx.PostEvent(self.view, event)

def create(parent_controller, main_view):
    c = Controller(parent_controller, GridContainer(main_view, WIN32), GridContainerInteractor())
    return c

if __name__ == '__main__':
    import numpy as np
    import wx.lib.mixins.inspection as wit
    app = wit.InspectableApp()

    f = wx.Frame(None)
    f.Show()
    gc = GridController(None, GridPanel(f), GridInteractor(), 'test', data=np.zeros((5,5)), the_grid=False)
    app.MainLoop()


