import numpy as np
from peak_o_mat import lineshapebase as lb
from peak_o_mat.pickers import Cmd
from peak_o_mat import symbols

def common_peak(x,amp,pos,fwhm):
    """common_peak loaded from userfunc.py"""
    return amp*np.exp(-(np.power(x-pos,2)/(fwhm*fwhm/4.0/np.log(2.0))))

lb.add('CPEAK',
        info=common_peak.__doc__,
        func='common_peak(x, amp, pos, sigma)',
        ptype='PEAK')

symbols.add_constant('G',6.673e-11)

class GFDPicker(list):
    def __init__(self, component, background_cb):
        list.__init__(self,[(Cmd('mx'),self.pos),(Cmd('mxy'),self.amp_sigma)])
        self.f = component
        self.background_cb = background_cb

    def pos(self, x):
        self.f['pos'].value = x

    def amp_sigma(self, xy):
        x, y = xy
        self.f['sigma'].value = np.abs(x - self.f['pos'].value)
        self.f['amp'].value = -(y - self.background_cb(x, ignore_last=True)) * self.f['sigma'].value * np.sqrt(np.e) * np.sign(x - self.f['pos'].value)

lb.add('GFD',
       func='-amp*(x-pos)/(sigma*sigma)*np.exp(-0.5*(pow((x-pos)/sigma,2)))',
       info='First derivative of a Gaussian',
       ptype='PEAK',
       picker=GFDPicker)

