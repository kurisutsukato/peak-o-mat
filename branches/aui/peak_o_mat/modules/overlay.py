import wx
import numpy as np

from PIL import Image

X,Y = 19,27

class Map(wx.Window):
    def __init__(self, parent):
        super(Map, self).__init__(parent, style=wx.WANTS_CHARS)

        self._cross = [2, 4]
        self.overlay = wx.Overlay()
        self._buffer = None

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnMapLeftDown)

        self.SetMinSize((500,200))

    def _draw_crosshair(self, pt=None):
        if pt is not None:
            x, y = pt
            self._cross = pt
        else:
            x, y = self._cross

        print('draw overlay at pos {},{}'.format(x,y))

        w, h = self.canvas_size
        dx = np.diff(self.xsteps)[x]
        dy = np.diff(self.ysteps)[y]

        dc = wx.ClientDC(self)
        odc = wx.DCOverlay(self.overlay, dc)
        odc.Clear()
        if 'wxMac' not in wx.PlatformInfo:
            dc = wx.GCDC(dc)

        dc.SetBrush(wx.Brush(wx.Colour(255, 255, 0, 120)))
        dc.SetPen(wx.Pen(wx.Colour(255, 255, 0, 120), 1))
        dc.DrawRectangle(self.xsteps[x], 0, dx, self.ysteps[y])
        dc.DrawRectangle(self.xsteps[x], self.ysteps[y] + dy, dx, h - (self.ysteps[y] + dy))
        dc.DrawRectangle(0, self.ysteps[y], self.xsteps[x], dy)
        dc.DrawRectangle(self.xsteps[x] + dx, self.ysteps[y], w - (self.xsteps[x] + dx), dy)

        del odc
        # del dc

    def OnMapLeftDown(self, evt):
        self.SetFocus()
        w,h = self.canvas_size
        x, y = evt.GetX(), evt.GetY()
        if evt.LeftIsDown() and x < w and y < h:
            idx_x = int(float(x)/w*X)
            idx_y = int(float(y)/h*Y)
            self._draw_crosshair([idx_x, idx_y])

    def OnPaint(self, event):
        print('on paint')
        if hasattr(self, '_buffer') and self._buffer is not None:
            dc = wx.BufferedPaintDC(self, self._buffer)

        wx.CallAfter(m._draw_crosshair)

    def OnSize(self, evt):
        print('size evt')
        w, h = self.GetClientSize()
        w = max(1, w)
        h = max(1, h)
        self._buffer = wx.Bitmap(w, h)
        self.Draw()

    def Draw(self):
        print('draw')
        w, h = self.GetClientSize()
        if w < 1 and h < 1:
            return

        if self._buffer is not None:
            self.overlay.Reset()

            dc = wx.BufferedDC(wx.ClientDC(self), self._buffer)
            if 'wxMac' not in wx.PlatformInfo:
                dc = wx.GCDC(dc)

            self.canvas_size = cw, ch = int(h * X / Y), h

            checker = np.zeros((Y * X), dtype='uint8')
            checker[::2] = 1
            checker.shape = (Y, X)

            if ch > 0 and cw > 0:
                img = Image.fromarray(checker*100, mode='L').resize((cw, ch), Image.NEAREST)
                self._image = wx.Bitmap.FromBuffer(cw,ch,img.convert('RGB').tobytes())
                checker = np.array(img)
                self.xsteps = np.hstack(([0], np.where(checker[0, :-1] != checker[0, 1:])[0] + 1, [cw]))
                self.ysteps = np.hstack(([0], np.where(checker[:-1, 0] != checker[1:, 0])[0] + 1, [ch]))

                dc.Clear()
                dc.DrawBitmap(wx.Bitmap(self._image), 0, 0)



if __name__ == '__main__':
    a = wx.App()
    f = wx.Frame(None)
    m = Map(f)
    b = wx.BoxSizer(wx.HORIZONTAL)
    b.Add(m,0,wx.EXPAND)
    f.SetSizer(b)
    m.Draw()

    f.Show()
    a.MainLoop()

