# -*- coding: utf-8 -*-
""" GUI classes for FEEDEX """


from feedex_gui_utils import *








class FeedexTab(Gtk.VBox):
    """ Tabs for searches and views """

    def __init__(self, parent, **kargs):

        # Maint. stuff
        self.MW = parent
        self.config = self.MW.config

        self.type = kargs.get('type', FX_TAB_SEARCH)

        self.title = kargs.get('title',None)
  
        # Set up an unique id to match finished searches
        uniq = False
        while not uniq:
            self.uid = randint(1,1000)
            uniq = True
            for i in range(self.MW.upper_notebook.get_n_pages()):
                tb = self.MW.upper_notebook.get_nth_page(i)
                if tb is None: continue
                if tb.uid == self.uid: uniq = False


        # Needed to selected entry to the top of the list
        self.top_entry  = kargs.get('top_entry')

        # Changeable parameters/flags
        self.busy = False
        self.feed_sums = {}
        self.final_status = ''
        self.refresh_feeds = True
        self.feed_filter_id = 0

        # Local search thread
        self.search_thread = None

        self.page_no = 1


        # GUI init stuff
        Gtk.VBox.__init__(self, homogeneous = False, spacing = 0)
        
        self.header = f_label('', markup=True, wrap=False)        
        
        self.top_entry_prev = False # Is top entry in preview window?

        self.save_to_cache = True # Should this tab type be savet to cache?

        self.mutable = True # Is this tab mutable?
        self.prependable = True # Can new item be prepended to the top?


        # Setup main result table
        if self.type == FX_TAB_SEARCH:
            self.header_icon_name = 'edit-find-symbolic'
            self.table = FeedexGUITable(self, ResultGUIEntry(main_win=self.MW))
            self.table.view.set_tooltip_markup(_("""Double-click to open in browser or edit. 
Right-click for more options
Hit <b>Ctrl-F</b> for interactive search by Title
Hit <b>F2</b> for Menu
Hit <b>Ctrl-F2</b> for Quick Main Menu"""))                
            self.header.set_markup(_('Search') )



        elif self.type == FX_TAB_PLACES:
            self.header_icon_name = 'folder-open-symbolic'
            self.table = FeedexGUITable(self, ResultGUIEntry(main_win=self.MW))
            self.table.view.set_tooltip_markup(_("""Double-click to open in browser or edit. 
Right-click for more options
Hit <b>Ctrl-F</b> for interactive search by Title
Hit <b>F2</b> for Menu
Hit <b>Ctrl-F2</b> for Quick Main Menu"""))
            self.header.set_markup(_('News') )
            self.save_to_cache = False



        elif self.type == FX_TAB_CONTEXTS:
            self.header_icon_name = 'view-list-symbolic'
            self.table = FeedexGUITable(self, ResultGUIContext(main_win=self.MW))
            self.table.view.set_tooltip_markup(_("""Search phrase in context is shown here.
Double-click to open the entry containing a context.
Right-click for more options
Hit <b>Ctrl-F</b> for interactive search by Title
Hit <b>F2</b> for Menu
Hit <b>Ctrl-F2</b> for Quick Main Menu"""))
            self.header.set_markup(_('Search Contexts') )
            self.prependable = False


        elif self.type == FX_TAB_SIMILAR:
            self.header_icon_name = 'emblem-shared-symbolic'
            self.table = FeedexGUITable(self, ResultGUIEntry(main_win=self.MW))
            self.table.view.set_tooltip_markup(_("""Items similar to given entry.
Double-click to open the entry.
Right-click for more options
Hit <b>Ctrl-F</b> for interactive search by Title
Hit <b>F2</b> for Menu
Hit <b>Ctrl-F2</b> for Quick Main Menu"""))
            self.header.set_markup(_('Find Similar') )
            self.save_to_cache = False
            self.prependable = False



        elif self.type == FX_TAB_TERM_NET:
            self.header_icon_name = 'emblem-shared-symbolic'
            self.table = FeedexGUITable(self, ResultGUITerm(main_win=self.MW))
            self.table.view.set_tooltip_markup(_("""Terms related to the one queried for. 
Right-click for more options            
Hit <b>Ctrl-F</b> for interactive search
Hit <b>F2</b> for Menu
Hit <b>Ctrl-F2</b> for Quick Main Menu""") )
            self.header.set_markup(_('Term Net') )
            self.prependable = False
            self.mutable = False


        elif self.type == FX_TAB_TIME_SERIES:
            self.header_icon_name = 'histogram-symbolic'
            self.table = FeedexGUITable(self, ResultGUITimeSeries(main_win=self.MW))
            self.table.view.set_tooltip_markup(_("""Time series for Term(s). 
Right-click for more options
Hit <b>F2</b> for Menu
Hit <b>Ctrl-F2</b> for Quick Main Menu""") )
            self.header.set_markup(_('Time Series') )
            self.prependable = False
            self.mutable = False


        elif self.type == FX_TAB_RULES:
            self.header_icon_name = 'view-list-compact-symbolic'
            self.table = FeedexGUITable(self, ResultGUIRule(main_win=self.MW), grid=True)
            self.table.view.set_tooltip_markup(_("""These are manually added rules used for ranking and flagging.
Each time articles are fetched or notes added, they are matched against these rules.
Rule's weight contributes to <b>importance</b> and <b>flag</b> accordingly.
When recommending, items are sorted first by user's rules' importance, then by ranking from learned features if enabled.                                                 

Double-click to edit.
Right-click for more options
Hit <b>Ctrl-F</b> for interactive search
Hit <b>F2</b> for Menu
Hit <b>Ctrl-F2</b> for Quick Main Menu"""))
            self.header.set_markup(_('Rules') )
            self.save_to_cache = False


        elif self.type == FX_TAB_FLAGS:
            self.header_icon_name = 'marker-symbolic'
            self.table = FeedexGUITable(self, ResultGUIFlag(main_win=self.MW), grid=True)
            self.table.view.set_tooltip_markup(_("""Flags used in rules and for manual marking of Entries.
Their names, descriptions and colors are completely arbitrary and up to user.

Right-click for more options
Hit <b>Ctrl-F</b> for interactive search by Name
Hit <b>F2</b> for Menu
Hit <b>Ctrl-F2</b> for Quick Main Menu"""))
            self.header.set_markup(_('Flags') )
            self.save_to_cache = False


        elif self.type == FX_TAB_PLUGINS:
            self.header_icon_name = 'extension-symbolic'
            self.table = FeedexGUITable(self, ResultGUIPlugin(main_win=self.MW), grid=True)
            self.table.view.set_tooltip_markup(_("""Plugins available in context menus allowing user to run custom shell commands and scripts on items

Right-click for more options
Hit <b>Ctrl-F</b> for interactive search
Hit <b>F2</b> for Menu
Hit <b>Ctrl-F2</b> for Quick Main Menu"""))
            self.header.set_markup(_('Plugins') )
            self.save_to_cache = False


        elif self.type == FX_TAB_REL_TIME:
            self.header_icon_name = 'histogram-symbolic'
            self.table = FeedexGUITable(self, ResultGUITimeSeries(main_win=self.MW))
            self.table.view.set_tooltip_markup(_("""Time distribution for similar documents.
It shows how subjects prominent in a Document were relevant in a time range. 

Right-click for more options            
Hit <b>Ctrl-F</b> for interactive search
Hit <b>F2</b> for Menu
Hit <b>Ctrl-F2</b> for Quick Main Menu""") )
            self.header.set_markup(_('Entry Relevance in Time') )
            self.save_to_cache = False
            self.prependable = False
            self.mutable = False
            self.top_entry_prev = True


        elif self.type == FX_TAB_TREE:
            self.header_icon_name = 'view-filter-symbolic'
            self.table = FeedexGUITable(self, ResultGUITree(main_win=self.MW), tree=True)
            self.table.view.set_tooltip_markup(_("""Double-click to open in browser or edit. 
Right-click for more options
Hit <b>Ctrl-F</b> for interactive search by Title
Hit <b>F2</b> for Menu
Hit <b>Ctrl-F2</b> for Quick Main Menu"""))
            self.header.set_markup(_('Summary') )
            self.prependable = False


        elif self.type == FX_TAB_NOTES:
            self.header_icon_name = 'format-unordered-list-symbolic'
            self.table = FeedexGUITable(self, ResultGUINote(main_win=self.MW), notes=True)
            self.table.view.set_tooltip_markup(_("""Double-click to edit or open in browser. 
Right-click for more options
Hit <b>Ctrl-F</b> for interactive search by Title
Hit <b>F2</b> for Menu
Hit <b>Ctrl-F2</b> for Quick Main Menu"""))
            self.header.set_markup(_('Search'))


        elif self.type == FX_TAB_TRENDS:
            self.header_icon_name = 'comment-symbolic'
            self.table = FeedexGUITable(self, ResultGUITerm(main_win=self.MW))
            self.table.view.set_tooltip_markup(_("""Strongest trending terms from filtered documents
Right-click for more options
Hit <b>Ctrl-F</b> for interactive search
Hit <b>F2</b> for Menu
Hit <b>Ctrl-F2</b> for Quick Main Menu"""))
            self.header.set_markup(_('Trends'))
            self.prependable = False
            self.mutable = False


        elif self.type == FX_TAB_CATALOG:
            self.header_icon_name = 'rss-symbolic'
            self.table = FeedexGUITable(self, ResultGUICatItem(main_win=self.MW), tree=True)
            self.table.view.set_tooltip_markup(_("""Mark Channels/Categories to Import.
If Channel's parent category is selected, it will be imported as well (if a category of the same name does not exist)
<i> Sorry about this catalog being in English only :( </i> 

Hit <b>F2</b> for Menu
Hit <b>Ctrl-F2</b> for Quick Main Menu"""))
            self.header.set_markup(_('Find Feeds...'))
            self.save_to_cache = False
            self.prependable = False
            self.mutable = False



        elif self.type == FX_TAB_LEARNED:
            self.header_icon_name = 'applications-engineering-symbolic'
            self.table = FeedexGUITable(self, ResultGUIKwTerm(main_win=self.MW), grid=True, table='keywords_learned')
            self.table.view.set_tooltip_markup(_("""List of Keywords learned after <b>adding Entries</b> and <b>reading Articles</b>
They are used for recommending articles based on your previous choices.

Right-click for more options
Hit <b>Ctrl-F</b> for interactive search
Hit <b>F2</b> for Menu
Hit <b>Ctrl-F2</b> for Quick Main Menu"""))
            self.header.set_markup(_('Learned Rules'))
            self.save_to_cache = False
            self.mutable = False
            self.prependable = False




        # Value for scrollbar state of preview window
        self.prev_vadj_val = 0

        # Insert custom title
        if self.title not in (None,''):
            self.header.set_markup(self.title)

        # Tab header
        self.header_box = Gtk.HBox(homogeneous = False, spacing = 0)

        self.spinner = Gtk.Spinner()
        self.header_icon = Gtk.Image.new_from_icon_name(self.header_icon_name, Gtk.IconSize.BUTTON)

        self.header_box.pack_start(self.header_icon, False, True, 5)
        self.header_box.pack_start(self.spinner, False, True, 1)
        self.header_box.pack_start(self.header, False, False, 1)


        # Close button
        if self.type != FX_TAB_PLACES:
            close_button = f_button(None,'window-close-symbolic', connect=self._on_close, size=Gtk.IconSize.MENU)
            close_button.set_relief(Gtk.ReliefStyle.NONE)
            self.header_box.pack_end(close_button, False, False, 1)
            self.header_box.set_tooltip_markup(_("""Right-click on tab headers to quickly switch tabs
Right-click on columns or search filters for layout and filters options
Hit <b>Ctrl-F2</b> for Quick Main Menu"""))



        self.search_filters = {}


        if FEEDEX_FILTERS_PER_TABS[self.type] != {}:
            self.search_box = Gtk.HBox(homogeneous = False, spacing = 0)
            self.search_entry_box = Gtk.HBox(homogeneous = False, spacing = 0)



            if FEEDEX_FILTERS_PER_TABS[self.type].get('search') in ('combo','catalog_combo',):
            
                self.history = Gtk.ListStore(str)
                self.reload_history()
            
                (self.query_combo, self.query_entry) = f_combo_entry(self.history, connect=self.on_query, connect_button=self._clear_query_entry, tooltip_button=_('Clear search phrase'))
                self.query_entry.connect("populate-popup", self._on_query_entry_menu)
                self.query_combo.connect('button-press-event', self._on_button_press_header)
                self.query_entry.connect('changed', self._on_entry_changed)

                self.search_button      = f_button(None,'edit-find-symbolic', connect=self.on_query)
                self.search_button.connect('button-press-event', self._on_button_press_header)
                
                if FEEDEX_FILTERS_PER_TABS[self.type].get('search') == 'catalog_combo':
                    self.cat_import_button = f_button(_('Subscribe to Selected'), 'rss-symbolic', connect=self.MW.act.import_catalog, args=(self.table.result.toggled_ids,), tooltip=_('Import selected Channels for subscription')  )


            elif FEEDEX_FILTERS_PER_TABS[self.type].get('search') == 'button':

                self.search_button      = f_button(None,'edit-find-symbolic', connect=self.on_query)
                self.search_button.connect('button-press-event', self._on_button_press_header)



            if len(FEEDEX_FILTERS_PER_TABS[self.type]['filters']) > 0:
            
                self.restore_button     = f_button(None,'edit-redo-rtl-symbolic', connect=self.on_restore, tooltip=_("Restore filters to defaults")) 
                self.restore_button.connect('button-press-event', self._on_button_press_header)
                self.search_filter_box = Gtk.HBox(homogeneous = False, spacing = 0)
                self.search_filter_box.connect('button-press-event', self._on_button_press_header)

                for f in FEEDEX_FILTERS_PER_TABS[self.type]['filters']:
                    curr_widget = None
                    if f == 'time_series': 
                        curr_widget = self.time_series_combo = f_time_series_combo(ellipsize=False, tooltip=_('Select time series grouping') )
                    elif f == 'group': 
                        curr_widget = self.group_combo = f_group_combo(ellipsize=False, with_times=True, tooltip=_('Select grouping field\n<b>Grouping by Similarity will collapse similar entries into most important node</b>\n<i>Note that grouping by similarity will be very time consuming for large date ranges</i>') )
                    elif f == 'depth':
                        curr_widget = self.depth_combo = f_depth_combo(ellipsize=False, tooltip=_('Select how many top results to show for each grouping') )
                    elif f == 'rank':
                        curr_widget = self.rank_combo = f_rank_combo(ellipsize=False)
                    elif f == 'time':
                        curr_widget = self.qtime_combo = f_time_combo(connect=self.on_date_changed, ellipsize=False, tooltip=f"""{_('Filter by date')}\n<i>{_('Searching whole database can be time consuming for large datasets')}</i>""")
                    elif f == 'cat':
                        curr_widget = self.cat_combo = f_feed_combo(self.MW, connect=self._on_filters_changed, ellipsize=False, with_feeds=True, tooltip="Choose Feed or Category to search")
                    elif f == 'read':
                        curr_widget = self.read_combo = f_read_combo(connect=self._on_filters_changed, ellipsize=False, tooltip=_('Filter for Read/Unread news. Manually added entries are marked as read by default') )
                    elif f == 'flag':
                        curr_widget = self.flag_combo = f_flag_combo(connect=self._on_filters_changed, ellipsize=False, filters=True, tooltip=_('Filter by Flag or lack thereof') )
                    elif f == 'notes':
                        curr_widget = self.notes_combo = f_note_combo(search=True, ellipsize=False, tooltip=_("""Chose which item type to filter (Notes, News Items or both)"""))
                    elif f == 'handler':
                        curr_widget = self.qhandler_combo = f_handler_combo(connect=self._on_filters_changed, ellipsize=False, local=True, all=True, tooltip=_('Which handler protocols should be taken into account?') )
                    elif f == 'type':
                        curr_widget = self.qtype_combo = f_query_type_combo(connect=self._on_filters_changed, ellipsize=False, rule=False)
                    elif f == 'logic':
                        curr_widget = self.qlogic_combo = f_query_logic_combo(connect=self._on_filters_changed, ellipsize=False)
                    elif f == 'lang':
                        curr_widget = self.qlang_combo = f_lang_combo(connect=self._on_filters_changed, ellipsize=False, with_all=True)
                    elif f == 'field':
                        curr_widget = self.qfield_combo = f_field_combo(connect=self._on_filters_changed, ellipsize=False, tooltip=_('Search in All or a specific field'), all_label=_('-- No Field --') )
                    elif f == 'case':
                        curr_widget = self.case_combo = f_dual_combo( (('___dummy',_("Detect case")),('case_sens', _("Case sensitive")),('case_ins',_("Case insensitive"))), ellipsize=False, tooltip=_('Set query case sensitivity'), connect=self._on_filters_changed)
                    elif f == 'catalog_field':
                        curr_widget = self.catalog_field_combo = f_catalog_field_combo()
                    elif f == 'page':
                        self.page_len_combo     = f_page_len_combo(connect=self._on_filters_changed, ellipsize=False, tooltip=_("Choose page length for query"), default=self.config.get('page_length',3000))
                        self.page_no_label      = f_label('Page: <b>1</b>', markup=True, wrap=False, char_wrap=False)
                        self.page_prev_button   = f_button(None, 'previous', connect=self._on_page_prev)
                        self.page_next_button   = f_button(None, 'next', connect=self._on_page_next)

                        self.search_filter_box.pack_start(self.page_prev_button, False, False, 1)
                        self.search_filter_box.pack_start(self.page_no_label, False, False, 1)
                        self.search_filter_box.pack_start(self.page_next_button, False, False, 1)
                        self.search_filter_box.pack_start(self.page_len_combo, False, False, 1)
                
                    if curr_widget is not None: self.search_filter_box.pack_start(curr_widget, False, False, 1)


                self.on_restore()
                self._on_filters_changed()



        if hasattr(self, 'search_entry_box'):
            if hasattr(self, 'cat_import_button'): self.search_entry_box.pack_start(self.cat_import_button, False, False, 1) 
            if hasattr(self, 'search_button'): self.search_entry_box.pack_start(self.search_button, False, False, 1)
            if hasattr(self, 'query_combo'): self.search_entry_box.pack_start(self.query_combo, False, False, 1)
            if hasattr(self, 'restore_button'): self.search_entry_box.pack_start(self.restore_button, False, False, 1)

            search_main_entry_box = Gtk.VBox(homogeneous = False, spacing = 0)
            search_padding_box2 = Gtk.HBox(homogeneous = False, spacing = 0) 
            search_main_entry_box.pack_start(self.search_entry_box, False, False, 0)
            search_main_entry_box.pack_start(search_padding_box2, False, False, 7)
            self.search_box.pack_start(search_main_entry_box, False, False, 0)


        if hasattr(self, 'search_filter_box'):
            search_filter_scrolled = Gtk.ScrolledWindow()
            search_filter_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)           

            # This is needed to prevent scrollbar from obscuring search bar for certain themes :(
            search_main_filter_box = Gtk.VBox(homogeneous = False, spacing = 0)
            search_padding_box1 = Gtk.HBox(homogeneous = False, spacing = 0) 

            search_main_filter_box.pack_start(self.search_filter_box, False, False, 0)
            search_main_filter_box.pack_start(search_padding_box1, False, False, 7)

            search_filter_scrolled.add(search_main_filter_box)


        if hasattr(self, 'search_box'):
            self.search_box.pack_start(search_filter_scrolled, True, True, 0)
            self.pack_start(self.search_box, False, False, 0)



        table_box = Gtk.ScrolledWindow()
        table_box.add(self.table.view)
        self.pack_start(table_box, True, True, 1)

        self.table.view.connect("cursor-changed", self._on_changed_selection)
        self.table.view.connect("row-activated", self._on_activate)
        self.table.view.connect("button-press-event", self._on_button_press)
        self.connect("key-press-event", self._on_key_press)

        debug(7, f'Tab created (id: {self.uid}, type:{self.type})')


        






    def _on_button_press(self, widget, event):
        """ Click signal handler """
        if event.button == 3:
            result = self.table.get_selection()
            self.MW.action_menu(result, self, event)
            

    def _on_button_press_header(self, widget, event):
        """ Header right-click menu """
        if event.button == 3 and self.type not in (FX_TAB_FEEDS,): 
            menu = None
            if hasattr(self, 'search_filter_box'):
                if menu is None: menu = Gtk.Menu()
                else: menu.append( f_menu_item(0, 'SEPARATOR', None) )
                menu.append( f_menu_item(1, _('Save filters'), self.save_filters, icon='filter-symbolic', tooltip=_('Save current search filters as defaults for future') ) )
            
            if menu is None: menu = Gtk.Menu()
            else: menu.append( f_menu_item(0, 'SEPARATOR', None) )
            menu.append( f_menu_item(1, _('Save layout'), self.table.save_layout, icon='view-column-symbolic', tooltip=_('Save column layout and sizing for current tab.\nIt will be used as default in the future') ) )

            if menu is not None:
                menu.show_all()
                menu.popup(None, None, None, None, event.button, event.time)



    def _on_key_press(self, widget, event):
        """ When keyboard is used ... """
        key = event.keyval
        key_name = Gdk.keyval_name(key)
        state = event.state
        ctrl = (state & Gdk.ModifierType.CONTROL_MASK)

        if key_name == 'Delete':
            result = self.table.get_selection()
            if isinstance(result, (ResultEntry, ResultContext,)): self.MW.act.on_del_entry(result)
            elif isinstance(result, ResultRule) and self.type != FX_TAB_LEARNED: self.MW.on_del_rule(result)
            elif isinstance(result, ResultFlag): self.MW.act.on_del_flag(result)
            elif isinstance(result, ResultPlugin): self.MW.act.on_del_plugin(result)


        elif ctrl and key_name == self.config.get('gui_key_add','a'):
            if isinstance(self.table.result, (ResultEntry, ResultContext,)): self.MW.act.on_edit_entry(None)
            elif isinstance(self.table.result, ResultRule) and self.type != FX_TAB_LEARNED: self.MW.act.on_edit_rule(None)
            elif isinstance(self.table.result, ResultFlag): self.MW.act.on_edit_flag(None)
            elif isinstance(self.table.result, ResultPlugin): self.MW.act.on_edit_plugin(None)

        elif ctrl and key_name == self.config.get('gui_key_edit','e'):
            result = self.table.get_selection()
            if isinstance(result, (ResultEntry, ResultContext,)): self.MW.act.on_edit_entry(result)
            elif isinstance(result, ResultRule) and self.type != FX_TAB_LEARNED: self.MW.act.on_edit_rule(result)
            elif isinstance(result, ResultFlag): self.MW.act.on_edit_flag(result)
            elif isinstance(result, ResultPlugin): self.MW.act.on_edit_plugin(result)

        elif ctrl and key_name in ('F2',): pass
        
        elif key_name in ('F2',):
            event.button = 3
            result = self.table.get_selection()
            self.MW.action_menu(result, self, event)

        #debug(9, f"""{key_name}; {key}; {state}""")





    def _on_changed_selection(self, *args, **kargs):
        """ Selection change handler"""
        if isinstance(self.table.result, (ResultEntry, ResultContext,)): 
            sel = self.table.get_selection()
            if isinstance(sel, (ResultEntry, ResultContext,)): self.MW.load_preview(sel)
            else: self.MW.startup_decor()

        elif isinstance(self.table.result, ResultRule) and self.type in (FX_TAB_RULES, FX_TAB_LEARNED,): 
            sel = self.table.get_selection()
            if sel is not None: self.MW.load_preview_rule(sel)
            else: self.MW.startup_decor()
        
        elif isinstance(self.table.result, ResultCatItem): 
            sel = self.table.get_selection()
            if sel is not None: 
                if not sel.get('is_node',False): self.MW.load_preview_catalog(sel)
                else: self.MW.startup_decor(from_catalog=True)
            else: self.MW.startup_decor(from_catalog=True)





    def _on_activate(self, widget, event, *args, **kargs):
        """ Result activation handler """
        result = self.table.get_selection()
        if isinstance(result, (ResultEntry, ResultContext,)):
            if scast(result['link'],str,'').strip() != '': self.MW.act.on_open_entry(result) 
            else: self.MW.act.on_edit_entry(False, result)
        elif isinstance(result, ResultRule): self.MW.act.on_edit_rule(result)
        elif isinstance(result, ResultFlag): self.MW.act.on_edit_flag(result)
        elif isinstance(result, ResultPlugin): self.MW.act.on_edit_plugin(result)



    def _clear_query_entry(self, *args, **kargs): self.query_entry.set_text('')
    def _on_close(self, *args, **kargs): self.MW.remove_tab(self.uid, self.type)

    def _on_query_entry_menu(self, widget, menu, *args, **kargs):
        """ Basically adds "Clear History" option to menu """
        menu.append( f_menu_item(0, 'SEPARATOR', None) ) 
        menu.append( f_menu_item(1, _('Clear Search History'), self.MW.act.on_clear_history, icon='edit-clear-all-symbolic'))
        menu.show_all()

    def _on_entry_changed(self, entry, *args):
        """ Deactivate ranking combo if query phrase is not empty """
        if hasattr(self, 'rank_combo'):
            if entry.get_text().strip() == '': self.rank_combo.set_sensitive(True)
            else: self.rank_combo.set_sensitive(False)

    def save_filters(self, *args, **kargs):
        """ Save current search filters as default for the future """
        if self.type in (FX_TAB_SEARCH, FX_TAB_CONTEXTS, FX_TAB_TIME_SERIES, FX_TAB_REL_TIME, FX_TAB_TREE, FX_TAB_NOTES, FX_TAB_TRENDS):
            self.get_search_filters()
            self.MW.default_search_filters = self.search_filters.copy()
            self.MW.gui_cache['default_search_filters'] = self.search_filters.copy()
            msg(_('Filters saved as defaults') )
            debug(7, f"Changed default filters: {self.MW.gui_cache['default_search_filters']}")



    def reload_history(self, *args, **kargs):
        """ Refresh search history from DB """
        self.history.clear()
        for h in fdx.search_history_cache: self.history.append((h[0],))



    def _add_date_str_to_combo(self, date_string):
        new_d = (f'_{date_string}', date_string)
        model = self.qtime_combo.get_model()
        for d in model:
            if d[0] == new_d[0]: return 0
        model.append(new_d)
        self.qtime_combo.set_model(model)
        self.qtime_combo.set_active(len(model)-1)
        

    def on_date_changed(self, *args):
        """ React when user requests a calendar """
        if f_get_combo(self.qtime_combo) == 'choose_dates':
            
            dialog = CalendarDialog(self.MW)
            dialog.run()
            if dialog.response == 1:
                self._add_date_str_to_combo(dialog.result["date_string"])
                dialog.destroy()
            else:
                self.qtime_combo.set_active(0)
                dialog.destroy()
                return -1



    def _on_page_prev(self, *args):
        self.page_no -= 1
        self.on_query()

    def _on_page_next(self, *args):
        self.page_no += 1
        self.on_query()




    def _on_filters_changed(self, *args, **krags):
        """ Update dictionary if filters change"""
        if hasattr(self, 'qtype_combo'):
            if f_get_combo(self.qtype_combo) == 1:
                if hasattr(self, 'qlang_combo'): self.qlang_combo.set_sensitive(True)
                if hasattr(self, 'case_combo'): self.case_combo.set_sensitive(False)
                if hasattr(self, 'qlogic_combo'): self.qlogic_combo.set_sensitive(True)
                if hasattr(self, 'query_entry'): self.query_entry.set_tooltip_markup(_("""Enter your search phrase here
Special tokens: AND, OR, NOT, (,), NEAR (for logical operations)
Proximity indicator: <b>~(number of words)</b>, e.g. test ~5 example
<b><i>Capitalized words are treated as exact/unstemmed</i></b>
Escape character: \ 

Advanced wildcards:
    <b>&lt;DIV&gt;</b>      - divider (period, punctation etc.)
    <b>&lt;NUM&gt;</b>      - number
    <b>&lt;CAP&gt;</b>      - capitalized word
    <b>&lt;ALLCAP&gt;</b>   - word with all capitals
    <b>&lt;UNCOMM&gt;</b>   - uncommon word
    <b>&lt;POLYSYL&gt;</b>  - long word (3+ syllables)
    <b>&lt;CURR&gt;</b>     - currency symbol
    <b>&lt;MATH&gt;</b>     - math symbol
    <b>&lt;RNUM&gt;</b>     - Roman numeral
    <b>&lt;GREEK&gt;</b>    - Greek symbol
    <b>&lt;UNIT&gt;</b>     - unit marker/symbol

""") )
            else:
                if hasattr(self, 'case_combo'): self.case_combo.set_sensitive(True)
                if hasattr(self, 'qlang_combo'): self.qlang_combo.set_sensitive(False)
                if hasattr(self, 'qlogic_combo'): self.qlogic_combo.set_sensitive(False)
                if hasattr(self, 'query_entry'): self.query_entry.set_tooltip_markup(_("""Enter your search string here
Wildcard: <b>*</b>
Field beginning/end: <b>^,$</b>
Escape: \ (only if before wildcards and field markers)""") )

            debug(7, 'Search filters changed...')




 

    def get_search_filters(self, **kargs):
        """ Get search filters state and put it into global dictionary """
        self.search_filters = {}

        if hasattr(self, 'qtime_combo'):
            time = f_get_combo(self.qtime_combo)
            if time.startswith('_') and time != '__dummy':
                time = time[1:]
                dts = time.split(' - ')
                if dts[0] != '...': self.search_filters['date_from'] = dts[0]
                if dts[1] != '...': self.search_filters['date_to'] = dts[1]
            else:
                self.search_filters[time] = True
        
            self.search_filters[f_get_combo(self.qtime_combo)] = True

        if hasattr(self, 'cat_combo'): self.search_filters['feed_or_cat'] = f_get_combo(self.cat_combo)
        if hasattr(self, 'read_combo'): self.search_filters[f_get_combo(self.read_combo)] = True
        if hasattr(self, 'case_combo'): self.search_filters[f_get_combo(self.case_combo)] = True
        if hasattr(self, 'flag_combo'): self.search_filters['flag'] = f_get_combo(self.flag_combo)
        if hasattr(self, 'qhandler_combo'): self.search_filters['handler'] = f_get_combo(self.qhandler_combo)
        if hasattr(self, 'notes_combo'): self.search_filters['note'] = f_get_combo(self.notes_combo, null_val=-1)
        if hasattr(self, 'qfield_combo'): self.search_filters['field'] = f_get_combo(self.qfield_combo)
        if hasattr(self, 'qlang_combo'): self.search_filters['lang'] = f_get_combo(self.qlang_combo)
        if hasattr(self, 'qtype_combo'): self.search_filters['qtype'] = f_get_combo(self.qtype_combo)
        if hasattr(self, 'qlogic_combo'): self.search_filters['logic'] = f_get_combo(self.qlogic_combo)
        if hasattr(self, 'time_series_combo'): self.search_filters['group'] = f_get_combo(self.time_series_combo)
        if hasattr(self, 'group_combo'): self.search_filters['group'] = f_get_combo(self.group_combo)
        if hasattr(self, 'depth_combo'): self.search_filters['depth'] = f_get_combo(self.depth_combo)            
        if hasattr(self, 'rank_combo'): self.search_filters['rank'] = f_get_combo(self.rank_combo)

        if hasattr(self, 'page_len_combo'): 
            self.search_filters['page_len'] = f_get_combo(self.page_len_combo)
            self.search_filters['page'] = self.page_no
        else:
            self.search_filters['page_len'] = self.config.get('page_length',3000)
            self.search_filters['page'] = 1

        if hasattr(self, 'catalog_field_combo'): self.search_filters['field'] = f_get_combo(self.catalog_field_combo)       


        debug(7, f'Search filters updated: {self.search_filters}')
        return 0
        
 


    def on_restore(self, *args, **kargs):
        """ Restore default filters """
        search_filters = kargs.get('filters', self.MW.default_search_filters)

        if hasattr(self, 'qtime_combo'):
            if search_filters.get('date_from') is not None or search_filters.get('date_to') is not None:
                date_str = f"""{search_filters.get('date_from','')} - {search_filters.get('date_to','')}"""
                self._add_date_str_to_combo(date_str)
                search_filters[f'_{date_str}'] = True

            f_set_combo_from_bools(self.qtime_combo, search_filters)
                

        if hasattr(self, 'time_series_combo'): f_set_combo(self.time_series_combo, search_filters.get('group'))
        if hasattr(self, 'qtime_combo'): f_set_combo_from_bools(self.qtime_combo, search_filters)
        if hasattr(self, 'cat_combo'): f_set_combo(self.cat_combo, search_filters.get('feed_or_cat'), null_val=-1)
        if hasattr(self, 'read_combo'): f_set_combo_from_bools(self.read_combo, search_filters)
        if hasattr(self, 'case_combo'): f_set_combo_from_bools(self.case_combo, search_filters)
        if hasattr(self, 'flag_combo'): f_set_combo(self.flag_combo, scast(search_filters.get('flag'), str, '-1'))
        if hasattr(self, 'qhandler_combo'): f_set_combo(self.qhandler_combo, search_filters.get('handler'))
        if hasattr(self, 'notes_combo'): f_set_combo(self.notes_combo, search_filters.get('note'), null_val=-1)
        if hasattr(self, 'qfield_combo'): f_set_combo(self.qfield_combo, search_filters.get('field'))
        if hasattr(self, 'qlang_combo'): f_set_combo(self.qlang_combo, search_filters.get('lang'))
        if hasattr(self, 'qtype_combo'): f_set_combo(self.qtype_combo, search_filters.get('qtype'))
        if hasattr(self, 'qlogic_combo'): f_set_combo(self.qlogic_combo, search_filters.get('logic'))
        if hasattr(self, 'time_series_combo'): f_set_combo(self.time_series_combo, search_filters.get('group'))
        if hasattr(self, 'group_combo'): f_set_combo(self.group_combo, search_filters.get('group'))
        if hasattr(self, 'depth_combo'): f_set_combo(self.depth_combo, search_filters.get('depth'))
        if hasattr(self, 'rank_combo'): f_set_combo(self.rank_combo, search_filters.get('rank'))
        if hasattr(self, 'page_len_combo'): f_set_combo(self.page_len_combo, search_filters.get('page_len'))

        self._on_filters_changed()











    def block_search(self, tab_text:str):
        """ Do some maintenance on starting a search """
        if hasattr(self, 'search_button'): self.search_button.set_sensitive(False)
        if hasattr(self, 'query_combo'): self.query_combo.set_sensitive(False)
        if hasattr(self, 'page_prev_button'): self.page_prev_button.set_sensitive(False) 
        if hasattr(self, 'page_next_button'): self.page_next_button.set_sensitive(False) 

        self.header_icon.hide()
        self.spinner.show()
        self.spinner.start()
        self.header.set_markup(tab_text)




    def unblock_search(self, **kargs):
        """ Unblock search widgets """
        if hasattr(self, 'search_button'): self.search_button.set_sensitive(True)
        if hasattr(self, 'query_combo'): self.query_combo.set_sensitive(True)
        if hasattr(self, 'page_prev_button'):
            if self.page_no != 1: self.page_prev_button.set_sensitive(True)
        if hasattr(self, 'page_next_button'):
            if not self.table.result_no < f_get_combo(self.page_len_combo): self.page_next_button.set_sensitive(True)
        if hasattr(self, 'page_no_label'): self.page_no_label.set_markup(f'Page <b>{self.page_no}</b>')




    def finish_search(self, **kargs):
        """ This is called by main window when it receives signals of finished search thread
            Performs maintenance, beautifies etc.
        """
        self.busy = False
        self.unblock_search()

        self.table.commit_populate()

        if self.top_entry is not None and isinstance(self.top_entry, (ResultEntry, FeedexEntry,)):
            if self.top_entry_prev and self.MW.curr_upper.uid == self.uid: self.MW.load_preview(self.top_entry)
            if isinstance(self.table.result, (ResultEntry,)): self.table.append(self.top_entry)


        if self.type == FX_TAB_TREE:
            if self.search_filters.get('group',None) == 'similar': self.table.collapse_all()
            else: self.table.expand_all()
        elif self.type == FX_TAB_CATALOG:
            if self.query_entry.get_text().strip() != '': self.table.expand_all()
            else: self.table.collapse_all()  

        self.spinner.hide()
        self.spinner.stop()
        self.header_icon.show()
        
        if self.table.result_no2 != 0: len_str = f'{self.table.result_no} {_("of")} {self.table.result_no2}'
        else: len_str = f'{self.table.result_no}'
        self.header.set_markup( f'{self.final_status} ({len_str})' )

        if self.MW.curr_upper.uid == self.uid and self.table.feed_sums is not None:
            self.MW.feed_tab.redecorate(self.table.curr_feed_filters, self.table.feed_sums)
        
        if self.type == FX_TAB_PLACES and self.MW.curr_place in (FX_PLACE_LAST, FX_PLACE_PREV_LAST,): 
            self.MW.new_items = 0
            self.MW.new_n = 0
            self.MW.feed_tab.redecorate_new()













    def query_thr(self, qr, filters, **kargs):
        """ Wrapper for sending queries """
        # DB interface for queries
        if self.type in (FX_TAB_PLUGINS,):
            DB = None
            QP = FeedexQueryInterface()
        elif self.type in (FX_TAB_CATALOG,):
            DB = None
            QP = FeedexCatalogQuery()
        else:
            DB = FeedexDatabase(connect=True)
            DB.connect_QP()
            QP = DB.Q

        if filters is not None: rank_scheme = filters.get('rank')


        if scast(qr, str, '').replace(' ','') == '': empty = True
        else: empty = False

        err = 0

        # Do query ...
        if self.type in (FX_TAB_SEARCH, FX_TAB_NOTES):

            feed_name = f_get_combo(self.cat_combo, name=True)

            if not empty: err = QP.query(qr, filters)
            elif rank_scheme == FX_RANK_RECOM: err = QP.recommend(filters, no_history=True)
            elif rank_scheme == FX_RANK_TREND: err = QP.trending('', filters, no_history=True)
            elif rank_scheme == FX_RANK_DEBUBBLE:
                filters['rev'] = True
                err = QP.recommend(filters, no_history=True)
            else:
                filters['sort'] = 'pubdate'
                err = QP.query('', filters, no_history=True)


            if empty:
                if feed_name is None: self.final_status = _('Results')
                else: self.final_status = f'<b>{esc_mu(feed_name, ell=50)}</b>'
            else:
                if feed_name is None: self.final_status = f'{_("Search for ")}<b>{esc_mu(qr, ell=50)}</b>'
                else: self.final_status = f'{_("Search for ")}<b>{esc_mu(qr, ell=50)}</b> {_("in")} <b><i>{esc_mu(feed_name, ell=50)}</i></b>'




        elif self.type == FX_TAB_PLACES:
 
            if qr == FX_PLACE_TRASH_BIN:

                err = QP.query('', {'deleted':True, 'sort':'adddate'}, no_history=True)
                self.final_status = _('Trash bin')

            else:

                if qr == FX_PLACE_LAST:
                    if self.MW.new_n <= 1: filters['last'] = True
                    else: filters['last_n'] = self.MW.new_n
                    self.final_status = _('News')
                elif qr == FX_PLACE_PREV_LAST or qr == 0:
                    filters['last'] = True
                    self.final_status = _('News')
                elif qr == FX_PLACE_LAST_HOUR: 
                    filters['last_hour'] = True
                    self.final_status = _('Last Hour')
                elif qr == FX_PLACE_TODAY: 
                    filters['today'] = True
                    self.final_status = _('Today')
                elif qr == FX_PLACE_LAST_WEEK: 
                    filters['last_week'] = True
                    self.final_status = _('Week')
                elif qr == FX_PLACE_LAST_MONTH: 
                    filters['last_month'] = True
                    self.final_status = _('Month')
                elif qr == FX_PLACE_LAST_QUARTER: 
                    filters['last_quarter'] = True
                    self.final_status = _('Quarter')
                elif qr == FX_PLACE_LAST_SIX_MONTHS: 
                    filters['last_six_months'] = True
                    self.final_status = _('Six Months')
                elif qr == FX_PLACE_LAST_YEAR: 
                    filters['last_year'] = True
                    self.final_status = _('Year')
                elif qr < 0:
                    filters['last_n'] = -qr
                    self.final_status = _('Prev. Updates')

                err = QP.recommend(filters, no_history=True)


        elif self.type == FX_TAB_SIMILAR and self.top_entry is not None:
            self.final_status = _('Similar to ...')            
            err = QP.similar(self.top_entry['id'], filters)

        elif self.type == FX_TAB_REL_TIME and self.top_entry is not None:
            self.final_status = _('Relevance in Time ...')            
            err = QP.relevance_in_time(self.top_entry['id'], filters)

        elif self.type == FX_TAB_CONTEXTS:
            self.final_status = f'{_("Contexts for ")}<b>{esc_mu(qr, ell=50)}</b>'
            err = QP.context(qr, filters)

        elif self.type == FX_TAB_TERM_NET:
            self.final_status = f'{_("Terms related to ")}<b>{esc_mu(qr, ell=50)}</b>'
            err = QP.term_net(qr, filters)

        elif self.type == FX_TAB_TRENDS:
            self.final_status = f'{_("Trends ")}<b>{esc_mu(qr, ell=50)}</b>'
            err = QP.trends(qr, filters)
        
        elif self.type == FX_TAB_TIME_SERIES:
            self.final_status = f'{_("Time Series for ")}<b>{esc_mu(qr, ell=50)}</b>'
            err = QP.time_series(qr, filters)


        elif self.type == FX_TAB_TREE:

            group = filters.get('group','category')

            if not empty: head_beg = f'<b>{esc_mu(qr, ell=50)}</b>'
            elif rank_scheme == FX_RANK_RECOM: head_beg = _('Recomm.')
            elif rank_scheme == FX_RANK_TREND: head_beg = _('Trending')
            elif rank_scheme == FX_RANK_DEBUBBLE: head_beg = _('Debubble')
            else: head_beg = _('Latest')

            if group == 'category': head_end = _('by Category')
            elif group == 'feed': head_end = _('by Channel')
            elif group == 'flag': head_end = _('by Flag')
            elif group == 'similar': head_end = _('by Simil.')
            elif group == 'monthly': head_end = _('by Month')
            elif group == 'daily': head_end = _('by Day')
            elif group == 'hourly': head_end = _('by Hour')

            self.final_status = f'{head_beg} {head_end}'

            if not empty:
                err = QP.query(qr, filters, allow_group=True)
            elif rank_scheme == FX_RANK_RECOM: err = QP.recommend(filters, allow_group=True)
            elif rank_scheme == FX_RANK_TREND: err = QP.trending('', filters, allow_group=True)
            elif rank_scheme == FX_RANK_DEBUBBLE:
                filters['rev'] = True
                err = QP.recommend(filters, allow_group=True)
            else:
                filters['sort'] = 'pubdate'
                err = QP.query('', filters, allow_group=True)



        elif self.type == FX_TAB_RULES:
            self.final_status = _('Rules')
            err = QP.list_rules()

        elif self.type == FX_TAB_LEARNED:
            self.final_status = _('Learned Keywords')
            err = QP.list_learned_terms()


        elif self.type == FX_TAB_FLAGS:
            self.final_status = _('Flags')
            err = QP.list_flags()


        elif self.type == FX_TAB_PLUGINS:
            self.final_status = _('Plugins')
            QP.results = self.MW.gui_plugins.copy()
            QP.result_no = len(QP.results)
            err = 0

        elif self.type == FX_TAB_CATALOG:
            self.final_status = _('Find Feeds...')
            err = QP.query(qr, filters, load_all=True)



        if err == 0: self.table.populate(QP)
        else: self.final_status = f"""<span foreground="red">{self.final_status}</span>"""

        if DB is not None: DB.close()
        fdx.bus_append((FX_ACTION_FINISHED_SEARCH, self.uid,))






    def query(self, phrase, filters):
        """ As above, threading"""
        if self.busy: return -1
        self.busy = True
        
        if self.type in (FX_TAB_TREE, FX_TAB_TRENDS): self.block_search(_("Generating summary...") )
        elif self.type in (FX_TAB_RULES, FX_TAB_FLAGS, FX_TAB_PLUGINS, FX_TAB_LEARNED,): self.block_search(_("Getting data...") )
        elif self.type == FX_TAB_CATALOG: self.block_search(_('Querying Feed Catalog...'))
        else: self.block_search(_("Searching...") )

        self.search_thread = threading.Thread(target=self.query_thr, args=(phrase, filters)   )
        self.search_thread.start()


    def on_query(self, *args):
        """ Wrapper for executing query from the tab """
        self.get_search_filters()
        if hasattr(self, 'query_entry'): self.query(self.query_entry.get_text(), self.search_filters)
        else: self.query('', self.search_filters)







    def on_filter_by_feed_thr(self, *args):
        """ Filter results by feed """
        ids = args[-1]
        self.table.filter_by_feed(ids)
        fdx.bus_append((FX_ACTION_FINISHED_FILTERING, self.uid,))



    def finish_filtering(self, **kargs):
        """ Finish filtering process """
        self.busy = False
        self.unblock_search()

        self.table.commit_filter_by_feed()
        
        self.spinner.hide()
        self.spinner.stop()
        self.header_icon.show()

        if self.type == FX_TAB_TREE:
            if self.search_filters.get('group',None) == 'similar': self.table.collapse_all()
            else: self.table.expand_all()
        
        if self.table.result_no2 != 0: len_str = f'{self.table.result_no} {_("of")} {self.table.result_no2}'
        else: len_str = f'{self.table.result_no}'
        self.header.set_markup( f'{self.final_status} ({len_str})' )
        
        if self.MW.curr_upper.uid == self.uid and self.table.feed_sums is not None: 
            self.MW.feed_tab.redecorate(self.table.curr_feed_filters, self.table.feed_sums)



    def on_filter_by_feed(self, *args):
        """ Wrapper for filtering by feed """
        if self.busy: return 0
        self.busy = True
        if self.table.result_no == 0: return 0
        self.block_search(_('Filtering...'))
        ids = args[-1]
        self.search_thread = threading.Thread(target=self.on_filter_by_feed_thr, args=(ids,))
        self.search_thread.start()




    def apply(self, action, item, **kargs):
        """ Updates local table from events from other widgets (e.g. delete, edit, new)"""
        if self.busy: return 0
        if action == FX_ACTION_EDIT and self.mutable: 
            self.table.replace(item['id'], item)
        elif action == FX_ACTION_ADD and self.mutable and self.prependable: 
            self.table.append(item)
        elif action == FX_ACTION_DELETE and self.mutable: 
            self.table.delete(item['id'], item.get('deleted'))

















        





class FeedexGUITable:
    """ Table display for entries tab """
    def __init__(self, parent, result, **kargs):

        self.parent = parent
        self.MW = self.parent.MW
        self.config = self.MW.config
        self.icons = self.MW.icons

        self.lock = threading.Lock()

        # Flags for different diplay types
        self.is_tree = kargs.get('tree', False)
        self.is_notes = kargs.get('notes', False)
        self.is_grid = kargs.get('grid', False)

        # Metadata from query processor interface
        self.result = result
        self.result.clear()
        self.results = [] # List of original results
        self.result_max = 0
        self.result_no = 0
        self.result_no2 = 0

        if kargs.get('table') is not None: self.result.table = kargs.get('table')

        self.result.TB = self # This is needed for some queries where aggregate data affects output (e.g. plots)

        # Store meta
        self.icon_col = None
        self.color_col = None
        self.weight_col = None

        # Init layout
        self.layout = self.MW.gui_cache['layouts'].get(self.result.table, FX_DEF_LAYOUTS[self.result.table])

        # Declare Gtk stores
        if self.is_tree:
            self.store = Gtk.TreeStore(*self.result.gui_types)
            self.tmp_store = None
        else: 
            self.store = Gtk.ListStore(*self.result.gui_types)
            self.tmp_store = None

        self.filtered_store = None

        # Currently active feed filters
        self.curr_feed_filters = None


        self.view = Gtk.TreeView(model=self.store)
        if self.is_tree: 
            self.view.set_enable_tree_lines(True)
            self.view.set_level_indentation(20)
        if self.is_notes or self.is_grid:
            self.view.set_grid_lines(True)

        # Generate columns
        if 'gui_toggle' in self.result.gui_fields:
            self.view.append_column( f_col('', 4, self.result.gindex('gui_toggle'), resizable=False, clickable=True, width=16, reorderable=False, connect=self._on_toggled) )
        if 'gui_icon' in self.result.gui_fields:
            self.view.append_column( f_col('', 3, self.result.gindex('gui_icon'), resizable=False, clickable=False, width=16, reorderable=False) )
        if 'gui_color' in self.result.gui_fields: self.color_col = self.result.gindex('gui_color')
        if 'gui_bold' in self.result.gui_fields: self.weight_col = self.result.gindex('gui_bold')


        # Try twice to build layout - second run is with default layout for this table type
        # If that fails - give up, the code is faulty 
        err = self._setup_layout()
        if err == -1: self._setup_layout()


        self.selection = self.view.get_selection()

        self.feed_sums = {}

        if self.result.search_col:
            self.view.set_enable_search(True)
            if self.is_tree: self.view.set_search_equal_func(quick_find_case_ins_tree, self.view, self.result.search_col) 
            else: self.view.set_search_equal_func(quick_find_case_ins, self.result.search_col)





    def _setup_layout(self, **kargs):
        """ Try and build column layout and catch value errors to try again """

        for c in self.layout:
            field = c[0]
            width = c[1]

            try:
                ix = self.result.gindex(field)
            except ValueError as e:
                self.MW.gui_cache['layouts'][self.result.table] = FX_DEF_LAYOUTS[self.result.table]
                self.layout = self.MW.gui_cache['layouts'][self.result.table]
                return -1

            if field in self.result.gui_fields: col_name = self.result.col_names[self.result.get_index(field)]
            else: col_name = field

            if field in self.result.gui_markup_fields: ctype = 1
            else: ctype = 0

            if field == 'entry' and self.is_notes:
                note = True
                yalign = 0
                col_name = _('Entry')
            else:
                note = False
                yalign = None

            if field == 'pubdate_short': sort_col = self.result.gindex('pubdate')
            else: sort_col = None

            self.view.append_column( f_col( col_name, ctype, ix, sort_col=sort_col, note=note, yalign=yalign, color_col=self.color_col, attr_col=self.weight_col, start_width=width, name=field) )


        return 0



    def gen_store_item(self, ix, **kargs):
        """ Returns a list for populating table store """       
        update_sums = kargs.get('update_sums',False)
        self.result.prep_gui_vals(ix, **kargs)
        
        if update_sums:
            self.feed_sums[self.result['feed_id']] = self.feed_sums.get(self.result['feed_id'],0) + 1
            parent_id = coalesce(self.result['parent_id'],0)
            if parent_id > 0 and parent_id != self.result['feed_id']: 
                self.feed_sums[self.result['parent_id']] = self.feed_sums.get(self.result['parent_id'],0) + 1

        return self.result.gtuplify()





    def populate(self, QR, **kargs):
        """ Wrapper for populating the store from a result list """
        to_temp = kargs.get('to_temp', True)
        commit = kargs.get('commit', False)

        self.results = QR.results
        self.result_max = QR.result_max
        self.result_no = QR.result_no
        self.result_no2 = QR.result_no2

        self.feed_sums = {}
        if isinstance(self.result, (ResultEntry, ResultContext,)): 
            update_sums = True
        else: update_sums = False

        if to_temp:
            if self.is_tree: self.tmp_store = Gtk.TreeStore(*self.result.gui_types)
            else: self.tmp_store = Gtk.ListStore(*self.result.gui_types)
        
        self.curr_node = None
        for ix, r in enumerate(self.results):
            self.result.populate(r)
            self.result.humanize()

            if self.is_tree:
                if self.result.get('is_node',0) == 1 or self.curr_node is None:
                    if to_temp: self.curr_node = self.tmp_store.append(None, self.gen_store_item(ix, update_sums=update_sums) )
                    else: self.curr_node = self.store.append(None, self.gen_store_item(ix, update_sums=update_sums) )
                else:
                    if to_temp: self.tmp_store.append(self.curr_node, self.gen_store_item(ix, update_sums=update_sums) )
                    else: self.store.append(self.curr_node, self.gen_store_item(ix, update_sums=update_sums) )

            else:
                if to_temp: self.tmp_store.append( self.gen_store_item(ix, update_sums=update_sums) )
                else: self.store.append( self.gen_store_item(ix, update_sums=update_sums) )

        if commit and to_temp: self.commit_populate()




    def commit_populate(self, **kargs):
        """ Swap store to tmp_store """
        self.lock.acquire()
        self.store = self.tmp_store
        #self.tmp_store.clear()
        self.view.set_model(self.store)
        self.curr_feed_filters = None
        self.lock.release()



    def append(self, item, **kargs):
        """ Wrapper for appending to store """
        top = kargs.get('top', True)
        fill = kargs.get('fill', True)
        tp = type(item)
        if tp in (list, tuple): self.result.populate(item)
        elif tp is dict: self.result.strict_merge(item)
        elif isinstance(item, SQLContainer): self.result.strict_merge(item.vals)
        else: return -1 

        self.result.humanize()
        if fill: self.result.fill()

        if type(self.results) is tuple: self.results = list(self.results)
        self.results.append(self.result.tuplify())
        ix = len(self.results) - 1

        if isinstance(self.result, (ResultEntry, ResultContext,)): new_col=True
        else: new_col=False

        self.lock.acquire()
        if not self.is_tree:
            if top: 
                if self.store is not None: self.store.prepend( self.gen_store_item(ix, new_col=new_col) )
                if self.filtered_store is not None: self.filtered_store.prepend( self.gen_store_item(ix, new_col=new_col) )
            else: 
                if self.store is not None: self.store.append( self.gen_store_item(ix, new_col=new_col) )
                if self.filtered_store is not None: self.filtered_store.append( self.gen_store_item(ix, new_col=new_col) )
        else:
            if top: 
                if self.store is not None: self.store.prepend(None, self.gen_store_item(ix, new_col=new_col))
                if self.filtered_store is not None: self.filtered_store.prepend(None, self.gen_store_item(ix, new_col=new_col))
            else: 
                if self.store is not None: self.store.append(None, self.gen_store_item(ix, new_col=new_col))
                if self.filtered_store is not None: self.filtered_store.append(None, self.gen_store_item(ix, new_col=new_col))

        self.lock.release()




    def _for_each_remove(self, model, path, iter, id):
        """ Check match for each item and do the removing """
        if model[iter][self.result.gindex('id')] == id:
            self.lock.acquire()
            model.remove(iter)
            self.lock.release()
            return True
        return False

    def remove(self, id, **kargs):
        """ Wrapper for removing item with a certain field value """
        if self.store is not None: self.store.foreach(self._for_each_remove, id)
        if self.filtered_store is not None: self.filtered_store.foreach(self._for_each_remove, id)


    def delete(self, id, lev, **kargs):
        """ Wrapper for nicely displaying deletion """
        if isinstance(self.result, (ResultEntry, ResultContext,)): 
            if lev == 2: self.replace(id, {'deleted':2}) 
            else: self.replace(id, {'deleted':1})      
        else: self.remove(id)



    def _for_each_replace(self, model, path, iter, id, changes):
        """ Check match for each result and then replace provided field with new value """
        if model[iter][self.result.gui_fields.index('id')] == id:
            
            ix = model[iter][self.result.gindex('gui_ix')]
            self.result.populate(self.results[ix])
            for k,v in changes.items(): self.result[k] = v
            self.result.humanize()
            self.result.fill()
            self.result.prep_gui_vals(ix)
            
            if type(self.results) is tuple: self.results = list(self.results)
            self.results[ix] = self.result.listify()

            edit_cols = []
            for i,f in enumerate(self.result.gui_fields):
                edit_cols.append(i)
                edit_cols.append(self.result.gget(f))
            self.lock.acquire()
            self.store.set(iter, *edit_cols)
            self.lock.release()

            if self.filtered_store is not None: 
                self.filtered_store.foreach(self._for_each_replace_basic, id)

            return True
        return False


    def _for_each_replace_basic(self, model, path, iter, id):
        """ This does the same as _for_each_replace but assumes the result is processed 
        and does not affect main results table. To be used for filterred stores """
        if model[iter][self.result.gui_fields.index('id')] == id:
            edit_cols = []
            for i,f in enumerate(self.result.gui_fields):
                edit_cols.append(i)
                edit_cols.append(self.result.gget(f))
            self.lock.acquire()
            self.filtered_store.set(iter, *edit_cols)
            self.lock.release()
            return True
        return False



    def replace(self, id, changes, **kargs):
        """ Wrapper for editting only one value in a result """
        if self.store is not None: self.store.foreach(self._for_each_replace, id, changes)



    def get_selection(self, *args, **kargs):
        """ Return selected row as Feedex Result object """
        model, treeiter = self.selection.get_selected()
        if treeiter is not None:
            ix = model[treeiter][self.result.gindex('gui_ix')]
            self.result.clear()
            self.result.populate(self.results[ix])


            # If result is a node, process it accordingly ...
            if isinstance(self.result, ResultEntry) and self.result.get('id') is None:
                
                if self.result.get('feed_id') not in (0,'', None):
                    item = ResultFeed()
                    feed = fdx.find_f_o_c(self.result.get('feed_id'), load=True)
                    if feed != -1:
                        item.populate(feed)
                        return item
                
                elif self.result.get('flag') not in (0,'', None):
                    item = ResultFlag()
                    flag = fdx.flags_cache.get(self.result.get('flag', -1))
                    if flag != -1:
                        flag = [self.result.get('flag')] + list(flag)
                        item.populate(flag)
                        return item

                elif self.result.get('pubdate_str') not in (0,'', None):
                    item = ResultTimeSeries()
                    item['time'] = self.result.get('title')
                    item['from'] = self.result.get('pubdate_str')
                    item['to'] = self.result.get('adddate_str')
                    item['freq'] = 0
                    return item

            else: return self.result








    def _for_each_filter_by_feed(self, model, path, iter, ids):
        """ Check match for each item and do the removing """
        if coalesce(model[iter][self.result.gindex('is_node')],0) == 1:
            if self.is_tree: self.curr_node = self.filtered_store.append(None, tuple(model[iter]))
            elif model[iter][self.result.gindex('feed_id')] in ids: self.filtered_store.append(tuple(model[iter]))
            return False
        elif model[iter][self.result.gindex('feed_id')] in ids:
            if self.is_tree: self.filtered_store.append(self.curr_node, tuple(model[iter]))
            else: self.filtered_store.append(tuple(model[iter]))
            return False

        return False


    def filter_by_feed(self, ids, **kargs):
        """ Apply filters """
        if not isinstance(self.result, (ResultEntry, ResultContext,)): return 0
        if type(ids) == int: ids = (ids,)

        commit = kargs.get('commit',False)

        if self.curr_feed_filters != ids:
            
            if self.is_tree: self.filtered_store = Gtk.TreeStore(*self.result.gui_types)
            else: self.filtered_store = Gtk.ListStore(*self.result.gui_types)

            if self.store is not None: self.store.foreach(self._for_each_filter_by_feed, ids)
            
            self.curr_feed_filters = ids
            if commit: self.commit_filter_by_feed()

        else:
            self.curr_feed_filters = None
            if commit: self.commit_filter_by_feed()


    def commit_filter_by_feed(self, **kargs):
        """ Commit filtering """
        self.lock.acquire()
        if self.curr_feed_filters is not None: self.view.set_model(self.filtered_store)
        else: self.view.set_model(self.store)
        self.lock.release()





    def expand_all(self, *args):
        if self.is_tree: self.view.expand_all()
    def collapse_all(self, *args):
        if self.is_tree: self.view.collapse_all()





    def _on_toggled_node(self, model, path, iter, parent_id, btog):
        if coalesce(model[iter][self.result.gindex('parent_id')],0) == parent_id:
            id = model[iter][self.result.gindex('id')]
            model[iter][self.result.gindex('gui_toggle')] = btog
            if btog:
                if id not in self.result.toggled_ids: self.result.toggled_ids.append(id)
            else:
                while id in self.result.toggled_ids: self.result.toggled_ids.remove(id)
        return False



    def _on_toggled(self, widget, path, *args):
        """ Handle toggled signal and pass results to nodes if needed """
        id = self.store[path][self.result.gindex('id')]
        btog = not self.store[path][self.result.gindex('gui_toggle')]
        self.store[path][self.result.gindex('gui_toggle')] = btog

        if btog:
            if id not in self.result.toggled_ids: self.result.toggled_ids.append(id)
        else: 
            while id in self.result.toggled_ids: self.result.toggled_ids.remove(id)
        
        if self.store[path][self.result.gindex('is_node')] == 1:
            self.store.foreach(self._on_toggled_node, id, btog)


    def _untoggle_all_foreach(self, model, path, iter):
        model[iter][self.result.gindex('gui_toggle')] = False 
        return False

    def untoggle_all(self, *args, **kargs):
        """ Untoggle all checkboxes """
        self.result.toggled_ids = []
        self.store.foreach(self._untoggle_all_foreach)





    def save_layout(self, *args, **kargs):
        """ Change QUI attributes to save in main class if something changes in here """
        layout = []
        for c in self.view.get_columns():
            name = c.get_name()
            if name is None: continue
            width = c.get_width()
            layout.append( (name, width) )
        
        self.MW.gui_cache['layouts'][self.result.table] = layout.copy()
        msg(_('Layout marked as default for this tab type') )
        debug(7, f'Layout saved: {self.MW.gui_cache}')











