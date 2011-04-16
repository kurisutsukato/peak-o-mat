import  wx
import wx.grid

class DumbRenderer(wx.grid.PyGridCellRenderer):
    def __init__(self):
        wx.grid.PyGridCellRenderer.__init__(self)
        
    def Draw(self, grid, attr, dc, rect, row, col, isSelected):
        dc.SetBackgroundMode(wx.SOLID)

        dc.SetBrush(wx.Brush(wx.Colour(230,230,230), wx.SOLID))
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.DrawRectangleRect(rect)

    def Clone(self):
        return DumbRenderer()

class CellRenderer(wx.grid.PyGridCellRenderer):
    def __init__(self):
        wx.grid.PyGridCellRenderer.__init__(self)
        
    def Draw(self, grid, attr, dc, rect, row, col, isSelected):
        dc.SetBackgroundMode(wx.SOLID)

        if isSelected:
            dc.SetBrush(wx.Brush(wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHT), wx.SOLID))
            dc.SetTextForeground(wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT))
        else:
            bg = grid.GetDefaultCellBackgroundColour()
            if attr.HasBackgroundColour():
                bg = attr.GetBackgroundColour()
            dc.SetBrush(wx.Brush(bg, wx.SOLID))
            dc.SetTextForeground(wx.BLACK)
            
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.DrawRectangleRect(rect)

        dc.SetBackgroundMode(wx.TRANSPARENT)
        #dc.SetFont(attr.GetFont())

    def drawText(self, text, rect, dc):
        x, y = rect.x+1, rect.y+1

        for ch in text:
            dc.DrawText(ch, x, y)
            w, h = dc.GetTextExtent(ch)
            x = x + w
            if x > rect.right - 5:
                break

    def GetBestSize(self, grid, attr, dc, row, col):
        text = unicode(grid.GetCellValue(row, col))
        dc.SetFont(attr.GetFont())
        w, h = dc.GetTextExtent(text)
        return wx.Size(w, h)

class ChoiceTextRenderer(CellRenderer):
    def __init__(self, choice):
        CellRenderer.__init__(self)
        self.choice = choice
        
    def Draw(self, grid, attr, dc, rect, row, col, isSelected):
        CellRenderer.Draw(self, grid, attr, dc, rect, row, col, isSelected)

        text = self.choice[int(grid.GetCellValue(row, col))]

        self.drawText(text, rect, dc)
        
    def Clone(self):
        return ChoiceTextRenderer(self.choice)

class FloatRenderer(CellRenderer):
    def __init__(self):
        CellRenderer.__init__(self)

    def Draw(self, grid, attr, dc, rect, row, col, isSelected):
        CellRenderer.Draw(self, grid, attr, dc, rect, row, col, isSelected)

        self.val = grid.GetCellValue(row, col)
        #if type(self.val) != str:
        #    if len(str(self.val)) > 12:
        #        val = '%.6e'%float(self.val)
        #    else:
        #        val = str(self.val)
            
        self.drawText(str(self.val), rect, dc)

    def Clone(self):
        return FloatRenderer()
        
    def GetBestSize(self, grid, attr, dc, row, col):
        dc.SetFont(attr.GetFont())
        text = '0'*min(12,len(unicode(grid.GetCellValue(row, col))))
        w, h = dc.GetTextExtent(text)
        return wx.Size(w+5, h)

class ChoiceCellEditor(wx.grid.PyGridCellEditor):
    def __init__(self, varList):
        wx.grid.PyGridCellEditor.__init__(self)
        self._varList = varList

    def Create(self, parent, id, evtHandler):
        """\
        Called to create the control, which must derive from wxControl.
        """
        self._choiceCtrl = wx.Choice(parent, id, choices = self._varList)
        self._choiceCtrl.Bind(wx.EVT_CHOICE, self.OnChoice)
        if len(self._varList):
            self._choiceCtrl.SetSelection(0)
        self.SetControl(self._choiceCtrl)
        if evtHandler:
            self._choiceCtrl.PushEventHandler(evtHandler)
            evtHandler.SetEvtHandlerEnabled(False)

    def SetSize(self, rect):
        """\
        Called to position/size the edit control within the cell rectangle.
        If you don't fill the cell (the rect) then be sure to override
        PaintBackground and do something meaningful there.
        """
        self._choiceCtrl.SetDimensions(rect.x, rect.y, rect.width, rect.height,
                               wx.SIZE_ALLOW_MINUS_ONE)

    def BeginEdit(self, row, col, grid):
        """
        Fetch the value from the table and prepare the edit control
        to begin editing.  Set the focus to the edit control.
        """
        self.grid = grid
        self.startValue = grid.GetTable().data[row][col]
        self._choiceCtrl.SetSelection(self.startValue)
        self._choiceCtrl.SetFocus()

    def OnChoice(self, evt):
        self.grid.EnableCellEditControl(False)
        evt.Skip()
        
    def EndEdit(self, row, col, grid):
        """
        Complete the editing of the current cell. Returns true if the value
        has changed.  If necessary, the control may be destroyed.
        """
        changed = False

        sel = self._choiceCtrl.GetSelection()
        if sel != self.startValue:
            changed = True
            grid.GetTable().SetValue(row, col, sel) # update the table

        self.startValue = None
        return changed


    def Reset(self):
        """
        Reset the value in the control back to its starting value.
        """
        self._choiceCtrl.SetSelection(self.startValue)

    def Clone(self):
        """
        Create a new object which is the copy of this one
        """
        return ChoiceCellEditor(self._varList)
