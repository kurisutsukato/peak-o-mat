import wx
import wx.aui as aui
import numpy as np
from scipy import ndimage, misc
from pubsub import pub
from PIL import Image, ImageDraw

from .. import module
from .. import plotcanvas
from ..spec import Dataset
from .. import misc_ui

def read():
    try:
        data = open('A90_map_pol_0.txt').readlines()
    except IOError:
        x, y = (np.linspace(0, 4, 5), np.linspace(0, 2, 5))
        data = ((10 * np.sin(x) ** 2 + 1 + (10 * np.cos(y)[:, None] ** 2))) * np.random.normal(size=(10))[:, None, None]
        return np.linspace(0, 1, 10), (x, y), data
    else:
        data = [[float(p) for p in q.strip().split('\t')] for q in data]
        wl = np.asarray(data[0])
        data = np.asarray(data[1:])
        pos = data[:, :2].T
        z = data[:, 2:]

        axes = [np.unique(q) for q in pos]
        x, y = [len(q) for q in axes]

        d = len(wl)

        data = z.ravel().reshape((x, y, d)).transpose((2, 0, 1))

        return wl, axes, data

from enum import Enum

class Mode(Enum):
    CROSS = 1
    LINE = 2

class Map(wx.Window):
    def __init__(self, parent):
        super(Map, self).__init__(parent, style=wx.WANTS_CHARS)
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)

        self.axes = [[0, 1], [0, 1]]
        self.line_coords = np.zeros((0, 2), dtype=int)

        self._line_overlay = None
        self._cross = [0, 0]
        self._line = None
        self._mode = Mode.LINE

        self.SetMinSize((140, 50))

        self._buffer = None

    @property
    def imdata(self):
        return self._imdata

    @imdata.setter
    def imdata(self, imdata):
        self._imdata = imdata  # (np.ones(3)[:,None,None]*imdata)
        self._imdata = np.log10(self._imdata)
        self._imdata = (255 * self._imdata / (max(1, self._imdata.max()))).astype('uint8')

    @property
    def axes(self):
        return self._axes

    @axes.setter
    def axes(self, ax):
        self._axes = [np.array(q) for q in ax]

    def _draw_line(self, dc):
        if self._line_overlay is not None:
            img = self._line_overlay.resize(self.canvas_size, Image.NEAREST)
            bmp = wx.Bitmap.FromBufferRGBA(*self.canvas_size, img.tobytes())
            dc.DrawBitmap(bmp, 0, 0)

    def _draw_crosshair(self, dc):
        x, y = self._cross

        w, h = self.canvas_size
        dx = np.diff(self.x_scaled)[x]
        dy = np.diff(self.y_scaled)[y]

        dc.SetBrush(wx.Brush(wx.Colour(255, 255, 0, 120)))
        dc.SetPen(wx.Pen(wx.Colour(255, 255, 0, 120), 1))
        dc.DrawRectangle(self.x_scaled[x], 0, dx, self.y_scaled[y])
        dc.DrawRectangle(self.x_scaled[x], self.y_scaled[y] + dy, dx, h - (self.y_scaled[y] + dy))
        dc.DrawRectangle(0, self.y_scaled[y], self.x_scaled[x], dy)
        dc.DrawRectangle(self.x_scaled[x] + dx, self.y_scaled[y], w - (self.x_scaled[x] + dx), dy)

        ylab = str(self._axes[0][y])
        xlab = str(self._axes[1][x])

        label = '{}/{}'.format(xlab, ylab)
        extx, exty = dc.GetTextExtent(label)

        if self.x_scaled[x] > w / 2.0:
            tx = self.x_scaled[x] - extx - 5
        else:
            tx = self.x_scaled[x] + dx + 5
        if self.y_scaled[y] > h / 2.0:
            ty = self.y_scaled[y] - exty - 5
        else:
            ty = self.y_scaled[y] + dy + 5

        dc.SetTextForeground(wx.Colour(255, 255, 0, 255))
        dc.DrawText(label, tx, ty)

    def move_crosshair(self, dx, dy):
        rows, cols = self._imdata.shape

        x, y = self._cross
        x += dx
        x %= cols
        y += dy
        y %= rows
        self._cross = [x, y]
        self.Redraw()

    def update_crosshair(self, x, y):
        self._cross = [x, y]
        self.Redraw()

    def update_line(self, start, end, additive=False):
        line = np.asarray([start, end])

        if not additive or self._line_overlay is None:
            img = Image.fromarray(np.zeros(self._imdata.shape, dtype='uint8'), mode='L').convert('RGBA')
            data = np.asarray(img).copy()
            data[:, :, 3] = 0
            img = Image.fromarray(data)
        else:
            img = self._line_overlay
        draw = ImageDraw.Draw(img)

        draw.line(np.ravel(line).tolist(), fill=(255,0,255,100), width=1)
        self._line_overlay = img

        self.line_coords = np.vstack(np.where(np.asarray(img)[:,:,:3].sum(axis=2) > 0)).T
        self.Redraw()

    def OnPaint(self, evt):
        dc = wx.BufferedPaintDC(self)
        dc.DrawBitmap(self._buffer, 0, 0)
        if 'wxMac' not in wx.PlatformInfo:
            dc = wx.GCDC(dc)
        self._draw_crosshair(dc)
        self._draw_line(dc)

    def OnSize(self, evt):
        w, h = self.GetClientSize()
        w = max(1, w)
        h = max(1, h)
        self._buffer = wx.Bitmap(w, h)
        self.Redraw(True)
        self.Refresh()

    def Redraw(self, full=False):
        if full:
            success = self.Draw()
            #dc = wx.BufferedDC(wx.ClientDC(self))
            dc = wx.ClientDC(self)
        else:
            dc = wx.BufferedDC(wx.ClientDC(self))
            dc.DrawBitmap(self._buffer, 0, 0)

        if not full or success:
            if 'wxMac' not in wx.PlatformInfo:
                dc = wx.GCDC(dc)
            self._draw_crosshair(dc)
            self._draw_line(dc)

    def Draw(self):
        w, h = self.GetClientSize()
        if w < 1 or h < 1:
            return

        if self._buffer is not None:
            if not hasattr(self, '_imdata'):
                self._imdata = np.ones((3, 1, 1), 'uint8') * 255

            dc = wx.BufferedDC(wx.ClientDC(self), self._buffer)
            if 'wxMac' not in wx.PlatformInfo:
                dc = wx.GCDC(dc)

            y, x = self._imdata.shape

            tw, th = dc.GetTextExtent('888')

            self.canvas_size = cw, ch = int(float(h) * x / y) - tw, h - th
            self.SetMinSize((h * x / y, h))

            if cw > 1 and ch > 1:
                dummy = np.zeros((y * x), dtype='uint8')
                dummy[::2] = 1
                dummy.shape = (y, x)

                img = Image.fromarray(self._imdata, mode='L').resize((cw, ch), Image.NEAREST)
                resized = np.array(img.convert('RGB'))

                self._image = wx.ImageFromBuffer(cw, ch, resized)

                dummy = np.array(Image.fromarray(dummy, mode='L').resize((cw, ch), Image.NEAREST))

                self.x_scaled = np.hstack(([0], np.where(dummy[0, :-1] != dummy[0, 1:])[0] + 1, [cw]))
                self.y_scaled = np.hstack(([0], np.where(dummy[:-1, 0] != dummy[1:, 0])[0] + 1, [ch]))

                br = wx.Brush(wx.Colour(200, 200, 200), wx.SOLID)
                dc.SetBackground(br)
                dc.SetBackgroundMode(wx.TRANSPARENT)
                dc.SetTextForeground((200, 0, 0, 200))
                dc.Clear()
                dc.DrawBitmap(wx.Bitmap(self._image), 0, 0)
                w, h = self.canvas_size
                lab = '{:.0f}'.format(self.axes[1][0])
                dc.DrawText(lab, 1, h)
                lab = '{:.0f}'.format(self.axes[1][-1])
                dc.DrawText(lab, w - dc.GetTextExtent(lab)[0], h + 1)
                lab = '{:.0f}'.format(self.axes[0][0])
                dc.DrawText(lab, w, 0)
                lab = '{:.0f}'.format(self.axes[0][-1])
                dc.DrawText(lab, w, h - dc.GetTextExtent(lab)[1])
                return True
        return False

class Interactor:
    def install(self, controller, view):
        self.controller = controller
        self.view = view

        self.view.map.Bind(wx.EVT_MOTION, self.OnMapMotion)
        self.view.map.Bind(wx.EVT_LEFT_UP, self.OnMapLeftUp)
        self.view.map.Bind(wx.EVT_LEFT_DOWN, self.OnMapLeftDown)
        self.view.map.Bind(wx.EVT_KEY_DOWN, self.OnKey)
        self.view.map.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        self.view.map.Bind(wx.EVT_ENTER_WINDOW, self.OnEnter)

        self.view.Bind(wx.EVT_BUTTON, self.OnTransfer)

        pub.subscribe(self.pubOnWlSelect, (self.view.instid, 'plot', 'xmarker'))

    def OnTransfer(self, evt):
        coords = self.view.map.line_coords
        specs = []
        for y, x in coords:
            specs.append(Dataset(self.controller.wl, self.controller.data[:, y, x], 'x{}-y{}'.format(x, y)))
        pub.sendMessage((self.controller.instid, 'set', 'add'), spec=specs)

    def OnEnter(self, evt):
        self.view.SetFocusIgnoringChildren()

    def OnKeyUp(self, evt):
        if evt.GetKeyCode() == wx.WXK_SHIFT:
            self.controller.update_plot(self.view.map.line_coords)

    def OnKey(self, evt):
        keycode = evt.GetKeyCode()
        map = {wx.WXK_RIGHT: (1, 0), wx.WXK_LEFT: (-1, 0),
               wx.WXK_UP: (0, -1), wx.WXK_DOWN: (0, 1)}
        if keycode in [wx.WXK_LEFT, wx.WXK_RIGHT, wx.WXK_UP, wx.WXK_DOWN]:
            idx = map[keycode]
            self.view.map.move_crosshair(*idx)
            self.controller.update_plot(*self.view.map._cross)
        elif keycode == wx.WXK_RETURN:
            self.OnTransfer(None)

    def pubOnPageChanged(self, msg):
        if msg == self.view:
            self.view.SetFocus()

    def pubOnWlSelect(self, wl):
        self.controller.update_map(wl)

    def world2map(self, pos):
        x, y = pos
        w, h = self.view.map.canvas_size
        if not (x < w and y < h):
            raise ValueError('out of world')
        ix = int(float(x) / w * len(self.view.map.axes[1]))
        iy = int(float(y) / h * len(self.view.map.axes[0]))
        return ix, iy

    def OnMapMotion(self, evt):
        try:
            ix, iy = self.world2map(evt.Position)
        except ValueError:
            return

        self.view.map.update_crosshair(ix, iy)

        if evt.ShiftDown():
            self.controller.update_plot(np.vstack((self.view.map.line_coords, [iy, ix])), highlight_last=True)
        if evt.Dragging():
            if self.view.map._mode == Mode.LINE:
                self.view.map.update_line(self._startpos, [ix, iy])

    def OnMapLeftUp(self, evt):
        if self.view.map._mode == Mode.LINE:
            self.controller.update_plot(self.view.map.line_coords)

    def OnMapLeftDown(self, evt):
        self.view.map.SetFocus()
        try:
            ix, iy = self.world2map(evt.Position)
        except ValueError:
            return
        self.view.map.update_crosshair(ix, iy)
        if self.view.map._mode == Mode.CROSS:
            self.controller.update_plot(ix, iy)
        elif self.view.map._mode == Mode.LINE:
            self.view.map.update_line([ix, iy], [ix, iy], evt.ShiftDown())
            self._startpos = [ix, iy]

class Module(module.BaseModule):
    title = 'Map scan browser'

    def __init__(self, *args):
        super(Module, self).__init__(*args)
        self.init()

        self.parent_view._mgr.AddPane(self.view, aui.AuiPaneInfo().
                                      Float().Dockable(False).Hide().MinSize(400, 200).
                                      Caption(self.title).Name(self.title))
        self.parent_view._mgr.Update()
        self.parent_controller.view.menu_factory.add_module(self.parent_controller.view.menubar, self.title)

    def init(self):
        self.view = ControlPanel(self.parent_view)
        super(Module, self).init()

        Interactor().install(self, self.view)

        self.read_data()
        self.init_map()

        wx.CallAfter(self.update_plot, *self.view.map._cross)

    def read_data(self):
        self.wl, self.axes, self.data = read()
        sort = np.argsort(self.wl)
        self.wl = self.wl.take(sort)
        self.data = self.data.take(sort, axis=0)

    def init_map(self):
        self.view.map.axes = self.axes
        self.view.map.imdata = self.data.sum(axis=0)

        self.view.map.OnSize(None)

    def update_map(self, wlrange):
        d, y, x = self.data.shape
        idx = self.wl.searchsorted(wlrange)
        if len(idx) == 1 or idx[0] == idx[1]:
            idx = idx[0]
            idx = min(max(idx, 0), d - 1)
            self.view.map.imdata = self.data[idx, :, :]
        else:
            idx.sort()
            idx = [min(max(q, 0), d - 1) for q in idx]
            self.view.map.imdata = self.data[slice(*idx)].sum(axis=0)

        self.view.map.Redraw(True)

    def update_plot(self, ix, iy=None, highlight_last=False):
        if iy is not None:
            ix = [(iy,ix)]

        self.view.btn_transfer.Enable()
        lines = []

        for n,(y,x) in enumerate(ix):
            #xlab = str(self.view.map._axes[1][x])
            #ylab = str(self.view.map._axes[0][y])
            c = wx.Colour(160,160,160) if n != len(ix)-1 and highlight_last else 'black'
            if highlight_last and n != len(ix)-1:
                wl = self.wl[::10]
                data = self.data[::10, y, x]
            else:
                wl = self.wl
                data = self.data[:, y, x]
            line = plotcanvas.Line(np.transpose([wl, data]), colour=c, width=1)
            lines.append(line)

        pg = plotcanvas.Graphics(lines)
        self.view.plot.setLogScale([False,True])
        self.view.plot.Draw(pg)

class ControlPanel(misc_ui.WithMessage, wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        misc_ui.WithMessage.__init__(self)

        self.setup_controls()
        self.layout()

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
        box.Add(hbox, 1, wx.EXPAND | wx.ALL, 5)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(wx.Window(self), 1)
        hbox.Add(self.btn_transfer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        box.Add(hbox, 0, wx.EXPAND | wx.BOTTOM, 5)
        self.SetSizer(box)
