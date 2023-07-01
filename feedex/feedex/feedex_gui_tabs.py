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
        
        # Tab label
        self.header_box = Gtk.HBox(homogeneous = False, spacing = 0)

        self.header = f_label('', markup=True, wrap=False)
        self.spinner = Gtk.Spinner()

        self.header_box.pack_start(self.spinner, False, True, 1)
        self.header_box.pack_start(self.header, False, False, 1)





        # Setup main result table
        if self.type == FX_TAB_SEARCH:
            self.table = FeedexGUITable(self, ResultGUIEntry(main_win=self.MW))
            self.table.view.set_tooltip_markup(_("""Double-click to open in browser. 
Right-click for more options
Hit <b>Ctrl-F</b> for interactive search by Title"""))                
            self.header.set_markup(_('Search') )



        elif self.type == FX_TAB_PLACES:
            self.table = FeedexGUITable(self, ResultGUIEntry(main_win=self.MW))
            self.table.view.set_tooltip_markup(_("""Double-click to open in browser. 
Right-click for more options
Hit <b>Ctrl-F</b> for interactive search by Title"""))
            self.header.set_markup(_('News') )



        elif self.type == FX_TAB_CONTEXTS:
            self.table = FeedexGUITable(self, ResultGUIContext(main_win=self.MW))
            self.table.view.set_tooltip_markup(_("""Search phrase in context is shown here.
Double-click to open the entry containing a context.
Right-click for more options
Hit <b>Ctrl-F</b> for interactive search by Title"""))
            self.header.set_markup(_('Search Contexts') )

        elif self.type == FX_TAB_SIMILAR:
            self.table = FeedexGUITable(self, ResultGUIEntry(main_win=self.MW))
            self.table.view.set_tooltip_markup(_("""Search items similar to top entry.
Double-click to open the entry.
Right-click for more options
Hit <b>Ctrl-F</b> for interactive search by Title"""))
            self.header.set_markup(_('Find Similar') )



        elif self.type == FX_TAB_TERM_NET:
            self.table = FeedexGUITable(self, ResultGUITerm(main_win=self.MW))
            self.table.view.set_tooltip_markup(_("""These are terms related to the one queried for. 
Right-click for more options            
Hit <b>Ctrl-F</b> for interactive search""") )
            self.header.set_markup(_('Term Net') )


        elif self.type == FX_TAB_TIME_SERIES:
            self.table = FeedexGUITable(self, ResultGUITimeSeries(main_win=self.MW))
            self.table.view.set_tooltip_markup(_("""Time series for term(s). Right-click for more options""") )
            self.header.set_markup(_('Time Series') )


        elif self.type == FX_TAB_RULES:
            self.table = FeedexGUITable(self, ResultGUIRule(main_win=self.MW))
            self.table.view.set_tooltip_markup(_("""These are manually added rules used for ranking and flagging. 
Double-click to edit. 
Right-click for more options
Hit <b>Ctrl-F</b> for interactive search"""))
            self.header.set_markup(_('Rules') )


        elif self.type == FX_TAB_FLAGS:
            self.table = FeedexGUITable(self, ResultGUIFlag(main_win=self.MW))
            self.table.view.set_tooltip_markup(_("""Flags used in rules and for manual marking of Entries
Right-click for more options"""))
            self.header.set_markup(_('Flags') )


        elif self.type == FX_TAB_REL_TIME:
            self.table = FeedexGUITable(self, ResultGUITimeSeries(main_win=self.MW))
            self.table.view.set_tooltip_markup(_("""Time distribution for similar documents. 
Right-click for more options            
Hit <b>Ctrl-F</b> for interactive search""") )
            self.header.set_markup(_('Entry Relevance in Time') )


        elif self.type == FX_TAB_TREE:
            self.table = FeedexGUITable(self, ResultGUITree(main_win=self.MW), tree=True)
            self.table.view.set_tooltip_markup(_("""Double-click to open in browser. 
Right-click for more options
Hit <b>Ctrl-F</b> for interactive search by Title"""))
            self.header.set_markup(_('Summary') )


        elif self.type == FX_TAB_NOTES:
            self.table = FeedexGUITable(self, ResultGUINote(main_win=self.MW), notes=True)
            self.table.view.set_tooltip_markup(_("""Double-click to edit. 
Right-click for more options
Hit <b>Ctrl-F</b> for interactive search by Title"""))
            self.header.set_markup(_('* Search'))


        elif self.type == FX_TAB_TRENDS:
            self.table = FeedexGUITable(self, ResultGUITerm(main_win=self.MW))
            self.table.view.set_tooltip_markup(_("""Strongest trending terms from filtered documents
Right-click for more options"""))
            self.header.set_markup(_('Trends'))


        elif self.type == FX_TAB_TRENDING:
            self.table = FeedexGUITable(self, ResultGUIEntry(main_win=self.MW))
            self.table.view.set_tooltip_markup(_("""Double-click to open in browser. 
Right-click for more options
Hit <b>Ctrl-F</b> for interactive search by Title"""))
            self.header.set_markup(_('Trending'))








        # Insert custom title
        if self.title not in (None,''):
            self.header.set_markup(self.title)


        # Close button
        if self.type != FX_TAB_PLACES:
            close_button = f_button(None,'window-close-symbolic', connect=self._on_close, size=Gtk.IconSize.MENU)
            close_button.set_relief(Gtk.ReliefStyle.NONE)
            self.header_box.pack_end(close_button, False, False, 1)


        # Search bar
        if self.type not in (FX_TAB_PLACES, FX_TAB_RULES, FX_TAB_FLAGS,):

            self.search_filters = {}
            
            self.search_entry_box = Gtk.HBox(homogeneous = False, spacing = 0)
            self.history = Gtk.ListStore(str)
            self.reload_history()

            if self.type not in (FX_TAB_REL_TIME, FX_TAB_SIMILAR,):
                (self.query_combo, self.query_entry) = f_combo_entry(self.history, connect=self.on_query, connect_button=self._clear_query_entry, tooltip_button=_('Clear search phrase'))
                self.query_entry.connect("populate-popup", self._on_query_entry_menu)

            self.search_button      = f_button(None,'edit-find-symbolic', connect=self.on_query)
            
            if self.type in (FX_TAB_SEARCH, FX_TAB_CONTEXTS, FX_TAB_SIMILAR, FX_TAB_TIME_SERIES, FX_TAB_REL_TIME, FX_TAB_TREE, FX_TAB_NOTES, FX_TAB_TRENDS, FX_TAB_TRENDING):

                self.search_filter_box = Gtk.HBox(homogeneous = False, spacing = 0)
                self.search_filter_box.connect('button-press-event', self._on_button_press_filters)

                self.restore_button     = f_button(None,'edit-redo-rtl-symbolic', connect=self.on_restore, tooltip=_("Restore filters to defaults")) 

                if self.type in (FX_TAB_TIME_SERIES, FX_TAB_REL_TIME):
                    self.time_series_combo = f_time_series_combo(ellipsize=False, tooltip=_('Select time series grouping') )
                
                elif self.type == FX_TAB_TREE:
                    self.group_combo = f_group_combo(ellipsize=False, with_times=True, tooltip=_('Select grouping field\n<b>Note that grouping by similarity will be very time consuming for large date ranges</b>') )
                    self.depth_combo = f_depth_combo(ellipsize=False, tooltip=_('Select how many top results to show for each grouping') )
                    self.sort_combo = f_sort_combo(ellipsize=False, tooltip=_('Default sorting field for empty queries\nUse <b>Debubble</b> to show news with the least importance for each grouping') )                    

                self.qtime_combo        = f_time_combo(connect=self.on_date_changed, ellipsize=False, tooltip=f"""{_('Filter by date')}\n<i>{_('Searching whole database can be time consuming for large datasets')}</i>""")
                self.cat_combo          = f_feed_combo(connect=self._on_filters_changed, ellipsize=False, with_feeds=True, tooltip="Choose Feed or Category to search")

                self.read_combo         = f_read_combo(connect=self._on_filters_changed, ellipsize=False, tooltip=_('Filter for Read/Unread news. Manually added entries are marked as read by default') )
                self.flag_combo         = f_flag_combo(connect=self._on_filters_changed, ellipsize=False, filters=True, tooltip=_('Filter by Flag or lack thereof') )

                self.notes_combo        = f_note_combo(search=True, ellipsize=False, tooltip=_("""Chose which item type to filter (Notes, News Items or both)"""))
                self.qhandler_combo     = f_handler_combo(connect=self._on_filters_changed, ellipsize=False, local=True, all=True, tooltip=_('Which handler protocols should be taken into account?') )

                if self.type != FX_TAB_REL_TIME:

                    self.qtype_combo        = f_query_type_combo(connect=self._on_filters_changed, ellipsize=False, rule=False)
                    self.qlogic_combo       = f_query_logic_combo(connect=self._on_filters_changed, ellipsize=False)
                    self.qlang_combo        = f_lang_combo(connect=self._on_filters_changed, ellipsize=False, with_all=True)
                    self.qfield_combo       = f_field_combo(connect=self._on_filters_changed, ellipsize=False, tooltip=_('Search in All or a specific field'), all_label=_('-- No Field --') )

                    self.case_combo         = f_dual_combo( (('___dummy',_("Detect case")),('case_sens', _("Case sensitive")),('case_ins',_("Case insensitive"))), ellipsize=False, tooltip=_('Set query case sensitivity'), connect=self._on_filters_changed)

                if self.type in (FX_TAB_SEARCH, FX_TAB_CONTEXTS, FX_TAB_NOTES):
                    self.page_len_combo     = f_page_len_combo(connect=self._on_filters_changed, ellipsize=False, tooltip=_("Choose page length for query"), default=self.config.get('page_length',3000))
                    self.page_no_label      = f_label('Page: <b>1</b>', markup=True, wrap=False, char_wrap=False)
                    self.page_prev_button   = f_button(None, 'previous', connect=self._on_page_prev)
                    self.page_next_button   = f_button(None, 'next', connect=self._on_page_next)

                self.on_restore()
                self._on_filters_changed()



            if hasattr(self, 'search_entry_box'):
                if hasattr(self, 'search_button'): self.search_entry_box.pack_start(self.search_button, False, False, 1)
                if hasattr(self, 'query_combo'): self.search_entry_box.pack_start(self.query_combo, False, False, 1)
                if hasattr(self, 'restore_button'): self.search_entry_box.pack_start(self.restore_button, False, False, 1)

            if hasattr(self, 'qtime_combo'): self.search_filter_box.pack_start(self.qtime_combo, False, False, 1)
            if hasattr(self, 'time_series_combo'): self.search_filter_box.pack_start(self.time_series_combo, False, False, 1)
            if hasattr(self, 'group_combo'): self.search_filter_box.pack_start(self.group_combo, False, False, 1)
            if hasattr(self, 'depth_combo'): self.search_filter_box.pack_start(self.depth_combo, False, False, 1)
            if hasattr(self, 'sort_combo'): self.search_filter_box.pack_start(self.sort_combo, False, False, 1)
            if hasattr(self, 'read_combo'): self.search_filter_box.pack_start(self.read_combo, False, False, 1)
            if hasattr(self, 'flag_combo'): self.search_filter_box.pack_start(self.flag_combo, False, False, 1)
            if hasattr(self, 'notes_combo'): self.search_filter_box.pack_start(self.notes_combo, False, False, 1)
            if hasattr(self, 'case_combo'): self.search_filter_box.pack_start(self.case_combo, False, False, 1)
            if hasattr(self, 'qfield_combo'): self.search_filter_box.pack_start(self.qfield_combo, False, False, 1)
            if hasattr(self, 'qlogic_combo'): self.search_filter_box.pack_start(self.qlogic_combo, False, False, 1)
            if hasattr(self, 'qtype_combo'): self.search_filter_box.pack_start(self.qtype_combo, False, False, 1)
            if hasattr(self, 'qlang_combo'): self.search_filter_box.pack_start(self.qlang_combo, False, False, 1)
            if hasattr(self, 'qhandler_combo'): self.search_filter_box.pack_start(self.qhandler_combo, False, False, 1)
            if hasattr(self, 'cat_combo'): self.search_filter_box.pack_start(self.cat_combo, False, False, 1)
            if hasattr(self, 'page_prev_button'): self.search_filter_box.pack_start(self.page_prev_button, False, False, 1)
            if hasattr(self, 'page_no_label'): self.search_filter_box.pack_start(self.page_no_label, False, False, 1)
            if hasattr(self, 'page_next_button'): self.search_filter_box.pack_start(self.page_next_button, False, False, 1)
            if hasattr(self, 'page_len_combo'): self.search_filter_box.pack_start(self.page_len_combo, False, False, 1)


            search_box = Gtk.HBox(homogeneous = False, spacing = 0)

            if hasattr(self, 'search_entry_box'):
                search_main_entry_box = Gtk.VBox(homogeneous = False, spacing = 0)
                search_padding_box2 = Gtk.HBox(homogeneous = False, spacing = 0) 
                search_main_entry_box.pack_start(self.search_entry_box, False, False, 0)
                search_main_entry_box.pack_start(search_padding_box2, False, False, 7)
                search_box.pack_start(search_main_entry_box, False, False, 0)

            if hasattr(self, 'search_filter_box'):
                search_filter_scrolled = Gtk.ScrolledWindow()
                search_filter_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)           

                # This is needed to prevent scrollbar from obscuring search bar for certain themes :(
                search_main_filter_box = Gtk.VBox(homogeneous = False, spacing = 0)
                search_padding_box1 = Gtk.HBox(homogeneous = False, spacing = 0) 

                search_main_filter_box.pack_start(self.search_filter_box, False, False, 0)
                search_main_filter_box.pack_start(search_padding_box1, False, False, 7)

                search_filter_scrolled.add(search_main_filter_box)

                search_box.pack_start(search_filter_scrolled, True, True, 0)

            self.pack_start(search_box, False, False, 0)

            
            


        table_box = Gtk.ScrolledWindow()
        table_box.add(self.table.view)
        self.pack_start(table_box, True, True, 1)

        self.table.view.connect("cursor-changed", self._on_changed_selection)
        self.table.view.connect("row-activated", self._on_activate)
        self.table.view.connect("button-press-event", self._on_button_press)
        
        debug(7, f'Tab created (id: {self.uid}, type:{self.type})')










    def _on_button_press(self, widget, event):
        """ Click signal handler """
        if event.button == 3:
            result = self.table.get_selection()
            self.MW.action_menu(result, self, event)

    def _on_button_press_filters(self, widget, event):
        if event.button == 3: self.MW.action_menu(None, self, event)
    

    def _on_changed_selection(self, *args, **kargs):
        """ Selection change handler"""
        if isinstance(self.table.result, (ResultEntry, ResultContext,)): 
            self.MW.load_preview(self.table.get_selection())

    def _on_activate(self, widget, event, *args, **kargs):
        """ Result activation handler """
        result = self.table.get_selection()
        if isinstance(result, (ResultEntry, ResultContext,)):
            if scast(result['link'],str,'').strip() != '': self.MW.on_open_entry(result) 
            else: self.MW.on_edit_entry(False, result)
        elif isinstance(result, ResultRule): self.MW.on_edit_rule(result)
        elif isinstance(result, ResultFlag): self.MW.on_edit_flag(result)



    def _clear_query_entry(self, *args, **kargs): self.query_entry.set_text('')
    def _on_close(self, *args, **kargs): self.MW.remove_tab(self.uid, self.type)

    def _on_query_entry_menu(self, widget, menu, *args, **kargs):
        """ Basically adds "Clear History" option to menu """
        menu.append( f_menu_item(0, 'SEPARATOR', None) ) 
        menu.append( f_menu_item(1, _('Clear Search History'), self.MW.on_clear_history, icon='edit-clear-symbolic'))
        menu.show_all()


    def save_filters(self, *args, **kargs):
        """ Save current search filters as default for the future """
        if self.type in (FX_TAB_SEARCH, FX_TAB_CONTEXTS, FX_TAB_TIME_SERIES, FX_TAB_REL_TIME, FX_TAB_TREE, FX_TAB_NOTES, FX_TAB_TRENDING, FX_TAB_TRENDS):
            self.get_search_filters()
            self.MW.default_search_filters = self.search_filters.copy()
            self.MW.gui_cache['default_search_filters'] = self.search_filters.copy()
            msg(_('Filters saved as defaults') )
            debug(7, f"Changed default filters: {self.MW.gui_cache['default_search_filters']}")



    def reload_history(self, *args, **kargs):
        """ Refresh search history from DB """
        self.history.clear()
        for h in fdx.search_history_cache: self.history.append((h[0],))



    def add_date_str_to_combo(self, date_string):
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
                self.add_date_str_to_combo(dialog.result["date_string"])
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
                dts = time.split(' --- ')
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
        if hasattr(self, 'sort_combo'): self.search_filters['fallback_sort'] = f_get_combo(self.sort_combo)

        if hasattr(self, 'page_len_combo'): 
            self.search_filters['page_len'] = f_get_combo(self.page_len_combo)
            self.search_filters['page'] = self.page_no
        else:
            self.search_filters['page_len'] = self.config.get('page_length',3000)
            self.search_filters['page'] = 1

        debug(7, f'Search filters updated: {self.search_filters}')
        return 0
        
 


    def on_restore(self, *args, **kargs):
        """ Restore default filters """
        default_search_filters = kargs.get('filters', self.MW.default_search_filters)

        if hasattr(self, 'time_series_combo'): f_set_combo(self.time_series_combo, default_search_filters.get('group'))
        if hasattr(self, 'qtime_combo'): f_set_combo_from_bools(self.qtime_combo, default_search_filters)
        if hasattr(self, 'cat_combo'): f_set_combo(self.cat_combo, default_search_filters.get('feed_or_cat'), null_val=-1)
        if hasattr(self, 'qtime_combo'): f_set_combo_from_bools(self.qtime_combo, default_search_filters)
        if hasattr(self, 'read_combo'): f_set_combo_from_bools(self.read_combo, default_search_filters)
        if hasattr(self, 'case_combo'): f_set_combo_from_bools(self.case_combo, default_search_filters)
        if hasattr(self, 'flag_combo'): f_set_combo(self.flag_combo, default_search_filters.get('flag'))
        if hasattr(self, 'qhandler_combo'): f_set_combo(self.qhandler_combo, default_search_filters.get('handler'))
        if hasattr(self, 'notes_combo'): f_set_combo(self.notes_combo, default_search_filters.get('note'), null_val=-1)
        if hasattr(self, 'qfield_combo'): f_set_combo(self.qfield_combo, default_search_filters.get('field'))
        if hasattr(self, 'qlang_combo'): f_set_combo(self.qlang_combo, default_search_filters.get('lang'))
        if hasattr(self, 'qtype_combo'): f_set_combo(self.qtype_combo, default_search_filters.get('qtype'))
        if hasattr(self, 'qlogic_combo'): f_set_combo(self.qlogic_combo, default_search_filters.get('logic'))
        if hasattr(self, 'time_series_combo'): f_set_combo(self.time_series_combo, default_search_filters.get('group'))
        if hasattr(self, 'group_combo'): f_set_combo(self.group_combo, default_search_filters.get('group'))
        if hasattr(self, 'depth_combo'): f_set_combo(self.depth_combo, default_search_filters.get('depth'))
        if hasattr(self, 'sort_combo'): f_set_combo(self.sort_combo, default_search_filters.get('fallback_sort'))
        if hasattr(self, 'page_len_combo'): f_set_combo(self.page_len_combo, default_search_filters.get('page_len'))

        self._on_filters_changed()











    def block_search(self, tab_text:str):
        """ Do some maintenance on starting a search """
        if hasattr(self, 'search_button'): self.search_button.set_sensitive(False)
        if hasattr(self, 'query_combo'): self.query_combo.set_sensitive(False)
        if hasattr(self, 'page_prev_button'): self.page_prev_button.set_sensitive(False) 
        if hasattr(self, 'page_next_button'): self.page_next_button.set_sensitive(False) 

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
        if self.top_entry is not None: self.table.append(self.top_entry)

        if self.type == FX_TAB_TREE:
            if self.search_filters.get('group',None) == 'similar': self.table.collapse_all()
            else: self.table.expand_all()

        self.spinner.hide()
        self.spinner.stop()
        
        if self.table.result_no2 != 0: len_str = f'{self.table.result_no} {_("of")} {self.table.result_no2}'
        else: len_str = f'{self.table.result_no}'
        self.header.set_markup( f'{self.final_status} ({len_str})' )

        if self.MW.curr_upper.uid == self.uid and self.table.feed_sums is not None: 
            self.MW.feed_tab.redecorate(self.table.curr_feed_filters, self.table.feed_sums)







    def query_thr(self, qr, filters, **kargs):
        """ Wrapper for sending queries """
        # DB interface for queries
        DB = FeedexDatabase(connect=True)
        DB.connect_QP()
        QP = DB.Q

        # Do query ...
        if self.type in (FX_TAB_SEARCH, FX_TAB_NOTES):

            feed_name = f_get_combo(self.cat_combo, name=True)

            filters['rev'] = False
            err = QP.query(qr, filters)

            if self.type == FX_TAB_NOTES: marker = '*'
            else: marker = ''

            if QP.phrase.get('empty',False):
                if feed_name is None: self.final_status = f"""{marker}{_('Results')}"""
                else: self.final_status = f'<b>{marker}{esc_mu(feed_name, ell=50)}</b>'
            else: 
                if feed_name is None: self.final_status = f'{marker}{_("Search for ")}<b>{esc_mu(qr, ell=50)}</b>'
                else: self.final_status = f'{marker}{_("Search for ")}<b>{esc_mu(qr, ell=50)}</b> {_("in")} <b><i>{esc_mu(feed_name, ell=50)}</i></b>'




        elif self.type == FX_TAB_PLACES:
 
            if qr == FX_PLACE_STARTUP:
                err = QP.query('', {'last':True, 'sort':'importance'})
                if err == 0 and QP.result_no <= 2:
                    err = QP.query('', {'last_hour':True, 'sort':'importance'})
                    if err == 0 and QP.result_no <= 2:
                        err = QP.query('', {'today':True, 'sort':'importance'})
                        if err == 0 and QP.result_no <= 2:
                            err = QP.query('', {'last_n':2, 'sort':'importance'})

                self.final_status = _('News')


            elif qr == FX_PLACE_TRASH_BIN:

                err = QP.query('', {'deleted':True, 'sort':'adddate'}, no_history=True)
                self.final_status = _('Trash bin')

            else:
                filters = {'sort':'importance'}
                if qr == FX_PLACE_LAST: 
                    filters['last'] = True
                    self.final_status = _('New Entries')
                elif qr == FX_PLACE_PREV_LAST: 
                    filters['last_n'] = 2
                    self.final_status = _('New Entries')
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

                err = QP.query('', filters, no_history=True)


        elif self.type == FX_TAB_SIMILAR and self.top_entry is not None:

            self.final_status = _('Similar to ...')            
            filters['rev'] = False
            err = QP.find_similar(self.top_entry['id'], **filters)

        elif self.type == FX_TAB_REL_TIME and self.top_entry is not None:
            filters['rev'] = False
            self.final_status = _('Relevance in Time ...')            
            err = QP.relevance_in_time(self.top_entry['id'], **filters)

        elif self.type == FX_TAB_CONTEXTS:
            filters['rev'] = False
            self.final_status = f'{_("Contexts for ")}<b>{esc_mu(qr, ell=50)}</b>'
            err = QP.term_context(qr, **filters)

        elif self.type == FX_TAB_TERM_NET:
            filters['rev'] = False
            self.final_status = f'{_("Terms related to ")}<b>{esc_mu(qr, ell=50)}</b>'
            err = QP.term_net(qr, print=False, lang=filters.get('lang'))

        elif self.type == FX_TAB_TRENDS:
            filters['rev'] = False
            self.final_status = f'{_("Trends ")}<b>{esc_mu(qr, ell=50)}</b>'
            err = QP.get_trends(qr, filters)
        
        elif self.type == FX_TAB_TRENDING:
            filters['rev'] = False
            self.final_status = f'{_("Trending ")}<b>{esc_mu(qr, ell=50)}</b>'
            err = QP.get_trending(qr, filters)


        elif self.type == FX_TAB_TIME_SERIES:
            filters['rev'] = False
            self.final_status = f'{_("Time Series for ")}<b>{esc_mu(qr, ell=50)}</b>'
            err = QP.term_in_time(qr, **filters)

        elif self.type == FX_TAB_TREE:

            group = filters.get('group','category')
            filters['rev'] = False


            if qr == FX_PLACE_STARTUP:
                
                filters['rev'] = False
                self.final_status = f'{_("Summary - latest")}'
                err = QP.query('', {'last':True, 'sort':'importance', 'group':group}, allow_group=True)
                if err == 0 and QP.result_no <= 5:
                    err = QP.query('', {'last_hour':True, 'sort':'importance', 'group':group}, allow_group=True)
                    if err == 0 and QP.result_no <= 5:
                        err = QP.query('', {'today':True, 'sort':'importance', 'group':group}, allow_group=True)
                        if err == 0 and QP.result_no <= 6:
                            err = QP.query('', {'last_n':2, 'sort':'importance', 'group':group}, allow_group=True)
            else:
                if group == 'category': self.final_status = f'{_("Summary by Category")} <b>{esc_mu(qr, ell=50)}</b>'
                elif group == 'feed': self.final_status = f'{_("Summary by Channel")} <b>{esc_mu(qr, ell=50)}</b>'
                elif group == 'flag': self.final_status = f'{_("Summary by Flag")} <b>{esc_mu(qr, ell=50)}</b>'
                elif group == 'similar': self.final_status = f'{_("Summary by Sim.")} <b>{esc_mu(qr, ell=50)}</b>'
                elif group == 'monthly': self.final_status = f'{_("Summary by Month")} <b>{esc_mu(qr, ell=50)}</b>'
                elif group == 'daily': self.final_status = f'{_("Summary by Day")} <b>{esc_mu(qr, ell=50)}</b>'
                elif group == 'hourly': self.final_status = f'{_("Summary by Hour")} <b>{esc_mu(qr, ell=50)}</b>'

                filters['rev'] = False
                err = QP.query(qr, filters, allow_group=True)
        


        elif self.type == FX_TAB_RULES:
            self.final_status = _('Rules')
            err = QP.list_rules()



        elif self.type == FX_TAB_FLAGS:
            self.final_status = _('Flags')
            err = QP.list_flags()


        if err == 0: self.table.populate(QP)
        
        DB.close()
        fdx.bus_append((FX_ACTION_FINISHED_SEARCH, self.uid,))





    def query(self, phrase, filters):
        """ As above, threading"""
        if self.busy: return -1
        self.busy = True
        
        if self.type in (FX_TAB_TREE, FX_TAB_TRENDS): self.block_search(_("Generating summary...") )
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
        self.block_search(_('Filtering...'))
        ids = args[-1]
        self.search_thread = threading.Thread(target=self.on_filter_by_feed_thr, args=(ids,))
        self.search_thread.start()




    def apply(self, action, item, **kargs):
        """ Updates local table from events from other widgets (e.g. delete, edit, new)"""
        if self.busy: return 0
        if action == FX_ACTION_EDIT: self.table.replace(item['id'], item)
        elif action == FX_ACTION_ADD and self.type not in (FX_TAB_SIMILAR, FX_TAB_TREE,): self.table.append(item)
        elif action == FX_ACTION_DELETE: self.table.delete(item['id'], item.get('deleted'))













class ResultGUI:
    """ Template for GUI result"""
    def __init__(self, **kargs) -> None:
        self.MW = kargs.get('main_win', None)
        self.config = kargs.get('config')
        if self.config is None:
            if self.MW is None: self.config = fdx.config
            else: self.config = self.MW.config
        self.gui_fields = ()
        self.gui_types = ()
        self.gui_vals = {}
        self.gui_markup_fields = ()
        self.search_col = None

    def gindex(self, field):
        """ Returns a GUI field index """
        return self.gui_fields.index(field)

    def gget(self, field, *args):
        """ Get GUI value """
        if len(args) > 1: default = args[0]
        else: default = None
        return self.gui_vals.get(field, default)

    def gadd(self, field, type):
        """ Add typed field to store template """
        self.gui_fields, self.gui_types = list(self.gui_fields), list(self.gui_types)
        self.gui_fields.append(field)
        self.gui_types.append(type)
        self.gui_fields, self.gui_types = tuple(self.gui_fields), tuple(self.gui_types)

    def gpopulate(self, ilist):
        for i,f in enumerate(self.gui_fields): self.gui_vals[f] = ilist[i]

    def gclear(self): self.gui_vals.clear()

    def glistify(self):
        """ Return GUI fields as ordered list"""
        out_list = []
        for f in self.gui_fields: out_list.append(self.gui_vals.get(f))
        return out_list

    def gtuplify(self): return tuple(self.glistify())






class ResultGUIEntry(ResultGUI, ResultEntry):
    """ GUI Result for generating and storing table items """
    def __init__(self, **kargs):
        ResultEntry.__init__(self, replace_nones=True, **kargs)
        ResultGUI.__init__(self, **kargs)
        self.gui_fields = ('gui_ix', 'gui_icon', 'id', 'pubdate_short', 'pubdate', 'title', 'feed_name', 'feed_id', 'desc', 'author', 'flag_name',
             'category', 'tags', 'read', 'importance', 'readability', 'weight', 'word_count', 'rank',
             'count', 'adddate_str', 'pubdate_str', 'publisher', 'link', 'is_node', 'gui_color', 'gui_bold')
        self.gui_types = (int, GdkPixbuf.Pixbuf, int,   str, int,   str, str, int, str, str, str, 
                          str, str, int, float, float, float, int, float, 
                          int, str, str, str, str, int,  str, int)
        self.search_col = self.gindex('title')


    def pre_prep_gui_vals(self, ix, **kargs):
        self.gui_vals.clear()
        self.gui_vals['gui_ix'] = ix
        self.gui_vals['gui_icon'] = self.MW.icons.get(self.vals["feed_id"], self.MW.icons['default'])
        self.gui_vals['id'] = self.vals['id']
        if self.vals['pubdate_short'] not in (None, ''):
            self.gui_vals['pubdate_short'] = humanize_date(self.vals['pubdate_short'], self.MW.today, self.MW.yesterday, self.MW.year)
        self.gui_vals['pubdate'] = self.vals['pubdate']
        self.gui_vals['title'] = self.vals['title']
        self.gui_vals['feed_name'] = self.vals['feed_name']
        self.gui_vals['feed_id'] = self.vals['feed_id']
        self.gui_vals['author'] = self.vals['author']
        self.gui_vals['flag_name'] = self.vals['flag_name']
        self.gui_vals['category'] = self.vals['category']
        self.gui_vals['tags'] = self.vals['tags']
        self.gui_vals['read'] = self.vals['read']
        self.gui_vals['importance'] = self.vals['importance']
        self.gui_vals['readability'] = self.vals['readability']
        self.gui_vals['weight'] = self.vals['weight']
        self.gui_vals['word_count'] = self.vals['word_count']
        self.gui_vals['rank'] = self.vals['rank']
        self.gui_vals['count'] = self.vals['count']
        self.gui_vals['adddate_str'] = self.vals['adddate_str']
        self.gui_vals['pubdate_str'] = self.vals['pubdate_str']
        self.gui_vals['publisher'] = self.vals['publisher']
        self.gui_vals['link'] = self.vals['link']
        self.gui_vals['is_node'] = self.vals['is_node']


    def prep_gui_vals(self, ix, **kargs):        
        """ Prepares values for display and generates icon and style fields """
        self.pre_prep_gui_vals(ix, **kargs)
        self.gui_vals['desc'] = ellipsize(scast(self.vals['desc'], str, ''), 150).replace('\n',' ').replace('\r',' ').replace('\t', ' ')

        if coalesce(self.vals['read'],0) > 0: self.gui_vals['gui_bold'] = 700
        else: self.gui_vals['gui_bold'] = 400

        if kargs.get('new_col',False): self.gui_vals['gui_color'] = self.config.get('gui_new_color','#0FDACA')
        elif coalesce(self.vals['deleted'],0) > 0 or coalesce(self.vals['is_deleted'],0) > 0: 
            self.gui_vals['gui_color'] = self.config.get('gui_deleted_color','grey')
        elif coalesce(self.vals['flag'],0) > 0: self.gui_vals['gui_color'] = fdx.get_flag_color(self.vals['flag'])




class ResultGUITree(ResultGUIEntry):
    """ GUI result for tree view """
    def __init__(self, **kargs):
        super().__init__(**kargs)
        self.table = 'tree'
        self.gui_markup_fields = ('title',)

    def prep_gui_vals(self, ix, **kargs):
        self.pre_prep_gui_vals(ix, **kargs)
        if self.vals['is_node'] == 1:
            self.gui_vals['gui_bold'] = 800
            self.gui_vals['title'] = f"""<b><u>{esc_mu(self.gui_vals['title'])} ({esc_mu(self.vals['children_no'])})</u></b>"""

        else:
            self.gui_vals['desc'] = ellipsize(scast(self.vals['desc'], str, ''), 150).replace('\n',' ').replace('\r',' ').replace('\t', ' ')
            self.gui_vals['title'] = esc_mu(self.gui_vals['title'])

            if coalesce(self.vals['read'],0) > 0: self.gui_vals['gui_bold'] = 700
            else: self.gui_vals['gui_bold'] = 400

            if kargs.get('new_col',False): self.gui_vals['gui_color'] = self.config.get('gui_new_color','#0FDACA')
            elif coalesce(self.vals['deleted'],0) > 0 or coalesce(self.vals['is_deleted'],0) > 0: 
                self.gui_vals['gui_color'] = self.config.get('gui_deleted_color','grey')
            elif coalesce(self.vals['flag'],0) > 0: self.gui_vals['gui_color'] = fdx.get_flag_color(self.vals['flag'])







class ResultGUINote(ResultGUIEntry):
    """ GUI result for note """
    def __init__(self, **kargs):
        ResultEntry.__init__(self, replace_nones=True, **kargs)
        ResultGUI.__init__(self, **kargs)
        self.table = 'notes'
        self.gui_fields = ('gui_ix', 'gui_icon', 'id', 'pubdate_short', 'pubdate', 'title', 'feed_name', 'feed_id', 'entry', 'author', 'flag_name',
             'category', 'tags', 'read', 'importance', 'readability', 'weight', 'word_count', 'rank',
             'count', 'adddate_str', 'pubdate_str', 'publisher', 'link', 'is_node', 'gui_color',)
        self.gui_types = (int, GdkPixbuf.Pixbuf, int,   str, int,   str, str, int, str, str, str, 
                          str, str, int, float, float, float, int, float, 
                          int, str, str, str, str, int,  str,)
        self.gui_markup_fields = ('entry',)
        self.search_col = self.gindex('entry')


    def prep_gui_vals(self, ix, **kargs):        
        """ Prepares values for display and generates icon and style fields """
        self.pre_prep_gui_vals(ix, **kargs)
        
        if self.vals.get('flag',0) > 0:
            color = fdx.get_flag_color(self.vals.get('flag',0)) 
            flag_str = f"""<b><span foreground="{color}">{esc_mu(self.vals.get("flag_name",''))}</span></b>: """
        else: flag_str = ''    
            
        desc = ellipsize(scast(self.vals['desc'], str, ''), 250).replace('\n',' ').replace('\r',' ').replace('\t', ' ')
        title = scast(self.vals['title'], str, '').replace('\n',' ').replace('\r',' ').replace('\t', ' ')

        self.gui_vals['entry'] = f"""---------------------------------------------------------------------------------
{flag_str}<b>{esc_mu(title)}</b>
{esc_mu(desc)}"""

        if coalesce(self.vals['deleted'],0) > 0 or coalesce(self.vals['is_deleted'],0) > 0: 
            self.gui_vals['gui_color'] = self.config.get('gui_deleted_color','grey')






class ResultGUIContext(ResultGUI, ResultContext):
    """ GUI result for context """
    def __init__(self, **kargs):
        ResultContext.__init__(self, replace_nones=True, **kargs)
        ResultGUI.__init__(self, **kargs)

        self.gui_fields = ('gui_ix', 'gui_icon', 'id', 'pubdate_short', 'pubdate', 'context', 'title', 'feed_name', 'feed_id', 'author', 'flag_name',
             'category', 'tags', 'read', 'importance', 'readability', 'weight', 'word_count', 'rank',
             'count', 'adddate_str', 'pubdate_str', 'publisher', 'link', 'gui_color',)
        self.gui_types = (int, GdkPixbuf.Pixbuf, int,   str, int,   str, str, str, int, str, str, 
                          str, str, int, float, float, float, int, float, 
                          int, str, str, str, str,  str,)
        self.gui_markup_fields = ('context','flag_name')
        self.search_col = self.gindex('title')



    def prep_gui_vals(self, ix, **kargs):
        self.gui_vals.clear()
        self.gui_vals['gui_ix'] = ix
        self.gui_vals['gui_icon'] = self.MW.icons.get(self.vals["feed_id"], self.MW.icons['default'])
        self.gui_vals['id'] = self.vals['id']
        if self.vals['pubdate_short'] not in (None, ''):
            self.gui_vals['pubdate_short'] = humanize_date(self.vals['pubdate_short'], self.MW.today, self.MW.yesterday, self.MW.year)
        self.gui_vals['pubdate'] = self.vals['pubdate']
        self.gui_vals['context'] = f"""{esc_mu(self.vals['context'][0][0])}<b>{esc_mu(self.vals['context'][0][1])}</b>{esc_mu(self.vals['context'][0][2])}"""
        self.gui_vals['title'] = self.vals['title']
        self.gui_vals['feed_name'] = self.vals['feed_name']
        self.gui_vals['feed_id'] = self.vals['feed_id']
        self.gui_vals['author'] = self.vals['author']
        self.gui_vals['flag_name'] = self.vals['flag_name']
        self.gui_vals['category'] = self.vals['category']
        self.gui_vals['tags'] = self.vals['tags']
        self.gui_vals['read'] = self.vals['read']
        self.gui_vals['importance'] = self.vals['importance']
        self.gui_vals['readability'] = self.vals['readability']
        self.gui_vals['weight'] = self.vals['weight']
        self.gui_vals['word_count'] = self.vals['word_count']
        self.gui_vals['rank'] = self.vals['rank']
        self.gui_vals['count'] = self.vals['count']
        self.gui_vals['adddate_str'] = self.vals['adddate_str']
        self.gui_vals['pubdate_str'] = self.vals['pubdate_str']
        self.gui_vals['publisher'] = self.vals['publisher']
        self.gui_vals['link'] = self.vals['link']

        if coalesce(self.vals['deleted'],0) > 0 or coalesce(self.vals['is_deleted'],0) > 0: 
            self.gui_vals['gui_color'] = self.config.get('gui_deleted_color','grey')
        elif coalesce(self.vals['flag'],0) > 0: 
            flag_col = fdx.get_flag_color(self.vals['flag'])
            self.gui_vals['flag_name'] = f"""<span foreground="{flag_col}">{esc_mu(self.gui_vals['flag_name'])}</span>"""






class ResultGUIRule(ResultGUI, ResultRule):
    """ GUI result for rule """
    def __init__(self, **kargs) -> None:
        ResultRule.__init__(self, replace_nones=True, **kargs)
        ResultGUI.__init__(self, **kargs)

        self.gui_fields = ('gui_ix', 'id', 'name', 'string', 'weight', 'scase_insensitive', 'query_type', 'flag_name', 'field_name', 'feed_name', 
                           'lang', 'matched', 'context_id', 'slearned', 'sadditive', 'flag', 'gui_color',)
        self.gui_types = (int, int, str, str, float, str, str, str, str, str, str, int, int,   str, str, int, str,)
        self.search_col = self.gindex('string')


    def prep_gui_vals(self, ix, **kargs):
        self.gui_vals.clear()
        self.gui_vals['gui_ix'] = ix
        self.gui_vals['id'] = self.vals['id']
        self.gui_vals['name'] = self.name()
        self.gui_vals['string'] = self.vals['string']
        self.gui_vals['weight'] = self.vals['weight']
        self.gui_vals['scase_insensitive'] = self.vals['scase_insensitive']
        self.gui_vals['query_type'] = self.vals['query_type']
        self.gui_vals['flag_name'] = self.vals['flag_name']
        self.gui_vals['field_name'] = self.vals['field_name']
        self.gui_vals['feed_name'] = self.vals['feed_name']
        self.gui_vals['lang'] = self.vals['lang']
        self.gui_vals['matched'] = self.vals['matched']
        self.gui_vals['context_id'] = self.vals['context_id']        
        self.gui_vals['slearned'] = self.vals['slearned']        
        self.gui_vals['sadditive'] = self.vals['sadditive']        
        self.gui_vals['flag'] = self.vals['flag']        
        if coalesce(self.vals['flag'],0) > 0: self.gui_vals['gui_color'] = fdx.get_flag_color(self.vals['flag'])




class ResultGUIFlag(ResultGUI, ResultFlag):
    """ GUI result for flag """
    def __init__(self, **kargs):
        ResultFlag.__init__(self, replace_nones=True, **kargs)
        ResultGUI.__init__(self, **kargs)
        self.gui_fields = ('gui_ix', 'id', 'name', 'desc', 'color', 'color_cli', 'gui_color',)
        self.gui_types = (int, int,  str, str, str, str, str,)
        self.search_col = self.gindex('name')

    def prep_gui_vals(self, ix, **kargs):
        self.gui_vals.clear()
        self.gui_vals['gui_ix'] = ix
        self.gui_vals['id'] = self.vals['id']
        self.gui_vals['name'] = self.vals['name']
        self.gui_vals['desc'] = self.vals['desc']
        self.gui_vals['color'] = self.vals['color']
        self.gui_vals['gui_color'] = self.vals['color']



class ResultGUITerm(ResultGUI, ResultTerm):
    """ GUI result for term list """
    def __init__(self, **kargs):
        ResultTerm.__init__(self, replace_nones=True, **kargs)
        ResultGUI.__init__(self, **kargs)
        self.gui_fields = ('gui_ix', 'term', 'weight', 'search_form',)
        self.gui_types = (int, str, float, str,)
        self.search_col = self.gindex('term')


    def prep_gui_vals(self, ix, **kargs):
        self.gui_vals.clear()
        self.gui_vals['gui_ix'] = ix
        self.gui_vals['term'] = self.vals['term']
        self.gui_vals['weight'] = self.vals['weight']
        self.gui_vals['search_form'] = self.vals['search_form']




class ResultGUITimeSeries(ResultGUI, ResultTimeSeries):
    """ GUI result for time series """
    def __init__(self, **kargs):
        ResultTimeSeries.__init__(self, replace_nones=True, **kargs)
        ResultGUI.__init__(self, **kargs)
        self.gui_fields = ('gui_ix', 'time', 'from', 'to', 'freq', 'gui_plot',)
        self.gui_types = (int, str, str, str, float, str,)
        self.gui_markup_fields = ('gui_plot',)
        self.search_col = self.gindex('time')


    def prep_gui_vals(self, ix, **kargs):
        self.gui_vals.clear()
        self.gui_vals['gui_ix'] = ix
        self.gui_vals['time'] = self.vals['time']
        self.gui_vals['from'] = self.vals['from']
        self.gui_vals['to'] = self.vals['to']
        self.gui_vals['freq'] = self.vals['freq']
        
        color = self.config.get('gui_hilight_color','blue')
        unit = dezeroe(self.TB.result_max,1)/200
        length = int(self.vals.get('freq',0)/unit)
        magn = ""
        for l in range(length): magn = f'{magn} ' 
        magn = f'<span background="{color}">{magn}</span>'
        self.gui_vals['gui_plot'] = magn










class FeedexGUITable:
    """ Table display for entries tab """
    def __init__(self, parent, result, **kargs):

        self.MW = parent.MW
        self.config = self.MW.config
        self.icons = self.MW.icons

        self.lock = threading.Lock()

        # Flags for different diplay types
        self.is_tree = kargs.get('tree', False)
        self.is_notes = kargs.get('notes', False)

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
        if self.is_notes:
            self.view.set_grid_lines(True)

        # Generate columns
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
            if self.is_tree: self.view.set_search_equal_func(self.MW.quick_find_case_ins_tree, self.view, self.result.search_col) 
            else: self.view.set_search_equal_func(self.MW.quick_find_case_ins, self.result.search_col)





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

            self.view.append_column( f_col( col_name, ctype, ix , sort_col=sort_col, note=note, yalign=yalign, color_col=self.color_col, attr_col=self.weight_col, start_width=width, name=field) )

        return 0



    def gen_store_item(self, ix, **kargs):
        """ Returns a list for populating table store """       
        update_sums = kargs.get('update_sums',False)
        self.result.prep_gui_vals(ix, **kargs)
        
        if update_sums:
            self.feed_sums[self.result['feed_id']] = self.feed_sums.get(self.result['feed_id'],0) + 1
            if coalesce(self.result['parent_id'],0) > 0: 
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
            return self.result






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








class CalendarDialog(Gtk.Dialog):
    """ Date chooser for queries """
    def __init__(self, parent, **kargs):

        self.response = 0
        self.result = {'from_date':None,'to_date':None, 'date_string':None}

        Gtk.Dialog.__init__(self, title=_("Choose date range"), transient_for=parent, flags=0)
        self.set_default_size(kargs.get('width',400), kargs.get('height',200))
        box = self.get_content_area()

        from_label = f_label(_('  From:'), justify=FX_ATTR_JUS_LEFT, selectable=False, wrap=False)
        to_label = f_label(_('    To:'), justify=FX_ATTR_JUS_LEFT, selectable=False, wrap=False)

        self.from_clear_button = Gtk.CheckButton.new_with_label(_('Empty'))
        self.from_clear_button.connect('toggled', self.clear_from)
        self.to_clear_button = Gtk.CheckButton.new_with_label(_('Empty'))
        self.to_clear_button.connect('toggled', self.clear_to)

        accept_button = f_button(_('Accept'),'object-select-symbolic', connect=self.on_accept)
        cancel_button = f_button(_('Cancel'),'window-close-symbolic', connect=self.on_cancel)

        self.cal_from = Gtk.Calendar()
        self.cal_to = Gtk.Calendar()
        self.cal_from.connect('day-selected', self.on_from_selected)
        self.cal_to.connect('day-selected', self.on_to_selected)



        top_box = Gtk.HBox(homogeneous = False, spacing = 0)
        bottom_box = Gtk.HBox(homogeneous = False, spacing = 0)

        left_box = Gtk.VBox(homogeneous = False, spacing = 0)
        right_box = Gtk.VBox(homogeneous = False, spacing = 0)

        box.pack_start(top_box, False, False, 1)
        box.pack_start(bottom_box, False, False, 1)

        bottom_box.pack_start(cancel_button, False, False, 1)
        bottom_box.pack_end(accept_button, False, False, 1)

        top_box.pack_start(left_box, False, False, 1)
        top_box.pack_start(right_box, False, False, 1)

        left_box.pack_start(from_label, False, False, 1)
        left_box.pack_start(self.cal_from, False, False, 1)
        left_box.pack_start(self.from_clear_button, False, False, 1)

        right_box.pack_start(to_label, False, False, 1)
        right_box.pack_start(self.cal_to, False, False, 1)
        right_box.pack_start(self.to_clear_button, False, False, 1)

        self.show_all()
        self.on_to_selected()
        self.on_from_selected()

    def on_accept(self, *args):
        self.response = 1
        if not self.from_clear_button.get_active():
            (year, month, day) = self.cal_from.get_date()
            self.result['from_date'] = f'{scast(year,str,"")}/{scast(month+1,str,"")}/{scast(day,str,"")}'
        else: self.result['from_date'] = None

        if not self.to_clear_button.get_active():
            (year, month, day) = self.cal_to.get_date()
            self.result['to_date'] = f'{scast(year,str,"")}/{scast(month+1,str,"")}/{scast(day,str,"")}'
        else: self.result['to_date'] = None

        self.result['date_string'] = f"""{coalesce(self.result['from_date'], '...')} --- {coalesce(self.result['to_date'], '...')}"""
        self.close()

    def on_cancel(self, *args):
        self.response = 0
        self.result = {'from_date':None,'to_date':None, 'date_string':None}
        self.close()
        
    def clear_from(self, *args):

        if self.cal_from.get_sensitive():
            self.cal_from.set_sensitive(False)
        else:
            self.cal_from.set_sensitive(True)

    def clear_to(self, *args):
        if self.cal_to.get_sensitive():
            self.cal_to.set_sensitive(False)
        else:
            self.cal_to.set_sensitive(True)

    def on_from_selected(self, *args):
        (year, month, day) = self.cal_from.get_date()
        self.result['from_date'] = f'{scast(year,str,"")}/{scast(month+1,str,"")}/{scast(day,str,"")}'

    def on_to_selected(self, *args):
        (year, month, day) = self.cal_to.get_date()
        self.result['to_date'] = f'{scast(year,str,"")}/{scast(month+1,str,"")}/{scast(day,str,"")}'

