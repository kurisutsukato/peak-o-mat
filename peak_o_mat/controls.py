
import wx

#import wx.lib.platebtn as platebtn

import  wx.lib.buttons  as  buttons
from wx.lib.pubsub import pub
from wx.lib import layoutf
import wx.stc as stc

import string

from . import misc_ui
from . import images

class MultipleChoice(wx.Dialog):
    def __init__(self, parent, title, choices):
        super(MultipleChoice, self).__init__(parent, -1, title, size=(200,-1))

        p = wx.Panel(self)

        #wx.StaticText(self, -1, "This example uses the wxCheckListBox control.", (45, 15))

        self.lb = wx.CheckListBox(p, -1, size=(120,-1), choices=choices+['Custom'])
        self.Bind(wx.EVT_CHECKLISTBOX, self.EvtCheckListBox, self.lb)
        self.lb.SetSelection(0)

        self.btn_ok = wx.Button(p, id=wx.ID_OK)
        self.btn_cancel = wx.Button(p, id=wx.ID_CANCEL)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(wx.Window(p), 1, wx.EXPAND)
        hbox.Add(self.btn_ok, 0, wx.EXPAND)
        hbox.Add(self.btn_cancel, 0, wx.EXPAND|wx.LEFT, 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.lb, 1, wx.EXPAND|wx.ALL,15)
        vbox.Add(hbox, 0, wx.EXPAND|wx.BOTTOM|wx.LEFT|wx.RIGHT, 15)
        p.SetSizer(vbox)

    def EvtCheckListBox(self, evt):
        index = evt.GetSelection()
        label = self.lb.GetString(index)
        if label == 'Custom':
            self.lb.SetCheckedStrings(['Custom'])
            self.selection = ['Custom']
        else:
            checked = list(self.lb.GetCheckedStrings())
            try:
                checked.remove('Custom')
            except ValueError:
                pass
            self.lb.SetCheckedStrings(checked)
            self.selection = checked

    def SetSelections(self, selections):
        self.lb.SetCheckedStrings(selections)
        self.selection = selections

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

        parent.Bind(misc_ui.EVT_SHOUT, self.OnMessage)
        
        self.counter = 0
        self.forever = False
        self.blink = False
        
    def OnMessage(self, evt):
        """\
        error handler for a misc_ui.ShoutEvent type message
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
        evt.Skip()
            
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
    tbdata = [
        ['logx.png','btn_logx', 'toggle Xlog/lin scale', 1, False],
        ['logy.png','btn_logy', 'toggle Ylog/lin scale', 1, False],
        ['linestyle.png','btn_style', 'toggle line/dot linestyle', 1, False],
        ['peaks.png','btn_peaks', 'toggle show single peaks', 1, False],
        ['eraser.png','btn_erase', 'remove bad data points', 2, True],
        ['hand.png','btn_drag', 'drag visible region', 2, True],
        ['zoomxy.png','btn_zoom', 'zoom to rectangular region', 2, True],
        ['auto.png','btn_auto', 'autoscale', 0, False],
        ['scalex.png','btn_autox', 'autoscale x', 0, False],
        ['scaley.png','btn_autoy', 'autoscale y', 0, False],
        ['auto2fit.png','btn_auto2fit', 'autoscale to fit region', 0, False],
        ]

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)
        self.action = []
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        for image,name,help,btn,action in self.tbdata:
            bmp = images.get_bmp(image)

            if btn in [1,2]:
                btn = buttons.GenBitmapToggleButton(self, -1, bmp, name=name, style=wx.BORDER_NONE)
                #btn.SetBitmap(bmp)
            elif btn == 0:
                btn = buttons.GenBitmapButton(self, -1, bmp, name=name, style=wx.BORDER_NONE)
                #btn.SetBitmap(bmp)
            btn.SetMinSize((30,30))
            if action:
                self.ActionButton(btn)
            btn.SetToolTip(wx.ToolTip(help))
            sizer.Add(btn, 0, wx.BOTTOM|wx.EXPAND,1)

        self.SetSizer(sizer)
        self.Layout()
        self.SetMinSize((30,400))

        pub.subscribe(self.OnNewMode, ('ID'+str(id(wx.GetTopLevelParent(self))),'canvas','newmode'))

    def _set_silent(self, state):
        self.SetEvtHandlerEnabled(not state)
    silent = property(fset=_set_silent)

    def OnNewMode(self, mode):
        self.silent = True
        btns = ['zoom','drag','erase']
        if mode in btns:
            btn = btns.pop(btns.index(mode))
            btn = self.FindWindowByName('btn_'+btn)
            btn.SetValue(True)
        for b in btns:
            b = self.FindWindowByName('btn_'+b)
            b.SetValue(False)
        self.silent = False
        
    def Enable(self, state=True):
        for child in self.GetChildren():
            child.Enable(state)
        wx.Panel.Enable(self, state)
        
    def Disable(self):
        self.Enable(False)
        
    def ActionButton(self, btn):
        self.action.append(btn)
        btn.Bind(wx.EVT_BUTTON, self.OnActionButton)

    def OnActionButton(self, evt):
        evt.Skip()
        self.silent = True
        this = evt.GetEventObject()
        state = this.GetValue()
        if state:
            for btn in self.action:
                if btn != this:
                    btn.SetValue(False)
        self.silent = False

ALPHA_ONLY = 1
INT_ONLY = 2
FLOAT_ONLY = 3
DIGIT_ONLY = 4

class InputValidator(wx.Validator):
    def __init__(self, flag=None, pyVar=None):
        wx.Validator.__init__(self)
        self.flag = flag
        self.Bind(wx.EVT_CHAR, self.OnChar)

        self.Bind(wx.EVT_TEXT, self.OnText)

    def OnText(self, evt):
        evt.Skip()
        tc = evt.GetEventObject()
        val = evt.GetEventObject().GetValue()
        try:
            if val != '':
                x = float(val)
        except ValueError as e:
            tc.SetBackgroundColour('pink')
            tc.Refresh()
        else:
            tc.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW))
            tc.Refresh()

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
            tc.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW))
            tc.Refresh()
            return True

    def OnChar(self, event):
        tc = self.GetWindow()
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
        if self.flag == FLOAT_ONLY and chr(key) in string.digits+'.-+e':
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

import re
import types

class FormatValidator(wx.Validator):
    def __init__(self, expr, pyVar=None):
        wx.Validator.__init__(self)
        if type(expr) == bytes:
            self.check = re.compile(expr).match
        elif type(expr) == types.FunctionType:
            self.check = expr
        else:
            return False

        self.Bind(wx.EVT_TEXT, self.OnText)

    def OnText(self, evt):
        evt.Skip()
        tc = evt.GetEventObject()
        val = evt.GetEventObject().GetValue()
        if self.check(val) is not None:
            tc.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW))
            tc.Refresh()
        else:
            tc.SetBackgroundColour('pink')
            tc.Refresh()

    def Clone(self):
        return FormatValidator(self.check)

    def Validate(self, win):
        tc = self.GetWindow()
        val = tc.GetValue()
        if val == '':
            tc.SetBackgroundColour('pink')
            tc.SetFocus()
            tc.Refresh()
            return False
        else:
            tc.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW))
            tc.Refresh()
            return True

    def TransferToWindow(self):
        return True

    def TransferFromWindow(self):
        return True

import  keyword

import  wx
import  wx.stc  as  stc

if wx.Platform == '__WXMSW__':
    faces = { 'times': 'Times New Roman',
              'mono' : 'Courier New',
              'helv' : 'Arial',
              'other': 'Comic Sans MS',
              'size' : 10,
              'size2': 8,
             }
elif wx.Platform == '__WXMAC__':
    faces = { 'times': 'Times New Roman',
              'mono' : 'Monaco',
              'helv' : 'Arial',
              'other': 'Comic Sans MS',
              'size' : 12,
              'size2': 10,
             }
else:
    faces = { 'times': 'Times',
              'mono' : 'Courier',
              'helv' : 'Helvetica',
              'other': 'new century schoolbook',
              'size' : 12,
              'size2': 10,
             }

class PythonSTC(stc.StyledTextCtrl):
    def __init__(self, parent, ID,
                 pos=wx.DefaultPosition, size=wx.DefaultSize,
                 style=0):
        stc.StyledTextCtrl.__init__(self, parent, ID, pos, size, style)

        self.CmdKeyAssign(ord('B'), stc.STC_SCMOD_CTRL, stc.STC_CMD_ZOOMIN)
        self.CmdKeyAssign(ord('N'), stc.STC_SCMOD_CTRL, stc.STC_CMD_ZOOMOUT)

        self.SetLexer(stc.STC_LEX_PYTHON)
        self.SetKeyWords(0, " ".join(keyword.kwlist))

        self.SetProperty("fold", "1")
        self.SetProperty("tab.timmy.whinge.level", "1")
        self.SetMargins(0,0)

        self.SetViewWhiteSpace(False)

        self.SetEdgeMode(stc.STC_EDGE_BACKGROUND)
        self.SetEdgeColumn(78)

        self.Bind(stc.EVT_STC_UPDATEUI, self.OnUpdateUI)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyPressed)

        # Make some styles,  The lexer defines what each style is used for, we
        # just have to define what each style looks like.  This set is adapted from
        # Scintilla sample property files.

        self.SetIndent(4)
        self.SetTabIndents(True)
        self.SetTabWidth(1)

        # Global default styles for all languages
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     "face:%(mono)s,size:%(size)d" % faces)
        self.StyleClearAll()  # Reset all to be like the default

        # Global default styles for all languages
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     "face:%(mono)s,size:%(size)d" % faces)
        self.StyleSetSpec(stc.STC_STYLE_LINENUMBER,  "back:#C0C0C0,face:%(mono)s,size:%(size2)d" % faces)
        self.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR, "face:%(other)s" % faces)
        self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT,  "fore:#0000FF,back:#DDFFDD,bold")
        self.StyleSetSpec(stc.STC_STYLE_BRACEBAD,    "fore:#000000,back:#FFAAAA,bold")

        # Python styles
        # Default
        self.StyleSetSpec(stc.STC_P_DEFAULT, "fore:#000000,face:%(mono)s,size:%(size)d" % faces)
        # Comments
        self.StyleSetSpec(stc.STC_P_COMMENTLINE, "fore:#007F00,face:%(other)s,size:%(size)d" % faces)
        # Number
        self.StyleSetSpec(stc.STC_P_NUMBER, "fore:#007F7F,size:%(size)d" % faces)
        # String
        self.StyleSetSpec(stc.STC_P_STRING, "fore:#7F007F,face:%(mono)s,size:%(size)d" % faces)
        # Single quoted string
        self.StyleSetSpec(stc.STC_P_CHARACTER, "fore:#7F007F,face:%(mono)s,size:%(size)d" % faces)
        # Keyword
        self.StyleSetSpec(stc.STC_P_WORD, "fore:#00007F,bold,size:%(size)d" % faces)
        # Triple quotes
        self.StyleSetSpec(stc.STC_P_TRIPLE, "fore:#7F0000,size:%(size)d" % faces)
        # Triple double quotes
        self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE, "fore:#7F0000,size:%(size)d" % faces)
        # Class name definition
        self.StyleSetSpec(stc.STC_P_CLASSNAME, "fore:#0000FF,bold,underline,size:%(size)d" % faces)
        # Function or method name definition
        self.StyleSetSpec(stc.STC_P_DEFNAME, "fore:#007F7F,bold,size:%(size)d" % faces)
        # Operators
        self.StyleSetSpec(stc.STC_P_OPERATOR, "bold,size:%(size)d" % faces)
        # Identifiers
        self.StyleSetSpec(stc.STC_P_IDENTIFIER, "fore:#000000,face:%(mono)s,size:%(size)d" % faces)
        # Comment-blocks
        self.StyleSetSpec(stc.STC_P_COMMENTBLOCK, "fore:#7F7F7F,size:%(size)d" % faces)
        # End of line where string is not closed
        self.StyleSetSpec(stc.STC_P_STRINGEOL, "fore:#000000,face:%(mono)s,back:#E0C0E0,eol,size:%(size)d" % faces)

        self.SetCaretForeground("BLUE")

        self.EmptyUndoBuffer()
        self.Colourise(0, -1)

        self.SetMarginType(1, stc.STC_MARGIN_NUMBER)
        self.SetMarginWidth(1, 25)


    def OnKeyPressed(self, event):
        if self.CallTipActive():
            self.CallTipCancel()
        key = event.GetKeyCode()

        if key == 32 and event.ControlDown():
            pos = self.GetCurrentPos()
        else:
            event.Skip()

    def OnUpdateUI(self, evt):
        # check for matching braces
        braceAtCaret = -1
        braceOpposite = -1
        charBefore = None
        caretPos = self.GetCurrentPos()

        if caretPos > 0:
            charBefore = self.GetCharAt(caretPos - 1)
            styleBefore = self.GetStyleAt(caretPos - 1)

        # check before
        if charBefore and chr(charBefore) in "[]{}()" and styleBefore == stc.STC_P_OPERATOR:
            braceAtCaret = caretPos - 1

        # check after
        if braceAtCaret < 0:
            charAfter = self.GetCharAt(caretPos)
            styleAfter = self.GetStyleAt(caretPos)

            if charAfter and chr(charAfter) in "[]{}()" and styleAfter == stc.STC_P_OPERATOR:
                braceAtCaret = caretPos

        if braceAtCaret >= 0:
            braceOpposite = self.BraceMatch(braceAtCaret)

        if braceAtCaret != -1  and braceOpposite == -1:
            self.BraceBadLight(braceAtCaret)
        else:
            self.BraceHighlight(braceAtCaret, braceOpposite)
            #pt = self.PointFromPosition(braceOpposite)
            #self.Refresh(True, wxRect(pt.x, pt.y, 5,5))
            #print pt
            #self.Refresh(False)

import wx.dataview as dv

class ListModel(dv.DataViewIndexListModel):
    def __init__(self, data):
        dv.DataViewIndexListModel.__init__(self)
        self.data = data

    @property
    def data(self):
        return self._data
    @data.setter
    def data(self, data):
        self._data = data
        self.Reset(len(data))

    def update(self, obj, value):
        idx = self._data.index(obj)
        self._data[idx] = value
        #TODO: next line releases the plot references, obj is a multiplotmodel
        #obj.release()
        del obj
        self.Cleared()

    def GetColumnCount(self):
        return 1

    def GetCount(self):
        return len(self.data)

    def GetColumnType(self, col):
        return 'string'

    def GetValueByRow(self, row, col):
        return self.data[row].identifier

    def SetValueByRow(self, value, row, col):
        self.data[row].identifier = value

    def get_selected(self, dataviewitem):
        return self.data[self.GetRow(dataviewitem)]

class _ListModel(dv.PyDataViewModel):
    def __init__(self, data):
        dv.PyDataViewModel.__init__(self)
        self.data = data

    def update(self, obj, value):
        idx = self._data.index(obj)
        self._data[idx] = value
        #TODO: next line releases the plot references, oj is a multiplotmodel
        obj.release()
        self.Cleared()

    @property
    def data(self):
        return self._data
    @data.setter
    def data(self, data):
        self._data = data
        self.Cleared()

    def GetChildren(self, parent, children):
        if not parent:
            for line in self._data:
                children.append(self.ObjectToItem(line))
            return len(self._data)

    def IsContainer(self, item):
        if not item:
            return True
        else:
            return False

    def GetColumnCount(self):
        return 1

    def GetCount(self):
        return len(self.data)

    def GetColumnType(self, col):
        return 'string'

    def GetParent(self, item):
        return dv.NullDataViewItem

    def GetValue(self, item, col):
        return self.ItemToObject(item).identifier

    def SetValue(self, value, item, col):
        self.ItemToObject(item).identifier = value

class FigureListController:
    def __init__(self, parent_view, data):
        self.parent_view = parent_view
        self.model = ListModel(data)

        self.create_ui()

        pub.subscribe(self.refresh_view, (self.view.id, 'figurelist','needsupdate'))

    def refresh_view(self):
        self.model.Reset(len(self.model.data))

    def create_ui(self):
        self.view = FigureListCtrl(self.parent_view.pan_tree, self.model, self)
        self.parent_view.pan_tree.GetSizer().Add(self.view,0,wx.EXPAND)
        self.parent_view.pan_tree.Layout()


class FigureListCtrl(wx.Panel):
    def __init__(self, parent, model, controller):
        wx.Panel.__init__(self, parent, size=(-1,150))
        self.model = model # ugly: this should be refe renced here

        self.controller = controller
        self.id = 'ID'+str(id(wx.GetTopLevelParent(self)))

        self.lst = dv.DataViewCtrl(self,style=dv.DV_NO_HEADER|dv.DV_ROW_LINES)

        self.lst.AssociateModel(self.model)

        self.lst.AppendTextColumn("Figure", 0, width=200)#, mode=dv.DATAVIEW_CELL_EDITABLE|dv.DATAVIEW_CELL_ACTIVATABLE)

        self.btn_fig_create = wx.Button(self, label='Create', style=wx.BU_EXACTFIT)
        #self.btn_fig_create.Disable()
        self.btn_fig_del = wx.Button(self, label='Delete', style=wx.BU_EXACTFIT)
        self.btn_fig_clone = wx.Button(self, label='Clone', style=wx.BU_EXACTFIT)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.lst, 1, wx.EXPAND)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.btn_fig_create, 0, wx.EXPAND|wx.ALL, 1)
        hbox.Add(self.btn_fig_del, 0, wx.EXPAND|wx.ALL, 1)
        hbox.Add(self.btn_fig_clone, 0, wx.EXPAND|wx.ALL, 1)
        vbox.Add(hbox, 0, wx.EXPAND)
        self.SetSizer(vbox)

        self.lst.Bind(dv.EVT_DATAVIEW_ITEM_ACTIVATED, self.OnShow)
        self.btn_fig_create.Bind(wx.EVT_BUTTON, self.OnCreateFigure)
        self.btn_fig_del.Bind(wx.EVT_BUTTON, self.OnDeleteFigure)
        self.btn_fig_clone.Bind(wx.EVT_BUTTON, self.OnCloneFigure)
        self.Bind(wx.EVT_IDLE, self.OnIdle)

        pub.subscribe(self.OnFigureClose, (self.id, 'figure','discard'))
        pub.subscribe(self.OnFigureClose, (self.id, 'figure','save'))

        self.set_tooltips()

    def set_tooltips(self):
        self.lst.SetToolTip('List of all figure objects. Double click on an item to open the figure.')
        self.btn_fig_create.SetToolTip('Create a new figure based on the current plot.')
        self.btn_fig_del.SetToolTip('Delete the figure corresponding to the selected item.')

    def OnFigureClose(self):
        self.Enable(True)

    def OnIdle(self, evt):
        self.btn_fig_del.Enable(self.lst.HasSelection())
        self.btn_fig_clone.Enable(self.lst.HasSelection())

    def OnCloneFigure(self, evt):
        if self.lst.HasSelection():
            sel = self.model.get_selected((self.lst.GetSelection()))
            pub.sendMessage((self.id, 'figurelist','clone'), msg=sel)

    def OnCreateFigure(self, evt):
        pub.sendMessage((self.id, 'figurelist','create'), msg=None)

    def OnShow(self, evt):
        sel = self.model.get_selected((self.lst.GetSelection()))
        pub.sendMessage((self.id, 'figurelist','show'), msg=sel)
        evt.Skip()
        self.Enable(False)

    def OnDeleteFigure(self, event):
        if self.lst.HasSelection():
            sel = self.model.get_selected((self.lst.GetSelection()))
            pub.sendMessage((self.id, 'figurelist','del'), msg=sel)


if __name__ == '__main__':
    app = wx.App()
    dlg = MultipleChoice(None, 'Select elements', ['eins','zwei','drei'])
    dlg.ShowModal()
    print(dlg.selection)
    dlg.Destroy()
    app.MainLoop()
