import os, sys
from distutils.sysconfig import PREFIX, EXEC_PREFIX

import _winreg as reg

iconpath = os.path.join(EXEC_PREFIX, 'peak-o-mat', 'peak-o-mat.ico')
pythonpath = os.path.join(EXEC_PREFIX, 'python.exe')
peakomatpath = os.path.join(EXEC_PREFIX, 'Scripts','peak-o-mat.py')
batchpath = os.path.join(EXEC_PREFIX, 'Scripts','peak-o-mat.bat')
desktop = get_special_folder_path("CSIDL_DESKTOPDIRECTORY")
python = 'start ' + os.path.join(PREFIX, 'python.exe')

template = """\
@echo off

%s %s %%1
"""

if sys.argv[1] == '-install':
    print "Creating", batchpath
    f = open(batchpath, 'w')
    f.write(template % (python, peakomatpath))
    f.close()

    os.chdir(desktop)
    try:
        create_shortcut(batchpath, 'This is peak-o-mat', 'peak-o-mat.lnk', '', 'c:\\', iconpath)
    except:
        print 'could not create desktop shortcut'

    reg.CreateKey(reg.HKEY_CLASSES_ROOT,'.lpj')
    reg.SetValue(reg.HKEY_CLASSES_ROOT, '.lpj', reg.REG_SZ, 'peak-o-mat')
    pom = reg.CreateKey(reg.HKEY_CLASSES_ROOT, 'peak-o-mat')
    ico = reg.CreateKey(pom, 'DefaultIcon')
    reg.SetValue(pom, 'DefaultIcon', reg.REG_SZ, iconpath)
    sh = reg.CreateKey(pom, 'shell')
    op = reg.CreateKey(sh, 'open')
    cmd = reg.CreateKey(op, 'command')
    reg.SetValue(op, 'command', reg.REG_SZ, '\"%s\" \"%%1\"'%batchpath)

    # open the explorer showing the peak-o-mat installation folder
    os.startfile(os.path.join(EXEC_PREFIX, 'peak-o-mat'))

elif sys.argv[1] == '-remove':
    try:
        os.unlink(batchpath)
    except:
        pass

    os.chdir(desktop)
    try:
        os.unlink('peak-o-mat.lnk')
    except:
        pass

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
