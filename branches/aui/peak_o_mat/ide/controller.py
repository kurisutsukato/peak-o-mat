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
import numpy as np

from ..symbols import pom_globals
from ..appdata import configdir
from peak_o_mat import config

logger = logging.getLogger('pom')

prjscripts = []

class DoesExist(Exception):
    pass

class ListModel(dv.DataViewIndexListModel):
    def __init__(self):
        dv.DataViewIndexListModel.__init__(self)
        self._data = []

    def RowChanged(self, row):
        self.ItemChanged(self.GetItem(row))

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

    def names(self):
        for d in self.data:
            yield d[1]

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
        self._data[:] = sorted(self._data, key=itemgetter(1))
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
            logger.warning('getvaluebyrow index error row {}, col {}'.format(row, col))
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

    def GetColumnCount(self):
        return 2

    def GetColumnType(self, col):
        return ['bool', 'string'][col]

class ProjectData(ListModel):
    def get_source(self):
        src = []
        for act, name, val in self.data:
            if act:
                src.append(val)
        return src

    def append_from_local(self, srcmodel, row, newname=None):
        act, name = srcmodel.data[row]
        if newname is not None:
            if newname[-3:] != '.py':
                newname = newname.replace('.', '')
                newname += '.py'
            if newname in self.names():
                raise DoesExist
        with open(os.path.join(srcmodel.basepath, name), 'r') as fp:
            script = fp.read()
            self.append([act, name if newname is None else newname, script])

    def update(self, row, val):
        self.data[row][2] = val

    def load(self, row):
        return self.data[row][2]

class LocalData(ListModel):
    def __init__(self, basepath):
        super(LocalData, self).__init__()
        self.basepath = basepath

        self.reload()

    def get_source(self):
        src = []
        for n, (act, name) in enumerate(self.data):
            if act:
                src.append(self.load(n))
        return src

    def reload(self, selectedrow=None):
        if self.basepath is not None:
            try:
                fls = [os.path.basename(q) for q in glob(os.path.join(self.basepath, '*.py'))]
            except OSError:
                raise

        if fls == [q[1] for q in self.data]:
            return

        if selectedrow is not None:
            selectedname = self.data[selectedrow][1]
            if len(fls) == len(self.data):
                if not self.data[selectedrow][1] in fls:
                    for n, name in enumerate(fls):
                        if name not in self:
                            selectedname = name
                self.data = [[False, q] for q in fls]
                selectedrow = self.index(selectedname)
            else:
                self.data = [[False, q] for q in fls]
                try:
                    selectedrow = self.index(selectedname)
                except ValueError:
                    selectedrow = max(0, selectedrow-1)
            return selectedrow
        else:
            self.data = [[False, q] for q in fls]

    def path(self, row):
        return os.path.join(self.basepath, self.data[row][1])

    def append_from_embedded(self, srcmodel, row, newname=None):
        act, name, script = srcmodel.data[row]
        if newname is not None:
            name = newname
        if name[-3:] != '.py':
            name = name.replace('.', '')
            name += '.py'
        if os.path.exists(os.path.join(self.basepath, name)):
            raise DoesExist
        else:
            with open(os.path.join(self.basepath, name), 'w') as fp:
                fp.write(script)
                self.append([act, name])

    def load(self, row):
        try:
            return open(os.path.join(self.basepath, self.data[row][1])).read()
        except OSError:
            return None

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
            pub.sendMessage((self.controller.view.instid, 'updateview'), full=True)

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
        self.do_not_listen = False

        scriptpath = config.get('general', 'userfunc_dir')
        self.script_path = scriptpath if os.path.exists(scriptpath) and os.path.isdir(scriptpath) else None
        if interactor is not None:
            interactor.Install(self, view)
        self.interpreter = Interpreter(parent_controller)

        self.model = {
            'prj': ProjectData(),
            'local': LocalData(self.script_path)
        }
        self.edit_mode = None   # maybe 'prj' or 'local'

        self.view.set_model('local', self.model['local'])
        self.view.set_model('prj', self.model['prj'])

        self.view.enable_local(self.script_path is not None)
        self.view.run()

    def get_activated_symbols(self):
        symbs = {}
        for source in self.model['local'].get_source()+self.model['prj'].get_source():
            try:
                m = types.ModuleType('dynamic')
                exec(source, m.__dict__, m.__dict__)
            except:
                pass
            else:
                for name in dir(m):
                    sym = getattr(m, name)
                    if type(sym) in [types.FunctionType, types.ModuleType, np.ufunc,
                                     types.BuiltinFunctionType, types.BuiltinMethodType]:
                        symbs.update({name: sym})
        return symbs

    def run(self, source):
        #self.register_symbols(source)

        tmp = sys.stdout
        sys.stdout = self.interpreter
        self.interpreter.runsource(source, symbol='exec')
        sys.stdout = tmp
        return self.interpreter.getresult()

    def rename(self, model, oldval, row):
        logger.debug('renaming {}: {}->{}'.format(self.edit_mode, oldval, model.data[row][1]))
        if hasattr(model, 'basepath'):
            try:
                os.rename(os.path.join(model.basepath, oldval),
                          os.path.join(model.basepath, model.data[row][1]))
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
        ctrl = getattr(self.view, 'lst_{}'.format(self.edit_mode))
        if self.edit_mode == 'prj':
            self.model[self.edit_mode].update(ctrl.selected, val)
        elif self.edit_mode == 'local':
            with open(self.model[self.edit_mode].path(ctrl.selected), 'w', encoding='utf-8') as fp:
                fp.write(val)
        self.model[self.edit_mode].data[ctrl.selected][0] = False
        self.model[self.edit_mode].RowChanged(ctrl.selected)

    def editor_push_file(self, scope, row):
        self.do_not_listen = True
        try:
            cont = self.model[scope].load(row)
        except OSError:
            self.view.editor.ChangeValue('unable to read file')
            self.view.show_editor(False)
        else:
            self.view.editor.ChangeValue(cont)
        self.do_not_listen = False

    def delete_entry(self, scope, row):
        model = self.model[scope]
        logger.debug('delete row {}'.format(row))
        if scope == 'local':
            try:
                os.unlink(model.path(row))
            except OSError:
                raise
            else:
                model.pop(row)
        else:
            model.pop(row)

    def add_entry(self, scope):
        model = self.model[scope]
        count = 0
        for name in model.names():
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
                open(os.path.join(model.basepath, newname), 'w')
            except OSError:
                raise
            else:
                row = model.append([False, newname])
        else:
            row = model.append([False, newname, ''])
        return row

def test():
    from peak_o_mat import config
    m = LocalData(config.get('general', 'userfunc_dir'))
    m.reload(1)
    print(m.data)


if __name__ == '__main__':
    #import wx
    #from .view import View
    #from .interactor import Interactor

    #app = wx.App()
    #c = Controller(None, View(None), Interactor())
    #app.MainLoop()

    test()
