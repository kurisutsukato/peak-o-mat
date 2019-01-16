Customising peak-o-mat
======================

All customisation data has to be saved in the peak-o-mat configuration folder
which is located at $HOME/.peak-o-mat on UNIX-type systems (linux and OSX) or in
%UserProfile%\\AppData\\peak-o-mat on windows
(see http://en.wikipedia.org/wiki/Home_directory). Note that the AppData folder (or
e.g. 'Anwendungsdaten' in german) is usually a hidden folder.

Config file
-----------

Upon start peak-o-mat looks for a configuration file config.py.  An example
config.py file looks like the following::

  # if fast_display is True, only fast_max_pts points of all sets but the
  # active one are shown
  fast_display = False
  fast_max_pts = 500

  # truncate the data upon import
  truncate = False
  truncate_max_pts = 2000
  truncate_interpolate = False

  # set to True if the floating point is ',' (e.g. german windows)
  # this affects the data import and export
  floating_point_is_comma = False


Adding custom peak shapes
-------------------------

On startup peak-o-mat imports the python module *userfunc.py* from the
configuration folder. Put your own function definitions there according to the
following scheme::

  import numpy as np
  from peak_o_mat import peaksupport as ps

  # parbolic background model
  ps.add('PAR',
            func='a*x**2+b*x+c',
	    ptype='BACKGROUND')

  def gauss(x, amp, pos, fwhm):
      return np.amp*np.exp(-(np.pow(x-pos,2)/(fwhm*fwhm/2.0)))

  # a gauss peak	    
  ps.add('PEAK',
            func='gauss(x,amp,pos,fwhm)',
            info='a gaussian',
	    ptype='PEAK',
            picker=ps.LOPicker)

ps.add() is defined as follows::

  def add(self, name, func=None, info='', ptype=None, picker=None):
      name:   uppercase model name, e.g. GA
      info:   an information text describing the model
      func:   the function string
      ptype:  one of 'BACKGROUND','PEAK','EXP','MISC'
      picker: a picker object, e.g. LOPicker, which handles the collection
	      of the function's parameters from mouse actions

If you do not specify a *picker*, the initial guess for that peak must be
entered by hand. Common *pickers* are defined in the file *peaksupport.py* in
the peak-o-mat source distribution.

A more complicated example of a custom peak shape, including a custom picker function is whon in the following::

  class GFDPicker(list):
      def __init__(self, component, background_cb):
          list.__init__(self,[(ps.Cmd('mx'),self.pos),(ps.Cmd('mxy'),self.amp_sigma)])
          self.f = component
          self.background_cb = background_cb

      def pos(self, x):
          self.f['pos'].value = x

      def amp_sigma(self, xy):
          x, y = xy
          self.f['sigma'].value = np.abs(x - self.f['pos'].value)
          self.f['amp'].value = -(y - self.background_cb(x, ignore_last=True)) * self.f['sigma'].value * np.sqrt(np.e) * np.sign(x - self.f['pos'].value)

  ps.add('GFD',
         func='-amp*(x-pos)/(sigma*sigma)*np.exp(-0.5*(pow((x-pos)/sigma,2)))',
         info='First derivative of a Gaussian',
         ptype='PEAK',
         picker=GFDPicker)
 
You can add own constants so that they can be used in the model definitions::

  from peak_o_mat import symbols

  # add gravitation constant
  symbols.add_constant('G',6.673e-11)


Installing/Writing Modules
--------------------------

In order to use third-party or own modules move the module's files to the
*modules* subdirectory whithin the configuration folder. peak-o-mat will load
them upon program start.  The modules which are distributed with peak-o-mat
reside in <site-packages>/peak_o_mat/modules.  Those global modules have to be
listed in __init__.py at the same location to be activated.

Writing  own   modules  is  easy.    Use  *xrced*  (part  of   every  wxPython
installation) to create a GUI and  save it as *mod_XXX.xrc*. The top-level GUI
element of each module must be  a wx.Panel having the module's filename as XML
ID (in this  case *mod_XXX*). Then add anything you like  but remember to keep
the overall height  of the panel small since the taller  the module's GUI, the
fewer space will  be availabe for the  graphs. If you provide XML  IDs for the
controls,  let the  IDs begin  with  *xrc_*. This  enables you  to access  the
controls by referencing  them as *self.xrc_xxx* in the  program. Then create a
python  source  file, named  *mod_XXX.py*,  which  has  the following  minimal
content::

  from peak_o_mat import module

  Module(module.Module):
      title = 'this modules title'
      def __init__(self, *args):
	  module.Module.__init__(self, __file__, *args)

It  is  absolutely necessary  to  call  the  constructor of  module.Module  as
described above, if not, peak-o-mat will  not be able to find the module's XRC
file.  However do  not add  code to  the constructor  which accesses  the GUI,
instead define the method::
  
  def init(self):
      ....

and use  it like  a constructor.  When  *OnInit* will  be called, the  GUI has
already  been  loaded and  can  be  accessed savely,  e.g.   to  set up  event
bindings.  The Module  class does  not derive  from a  wx control,  however it
provides the following instance variables/methods::

  self.panel       - reference to the panel
  self.controller  - reference to the main controller
  self.project	   - reference to the project data
  self.Bind()      - self.panel.Bind()
  self.Unbind()    - self.panel.Unbind()
  self.xrc_xxx	   - reference to the wx control with
                     the XML ID *xrc_xxx*

See the files template.py/template.xrc in the *modules* subdir for a working
example.
