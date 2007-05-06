###############################################################################
#    Copyright (C) 2007 Cody Precord                                          #
#    cprecord@editra.org                                                      #
#                                                                             #
#    Editra is free software; you can redistribute it and#or modify           #
#    it under the terms of the GNU General Public License as published by     #
#    the Free Software Foundation; either version 2 of the License, or        #
#    (at your option) any later version.                                      #
#                                                                             #
#    Editra is distributed in the hope that it will be useful,                #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of           #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the            #
#    GNU General Public License for more details.                             #
#                                                                             #
#    You should have received a copy of the GNU General Public License        #
#    along with this program; if not, write to the                            #
#    Free Software Foundation, Inc.,                                          #
#    59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.                #
###############################################################################

"""
#-----------------------------------------------------------------------------#
# FILE: ed_stc.py                                                             #
# LANGUAGE: Python                                                            #
# AUTHOR: Cody Precord                                                        #
#                                                                             #
# SUMMARY:                                                                    #
# This file contains the definition of the text control class                 #
# The text control is responsible for keeping reference to the file that      #
# is currently being edited in it.                                            #
#                                                                             #
# The class also contains the definitions of all the styles for fonts and     #
# highlighting in the context of code editing.                                #
#                                                                             #
# METHODS:                                                                    #
# - ED_STC: Main class object definition, based on wx.stc                     #
# - GetPos: Returns line and column information of carat                      #
# - OnUpdateUI: Checks brackets after each change to the screen.              #
# - OnMarginClick: Margin Event handler                                       #
# - OnFoldAll: Opens or closes a folder tree                                  #
# - Expand: Opens margin folders                                              #
# - FindLexer: Finds the approriate lexer based on file extentsion            #
#                                                                             #
#-----------------------------------------------------------------------------#
"""

__revision__ = "$Id:  $"

#-------------------------------------------------------------------------#
# Dependencies

import os
import wx, wx.stc
from ed_glob import *
from syntax import syntax
from autocomp import autocomp
import util
import ed_style

_ = wx.GetTranslation
MARK_MARGIN = 0
NUM_MARGIN  = 1
FOLD_MARGIN = 2
#-------------------------------------------------------------------------#
class EDSTC(wx.stc.StyledTextCtrl, ed_style.StyleMgr):
    """Defines a styled text control for editing text in"""
    ED_STC_MASK_MARKERS = ~wx.stc.STC_MASK_FOLDERS
    def __init__(self, parent, win_id,
                 pos=wx.DefaultPosition, size=wx.DefaultSize,
                 style=0, useDT=True):
        """Initializes a control and sets the default objects for
        Tracking events that occur in the control.

        """
        wx.stc.StyledTextCtrl.__init__(self, parent, win_id, pos, size, style)
        ed_style.StyleMgr.__init__(self, self.GetStyleSheet())

        self.SetModEventMask(wx.stc.STC_PERFORMED_UNDO | wx.stc.STC_PERFORMED_REDO | \
                             wx.stc.STC_MOD_DELETETEXT | wx.stc.STC_MOD_INSERTTEXT | \
                             wx.stc.STC_PERFORMED_USER)

        self.CmdKeyAssign(ord('-'), wx.stc.STC_SCMOD_CTRL, wx.stc.STC_CMD_ZOOMOUT)
        self.CmdKeyAssign(ord('+'), wx.stc.STC_SCMOD_CTRL | wx.stc.STC_SCMOD_SHIFT, \
                          wx.stc.STC_CMD_ZOOMIN)
        #---- Drop Target ----#
        if useDT:
            self.fdt = util.DropTargetFT(parent)
            self.SetDropTarget(self.fdt)

        # Attributes
        self.LOG = wx.GetApp().GetLog()
        self.frame = parent	                # Notebook
        self.filename = ''	                # This controls File
        self.dirname = ''                   # Files Directory
        self.path_char = util.GetPathChar()	# Path Character / 0r \
        self.zoom = 0
        self.old_pos = -1
        self.column = 0
        self.line = 0
        self._autocomp_svc = autocomp.AutoCompService(self)
        self._use_autocomp = PROFILE['AUTO_COMP']
        self._autoindent = PROFILE['AUTO_INDENT']
        self.brackethl = PROFILE["BRACKETHL"]
        self.folding = PROFILE['CODE_FOLD']
        self.highlight = PROFILE["SYNTAX"]
        self.keywords = [ ' ' ]		# Keywords list
        self.syntax_set = list()
        self._comment = list()
        self.lang_id = 0
        self.Configure()

        # Set Up Margins 
        self.SetMarginType(MARK_MARGIN, wx.stc.STC_MARGIN_SYMBOL)
        self.SetMarginMask(MARK_MARGIN, self.ED_STC_MASK_MARKERS)
        self.SetMarginSensitive(MARK_MARGIN, True)
        self.SetMarginWidth(MARK_MARGIN, 12)

        ## Outer Left Margin Line Number Indication
        self.SetMarginType(NUM_MARGIN, wx.stc.STC_MARGIN_NUMBER)
        self.SetMarginMask(NUM_MARGIN, 0)
        if PROFILE['SHOW_LN']:
            self.SetMarginWidth(NUM_MARGIN, 30)
        else:
            self.SetMarginWidth(NUM_MARGIN, 0)

        ## Inner Left Margin Setup Folders
        self.SetMarginType(FOLD_MARGIN, wx.stc.STC_MARGIN_SYMBOL)
        self.SetMarginMask(FOLD_MARGIN, wx.stc.STC_MASK_FOLDERS)
        self.SetMarginSensitive(FOLD_MARGIN, True)
        if self.folding:
            self.SetMarginWidth(FOLD_MARGIN, 12)
        else:
            self.SetMarginWidth(FOLD_MARGIN, 0)

        # Set Default Styles used by all documents
        if self.highlight:
            self.UpdateBaseStyles()
        else:
            self.StyleDefault()

        # Configure Autocompletion
        # NOTE: must be done after syntax configuration
        if self._use_autocomp:
            self.ConfigureAutoComp()

        ### Folder Marker Styles
        self.DefineMarkers()

        # Events
        if self.brackethl:
            self.Bind(wx.stc.EVT_STC_UPDATEUI, self.OnUpdateUI)
        self.Bind(wx.stc.EVT_STC_MARGINCLICK, self.OnMarginClick)
        self.Bind(wx.EVT_CHAR, self.OnChar)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
       #---- End Init ----#

    __name__ = u"EditraTextCtrl"

    #---- Begin Function Definitions ----#
    def AddLine(self, before=False):
        """Add a new line to the document"""
        line = self.LineFromPosition(self.GetCurrentPos())
        if before:
            line = line - 1
            if line < 0:
                line = 0
        pos = self.GetLineEndPosition(line)
        self.InsertText(pos, self.GetEOLChar())
        self.GotoPos(pos + 1)

    def Configure(self):
        """Configures the editors settings by using profile values"""
        self.SetWrapMode(PROFILE['WRAP']) 
        self.SetViewWhiteSpace(PROFILE['SHOW_WS'])
        self.SetUseAntiAliasing(PROFILE['AALIASING'])
        self.SetUseTabs(PROFILE['USETABS'])
        self.SetIndent(int(PROFILE['TABWIDTH']))
        self.SetTabWidth(int(PROFILE['TABWIDTH']))
        self.SetIndentationGuides(PROFILE['GUIDES'])
        self.SetEOLFromString(PROFILE['EOL'])
        self.SetViewEOL(PROFILE['SHOW_EOL'])
        self.SetAutoComplete(PROFILE['AUTO_COMP'])
        self.FoldingOnOff(PROFILE['CODE_FOLD'])
        self.SyntaxOnOff(PROFILE['SYNTAX'])
        self.ToggleAutoIndent(PROFILE['AUTO_INDENT'])
        self.ToggleBracketHL(PROFILE['BRACKETHL'])
        self.ToggleLineNumbers(PROFILE['SHOW_LN'])

    def Comment(self, uncomment=False):
        """(Un)Comments a line or a selected block of text
        in a document.

        """
        if self.GetLexer() == wx.stc.STC_LEX_NULL or not len(self._comment):
            return
        else:
            sel = self.GetSelection()
            start = self.LineFromPosition(sel[0])
            end = self.LineFromPosition(sel[1])
            c_start = self._comment[0] + " "
            c_end = u''
            if len(self._comment) > 1:
                c_end = " " + self._comment[1]
            if end > start and self.GetColumn(sel[1]) == 0:
                end = end - 1
            self.BeginUndoAction()
            try:
                nchars = 0
                lines = range(start, end+1)
                lines.reverse()
                for lineNumber in lines:
                    lstart = self.PositionFromLine(lineNumber)
                    lend = self.GetLineEndPosition(lineNumber)
                    text = self.GetTextRange(lstart, lend)
                    if len(text.strip()):
                        if not uncomment:
                            text = c_start + text + c_end
                            nchars = nchars + len(c_start + c_end)
                        else:
                            text = text.replace(c_start, u'', 1)
                            if len(c_end):
                                text = text.replace(c_end, u'', 1)
                            nchars = nchars - len(c_start + c_end)
                        self.SetTargetStart(lstart)
                        self.SetTargetEnd(lend)
                        self.ReplaceTarget(text)
            finally:
                self.EndUndoAction()
                self.SetSelection(sel[0], sel[1] + nchars)

    def GetAutoIndent(self):
        """Returns whether auto-indent is being used"""
        return self._autoindent

    def GetPos(self, key):
        """ Update Line/Column information """
        pos = self.GetCurrentPos()
        self.line = self.GetCurrentLine()
        self.column = self.GetColumn(pos)
        if (self.old_pos != pos):
            self.old_pos = pos
            if self._use_autocomp:
                key_code = key.GetKeyCode()
                if key_code == wx.WXK_RETURN:
                    self._autocomp_svc.UpdateNamespace(True)
            return (self.line + 1, self.column)
        else:
            return (-1, -1)

    def DefineMarkers(self):
        """Defines the folder and bookmark icons for this control"""
        back = self.GetDefaultForeColour()
        fore = self.GetDefaultBackColour()
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDEROPEN, 
                          wx.stc.STC_MARK_BOXMINUS, fore, back)
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDER,
                          wx.stc.STC_MARK_BOXPLUS,  fore, back)
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDERSUB,     
                          wx.stc.STC_MARK_VLINE, fore, back)
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDERTAIL,
                          wx.stc.STC_MARK_LCORNER, fore, back)
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDEREND,
                          wx.stc.STC_MARK_BOXPLUSCONNECTED, fore, back)
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDEROPENMID, 
                          wx.stc.STC_MARK_BOXMINUSCONNECTED, fore, back)
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDERMIDTAIL, 
                          wx.stc.STC_MARK_TCORNER, fore, back)
        self.MarkerDefine(0, wx.stc.STC_MARK_SHORTARROW, fore, back)
        self.SetFoldMarginHiColour(True, fore)
        self.SetFoldMarginColour(True, fore)

    def FindTagById(self, id):
        """Find the style tag that is associated with the given
        Id. If not found it returns an empty string.

        """
        for data in self.syntax_set:
            if id == getattr(wx.stc, data[0]):
                return data[1]
        return wx.EmptyString

    def GetAutoComplete(self):
        """Is Autocomplete being used by this instance"""
        return self._use_autocomp

    def GetFileName(self):
        """Returns the full path name of the current file"""
        return "".join([self.dirname, self.path_char, self.filename])

    def GetStyleSheet(self):
        """Finds the current style sheet and returns its path. The
        Lookup is done by first looking in the users config directory
        and if it is not found there it looks for one on the system
        level and if that fails it returns None.

        """
        if PROFILE['SYNTHEME'].split(u'.')[-1] != u"ess":
            style = (PROFILE['SYNTHEME'] + u".ess").lower()
        else:
            style = PROFILE['SYNTHEME'].lower()
        user = os.path.join(CONFIG['STYLES_DIR'], style)
        sys = os.path.join(CONFIG['SYS_STYLES_DIR'], style)
        if os.path.exists(user):
            return user
        elif os.path.exists(sys):
            return sys
        else:
            return None

    def OnKeyDown(self, evt):
        """Handles keydown dependent events"""
        # Toggle Autocomp window by pressing button again
        k_code = evt.GetKeyCode()
        if self._autoindent and k_code == wx.WXK_RETURN:
            if self.GetSelectedText():
                self.CmdKeyExecute(wx.stc.STC_CMD_NEWLINE)
                return
            line = self.GetCurrentLine()
            text = self.GetTextRange(self.PositionFromLine(line), self.GetCurrentPos())
            if text.strip() == u'':
                self.AddText(self.GetEOLChar() + text)
                self.EnsureCaretVisible()
                return
            indent = self.GetLineIndentation(line)
            i_space = indent / self.GetTabWidth()
            ndent = self.GetEOLChar() + self.GetIndentChar() * i_space
            self.AddText(ndent + ((indent - (self.GetTabWidth() * i_space)) * u' '))
            self.EnsureCaretVisible()
        else:
            evt.Skip()

    #TODO autocomp and calltip lookup can be very cpu/time expensive
    #     when active the lookup should be done on a separate thread
    #     to help from slowing the input into the buffer
    def OnChar(self, evt):
        """Handles Char events that arent caught by the
        KEY_DOWN event.

        """
        if not self._use_autocomp:
            evt.Skip()
            return True

        key_code = evt.GetKeyCode()
        if key_code in self._autocomp_svc.GetAutoCompKeys():
            if self.AutoCompActive():
                self.AutoCompCancel()
            command = self.GetCommandStr() + chr(key_code)
            self.AddText(chr(key_code))
            if self._use_autocomp:
                self.ShowAutoCompOpt(command)
        elif key_code in self._autocomp_svc.GetCallTipKeys():
            if self.AutoCompActive():
                self.AutoCompCancel()
            command = self.GetCommandStr()
            self.AddText(chr(key_code))
            if self._use_autocomp:
                self.ShowCallTip(command)
        else:
            evt.Skip()
        return

    def GetCommandStr(self):
        curr_pos = self.GetCurrentPos()
        start = curr_pos - 1
        col = self.GetColumn(curr_pos)
        cmd_lmt = list(self._autocomp_svc.GetAutoCompStops())
        for key in self._autocomp_svc.GetAutoCompKeys():
            if chr(key) in cmd_lmt:
                cmd_lmt.remove(chr(key))
        while self.GetTextRange(start, curr_pos)[0] not in cmd_lmt \
              and col - (curr_pos - start) > 0:
            start -= 1
        s_col = self.GetColumn(start)
        if s_col != 0:
            start += 1
        cmd = self.GetTextRange(start, curr_pos)
        return cmd.strip()

    def ShowAutoCompOpt(self, command, offset=0):
        """Shows the autocompletion options list for the command"""
        lst = self._autocomp_svc.GetAutoCompList(command)
        if len(lst):
            options = u' '.join(lst)
            self.AutoCompShow(0, options)

    def ShowCallTip(self, command):
        """Shows call tip for given command"""
        if self.CallTipActive():
            self.CallTipCancel()
        tip = self._autocomp_svc.GetCallTip(command)
        if len(tip):
            curr_pos = self.GetCurrentPos()
            tip_pos = curr_pos - (len(command) + 1)
            fail_safe = curr_pos - self.GetColumn(curr_pos)
            tip_pos = max(tip_pos, fail_safe)
            self.CallTipShow(tip_pos, tip)

    def ShowKeywordHelp(self):
        """Displays the keyword helper"""
        if self.AutoCompActive():
            self.AutoCompCancel()
        elif len(self.keywords) > 1:
            pos = self.GetCurrentPos()
            pos2 = self.WordStartPosition(pos, True)
            context = pos - pos2
            self.AutoCompShow(context, self.keywords)
        return

    def OnUpdateUI(self, evt):
        """Check for matching braces"""
        braceAtCaret = -1
        braceOpposite = -1
        charBefore = None
        caretPos = self.GetCurrentPos()

        if caretPos > 0:
            charBefore = self.GetCharAt(caretPos - 1)
            styleBefore = self.GetStyleAt(caretPos - 1)

        # check before
        if charBefore and chr(charBefore) in "[]{}()<>": 
            braceAtCaret = caretPos - 1

        # check after
        if braceAtCaret < 0:
            charAfter = self.GetCharAt(caretPos)
            styleAfter = self.GetStyleAt(caretPos)
            if charAfter and chr(charAfter) in "[]{}()<>":
                braceAtCaret = caretPos

        if braceAtCaret >= 0:
            braceOpposite = self.BraceMatch(braceAtCaret)

        if braceAtCaret != -1  and braceOpposite == -1:
            self.BraceBadLight(braceAtCaret)
        else:
            self.BraceHighlight(braceAtCaret, braceOpposite)
        evt.Skip()

    def OnMarginClick(self, evt):
        """Open and Close Folders as Needed"""
        if evt.GetMargin() == FOLD_MARGIN:
            if evt.GetShift() and evt.GetControl():
                self.FoldAll()
            else:
                lineClicked = self.LineFromPosition(evt.GetPosition())
                if self.GetFoldLevel(lineClicked) & \
                   wx.stc.STC_FOLDLEVELHEADERFLAG:
                    if evt.GetShift():
                        self.SetFoldExpanded(lineClicked, True)
                        self.Expand(lineClicked, True, True, 1)
                    elif evt.GetControl():
                        if self.GetFoldExpanded(lineClicked):
                            self.SetFoldExpanded(lineClicked, False)
                            self.Expand(lineClicked, False, True, 0)
                        else:
                            self.SetFoldExpanded(lineClicked, True)
                            self.Expand(lineClicked, True, True, 100)
                    else:
                        self.ToggleFold(lineClicked)
        elif evt.GetMargin() == MARK_MARGIN:
            lineClicked = self.LineFromPosition(evt.GetPosition())
            if self.MarkerGet(lineClicked):
                self.MarkerDelete(lineClicked, MARK_MARGIN)
            else:
                self.MarkerAdd(lineClicked, MARK_MARGIN)

    def FoldAll(self):
        """Fold Tree In or Out"""
        lineCount = self.GetLineCount()
        expanding = True

        # find out if we are folding or unfolding
        for lineNum in range(lineCount):
            if self.GetFoldLevel(lineNum) & wx.stc.STC_FOLDLEVELHEADERFLAG:
                expanding = not self.GetFoldExpanded(lineNum)
                break

        lineNum = 0

        while lineNum < lineCount:
            level = self.GetFoldLevel(lineNum)

            if level & wx.stc.STC_FOLDLEVELHEADERFLAG and \
               (level & wx.stc.STC_FOLDLEVELNUMBERMASK) == \
               wx.stc.STC_FOLDLEVELBASE:

                if expanding:
                    self.SetFoldExpanded(lineNum, True)
                    lineNum = self.Expand(lineNum, True)
                    lineNum = lineNum - 1
            else:
                lastChild = self.GetLastChild(lineNum, -1)
                self.SetFoldExpanded(lineNum, False)

                if lastChild > lineNum:
                    self.HideLines(lineNum+1, lastChild)

            lineNum = lineNum + 1

    def Expand(self, line, doExpand, force=False, visLevels=0, level=-1):
        """Open the Margin Folder"""
        lastChild = self.GetLastChild(line, level)
        line = line + 1

        while line <= lastChild:
            if force:
                if visLevels > 0:
                    self.ShowLines(line, line)
                else:
                    self.HideLines(line, line)
            else:
                if doExpand:
                    self.ShowLines(line, line)

            if level == -1:
                level = self.GetFoldLevel(line)

            if level & wx.stc.STC_FOLDLEVELHEADERFLAG:
                if force:
                    self.SetFoldExpanded(line, visLevels > 1)
                    line = self.Expand(line, doExpand, force, visLevels-1)
                else:
                    if doExpand and self.GetFoldExpanded(line):
                        line = self.Expand(line, True, force, visLevels-1)
                    else:
                        line = self.Expand(line, False, force, visLevels-1)
            else:
                line = line + 1
        return line

    def FindLexer(self, set_ext=0):
        """Sets Text Controls Lexer Based on File Extension"""
        if not self.highlight:
            return 2

        if not isinstance(set_ext, int):
            ext = set_ext.lower()
        else:
            ext = util.GetExtension(self.filename).lower()
        self.ClearDocumentStyle()

        # Configure Lexer from File Extension
        # TODO add more comprehensive file type checking, the use of just
        # the file extension is not always accurate such as in the case of
        # many shell scripts that often dont use file extensions
        self.ConfigureLexer(ext)
        self.Colourise(0, -1)
        # Configure Autocompletion
        # NOTE: must be done after syntax configuration
        if self._use_autocomp:
            self.ConfigureAutoComp()
        return 0

    def ControlDispatch(self, evt):
        """Dispatches events caught from the mainwindow to the
        proper functions in this module.

        """
        e_id = evt.GetId()
        e_obj = evt.GetEventObject()
        e_type = evt.GetEventType()
        e_map = { ID_COPY  : self.Copy,         ID_CUT  : self.Cut,
                  ID_PASTE : self.Paste,        ID_UNDO : self.Undo,
                  ID_REDO  : self.Redo,         ID_KWHELPER: self.ShowKeywordHelp,
                  ID_CUT_LINE : self.LineCut,   ID_BRACKETHL : self.ToggleBracketHL,
                  ID_COPY_LINE : self.LineCopy, ID_SYNTAX : self.SyntaxOnOff,
                  ID_INDENT : self.Tab,         ID_UNINDENT : self.BackTab,
                  ID_TRANSPOSE : self.LineTranspose, ID_SELECTALL: self.SelectAll,
                  ID_FOLDING : self.FoldingOnOff, ID_SHOW_LN : self.ToggleLineNumbers,
                  ID_COMMENT : self.Comment, ID_AUTOINDENT : self.ToggleAutoIndent,
                  ID_LINE_AFTER : self.AddLine
        }
        if e_obj.GetClassName() == "wxToolBar":
            self.LOG("[stc_evt] Caught Event Generated by ToolBar")
            if e_map.has_key(e_id):
                e_map[e_id]()
            return

        if e_id in [ID_ZOOM_OUT, ID_ZOOM_IN, ID_ZOOM_NORMAL]:
            zoom_level = self.DoZoom(e_id)
        elif e_map.has_key(e_id):
            e_map[e_id]()
        elif e_id == ID_SHOW_EOL:
            self.SetViewEOL(not self.GetViewEOL())
        elif e_id == ID_SHOW_WS:
            self.SetViewWhiteSpace(not self.GetViewWhiteSpace())
        elif e_id == ID_WORD_WRAP:
            self.SetWrapMode(not bool(self.WrapMode))
        elif e_id in [ ID_NEXT_MARK, ID_PRE_MARK, ID_ADD_BM, ID_DEL_BM,
                     ID_DEL_ALL_BM]:
            n = self.GetCurrentLine()
            if e_id == ID_ADD_BM:
                self.MarkerAdd(n, MARK_MARGIN)
                return
            elif e_id == ID_DEL_BM:
                self.MarkerDelete(n, MARK_MARGIN)
                return
            elif e_id == ID_DEL_ALL_BM:
                self.MarkerDeleteAll(MARK_MARGIN)
                return
            elif e_id == ID_NEXT_MARK:
                if self.MarkerGet(n):
                    n += 1
                mark = self.MarkerNext(n, 1)
                if mark == -1:
                    mark = self.MarkerNext(0, 1)
            elif e_id == ID_PRE_MARK:
                if self.MarkerGet(n):
                    n -= 1
                mark = self.MarkerPrevious(n, 1)
                if mark == -1:
                    mark = self.MarkerPrevious(self.GetLineCount(), 1)
            if mark != -1:
                self.GotoLine(mark)
            return
        elif e_id == ID_JOIN_LINES:
            self.SetTargetStart(self.GetSelectionStart())
            self.SetTargetEnd(self.GetSelectionEnd())
            self.LinesJoin()
        elif e_id == ID_INDENT_GUIDES:
            self.SetIndentationGuides(not bool(self.GetIndentationGuides()))
        elif e_id in [ID_EOL_MAC, ID_EOL_UNIX, ID_EOL_WIN]:
            self.ConvertLineMode(e_id)
        elif e_id in syntax.SyntaxIds():
            f_ext = syntax.GetExtFromId(e_id)
            self.LOG("[stc_evt] Manually Setting Lexer to " + str(f_ext))
            self.FindLexer(f_ext)
        elif e_id == ID_AUTOCOMP:
            self.SetAutoComplete(not self.GetAutoComplete())
        elif e_id == ID_UNCOMMENT:
            self.Comment(True)
        elif e_id == ID_LINE_BEFORE:
            self.AddLine(before=True)
        else:
            evt.Skip()

    def ConvertLineMode(self, mode_id):
        """Converts all line endings in a document to a specified
        format.

        """
        eol_map = { ID_EOL_MAC  : wx.stc.STC_EOL_CR,
                    ID_EOL_UNIX : wx.stc.STC_EOL_LF,
                    ID_EOL_WIN  : wx.stc.STC_EOL_CRLF
                  }
        self.ConvertEOLs(eol_map[mode_id])
        self.SetEOLMode(eol_map[mode_id])

    def GetEOLChar(self):
        """Gets the eol character used in document"""
        m_id = self.GetEOLModeId()
        if m_id == ID_EOL_MAC:
            return '\r'
        elif m_id == ID_EOL_WIN:
            return '\r\n'
        else:
            return '\n'

    def GetIndentChar(self):
        """Gets the indentation char used in document"""
        if self.GetUseTabs():
            return '\t'
        else:
            return ' ' * self.GetTabWidth()

    def GetEOLModeId(self):
        """Gets the id of the eol format"""
        eol_mode = self.GetEOLMode()
        eol_map = { wx.stc.STC_EOL_CR : ID_EOL_MAC,
                    wx.stc.STC_EOL_LF : ID_EOL_UNIX,
                    wx.stc.STC_EOL_CRLF : ID_EOL_WIN
                  }
        return eol_map[eol_mode]

    def SetAutoComplete(self, value):
        """Turns Autocompletion on and off"""
        if isinstance(value, bool):
            self._use_autocomp = value
            if value:
                self._autocomp_svc.LoadCompProvider(self.GetLexer())

    def SetEOLFromString(self, mode_str):
        """Sets the EOL mode from a string descript"""
        mode_map = { 'Macintosh (\\r\\n)' : wx.stc.STC_EOL_CR,
                     'Unix (\\n)' : wx.stc.STC_EOL_LF,
                     'Windows (\\r\\n)' : wx.stc.STC_EOL_CRLF
                   }
        if mode_map.has_key(mode_str):
            self.SetEOLMode(mode_map[mode_str])
        else:
            self.SetEOLMode(wx.stc.STC_EOL_LF)

    def FoldingOnOff(self, set=None):
        """Turn code folding on and off"""
        if (set == None and not self.folding) or set:
            self.LOG("[stc_evt] Code Folding Turned On")
            self.folding = True
            self.SetMarginWidth(FOLD_MARGIN, 12)
        else:
            self.LOG("[stc_evt] Code Folding Turned Off")
            self.folding = False
            self.SetMarginWidth(FOLD_MARGIN, 0)

    def SyntaxOnOff(self, set=None):
        """Turn Syntax Highlighting on and off"""
        if (set == None and not self.highlight) or set:
            self.LOG("[stc_evt] Syntax Highlighting Turned On")
            self.highlight = True
            self.FindLexer()
        else:
            self.LOG("[stc_evt] Syntax Highlighting Turned Off")
            self.highlight = False
            self.SetLexer(wx.stc.STC_LEX_NULL)
            self.StyleDefault()
        return 0

    def ToggleAutoIndent(self, set=None):
        """Toggles Auto-indent On and Off"""
        if (set == None and not self._autoindent) or set:
            self._autoindent = True
        else:
            self._autoindent = False

    def ToggleBracketHL(self, set=None):
        """Toggle Bracket Highlighting On and Off"""
        if (set == None and not self.brackethl) or set:
            self.LOG("[stc_evt] Bracket Highlighting Turned On")
            self.brackethl = True
            self.Bind(wx.stc.EVT_STC_UPDATEUI, self.OnUpdateUI)
        else:
            self.LOG("[stc_evt] Bracket Highlighting Turned Off")
            self.brackethl = False
            self.Unbind(wx.stc.EVT_STC_UPDATEUI)

    def ToggleLineNumbers(self, set=None):
        """Toggles the visibility of the line number margin"""
        if (set == None and not self.GetMarginWidth(NUM_MARGIN)) or set:
            self.LOG("[stc_evt] Showing Line Numbers")
            self.SetMarginWidth(NUM_MARGIN, 30)
        else:
            self.LOG("[stc_evt] Hiding Line Numbers")
            self.SetMarginWidth(NUM_MARGIN, 0)

    def Save(self):
        """Save Text To File"""
        if self.filename != '':
            path = self.dirname + self.path_char + self.filename
            try:
                self.SaveFile(path)
                self.SetSavePoint()
                result = wx.ID_OK
            except IOError,msg:
                self.LOG("[stc] [exception] " + str(msg))
                result = msg
        return result

    def SaveAs(self, path):
        """Save Text to File using specified name"""
        try:
            self.SaveFile(path)
        except IOError,msg:
            self.LOG("[stc] [exception] Failed to perform SaveAs on File")
            return msg
        self.filename = util.GetFileName(path)
        self.dirname = util.GetPathName(path)
        self.SetSavePoint()
        self.FindLexer()
        return wx.ID_OK

    def DoZoom(self, mode):
        """Zoom control in or out"""
        id_type = mode
        zoomlevel = self.GetZoom()
        if id_type == ID_ZOOM_OUT:
            if zoomlevel > -9:
                self.ZoomOut()
        elif id_type == ID_ZOOM_IN:
            if zoomlevel < 19:
                self.ZoomIn()
        else:
            self.SetZoom(0)
        return self.GetZoom()

    def ConfigureAutoComp(self):
        """Sets up the Autocompleter, the autocompleter
        configuration depends on the currently set lexer

        """
        self.AutoCompSetAutoHide(False)
        self._autocomp_svc.LoadCompProvider(self.GetLexer())
        case = self._autocomp_svc.GetIgnoreCase()
        self.AutoCompSetIgnoreCase(case)
        stops = self._autocomp_svc.GetAutoCompStops()
        self.AutoCompStops(stops)
        self._autocomp_svc.UpdateNamespace(True)

    def ConfigureLexer(self, file_ext):
        """Sets Lexer and Lexer Keywords for the specifed file extension"""
        syn_data = syntax.SyntaxData(file_ext)

        # Set the ID of the selected lexer
        try:
           self.lang_id = syn_data[syntax.LANGUAGE]
        except KeyError:
           self.lang_id = 0

        lexer = syn_data[syntax.LEXER]
        # Check for special cases
        if lexer in [ wx.stc.STC_LEX_HTML, wx.stc.STC_LEX_XML]:
            self.SetStyleBits(7)
        elif lexer == wx.stc.STC_LEX_NULL:
            self.SetIndentationGuides(False)
            self.UpdateBaseStyles()
            return 1
        else:
            pass

        try:
            keywords = syn_data[syntax.KEYWORDS]
        except KeyError:
            keywords = []
       
        try:
            synspec = syn_data[syntax.SYNSPEC]
        except KeyError:
            self.LOG("[stc] [exception] Failed to get Syntax Specifications")
            synspec = []

        try:
            props = syn_data[syntax.PROPERTIES]
        except KeyError:
            self.LOG("[stc] [exception] No Extra Properties to Set")
            props = []

        try:
            comment = syn_data[syntax.COMMENT]
        except KeyError:
            self.LOG("[stc] [exception] No Comment Pattern to set")
            comment = []

        # Set Lexer
        self.SetLexer(lexer)
        # Set Keywords
        self.SetKeyWords(keywords)
        # Set Lexer/Syntax Specifications
        self.SetSyntax(synspec)
        # Set Extra Properties
        self.SetProperties(props)
        # Set Comment Pattern
        self._comment = comment

        return True

    def SetKeyWords(self, kw_lst):
        """Sets the keywords from a list of keyword sets
        PARAM: kw_lst [ (KWLVL, "KEWORDS"), (KWLVL2, "KEYWORDS2"), ect...]

        """
        # Parse Keyword Settings List simply ignoring bad values and badly
        # formed lists
        self.keywords = ""
        for kw in kw_lst:
            if len(kw) != 2:
                continue
            else:
                if not isinstance(kw[0], int):
                    continue
                elif not isinstance(kw[1], basestring):
                    continue
                else:
                    self.keywords += kw[1]
                    wx.stc.StyledTextCtrl.SetKeyWords(self, kw[0], kw[1])
        #TODO These next four lines are very expensive for languages with
        # many keywords. 
        kwlist = self.keywords.split()      # Split into a list of words
        kwlist = list(set(kwlist))          # Uniqueify the list
        kwlist.sort()                       # Sort into alphbetical order
        self.keywords = " ".join(kwlist)    # Put back into a string
        return True
 
    def SetSyntax(self, syn_lst):
        """Sets the Syntax Style Specs from a list of specifications
        PARAM: syn_lst = [(STYLE_ID, "STYLE_TYPE"), (STYLE_ID2, "STYLE_TYPE2)]

        """
        # Parses Syntax Specifications list, ignoring all bad values
        self.UpdateBaseStyles()
        valid_settings = list()
        for syn in syn_lst:
            if len(syn) != 2:
                self.LOG("[ed_stc][warn] Error setting syntax spec")
                continue
            else:
                if not isinstance(syn[0], basestring) or not hasattr(wx.stc, syn[0]):
                    self.LOG("[ed_stc][warn] Unknown syntax region: %s" % str(syn[0]))
                    continue
                elif not isinstance(syn[1], basestring):
                    self.LOG("[ed_stc][warn] Improperly formated style tag: %s" % str(syn[1]))
                    continue
                else:
                    self.StyleSetSpec(getattr(wx.stc, syn[0]), self.GetStyleByName(syn[1]))
                    valid_settings.append(syn)
        self.syntax_set = valid_settings
        return True

    def SetProperties(self, prop_lst):
        """Sets the Lexer Properties from a list of specifications
        PARAM: prop_lst = [ ("PROPERTY", "VAL"), ("PROPERTY2", "VAL2) ]

        """
        # Parses Property list, ignoring all bad values
        for prop in prop_lst:
            if len(prop) != 2:
                continue
            else:
                if not isinstance(prop[0], basestring) or not isinstance(prop[1], basestring):
                    continue
                else:
                    self.SetProperty(prop[0], prop[1])
        return True

    #---- End Function Definitions ----#

    #---- Style Function Definitions ----#
    def RefreshStyles(self):
        self.Freeze()
        self.StyleClearAll()
        self.UpdateBaseStyles()
        self.SetSyntax(self.syntax_set)
        self.DefineMarkers()
        self.Thaw()
        self.Refresh()

    def StyleDefault(self):
        """Clears the editor styles to default"""
        self.StyleResetDefault()
        self.StyleClearAll()
        self.SetCaretForeground(wx.NamedColor("black"))
        self.Colourise(0,-1)

    def UpdateBaseStyles(self):
        """Updates the base styles of editor to the current settings"""
       # self.keywords = [ ' ' ]
        self.StyleDefault()
        self.SetMargins(0, 0)
        # Global default styles for all languages
        self.StyleSetSpec(wx.stc.STC_STYLE_DEFAULT, self.GetStyleByName('default_style'))
        self.StyleSetSpec(wx.stc.STC_STYLE_LINENUMBER, self.GetStyleByName('line_num'))
        self.StyleSetSpec(wx.stc.STC_STYLE_CONTROLCHAR, self.GetStyleByName('ctrl_char'))
        self.StyleSetSpec(wx.stc.STC_STYLE_BRACELIGHT, self.GetStyleByName('brace_good'))
        self.StyleSetSpec(wx.stc.STC_STYLE_BRACEBAD, self.GetStyleByName('brace_bad'))
        calltip = self.GetItemByName('calltip')
        self.CallTipSetBackground(calltip.GetBack())
        self.CallTipSetForeground(calltip.GetFore())
        self.SetCaretForeground(self.GetDefaultForeColour())
        self.DefineMarkers()

    def UpdateAllStyles(self, spec_style=None):
        """Refreshes all the styles and attributes of the control"""
        if spec_style == None:
            self.LoadStyleSheet(self.GetStyleSheet())
        else:
            self.LoadStyleSheet(os.path.join(CONFIG['STYLES_DIR'], spec_style + u".ess"))
        self.UpdateBaseStyles()
        self.SetSyntax(self.syntax_set)
        self.DefineMarkers()
        self.Refresh()

    #---- End Style Definitions ----#