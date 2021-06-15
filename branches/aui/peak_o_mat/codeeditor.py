import wx

from wx import stc
from pubsub import pub
import wx.lib.agw.flatnotebook as fnb

import types
from datetime import datetime

# from RestrictedPython import

import code
from io import StringIO
import sys
import re

from .controls import PythonSTC
from .misc_ui import WithMessage
from . import images

from .symbols import pom_globals


class Locals(dict):
    def __init__(self, *args):
        self.autocall = []
        super(Locals, self).__init__(*args)

    def __getitem__(self, name):
        if name in self.autocall:
            return dict.__getitem__(self, name)()
        else:
            return dict.__getitem__(self, name)

    def add(self, name, val, autocall=False):
        self[name] = val
        if autocall:
            self.autocall.append(name)

    def __setitem__(self, name, val):
        if name in self.autocall:
            raise Exception('overwriting \'%s\' not allowed' % name)
        else:
            dict.__setitem__(self, name, val)


class Interpreter(code.InteractiveInterpreter):
    def __init__(self, controller):
        self.controller = controller
        self.errline = None

        code.InteractiveInterpreter.__init__(self, self.init_locals())

        self.out = StringIO()

    def init_locals(self):
        locs = Locals(locals())
        locs.add('add_plot', self.controller.add_plot)
        locs.add('add_set', self.controller.add_set)
        locs.add('project', self.controller.project)
        locs.add('controller', self.controller)

        def _get_model():
            return self.controller.fit_controller.model

        locs.add('model', _get_model, True)

        def _update_view():
            #TODO: should not be necesary anymore: # self.controller.update_tree()
            self.controller.update_plot()

        locs.add('sync', _update_view)

        def _get_active_set():
            return self.controller.active_set

        locs.add('aset', _get_active_set, True)
        # locs.add('intro', intro, False)
        return locs

    def write(self, text):
        self.out.write(text)
        mat = re.match(r'.+, line (\d+)\D+', text)
        if mat is not None:
            self.errline = int(mat.groups()[0]) - 1

    def getresult(self):
        ret = self.out.getvalue(), self.errline
        self.out = StringIO()
        return ret

class CodeController(object):
    def __init__(self, main, view):
        self.controller = main
        self.view = view
        self.interpreter = Interpreter(self.controller)
        Interactor().Install(self, view)

    def new_editor(self):
        self.view.editor.add()

    def remove_editor(self, pos):
        self.view.editor.pop(pos)

    def register_symbols(self, source):
        '''das braucht man wohl um im code editor funktionen zu definieren,
        die man spaeter zum fitten nehmen kann'''

        try:
            m = types.ModuleType('dynamic')
            # m = imp.new_module('dynamic')
            exec(source, {}, m.__dict__)
        except:
            return
        else:
            for name in dir(m):
                sym = getattr(m, name)
                if type(sym) in [types.FunctionType]: # TODO:, types.ModuleType, np.ufunc]:
                    pom_globals.update({name: sym})

    def run(self, source):
        self.register_symbols(source)

        tmp = sys.stdout
        sys.stdout = self.interpreter
        self.interpreter.runsource(source, symbol='exec')
        sys.stdout = tmp
        return self.interpreter.getresult()

    @property
    def data(self):
        return self.view.editor.get_pages()

    @data.setter
    def data(self, data):
        self.view.silent = True
        self.view.editor.set_pages(data)
        self.view.silent = False


class Interactor:
    def Install(self, controller, view):
        self.controller = controller
        self.view = view

        self.view.btn_runcode.Bind(wx.EVT_BUTTON, self.OnExecute)
        self.view.btn_runselectedcode.Bind(wx.EVT_BUTTON, self.OnExecute)
        self.view.Bind(wx.EVT_CLOSE, self.OnClose)
        self.view.Bind(stc.EVT_STC_MODIFIED, self.on_code_modified)

        self.view.Bind(wx.EVT_IDLE, self.OnIdle)

        self.view.Bind(wx.EVT_LEAVE_WINDOW, self.OnKillFocus)

        self.view.btn_neweditor.Bind(wx.EVT_BUTTON, self.OnNewEditor)
        self.view.btn_closeeditor.Bind(wx.EVT_BUTTON, self.OnCloseEditor)
        self.view.btn_renameeditor.Bind(wx.EVT_BUTTON, self.OnRenameEditor)

    def OnKillFocus(self, evt):
        self.controller.register_symbols(self.view.editor.GetText())

    def OnIdle(self, evt):
        self.view.btn_runselectedcode.Enable(len(self.view.editor.GetSelectedText().strip()) > 0)
        self.view.btn_runcode.Enable(self.view.editor is not None)

    def OnRenameEditor(self, evt):
        dlg = wx.TextEntryDialog(self.view, 'New Name', 'Rename', self.view.editor.name)
        if dlg.ShowModal() == wx.ID_OK:
            self.view.editor.name = dlg.GetValue()
            pub.sendMessage((self.view.instid, 'code', 'changed'), msg=None)

    def OnCloseEditor(self, evt):
        self.view.editor.close()
        pub.sendMessage((self.view.instid, 'code', 'changed'), msg=None)

    def OnNewEditor(self, evt):
        self.controller.new_editor()
        pub.sendMessage((self.view.instid, 'code', 'changed'), msg=None)

    def on_code_modified(self, evt):
        if evt.GetModificationType() & 3:  # char added or removed
            pub.sendMessage((self.view.instid, 'code', 'changed'), msg=None)

    def OnExecute(self, evt):
        wx.BeginBusyCursor()
        self.view.txt_result.AppendText('Code execution started at {}\n'.format(datetime.now().strftime('%H:%M:%S')))
        if evt.GetEventObject() == self.view.btn_runcode:
            val, errline = self.controller.run(self.view.editor.GetText())
        else:
            anc, pos = self.view.editor.GetSelection()
            start = self.view.editor.LineFromPosition(anc)
            val, errline = self.controller.run(self.view.editor.GetSelectedText())
            if errline is not None:
                errline += start

        self.view.txt_result.AppendText('{}\nCode execution finished.\n'.format(val))

        if errline is not None:
            self.view.editor.SelectLine(errline)
        wx.EndBusyCursor()

    def OnClose(self, evt):
        self.controller.controller.show_codeeditor(False)


class EditorsProxy(list):
    def __init__(self, container):
        self.container = container

    def get_pages(self):
        return [(self.container.GetPageText(n), q.GetText()) for n, q in enumerate(self)]

    def set_pages(self, pages):
        self.container.DeleteAllPages()
        self[:] = []
        for name, data in pages:
            self.add(name)
            self.SetText(data)

    @property
    def name(self):
        return self.container.GetPageText(self.container.GetSelection())

    @name.setter
    def name(self, name):
        self.container.SetPageText(self.container.GetSelection(), name)

    def add(self, name='new'):
        self.append(CodeEditor(self.container))
        self.container.AddPage(self[-1], name)
        self.container.SetSelection(self.container.GetPageCount() - 1)

    def close(self):
        if self.container.GetPageCount() == 1:
            self.SetText('')
            self.container.SetPageText(0, 'new')
        else:
            sel = self.container.GetSelection()
            if sel != -1:
                self.container.DeletePage(sel)
                self.pop(sel)

    def __getattr__(self, item):
        return getattr(self.selection, item)

    @property
    def selection(self):
        sel = self.container.GetSelection()
        if sel == -1:
            return None
        else:
            return self.container.GetPage(sel)

    def GetSelectedText(self):
        if self.selection is None:
            return ''
        else:
            return self.selection.GetSelectedText()

    def GetText(self):
        if self.selection is None:
            return ''
        else:
            return self.selection.GetText()


class CodeEditorFrame(WithMessage, wx.Frame):
    def __init__(self, parent):
        style = wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT
        wx.Frame.__init__(self, parent, style=style)
        WithMessage.__init__(self)

        self.setup_controls()
        self.layout()

        self.SetTitle('Code Editor')

        ico = wx.Icon()
        ico.CopyFromBitmap(images.get_bmp('logosmall.png'))
        self.pom_ico = ico
        self.SetIcon(ico)

    def Show(self, state):
        if not hasattr(self, '_centered'):
            self._centered = True
            self.CenterOnParent()
            self.SetSize((600, 500))
        wx.Frame.Show(self, state)

    def _set_silent(self, state):
        self.SetEvtHandlerEnabled(not state)

    silent = property(fset=_set_silent)

    def setup_controls(self):
        self.panel = wx.Panel(self)
        # self.nb = wx.Notebook(self.panel)
        self.nb = fnb.FlatNotebook(self.panel, agwStyle=fnb.FNB_NO_X_BUTTON)
        self.editor = EditorsProxy(self.nb)
        self.editor.add('new')
        self.btn_neweditor = wx.Button(self.panel, label='New Page')
        self.btn_closeeditor = wx.Button(self.panel, label='Close Page')
        self.btn_renameeditor = wx.Button(self.panel, label='Rename Page')
        self.btn_runcode = wx.Button(self.panel, label='Run')
        self.btn_runselectedcode = wx.Button(self.panel, label='Run Selection')
        self.txt_result = wx.TextCtrl(self.panel, size=(500, 120), style=wx.TE_MULTILINE)

    def layout(self):
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.nb, 1, wx.EXPAND | wx.ALL, 2)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.btn_neweditor, 0, wx.RIGHT, 5)
        hbox.Add(self.btn_closeeditor, 0, wx.RIGHT, 5)
        hbox.Add(self.btn_renameeditor, 0)
        hbox.Add(wx.Window(self.panel, size=(1, 1)), 1)
        hbox.Add(self.btn_runselectedcode, 0, wx.RIGHT, 5)
        hbox.Add(self.btn_runcode, 0)

        vbox.Add(hbox, 0, wx.EXPAND | wx.RIGHT | wx.LEFT | wx.BOTTOM, 2)
        vbox.Add(self.txt_result, 0, wx.EXPAND | wx.ALL, 2)
        vbox.Add(wx.Window(self.panel, size=(10, 10)))
        self.panel.SetSizer(vbox)


class CodeEditor(PythonSTC):
    def __init__(self, parent, style=wx.BORDER_NONE):
        PythonSTC.__init__(self, parent, -1, style=style)

    # Some methods to make it compatible with how the wxTextCtrl is used
    def SetValue(self, value):
        if wx.USE_UNICODE:
            value = value.decode('iso8859_1')
        val = self.GetReadOnly()
        self.SetReadOnly(False)
        self.SetText(value)
        self.EmptyUndoBuffer()
        self.SetSavePoint()
        self.SetReadOnly(val)

    def SetEditable(self, val):
        self.SetReadOnly(not val)

    def IsModified(self):
        return self.GetModify()

    def Clear(self):
        self.ClearAll()

    def SetInsertionPoint(self, pos):
        self.SetCurrentPos(pos)
        self.SetAnchor(pos)

    def ShowPosition(self, pos):
        line = self.LineFromPosition(pos)
        # self.EnsureVisible(line)
        self.GotoLine(line)

    def GetLastPosition(self):
        return self.GetLength()

    def GetPositionFromLine(self, line):
        return self.PositionFromLine(line)

    def GetRange(self, start, end):
        return self.GetTextRange(start, end)

    def GetSelection(self):
        return self.GetAnchor(), self.GetCurrentPos()

    def SetSelection(self, start, end):
        self.SetSelectionStart(start)
        self.SetSelectionEnd(end)

    def SelectLine(self, line):
        start = self.PositionFromLine(line)
        end = self.GetLineEndPosition(line)
        self.SetSelection(start, end)

    def RegisterModifiedEvent(self, eventHandler):
        self.Bind(wx.stc.EVT_STC_CHANGE, eventHandler)


def new(controller, parent):
    return CodeController(controller, CodeEditorFrame(parent))


if __name__ == '__main__':
    app = wx.PySimpleApp(None)
    c = new(None, None)
    app.MainLoop()
