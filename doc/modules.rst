The modules
===========

A module  is a  small functional unit  which adds a  feature to  peak-o-mat. The
available modules  are shown  as notebook  tabs in  the lower  part of  the main
window.   The only  built-in  module is  the *Fit*  module.   All other  modules
consist of a  python source (.py) and  a XRC (.xrc) file,  the latter describing
the GUI of the  module. See the 'customisation' section below  for an example of
how to add custom modules to peak-o-mat.

Fit module
----------

This is the core module of peak-o-mat. It has four components:

Model
`````

As said before,  the model can be  either a list of predefined  tokens which may
suffixed  by an  integer number  or a  valid python  expression using  arbitrary
parameter names.   Note that tokens  always consist  of uppercase letter  and an
optional number whereas fit parameters have  to be lowercase. It is not possible
to mix tokens and python expressions  in a single model. See the 'customisation'
section for  details. Just  type to  the 'Fit  model' text  input to  define the
model. All available tokens are shown in  the listbox on the left of the window.
When you select a model token from the  list its definition will be shown in the
textbox on the right. Double-clicking on any item or clicking the 'Add to model'
button will  add the token  to the model definition.   While typing to  the 'Fit
model'  field, the  function  parser will  try to  identify  fit parameters  and
functions and it will  tell you if the entered expression is  vaild.  Do not pay
too much attention  to the error messages  which will pop up  while typing until
you have not finished the expression.  Once the model is complete however, there
should be no error message.


Parameters
``````````

In order  to work on  the parameters of  the model a single  data set has  to be
selected. In the parameters view the fit parameters of the current the model are
shown in the data grid on the left.  The parameter called 'area' though is not a
fit parameter.  It represents the  value of  the numerically integrated  area in
between  the lineshape  and the  abscissa  in case  the lineshape  has a  finite
area. If  you just entered  a new model  all parameters are  undefinied.  Before
doing a fit  you need to provide  an initial guess for every  parameter, i.e.  a
value  near the  value you  would expect.   Whenever you  change a  parameter by
editing  the  corresponding  cell  of  the paramter  grid,  the  model  will  be
immediately  evaluated  at the  x-data  points  of  the  selected data  set  and
displayed in green together  with the data. Like this it is easy  to find a good
initial  guess since  you  can  directly compare  the  evaluted  model with  the
measured data. After  having entered values for all parameters  you may click on
'Fit (short link)' to do the fit. The button's label says 'short link' since the
button is a duplicate of the 'Fit' button on the fit panel (see below) where you
can specify the fit options.

Parameter picking
:::::::::::::::::

If the model  is defined by combinations  of those tokens which are  built in to
peak-o-mat there  is an easier  way to provide  the initial guess  than entering
values  by hand.   The initial  guess  for any  of  the built-in  tokens may  be
provided  by placing  the corresponding  lineshape on  the plot  area.  This  is
called 'parameter picking'  since the parameters are picked up  from the plot by
using the mouse. If you click on  the 'Pick' button just right to the parameters
grid view and  move the pointer to the  plot area you will quickly  learn how to
handle the parameter picking procedure. In the  status line of the window at its
very bottom you can  see which component of the model  you are currently working
on.  The parameter picking procedure ends when all components have been defined,
i.e. all lineshapes  have been placed on  the plot.  In case you  need to refine
the guess  for just one  component of the model  choose that component  from the
drop down list to the right of the  'Pick' button, click on 'Pick' and place the
lineshape on the plot as before.

Parameter export
::::::::::::::::

Once the model has been fitted to the data the parameter grid is filled with the
fitted  parameters overwriting  the initial  guess.  For  further processing  or
visualization of  the fitted values  they can be  exported or transfered  to the
*data grid* which is a spreadsheet like tool integrated into peak-o-mat. This is
done by  pressing the 'Export'  button.  A message will  be shown in  the status
line  telling that  the parameters  have been  exported. To  open the  data grid
choose the  corresponding item  from the  'View' menu or  press CTRL-d.  See the
section on the data  grid for more information. You may choose  to only export a
certain  parameter  of  each component  of  the  model,  e.g.  if you  are  only
interested in the 'pos' parameter of  a series of peak shaped components, choose
'pos' from  the drop-down list  and click  'Export' afterwards. If  the checkbox
'include  errors' is  selected the  parameters  and their  fit uncertainity  are
exported and displayed in separate rows of the data grid.
 
Creating data sets from model parameters
::::::::::::::::::::::::::::::::::::::::

Once a model has been fitted to a data set, the fit is shown along with the data
evaluated on-the-fly at the x-values of the  data. In order to create a data set
from the evaluated modele  enter values for the x-region and  the number of data
points of the new data set and click  'Load'. The newly created data set will be
added current plot. The  end points of the region default to  the x-range of the
selected set. You  have the choice to  evaluate the complete model  with all its
components or only a single component by choosing a component from the drop-down
list next to the 'Load' button.


Weights
```````

In the weights view you can define regions  on the x-axis each of which may have
a distinct weight.  Although talking of  weights you actually specify a standard
deviation. The deviation  can be defined as relative to  the y-data, in absolute
values or  as a combination of  both.  If you  have not yet defined  regions the
table  shows a  single  line and  the  region  spans the  wohle  x-range of  the
data. Clik on 'Place  region borders' and then click on the  plot where you want
to place  a border  between two  regions.  The region  borders are  displayed as
vertical lines  on the plot. In  the moment you click  on the plot the  table is
updated  to reflect  the new  regions.  As  long as  the 'Place  region borders'
button is pressed you may add  region borders or drag existing ones. Right-click
an existing border to  remove it. For each region enter  the desired values into
the table and choose whether it is meant to bet relative to the y-data, absoulte
or a  combination of  both.  You  will notice that  the standard  deviations are
displayed  on  the  plot  area  as  light blue  band  with  its  center  at  the
y-data. Click on 'Attach to set'  to attach the current weights configuration to
the  currently selected  data set.   Only if  you do  that the  weights will  be
honoured in the fit. If a weights configuration is attached to a set the display
style changes to  dark blue and it  will always be displayed along  with the set
data also if you leave the weights view.

Fit
```

In the fit view you can tune the fit procedure and see the result message of the
last  fits.  Although  you may  choose  between least  squares minimization  and
orthogonal distance regression  (ODR), ODR is not completely supported  as it is
not  possible   to  specify   weights  for   both  depenendet   and  independent
variables. Anyway, spectroscopic data hardly ever need ODR. Usually is is not necesary to modify 

Data operations module
----------------------

As mentioned  before, manipulations of  the set data  can be done on  a higher
level than editing the x- and  y-data directly.  

Operations on the sets can be either an operation between the y-values of
different sets (inter-set) or a transformation of either the x- or y-values of
one set (intra-set).  In the former case, a new set is created, in the latter
case the transformation is attached to the current set and can be removed later
thus restoring the original data.  The sets can be referenced by the identifier
'sX', where X is the set number of the active plot shown in the tree view on the
right side.  Inter-set operations are only possible between sets of the same
plot.  The intra-set operations are applied to all selected sets.  The axis and
set identifiers ('x','y','sX') appearing in the expression determine wether the
expression is an inter- or an intra-set operation. The special operator & will
join two sets if they do not overlap.

examples of valid expressions are::

  x+10              intra-set, x-axis
  1/y               intra-set, y-axis
  log10(y)          intra-set, y-axis
  (s0+s1)/2         inter-set
  s0&s1             inter-set

Evaluate module
---------------

This module  allows you to create sets  by evaluating a custom  function or by
drawing a spline on the plot canvas. 

Set info module
---------------

The  set info  module gives  information about  the number  of total  and masked
points  of  a  set  and  the  list  of  transformations  attached  to  it.   The
transformations can  be deactivated temporarily by  unchecking the corresponding
checkbox, removed completely  and the transformations and their  comments can be
edited when double-clicking on the corresponding field.

Calibration module
------------------

calibrate data using spectral lines of Ne,Ar,He,Me, etc.

Shell module
------------

shell access to the internals of peak-o-mat (dangerous)

Ruby calibration module
-----------------------

pressure calibration using the R1 luminescence
