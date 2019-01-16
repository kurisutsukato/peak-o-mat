
import wx
import wx.dataview as dv

#----------------------------------------------------------------------

# This model class provides the data to the view when it is asked for.
# Since it is a list-only model (no hierarchical data) then it is able
# to be referenced by row rather than by item object, so in this way
# it is easier to comprehend and use than other model types.  In this
# example we also provide a Compare function to assist with sorting of
# items in our model.  Notice that the data items in the data model
# object don't ever change position due to a sort or column
# reordering.  The view manages all of that and maps view rows and
# columns to the model's rows and columns as needed.
#
# For this example our data is stored in a simple list of lists.  In
# real life you can use whatever you want or need to hold your data.

#class TestModel(dv.PyDataViewModel):



class TestModel(dv.DataViewIndexListModel):
    def __init__(self, data):
        dv.DataViewIndexListModel.__init__(self, len(data))
        self.data = data

    # All of our columns are strings.  If the model or the renderers
    # in the view are other types then that should be reflected here.
    def GetColumnType(self, col):
        return ['string','string','int'][col]

    # This method is called to provide the data object for a
    # particular row,col
    def GetValueByRow(self, row, col):
        return self.data[row][col]

    # This method is called when the user edits a data item in the view.
    def SetValueByRow(self, value, row, col):
        self.data[row][col] = value
        return True

    # Report how many columns this model provides data for.
    def GetColumnCount(self):
        return len(self.data[0])

    # Report the number of rows in the model
    def GetCount(self):
        print('GetCount')
        return len(self.data)

    # Called to check if non-standard attributes should be used in the
    # cell at (row, col)
    def GetAttrByRow(self, row, col, attr):
        ##self.log.write('GetAttrByRow: (%d, %d)' % (row, col))
        if col == 2:
            attr.SetColour('blue')
            attr.SetBold(True)
            return True
        return False


    def Compare(self, item1, item2, col, ascending):
        if not ascending: # swap sort order?
            item2, item1 = item1, item2
        row1 = self.GetRow(item1)
        row2 = self.GetRow(item2)
        cmp = (lambda a,b:(a>b)-(a<b))
        if col == 0:
            return cmp(int(self.data[row1][col]), int(self.data[row2][col]))
        else:
            return cmp(self.data[row1][col], self.data[row2][col])

class TestPanel(wx.Panel):
    def __init__(self, parent, model):
        wx.Panel.__init__(self, parent, -1)

        # Create a dataview control
        self.dvc = dv.DataViewCtrl(self,
                                   style=wx.BORDER_THEME
                                   | dv.DV_ROW_LINES # nice alternating bg colors
                                   #| dv.DV_HORIZ_RULES
                                   | dv.DV_VERT_RULES
                                   | dv.DV_MULTIPLE
                                   )

        self.model = model

        self.dvc.AssociateModel(self.model)

        self.dvc.AppendTextColumn("Vorname",  1, width=170, mode=dv.DATAVIEW_CELL_EDITABLE)
        self.dvc.AppendTextColumn("Nachname",  2, width=260, mode=dv.DATAVIEW_CELL_EDITABLE)
        c0 = self.dvc.PrependTextColumn("Id", 0, width=40)

        c0.Alignment = wx.ALIGN_RIGHT
        c0.Renderer.Alignment = wx.ALIGN_RIGHT
        c0.MinWidth = 40

        # Through the magic of Python we can also access the columns
        # as a list via the Columns property.  Here we'll mark them
        # all as sortable and reorderable.
        for c in self.dvc.Columns:
            c.Sortable = True
            c.Reorderable = False

        # set the Sizer property (same as SetSizer)
        s = wx.BoxSizer(wx.VERTICAL)
        s.Add(self.dvc, 1, wx.EXPAND)
        self.SetSizer(s)

        self.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.OnSelect)

    def OnSelect(self, evt):

        print(evt.GetModel().GetRow(self.dvc.GetSelection()))

data = '''\
Marie Curie
Frida Kahlo
Clara Schumann
Lili Boulanger'''

if __name__ == '__main__':
    data = [[str(n*53)]+q.split(' ') for n,q in enumerate(data.strip().split('\n'))]

    m = TestModel(data)
    app = wx.App()
    f = wx.Frame(None)
    p = TestPanel(f, m)
    f.Show()
    app.MainLoop()
