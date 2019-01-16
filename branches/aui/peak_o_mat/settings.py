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

import os
from .appdata import configdir

fast_display = False
fast_max_pts = 200

truncate = False
truncate_max_pts = 1000
truncate_interpolate = True

floating_point_is_comma = False

from .appdata import configdir

configfile = os.path.join(configdir(),'config.py')
if os.path.exists(configfile):
    try:
        exec(compile(open(configfile).read(), configfile, 'exec'))
    except:
        print('could not read config.py')
else:
    print('no config.py in \'%s\''%configdir())




