import wx
from wx.lib.pubsub import pub

from operator import add
import copy
import re
import time

import numpy as np

from threading import Thread, Event

from functools import reduce

from . import misc_ui
from . import model
from . import lineshapebase as lb
from . import fit

from . import weights
from .spec import Spec

class FitController(object):
    def __init__(self, selection_cb, view, interactor):
        self.view = view

        self._model = None
        self._weights = None
        self.exportwhich = 'all'
        self._last_page = None
        self._current_page = None
        self._current_ds = None
        self._current_pl = None
        self._fit_in_progress = False

        self._selection_cb = selection_cb

        self.interactor = interactor
        
        self.view.drawModelButtons()
        interactor.Install(self, self.view)
        
        self.weights = weights.Weights([weights.WeightsRegion(-np.inf,np.inf, 0.1, 0.5, 1)])

    @property
    def selection(self):
        return self._selection_cb()

    def _set_weights(self, w):
        self._weights = w
        self.view.pan_weights.weightsgrid.table.data = self._weights
    def _get_weights(self):
        if self._current_page != 'tab_weights':
            return None
        else:
            return self._weights
    weights = property(_get_weights,_set_weights)

    def _set_model(self, m):
        if self._model is not None:
            self._model.listener = None
        self._model = m
        if self._model is not None:
            self._model.listener = self.refresh_pargrid
        self.view.pan_pars.pargrid.data = model.ModelTableProxy(self._model)
    def _get_model(self):
        return self._model
    model = property(_get_model,_set_model)

    def refresh_pargrid(self):
        print('fitcontroller:refresh_pragrid')
        self.view.pan_pars.pargrid.refresh()
    
    def set_limit_fitrange(self, state):
        self.view.silent = True
        self.view.limitfitrange = state
        pub.sendMessage((self.view.id, 'fitctrl','limitfitrange'),msg=state)
        self.view.silent = False
        
    def page_changed(self, name):
        self._current_page = name
        if name == 'tab_parameters':
            if self.model is not None:
                #self.model.analyze()
                if self.model.ok:
                    self.model.parse()
                    self.model = self.model # this will update the pargrid 
                    self.update_parameter_panel()
        elif name == 'tab_weights':
            pub.sendMessage((self.view.id, 'fitctrl','plot'), msg=None)

        if self._last_page == 'tab_weights':
            self.stop_select_weights()
        self._last_page = name
        wx.CallAfter(self.sync_gui)

    def sync_gui(self, **kwargs):
        if 'fit_in_progress' in kwargs:
            self._fit_in_progress = kwargs['fit_in_progress']

        self.view.enable_fit(not self._fit_in_progress and self.model is not None and self.model.is_filled() and self._current_ds is not None)
        self.view.enable_pick(not self._fit_in_progress and self.model is not None and self._current_ds is not None and self.model.is_autopickable())
        self.view.pan_pars.Enable(self.model is not None and not self.model.is_empty())

    def selection_changed(self, plot, dataset):
        #print('fitcontroller selection changed',plot,dataset)
        self._current_ds = None if len(dataset) != 1 else dataset[0]
        plot_changed = self._current_pl != plot
        self._current_pl = plot

        if self._current_ds is not None:
            dataset = self._current_ds
            if dataset.weights is not None:
                self.weights = dataset.weights
                if self._current_page == 'tab_weights':
                    self.view.canvas.set_handles(self._weights.getBorders())
            else:
                self.weights = copy.deepcopy(self._weights)
            if dataset.mod is not None:
                old_model = self.model
                self.model = copy.deepcopy(dataset.mod)
                self.view.silent = True
                self.view.model = dataset.mod.get_model_unicode()
                if old_model != dataset.mod:
                    self.update_parameter_panel()
                self.view.silent = False
            self.view.loadrange = dataset.xrng
            self.view.limitfitrange = (dataset.limits is not None or dataset.mod is None)

        if plot_changed:
            # TODO
            # gibt es einen grund zu updaten, wenn nur ein anderes ds angewahlt wird?

            self.view.pan_batch.bf_update(self._current_pl, keep_selection=True)

        wx.CallAfter(self.sync_gui)

    def update_parameter_panel(self):
        self.view.pickwhich_choice = ['all']+self.model.tokens.split(' ')

    def clear_weights(self):
        self.weights = weights.Weights([weights.WeightsRegion(-np.inf,np.inf, 0.1, 0.5, 1)])
        self.view.canvas.set_handles(self._weights.getBorders())
        self.weights_changed()

    def set_weights_regions(self, borders):
        borders = borders[:,0].tolist() # only xcoords
        regions = []
        for region in [-np.inf]+borders:
            regions.append(region)
        for n,region in enumerate(borders+[np.inf]):
            regions[n] = [regions[n],region]

        self.weights.newRegions(regions)
        self.view.pan_weights.weightsgrid.table.Update()
        self.weights_changed()
        
    def start_select_weights(self):
        handles = self._weights.getBorders()
        self.view.canvas.set_handles(handles)
        self.view.canvas.state.set('handle','x')
        self.interactor.listen_to_handles()

    def stop_select_weights(self):
        self.interactor.listen_to_handles(False)
        self.view.canvas.set_handles(np.zeros((0,1)))
        self.weights_changed()
        self.view.canvas.state.restore_last()

    def attach_weights(self):
        pub.sendMessage((self.view.id, 'fitctrl','attachweights'),msg=(self.view.pan_weights.weightsgrid.table.data))
    
    def weights_changed(self):
        pub.sendMessage((self.view.id, 'fitctrl','plot'), msg=None)

    def analyze_model(self):
        if self.model is not None:
            msg, pars = self.model.analyze()
            if not self.model.predefined:
                self.message('custom model')
                if len(pars) > 0:
                    msg += '\n\nFit parameters: '+', '.join(pars)
                self.view.pan_model.lab_peakinfo.Value = msg
            else:
                self.view.pan_model.lab_peakinfo.Value = msg
                self.message(msg)
        
    def new_tokens(self, tokens):
        #print 'new tokens', tokens
        mod = model.Model(tokens)
        self.view.silent = True
        self.model = mod
        self.analyze_model()
        self.view.model = tokens
        self.view.silent = False
        
    def add_token(self, newtoken):
        try:
            oldtokens = re.split(r'[\s\+\-\*]+',self.model.tokens)
            if oldtokens == ['CUSTOM']:
                oldtokens = []
        except:
            oldtokens = []
        if newtoken not in lb.lineshapes.background:
            tokens = {}
            for i in oldtokens:
                i = re.sub(r'[0-9]','',i)
                if i not in list(tokens.keys()):
                    tokens[i] = 1
                else:
                    tokens[i] += 1
            if newtoken in tokens:
                num = (tokens[newtoken])+1
            else:
                num = 1
            newtoken += '%d'%num
        oldtokens.append(newtoken)
        tokens = ' '.join(oldtokens).strip()
        self.new_tokens(tokens)

    def load_set_from_model(self, which, xr, pts):
        pub.sendMessage((self.view.id, 'fitctrl','loadset'),msg=(self.model,which,xr,pts))

    def export_pars(self, which, witherrors):
        pub.sendMessage((self.view.id, 'fitctrl','parexport'),
                        msg=(self.model.parameters_as_table(which,witherrors)))

    def start_pick_pars(self):
        self.model = copy.deepcopy(self.model)
        self.view.enable_fit(False)
        self.pickers = []
        if self.view.pickwhich != 0:
            component = self.model[self.view.pickwhich-1]
            component.clear()
            picker = lb.lineshapes[component.name].picker(component,self.model.background)
            self.pickers.append(picker)
        else:
            self.model.clear()
            for component in self.model:
                picker = lb.lineshapes[component.name].picker(component,self.model.background)
                self.pickers.append(picker)
        tmp = [len(p) for p in self.pickers]
        #cumtmp = tmp[:]
        #for i in range(1,len(tmp)):
        #    cumtmp[i] = cumtmp[i]+cumtmp[i-1]
        pub.sendMessage((self.view.id, 'fitctrl','pickpars'), msg=(tmp, reduce(add, self.pickers)))

    def got_pars(self):
        self.view.pan_pars.pargrid.refresh()
        self.view.enable_fit(self.model.is_filled())
        
    def changed_pars(self):
        self.view.enable_fit(self.model.is_filled())
        pub.sendMessage((self.view.id, 'fitctrl','editpars'), msg=None)

    def log(self, msg):
        self.view.log = msg

    def _start_fit(self):
        fitopts = dict([('fittype',self.view.fittype), ('maxiter',self.view.maxiter), \
                        ('stepsize',self.view.stepsize), ('autostep',self.view.autostep)])

        pub.sendMessage((self.view.id, 'fitctrl','fit'),
                                msg=(self.model,
                                 self.view.limitfitrange,
                                 fitopts))

    def export(self):
        pass

    def generate_dataset_check_xexpr(self, xexpr):
        pl,_ = self.selection

        try:
            x = [float(q.strip()) for q in re.split('[,;]',xexpr)]
        except ValueError:
            x_from_regexp = True
            x = []
        else:
            x_from_regexp = False
        # TODO
        # handle case when txt input is not list nor regexp

        withmodel = len([q for q in pl if q.model is not None])

        if x_from_regexp:
            for n,ds in enumerate(pl):
                if ds.model is not None:
                    try:
                        val = re.search(xexpr, ds.name).groups()[0]
                    except (AttributeError, IndexError, re.error):
                        continue
                        #return False
                    else:
                        try:
                            x.append(float(val))
                        except ValueError:
                            continue

        return x,withmodel==len(x)

    def generate_dataset(self, xexpr, yexpr, target):
        print(xexpr, yexpr)

        data = self._batch_parameters(xexpr, yexpr)
        print(data)
        try:
            spec = [data.as_spec(c) for c in sorted(data.keys())]
        except IndexError:
            raise
            return False

        pub.sendMessage((self.view.id, 'generate_dataset'), spec=spec, target=target)
        return True

    def batch_export(self, xexpr, yexpr, errors=False):
        data = self._batch_parameters(xexpr, yexpr)
        table = data.as_table(errors)
        pub.sendMessage((self.view.id, 'generate_grid'), data=table, name=data.name)
        return True

    def _batch_parameters(self, xexpr, yexpr):
        pl,_ = self.selection

        comp,par = yexpr

        data = fit.BatchParameters(name=pl.name, par=par)
        try:
            x = [float(q.strip()) for q in re.split('[,;]',xexpr)]
        except ValueError:
            x_from_regexp = True
        else:
            data.x = x
            x_from_regexp = False
        # TODO
        # handle case when txt input is not list nor regexp

        for n,ds in enumerate(pl):
            if ds.model is not None:
                if x_from_regexp:
                    try:
                        val = re.search(xexpr, ds.name).groups()[0]
                    except (AttributeError, IndexError, re.error):
                        continue
                        #return False
                    else:
                        data.x.append(float(val))
                if comp != 'all':
                    try:
                        val = ds.model[comp][par] # val is instance of model.Var
                    except KeyError:
                        continue
                    else:
                        data[comp].append(n,val) # first access to item creates item if not existent
                else:
                    for c in [q.name for q in ds.model]:
                        try:
                            val = ds.model[c][par] # val is instance of model.Var
                        except KeyError:
                            continue
                        else:
                            data[c].append(n, val)

        #pub.sendMessage((self.view.id, 'generate_grid'),
        #                data=data.as_table(), name='{}:{}'.format(data.name, data.par))
        return data

    def batch_fit(self, baseds_name, initial, order, fitopts):
        pl,ds = self.selection

        # hier gabs mal nen Fehler
        # TODO
        '''
          File "D:\peak-o-mat\peak_o_mat\fitcontroller.py", line 316, in batch_fit
    self._base_ds = base = int(baseds_name[1:])
ValueError: invalid literal for int() with base 10: ''
'''

        self._base_ds = base = int(baseds_name[1:])

        if order == 0:
            rng = list(range(base-1,-1,-1))
        else:
            rng = list(range(base+1, len(pl)))

        job = (pl, rng, base, initial, order, fitopts)
        #self.view.progress_dialog(len(rng))
        self._batch_job = BatchWorker(self.view, job)
        self._batch_job.start()

    def stop_batch_fit(self):
        if hasattr(self, '_batch_job'):
            self._batch_job.join()
            self.message('Batch job canceled.')

    def start_fit(self, limit, fitopts):
        pl,ds = self.selection
        ds = ds[0]
        if limit:
            xr = self.view.canvas.GetXCurrentRange()
            ds.limits = xr
        job = (ds, self.model, fitopts)

        self.sync_gui(fit_in_progress=True)
        WorkerThread(self.view, job).start()

        self.message('Fitting....', blink=True, forever=True)

    def fit_finished(self, msg):
        self.message('')

        self.sync_gui(fit_in_progress=False)

        pub.sendMessage((self.view.id, 'updateview'))

        #self.message('%s: fit finshed'%ds.name)
        #self.log(u'\'{}\' fit to {}\n'.format(ds.model,ds.name))
        #self.log(u'\n'.join(msgs))

        pub.sendMessage((self.view.id, 'fitfinished'))

    def message(self, msg, target=1, blink=False, forever=False):
        event = misc_ui.ShoutEvent(self.view.GetId(), msg=msg, target=target, blink=blink, forever=forever)
        wx.PostEvent(self.view, event)

class BatchWorker(Thread):
    threadnum = 0
    def __init__(self, notify, job):
        Thread.__init__(self)
        self._notify = notify
        self._job = job
        BatchWorker.threadnum += 1
        self.stopreason = Event()

    def join(self):
        self.stopreason.set()
        event = misc_ui.ResultEvent(self._notify.GetId(), endbatch='canceled')
        wx.PostEvent(self._notify, event)
        super(BatchWorker, self).join()

    def run(self):
        msg = []

        pl, rng, base, initial, order, fitopts = self._job
        for n,setnum in enumerate(rng):
            if self.stopreason.is_set():
                return
            event = misc_ui.ResultEvent(self._notify.GetId(), name=pl[setnum].name)
            wx.PostEvent(self._notify, event)
            # TODO
            #
            time.sleep(0.01)

            if initial == 0 or n == 0:
                mod = pl[base].mod.copy()
            pl[setnum].limits = pl[base].limits
            f = fit.Fit(pl[setnum], mod, **fitopts)
            res = f.run()
            mod.update_from_fit(res)
            pl[setnum].model = mod.copy()

        event = misc_ui.ResultEvent(self._notify.GetId(), endbatch='finished')
        wx.PostEvent(self._notify, event)

class WorkerThread(Thread):
    threadnum = 0
    def __init__(self, notify, job):
        Thread.__init__(self)
        self._notify = notify
        self._job = job
        WorkerThread.threadnum += 1
        self.stopreason = Event()

    def join(self):
        self.stopreason.set()
        super(BatchWorker, self).join()

    def run(self):
        ds, mod, fitopts = self._job
        f = fit.Fit(ds, mod, **fitopts)
        res = f.run()
        mod.update_from_fit(res)
        ds.model = mod.copy()

        pars,errors,msg = res

        event = misc_ui.ResultEvent(self._notify.GetId(), end=msg)
        wx.PostEvent(self._notify, event)

if __name__ == '__main__':
    from .fitinteractor import FitInteractor
    from .fitpanel import FitPanel
    from .model import Model
    from .project import Project

    prj = Project()
    prj.load('example.lpj')

    app = wx.App()
    f = wx.Frame(None)
    p = FitPanel(f)
    f.Show()

    def selection():
        return prj[3],[prj[3][2]]

    c = FitController(selection, p, FitInteractor())
    c.model = selection()[1][0].model
    app.MainLoop()
