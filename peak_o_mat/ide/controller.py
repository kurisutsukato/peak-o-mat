__author__ = 'kristukat'

import wx.dataview as dv
from pubsub import pub
import logging
from io import StringIO
from operator import itemgetter
from glob import glob
import os, re, sys
import code
import types

from ..symbols import pom_globals
from ..appdata import configdir

logger = logging.getLogger('pom')

prjscripts = []

class SortList(list):
    def _append(self, item):
        super(SortList, self).append(item)
        self[:] = sorted(self, key=itemgetter(1))

    def _index(self, item):
        for n, i in enumerate(self):
            if i[1] == item:
                return n
        raise IndexError

class LocalScripts(SortList):
    def __init__(self, basepath):
        self.basepath = basepath
        fls = glob(os.path.join(basepath, '*.py'))

        super(LocalScripts, self).__init__([[False, os.path.basename(q)] for q in fls])

    def append(self, item):
        super(SortList, self).append(item)
        self[:] = sorted(self, key=itemgetter(1))
        return self.index(item)

    def load(self, row):
        return open(os.path.join(self.basepath, self[row][1])).read()

    def names(self):
        for a, name in self:
            yield name

    def path(self, row):
        return os.path.join(self.basepath, self[row][1])

class PrjScripts(SortList):
    def load(self, row):
        return self[row][2]

    def append(self, item):
        super(SortList, self).append(item)
        self[:] = sorted(self, key=itemgetter(1))
        return self.index(item)

    def names(self):
        for a, name, script in self:
            yield name

    def update(self, row, val):
        self[row][2] = val

class ListModel(dv.DataViewIndexListModel):
    def __init__(self, data):
        dv.DataViewIndexListModel.__init__(self, len(data))
        self._data = data

    def Reset(self, length=None):
        if length is None:
            super(ListModel, self).Reset(len(self.data))
        else:
            super(ListModel, self).Reset(length)

    def __contains__(self, item):
        for row in self.data:
            if row[1] == item:
                return True
        return False

    def pop(self, row):
        self._data.pop(row)
        self.Reset(len(self._data))

    def index(self, item):
        for n, row in enumerate(self.data):
            if row[1] == item:
                return n
        raise ValueError('\'{}\' not in list'.format(item))

    def append(self, item):
        self._data.append(item)
        self.Reset(len(self._data))
        return self._data.index(item)

    def sort(self):
        self._data[:] = sorted(self._data, key=itemgetter(1))
        self.Reset(len(self._data))

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data):
        self._data = data
        self.Reset(len(data))

    def GetValueByRow(self, row, col):
        try:
            return str(self._data[row][col]) if col > 0 else self._data[row][col]
        except IndexError:
            print('getvaluebyrow index error row {}, col {}'.format(row, col))
            return 0

    def SetValueByRow(self, value, row, col):
        if col == 0:
            self._data[row][col] = bool(value)
        else:
            for _r in self._data:
                if _r[1] == str(value):
                    return False
            self._data[row][col] = str(value)
        return True

    def update(self):
        self.Reset(len(self.data))

    def GetColumnCount(self):
        return 2

    def GetColumnType(self, col):
        return ['bool', 'string'][col]

class Locals(dict):
    def __init__(self, *args):
        self.autocall = []
        super(Locals, self).__init__(*args)

    def __getitem__(self, name):
        if name in self.autocall:
            return dict.__getitem__(self, name)()
        else:
            return dict.__getitem__(self, name)

    def add(self, name, val, autocall=False):
        self[name] = val
        if autocall:
            self.autocall.append(name)

    def __setitem__(self, name, val):
        if name in self.autocall:
            raise Exception('overwriting \'%s\' not allowed' % name)
        else:
            dict.__setitem__(self, name, val)

class Interpreter(code.InteractiveInterpreter):
    def __init__(self, controller):
        self.controller = controller
        self.errline = None

        code.InteractiveInterpreter.__init__(self, self.init_locals())

        self.out = StringIO()

    def init_locals(self):
        locs = Locals(locals())
        locs.add('add_plot', self.controller.add_plot)
        locs.add('add_set', self.controller.add_set)
        locs.add('project', self.controller.project)
        locs.add('controller', self.controller)

        def _get_model():
            return self.controller.fit_controller.model

        locs.add('model', _get_model, True)

        def _update_view():
            #TODO: should not be necesary anymore: # self.controller.update_tree()
            self.controller.update_plot()

        locs.add('sync', _update_view)

        def _get_active_set():
            return self.controller.active_set

        locs.add('aset', _get_active_set, True)
        locs.add('active_set', _get_active_set, True)
        # locs.add('intro', intro, False)
        return locs

    def write(self, text):
        self.out.write(text)
        mat = re.match(r'.+, line (\d+)\D+', text)
        if mat is not None:
            self.errline = int(mat.groups()[0]) - 1

    def getresult(self):
        ret = self.out.getvalue(), self.errline
        self.out = StringIO()
        return ret

class Controller(object):
    def __init__(self, parent_controller, view=None, interactor=None):
        self.view = view
        if interactor is not None:
            interactor.Install(self, view)
        self.interpreter = Interpreter(parent_controller)

        self.model = {
            'prj': ListModel(PrjScripts([])),
            'local': ListModel(LocalScripts(os.path.join(configdir(), 'userfunc')))
        }
        self.edit_mode = None   # maybe 'prj' or 'local'

        self.view.set_model('local', self.model['local'])
        self.view.set_model('prj', self.model['prj'])

        self.view.run()

    def register_symbols(self, source):
        '''das braucht man wohl um im code editor funktionen zu definieren,
        die man spaeter zum fitten nehmen kann'''

        try:
            m = types.ModuleType('dynamic')
            # m = imp.new_module('dynamic')
            exec(source, {}, m.__dict__)
        except:
            return
        else:
            for name in dir(m):
                sym = getattr(m, name)
                if type(sym) in [types.FunctionType]: # TODO:, types.ModuleType, np.ufunc]:
                    pom_globals.update({name: sym})

    def run(self, source):
        self.register_symbols(source)

        tmp = sys.stdout
        sys.stdout = self.interpreter
        self.interpreter.runsource(source, symbol='exec')
        sys.stdout = tmp
        return self.interpreter.getresult()

    def rename(self, model, oldval, row):
        logger.debug('renaming {}: {}->{}'.format(self.edit_mode, oldval, model.data[row][1]))
        if hasattr(model.data, 'basepath'):
            try:
                os.rename(os.path.join(model.data.basepath, oldval),
                          os.path.join(model.data.basepath, model.data[row][1]))
            except IOError:
                return False
            return True
        else:
            return True

    def load_from_project(self, project_data):
        self.model['prj'].data[:] = []
        reg = {}
        for name, cont in project_data:
            if name not in reg.keys():
                reg[name] = 0
            else:
                reg[name] += 1
            if reg[name] > 0:
                name += '-{}'.format(reg[name])
            if name[-3:] != '.py':
                name = name.replace('.','')
                name += '.py'

            self.model['prj'].data.append([False, name, cont])
        self.model['prj'].Reset()

    def save_to_project(self):
        logger.debug('save to project')
        return [[q,p] for _,q,p in self.model['prj'].data]

    def model_update(self):
        val = self.view.editor.GetText()
        ctrl = getattr(self.view,'lst_{}'.format(self.edit_mode))
        if self.edit_mode == 'prj':
            self.model[self.edit_mode].data.update(ctrl._selected, val)
        elif self.edit_mode == 'local':
            with open(self.model[self.edit_mode].data.path(ctrl._selected), 'w', encoding='utf-8') as fp:
                fp.write(val)

    def editor_push_file(self, scope, row):
        data = self.model[scope].data
        cont = data.load(row)
        self.view.editor.ChangeValue(cont)

    def delete_entry(self, scope, row):
        model = self.model[scope]
        logger.debug('delete row {}'.format(row))
        if scope == 'local':
            try:
                os.unlink(model.data.path(row))
            except OSError:
                raise
            else:
                model.pop(row)
        else:
            model.pop(row)

    def add_entry(self, scope):
        model = self.model[scope]
        count = 0
        for name in model.data.names():
            name = name.rstrip('.py')
            try:
                name, num = name.split('-')
            except ValueError:
                num = 0
            if name == 'untitled':
                count = max(count, int(num) + 1)
        if count > 0:
            newname = 'untitled-{}.py'.format(count)
        else:
            newname = 'untitled.py'
        if scope == 'local':
            try:
                open(os.path.join(model.data.basepath, newname), 'w')
            except OSError:
                raise
            else:
                row = model.append([False, newname])
        else:
            row = model.append([False, newname, ''])
        return row

if __name__ == '__main__':
    import wx
    from .view import View
    from .interactor import Interactor

    app = wx.App()
    Controller(View(None), Interactor())
