############################################################################
#    Copyright (C) 2007 Cody Precord                                       #
#    cprecord@editra.org                                                   #
#                                                                          #
#    Editra is free software; you can redistribute it and#or modify        #
#    it under the terms of the GNU General Public License as published by  #
#    the Free Software Foundation; either version 2 of the License, or     #
#    (at your option) any later version.                                   #
#                                                                          #
#    Editra is distributed in the hope that it will be useful,             #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of        #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         #
#    GNU General Public License for more details.                          #
#                                                                          #
#    You should have received a copy of the GNU General Public License     #
#    along with this program; if not, write to the                         #
#    Free Software Foundation, Inc.,                                       #
#    59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.             #
############################################################################

"""
#--------------------------------------------------------------------------#
# FILE: ed_menu.py                                                         #
# AUTHOR: Cody Precord                                                     #
# LANGUAGE: Python                                                         #
# SUMMARY:                                                                 #
#   Provides a more convenient menu class for the editor.                  #
#                                                                          #
# METHODS:
#
#
#
#--------------------------------------------------------------------------#
"""

__author__ = "Cody Precord <cprecord@editra.org>"
__cvsid__ = "$Id: Exp $"
__revision__ = "$Revision:  $"

#--------------------------------------------------------------------------#
# Dependancies
import os
import wx
import ed_glob

#--------------------------------------------------------------------------#
# Globals
_ = wx.GetTranslation

#--------------------------------------------------------------------------#

class ED_Menu(wx.Menu):
    """Overides the default wxMenu class to make it easier to
    customize and access items.

    """
    def __init__(self, title=wx.EmptyString, style=0):
        """Initialize a Menu Object"""
        wx.Menu.__init__(self, title, style)

    def Append(self, id, text=u'', help=u'', kind=wx.ITEM_NORMAL, use_bmp=True):
        """Append a MenuItem"""
        item = wx.MenuItem(self, id, text, help, kind)
        self.AppendItem(item)
        return item

    def AppendItem(self, item, use_bmp=True):
        """Appends a MenuItem to the menu and adds an associated
        bitmap if one is available, unless use_bmp is set to false.

        """
        if use_bmp and item.GetKind() == wx.ITEM_NORMAL:
            self.SetItemBitmap(item)
        wx.Menu.AppendItem(self, item)

    def Insert(self, pos, id, text=u'', help=u'', kind=wx.ITEM_NORMAL, use_bmp=True):
        """Insert an item at position and attach a bitmap
        if one is available.

        """
        item = wx.Menu.Insert(self, pos, id, text, help, kind)
        if use_bmp and kind == wx.ITEM_NORMAL:
            self.SetItemBitmap(item)
        return item

    def InsertAfter(self, item_id, id, label=u'', help=u'', 
                    kind=wx.ITEM_NORMAL, use_bmp=True):
        """Inserts the given item after the specified item id in
        the menu. If the id cannot be found then the item will appended
        to the end of the menu.

        """
        for pos in range(self.GetMenuItemCount()):
            mitem = self.FindItemByPosition(pos)
            if mitem.GetId() == item_id:
                break
        if pos:
            mitem = self.Insert(pos+1, id, label, help, kind, use_bmp)
        else:
            mitem = self.Append(id, label, help, kind, use_bmp)
        return mitem

    def InsertBefore(self, item_id, id, label=u'', help=u'', 
                    kind=wx.ITEM_NORMAL, use_bmp=True):
        """Inserts the given item before the specified item id in
        the menu. If the id cannot be found then the item will appended
        to the end of the menu.

        """
        for pos in range(self.GetMenuItemCount()):
            mitem = self.FindItemByPosition(pos)
            if mitem.GetId() == item_id:
                break
        if pos:
            mitem = self.Insert(pos, id, label, help, kind, use_bmp)
        else:
            mitem = self.Append(id, label, help, kind, use_bmp)
        return mitem

    def InsertAlpha(self, id, label=u'', help=u'', 
                    kind=wx.ITEM_NORMAL, after=0, use_bmp=True):
        """Attempts to insert the new menuitem into the menu
        alphabetically. The optional parameter 'after' is used
        specify an item id to start the alphabetical lookup after.
        Otherwise the lookup begins from the first item in the menu.

        """
        if after:
            start = False
        else:
            start = True
        for pos in range(self.GetMenuItemCount()):
            mitem = self.FindItemByPosition(pos)
            if mitem.IsSeparator():
                continue
            mlabel = mitem.GetLabel()
            if after and mitem.GetId() == after:
                start = True
                continue
            if after and not start:
                continue
            if label < mlabel:
                break
        last_ind = self.GetMenuItemCount() - 1
        l_item = self.FindItemByPosition(last_ind)
        if pos == last_ind and (l_item.IsSeparator() or label > mlabel):
            mitem = self.Append(id, label, help, kind, use_bmp)
        else:
            mitem = self.Insert(pos, id, label, help, kind, use_bmp)
        return mitem

    def RemoveItemByName(self, name):
        """Removes an item by the label. It will remove the first
        item matching the given name in the menu, the matching is
        case sensitive. The return value is the either the id of the
        removed item or None if the item was not found.

        """
        id = None
        for pos in range(self.GetMenuItemCount()):
            item = self.FindItemByPosition(pos)
            if name == item.GetLabel():
                id = item.GetId()
                self.Remove(id)
                break
        return id

    def SetItemBitmap(self, item):
        """Sets the MenuItems bitmap by getting the id from the
        artprovider if one exists.

        """
        try:
            bmp = wx.ArtProvider.GetBitmap(str(item.GetId()), wx.ART_MENU)
            if not bmp.IsNull():
                item.SetBitmap(bmp)
        finally:
            pass

class ED_MenuBar(wx.MenuBar):
    """Custom menubar to allow for easier access and updating
    of menu components.
    
    """
    def __init__(self, style=0):
        """Initializes the Menubar"""
        wx.MenuBar.__init__(self, style)
        self._filehistorymenu = ED_Menu()
        self._filemenu = self.GenFileMenu()
        self._whitespaceformatmenu = ED_Menu()
        self._lineformatmenu = ED_Menu()
        self._editmenu = self.GenEditMenu()
        self._vieweditmenu = ED_Menu()
        self._viewmenu = self.GenViewMenu()
        self._formatmenu = self.GenFormatMenu()
        self._settingsmenu = self.GenSettingsMenu()
        self._toolsmenu = self.GenToolsMenu()
        self._helpmenu = self.GenHelpMenu()

    # TODO these Gen functions should be broken up to the components
    #      that supply the functionality and inserted in the menus on
    #      init when the editor loads an associated widget. But this
    #      is the first step to get there.
    def GenFileMenu(self):
        """Makes and attaches the file menu"""
        filemenu = ED_Menu()
        filehist = self._filehistorymenu
        filemenu.Append(ed_glob.ID_NEW, _("New") + u"\tCtrl+N", 
                        _("Start a New File"))
        filemenu.Append(ed_glob.ID_OPEN, _("Open") + "\tCtrl+O", _("Open"))
        ## Setup File History in the File Menu
        filemenu.AppendMenu(ed_glob.ID_FHIST, _("Open Recent"), 
                            filehist, _("Recently Opened Files"))
        filemenu.AppendSeparator()
        filemenu.Append(ed_glob.ID_CLOSE, _("Close Page") + "\tCtrl+W", 
                        _("Close Current Page"))
        filemenu.Append(ed_glob.ID_CLOSEALL, _("Close All Pages"),
                        _("Close all open tabs"))
        filemenu.AppendSeparator()
        filemenu.Append(ed_glob.ID_SAVE, _("Save") + "\tCtrl+S", 
                        _("Save Current File"))
        filemenu.Append(ed_glob.ID_SAVEAS, _("Save As") + "\tCtrl+Shift+S", 
                        _("Save As"))
        filemenu.Append(ed_glob.ID_SAVEALL, _("Save All"), _("Save all open pages")) 
        filemenu.AppendSeparator()
        filemenu.Append(ed_glob.ID_SAVE_PROFILE, _("Save Profile"), 
                             _("Save Current Settings to a New Profile"))
        filemenu.Append(ed_glob.ID_LOAD_PROFILE, _("Load Profile"), 
                        _("Load a Custom Profile"))
        filemenu.AppendSeparator()
        filemenu.Append(ed_glob.ID_PRINT_SU, _("Page Setup") + "\tCtrl+Shift+P",
                        _("Configure Printer"))
        filemenu.Append(ed_glob.ID_PRINT_PRE, _("Print Preview"), 
                        _("Preview Printout"))
        filemenu.Append(ed_glob.ID_PRINT, _("Print") + "\tCtrl+P", 
                        _("Print Current File"))
        filemenu.AppendSeparator()
        filemenu.Append(ed_glob.ID_EXIT, _("Exit") + "\tAlt+Q", 
                        _("Exit the Program"))
        self.Append(filemenu, _("File"))
        return filemenu

    def GenEditMenu(self):
        """Makes and attaches the edit menu"""
        editmenu = ED_Menu()
        editmenu.Append(ed_glob.ID_UNDO, _("Undo") + "\tCtrl+Z", 
                        _("Undo Last Action"))
        editmenu.Append(ed_glob.ID_REDO, _("Redo") + "\tCtrl+Shift+Z", 
                        _("Redo Last Undo"))
        editmenu.AppendSeparator()
        editmenu.Append(ed_glob.ID_CUT, _("Cut") + "\tCtrl+X", 
                        _("Cut Selected Text from File"))
        editmenu.Append(ed_glob.ID_COPY, _("Copy") + "\tCtrl+C", 
                        _("Copy Selected Text to Clipboard"))
        editmenu.Append(ed_glob.ID_PASTE, _("Paste") + "\tCtrl+V", 
                        _("Paste Text from Clipboard to File"))
        editmenu.AppendSeparator()
        editmenu.Append(ed_glob.ID_SELECTALL, _("Select All") + "\tCtrl+A", 
                        _("Select All Text in Document"))
        editmenu.AppendSeparator()
        linemenu = ED_Menu()
        linemenu.Append(ed_glob.ID_LINE_AFTER, _("New Line After") + "\tCtrl+L",
                         _("Add a new line after the current line"))
        linemenu.Append(ed_glob.ID_LINE_BEFORE, 
                        _("New Line Before") + "\tCtrl+Shift+L",
                        _("Add a new line before the current line"))
        linemenu.AppendSeparator()
        linemenu.Append(ed_glob.ID_CUT_LINE, _("Cut Line") + "\tCtrl+D",
                        _("Cut Current Line"))
        linemenu.Append(ed_glob.ID_COPY_LINE, _("Copy Line") + "\tCtrl+Y",
                        _("Copy Current Line"))
        linemenu.AppendSeparator()
        linemenu.Append(ed_glob.ID_JOIN_LINES, _("Join Lines") + "\tCtrl+J",
                        _("Join the Selected Lines"))
        linemenu.Append(ed_glob.ID_TRANSPOSE, _("Transpose Line") + "\tCtrl+T",
                        _("Transpose the current line with the previous one"))
        editmenu.AppendMenu(ed_glob.ID_LINE_EDIT, _("Line Edit"), linemenu,
                            _("Commands that affect an entire line"))
        bookmenu = ED_Menu()
        bookmenu.Append(ed_glob.ID_ADD_BM, _("Add Bookmark") + u"\tCtrl+B",
                        _("Add a bookmark to the current line"))
        bookmenu.Append(ed_glob.ID_DEL_BM, _("Remove Bookmark") + u"\tCtrl+Shift+B",
                        _("Remove bookmark from current line"))
        bookmenu.Append(ed_glob.ID_DEL_ALL_BM, _("Remove All Bookmarks"),
                        _("Remove all bookmarks from the current document"))
        editmenu.AppendMenu(ed_glob.ID_BOOKMARK, _("Bookmarks"),  bookmenu,
                            _("Add and remove bookmarks"))
        editmenu.AppendSeparator()
        editmenu.Append(ed_glob.ID_FIND, _("Find") + "\tCtrl+Shift+F", 
                        _("Find Text"))
        editmenu.Append(ed_glob.ID_FIND_REPLACE, _("Find/Replace") + "\tCtrl+R", 
                        _("Find and Replace Text"))
        editmenu.Append(ed_glob.ID_QUICK_FIND, _("Quick Find") + "\tCtrl+F", 
                        _("Open the Quick Find Bar"))
        editmenu.AppendSeparator()
        editmenu.Append(ed_glob.ID_PREF, _("Preferences"), 
                        _("Edit Preferences / Settings"))
        self.Append(editmenu, _("Edit"))
        return editmenu

    def GenViewMenu(self):
        """Makes and attaches the view menu"""
        viewmenu = ED_Menu()
        viewmenu.Append(ed_glob.ID_ZOOM_OUT, _("Zoom Out") + "\tCtrl+-", 
                        _("Zoom Out"))
        viewmenu.Append(ed_glob.ID_ZOOM_IN, _("Zoom In") + "\tCtrl++", 
                        _("Zoom In"))
        viewmenu.Append(ed_glob.ID_ZOOM_NORMAL, _("Zoom Default") + "\tCtrl+0", 
                        _("Zoom Default"))
        viewmenu.AppendSeparator()
        self._vieweditmenu.Append(ed_glob.ID_INDENT_GUIDES, _("Indentation Guides"), 
                                  _("Show Indentation Guides"), wx.ITEM_CHECK)
        self._vieweditmenu.Append(ed_glob.ID_SHOW_EDGE, _("Show Edge Guide"),
                                  _("Show the edge column guide"), wx.ITEM_CHECK)
        self._vieweditmenu.Append(ed_glob.ID_SHOW_EOL, _("Show EOL Markers"),
                                  _("Show EOL Markers"), wx.ITEM_CHECK)
        self._vieweditmenu.Append(ed_glob.ID_SHOW_LN, _("Show Line Numbers"), 
                                  _("Show Line Number Margin"), wx.ITEM_CHECK)
        self._vieweditmenu.Append(ed_glob.ID_SHOW_WS, _("Show Whitespace"), 
                                  _("Show Whitespace Markers"), wx.ITEM_CHECK)
        viewmenu.AppendSubMenu(self._vieweditmenu, _("Editor"), \
                               _("Toggle Editor View Options"))
        viewmenu.AppendSeparator()
        viewmenu.Append(ed_glob.ID_GOTO_LINE, _("Goto Line") + u"\tCtrl+G",
                            _("Goto Line Number"))
        viewmenu.Append(ed_glob.ID_NEXT_MARK, _("Next Bookmark") + u"\tCtrl+Right", 
                            _("View Line of Next Bookmark"))
        viewmenu.Append(ed_glob.ID_PRE_MARK, _("Previous Bookmark") + u"\tCtrl+Left", 
                            _("View Line of Previous Bookmark"))
        viewmenu.AppendSeparator()
        viewmenu.Append(ed_glob.ID_VIEW_TOOL, _("Toolbar"), 
                             _("Show Toolbar"), wx.ITEM_CHECK)
        self.Append(viewmenu, _("View"))
        return viewmenu

    def GenFormatMenu(self):
        """Makes and attaches the format menu"""
        formatmenu = ED_Menu()
        formatmenu.Append(ed_glob.ID_FONT, _("Font"), _("Change Font Settings"))
        formatmenu.AppendSeparator()
        formatmenu.Append(ed_glob.ID_COMMENT, _("Comment Lines") + u"\tCtrl+1", 
                               _("Comment the selected lines"))
        formatmenu.Append(ed_glob.ID_UNCOMMENT, _("Uncomment Lines") + u"\tCtrl+2", 
                               _("Uncomment the selected lines"))
        formatmenu.AppendSeparator()
        formatmenu.Append(ed_glob.ID_INDENT, _("Indent Lines"), 
                              _("Indent the selected lines"))
        formatmenu.Append(ed_glob.ID_UNINDENT, _("Unindent Lines") + u"\tShift+Tab", 
                              _("Unindent the selected lines"))
        formatmenu.AppendSeparator()
        formatmenu.Append(ed_glob.ID_WORD_WRAP, _("Word Wrap"), 
                               _("Wrap Text Horizontally"), wx.ITEM_CHECK)
        formatmenu.AppendSeparator()
        whitespace = self._whitespaceformatmenu
        whitespace.Append(ed_glob.ID_SPACE_TO_TAB, _("Spaces to Tabs"),
                          _("Convert spaces to tabs in selected/all text"))
        whitespace.Append(ed_glob.ID_TAB_TO_SPACE, _("Tabs to Spaces"),
                          _("Convert tabs to spaces in selected/all text"))
        whitespace.Append(ed_glob.ID_TRIM_WS, _("Trim Trailing Whitespace"),
                          _("Remove trailing whitespace"))
        formatmenu.AppendMenu(ed_glob.ID_WS_FORMAT, _("Whitespace"), whitespace,
                              _("Whitespace formating commands"))
        lineformat = self._lineformatmenu
        lineformat.Append(ed_glob.ID_EOL_MAC, _("Macintosh (\\r)"), 
                              _("Format all EOL characters to %s Mode") % \
                              u"Macintosh (\\r)", wx.ITEM_CHECK)
        lineformat.Append(ed_glob.ID_EOL_UNIX, _("Unix (\\n)"), 
                              _("Format all EOL characters to %s Mode") % \
                              u"Unix (\\n)", wx.ITEM_CHECK)
        lineformat.Append(ed_glob.ID_EOL_WIN, _("Windows (\\r\\n)"), 
                              _("Format all EOL characters to %s Mode") % \
                              "Windows (\\r\\n)", wx.ITEM_CHECK)
        formatmenu.AppendMenu(ed_glob.ID_EOL_MODE, _("EOL Mode"), lineformat,
                                  _("End of line character formatting"))
        self.Append(formatmenu, _("Format"))
        return formatmenu

    def GenSettingsMenu(self):
        """Makes and attaches the settings menu"""
        settingsmenu = ED_Menu()
        settingsmenu.Append(ed_glob.ID_AUTOCOMP, _("Auto-Completion"),
                            _("Use Auto Completion when available"), wx.ITEM_CHECK)
        settingsmenu.Append(ed_glob.ID_AUTOINDENT, _("Auto-Indent"),
                            _("Toggle Auto-Indentation functionality"), 
                            wx.ITEM_CHECK)
        settingsmenu.Append(ed_glob.ID_BRACKETHL, _("Bracket Highlighting"), 
                            _("Highlight Brackets/Braces"), wx.ITEM_CHECK)
        settingsmenu.Append(ed_glob.ID_FOLDING, _("Code Folding"),
                            _("Toggle Code Foldering"), wx.ITEM_CHECK)
        settingsmenu.Append(ed_glob.ID_SYNTAX, _("Syntax Highlighting"), 
                            _("Color Highlight Code Syntax"), wx.ITEM_CHECK)
        # Lexer Menu Appended later by main frame
        self.Append(settingsmenu, _("Settings"))
        return settingsmenu

    def GenToolsMenu(self):
        """Makes and attaches the tools menu"""
        toolsmenu = ED_Menu()
        toolsmenu.Append(ed_glob.ID_KWHELPER,_("Keyword Helper") + u'\tCtrl+K', 
                         _("Provides a Contextual Help Menu Listing Standard "
                           "Keywords/Functions"))
        toolsmenu.Append(ed_glob.ID_PLUGMGR, _("Plugin Manager"),
                         _("Manage, Download, and Install plugins"))
        toolsmenu.Append(ed_glob.ID_STYLE_EDIT, _("Style Editor"), 
                         _("Edit the way syntax is highlighted"))
        toolsmenu.AppendSeparator()
#         toolsmenu.Append(ed_glob.ID_MACRO_START, _("Record Macro"),
#                          _("Start macro recording"))
#         toolsmenu.Append(ed_glob.ID_MACRO_STOP, _("Stop Recording"),
#                          _("Stop macro recording"))
#         toolsmenu.Append(ed_glob.ID_MACRO_PLAY, "Play Macro", "Play Macro")
        self.Append(toolsmenu, _("Tools"))
        return toolsmenu

    def GenHelpMenu(self):
        """Makes and attaches the help menu"""
        helpmenu = ED_Menu()
        helpmenu.Append(ed_glob.ID_ABOUT, _("&About") + u"...", _("About") + u"...")
        helpmenu.Append(ed_glob.ID_HOMEPAGE, _("Project Homepage"), 
                            _("Visit the project homepage %s") % ed_glob.home_page)
        helpmenu.Append(ed_glob.ID_CONTACT, _("Feedback"),
                            _("Send me bug reports and suggestions"))
        self.Append(helpmenu, _("Help"))
        return helpmenu

    def GetMenuByName(self, namestr):
        """Find and return a menu by name"""
        menu = "_%smenu" % namestr.lower()
        if hasattr(self, menu):
            return getattr(self, menu)
        else:
            return None
