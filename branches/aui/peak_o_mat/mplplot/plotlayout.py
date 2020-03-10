__author__ = 'kristukat'

import numpy as np
import wx
from wx.lib import newevent
from wx.lib.floatcanvas import FloatCanvas
from functools import reduce

SelectEvent, EVT_RECT_SELECT = newevent.NewEvent()
ReorderEvent, EVT_RECT_REORDER = newevent.NewEvent()

class Map(list):
    def __getitem__(self, item):
        if type(item) == tuple:
            for k in self:
                if k.gridpos == item:
                    return k
            raise IndexError(item)
        else:
            return super(Map, self).__getitem__(item)

class PlotOrderPanel(wx.Panel):
    def __init__(self, parent, **kwargs):
        wx.Panel.__init__(self, parent, **kwargs)

        self.Canvas = FloatCanvas.FloatCanvas(self, BackgroundColor = "LIGHT BLUE")
        self.Canvas.InitAll()

        MainSizer = wx.BoxSizer(wx.VERTICAL)
        MainSizer.Add(self.Canvas, 4, wx.EXPAND)
        self.SetSizer(MainSizer)

        self.Bind(wx.EVT_SIZE, self.OnSize)

    def OnSize(self, evt):
        evt.Skip()
        self.Canvas.ZoomToBB()

    def Log(self, text):
        print(text)

    def OnLeftUp(self, event):
        if self.moving is not None:
            frm = self.moving
            self.moving.PutInBackground()
            self.moving.Text.PutInBackground()
            self.moving.SetFillColor('White')
            self.moving = None
            if self.target is not None:
                to = self.target
                self.target.SetFillColor('White')
                self.Canvas.Draw(Force=True)
                self.target = None
                self.reorder(frm, to)
            self.redraw_rects()

    def add_rect(self, row, col):
        xy = np.asarray([col,row])*[1,-1]
        rect = self.Canvas.AddRectangle(xy, (0.8,0.8), LineWidth = 1, FillColor = 'White')
        rect.Name = ''
        rect.gridpos = (row,col)
        self.__rects.append(rect)

        t = self.Canvas.AddText(rect.Name, xy+[0.3,0.4], Size = 9, Position = 'cc')
        rect.Text = t
        rect.Bind(FloatCanvas.EVT_FC_LEFT_DOWN, self.RectGotHitLeft)
        rect.Bind(FloatCanvas.EVT_FC_ENTER_OBJECT, self.RectMouseOver)
        rect.Bind(FloatCanvas.EVT_FC_LEAVE_OBJECT, self.RectMouseLeave)

    def reorder(self, frm, to):
        to.gridpos, frm.gridpos = frm.gridpos, to.gridpos
        wx.PostEvent(self, ReorderEvent(swap=(frm.gridpos, to.gridpos)))

    def redraw_rects(self, removed=[]):
        for r in removed:
            self.Canvas.RemoveObject(r.Text)
            self.Canvas.RemoveObject(r)

        for r in self.__rects:
            xy = np.asarray(r.gridpos[::-1])*[1,-1]
            r.SetPoint(xy)
            r.Text.SetText(r.Name)
            r.Text.SetPoint(xy+[0.3,0.4])
        self.Canvas.Draw(Force=True)

    @property
    def shape(self):
        return self.__shape
    @shape.setter
    def shape(self, shape):
        if np.asarray(shape).sum() < 2:
            shape = (1,1)
        remove = []
        for r in range(self.__shape[0],shape[0]): # only if new shape has more rows than current
            for c in range(self.__shape[1]):
                self.add_rect(r,c)
            self.__shape = shape[0],self.__shape[1]
        for c in range(self.__shape[1], shape[1]):
            for r in range(self.__shape[0]):
                self.add_rect(r,c)
            self.__shape = self.__shape[0],shape[1]
        for n in range(len(self.__rects)-1,-1,-1):
            if self.__rects[n].gridpos[0] >= shape[0]:
                remove.append(self.__rects.pop(n))
                self.__shape = shape[0], self.__shape[1]
        for n in range(len(self.__rects)-1,-1,-1):
            if self.__rects[n].gridpos[1] >= shape[1]:
                remove.append(self.__rects.pop(n))
                self.__shape = self.__shape[0], shape[1]
        if self.selection in remove:
            self.selection = self.__rects[0]
            self.Focus(self.__rects[0])
            wx.PostEvent(self, SelectEvent(pos=self.selection.gridpos, name=self.selection.Name))
        self.redraw_rects(remove)
        self.Canvas.ZoomToBB()

    @property
    def order(self):
        return [(q.gridpos, q.Name) for q in self.__rects if q.Name != '']

    def set_name(self, name, idx=None):
        if idx is None:
            self.selection.Name = name
            self.selection.Text.SetText(name)
        else:
            self.__rects[idx].Name = name
            self.__rects[idx].Text.SetText(name)
        self.Canvas.Draw(Force=True)

    def Init(self, shape=(1,1)):
        self.moving = None
        self.selection = None
        self.target = None

        self.__shape = shape
        self.__rects = Map()

        Canvas = self.Canvas

        for row,col in np.mgrid[0:shape[1],0:shape[0]].reshape((2,reduce(np.multiply, shape))).T:
            xy = np.asarray([col,row])*[1,-1]
            self.add_rect(row, col)

        self.Canvas.Bind(FloatCanvas.EVT_MOTION, self.OnDrag)
        self.Canvas.Bind(FloatCanvas.EVT_LEFT_UP, self.OnLeftUp)

        Canvas.ZoomToBB()
        self.redraw_rects()

        self.selection = self.__rects[0]

    def update_from_model(self, mpmodel):
        self.shape = mpmodel.shape
        for k,v in mpmodel.items():
            self.__rects[k].Name = v.name

        self.redraw_rects()

        if self.selection is not None:
            self.Focus(self.__rects[0])
            wx.PostEvent(self, SelectEvent(pos=self.selection.gridpos, name=self.selection.Name))

    def OnDrag(self, evt):
        self.curr_coords = evt.Coords
        if self.moving is not None:
            x, y = evt.Coords
            ox, oy = self.moving.XY+self.offset
            self.moving.SetFillColor('Lime Green')
            self.moving.Move((x-ox,y-oy))
            self.moving.Text.Move((x-ox,y-oy))
            self.Canvas.Draw(Force=True)
            wx.GetApp().Yield(True)

    def RectGotHitLeft(self, Object):
        if self.selection == Object:
            return
        self.offset = self.curr_coords-Object.XY
        self.Focus(Object)
        self.selection = Object
        wx.PostEvent(self, SelectEvent(pos=Object.gridpos, name=Object.Name))
        self.moving = Object
        Object.PutInForeground()
        Object.Text.PutInForeground()

    def Focus(self, Object=None):
        if self.selection is not None:
            self.selection.SetLineColor('Black')
            self.selection.SetLineWidth(1)
        if Object is not None:
            Object.SetLineColor('Light Grey')
            Object.SetLineWidth(4)
        self.Canvas.Draw(Force=True)

    def RectMouseOver(self, Object):
        if Object == self.moving:
            return
        if self.moving is not None:
            Object.SetFillColor('Red')
            self.Canvas.Draw(Force=True)
            self.target = Object

    def RectMouseLeave(self, Object):
        if Object == self.moving:
            return
        if self.moving is not None:
            Object.SetFillColor('White')
            self.Canvas.Draw(Force=True)
            self.target = None

class PlotLayout(wx.Panel):
    def __init__(self, parent, **kwargs):
        super(PlotLayout, self).__init__(parent, **kwargs)

        self.setup_controls()
        self.layout()

        #self.pop.Bind(EVT_RECT_SELECT, self.OnSelect)
        self.ch_plot_pri.Bind(wx.EVT_CHOICE, self.OnChoice)
        self.ch_rows.Bind(wx.EVT_CHOICE, self.OnShape)
        self.ch_cols.Bind(wx.EVT_CHOICE, self.OnShape)

        wx.CallAfter(self.pop.Canvas.ZoomToBB)

    def setup_controls(self):
        self.pop = PlotOrderPanel(self, size=(200,150))
        self.pop.Init((1,1))

        self.ch_rows = wx.Choice(self, choices=[str(q) for q in range(1,6)])
        self.ch_rows.SetSelection(0)
        self.ch_cols = wx.Choice(self, choices=[str(q) for q in range(1,6)])
        self.ch_cols.SetSelection(0)

        self.ch_plot_pri = wx.Choice(self, choices=[''], name='pri')
        self.ch_plot_sec = wx.Choice(self, choices=[''], name='sec')

    def layout(self):
        b = wx.BoxSizer(wx.VERTICAL)
        fg = wx.FlexGridSizer(2, 2, 0, 0)
        fg.Add(wx.StaticText(self, label='Rows'), 0, wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 5)
        fg.Add(self.ch_rows, 0, wx.EXPAND|wx.ALIGN_CENTRE_VERTICAL|wx.ALL, 5)
        fg.Add(wx.StaticText(self, label='Columns'), 0, wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 5)
        fg.Add(self.ch_cols, 0, wx.EXPAND|wx.ALIGN_CENTRE_VERTICAL|wx.ALL, 5)
        hb = wx.BoxSizer(wx.HORIZONTAL)
        hb.Add(fg, 0, wx.EXPAND)
        hb.Add(self.pop, 1, wx.EXPAND)
        b.Add(hb, 1, wx.EXPAND)

        hb = wx.BoxSizer(wx.HORIZONTAL)
        hb.Add(wx.StaticText(self, label='Primary axis'), 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)
        hb.Add(self.ch_plot_pri, 1, wx.EXPAND)
        hb.Add(wx.StaticText(self, label='Secondary axis'), 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 10)
        hb.Add(self.ch_plot_sec, 1, wx.LEFT|wx.EXPAND, 5)
        b.Add(hb, 0, wx.EXPAND|wx.ALL, 5)
        self.SetSizer(b)

    def update_from_model(self, mpmodel):
        print('plotlayout: update from model, mpmodel.shape',mpmodel.shape)
        rows,cols = mpmodel.shape

        self.ch_rows.SetSelection(max(0,rows-1))
        self.ch_cols.SetSelection(max(0,cols-1))

        def select(ctrl, uuid):
            if uuid is None:
                ctrl.Selection = 0
            else:
                for n in range(ctrl.Count):
                    if ctrl.GetClientData(n) == uuid:
                        ctrl.Selection = n

        if mpmodel.selected is not None:
            pd = mpmodel.selected

            select(self.ch_plot_pri, pd.plot_ref)
            select(self.ch_plot_sec, pd.plot_ref_secondary)
        else:
            select(self.ch_plot_pri, None)
            select(self.ch_plot_sec, None)

    def set_plot_choices(self, choices, clientdata):
        for ch in self.ch_plot_pri, self.ch_plot_sec:
            ch.Clear()
            for c,d in zip(choices,clientdata):
                ch.Append(c, d)

    @property
    def selection(self):
        sel = self.pop.selection
        return sel.gridpos if sel is not None else None

    def OnShape(self, evt):
        evt.Skip()
        self.pop.shape = self.ch_rows.GetSelection()+1,self.ch_cols.GetSelection()+1

    def OnSelect(self, evt):
        #TODO: remove
        print('plotlayout on select should not be called')
        evt.Skip()
        if evt.name != '':
            self.ch_plot_pri.SetSelection(self.ch_plot_pri.FindString(evt.name))
            self.ch_plot_sec.SetSelection(0)
        else:
            self.ch_plot_pri.SetSelection(0)
            self.ch_plot_sec.SetSelection(0)

    def OnChoice(self, evt):
        evt.Skip()
        sel = evt.GetEventObject().GetSelection()
        name = evt.GetEventObject().GetString(sel)
        self.pop.set_name(name if sel != 0 else '')

if __name__ == "__main__":
    class DemoFrame(wx.Frame):
        def __init__(self):
            super(DemoFrame, self).__init__(None)
            self.panel = PlotLayout(self)

    class DemoApp(wx.App):
        def __init__(self, *args, **kwargs):
            wx.App.__init__(self, *args, **kwargs)

        def OnInit(self):
            frame = DemoFrame()
            frame.Show()
            return True

    app = DemoApp(False)
    app.MainLoop()
