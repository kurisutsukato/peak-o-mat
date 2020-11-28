from scipy import signal
import numpy as np

from .spec import Spec
from .misc import PomError

def sg_filter(sp, window, order):
    newy = signal.savgol_filter(sp.y, window, order)

    return Spec(sp.x, newy, 'SGfilt_%s' % sp.name)

from scipy.interpolate import splrep, splev, UnivariateSpline

def spline_filter(sp, smoothing, sample=None):
    if np.any(np.diff(sp.x)<=0.0):
        raise PomError('{}: X-values must be monotonously increasing.'.format(sp.name))
    try:
        spl = UnivariateSpline(sp.x, sp.y, s=smoothing/len(sp.x))
    except TypeError as er:
        raise PomError('error: %s' % er)
    else:
        if type(sample) == int and sample > 1:
            nx = np.linspace(sp.x.min(),sp.x.max(),sample)
            sp = Spec(nx, spl(nx), 'spline_{}'.format(sp.name))
        else:
            sp = Spec(sp.x, spl(sp.x), 'spline_{}'.format(sp.name))
        return sp

def fft_filter(sp, noise_threshold=None):
    ft = np.fft.rfft(sp.y)
    freqs = np.fft.rfftfreq(len(sp.y), sp.x[1] - sp.x[0])  # Get frequency axis from the time axis
    if noise_threshold is not None:
        mags = abs(ft)  # We don't care about the phase information here
        phase = np.arctan2(ft.imag, ft.real) * 180 / np.pi
        phase[np.abs(mags)/np.max(np.abs(mags))<noise_threshold] = 0.0
        return Spec(freqs, mags, 'fftamp_{}'.format(sp.name)), \
               Spec(freqs, phase, 'fftphase_{}'.format(sp.name))
    else:
        return Spec(freqs, ft.real, 'fftreal_{}'.format(sp.name)), \
               Spec(freqs, ft.imag, 'fftimag_{}'.format(sp.name))

def autocorrelation_filter(sp):
    y = np.correlate(sp.y,sp.y,mode='full')[-len(sp.y):]

    return Spec(sp.x, y, 'autocrr._{}'.format(sp.name))

def mavg_filter(sp, avg):
    #TODO: interpolate/bin before averaging, replace loop by stride tricks
    l = len(sp.y)
    newy = np.zeros((0,l-avg))
    for i in range(avg):
        newy = np.concatenate((newy,np.reshape(sp.y[i:l-avg+i], (1,l-avg))))
    newy = newy.sum(axis=0)/avg
    s = int(avg/2)
    e = avg-s
    newx = sp.x[s:-e]
    return Spec(newx, newy, '%dpt_avg_%s'%(avg, sp.name))

def emavg_filter(sp, win):
    # makes no sense for spectroscopy
    alpha = 2 /(win + 1)
    b = [alpha]
    a = [1, alpha-1]
    zi = signal.lfiltic(b, a, sp.y[0:1], [0])
    newy = signal.lfilter(b, a, sp.y, zi=zi)[0]
    return Spec(sp.x, newy, '%dpt_eavg_%s' % (win, sp.name))

def wmavg_filter(sp, step_size=0.05, width=1):
    # makes no sense for spectroscopy
    bin_centers = np.arange(np.min(sp.x),np.max(sp.x)-0.5*step_size,step_size)+0.5*step_size
    bin_avg = np.zeros(len(bin_centers))

    def gaussian(x,amp=1,mean=0,sigma=1):
        return amp*np.exp(-(x-mean)**2/(2*sigma**2))

    for index in range(0,len(bin_centers)):
        bin_center = bin_centers[index]
        weights = gaussian(sp.x,mean=bin_center,sigma=width)
        bin_avg[index] = np.average(sp.y,weights=weights)

    return Spec(bin_centers,bin_avg, 'wmavg_%s'%(sp.name))

from numpy.lib.stride_tricks import as_strided

def moving_weighted_average(x, y, step_size=.9, steps_per_bin=10,
                            weights=None):
    # makes no sense for spectroscopy
    # This ensures that all samples are within a bin
    number_of_bins = int(np.ceil(np.ptp(x) / step_size))
    bins = np.linspace(np.min(x), np.min(x) + step_size*number_of_bins,
                       num=number_of_bins+1)
    bins -= (bins[-1] - np.max(x)) / 2
    bin_centers = bins[:-steps_per_bin] + step_size*steps_per_bin/2

    counts, _ = np.histogram(x, bins=bins)
    vals, _ = np.histogram(x, bins=bins, weights=y)
    bin_avgs = vals / counts
    n = len(bin_avgs)
    windowed_bin_avgs = as_strided(bin_avgs,
                                   (n-steps_per_bin+1, steps_per_bin),
                                   bin_avgs.strides*2)

    weighted_average = np.average(windowed_bin_avgs, axis=1, weights=weights)

    return bin_centers, weighted_average

if __name__ == '__main__':
    x = np.linspace(4,9,23)
    y = x*1
    moving_weighted_average(x, y, 0.3, steps_per_bin=3)
