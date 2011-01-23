import wx
import wx.grid
import wx.lib.flatnotebook as fnb

from wx.py import shell
from wx.lib.splitter import MultiSplitterWindow

from peak_o_mat import misc

ID_LOAD = wx.NewId()
ID_SAVE = wx.NewId()
ID_NEW = wx.NewId()
ID_EXPORT = wx.NewId()

class GridContainer(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, 'datagrid', size=(700,400), style=wx.DEFAULT_FRAME_STYLE|wx.FRAME_FLOAT_ON_PARENT)
        self.CreateStatusBar()
        self.init_menu()

        pan = wx.Panel(self, -1)

        splitter = MultiSplitterWindow(pan, style=wx.SP_LIVE_UPDATE)
        splitter.SetOrientation(wx.VERTICAL)
        self.nb = fnb.FlatNotebook(splitter, -1, name='grid_notebook', style=fnb.FNB_NODRAG|fnb.FNB_NO_X_BUTTON|fnb.FNB_X_ON_TAB)

        shellpanel = wx.Panel(splitter, -1)
        sh = shell.Shell(shellpanel, -1, introText='datagrid shell')
        #sh.SetWindowStyleFlag(sh.GetWindowStyleFlag()|wx.SUNKEN_BORDER)
        sh.SetMinSize((-1,130))
        #sh.Refresh()
        self.shell = sh

        splitter.AppendWindow(self.nb, 250)
        splitter.AppendWindow(shellpanel, 140)

        self.btn_transpose = wx.Button(shellpanel, -1, '&transpose', style=wx.BU_EXACTFIT)
        self.btn_clear = wx.Button(shellpanel, -1, 'clear', style=wx.BU_EXACTFIT)
        self.btn_resize = wx.Button(shellpanel, -1, 'resize', style=wx.BU_EXACTFIT)
        self.txt_resize = wx.TextCtrl(shellpanel, -1, '30,5')

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.btn_transpose, 0, wx.ALL|wx.EXPAND, 2)
        hbox.Add(self.btn_clear, 0, wx.ALL|wx.EXPAND, 2)
        hbox.Add(wx.Window(shellpanel, -1, size=(20,0)))
        hbox.Add(self.btn_resize, 0, wx.ALL|wx.EXPAND, 2)
        hbox.Add(self.txt_resize, 0, wx.ALL|wx.EXPAND, 2)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.Add(sh, 1, wx.EXPAND)
        shellpanel.SetSizer(vbox)
        
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(splitter, 1, wx.EXPAND)
        #box.Add(sh, 1, wx.EXPAND)
        pan.SetSizer(box)

    def init_menu(self):
        menubar = wx.MenuBar()
        menu = wx.Menu()
        menubar.Append(menu, 'Data')
        menu.Append(ID_NEW, "New", "open an new datagrid", wx.ITEM_NORMAL)
        menu.Append(ID_LOAD, "Load...", "load table data", wx.ITEM_NORMAL)
        menu.Append(ID_SAVE, "Save...", "save table data", wx.ITEM_NORMAL)
        #menu.Append(ID_EXPORT, "Export...", "export table data", wx.ITEM_NORMAL)
        self.SetMenuBar(menubar)

class GridPanel(wx.Panel):
    def __init__(self, parent, show_shell=False):
        wx.Panel.__init__(self, parent)
        self.init(show_shell)

    def init(self, show_shell=False):
        
        #self.btn_copy = wx.Button(self, -1, 'copy', style=wx.BU_EXACTFIT)
        #self.btn_pastereplace = wx.Button(self, -1, 'paste&&replace', style=wx.BU_EXACTFIT)
        #self.btn_paste = wx.Button(self, -1, 'paste', style=wx.BU_EXACTFIT)
        #self.btn_unselect = wx.Button(self, -1, 'unselect all', style=wx.BU_EXACTFIT)
        #self.btn_save = wx.Button(self, -1, '&save', style=wx.BU_EXACTFIT)
        #self.btn_load = wx.Button(self, -1, '&load', style=wx.BU_EXACTFIT)
        #self.btn_close = wx.BitmapButton(self, -1, misc.get_bmp('close.png'), style=wx.BU_EXACTFIT|wx.NO_BORDER)
        
        #self.pan_tools = wx.Panel(self, -1)
        #self.btn_transpose = wx.Button(self.pan_tools, -1, '&transpose', style=wx.BU_EXACTFIT)
        #self.btn_clear = wx.Button(self.pan_tools, -1, 'clear', style=wx.BU_EXACTFIT)
        #self.btn_resize = wx.Button(self.pan_tools, -1, 'resize', style=wx.BU_EXACTFIT)
        #self.txt_resize = wx.TextCtrl(self.pan_tools, -1, '30,5')
        #self.btn_create = wx.Button(self.pan_tools, -1, 'create set', style=wx.BU_EXACTFIT)

        self.grid = Grid(self)
            
        vbox = wx.BoxSizer(wx.VERTICAL)
        #hbox = wx.BoxSizer(wx.HORIZONTAL)
        #hbox.Add(self.btn_load, 0, wx.ALL|wx.EXPAND, 2)
        #hbox.Add(self.btn_save, 0, wx.ALL|wx.EXPAND, 2)
        #hbox.Add(wx.Window(self, -1, size=(20,0)))
        #hbox.Add(self.btn_copy, 0, wx.ALL|wx.EXPAND, 2)
        #hbox.Add(self.btn_paste, 0, wx.ALL|wx.EXPAND, 2)
        #hbox.Add(self.btn_pastereplace, 0, wx.ALL|wx.EXPAND, 2)
        #hbox.Add(self.btn_unselect, 0, wx.ALL|wx.EXPAND, 2)
        #hbox.Add(wx.Window(self, -1, size=(20,0)),1)
        #hbox.Add(self.btn_close , 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL,2)
        #vbox.Add(hbox, 0, wx.EXPAND)

        vbox.Add(self.grid, 1, wx.EXPAND)

        #hbox = wx.BoxSizer(wx.HORIZONTAL)
        #hbox.Add(self.btn_transpose, 0, wx.ALL|wx.EXPAND, 2)
        #hbox.Add(self.btn_clear, 0, wx.ALL|wx.EXPAND, 2)
        #hbox.Add(wx.Window(self.pan_tools, -1, size=(20,0)))
        #hbox.Add(self.btn_resize, 0, wx.ALL|wx.EXPAND, 2)
        #hbox.Add(self.txt_resize, 0, wx.ALL|wx.EXPAND, 2)
        #hbox.Add(wx.Window(self.pan_tools, -1, size=(20,0)))
        #hbox.Add(self.btn_create, 0, wx.ALL|wx.EXPAND, 2)
        #self.pan_tools.SetSizer(hbox)
        #self.pan_tools.Layout()
        
        #vbox.Add(self.pan_tools, 0, wx.EXPAND|wx.TOP, 2)

        self.SetSizer(vbox)

        #if type(self.GetParent()) != wx.Notebook:
        #    self.btn_close.Hide()

        #self.grid.SetMinSize((-1,200))
        #self.GetParent().SetMinSize(vbox.GetMinSize())
        self.Layout()

    def set_name(self, name):
        nb = self.GetParent()
        if type(nb) in [wx.Notebook,fnb.FlatNotebook]:
            for p in range(nb.GetPageCount()):
                if nb.GetPage(p) == self:
                    nb.SetPageText(p, name)
    def get_name(self):
        nb = self.GetParent()
        if type(nb) in [wx.Notebook,fnb.FlatNotebook]:
            for p in range(nb.GetPageCount()):
                if nb.GetPage(p) == self:
                    return nb.GetPageText(p)
    name = property(fset=set_name)
        
    def close(self):
        self.SetEvtHandlerEnabled(False)
        nb = self.GetParent()
        for n in range(nb.GetPageCount()):
            if nb.GetPage(n) == self:
                nb.RemovePage(n) #does not delete the panel
                break

    def show_rename_dialog(self, val):
        dlg = wx.TextEntryDialog(self, 'Enter new label:',
            'Rename label', val)

        if dlg.ShowModal() == wx.ID_OK:
            ret = dlg.GetValue()
        else:
            ret = None

        dlg.Destroy()

        return ret

class Grid(wx.grid.Grid):
    def __init__(self, parent):
        wx.grid.Grid.__init__(self, parent, -1, style=wx.SUNKEN_BORDER)

        self.SetColLabelSize(20)
        self.SetDefaultCellOverflow(False)
        self.SetRowLabelSize(120)
        self.SetRowLabelAlignment(wx.ALIGN_LEFT, wx.ALIGN_CENTER)
        self.SetDefaultColSize(100)
        self.FitInside()

    def paint_row_header(self, rowtoadd):
        w = self.GetGridRowLabelWindow()
        dc = wx.PaintDC(w)
        clientRect = w.GetClientRect()
        font = dc.GetFont()

        totRowSize = -self.GetViewStart()[1]*self.GetScrollPixelsPerUnit()[1]
        l,t,r,b = self.GetClientRect()
        width = self.GetRowLabelSize()
        for row in range(self.GetNumberRows()):
            rowSize = self.GetRowSize(row)
            if totRowSize > -10 and totRowSize < b+10:
                dc.SetTextForeground(wx.BLACK)
                rect = [0,totRowSize,width,rowSize]
                if row == rowtoadd:
                    dc.SetBrush(wx.Brush("RED", wx.SOLID))
                else:
                    dc.SetBrush(wx.Brush("WHEAT", wx.TRANSPARENT))

                dc.DrawRectangle(rect[0], rect[1] - (row<>0 and 1 or 0),
                                 rect[2], rect[3] + (row<>0 and 1 or 0))
                font.SetWeight(wx.BOLD)

                dc.SetFont(font)
                rect[0] += 5
                dc.DrawLabel("%s" % self.GetTable().GetRowLabelValue(row),
                             rect, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_TOP)
            totRowSize += rowSize

class Datagrid(object):
    def __init__(self, show_shell=False):
        app = wx.PySimpleApp(0)
        self.f = wx.Frame(None, -1, 'data grid')
        self.f.Bind(wx.EVT_CLOSE, self.OnClose)
        self.f.Bind(misc.EVT_SHOUT, self.OnMessage)
        p = GridPanel(self.f, show_shell=show_shell)
        self.ctrl = Controller(None,p,Interactor(), 'nn')
        self.locals = DataBridge(self.ctrl)
        self.f.Show()
        app.MainLoop()

    def OnClose(self, evt):
        del self.ctrl
        self.f.Destroy()

    def OnMessage(self, evt):
        print evt.msg
        
    def __getattr__(self, attr):
        try:
            return self.locals[attr]
        except KeyError:
            raise AttributeError, attr

    def __setattr__(self, attr, val):
        if attr == 'data':
            self.__dict__['locals'][attr] = val
        else:
            dict.__setattr__(self, attr, val)
