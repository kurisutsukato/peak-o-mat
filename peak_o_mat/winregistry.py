import os, sys
from distutils.sysconfig import PREFIX
import re
import winreg as reg

def basepath():
    thisdir,f = os.path.split(os.path.abspath(__file__))
    parentdir,f = os.path.split(thisdir)
    return parentdir

def _q(arg):
    arg = arg.strip('"')
    return '"%s"'%arg

iconpath = os.path.join(basepath(), 'peak-o-mat.ico')
peakomatpath = os.path.join(basepath(), 'peak-o-mat.py')
python = os.path.join(PREFIX, 'python.exe')

def check():
    try:
        basekey = reg.OpenKey(reg.HKEY_CLASSES_ROOT, 'peak-o-mat')
        shell = reg.OpenKey(basekey, 'shell')
        open = reg.OpenKey(shell, 'open')
        command = reg.OpenKey(open, 'command')
        cmd = [q.strip('"') for q in re.split(r'\s(?=(?:[^"]|"[^"]*")*$)',reg.QueryValue(command, None).strip())]
        if len(cmd) == 3:
            python, pom, arg = cmd
        elif len(cmd) == 2:
            pom, arg = cmd
        else:
            return False
    except WindowsError:
        return False
    else:
        return pom.strip('"') == peakomatpath

def unregister():
    reg.DeleteKey(reg.HKEY_CLASSES_ROOT,'.lpj')
    pom = reg.CreateKey(reg.HKEY_CLASSES_ROOT, 'peak-o-mat')
    sh = reg.CreateKey(pom, 'shell')
    op = reg.CreateKey(sh, 'open')
    cmd = reg.CreateKey(op, 'command')
    reg.DeleteKey(op, 'command')
    reg.DeleteKey(sh, 'open')
    reg.DeleteKey(pom, 'shell')
    reg.DeleteKey(pom, 'DefaultIcon')
    reg.DeleteKey(reg.HKEY_CLASSES_ROOT, 'peak-o-mat')

def register():
    reg.CreateKey(reg.HKEY_CLASSES_ROOT,'.lpj')
    reg.SetValue(reg.HKEY_CLASSES_ROOT, '.lpj', reg.REG_SZ, 'peak-o-mat')
    pom = reg.CreateKey(reg.HKEY_CLASSES_ROOT, 'peak-o-mat')
    ico = reg.CreateKey(pom, 'DefaultIcon')
    reg.SetValue(pom, 'DefaultIcon', reg.REG_SZ, _q(iconpath))
    sh = reg.CreateKey(pom, 'shell')
    op = reg.CreateKey(sh, 'open')
    cmd = reg.CreateKey(op, 'command')
    reg.SetValue(op, 'command', reg.REG_SZ, '%s %s "%%1"'%(_q(python),_q(peakomatpath)))

if __name__ == '__main__':
    print(check())
    
