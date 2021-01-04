import wx
import wx.aui as aui
import numpy as np
from scipy import ndimage, misc
from pubsub import pub
from PIL import Image

from .. import module
from .. import plotcanvas
from ..spec import Spec

def read():
    try:
        data = open('A90_map_pol_0.txt').readlines()
    except IOError:
        x,y = (np.linspace(0,4,5),np.linspace(0,2,5))
        data = ((10*np.sin(x)**2+1+(10*np.cos(y)[:,None]**2)))*np.random.normal(size=(10))[:,None,None]
        return np.linspace(0,1,10),(x,y),data
    else:
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
        super(Map,self).__init__(parent, style=wx.WANTS_CHARS)

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)


        self.axes = [[0,1],[0,1]]

        self._cross = [0,0]

        self.SetMinSize((140,50))

        self.overlay = wx.Overlay()

        self._buffer = None

    @property
    def imdata(self):
        return self._imdata
    @imdata.setter
    def imdata(self, imdata):
        self._imdata = imdata #(np.ones(3)[:,None,None]*imdata)
        self._imdata = np.log10(self._imdata)
        self._imdata = (255*self._imdata/(max(1,self._imdata.max()))).astype('uint8')

    @property
    def axes(self):
        return self._axes
    @axes.setter
    def axes(self, ax):
        self._axes = [np.array(q) for q in ax]

    def _move_crosshair(self, x=0, y=0):
        rows,cols = self._imdata.shape
        self._cross[0] += x
        self._cross[0] %= cols
        self._cross[1] += y
        self._cross[1] %= rows

    def _draw_crosshair(self, pt=None):
        print('draw crosshair',pt,self._cross)
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

        #dc = wx.BufferedDC(wx.ClientDC(self), self._buffer)
        dc = wx.ClientDC(self)
        odc = wx.DCOverlay(self.overlay, dc)
        odc.Clear()
        if 'wxMac' not in wx.PlatformInfo:
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
        #del dc

    def OnPaint(self, event):
        print('on paint')
        if hasattr(self, '_buffer') and self._buffer is not None:
            dc = wx.BufferedPaintDC(self, self._buffer)

    def OnSize(self, evt):
        print('on size')
        w,h = self.GetClientSize()
        w = max(1,w)
        h = max(1,h)
        self._buffer = wx.Bitmap(w,h)
        self.Draw()
        self.Refresh()
        wx.CallAfter(self._draw_crosshair)

    def Draw(self):
        print('draw')
        w, h = self.GetClientSize()
        if w < 1 and h < 1:
            return
        if self._buffer is not None:
            self.overlay.Reset()
            if not hasattr(self, '_imdata'):
                self._imdata = np.ones((3,1,1),'uint8')*255

            dc = wx.BufferedDC(wx.ClientDC(self), self._buffer)
            #dc = wx.ClientDC(self)
            if 'wxMac' not in wx.PlatformInfo:
                dc = wx.GCDC(dc)

            y,x = self._imdata.shape

            tw, th = dc.GetTextExtent('888')

            #self.canvas_size = cw, ch  = int(min(w,float(h)*x/y)-tw),int(min(float(w)/x*y,h)-th)
            self.canvas_size = cw, ch = int(float(h)*x/y)-tw,h-th
            self.SetMinSize((h*x/y,h))

            #self.x_scaled = (np.arange(x+1)*cw/(x)).astype('int')
            #self.y_scaled = (np.arange(y+1)*ch/(y)).astype('int')

            dummy = np.zeros((y*x), dtype='uint8')
            dummy[::2] = 1
            dummy.shape = (y,x)
            #dummy = np.array((dummy,dummy,dummy)).astype('uint8')

            if ch > 0 and cw > 0:
                img = Image.fromarray(self._imdata, mode='L').resize((cw, ch), Image.NEAREST)
                resized = np.array(img.convert('RGB'))

                self._image = wx.ImageFromBuffer(cw, ch, resized)

                dummy = np.array(Image.fromarray(dummy, mode='L').resize((cw, ch), Image.NEAREST))

                self.x_scaled = np.hstack(([0],np.where(dummy[0,:-1] != dummy[0,1:])[0]+1,[cw]))
                self.y_scaled = np.hstack(([0],np.where(dummy[:-1,0] != dummy[1:,0])[0]+1,[ch]))

                br = wx.Brush(wx.Colour(200,200,200), wx.SOLID)
                dc.SetBackground(br)
                dc.SetBackgroundMode(wx.TRANSPARENT)
                dc.SetTextForeground((200,0,0,200))
                dc.Clear()
                dc.DrawBitmap(wx.Bitmap(self._image), 0, 0)
                w,h = self.canvas_size
                lab = '{:.0f}'.format(self.axes[1][0])
                dc.DrawText(lab,1,h)
                lab = '{:.0f}'.format(self.axes[1][-1])
                dc.DrawText(lab,w-dc.GetTextExtent(lab)[0],h+1)
                lab = '{:.0f}'.format(self.axes[0][0])
                dc.DrawText(lab,w,0)
                lab = '{:.0f}'.format(self.axes[0][-1])
                dc.DrawText(lab,w,h-dc.GetTextExtent(lab)[1])
                #self.Refresh()
                #self.Update()
                del dc

class Interactor:
    def Install(self, controller, view):
        self.controller = controller
        self.view = view

        self.view.map.Bind(wx.EVT_MOTION, self.OnMapLeftDown)
        self.view.map.Bind(wx.EVT_LEFT_DOWN, self.OnMapLeftDown)
        self.view.plot.Bind(wx.EVT_LEFT_DOWN, self.OnMapLeftDown)
        self.view.map.Bind(wx.EVT_KEY_DOWN, self.OnKey)
        #self.view.Bind(wx.EVT_KEY_DOWN, self.OnKey)
        self.view.Bind(wx.EVT_BUTTON, self.OnTransfer)
        
        pub.subscribe(self.pubOnWlSelect, ('plot','xmarker'))
        pub.subscribe(self.pubOnPageChanged, ('notebook','pagechanged'))

    def OnTransfer(self, evt):
        pub.sendMessage('set.add', spec=self.controller._spec)

    def OnKey(self, evt):
        keycode = evt.GetKeyCode()
        map = {wx.WXK_RIGHT:(1,0),wx.WXK_LEFT:(-1,0),
               wx.WXK_UP:(0,-1),wx.WXK_DOWN:(0,1)}
        if keycode in [wx.WXK_LEFT, wx.WXK_RIGHT, wx.WXK_UP, wx.WXK_DOWN]:
            idx = map[keycode]
            self.view.map._move_crosshair(*idx)
            self.controller.update_plot(*self.view.map._cross)
            self.view.map._draw_crosshair()
        elif keycode == wx.WXK_RETURN:
            self.OnTransfer(None)

    def pubOnPageChanged(self, msg):
        if msg == self.view:
            self.view.SetFocus()

    def pubOnWlSelect(self, wl):
        self.controller.update_map(wl)

    def OnMapLeftDown(self, evt):
        self.view.map.SetFocus()
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
        self.view.map.imdata = self.data.sum(axis=0)

        self.view.map.OnSize(None)

    def update_map(self, wlrange):
        d,y,x = self.data.shape
        idx = self.wl.searchsorted(wlrange)
        if len(idx) == 1 or idx[0] == idx[1]:
            idx = idx[0]
            idx = min(max(idx,0),d-1)
            self.view.map.imdata = self.data[idx,:,:]
        else:
            idx.sort()
            idx = [min(max(q,0),d-1) for q in idx]
            self.view.map.imdata = self.data[slice(*idx)].sum(axis=0)

        self.view.map.Draw()

    def update_plot(self, x, y):
        self.view.map.idx_x = x
        self.view.map.idx_y = y
        xlab = str(self.view.map._axes[1][x])
        ylab = str(self.view.map._axes[0][y])
        self._spec = Spec(self.wl, self.data[:,y,x],'X{}/Y{}'.format(xlab,ylab))
        self.view.btn_transfer.Enable()
        line1 = plotcanvas.Line(np.transpose([self.wl, self.data[:,y,x]]), colour='black', width=1)
        pg = plotcanvas.Graphics([line1])
        #self.view.plot.setLogScale([False,True])
        self.view.plot.Draw(pg)

class Module(module.BaseModule):
    title = 'Map scan browser'

    def __init__(self, *args):
        super(Module, self).__init__(*args)
        assert self.parent_view is not None
        self.view = Controller(ControlPanel(self.parent_view),Interactor()).view
        self.parent_view._mgr.AddPane(self.view, aui.AuiPaneInfo().
                                      Float().Dockable(True).Hide().
                                      Caption(self.title).Name(self.title))
        self.parent_view._mgr.Update()
        self.parent_controller.view.menu_factory.add_module(self.parent_controller.view.menubar, self.title)

class ControlPanel(wx.Panel):
    def __init__(self, parent):
        super(ControlPanel, self).__init__(parent)

        self.setup_controls()
        self.layout()

        #parent.AddPage(self, 'Map scan browser', select=False)

    def setup_controls(self):
        self.map = Map(self)

        self.plot = plotcanvas.Canvas(self)
        self.plot.state.set('xmarker')
        self.plot.SetYSpec('min')
        self.plot.SetXSpec('min')
        self.btn_transfer = wx.Button(self, label='Transfer')
        self.btn_transfer.Disable()

    def layout(self):
        box = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.map, 0, wx.EXPAND)
        hbox.Add(self.plot, 1, wx.EXPAND)
        box.Add(hbox, 1, wx.EXPAND|wx.ALL,5)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(wx.Window(self), 1)
        hbox.Add(self.btn_transfer, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 5)
        box.Add(hbox,0, wx.EXPAND|wx.BOTTOM, 5)
        self.SetSizer(box)


        
