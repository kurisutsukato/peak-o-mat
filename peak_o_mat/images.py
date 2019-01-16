import wx
from . import misc

def get_bmp(image):
    bmp = wx.Bitmap(misc.basepath('images',image))
    assert bmp is not None
    return bmp

def get_img(image):
    return wx.Image(misc.basepath('images',image))
