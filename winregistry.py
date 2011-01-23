# Adds entries to the windows registry to register .lpj files with
# peak-o-mat
# This files needs to be in the same location as peak-o-mat.py.
# Whenever you move the peak-o-mat folder, execute this script in order
# to update the registry.
#
#  execute with '--unregister' to remove the registry entries

import os, sys
from distutils.sysconfig import PREFIX

import _winreg as reg

def basepath():
    return os.path.dirname(os.path.abspath(__file__))

iconpath = os.path.join(basepath(), 'peak-o-mat.ico')
peakomatpath = os.path.join(basepath(), 'peak-o-mat.py')
python = os.path.join(PREFIX, 'python.exe')


if len(sys.argv) > 1 and sys.argv[1] == '--unregister':
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
else:
    reg.CreateKey(reg.HKEY_CLASSES_ROOT,'.lpj')
    reg.SetValue(reg.HKEY_CLASSES_ROOT, '.lpj', reg.REG_SZ, 'peak-o-mat')
    pom = reg.CreateKey(reg.HKEY_CLASSES_ROOT, 'peak-o-mat')
    ico = reg.CreateKey(pom, 'DefaultIcon')
    reg.SetValue(pom, 'DefaultIcon', reg.REG_SZ, iconpath)
    sh = reg.CreateKey(pom, 'shell')
    op = reg.CreateKey(sh, 'open')
    cmd = reg.CreateKey(op, 'command')
    reg.SetValue(op, 'command', reg.REG_SZ, '\"%s\" \"%s\" \"%%1\"'%(python,peakomatpath))

