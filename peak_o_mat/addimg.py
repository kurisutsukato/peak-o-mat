#!/usr/bin/python

from wx.tools import img2py
import sys

try:
    arg = '-c -u -n %s -a %s images.py'%(sys.argv[1],sys.argv[2])
except IndexError:
    print 'syntax: %s <bitmap name> <imagefile>'%sys.argv[0]
    sys.exit()

img2py.main(arg.split())
