import os
import wx
from wx.lib import buttons
from wx.lib.pubsub import pub as Publisher
from wx.lib import layoutf

import  time
import string

import misc

class ScrolledMessageDialog(wx.Dialog):
    def __init__(self, parent, msg, caption,
                 pos=wx.DefaultPosition, size=(500,300),
                 style=wx.DEFAULT_DIALOG_STYLE):
        wx.Dialog.__init__(self, parent, -1, caption, pos, size, style)
        x, y = pos
        if x == -1 and y == -1:
            self.CenterOnScreen(wx.BOTH)

        pt = wx.SystemSettings_GetFont(wx.SYS_SYSTEM_FONT).GetPointSize()

        self.text = text = wx.TextCtrl(self, -1, '', 
                                       style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.text.SetDefaultStyle(wx.TextAttr(wx.BLACK, wx.WHITE, wx.Font(pt, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)))

        self.text.WriteText(msg)
        ok = wx.Button(self, wx.ID_OK, "OK")
        ok.SetDefault()
        lc = layoutf.Layoutf('t=t5#1;b=t5#2;l=l5#1;r=r5#1', (self,ok)) 
        text.SetConstraints(lc)

        lc = layoutf.Layoutf('b=b5#1;x%w50#1;w!80;h*', (self,))
        ok.SetConstraints(lc)
        self.SetAutoLayout(1)
        self.Layout()

class Status(wx.StatusBar):

    def __init__(self, parent):
        wx.StatusBar.__init__(self, parent, -1)

        self.SetFieldsCount(2)
        self.SetStatusWidths([-2,-5])

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.OnTime)

        parent.Bind(misc.EVT_SHOUT, self.OnMessage)
        
        self.counter = 0
        self.forever = False
        self.blink = False
        
    def OnMessage(self, evt):
        """\
        error handler for a misc.ShoutEvent type message
        """
        try:
            time = evt.time
        except AttributeError:
            time = 5000
            
        if evt.target == 1:
            self.timer.Stop()
            if evt.blink:
                self.blink = 1
                self.message(500, evt.msg, forever=evt.forever)
            else:
                self.blink = 0
                self.message(time, evt.msg, forever=evt.forever)
        else:
            self.shortmessage(evt.msg)
            
    def OnTime(self, evt):
        if self.blink:
            if self.counter < 7 or self.forever:
                msg = self.GetStatusText(1)
                self.SetStatusText('', 1)
                wx.FutureCall(150, self.message, 500, msg, self.forever)
                self.counter += 1
            else:
                self.timer.Stop()
                self.counter = 0
                self.SetStatusText('', 1)
        else:
            self.timer.Stop()
            self.SetStatusText('', 1)

    def shortmessage(self, msg):
        self.SetStatusText(msg, 0)
            
    def message(self, time, msg, forever=False):
        self.forever = forever
        self.timer.Start(time, wx.TIMER_ONE_SHOT)
        self.SetStatusText(msg, 1)

class HistTextCtrl(wx.ComboBox):
    def __init__(self, parent, id, value, **kwargs):
        wx.ComboBox.__init__(self, parent, id, value=value, style=wx.TE_PROCESS_ENTER)

        self._history = []
        self._cycle = None
        self.Bind(wx.EVT_KEY_DOWN, self.OnKey)

    def _get_last_op(self):
        return self._history[-1]
    last_op = property(_get_last_op)
        
    def OnKey(self, evt):
        key = evt.KeyCode
        if key == wx.WXK_UP:
            self.History()
        elif key == wx.WXK_DOWN:
            self.History(back=False)
        else:
            evt.Skip()
        
    def Store(self):
        if len(self._history) > 0:
            last = self._history[-1]
        else:
            last = ''
        if last != self.GetValue():
            self._history.append(self.GetValue())
        self._cycle = len(self._history)
        self.Insert(self.GetValue(), 0)
        self.SetValue('')
        
    def History(self, back=True):
        if self._cycle is None:
            return
        if not back:
            self._cycle += 1
            if self._cycle >= len(self._history):
                self._cycle = len(self._history)
                self.SetValue('')
                return
        else:
            self._cycle -= 1
            if self._cycle < 0:
                self._cycle = 0
        self.SetValue(self._history[self._cycle])

class Toolbar(wx.Panel):
    toggle = buttons.GenBitmapToggleButton
    push = buttons.GenBitmapButton
    tbdata = [
        ['logx.png','btn_logx', 'toggle Xlog/lin scale', toggle, False],
        ['logy.png','btn_logy', 'toggle Ylog/lin scale', toggle, False],
        ['linestyle.png','btn_style', 'toggle line/dot linestyle', toggle, False],
        ['peaks.png','btn_peaks', 'toggle show single peaks', toggle, False],
        ['eraser.png','btn_erase', 'remove bad data points', toggle, True],
        ['hand.png','btn_drag', 'drag visible region', toggle, True],
        ['zoomxy.png','btn_zoom', 'zoom to rectangular region', toggle, True],
        ['auto.png','btn_auto', 'autoscale', push, False],
        ['scalex.png','btn_autox', 'autoscale x', push, False],
        ['scaley.png','btn_autoy', 'autoscale y', push, False],
        ['auto2fit.png','btn_auto2fit', 'autoscale to fit region', push, False],
        ]

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.action = []
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        for image,name,help,btn,action in self.tbdata:
            imgdir = os.path.normpath(os.path.join(os.path.dirname(__file__),'../images'))
            imgpath = os.path.join(imgdir,image)

            bmp = misc.get_bmp(image)

            btn = btn(self, -1, bmp, name=name)
            if action:
                self.ActionButton(btn)
            btn.SetToolTip(wx.ToolTip(help))
            sizer.Add(btn, flag=wx.ADJUST_MINSIZE)

        self.SetSizer(sizer)

        Publisher.subscribe(self.OnNewMode, ('canvas','newmode'))

    def OnNewMode(self, msg):
        self.SetEvtHandlerEnabled(False)
        mode = msg.data
        btns = ['zoom','drag','erase']
        if mode in btns:
            btn = btns.pop(btns.index(mode))
            btn = self.FindWindowByName('btn_'+btn)
            btn.SetToggle(True)
        for b in btns:
            b = self.FindWindowByName('btn_'+b)
            b.SetToggle(False)
        self.SetEvtHandlerEnabled(True)
        
    def Enable(self, state=True):
        for child in self.GetChildren():
            child.Enable(state)
        wx.Panel.Enable(self, state)
        
    def Disable(self):
        self.Enable(False)
        
    def ActionButton(self, btn):
        self.action.append(btn)
        self.Bind(wx.EVT_BUTTON, self.OnActionButton, btn)
        
    def OnActionButton(self, evt):
        this = evt.GetEventObject()
        state = this.GetToggle() == 1
        if state:
            for btn in self.action:
                if btn != this:
                    btn.SetToggle(False)
        evt.Skip()

ALPHA_ONLY = 1
INT_ONLY = 2
FLOAT_ONLY = 3
DIGIT_ONLY = 4

class InputValidator(wx.PyValidator):
    def __init__(self, flag=None, pyVar=None):
        wx.PyValidator.__init__(self)
        self.flag = flag
        self.Bind(wx.EVT_CHAR, self.OnChar)

    def Clone(self):
        return InputValidator(self.flag)

    def Validate(self, win):
        tc = self.GetWindow()
        val = tc.GetValue()
        if val == '':
            tc.SetBackgroundColour('pink')
            tc.SetFocus()
            tc.Refresh()
            return False
        else:
             tc.SetBackgroundColour(wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOW))
             tc.Refresh()
             return True

        # should not be neccessary
        if self.flag == ALPHA_ONLY:
            for x in val:
                if x not in string.letters:
                    return False
        elif self.flag == FLOAT_ONLY:
            for x in val:
                if x not in string.digits+'.e-+':
                    return False
        elif self.flag == INT_ONLY:
            for x in val:
                if x not in string.digits+'-+':
                    return False
        elif self.flag == DIGIT_ONLY:
            for x in val:
                if x not in string.digits:
                    return False
        return True


    def OnChar(self, event):
        key = event.GetKeyCode()

        if self.flag is None:
            event.Skip()
            return

        if key < wx.WXK_SPACE or key == wx.WXK_DELETE or key > 255:
            event.Skip()
            return
        if self.flag == ALPHA_ONLY and chr(key) in string.letters:
            event.Skip()
            return
        if self.flag == INT_ONLY and chr(key) in string.digits+'-+':
            event.Skip()
            return
        if self.flag == DIGIT_ONLY and chr(key) in string.digits:
            event.Skip()
            return
        if self.flag == FLOAT_ONLY and chr(key) in string.digits+'.e+-':
            event.Skip()
            return

        if not wx.Validator_IsSilent():
            wx.Bell()

        # Returning without calling even.Skip eats the event before it
        # gets to the text control
        return

    def TransferToWindow(self):
        return True

    def TransferFromWindow(self):
        return True

