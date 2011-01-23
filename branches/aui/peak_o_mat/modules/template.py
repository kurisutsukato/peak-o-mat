import wx

from peak_o_mat import module

class Module(module.Module):
    """
    Every module must subclass module.Module. You have to set the class
    variable 'title', which should hold the text that appears in the notebook
    tab title.  A module must be named 'mod_XXX.py', the GUI part has to be
    named 'mod_XXX.xrc'. The top level GUI element must be a wx.Panel with the
    XMLID set to 'mod_XXX'. Modules are loaded automatically upon program
    start from

    <system pythonpath>/peak_o_mat/modules/

    and

    $HOME/.peak-o-mat/modules 

    In the former case, the module has to be listed in

    <system pythonpath>/peak_o_mat/modules/__init__.py
    
    Instance variables:

    self.panel      : reference to the panel
    self.controller : reference to the main controller
    self.project    : reference to the project data
    
    self.xrc_XXX    : reference to the wx control with XMLID xrc_XXX

    self.Bind/Unbind are redirected to self.panel.Bind/Unbind for convenience

    
    """
    title = 'module template'

    def __init__(self, *args):
        """\
        This is the minimal constructor that each module needs. Passing
        '__file__' is needed in order to tell the XRC loader name and location
        of the xrc file.
        """
        module.Module.__init__(self, __file__, *args)
    
    def init(self):
        """\
        This method will be called after the gui has been loaded via xrc. Use
        it e.g. to setup the bindings to gui events here:

        self.Bind(wx.EVT_BUTTON, self.OnButton, self.xrc_btn_do)

        will bind self.OnButton to the xrc control with XMLID xrc_btn_do.
        """
        
        pass

    def selection_changed(self):
        """\
        Override this method to recieve notification whenever the set selection has
        changed.
        """

        pass

    def page_changed(self, me):
        """\
        Override this method to recieve notification whenever the notebook page has
        changed.
        
        me: boolean, True if this page has been selected, false otherwise
        """

        pass
    
        

        
