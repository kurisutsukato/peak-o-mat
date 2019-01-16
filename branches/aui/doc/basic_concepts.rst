Basic Concepts
==============

Data
----

The data is stored in a tree-like structure.  The root element is the *project*.
The next lower level is that of the *plots*, each of which can hold an arbitrary
number of  *sets*.  A *set*  is a  2d array containing  the x-y data,  where the
x-data  is ordered  (typical for  spectroscopic  data). This  data structure  is
represented by the tree view on the  right side of the main window.  In addition
to  the plain  x-y  data, a  set  can  have various  objects  attached, such  as
transformations (*trafo*), a fit *model* and *weights*.

Unlike  many   other  data  analysis   programs,  peak-o-mat  allows   for  data
manipulation/transformation on  a higher  level than operating  on the  raw data
through a spreadsheet  like interface.  As peak-o-mat is  especially designed to
work  with spectroscopic  data, arithmetics  on *sets*  will do  what you  would
expect intuitively,  e.g.  adding  two *sets*  will only  add the  y-data, while
interpolating the x-axes in case they differ. Those kind of manipulations can be
done  using the  'Set operations'  module.  If  you need  to do  more complicate
operations, you can still copy the data to a *data grid* and manipulate the data
there by means of a python shell.

Models
------

A *model*  describes the relation  between independent and response  variable of
the data set. It may be described by

- a valid  python expression, where *x*  stands for the set's  x-values. You can
  use  arbitrary   variable  names  containing  alphanumeric   characters,  e.g.
  "a*x-b0*x**2".  Also,  all mathematical  functions, which  are defined  in the
  toplevel namespace  of the python *numpy*  package are avilable. In  the model
  expression   the    function   name   has    to   be   prefixed    by   *np.*,
  e.g. "amp*np.exp(-x/beta)". In case the model is too complicated to be entered
  in a  single line, or  you just  need more flexibility,  you can use  your own
  python functions as model.  Physical constants are available through prefixing
  their common name by 'c_', e.g.   'c_e' referes to the elementary charge.  See
  the  'customisation'  section for  how  to  define  custom functions  and  add
  constants.
  
- a space  separated list  of pre-defined symbols,  here called  *tokens*, which
  represent common background and peak  shapes.  The function values represented
  by the tokens are finally added, e.g.  "CB LO GA LO" represents a model with a
  constant background, one gaussian peak and  two lorenzian peak shapes. You can
  append a number  to any token to  be able to distinguish them  later, e.g. "CB
  LO1 GA LO2".   Instead of the whitespace between the  tokens, the '+' operator
  can be  used.  In  some rare  cases you  might want  to multiply  the function
  represented by  the tokens.  This can  be achieved by using  the '*' operator.
  The model  is evaluated from  left to  right and the  usual sign rules  do not
  apply.  You may  define customs  tokens similar  to the  definition of  custom
  functions. See the 'customisation' section for details.

Once a  model has  been fitted  to a data  set, the  model including  the fitted
parameters is attached to the set and whenever the set is selected, the model is
evaluated and displayed together with the data.

Transformations and masks
-------------------------

A *trafo* denotes  any transformation of the  x- or y-data of a  set. Instead of
changing the original data, all trafos are  attached to a data set and evaluated
on demand whenever the  set data is accessed.  Like this,  the original data can
be restored by simply removing all  trafos.  Furthermore, if you remove bad data
points from  a set, a *mask*  is applied to the  data so that all  points can be
restored at  any time. Use the  popup menu in the  tree view to unset  a mask or
remove the  transformations attached  to the currently  selected sets.  The 'Set
Info' model allows for manipulation of every single transformation of a set. The
transformation expresseion  can be  changed, transformations can  be deactivated
and both masks  and tranformations can be made permanent,  i.e. they are applied
once and the original data is overwritten with the result from the evaluation.

Weights
-------

The residuals of a  fit may be weighted in order to improve  the fit but this is
not in particular  meant to reduce the  effect of outliers on the  fit, as those
can be erased before fitting. In spectrosopy it is quite common that only a part
of the measured data,  i.e. in a certain region of  the independent variable can
be sufficiently well described by a model  and that the data is overlayed by the
results of  unknown physical and/or measurement  effects. In that sense  you may
want to assign low  weights to regions which you are not  interested in and high
weights in regions where the model should work well.  Though talking of weights,
you actually specify  the standard deviation of the data  rather than the weight
of the residual which is just the inverse of the standard deviation.
