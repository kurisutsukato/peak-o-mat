import wx
from wx.lib import flatnotebook as fnb

from peak_o_mat import misc, io, csvwizard

from view import ID_NEW, ID_LOAD, ID_SAVE, ID_EXPORT

class GridContainerInteractor(object):
    import_fileext = 0
    def Install(self, controller, view):
        self.controller = controller
        self.view = view

        self.view.Bind(wx.EVT_CLOSE, self.OnClose)
        self.view.Bind(fnb.EVT_FLATNOTEBOOK_PAGE_CHANGED, self.OnPageChanged, self.view.nb)
        self.view.Bind(fnb.EVT_FLATNOTEBOOK_PAGE_CLOSING, self.OnPageClosing)
        self.view.Bind(wx.EVT_BUTTON, self.OnTranspose, self.view.btn_transpose)
        self.view.Bind(wx.EVT_BUTTON, self.OnClear, self.view.btn_clear)
        self.view.Bind(wx.EVT_BUTTON, self.OnResize, self.view.btn_resize)
        self.view.Bind(wx.EVT_TEXT, self.OnSizeEntered, self.view.txt_resize)
        
        self.view.Bind(wx.EVT_MENU, self.OnLoad, id=ID_LOAD)
        self.view.Bind(wx.EVT_MENU, self.OnSave, id=ID_SAVE)
        self.view.Bind(wx.EVT_MENU, self.OnNew, id=ID_NEW)

    def OnLoad(self, evt):
        wc = "CSV files (*.csv)|*.csv|DAT files (*.dat)|*.dat|All files (*)|*"
        dlg = wx.FileDialog(self.view, defaultDir=misc.cwd(), wildcard=wc, style=wx.OPEN)
        dlg.SetFilterIndex(self.import_fileext)
        if dlg.ShowModal() == wx.ID_OK:
            gc = self.controller.new()
            path = dlg.GetPaths()[0]
            self.import_fileext = dlg.GetFilterIndex()
            gc.import_data(path)
            misc.set_cwd(path)
        
    def OnSave(self, evt=None):
        dlg = wx.FileDialog(self.view, defaultFile="", defaultDir=misc.cwd(), wildcard="CSV files (*.csv)|*.csv|TEX tabluar (*.tex)|*.tex", style=wx.SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            ext = ['csv','tex'][dlg.GetFilterIndex()]
            self.controller.current.export_data(path, ext)
            misc.set_cwd(path)
            
    def OnNew(self, evt):
        gc = self.controller.new()
        
    def OnTranspose(self, evt):
        self.controller.transpose()

    def OnClear(self, evt):
        dlg = wx.MessageDialog(self.view, 'Are you sure to delete all grid data?', 'Warning',style=wx.YES_NO|wx.NO_DEFAULT|wx.ICON_EXCLAMATION)
        if dlg.ShowModal() == wx.ID_YES:
            self.controller.clear()

    def OnResize(self, evt):
        dlg = wx.MessageDialog(self.view, 'This will clear the data grid.\n\nAre you sure to resize?', 'Warning',style=wx.YES_NO|wx.NO_DEFAULT|wx.ICON_EXCLAMATION)
        if dlg.ShowModal() == wx.ID_YES:
            val = self.view.txt_resize.GetValue()
            x,y = [int(q) for q in val.split(',')]
            self.controller.resize((x,y))
        
    def OnSizeEntered(self, evt):
        val = evt.GetEventObject().GetValue()
        try:
            x,y = [int(q) for q in val.split(',')]
        except:
            self.view.btn_resize.Disable()
        else:
            self.view.btn_resize.Enable()

    def OnClose(self, evt):
        self.controller.hide()

    def OnPageClosing(self, evt):
        if self.controller.close_gridcontroller(evt.GetSelection()):
            evt.Allow()
        else:
            evt.Veto()
        
    def OnPageChanged(self, evt):
        self.controller.page_changed(self.view.nb.GetCurrentPage())
        
class GridInteractor(object):
    import_fileext = 0
    selection = None
    selecting = False
    col_menu = False
    row_menu = False
    pointer_pos = (-1,-1)
    
    def Install(self, controller, view, the_grid=False):
        self.controller = controller
        self.view = view

        self.init_menus()

        #self.view.Bind(wx.EVT_BUTTON, self.OnTranspose, self.view.btn_transpose)
        #self.view.Bind(wx.EVT_BUTTON, self.OnClear, self.view.btn_clear)
        #self.view.Bind(wx.EVT_BUTTON, self.OnPasteReplace, self.view.btn_pastereplace)
        #self.view.Bind(wx.EVT_BUTTON, self.OnUnselect, self.view.btn_unselect)
        #self.view.Bind(wx.EVT_BUTTON, self.OnSave, self.view.btn_save)
        #self.view.Bind(wx.EVT_BUTTON, self.OnLoad, self.view.btn_load)
        #self.view.Bind(wx.EVT_BUTTON, self.OnClose, self.view.btn_close)
        #self.view.Bind(wx.EVT_BUTTON, self.OnResize, self.view.btn_resize)
        #self.view.Bind(wx.EVT_TEXT, self.OnSizeEntered, self.view.txt_resize)

        self.view.grid.Bind(wx.grid.EVT_GRID_RANGE_SELECT, self.OnSelectedRange)
        self.view.grid.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.OnSelectCell)
                            
        if the_grid:
            self.view.grid.GetGridRowLabelWindow().Bind(wx.EVT_PAINT, self.OnGridRowLabelPaint)
            self.view.grid.Bind(wx.grid.EVT_GRID_LABEL_LEFT_DCLICK, self.OnGridLabelLeftDClick)

    def init_menus(self):
        self.cellmenumap = [(-1,'plot (X from col0)', lambda evt: self.OnCreateSet(evt, col0isX=True)),
                            (-1,'plot (XY from selection)', lambda evt: self.OnCreateSet(evt, col0isX=False)),
                            (wx.ID_SEPARATOR, '', None),
                            (-1,'insert shift right',self.OnMenuInsDelNShift),
                            (-1,'insert shift down',self.OnMenuInsDelNShift),
                            (-1,'delete shift left',self.OnMenuInsDelNShift),
                            (-1,'delete shift up',self.OnMenuInsDelNShift),
                            (wx.ID_SEPARATOR, '', None),
                            (-1, 'copy', self.OnCopy),
                            (-1, 'paste', self.OnPaste),
                            ]

        self.labelmenumap = [(-1,'plot (X from col0)', lambda evt: self.OnCreateSet(evt, col0isX=True)),
                             (-1,'plot (XY from selection)', lambda evt: self.OnCreateSet(evt, col0isX=False)),
                             (wx.ID_SEPARATOR, '', None),
                             (-1,'delete',self.OnMenuDelete),
                             (-1,'insert',self.OnMenuInsert),
                             (-1,'append',self.OnMenuAppend),
                             (wx.ID_SEPARATOR, '', None),
                             (-1, 'copy', self.OnCopy),
                             (-1, 'paste', self.OnPaste),
                             (wx.ID_SEPARATOR, '', None),
                             (-1, 'rename', self.OnRename),
                             ]

        self.cellmenu = wx.Menu()
        for id,text,act in self.cellmenumap:
            item = wx.MenuItem(self.cellmenu, id=id, text=text)
            item = self.cellmenu.AppendItem(item)
            if act is not None:
                self.view.Bind(wx.EVT_MENU, act, item)

        self.labelmenu = wx.Menu()
        for id,text,act in self.labelmenumap:
            item = wx.MenuItem(self.labelmenu, id=id, text=text)
            item = self.labelmenu.AppendItem(item)
            self.view.Bind(wx.EVT_MENU, act, item)
        
        self.view.Bind(wx.grid.EVT_GRID_LABEL_RIGHT_CLICK, self.OnLabelMenu)
        self.view.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.OnCellMenu)

    def OnCopy(self, evt):
        self.controller.selection2clipboard()

    def OnPaste(self, evt):
        self.controller.clipboard2selection()

    def OnPasteReplace(self, evt):
        self.controller.clipboard2grid()

    def OnUnselect(self, evt):
        self.controller.clear_selection()

    def OnRename(self, evt):
        if self.pointer_pos != (-1,-1):
            self.controller.show_rename_dialog(*self.pointer_pos)
        
    def OnLabelMenu(self, evt):
        self.pointer_pos = evt.GetRow(),evt.GetCol()
        self.col_menu = evt.GetCol() >= 0
        self.row_menu = evt.GetRow() >= 0

        for i in range(3):
            item = self.labelmenu.FindItemByPosition(i).GetId()
            self.labelmenu.Enable(item, self.controller.can_create_set >= i+1)
        for i in range(3,6):
            item = self.labelmenu.FindItemByPosition(i).GetId()
            self.labelmenu.Enable(item, self.selection is not None)
        for i in range(7,9):
            item = self.labelmenu.FindItemByPosition(i).GetId()
            self.labelmenu.Enable(item, self.controller.can_copy)
        self.labelmenu.Enable(self.labelmenu.FindItemByPosition(10).GetId(), self.pointer_pos != (-1,-1))
        self.view.PopupMenu(self.labelmenu, evt.GetPosition())

    def OnCellMenu(self, evt):
        for i in range(3):
            item = self.cellmenu.FindItemByPosition(i).GetId()
            self.cellmenu.Enable(item, self.controller.can_create_set >= i+1)
        for i in range(3,4+3):
            item = self.cellmenu.FindItemByPosition(i).GetId()
            self.cellmenu.Enable(item, self.selection is not None)
        for i in range(8,10):
            item = self.cellmenu.FindItemByPosition(i).GetId()
            self.cellmenu.Enable(item, self.controller.can_copy)
        self.view.PopupMenu(self.cellmenu, evt.GetPosition())

    def OnMenuInsDelNShift(self, evt):
        cmd = self.cellmenu.FindItemById(evt.GetId()).GetText()
        self.controller.modify_and_shift(cmd)

    def OnMenuDelete(self, evt):
        self.controller.delete_rowscols()

    def OnMenuInsert(self, evt):
        self.controller.insert_rowscols(self.row_menu, self.col_menu)

    def OnMenuAppend(self, evt):
        self.controller.append_rowscols(self.row_menu, self.col_menu)

    def OnSelectCell(self, evt):
        t,l = evt.GetRow(),evt.GetCol()
        self.view.grid.SelectBlock(t,l,t,l)
        evt.Skip()

    def OnSelectedRange(self, evt): 
        """Internal update to the selection tracking list"""
        if self.selecting:
            return
        top,bottom = evt.GetTopRow(),evt.GetBottomRow()
        left,right = evt.GetLeftCol(),evt.GetRightCol()
        rows,cols = self.controller.table.data.shape

        pointeronlabel = False
        
        if evt.Selecting():
            if rows == bottom-top+1 or cols == right-left+1:
                pointeronlabel = True
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
            if not pointeronlabel or evt.ControlDown():
                self.selecting = True
                self.view.grid.SelectBlock(*self.selection)
                self.selecting = False
                

        self.controller.selection_changed(self.selection)
        
    def OnSizeEntered(self, evt):
        val = evt.GetEventObject().GetValue()
        try:
            x,y = [int(q) for q in val.split(',')]
        except:
            self.view.btn_resize.Disable()
        else:
            self.view.btn_resize.Enable()

    def OnResize(self, evt):
        dlg = wx.MessageDialog(self.view, 'This will clear the data grid.\n\nAre you sure to resize?', 'Warning',style=wx.YES_NO|wx.NO_DEFAULT|wx.ICON_EXCLAMATION)
        if dlg.ShowModal() == wx.ID_YES:
            val = self.view.txt_resize.GetValue()
            x,y = [int(q) for q in val.split(',')]
            self.controller.resize((x,y))
        
    def OnTranspose(self, evt):
        self.controller.transpose()

    def OnLoad(self, evt):
        wc = "CSV files (*.csv)|*.csv|DAT files (*.dat)|*.dat|All files (*)|*"
        dlg = wx.FileDialog(self.view, defaultDir=misc.cwd(), wildcard=wc, style=wx.OPEN)
        dlg.SetFilterIndex(self.import_fileext)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPaths()[0]
            self.import_fileext = dlg.GetFilterIndex()
            self.controller.import_data(path)
            misc.set_cwd(path)
        
    def OnSave(self, evt=None):
        #dlg = wx.FileDialog(self.view, defaultFile="", defaultDir=misc.cwd(), wildcard="CSV files (*.csv)|*.csv|TEX tabluar (*.tex)|*.tex", style=wx.SAVE)
        print misc.cwd()
        dlg = wx.FileDialog(self.view, defaultFile="", defaultDir=misc.cwd(), wildcard="CSV files (*.csv)|*.csv|TEX tabluar (*.tex)|*.tex", style=wx.SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            ext = ['csv','tex'][dlg.GetFilterIndex()]
            self.controller.export_data(path, ext)
            misc.set_cwd(path)
            
    def OnClear(self, evt):
        dlg = wx.MessageDialog(self.view, 'Are you sure to delete all grid data?', 'Warning',style=wx.YES_NO|wx.NO_DEFAULT|wx.ICON_EXCLAMATION)
        if dlg.ShowModal() == wx.ID_YES:
            self.controller.clear()

    def OnClose(self, evt):
        dlg = wx.MessageDialog(self.view, 'Really close this page?\nAll data will be lost!', 'Warning',style=wx.YES_NO|wx.NO_DEFAULT|wx.ICON_EXCLAMATION)
        if dlg.ShowModal() == wx.ID_YES:
            self.controller.close()
        
    def OnGridRowLabelPaint(self, evt):
        self.view.grid.paint_row_header(self.controller.rowtoadd)
        
    def OnGridLabelLeftDClick(self, evt):
        row = evt.GetRow()
        if row >= 0:
            self.controller.rowtoadd = row
            self.view.grid.Refresh()

    def OnCreateSet(self, evt, col0isX=True):
        self.controller.create_set(col0isX)

