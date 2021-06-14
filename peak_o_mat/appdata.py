try:
    import winreg
except ImportError:
    WIN = False
else:
    WIN = True
    
import os, sys

## The registry keys where the SHGetFolderPath values appear to be stored
#r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
#r"HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"

def homedirectory():
    if WIN:
        # on Win32, but no Win32 shell com available, this uses
        # a direct registry access, likely to fail on Win98/Me
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
		r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
        try:
            # should check that it's valid? How?
            #print 'home dir from registry'
            return winreg.QueryValueEx( k, "AppData" )[0]
        finally:
            winreg.CloseKey( k )       
    for name in ['appdata', 'home']:
        if name in os.environ:
            #print 'home dir from environment'
            return os.environ[name]
    # well, someone's being naughty, see if we can get ~ to expand to a directory...
    possible = os.path.abspath(os.path.expanduser( '~/' ))
    if os.path.exists(possible):
        #print 'home dir from expanduser'
        return possible
    raise OSError('Unable to determine user\'s application-data directory')
    
def configdir():
    if WIN:
        pomdir = 'peak-o-mat'
    else:
        pomdir = '.peak-o-mat'
    return os.path.join(homedirectory(), pomdir)

def logfile():
    return os.path.join(configdir(), 'peak-o-mat.log')

if __name__ == "__main__":
    print(configdir())
    
