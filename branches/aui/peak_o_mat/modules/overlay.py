import wx
import numpy as np
print(wx.__version__)

from PIL import Image

X,Y = 19,27

class Map(wx.Window):
    def __init__(self, parent):
        super(Map, self).__init__(parent, style=wx.WANTS_CHARS)

        self._cross = [2, 4]
        self._buffer = None
        self._update_needed = False

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnMapLeftDown)
        self.Bind(wx.EVT_MOTION, self.OnMapLeftDown)

    def _draw_crosshair(self, dc):
        x, y = self._cross

        print('draw overlay at pos {},{}'.format(x,y))

        w, h = self.canvas_size
        dx = np.diff(self.xsteps)[x]
        dy = np.diff(self.ysteps)[y]

        if 'wxMac' not in wx.PlatformInfo:
            dc = wx.GCDC(dc)

        dc.SetBrush(wx.Brush(wx.Colour(255, 255, 0, 120)))
        dc.SetPen(wx.Pen(wx.Colour(255, 255, 0, 120), 0))
        dc.DrawRectangle(self.xsteps[x], 0, dx, self.ysteps[y])
        dc.DrawRectangle(self.xsteps[x], self.ysteps[y] + dy, dx, h - (self.ysteps[y] + dy))
        dc.DrawRectangle(0, self.ysteps[y], self.xsteps[x], dy)
        dc.DrawRectangle(self.xsteps[x] + dx, self.ysteps[y], w - (self.xsteps[x] + dx), dy)

    def _update_crosshair(self, evt):
        w,h = self.canvas_size
        x, y = evt.GetX(), evt.GetY()
        if x < w and y < h:
            idx_x = int(float(x)/w*X)
            idx_y = int(float(y)/h*Y)
            self._cross = [idx_x, idx_y]
            self.Refresh()

    def OnMapLeftDown(self, evt):
        self.SetFocus()
        if evt.LeftIsDown():
            self._update_crosshair(evt)

    def OnPaint(self, evt):
        dc = wx.PaintDC(self) if self.IsDoubleBuffered() else wx.BufferedPaintDC(self)
        if hasattr(self, '_buffer') and self._buffer is not None:
            dc.DrawBitmap(self._buffer, 0, 0)
            self._draw_crosshair(dc)

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
            dc = wx.BufferedDC(None, self._buffer)
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

                self.Refresh()


if __name__ == '__main__':
    a = wx.App()
    f = wx.Frame(None)
    m = Map(f)
    b = wx.BoxSizer(wx.HORIZONTAL)
    b.Add(m,1,wx.EXPAND)
    f.SetSizer(b)
    m.Draw()
    f.Show()
    a.MainLoop()

