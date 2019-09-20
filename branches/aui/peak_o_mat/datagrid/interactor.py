import wx
import wx.grid

from pubsub import pub

from wx.lib.agw import flatnotebook as fnb

from .. import misc, pomio, csvwizard

from .view import ID_NEW, ID_LOAD, ID_SAVE, ID_EXPORT, ID_DELETE, ID_CUT, ID_COPY,\
                 ID_PASTE, ID_INSERTPASTE, ID_APPEND, ID_INSERT, ID_SETVALUES,\
                 ID_PLOTY, ID_PLOTXY

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
        self.view.Bind(wx.EVT_BUTTON, self.OnRename, self.view.btn_rename)
        self.view.Bind(wx.EVT_BUTTON, self.OnExportExcel, self.view.btn_export_excel)

        menumap = {ID_LOAD:self.OnLoad, ID_SAVE:self.OnSave, ID_NEW:self.OnNew, ID_DELETE:self.OnDelete,
                   ID_COPY:self.OnCopy, ID_CUT:self.OnCut, ID_PASTE:self.OnPaste,
                   ID_INSERTPASTE:self.OnInsertPaste, ID_APPEND:self.OnAppend,
                   ID_INSERT:self.OnInsert, ID_SETVALUES:self.OnSetValues,
                   ID_PLOTY:lambda evt: self.OnPlot(evt, col0isX=True),
                   ID_PLOTXY:lambda evt: self.OnPlot(evt, col0isX=False)}

        for k,v in menumap.items():
            self.view.Bind(wx.EVT_MENU, v, id=k)

        self.view.Bind(wx.EVT_IDLE, self.OnIdle)

    def OnIdle(self, evt):
        self.view.btn_export_excel.Enable(len(self.controller) > 0)
        self.view.btn_transpose.Enable(len(self.controller) > 0)
        self.view.btn_clear.Enable(len(self.controller) > 0)
        self.view.btn_rename.Enable(len(self.controller) > 0)

        if self.controller.current is not None:
            sm = self.view.selection_menu
            pm = self.view.plot_menu

            if self.controller.current.has_row_selection:
                sm['Insert'].SetItemLabel('Insert rows\tCTRL-i')
                sm['Append'].SetItemLabel('Append rows\tCTRL-a')
                [sm[q].Enable() for q in ['Insert','Append']]
            elif self.controller.current.has_col_selection:
                sm['Insert'].SetItemLabel('Insert columns\tCTRL-i')
                sm['Append'].SetItemLabel('Append columns\tCTRL-a')
                [sm[q].Enable() for q in ['Insert','Append']]
            else:
                sm['Insert'].SetItemLabel('Insert')
                sm['Append'].SetItemLabel('Append')
                [sm[q].Enable(False) for q in ['Insert','Append']]

            sm['Cut'].Enable(self.controller.current.can_cut)
            sm['Delete'].Enable(self.controller.current.can_cut)
            sm['Copy'].Enable(self.controller.current.can_copy)
            sm['Paste'].Enable(self.controller.current.can_paste)
            sm['Insert & paste'].Enable(self.controller.current.can_paste)
            sm['Set values...'].Enable(self.controller.current.can_cut and \
                                       self.controller.current.selection1d)

            pm['Plot Y'].Enable(self.controller.current.can_create_set > 0)
            pm['Plot XY'].Enable(self.controller.current.can_create_set > 1)

    def OnSetValues(self, evt):
        w,h = self.controller.current._selection_size()
        rows,cols = self.controller.current.table.data.shape
        t,l,b,r = self.controller.current.selection
        if rows == h:
            val = '_col{} = '.format(l)
        elif cols == w:
            val = '_row{} = '.format(t)
        else:
            return
        dlg = wx.TextEntryDialog(self.view, 'Set values', 'Set row or column values',val)
        if dlg.ShowModal() == wx.ID_OK:
            val = dlg.GetValue()
            self.view.sh.write(val)
            self.view.sh.push(val)

    def OnPlot(self, evt, col0isX=True):
        self.controller.current.create_set(col0isX)

    def OnAppend(self, evt):
        self.controller.current.append_rowscols()

    def OnInsert(self, evt):
        self.controller.current.insert_rowscols()

    def OnCopy(self, evt):
        self.controller.current.selection2clipboard()

    def OnDelete(self, evt):
        self.controller.current.delete_rowscols()

    def OnCut(self, evt):
        self.controller.current.selection2clipboard()
        self.controller.current.delete_rowscols()

    def OnPaste(self, evt):
        self.controller.current.clipboard2selection()

    def OnInsertPaste(self, evt):
        self.controller.current.insert_rowscols_paste()

    def OnExportExcel(self, evt):
        self.controller.export_to_excel()

    def OnLoad(self, evt):
        wc = "CSV files (*.csv)|*.csv|All files (*)|*"
        dlg = wx.FileDialog(self.view, defaultDir=misc.cwd(), wildcard=wc, style=wx.FD_OPEN)
        dlg.SetFilterIndex(self.import_fileext)
        if dlg.ShowModal() == wx.ID_OK:
            gc = self.controller.new()
            path = dlg.GetPaths()[0]
            self.import_fileext = dlg.GetFilterIndex()
            gc.import_data(path)
            misc.set_cwd(path)
        
    def OnSave(self, evt=None):
        dlg = wx.FileDialog(self.view, defaultFile="", defaultDir=misc.cwd(),
                            wildcard="Text - w/o headers (*.txt)|*.txt|CSV files (*.csv)|*.csv|TEX tabluar (*.tex)|*.tex", style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            ext = ['txt','csv','tex'][dlg.GetFilterIndex()]
            self.controller.current.export_data(path, ext)
            misc.set_cwd(path)
            
    def OnNew(self, evt):
        gc = self.controller.new()
        
    def OnTranspose(self, evt):
        self.controller.transpose()

    def OnRename(self, evt):
        self.controller.show_rename_dialog()

    def OnClear(self, evt):
        dlg = wx.MessageDialog(self.view, 'Are you sure to delete all grid data?', 'Warning',style=wx.YES_NO|wx.NO_DEFAULT|wx.ICON_EXCLAMATION)
        if dlg.ShowModal() == wx.ID_YES:
            self.controller.clear_current()

    def OnClose(self, evt):
        self.view.Hide()

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
        self.frame = self.view
        while self.frame.GetName() != 'frame':
            self.frame = self.frame.GetParent()

        self.init_menus()

        self.view.grid.Bind(wx.grid.EVT_GRID_RANGE_SELECT, self.OnSelectedRange)
        self.view.grid.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.OnSelectCell)
                            
        if the_grid:
            self.view.grid.GetGridRowLabelWindow().Bind(wx.EVT_PAINT, self.OnGridRowLabelPaint)
            self.view.grid.Bind(wx.grid.EVT_GRID_LABEL_LEFT_DCLICK, self.OnGridLabelLeftDClick)

        self.view.grid.Bind(wx.grid.EVT_GRID_LABEL_LEFT_CLICK, self.OnLabelClick)

        self.view.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)

    def OnLabelClick(self, evt):
        self.view.selection_type = ['row','col'][1 if evt.GetCol() > -1 else 0]
        self.view.grid.SetFocus()
        evt.Skip()


    def OnKeyDown(self, evt):
        # TODO
        '''replace with accelerator table'''
        # vielleicht gar nicht mehr noetig, weil menu shortcut
        codes = [67,86]
        kc = evt.GetKeyCode()
        if evt.CmdDown() and kc in codes:
            action = [self.OnCopy, self.OnPaste]
            action[codes.index(kc)](None)
        else:
            evt.Skip()
            
    def init_menus(self):
        self.cellmenumap = [(-1,'Insert shift right',self.OnMenuInsDelNShift),
                            (-1,'Insert shift down',self.OnMenuInsDelNShift),
                            (-1,'Delete shift left',self.OnMenuInsDelNShift),
                            (-1,'Delete shift up',self.OnMenuInsDelNShift),
                            (wx.ID_SEPARATOR, '', None),
                            (-1, 'Copy', self.OnCopy),
                            (-1, 'Paste', self.OnPaste),
                            ]

        # self.labelmenumap = [(-1,'Plot (X from column 0)', lambda evt: self.OnCreateSet(evt, col0isX=True)),
        #                      (-1,'Plot (XY from selection)', lambda evt: self.OnCreateSet(evt, col0isX=False)),
        #                      (wx.ID_SEPARATOR, '', None),
        #                      (-1,'Delete',self.OnMenuDelete),
        #                      (-1,'Insert',self.OnMenuInsert),
        #                      (-1,'Append',self.OnMenuAppend),
        #                      (wx.ID_SEPARATOR, '', None),
        #                      (-1, 'Cut', self.OnCut),
        #                      (-1, 'Copy', self.OnCopy),
        #                      (-1, 'Paste', self.OnPaste),
        #                      (-1, 'Insert && Paste', self.OnInsertPaste),
        #                      (wx.ID_SEPARATOR, '', None),
        #                      (-1, 'Rename', self.OnRename),
        #                      (-1, 'Formula', self.OnFormula)
        #                      ]
        self.labelmenumap = [(-1, 'Rename', self.OnRename)]

        self.cellmenu = wx.Menu()
        for id,text,act in self.cellmenumap:
            item = wx.MenuItem(self.cellmenu, id=id, text=text)
            item = self.cellmenu.Append(item)
            if act is not None:
                self.frame.Bind(wx.EVT_MENU, act, item)

        self.labelmenu = wx.Menu()
        for id,text,act in self.labelmenumap:
            item = wx.MenuItem(self.labelmenu, id=id, text=text)
            item = self.labelmenu.Append(item)
            if act is not None:
                self.frame.Bind(wx.EVT_MENU, act, item)
        
        self.view.Bind(wx.grid.EVT_GRID_LABEL_RIGHT_CLICK, self.OnLabelMenu)
        self.view.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.OnCellMenu)

    def OnCut(self, evt):
        self.controller.selection2clipboard()
        self.controller.delete_rowscols()

    def OnCopy(self, evt):
        self.controller.selection2clipboard()

    def OnPaste(self, evt):
        self.controller.clipboard2selection()

    def OnInsertPaste(self, evt):
        self.controller.insert_rowscols_paste()

    def OnPasteReplace(self, evt):
        self.controller.clipboard2grid()

    def OnUnselect(self, evt):
        self.controller.clear_selection()

    def OnRename(self, evt):
        if self.pointer_pos != (-1,-1):
            self.controller.show_rename_dialog(*self.pointer_pos)

    def OnLabelMenu(self, evt):
        self.pointer_pos = evt.GetRow(),evt.GetCol()
        self.frame.PopupMenu(self.labelmenu, evt.GetPosition())

    def OnCellMenu(self, evt):
        #for i in range(3):
        #    item = self.cellmenu.FindItemByPosition(i).GetId()
        #    self.cellmenu.Enable(item, self.controller.can_create_set >= i+1)
        for i in range(4):
            item = self.cellmenu.FindItemByPosition(i).GetId()
            self.cellmenu.Enable(item, self.selection is not None)
        for i in range(4,6):
            item = self.cellmenu.FindItemByPosition(i).GetId()
            self.cellmenu.Enable(item, self.controller.can_copy)
        self.frame.PopupMenu(self.cellmenu, evt.GetPosition())

    def OnMenuInsDelNShift(self, evt):
        cmd = self.cellmenu.FindItemById(evt.GetId()).GetText()
        self.controller.modify_and_shift(cmd)

    def OnMenuDelete(self, evt):
        self.controller.delete_rowscols()

    def OnMenuInsert(self, evt):
        self.controller.insert_rowscols((self.row_menu, self.col_menu))

    def OnMenuAppend(self, evt):
        self.controller.append_rowscols((self.row_menu, self.col_menu))

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
            #if not pointeronlabel or evt.ControlDown():
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
        #print misc.cwd()
        dlg = wx.FileDialog(self.view, defaultFile="", defaultDir=misc.cwd(), wildcard="CSV files (*.csv)|*.csv|TEX tabluar (*.tex)|*.tex", style=wx.SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            ext = ['csv','tex'][dlg.GetFilterIndex()]
            self.controller.export_data(path, ext)
            misc.set_cwd(path)

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
