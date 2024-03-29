import operator
import re
from re import Scanner
import sys

import copy as cp
from operator import mul, add
from functools import reduce
import logging

import numpy as np
# np.seterr(divide='ignore')

from . import lineshapebase
from .pickers import DummyPicker

from .symbols import pom_globals
from .filters import bg_snip
#from .fit import FitModel, O

class UnknownToken(Exception):
    pass


tokre = re.compile(r"([,+\s]*)([A-Z]+[0-9]*)")

logger = logging.getLogger('pom')


def ireduce(func, iterable, init=None):
    iterable = iter(iterable)
    if init is None:
        init = next(iterable)
        yield init
    else:
        try:
            init = func(init, next(iterable))
            yield init
        except StopIteration:
            yield init
    for item in iterable:
        init = func(init, item)
        yield init


class ModelTableProxy(list):
    """provides a list-type read-write interface to the model object
    used e.g. by the parameter grid
    """

    class Constant(object):
        __const__ = True

        def __init__(self, name, area):
            self.name = name
            self.area = area

        def __getitem__(self, item):
            if item > 1:
                return 0
            elif item == 0:
                return self.name
            elif item == 1:
                return self.area()

        def __setitem__(self, item, value):
            return

    class Variable(object):
        attrmap = [None, 'value', 'error', 'constr', 'amin', 'amax', None]
        types = [str, float, float, int, float, float, float]

        def __init__(self, fname, vname, var):
            self.var = var
            self.name = '%s:%s' % (fname, vname)

        def __getitem__(self, item):
            if item == 0:
                return self.name
            else:
                try:
                    return getattr(self.var, self.attrmap[item])
                except:
                    print('var getitem', item)

        def __setitem__(self, item, value):
            if item in [1, 3, 4, 5]:
                try:
                    setattr(self.var, self.attrmap[item], self.types[item](value))
                except ValueError:
                    return

    def __init__(self, model):
        if model is None:
            return
        self.model = model
        a = {}

        # the following code is needed to add the :area information for
        # each peak-like feature
        counts = []
        for component in model:
            counts.append(len(component))
            for key, par in component.items():
                a[par.count] = component.name, key, par

        if len(counts) > 0:
            counts = ireduce(operator.add, counts)

        for name, key, par in list(a.values()):
            # if not par.hidden:
            self.append(self.Variable(name, key, par))

        for ins, component in reversed(list(zip(list(counts), model))):
            if component.area() == np.inf:
                continue
            self.insert(ins, self.Constant('%s:area' % (component.name), component.area))

    def _get_shape(self):
        return len(self), 6

    shape = property(_get_shape)


class BaseModel(list):
    """
    List type class to store the fit model and parameters. The list items are
    the model's 'components', e.g. CB, GA, etc.
    """

    def __init__(self, tokens, listener=None):
        """
tokens: a space separated list of valid function symbols
"""
        list.__init__(self)
        self.ok = False  # True if check_model() was succesful
        self.parser = None
        self.parsed = False
        self.func = None
        self.listener = listener
        self.tokens = ''

        if tokens.isupper() or tokens == '' or lineshapebase.lineshapes.known(tokens):
            self.predefined = True
            self.tokens = tokens.strip()
        else:
            self.predefined = False
            self.tokens = 'CUSTOM'
            self.func = tokens.strip()

    def __repr__(self):
        return '<%s.%s at %s>' % (
            self.__class__.__module__,
            self.__class__.__name__,
            hex(id(self))
        )

    def __str__(self):
        if self.tokens == 'CUSTOM':
            return self.func
        else:
            return ' '.join([str(q) for q in self])

    def keys(self):
        return [q.name for q in self]

    def copy(self):
        return cp.deepcopy(self)

    def __deepcopy__(self, memo):
        m = self.__class__('')
        for f in self:
            m.append(cp.deepcopy(f))
        m.tokens = self.tokens
        m.func = self.func
        m.parsed = self.parsed
        return m

    def __getattr__(self, attr):
        if attr.startswith('__') and attr.endswith('__'):
            return super(BaseModel, self).__getattr__(attr)
        for q in self:
            if q.name == attr:
                return q
        raise AttributeError('%s has no Attribute \'%s\'' % (repr(self), attr))

    def __getitem__(self, item):
        if type(item) in (int, slice):
            return list.__getitem__(self, item)
        else:
            try:
                return getattr(self, item)
            except AttributeError:
                raise KeyError('TokenModel has no feature \'{}\''.format(item))

    def __eq__(self, other):
        # TODO: better override in each subclass
        if not hasattr(other, 'tokens'):
            # print 'can\'t compare: empty model'
            return False
        if self.tokens == other.tokens:
            if self.tokens != 'CUSTOM':
                return True
            return self.func == other.func
        else:
            return False

    def __ne__(self, other):
        if not hasattr(other, 'tokens'):
            # print 'can\'t compare: empty model'
            return True
        if self.tokens != other.tokens:
            return True
        elif self.tokens == 'CUSTOM' and self.func != other.func:
            return True
        else:
            return False

    @property
    def coupled_model(self):
        # TODO: brauch man das noch? Es gibt doch ein class atribute
        commas_found = reduce(lambda a, b: a + b, [q.num_coupling for q in self], 0)
        return commas_found + 1 if commas_found > 0 else 0

    def analyze(self):
        names = []
        txt = ''
        self.ok = False

        if self.func is not None:
            try:
                self.parse()
            except SyntaxError:  # raises only if forbidden characters are encountered
                txt = 'Invalid model (SyntaxError)'
            else:
                names = self.get_parameter_names()
                try:
                    ev = QuickEvaluate(self)
                    out = ev(np.array([-2, 1]), np.zeros(len(names)))
                except SyntaxError:
                    txt = 'Incomplete or invalid model.'
                except TypeError as err:
                    tpe, val, tb = sys.exc_info()
                    if str(val).find('bad operand') != -1:
                        txt = 'Incomplete or invalid model.'
                    else:
                        txt = 'TypeError: %s' % err
                except NameError as err:
                    txt = 'NameError: %s' % err
                except AttributeError as err:
                    txt = 'AttributeError: %s' % err
                    pass
                except ValueError as err:
                    txt = 'ValueError: %s' % err
                else:
                    if len(list(self['CUSTOM'].keys())) > 0 and self['CUSTOM'].has_x:
                        txt = 'Model valid.'
                        self.ok = True
                    elif not self['CUSTOM'].has_x:
                        txt = "'x' is missing from model definition."
                    else:
                        txt = 'No fit parameters found.'
            self.parsed = False
        else:
            if self.tokens != '' and not lineshapebase.lineshapes.known(self.tokens):
                txt = 'Unknown tokens.'
            else:
                txt = 'Model valid.'
                self.ok = True
        if self.coupled_model:
            txt += '\nThis is a coupled model for {} datasets.'.format(self.coupled_model)
        return txt, names

    def get_parameter_names(self):
        out = []
        for f in self:
            for name in f.keys():
                if name not in out:
                    out.append(name)
        return out

    def get_parameter_by_name(self, name):
        ret = []
        for f in self:
            for k, v in f.items():
                if k == name:
                    ret.append(v.value)
        return ret

    def get_model_unicode(self):
        return [self.func, self.tokens][int(self.tokens != 'CUSTOM')]

    def parameters_as_csv(self, **args):
        tbl = self.parameters_as_table(**args)
        tbl = '\n'.join([','.join([str(y) for y in x]) for x in tbl])
        return tbl

    def parameters_as_table(self, selection='all', witherrors=False):
        """\
        Export the model parameters as table. The first columns contains the
        name, the second the value. If 'selection' is not None, only
        parameters with names given by 'selection' will be exported, e.g. all
        peak positions, when selection = 'pos'
        
        selection: the parameter name as string according to the peak
        definition, can be a list of parameter names, too
        """
        pars = []
        for f in self:
            for name, par in list(f.items()):
                if par.hidden:
                    continue
                if name == selection or selection == 'all' or name in selection:
                    if witherrors:
                        pars.append((f.name, name, par.value, par.error))
                    else:
                        pars.append((f.name, name, par.value))
            if 'area' == selection or selection == 'all' or 'area' in selection:
                if f.area() != np.inf:
                    if witherrors:
                        pars.append((f.name, 'area', f.area(), 0.0))
                    else:
                        pars.append((f.name, 'area', f.area()))

        return [list(x) for x in pars]

    def is_autopickable(self):
        if self.tokens == 'CUSTOM':
            return False
        for f in self:
            if lineshapebase.lineshapes[f.name].picker != DummyPicker:
                return True
        return False

    def is_empty(self):
        return self.tokens == ''

    def is_filled(self):
        if not self.parsed:
            return False
        else:
            for f in self:
                if not f.is_filled():
                    return False
            return True

    def aa_parse(self):
        """\
        Starts the parser. Needed before every other operation.
        """
        if self.parsed or self.tokens == '':
            return

        try:
            self[:] = []
            self.parser = TokParser(self, self.tokens, self.func)
            self.parsed = True
        except KeyError:
            print('model key error')
            pass

    def clear(self):
        """\
        Set all parameters to zero.
        """
        for component in self:
            for el in component.keys():
                component[el].value = np.nan
                component[el].error = 0.0

    def set_parameters(self, param):
        """
Use this function if you want to set the parameter values
by hand.

param: A list - one element for each component - of dictionaries whoose
       keys correspond to the parameter names used in the function
       definition.
"""
        if not self.parsed:
            self.parse()

        count = 0
        for n, component in enumerate(param):
            for key, val in list(component.items()):
                if isinstance(val, Var):
                    self[n][key].value = val.value
                    self[n][key].constr = val.constr
                    self[n][key].amin = val.amin
                    self[n][key].amax = val.amax
                    self[n][key].error = val.error
                else:
                    self[n][key].value = val

    def update_from_fit(self, fitresult):
        """\
fitresult: result of Fit.run()

Update the model with the results from a fit.
        """
        (beta, sd_beta), msg = fitresult

        for component in self:
            for key, var in list(component.items()):
                var.value = beta[var.count]
                var.error = sd_beta[var.count]
        logger.debug('update from fit {}, has listener: {}'.format(repr(self), self.listener is not None))
        if self.listener is not None:
            self.listener()

    def aa_newpars(self, a, b):
        """\
        This function should not be called by the user. Use set_parameters
        instead.
        """
        for component in self:
            for key, var in list(component.items()):
                var.value = a[var.count]
                if b is not None:
                    var.error = b[var.count]
        if self.listener is not None:
            self.listener()

    def detach_stuck(self):
        # if a fit parameter approaches the limit to closely it won't
        # be modified ever again by the minimizer, so we need to
        # detach it manually from the limit
        for comp in self:
            for var in comp.values():
                if var.constr == 2:
                    if np.isclose(var.value, var.amin):
                        var.value += var.value * 1e-6
                    elif np.isclose(var.value, var.amax):
                        var.value -= var.value * 1e-6

    def evaluate(self, x, single=False, addbg=False, restrict=None):
        """\
        Evaluate the current model at positions x.
        single: if True, returns a list of all peaks evaluated
                separately
		restrict: list of tokens to be evaluated or None
        """

        x = np.atleast_1d(x)

        background = None

        # if self.parsed is False:
        #    self.parse()
        #    self.parsed = True

        evaly = np.zeros((0, len(x)))
        newy = []

        op = {'*': mul, '+': add, '': add}
        locs = {'x': x}

        for component in self:
            if restrict is not None and component.name not in restrict:
                continue
            for key, val in component.items():
                locs[key] = val.value
            try:
                if self.func is not None:
                    newy = eval(self.func, pom_globals, locs)
                else:
                    newy = eval(component.func, pom_globals, locs)
            except (ValueError, TypeError, ZeroDivisionError) as msg:
                continue  # does never happen
            else:
                if type(newy) == tuple:
                    # coupled model
                    return newy
                if single and np.isfinite(newy).all():
                    if component.name in lineshapebase.lineshapes.background:
                        background = newy
                    evaly = np.vstack((np.asarray(evaly), newy))
                    continue
                if np.logical_not(np.isfinite(newy)).any():
                    try:
                        tmpy = np.zeros(newy.shape, float)
                    except AttributeError:
                        raise
                    np.put(tmpy, np.isfinite(newy), np.compress(np.isfinite(newy), newy))
                    newy = tmpy
                if len(evaly) == 0:
                    evaly = newy
                else:
                    # print 'eval: all finite', np.isfinite(evaly).all()
                    if len(evaly) == 0:
                        evaly = newy
                    else:
                        evaly = op[component.op](evaly, newy)  # add or multiply components

        if single:
            evaly = np.atleast_2d(evaly)

        if single and addbg:
            for n in range(evaly.shape[0]):
                if background is not None:
                    evaly[n] = evaly[n] + background
            if background is not None:
                evaly = evaly[1:]

        return None if len(evaly) == 0 else evaly

    def background(self, x, ignore_last=False):
        out = 0.0
        peaks = self.evaluate(x, single=True)
        if ignore_last:
            peaks = peaks[:-1]
        if peaks is not False and len(peaks) > 0:
            for p, f in zip(peaks, self):
                if f.is_filled():
                    out += p[0]
                else:
                    break
        return out

    def loadpeaks(self, x, addbg=False):
        if not self.is_filled():
            return []
        lines = []

        ys = self.evaluate(x, single=True, addbg=addbg)
        if ys is not None:
            for y in ys:
                points = np.array([x, y])
                lines.append(points)

        return lines


class CustomModel(BaseModel):
    predefined = False

    def __init__(self, funcstr, listener=None):
        self.tokens = 'CUSTOM'
        self.func = funcstr.strip()
        self.ok = False
        self.listener = listener

    def __str__(self):
        return 'custom model: {}'.format(self.func)

    def analyze(self):
        names = []
        txt = ''
        self.ok = False

        try:
            self.parse()
        except SyntaxError:  # raises only if forbidden characters are encountered
            txt = 'Invalid model (SyntaxError)'
        else:
            names = self.get_parameter_names()
            try:
                ev = QuickEvaluate(self)
                out = ev(np.array([-2, 1]), np.zeros(len(names)))
            except SyntaxError:
                txt = 'Incomplete or invalid model.'
            except TypeError as err:
                txt = 'Incomplete or invalid model.'
                # tpe, val, tb = sys.exc_info()
                # if str(val).find('bad operand') != -1:
                #    txt = 'Incomplete or invalid model.'
                # else:
                #    txt = 'TypeError: %s'%err
            except NameError as err:
                txt = 'NameError: %s' % err
            except AttributeError as err:
                txt = 'AttributeError: %s' % err
                pass
            except ValueError as err:
                txt = 'ValueError: %s' % err
            else:
                if len(list(self['CUSTOM'].keys())) > 0 and self['CUSTOM'].has_x:
                    txt = 'Model valid.'
                    self.ok = True
                elif not self['CUSTOM'].has_x:
                    txt = "'x' is missing from model definition."
                else:
                    txt = 'No fit parameters found.'
        self.parsed = False
        self[:] = []
        return txt, names

    def parse(self):
        self.append(Component(self.func, '+', 0))
        self.parsed = True


class CoupledTokenModel(BaseModel):
    func = None
    predefined = True
    coupled_model = True

    def __init__(self, tokens, listener=None):
        self.ok = False  # True if check_model() was succesful
        self.parsed = False
        self.listener = listener

        self.tokens = tokens.strip()

    def __str__(self):
        return ' '.join([str(q) for q in self])

    def parse(self):
        if self.parsed or self.tokens == '':
            return

        self[:] = []
        count = 0
        comp = None
        for op, token in tokre.findall(self.tokens):
            if op.strip() == '':
                op = '+'
            syms = {} if comp is None else comp.symbol_map
            comp = Component(token, op, count, repeated_symbols=syms)
            self.append(comp)
            count += len(comp)
        self.parsed = True

    def analyze(self):
        self.ok = False

        tokens = [p for q, p in tokre.findall(self.tokens)]
        if self.tokens != '' and not lineshapebase.lineshapes.known(tokens):
            txt = 'Coupled model.\n\nUnknown tokens.'
        else:
            txt = 'Coupled model.\n\nModel valid.'
            self.ok = True

        return txt, []  # empty list because this is a token model

    def evaluate(self, x, single=True, restrict=None):
        """\
        Evaluate the current model at positions x.
        single: if True, returns a list of all peaks evaluated
                separately
		restrict: list of tokens to be evaluated or None
        """

        x = np.atleast_1d(x)

        if self.parsed is False:
            self.parse()

        evaly = np.zeros((0, len(x)))
        newy = []

        locs = {'x': x}

        func = ','.join([comp.func for comp in self])

        # qe = QuickEvaluate(self)

        for component in self:
            if restrict is not None and component.name not in restrict:
                continue
            for key, val in component.items():
                locs[key] = val.value
        try:
            newy = eval(func, pom_globals, locs)
        except (ValueError, TypeError, ZeroDivisionError) as msg:
            pass
        return newy


class TokenModel(BaseModel):
    func = None
    predefined = True

    def __init__(self, tokens, listener=None):
        self.ok = False  # True if check_model() was succesful
        self.parsed = False
        self.listener = listener

        self.tokens = tokens.strip()

    def __str__(self):
        return ' '.join([str(q) for q in self])

    def fit_bg(self, ds):
        if not self.parsed:
            return
        x, y = ds.xy
        bgmod = None
        for comp in self:
            if comp in lineshapebase.lineshapes.background:
                bgmod = TokenModel(comp.name)
                bgmod.parse()
                bgmod[0].init_to_zero()
                y = bg_snip(None, y)
                func = QuickEvaluate(bgmod)
                guess = list(func.par_fit.values())

                #m = FitModel(func)
                #dat = O.Data(x, y)



    def parse(self):
        if self.parsed or self.tokens == '':
            return

        self[:] = []
        count = 0
        for op, token in tokre.findall(self.tokens):
            if op.strip() == '':
                op = '+'
            comp = Component(token, op, count)
            self.append(comp)
            count += len(comp)
        self.parsed = True

    def analyze(self):
        self.ok = False

        tokens = [p for q, p in tokre.findall(self.tokens)]
        if self.tokens != '' and not lineshapebase.lineshapes.known(tokens):
            txt = 'Unknown tokens.'
        else:
            txt = 'Model valid.'
            self.ok = True

        return txt, []  # empty list because this is a token model

    def evaluate(self, x, single=False, addbg=False, restrict=None):
        """\
        Evaluate the current model at positions x.
        single: if True, returns a list of all peaks evaluated
                separately
		restrict: list of tokens to be evaluated or None
        """

        x = np.atleast_1d(x)

        background = None

        if self.parsed is False:
            self.parse()

        evaly = np.zeros((0, len(x)))
        newy = []

        locs = {'x': x}

        func = [','.join(comp.code for comp in self)]

        for component in self:
            if restrict is not None and component.name not in restrict:
                continue
            for key, val in component.items():
                locs[key] = val.value
            try:
                newy = eval(component.func, pom_globals, locs)
            except (ValueError, TypeError, ZeroDivisionError) as msg:
                continue  # does never happen
            else:
                if single and np.isfinite(newy).all():
                    if component.name in lineshapebase.lineshapes.background:
                        background = newy
                    evaly = np.vstack((np.asarray(evaly), newy))
                    continue
                if np.logical_not(np.isfinite(newy)).any():
                    try:
                        tmpy = np.zeros(newy.shape, float)
                    except AttributeError:
                        raise
                    np.put(tmpy, np.isfinite(newy), np.compress(np.isfinite(newy), newy))
                    newy = tmpy
                if len(evaly) == 0:
                    evaly = newy
                else:
                    evaly += newy

        if single:
            evaly = np.atleast_2d(evaly)

        if single and addbg:
            for n in range(evaly.shape[0]):
                if background is not None:
                    evaly[n] = evaly[n] + background
            if background is not None:
                evaly = evaly[1:]

        return None if len(evaly) == 0 else evaly


def Model(modelstring):
    if tokre.match(modelstring) is None:
        logger.debug('creating custommodel')
        return CustomModel(modelstring)
    else:
        if modelstring.find(',') != -1:
            logger.debug('creating coupled model {}'.format(tokre.findall(modelstring)))
            return CoupledTokenModel(modelstring)
        else:
            logger.debug('creating token model: {}'.format(tokre.findall(modelstring)))
            return TokenModel(modelstring)


class aa_TokParser(object):
    def __init__(self, model, pstr):
        self.model = model
        self.pstr = pstr
        self.ntok = 0
        self.parse()
        self.parsed = True

    def funcstr(self, scanner, name):
        mat = tokre.match(name)
        op, tok = mat.groups()
        if op in ['', ' ']:
            op = '+'
        self.ntok += 1
        return tok, op

    def parse(self):
        self.function = ''

        scanner = Scanner([
            (r"[,+*\s]*[A-Z]+[0-9]*", self.funcstr),
            (r"\+|\*\,", lambda y, x: x),
            (r"\s+", None),
        ])

        count = 0
        parsed, rubbish = scanner.scan(self.pstr)

        if rubbish != '':
            raise Exception('parsed: %s, rubbish %s' % (parsed, rubbish))

        for tok, op in parsed:
            comp = Component(tok, op, count)
            self.model.append(comp)
            count += len(comp)


class Component(dict):
    def __init__(self, tok, op, count, repeated_symbols={}):
        assert tok is not None
        self.has_x = False
        self.repeated_symbols = repeated_symbols

        self._plevel = 0
        self.num_coupling = 0

        self.name = tok
        self.op = op
        try:
            self.func = lineshapebase.lineshapes[tok].func
        except KeyError:
            mat = tokre.match(tok)
            if mat is not None:
                sym = re.match(r'([A-Z]+)\d*', mat.groups()[1]).groups()[0]
                raise UnknownToken('unknown model string found: {}'.format(sym))
            self.func = tok
            self.name = 'CUSTOM'
        self.dummy = []
        self.par_count_start = count
        self.count = count
        self.parse()

    def __str__(self):
        return self.name

    @property
    def symbol_map(self):
        return dict([(q, self[q].count) for q in self.keys()])

    def init_to_zero(self):
        for k in self.keys():
            self[k].value = 1.0

    def clear(self):
        for k in self.keys():
            self[k].value = np.nan
            self[k].error = 0.0

    def var_found(self, scanner, name):
        if name not in list(self.keys()) + list(self.repeated_symbols.keys()):
            self[name] = Var(np.nan, count=self.count)
            self.dummy.append(name)
            ret = 'a[%d]' % self.count
            self.count += 1
        elif name in self.keys():
            ret = 'a[{:d}]'.format(self.dummy.index(name) + self.par_count_start)
        elif name in self.repeated_symbols.keys():
            ret = 'a[{:d}]'.format(self.repeated_symbols[name])
        return ret

    def x_found(self, p, x):
        self.has_x = True
        return x

    def open(self, p, x):
        self._plevel += 1
        return x

    def close(self, p, x):
        self._plevel -= 1
        return x

    def func_found(self, p, x):
        self._plevel += 1
        return x

    def comma_found(self, p, x):
        if self._plevel == 0:
            self.num_coupling += 1
        return x

    def dottedsymbol(self, p, x):
        return x

    def parse(self):
        scanner = Scanner([
            (r"(?<![a-z0-9])x(?![a-z0-9(])", self.x_found),
            (r"c_[a-zA-Z0-9_]+", lambda y, x: x),
            (r"[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?", lambda y, x: x),
            # (r"[A-Za-z_][A-Za-z0-9_]*((\.[A-Za-z_][A-Za-z0-9_]*)|^(?!\(\()\()+", self.func_found),
            (r"([A-Za-z_][A-Za-z0-9_]*\.|)([A-Za-z_][A-Za-z0-9_]+\()", self.func_found),
            (r"([A-Za-z_][A-Za-z0-9_]*\.)([A-Za-z_][A-Za-z0-9_]+)", lambda y, x: x),
            (r"[a-zA-Z_][a-zA-Z0-9_]*", self.var_found),
            (r"\+|-|\*|/", lambda y, x: x),
            (r"\s+", None),
            (r"\)", self.close),
            (r"\(", self.open),
            (r"<", lambda y, x: x),
            (r">", lambda y, x: x),
            (r",", self.comma_found),
        ])

        parsed, rubbish = scanner.scan(self.func)
        parsed = ''.join(parsed)
        if rubbish != '':
            # print 'original string', self.func
            # print 'parsed',parsed
            # print 'rubbish', rubbish
            raise SyntaxError(rubbish)

        self.code = parsed

    def __getattr__(self, attr):
        if attr.startswith('__') and attr.endswith('__'):
            return super(Component, self).__getattr__(attr)
        if attr in list(self.keys()):
            return self[attr]
        else:
            raise AttributeError('%s has no Attribute \'%s\'' % (self, attr))

    def __setattr__(self, attr, value):
        if attr in list(self.keys()):
            raise AttributeError('''\
%s does not allow to overwrite \'%s\' attribute.
Use \'%s.value\' instead.''' % (repr(self), attr, attr))
        else:
            dict.__setattr__(self, attr, value)

    def is_filled(self):
        for k, v in list(self.items()):
            if v.value == np.nan:
                return False
        return True

    def val(self, vardic):
        for k, v in vardic.items():
            self[k].value = v

    def area(self):
        if self.name not in lineshapebase.lineshapes.peak:
            return np.inf
        locs = {}

        for key, val in list(self.items()):
            locs[key] = val.value

        try:
            x = eval('np.arange(pos-12*fwhm,pos+12*fwhm,fwhm/50.0)', pom_globals, locs)
        except:
            return np.inf
        else:
            locs['x'] = x
            try:
                y = eval(lineshapebase.lineshapes[self.name].func, pom_globals, locs)
            except ValueError:
                return np.inf
            else:
                dx = x[1:] - x[:-1]
                dy = (y[1:] + y[:-1]) / 2.0
                integ = sum(dy * dx)
                return integ


class Var(object):
    def __init__(self, value, error=0.0, count=0, constr=0, bounds=False, hidden=False):
        self.value = value
        self.error = error
        self.constr = constr
        self.count = count
        self.hidden = hidden
        if constr == 2:
            if type(bounds) not in [tuple, list]:
                raise TypeError('need upper and lower bounds as tuple')
            self.amin = bounds[0]
            self.amax = bounds[1]
        else:
            self.amin = np.nan
            self.amax = np.nan

    def _coerce(self):
        if self.constr != 2:
            return self.value
        else:
            # ret = np.arcsin(2*(self.value - self.amin)/(self.amax - self.amin) - 1)
            t = (self.value - (self.amin + self.amax) / 2.0) / ((self.amax - self.amin) / 2.0)
            ret = (-1 / (t - 1 * (2 * (t > 0) - 1)) - 1 * (2 * (t > 0) - 1))
            # print('coerce from {} to {}'.format(self.value,ret))
            return ret

    def _decoerce(self, arg):
        if self.constr != 2:
            self.value = arg
        else:
            # self.value = self.amin + (np.sin(self.value) + 1) * (self.amax - self.amin) / 2.0
            t = arg / (abs(arg) + 1.0)
            self.value = (self.amin + self.amax) / 2.0 + (self.amax - self.amin) / 2.0 * t
            # print('decoerce from {} to {}'.format(arg,self.value))

    value_mapped = property(_coerce, _decoerce)

    def __str__(self):
        return '{:.3g}'.format(self.value)


class curry_var(object):
    def __init__(self, var):
        self.amin = var.amin
        self.amax = var.amax

    def __call__(self, arg):
        # ret = self.amin + (np.sin(arg) + 1) * (self.amax - self.amin) / 2.0
        t = arg / (abs(arg) + 1.0)
        ret = (self.amin + self.amax) / 2.0 + (self.amax - self.amin) / 2.0 * t
        # print('decorce from {} to {}'.format(arg, ret))
        return ret


class QuickEvaluate(object):
    def __init__(self, model):
        self.model = model
        # print('instantiated QuickEvaluate', model.func, model)
        self.pre_fit()

    def pre_fit(self):
        func = ''
        replace = re.compile(r'(c)(?=[^a-zA-Z0-9])')
        for component in self.model:
            func += component.op + component.code

        self.func = compile(func, '<string>', 'eval')

        self.par_all = {}
        self.par_fit = {}
        self.par_demap = {}

        for component in self.model:
            for name, var in list(component.items()):
                self.par_all[var.count] = var.value_mapped
                if var.constr == 0:
                    self.par_fit[var.count] = var.value
                elif var.constr == 2:
                    self.par_fit[var.count] = var.value_mapped
                    self.par_demap[var.count] = curry_var(var)

    def fill(self, a, b):
        pars = np.array(list(self.par_all.values()))
        np.put(pars, list(self.par_fit.keys()), a)
        for k, v in self.par_demap.items():
            pars[k] = v(pars[k])

        errors = np.zeros(pars.shape)
        np.put(errors, list(self.par_fit.keys()), b)
        return pars, errors

    def __call__(self, x, a):
        fitpars = np.array(list(self.par_all.values()))

        np.put(fitpars, list(self.par_fit.keys()), a)
        for k, v in self.par_demap.items():
            fitpars[k] = v(fitpars[k])

        locs = {'a': fitpars, 'x': x}

        tmp = np.atleast_1d(eval(self.func, pom_globals, locs))
        # print 'all finite', np.isfinite(tmp).all()
        tmp[np.logical_not(np.isfinite(tmp))] = 0.0
        return tmp


def test1():
    m = Model('np.func(x,pos,width,amp)')
    m.parse()
    print(m.get_parameter_names())
    m = Model('func(x,pos,width,amp)')
    m.parse()
    print(m.get_parameter_names())
    m = Model('xan*x+23')
    m.parse()
    print(m.get_parameter_names())


def qe():
    m = Model('CB LO1')
    m.CB.const.value = 3.4
    m.LO1.amp.value = 3
    m.LO1.fwhm.value = 2.3
    m.LO1.pos.value = 45
    m.parse()
    QuickEvaluate(m)


def tp():
    m = Model('LO GA')
    m.parse()
    print([q.name for q in m])


def dm():
    m = Model('a*x*np.pi,np.sin((x*a))+b')
    m.parse()
    m.CUSTOM.a.value = 1
    m.CUSTOM.b.value = 2
    print(m.func)
    import numpy as np
    print(m.evaluate(np.linspace(0, 10, 5)))


def check_model(a):
    a.analyze()
    a.parse()
    for q in a:
        print(q.name, q.code)
    print(a.coupled_model)
    return a


def commamodels():
    a = check_model(Model('CB GA LO'))
    a.CB.const.value = 1.0
    a.GA.pos.value = 5.0
    a.GA.fwhm.value = 2.0
    a.GA.amp.value = 2.0
    a.LO.pos.value = 5.0
    a.LO.fwhm.value = 2.0
    a.LO.amp.value = 2.0
    print(a.evaluate([2.2, 3.3, 4.5, 5.5]))

    a = check_model(Model('CB,GA,LO'))
    a.CB.const.value = 1.0
    a.GA.pos.value = 5.0
    a.GA.fwhm.value = 2.0
    a.GA.amp.value = 2.0
    print(a.evaluate([2.2, 3.3, 4.5, 5.5]))

    check_model(Model('a*x,b*x+a'))


if __name__ == '__main__':
    commamodels()
