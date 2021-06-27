
#TODO: rausschmeissen, ist jetzt map_mod

import wx
import numpy as np
from scipy import ndimage, misc
from pubsub import pub

from . import plotcanvas

def read():
    data = open('../A90_map_pol_1.txt').readlines()
    data = [[float(p) for p in q.strip().split('\t')] for q in data]
    wl = np.asarray(data[0])
    data = np.asarray(data[1:])
    pos = data[:,:2].T
    z = data[:,2:]

    axes = [np.unique(q) for q in pos]
    x,y = [len(q) for q in axes]

    d = len(wl)

    data = z.ravel().reshape((x,y,d)).transpose((2,0,1))

    return wl,axes,data

class Map(wx.Window):
    def __init__(self, parent):
        super(Map,self).__init__(parent)

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)

        self.axes = [[0,1],[0,1]]

        self._cross = None

        self.SetMinSize((140,50))

        self.overlay = wx.Overlay()

    @property
    def imdata(self):
        return self._imdata
    @imdata.setter
    def imdata(self, imdata):
        self._imdata = np.array([imdata]*3)
        #self._imdata = np.log10(self._imdata)
        self._imdata = 255*self._imdata/self._imdata.max().astype('uint8')

    @property
    def axes(self):
        return self._axes
    @axes.setter
    def axes(self, ax):
        self._axes = [np.array(q) for q in ax]

    def _move_crosshair(self, x=0, y=0):
        d,rows,cols = self._imdata.shape
        self._cross[0] += x
        self._cross[0] %= cols
        self._cross[1] += y
        self._cross[1] %= rows

    def _draw_crosshair(self, pt=None):
        if pt is not None:
            x, y = pt
            self._cross = pt
        elif self._cross is not None:
            x, y = self._cross
        else:
            return

        w, h = self.canvas_size

        dx = np.diff(self.x_scaled)[x]
        dy = np.diff(self.y_scaled)[y]

        dc = wx.BufferedDC(wx.ClientDC(self), self._buffer)
        odc = wx.DCOverlay(self.overlay, dc)
        odc.Clear()
        dc = wx.GCDC(dc)

        dc.SetBrush(wx.Brush(wx.Colour(255,255,0,120)))
        dc.SetPen(wx.Pen(wx.Colour(255,255,0,120), 1))
        dc.DrawRectangle(self.x_scaled[x],0,dx,self.y_scaled[y])
        dc.DrawRectangle(self.x_scaled[x],self.y_scaled[y]+dy,dx,h-(self.y_scaled[y]+dy))
        dc.DrawRectangle(0,self.y_scaled[y],self.x_scaled[x],dy)
        dc.DrawRectangle(self.x_scaled[x]+dx,self.y_scaled[y],w-(self.x_scaled[x]+dx),dy)

        ylab = str(self._axes[0][y])
        xlab = str(self._axes[1][x])

        label = '{}/{}'.format(xlab,ylab)
        extx, exty = dc.GetTextExtent(label)

        if self.x_scaled[x] > w/2.0:
            tx = self.x_scaled[x]-extx-5
        else:
            tx = self.x_scaled[x]+dx+5
        if self.y_scaled[y] > h/2.0:
            ty = self.y_scaled[y]-exty-5
        else:
            ty = self.y_scaled[y]+dy+5

        dc.SetTextForeground(wx.Colour(255,255,0,255))
        dc.DrawText(label,tx,ty)

        del odc

    def OnPaint(self, event):
        if hasattr(self, '_buffer'):
            dc = wx.BufferedPaintDC(self, self._buffer)

    def OnSize(self, evt):
        self._buffer = wx.EmptyBitmap(*self.GetClientSize())
        self.Draw()
        self._draw_crosshair()

    def Draw(self):
        self.overlay.Reset()
        if not hasattr(self, '_imdata'):
            self._imdata = np.ones((3,1,1),'uint8')*255

        dc = wx.BufferedDC(wx.ClientDC(self), self._buffer)
        if 'wxMac' not in wx.PlatformInfo:
            dc = wx.GCDC(dc)

        w, h = self.GetClientSize()
        d,y,x = self._imdata.shape

        tw, th = dc.GetTextExtent('888')

        #self.canvas_size = cw, ch  = int(min(w,float(h)*x/y)-tw),int(min(float(w)/x*y,h)-th)
        self.canvas_size = cw, ch = int(h*float(x)/y)-tw,int(h-th)
        self.SetMinSize((h*x/y,h))

        dummy = np.zeros((y*x))
        dummy.shape = (y,x)
        dummy[::2,1::2] = 1
        dummy[1::2,::2] = 1
        dummy = np.array((dummy,dummy,dummy))

        #dummy = misc.imresize(dummy, (ch, cw), 'nearest')
        dummy = np.ascontiguousarray(ndimage.interpolation.zoom(dummy,[1,ch/y,cw/x],order=0,mode='nearest').transpose((1,2,0)), dtype='uint8')
        self.x_scaled = np.hstack(([0],np.where(dummy[0,:-1,0] != dummy[0,1:,0])[0]+1,[cw]))
        self.y_scaled = np.hstack(([0],np.where(dummy[:-1,0,0] != dummy[1:,0,0])[0]+1,[ch]))
        print(self.x_scaled)

        resized = misc.imresize(self.imdata, (ch, cw), 'nearest')
        #resized = np.ascontiguousarray(ndimage.interpolation.zoom(self.imdata,[1,ch/y,cw/x],order=0,mode='nearest').transpose((1,2,0)))
        resized -= resized.min()
        resized = np.asarray(resized/resized.max()*255,dtype='uint8')
        self._image = wx.ImageFromBuffer(cw, ch, resized)
        self._image.SaveFile('resize.png',wx.BITMAP_TYPE_PNG)
        #self.x_scaled = np.hstack(([0],np.where(resized[0,:-1,0] != resized[0,1:,0])[0]+1,[cw]))
        #self.y_scaled = np.hstack(([0],np.where(resized[:-1,0,0] != resized[1:,0,0])[0]+1,[ch]))

        br = wx.Brush(wx.Colour(200,200,200), wx.SOLID)
        dc.SetBackground(br)
        dc.SetBackgroundMode(wx.TRANSPARENT)
        dc.SetTextForeground((200,0,0,200))
        dc.Clear()
        dc.DrawBitmap(wx.BitmapFromImage(self._image), 0, 0)
        w,h = self.canvas_size
        lab = '{:.0f}'.format(self.axes[1][0])
        dc.DrawText(lab,1,h)
        lab = '{:.0f}'.format(self.axes[1][-1])
        dc.DrawText(lab,w-dc.GetTextExtent(lab)[0],h+1)
        lab = '{:.0f}'.format(self.axes[0][0])
        dc.DrawText(lab,w,0)
        lab = '{:.0f}'.format(self.axes[0][-1])
        dc.DrawText(lab,w,h-dc.GetTextExtent(lab)[1])

class Interactor:
    def Install(self, controller, view):
        self.controller = controller
        self.view = view

        self.view.map.Bind(wx.EVT_MOTION, self.OnMapLeftDown)
        self.view.map.Bind(wx.EVT_LEFT_DOWN, self.OnMapLeftDown)
        self.view.map.Bind(wx.EVT_KEY_DOWN, self.OnKey)
        self.view.plot.canvas.Bind(wx.EVT_KEY_DOWN, self.OnKey)
        pub.subscribe(self.OnWlSelect, ('plot','xmarker'))

    def OnKey(self, evt):
        keycode = evt.GetKeyCode()
        map = {wx.WXK_RIGHT:(1,0),wx.WXK_LEFT:(-1,0),
               wx.WXK_UP:(0,-1),wx.WXK_DOWN:(0,1)}
        if keycode in [wx.WXK_LEFT, wx.WXK_RIGHT, wx.WXK_UP, wx.WXK_DOWN]:
            idx = map[keycode]
            self.view.map.move_crosshair(*idx)
            self.controller.update_plot(*self.view.map._cross)
            self.view.map._draw_crosshair()

    def OnWlSelect(self, wl):
        self.controller.update_map(wl)

    def OnMapLeftDown(self, evt):
        w,h = self.view.map.canvas_size
        x, y = evt.GetX(), evt.GetY()
        if evt.LeftIsDown() and x < w and y < h:
            idx_x = int(float(x)/w*len(self.view.map.axes[1]))
            idx_y = int(float(y)/h*len(self.view.map.axes[0]))
            self.controller.update_plot(idx_x, idx_y)
            self.view.map._draw_crosshair([idx_x, idx_y])

class Controller:
    def __init__(self, view, interactor):
        self.view = view
        interactor.Install(self, view)

        self.read_data()
        self.init_map()

    def read_data(self):

        self.wl,self.axes,self.data = read()
        sort = np.argsort(self.wl)
        self.wl = self.wl.take(sort)
        self.data = self.data.take(sort, axis=0)

    def init_map(self):
        self.view.map.axes = self.axes
        self.view.map.imdata = self.data[0]

        self.view.map.Draw()

    def update_map(self, wlrange):
        d,y,x = self.data.shape
        idx = self.wl.searchsorted(wlrange)
        if len(idx) == 1 or idx[0] == idx[1]:
            idx = idx[0]
            idx = min(max(idx,0),d-1)
            self.view.map.imdata = self.data[idx]
        else:
            idx.sort()
            idx = [min(max(q,0),d-1) for q in idx]
            self.view.map.imdata = self.data[slice(*idx)].sum(axis=0)
        self.view.lab_wl.SetLabel('{:s}'.format(str(wlrange)))

        self.view.map.Draw()
        self.view.map._draw_crosshair()

    def update_plot(self, x, y):
        self.view.map.idx_x = x
        self.view.map.idx_y = y
        line1 = plotcanvas.Line(np.transpose([self.wl, self.data[:,y,x]]), colour='black', width=1)
        pg = plotcanvas.Graphics([line1])
        #self.view.plot.setLogScale([False,True])
        #self.view.plot.Draw(pg, None, (self.data[:,y,x].min(),self.data.max()))
        self.view.plot.Draw(pg)

    def run(self):
        wx.GetApp().MainLoop()

class ControlPanel(wx.Panel):
    def __init__(self, parent):
        super(ControlPanel, self).__init__(parent)

        self.setup_controls()
        self.layout()

    def setup_controls(self):
        self.map = Map(self)
        self.lab_wl = wx.StaticText(self, label='')

        self.plot = plotcanvas.Canvas(self)
        self.plot.state.set('xmarker')

    def layout(self):
        box = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.map, 0, wx.EXPAND)
        hbox.Add(self.plot, 1, wx.EXPAND)
        box.Add(hbox, 1, wx.EXPAND|wx.ALL, 10)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.lab_wl, 0, wx.EXPAND|wx.LEFT, 5)
        box.Add(hbox,0, wx.EXPAND|wx.ALL, 10)
        self.SetSizer(box)


def run():
    app = wx.App(None)
    f = wx.Frame(None)
    f.panel = ControlPanel(f)
    f.Show()
    c = Controller(f.panel, Interactor())
    c.run()

if __name__ == '__main__':
    wl,pos,val = read()

    x = np.unique(pos[0])
    y = np.unique(pos[1])
    val = val.reshape((len(wl),len(x),len(y)))


    #p = Map(f)
    #p.imdata = val[:,10].reshape(len(x),len(y))

    run()
