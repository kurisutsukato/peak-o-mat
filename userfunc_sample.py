from peak_o_mat import peaks

class DGAPicker(list):
    def __init__(self, component, background_cb):
        list.__init__(self, [(peaks.Cmd('xy'),self.amp_pos),(peaks.Cmd('mx'),self.fwhm),
                             (peaks.Cmd('mxy'),self.amp_pos2)])
        self.f = component
        self.background_cb = background_cb
        
    def amp_pos(self, xy):
        x, y = xy
        if not hasattr(self, 'bg'):
            self.bg = self.background_cb(x)
            self.f['pos2'].value = self.f['amp2'].value = 0
            self.f['pos'].value = x
        self.f['amp'].value = y-self.bg

    def amp_pos2(self, xy):
        x, y = xy
        self.f['pos2'].value = x
        self.f['amp2'].value = y-self.bg
        
    def fwhm(self, x):
        self.f['fwhm'].value = x-self.f['pos'].value


peaks.add('DGA',
          func='amp*exp(-(power(x-pos,2)/(fwhm*fwhm/2.0)))+amp2*exp(-(power(x-pos2,2)/(fwhm*fwhm/2.0)))',
          info='a double gaussian',
          ptype=peaks.ptype.PEAK,
          picker=DGAPicker)
