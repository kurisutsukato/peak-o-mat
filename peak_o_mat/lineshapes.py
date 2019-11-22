import numpy as np
    
from scipy.special import wofz

from scipy.integrate import trapz

from . import pickers
from .lineshapebase import add

def lbstep(x,amp,pos,sigma,sigmap=100.0,rng=5,pts=1000):
    """\
lorentian broadened step function according to

Quantum well interface broadening effects
Vladimir Gavryushin
Proc. SPIE  6596, Advanced Optical Materials, Technologies, and Devices, 659619 (January 25, 2007);   doi: 10.1117/12.726499

caution: this function implies numerical convolution which is
computationally intensive.  For accurate results you should run
convergence tests taking into account the 'rng' and 'pts' parameters
in the function definition in lineshapes.py.

    """ 
    if len(x) == 1:
        dx = x[0]*0.1
    else:
        dx = x[-1]-x[0]
    up = x[-1]+rng*dx
    lo = x[0]-rng*dx
    f = amp/np.pi
    xp = np.linspace(lo,up,pts)[:,np.newaxis]
    s2 = np.power(sigma,2)
    i = trapz(sigma/(np.power(x-xp,2)+s2)/(1+np.exp(-sigmap*(xp-pos))), xp, axis=0)
    return f*i

def gbstep(x,amp,pos,sigma,sigmap=100,rng=5,pts=1000):
    """\
gaussian broadened step function according to

Quantum well interface broadening effects
Vladimir Gavryushin
Proc. SPIE  6596, Advanced Optical Materials, Technologies, and Devices, 659619 (January 25, 2007);   doi: 10.1117/12.726499

caution: this function implies numerical convolution which is
computationally intensive.  For accurate results you should run
convergence tests taking into account the 'rng' and 'pts' parameters
in the function definition in lineshapes.py.

    """
    f = amp/np.sqrt(2*np.pi)/sigma
    s2 = 2*np.power(sigma,2)
    if len(x) == 1:
        dx = x[0]*0.1
    else:
        dx = x[-1]-x[0]
    up = x[-1]+rng*dx
    lo = x[0]-rng*dx
    xp = np.linspace(lo,up,pts)[:,np.newaxis]
    i = trapz(np.exp(-np.power(x-xp,2)/s2)/(1+np.exp(-sigmap*(xp-pos))), xp, axis=0)
    return f*i

def pearson7(x, amp=1.0, pos=0.0, sigma=1.0, expon=1.0):
    """Pearson7 lineshape, using the wikipedia definition:

    pearson7(x, pos, sigma, expon) =
      amp*(1+arg**2)**(-expon)/(sigma*beta(expon-0.5, 0.5))

    where arg = (x-pos)/sigma
    and beta() is the beta function.
    """
    arg = (x-pos)/sigma
    scale = amp * gamfcn(expon)/(gamfcn(0.5)*gamfcn(expon-0.5))
    return  scale*(1+arg**2)**(-expon)/sigma    
    
def voigt(x,amp,pos,fwhm,shape):
    """\
Voigt lineshape

V(x,sig,gam) = Re(w(z))/(sig*sqrt(2*pi))
z = (x+i*gam)/(sig*sqrt(2))

where Re(w(z)) is the real part of the Faddeeva function
    """
    tmp = 1/wofz(np.zeros((len(x))) +1j*np.sqrt(np.log(2.0))*shape).real
    return tmp*amp*wofz(2*np.sqrt(np.log(2.0))*(x-pos)/fwhm+1j*np.sqrt(np.log(2.0))*shape).real

def sdec(x, amp, tau, beta):
    """\
Stretched exponential decay

y = amp*np.exp(-np.power(x/tau,beta))
    """
    y = amp*np.exp(-np.power(x/tau,beta))*(x>=0)
    tmp = np.zeros(x.shape,dtype=float)
    mask = np.compress(np.isfinite(y),np.arange(len(y),dtype=int))
    np.put(tmp, mask, np.compress(np.isfinite(y),y))
    return tmp

add('CB',
    func='const+0*x',
    info='Constant background',
    picker=pickers.CBPicker, 
    ptype='BACKGROUND')

add('LB',
    func='const+lin*x',
    info='Linear background',
    picker=pickers.LBPicker, 
    ptype='BACKGROUND')

add('QB',
    func='a*x**2+b*x+c',
    info='Quadratic background',
    picker=pickers.QBPicker, 
    ptype='BACKGROUND')

add('GA',
    func='amp*np.exp(-(np.power(x-pos,2)/(fwhm*fwhm/4.0/np.log(2.0))))',
    info='Symmetric gaussian lineshape',
    picker=pickers.LOPicker,
    ptype='PEAK')

add('LO',
    func='amp/(1+np.power((x-pos)/(fwhm/2.0),2))',
    info='Symmetric lorentzian lineshape',
    picker=pickers.LOPicker, 
    ptype='PEAK')

add('FAN',
    func='amp*np.power((1+(x-pos)/(fwhm/2)*shape),2)/(1+np.power((x-pos)/(fwhm/2),2))',
    info='Fano lineshape',
    picker=pickers.FANPicker, 
    ptype='PEAK')

add('VO',
    func='voigt(x,amp,pos,fwhm,shape)',
    info=voigt.__doc__, 
    picker=pickers.FANPicker, 
    ptype='PEAK')

add('PSV',
    func='amp*(shape*np.exp(-2/np.pi*np.power((x-pos)/(fwhm/2),2))+(1-shape)/(1+np.power((x-pos)/(fwhm/2),2)))',
    info='Pseudo voigt profile',
    picker=pickers.FANPicker, 
    ptype='PEAK')

add('DEC',
    func='amp*np.exp(-x/tau)',
    info='Exponential decay',
    ptype='EXP',
    picker=pickers.EXPPicker)

add('RISE',
    func='1.0-np.exp(-x/tau)',
    info='Exponential rise',
    ptype='EXP')

add('SDEC',
    func='sdec(x,amp,tau,beta)',
    info=sdec.__doc__,
    ptype='EXP',
    picker=pickers.SEXPPicker)

add('LBSTP',
    info=lbstep.__doc__,
    func='lbstep(x, amp, pos, sigma)',
    picker=pickers.STEPPicker,
    ptype='STEP')

add('GBSTP',
    info=gbstep.__doc__,
    func='gbstep(x, amp, pos, sigma)',
    picker=pickers.STEPPicker,
    ptype='STEP')

add('FERMI', 
    info='Fermi function with abscissa in eV',
    func='amp/(np.exp(-(x-energy)/(c_kb/c_e*T))+1)',
    picker=pickers.FERMIPicker,
    ptype='STEP')
    
add('CTLMRF',
    func='Rs/(np.pi*2)*(np.log((50.0+x*3)/50)+Lt*(1.0/(50+x*3)+0.02))',
    info='Model for circular TLM pattern. The inner radius is constant \n'
         'r = 50um, the outer increases in steps of 3um, smallest gap 3um',
    ptype='MISC')

add('CTLMPD',
    func='Rs/(np.pi*2)*(np.log(100/(91-x*3))+Lt*(1.0/(91-x*3)+0.01))',
    info = 'Model for circular TLM pattern. TLM mask.\n'
           'The outer radius is constant r = 100um\n'
           'the inner decreases in steps of 3um, smallest gap 12um',
    ptype='MISC')

add('CTLM',
    func='Rs/(np.pi*2)*(np.log(100/(91-x*3))+Lt*(1.0/(91-x*3)+0.01))',
    info = 'Model for circular TLM pattern. TLM mask.\n'
           'The outer radius is constant r = 100um\n'
           'the inner decreases in steps of 3um, smallest gap 12um',
    ptype='MISC')


