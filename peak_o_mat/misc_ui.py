##     Copyright (C) 2003 Christian Kristukat (ckkart@hoc.net)

##     This program is free software; you can redistribute it and/or modify
##     it under the terms of the GNU General Public License as published by
##     the Free Software Foundation; either version 2 of the License, or
##     (at your option) any later version.

##     This program is distributed in the hope that it will be useful,
##     but WITHOUT ANY WARRANTY; without even the implied warranty of
##     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##     GNU General Public License for more details.

##     You should have received a copy of the GNU General Public License
##     along with this program; if not, write to the Free Software
##     Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from wx.lib import newevent
from wx import xrc

import sys
import os
from . import misc

ResultEvent, EVT_RESULT = newevent.NewCommandEvent()
BatchStepEvent, EVT_BATCH_STEP = newevent.NewCommandEvent()
#ResultEvent, EVT_RESULT = newevent.NewCommandEvent()
HandlesChangedEvent, EVT_HANDLES_CHANGED = newevent.NewCommandEvent()
ShoutEvent, EVT_SHOUT = newevent.NewCommandEvent()
ParEvent, EVT_GOTPARS = newevent.NewCommandEvent()
RangeEvent, EVT_RANGE = newevent.NewCommandEvent()

#ShoutEvent.forever = False

GOTPARS_MOVE = 1
GOTPARS_DOWN = 2
GOTPARS_EDIT = 3
GOTPARS_END = 4

xres_loaded = False
def xrc_resource():
    global xres_loaded
    if not xres_loaded:
        if hasattr(sys,"frozen") and sys.frozen in ['windows_exe','console_exe']:
            xrcpath = os.path.join(misc.frozen_base, 'xrc', 'peak-o-mat.xrc')
        elif hasattr(sys,"frozen") and sys.platform == "darwin":
            xrcpath = os.path.join(misc.darwin_base, 'xrc', 'peak-o-mat.xrc')
        else:
            xrcpath = os.path.join(misc.source_base, 'peak-o-mat.xrc')
        xrc.XmlResource.Get().Load(xrcpath)
        xres_loaded = True
    return xrc.XmlResource.Get()
