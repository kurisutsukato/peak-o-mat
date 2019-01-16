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

"""\
In addition to the features of a standard python shell
the following symbols are available:

_name:      The name of the selected grid.
_data:      The ndarray or rank 2 displayed in the table above.
_selection: The indices of the current selection such
            that data[selection] retrieves the selected
            data.
_colX:      Column X as 2d column vector. 
_rowX:      Row X as 2d row vector.
_x:         The row indices as 2d row vector.
_y:         The column indices as 2d column vector.

_data, _colX and _rowX are readable *and* writable. In order to
write to the latter two, the shapes have to match exactly.

The numpy array broadcasting mechanism allows to create 2d
data writing expression like, e.g.

_data = _x+_y

"""

from .controller import create
