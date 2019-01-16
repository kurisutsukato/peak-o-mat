from win32com import universal
from win32com.client import gencache
from win32com.server import util
import pythoncom

import sys, os
import logging as log
import numpy as np
import pickle
import zmq

import win32traceutil

import win32com.client
win32com.client.gencache.is_readonly = False
win32com.client.gencache.Rebuild()

bValidateGencache = not hasattr(sys, "frozen")
gencache.EnsureModule('{00020813-0000-0000-C000-000000000046}', 0, 1, 3, bForDemand=True) # Excel 9
gencache.EnsureModule('{2DF8D04C-5BFA-101B-BDE5-00AA0044DE52}', 0, 2, 1, bForDemand=True, bValidateFile=bValidateGencache) # Office 9
# the "Addin Designer" typelib for its constants
gencache.EnsureModule('{AC0714F2-3D04-11D1-AE7D-00A0C90F26F4}', 0, 1, 0, bForDemand=True, bValidateFile=bValidateGencache)

# the TLB defining the interfaces we implement
universal.RegisterInterfaces('{AC0714F2-3D04-11D1-AE7D-00A0C90F26F4}', 0, 1, 0, ["_IDTExtensibility2"])
universal.RegisterInterfaces('{2DF8D04C-5BFA-101B-BDE5-00AA0044DE52}', 0, 2, 4, ["IRibbonExtensibility", "IRibbonControl"])


import winxpgui as win32gui
import win32gui_struct
import win32api
import win32con, winerror
import struct, array
import commctrl
import queue
import os


IDC_BUTTON_OK = 1028


class Dialog:
    def __init__(self):
        win32gui.InitCommonControls()
        self.hinst = win32gui.dllhandle
        self.list_data = {}

    def _RegisterWndClass(self):
        className = "PythonDocSearch"
        message_map = {}
        wc = win32gui.WNDCLASS()
        wc.SetDialogProc() # Make it a dialog class.
        wc.hInstance = self.hinst
        wc.lpszClassName = className
        wc.style = win32con.CS_VREDRAW | win32con.CS_HREDRAW
        wc.hCursor = win32gui.LoadCursor( 0, win32con.IDC_ARROW )
        wc.hbrBackground = win32con.COLOR_WINDOW + 1
        wc.lpfnWndProc = message_map # could also specify a wndproc.
        # C code: wc.cbWndExtra = DLGWINDOWEXTRA + sizeof(HBRUSH) + (sizeof(COLORREF));
        wc.cbWndExtra = win32con.DLGWINDOWEXTRA + struct.calcsize("Pi")
        icon_flags = win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE

        try:
            classAtom = win32gui.RegisterClass(wc)
        except win32gui.error as err_info:
            if err_info.winerror!=winerror.ERROR_CLASS_ALREADY_EXISTS:
                raise
        return className

    def _GetDialogTemplate(self, dlgClassName):
        style = win32con.WS_THICKFRAME | win32con.WS_POPUP | win32con.WS_VISIBLE | win32con.WS_CAPTION | win32con.WS_SYSMENU | win32con.DS_SETFONT | win32con.WS_MINIMIZEBOX
        cs = win32con.WS_CHILD | win32con.WS_VISIBLE
        title = "WARNING"

        # Window frame and title
        dlg = [ [title, (0, 0, 210, 60), style, None, (8, "MS Sans Serif"), None, dlgClassName], ]

        # ID label and text box
        dlg.append([130,'Unable to communicate with peak-o-mat.',-1, (5, 5, 200, 9), cs | win32con.SS_LEFT])
        dlg.append([130,'Have you started the plot server?',-1, (5, 15, 200, 9), cs | win32con.SS_LEFT])

        # Search/Display Buttons
        # (x positions don't matter here)
        s = cs | win32con.WS_TABSTOP
        dlg.append([128, "Ok", IDC_BUTTON_OK, (5, 35, 50, 14), s | win32con.BS_DEFPUSHBUTTON])

        return dlg

    def _DoCreate(self, fn):
        message_map = {
            #win32con.WM_SIZE: self.OnSize,
            win32con.WM_COMMAND: self.OnCommand,
            #win32con.WM_NOTIFY: self.OnNotify,
            win32con.WM_INITDIALOG: self.OnInitDialog,
            win32con.WM_CLOSE: self.OnClose,
            win32con.WM_DESTROY: self.OnDestroy,
        }
        dlgClassName = self._RegisterWndClass()
        template = self._GetDialogTemplate(dlgClassName)
        return fn(self.hinst, template, 0, message_map)

    def OnInitDialog(self, hwnd, msg, wparam, lparam):
        self.hwnd = hwnd
        # centre the dialog
        desktop = win32gui.GetDesktopWindow()
        l,t,r,b = win32gui.GetWindowRect(self.hwnd)
        dt_l, dt_t, dt_r, dt_b = win32gui.GetWindowRect(desktop)
        centre_x, centre_y = win32gui.ClientToScreen( desktop, ( (dt_r-dt_l)//2, (dt_b-dt_t)//2) )
        win32gui.MoveWindow(hwnd, centre_x-(r//2), centre_y-(b//2), r-l, b-t, 0)
        #self._SetupList()
        l,t,r,b = win32gui.GetClientRect(self.hwnd)
        self._DoSize(r-l,b-t, 1)

    def _DoSize(self, cx, cy, repaint = 1):
        ctrl = win32gui.GetDlgItem(self.hwnd, IDC_BUTTON_OK)
        l, t, r, b = win32gui.GetWindowRect(ctrl)
        l, t = win32gui.ScreenToClient(self.hwnd, (l,t) )
        r, b = win32gui.ScreenToClient(self.hwnd, (r,b) )
        list_y = b + 10
        w = r - l
        win32gui.MoveWindow(ctrl, cx - 5 - w, t, w, b-t, repaint)

    def OnCommand(self, hwnd, msg, wparam, lparam):
        id = win32api.LOWORD(wparam)
        if id == IDC_BUTTON_OK:
            win32gui.DestroyWindow(hwnd)

    # These function differ based on how the window is used, so may be overridden
    def OnClose(self, hwnd, msg, wparam, lparam):
        raise NotImplementedError

    def OnDestroy(self, hwnd, msg, wparam, lparam):
        pass

    def DoModal(self):
        return self._DoCreate(win32gui.DialogBoxIndirect)

    def OnClose(self, hwnd, msg, wparam, lparam):
        win32gui.EndDialog(hwnd, 0)

class AppEvent:
    def Init(self, addin):
        self.addin = addin

    def OnSheetSelectionChange(self, *args):
        self.addin.ribbon_refresh()

class pomAddin:
    _com_interfaces_ = ['_IDTExtensibility2','IRibbonExtensibility']

    _reg_clsctx_ = pythoncom.CLSCTX_INPROC_SERVER
    _reg_clsid_ = '{C9C904C5-D932-428E-A71B-51414EB7864E}'
    _reg_progid_ = "peak-o-mat_addin"
    _reg_policy_spec_ = "win32com.server.policy.EventHandlerPolicy"

    active = False

    _error_msg = None

    _public_methods_ = ['ribbon_onLoad','plot','enabled_plot']

    editor_is_visible = False

    def OnConnection(self, app, connectMode, addin, custom):
        self.app = app

        #register as running COM server
        wrapped = util.wrap(self)
        try:
            pythoncom.RegisterActiveObject(wrapped, self._reg_clsid_, 0)
        except pythoncom.com_error as e:
            print(e)

    def OnStartupComplete(self, custom):
        print('setup event handling')
        self.app_event = win32com.client.DispatchWithEvents(self.app, AppEvent)
        self.app_event.Init(self)

        self.ribbon_refresh()


    def OnDisconnection(self, mode, custom):
        print("OnDisconnection")
    def OnAddInsUpdate(self, custom):
        print("OnAddInsUpdate", custom)
    def OnBeginShutdown(self, custom):
        print("OnBeginShutdown", custom)


    def GetCustomUI(self, arg):
        xml_folder = """
        <customUI xmlns="http://schemas.microsoft.com/office/2006/01/customui" onLoad="ribbon_onLoad">
  <ribbon startFromScratch="false">
    <tabs>
      <tab idMso="TabHome">
        <group id="pom" label="peak-o-mat">
            <box id="group1" boxStyle="vertical">
                <button id="btn_plot" label="plot" onAction="plot" getEnabled="enabled_plot" tag="plot"/>
            </box>
        </group>
      </tab>
    </tabs>
  </ribbon>
</customUI>
        """
        print(arg)
        if arg == 'Microsoft.Excel.Workbook':
            return xml_folder
        else:
            return ''

    def ribbon_onLoad(self, ribbon):
        self.ribbonUI = ribbon

    def ribbon_refresh(self):
        log.debug('ribbon refresh')
        if hasattr(self, 'ribbonUI'):
            self.ribbonUI.Invalidate()

    def enabled_plot(self, *args):
        try:
            data = np.array([[float(q) for q in line] for line in self.app.Selection.Value], dtype=float).T
            assert data.ndim == 2
            assert min(data.shape) > 1
        except (AssertionError,AttributeError,TypeError,ValueError) as e:
            print(e)
            return False
        else:
            return True

    def plot(self, tag):
        try:
            data = np.array([[float(q) for q in line] for line in self.app.Selection.Value], dtype=float).T
            assert data.ndim == 2
            assert min(data.shape) > 1
        except (TypeError,ValueError) as e:
            print(e)
        else:
            msg = {'name':self.app.ActiveSheet.Name, 'data':data}
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            try:
                socket.connect("tcp://localhost:6789")
            except:
                d = Dialog()
                d.DoModal()
            else:
                socket.send_pyobj(msg)

                print(socket.recv_string())

def RegisterAddin(klass):
    import winreg
    x = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
    key = winreg.CreateKeyEx(x, "Software\\Microsoft\\Office\\Excel\\Addins")
    subkey = winreg.CreateKeyEx(key, klass._reg_progid_)
    winreg.SetValueEx(subkey, "CommandLineSafe", 0, winreg.REG_DWORD, 0)
    winreg.SetValueEx(subkey, "LoadBehavior", 0, winreg.REG_DWORD, 3)
    winreg.SetValueEx(subkey, "Description", 0, winreg.REG_SZ, klass._reg_progid_)
    winreg.SetValueEx(subkey, "FriendlyName", 0, winreg.REG_SZ, klass._reg_progid_)

def UnregisterAddin(klass):
    import winreg
    x = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
    winreg.DeleteKey(x, "Software\\Microsoft\\Office\\Excel\\Addins\\" + klass._reg_progid_)

if __name__ == '__main__':
    import win32com.server.register
    win32com.server.register.UseCommandLine(pomAddin)
    if "--unregister" in sys.argv:
        UnregisterAddin(pomAddin)
    else:
        RegisterAddin(pomAddin)