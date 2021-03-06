# -*- coding: utf-8 -*-
""" GUI classes for FEEDEX """


from feedex_gui_utils import *








class FeedexTab(Gtk.ScrolledWindow):
    """ Tabs for searches and views """

    def __init__(self, parent, **kargs):

        # Maint. stuff
        self.parent = parent
        self.config = parent.config
        self.debug = parent.debug

        self.type = kargs.get('type', FX_TAB_SEARCH)
        self.tab_id = kargs.get('tab_id',0)
        
        # Set up an unique id to match finished searches
        uniq = False
        while not uniq:
            self.uid = randint(1,1000)
            uniq = True
            for up in self.parent.upper_pages:
                if up.uid == self.uid: uniq = False



        # Containers for selected/processed items
        self.result = SQLContainer('entries', RESULTS_SQL_TABLE, replace_nones=True)
        self.tree_result = SQLContainer('entries', RESULTS_SQL_TABLE + ('is_node',), replace_nones=True)
        self.context = SQLContainer('entries', RESULTS_SQL_TABLE + ('context',), replace_nones=True)
        self.rule = SQLContainer('rules', RULES_SQL_TABLE_RES, replace_nones=True)
        self.feed = SQLContainer('feeds', FEEDS_SQL_TABLE, replace_nones=True)
        self.flag = SQLContainer('flags', FLAGS_SQL_TABLE, replace_nones=True)

        # Needed to selected entry to the top of the list
        self.top_entry = SQLContainer('entries', RESULTS_SQL_TABLE, replace_nones=True)


        # Changeable parameters/flags
        self.processing_flag = False
        self.feed_aggr = {}
        self.final_status = ''
        self.refresh_feeds = True
        self.feed_filter_id = 0

        # Local search thread
        self.search_thread = None

        # Results storage
        self.results = kargs.get('results',[]).copy()



        # GUI init stuff
        # Tab 
        self.main_box = Gtk.VBox(homogeneous = False, spacing = 0)

        # Tab label
        self.header_box = Gtk.HBox(homogeneous = False, spacing = 0)

        self.header = f_label('', markup=True, wrap=False)
        self.spinner = Gtk.Spinner()

        self.header_box.pack_start(self.spinner, True, True, 1)
        self.header_box.pack_start(self.header, True, True, 1)

        if self.type == FX_TAB_SEARCH:
            self.header.set_markup(_('Search') )
        elif self.type == FX_TAB_PLACES:
            self.header.set_markup(_('News') )
        elif self.type == FX_TAB_CONTEXTS:
            self.header.set_markup(_('Search Contexts') )
        elif self.type == FX_TAB_TERM_NET:
            self.header.set_markup(_('Search Terms') )
        elif self.type == FX_TAB_TIME_SERIES:
            self.header.set_markup(_('Time Series') )
        elif self.type == FX_TAB_RULES:
            self.header.set_markup(_('Rules') )
        elif self.type == FX_TAB_FLAGS:
            self.header.set_markup(_('Flags') )
        elif self.type == FX_TAB_REL_TIME:
            self.header.set_markup(_('Entry Relevance in Time') )
        elif self.type == FX_TAB_TREE:
            self.header.set_markup(_('Summary') )
        elif self.type == FX_TAB_NOTES:
            self.header.set_markup(_('* Search'))


        # Close button
        if self.type != FX_TAB_PLACES:
            close_button = f_button(None,'window-close-symbolic', connect=self.on_close, size=Gtk.IconSize.MENU)
            close_button.set_relief(Gtk.ReliefStyle.NONE)
            self.header_box.pack_end(close_button, False, False, 1)


        # Search bar
        if self.type in (FX_TAB_SEARCH, FX_TAB_CONTEXTS, FX_TAB_TERM_NET, FX_TAB_TIME_SERIES, FX_TAB_REL_TIME, FX_TAB_TREE, FX_TAB_NOTES):

            self.search_filters = {}

            search_box = Gtk.HBox(homogeneous = False, spacing = 0)
 
            search_filter_scrolled = Gtk.ScrolledWindow()
            search_filter_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)           
            search_entry_box = Gtk.HBox(homogeneous = False, spacing = 0)

            self.history = Gtk.ListStore(str)
            self.reload_history()

            search_main_entry_box = Gtk.VBox(homogeneous = False, spacing = 0)
            search_padding_box2 = Gtk.HBox(homogeneous = False, spacing = 0) 
            search_main_entry_box.pack_start(search_entry_box, False, False, 0)
            search_main_entry_box.pack_start(search_padding_box2, False, False, 7)

            search_box.pack_start(search_main_entry_box, False, False, 0)


            if self.type != FX_TAB_REL_TIME:
                (self.query_combo, self.query_entry) = f_combo_entry(self.history, connect=self.on_query, connect_button=self._clear_query_entry, tooltip_button=_('Clear search phrase'))
            
            self.search_button      = f_button(None,'edit-find-symbolic', connect=self.on_query)
            search_entry_box.pack_start(self.search_button, False, False, 1)
            
            if self.type != FX_TAB_REL_TIME:
                search_entry_box.pack_start(self.query_combo, False, False, 1)



            if self.type in (FX_TAB_SEARCH, FX_TAB_CONTEXTS, FX_TAB_TIME_SERIES, FX_TAB_REL_TIME, FX_TAB_TREE, FX_TAB_NOTES):

                self.restore_button     = f_button(None,'edit-redo-rtl-symbolic', connect=self.on_restore, tooltip=_("Restore filters to defaults")) 
                search_entry_box.pack_start(self.restore_button, False, False, 1)
                search_filter_box = Gtk.HBox(homogeneous = False, spacing = 0)

                if self.type in (FX_TAB_TIME_SERIES, FX_TAB_REL_TIME):
                    self.time_series_combo = f_time_series_combo(ellipsize=False, tooltip=_('Select time series grouping') )
                    search_filter_box.pack_start(self.time_series_combo, False, False, 1)
                
                elif self.type == FX_TAB_TREE:
                    self.group_combo = f_group_combo(ellipsize=False, with_times=True, tooltip=_('Select grouping field') )
                    self.depth_combo = f_depth_combo(ellipsize=False, tooltip=_('Select how many top results to show for each grouping') )
                    self.sort_combo = f_sort_combo(ellipsize=False, tooltip=_('Default sorting field for empty queries\nUse <b>Debubble</b> to show news with the least importance for each grouping') )
                    search_filter_box.pack_start(self.group_combo, False, False, 1)
                    search_filter_box.pack_start(self.depth_combo, False, False, 1)
                    search_filter_box.pack_start(self.sort_combo, False, False, 1)
                    

                self.qtime_combo        = f_time_combo(add=self.parent.date_store_added, connect=self.on_date_changed, ellipsize=False, tooltip=f"""{_('Filter by date')}\n<i>{_('Searching whole database can be time consuming for large datasets')}</i>""")
                self.cat_combo          = f_feed_combo(parent.FX, connect=self.on_filters_changed, ellipsize=False, with_feeds=True, tooltip="Choose Feed or Category to search")

                if self.type != FX_TAB_REL_TIME:
                    self.read_combo         = f_read_combo(connect=self.on_filters_changed, ellipsize=False, tooltip=_('Filter for Read/Unread news. Manually added entries are marked as read by default') )
                    self.flag_combo         = f_flag_combo(self.parent.FX, connect=self.on_filters_changed, ellipsize=False, filters=True, tooltip=_('Filter by Flag or lack thereof') )

                    self.notes_combo        = f_note_combo(search=True, ellipsize=False, tooltip=_("""Chose which item type to filter (Notes, News Items or both)"""))
                    self.qhandler_combo     = f_handler_combo(connect=self.on_filters_changed, ellipsize=False, local=True, all=True, tooltip=_('Which handler protocols should be taken into account?') )


                    self.qtype_combo        = f_query_type_combo(connect=self.on_filters_changed, ellipsize=False, rule=False)
                    self.qlang_combo        = f_lang_combo(parent.FX, connect=self.on_filters_changed, ellipsize=False, with_all=True)
                    self.qfield_combo       = f_field_combo(connect=self.on_filters_changed, ellipsize=False, tooltip=_('Search in All or a specific field'), all_label=_('-- No Field --') )

                    self.case_combo         = f_dual_combo( (('___dummy',_("Detect case")),('case_sens', _("Case sensitive")),('case_ins',_("Case insensitive"))), ellipsize=False, tooltip=_('Set query case sensitivity'), connect=self.on_filters_changed)

                self.on_restore()
                self.on_filters_changed()



                search_filter_box.pack_start(self.qtime_combo, False, False, 1)

                if self.type != FX_TAB_REL_TIME:
                    search_filter_box.pack_start(self.read_combo, False, False, 1)
                    search_filter_box.pack_start(self.flag_combo, False, False, 1)
                    search_filter_box.pack_start(self.notes_combo, False, False, 1)
                    search_filter_box.pack_start(self.case_combo, False, False, 1)
                    search_filter_box.pack_start(self.qfield_combo, False, False, 1)
 
                    search_filter_box.pack_start(self.qtype_combo, False, False, 1)

                    search_filter_box.pack_start(self.qlang_combo, False, False, 1)
                    search_filter_box.pack_start(self.qhandler_combo, False, False, 1)

                search_filter_box.pack_start(self.cat_combo, False, False, 1)


                # This is needed to prevent scrollbar from obscuring search bar for certain themes :(
                search_main_filter_box = Gtk.VBox(homogeneous = False, spacing = 0)
                search_padding_box1 = Gtk.HBox(homogeneous = False, spacing = 0) 

                search_main_filter_box.pack_start(search_filter_box, False, False, 0)
                search_main_filter_box.pack_start(search_padding_box1, False, False, 7)

                search_filter_scrolled.add(search_main_filter_box)

                search_box.pack_start(search_filter_scrolled, True, True, 0)


            self.main_box.pack_start(search_box, False, False, 0)

            
            





        # Result trees

        if self.type in (FX_TAB_PLACES, FX_TAB_SEARCH, FX_TAB_SIMILAR, FX_TAB_TREE):
            self.column_types   = (GdkPixbuf.Pixbuf, int,int, str,str,str,str,str,str,str,str,int,str,int, int,int, float,float,float, int,float,int,float, int,str, str, str,  int)
        elif self.type == FX_TAB_NOTES:
            self.column_types   = (GdkPixbuf.Pixbuf, int, str, str, str, str, int,  float, float, int, float, int,   int)
        elif self.type == FX_TAB_CONTEXTS:
            self.column_types   = (GdkPixbuf.Pixbuf, int,int, str,str,str,str,str, int,int,int, float,float,float,int, int,float, str, str, str,  int)
        elif self.type == FX_TAB_TERM_NET:
            self.column_types   = (str, float, int,   int)
        elif self.type in (FX_TAB_TIME_SERIES, FX_TAB_REL_TIME):
            self.column_types   = (str, str, int,   int)
        elif self.type == FX_TAB_RULES:
            self.column_types   = (int, str, str, float, str, str, str, str, str, str, str,    int)
        elif self.type == FX_TAB_FLAGS:
            self.column_types   = (int, str, str, str, str,    int)

        if self.type == FX_TAB_TREE:
            self.result_store = Gtk.TreeStore(*self.column_types)
            self.tmp_store = Gtk.TreeStore(*self.column_types)
        else:            
            self.result_store = Gtk.ListStore(*self.column_types)
            self.tmp_store = Gtk.ListStore(*self.column_types)

        self.result_list = Gtk.TreeView(model=self.result_store)


        if self.type in (FX_TAB_PLACES, FX_TAB_SEARCH, FX_TAB_SIMILAR, FX_TAB_TREE):

            self.result_list.append_column( f_col('', 3, 0, resizable=False, clickable=False, width=16, reorderable=False) )
            columns = {}
            columns[25] = f_col(_('Date'), 0, 25, color_col=24, attr_col=23, sort_col=11, start_width=self.parent.gui_attrs.get('results',{}).get('25',100), name='25') 
            
            if self.type == FX_TAB_TREE: columns[4] = f_col(_('Title'), 1, 4, color_col=24, attr_col=23, start_width=self.parent.gui_attrs.get('results',{}).get('4',650), name='4')
            else: columns[4] = f_col(_('Title'), 0, 4, color_col=24, attr_col=23, start_width=self.parent.gui_attrs.get('results',{}).get('4',650), name='4') 
            
            columns[3] = f_col(_('Source'), 0, 3, color_col=24, attr_col=23, start_width=self.parent.gui_attrs.get('results',{}).get('3',200), name='3')
            columns[5] = f_col(_('Description'), 0, 5, color_col=24, attr_col=23, start_width=self.parent.gui_attrs.get('results',{}).get('5',650), name='5')
            columns[7] = f_col(_('Author'), 0, 7, color_col=24, attr_col=23, start_width=self.parent.gui_attrs.get('results',{}).get('7',200), name='7')
            columns[8] = f_col(_('Publisher'), 0, 8, color_col=24, attr_col=23, start_width=self.parent.gui_attrs.get('results',{}).get('8',200), name='8')
            columns[9] = f_col(_('Category'), 0, 9, color_col=24, attr_col=23, start_width=self.parent.gui_attrs.get('results',{}).get('9',200), name='9')
            columns[26] = f_col(_('Flag'), 0, 26, color_col=24, attr_col=23, start_width=self.parent.gui_attrs.get('results',{}).get('26',100), name='26') 
            columns[10] = f_col(_('Publ. Timestamp'), 0, 10, color_col=24, attr_col=23, start_width=self.parent.gui_attrs.get('results',{}).get('10',200), name='10')
            columns[12] = f_col(_('Added'), 0, 12, color_col=24, attr_col=23, start_width=self.parent.gui_attrs.get('results',{}).get('12',200), name='12')
            columns[14] = f_col(_('Read?'), 0, 14, color_col=24, attr_col=23, start_width=self.parent.gui_attrs.get('results',{}).get('14',200), name='14')
            columns[15] = f_col(_('Flag ID'), 0, 15, color_col=24, attr_col=23, start_width=self.parent.gui_attrs.get('results',{}).get('15',200), name='15')
            columns[16] = f_col(_('Importance'), 0, 16, color_col=24, attr_col=23, start_width=self.parent.gui_attrs.get('results',{}).get('16',200), name='16')
            columns[17] = f_col(_('Weight'), 0, 17, color_col=24, attr_col=23, start_width=self.parent.gui_attrs.get('results',{}).get('17',200), name='17')
            columns[18] = f_col(_('Readability'), 0, 18, color_col=24, attr_col=23, start_width=self.parent.gui_attrs.get('results',{}).get('18',200), name='18')
            columns[19] = f_col(_('Word Count'), 0, 19, color_col=24, attr_col=23, start_width=self.parent.gui_attrs.get('results',{}).get('19',200), name='19')
            columns[6] = f_col(_('Link'), 0, 6, color_col=24, attr_col=23, start_width=self.parent.gui_attrs.get('results',{}).get('6',400), name='6')
            columns[21] = f_col(_('Term Count'), 0, 21, color_col=24, attr_col=23, start_width=self.parent.gui_attrs.get('results',{}).get('21',150), name='21')
            columns[20] = f_col(_('Search Rank'), 0, 20, color_col=24, attr_col=23, start_width=self.parent.gui_attrs.get('results',{}).get('20',150), name='20')
            
            for c in self.parent.gui_attrs.get('results_order', FX_DEF_COLS_RESULTS): self.result_list.append_column(columns[c])

            self.result_list.set_tooltip_markup(_("""Double-click to open in browser. 
Right-click for more options
Hit <b>Ctrl-F</b> for interactive search by Title"""))

            self.result_list.connect("row-activated", self.parent.on_activate_result)

            if self.type == FX_TAB_TREE: self.result_list.connect("button-press-event", self._rbutton_press, FX_TAB_TREE)
            else: self.result_list.connect("button-press-event", self._rbutton_press, FX_TAB_RESULTS)

            self.result_list.set_enable_search(True)
            self.result_list.set_search_equal_func(self.parent.quick_find_case_ins, 4)

            if self.type == FX_TAB_TREE:
                self.result_list.set_enable_tree_lines(True)
                self.result_list.set_level_indentation(20)





        elif self.type == FX_TAB_NOTES:

            self.result_list.append_column( f_col('', 3, 0, yalign=0.1, resizable=False, clickable=False, width=32, reorderable=False) )
            columns = {}
            columns[1] = f_col(_('Entry'), 1, 2, yalign=0, note=True, start_width=self.parent.gui_attrs.get('notes',{}).get('1',650), name='1')
            columns[2] = f_col(_('Date'), 1, 3, sort_col=6, start_width=self.parent.gui_attrs.get('notes',{}).get('2',150), name='2')
            columns[3] = f_col(_('Source'), 1, 4, start_width=self.parent.gui_attrs.get('notes',{}).get('3',200), name='3')
            columns[4] = f_col(_('Link'), 0, 5, start_width=self.parent.gui_attrs.get('notes',{}).get('4',100), name='4')
            columns[5] = f_col(_('Importance'), 0, 7, start_width=self.parent.gui_attrs.get('notes',{}).get('5',100), name='5')
            columns[6] = f_col(_('Readability'), 0, 8, start_width=self.parent.gui_attrs.get('notes',{}).get('6',100), name='6')
            columns[7] = f_col(_('Word Count'), 0, 9, start_width=self.parent.gui_attrs.get('notes',{}).get('7',100), name='7')
            columns[8] = f_col(_('Rank'), 0, 10, start_width=self.parent.gui_attrs.get('notes',{}).get('8',100), name='8')
            columns[9] = f_col(_('Term Count'), 0, 11, start_width=self.parent.gui_attrs.get('notes',{}).get('9',100), name='9')

            for c in self.parent.gui_attrs.get('notes_order', FX_DEF_COLS_NOTES): self.result_list.append_column(columns[c])

            self.result_list.set_tooltip_markup(_("""Double-click to edit. 
Right-click for more options
Hit <b>Ctrl-F</b> for interactive search by Title"""))

            self.result_list.connect("row-activated", self.parent.on_activate_result)
            self.result_list.connect("button-press-event", self._rbutton_press, FX_TAB_NOTES)

            self.result_list.set_enable_search(True)
            self.result_list.set_search_equal_func(self.parent.quick_find_case_ins, 1)

            self.result_list.set_grid_lines(True)




        elif self.type == FX_TAB_CONTEXTS:

            self.result_list.append_column( f_col('', 3, 0, resizable=False, clickable=False, width=16, reorderable=False) )
            columns = {}
            columns[3] = f_col(_('Context'), 1, 3, start_width=self.parent.gui_attrs.get('contexts',{}).get('3',650), name='3')
            columns[17] = f_col(_('Date'), 0, 17, sort_col=8, start_width=self.parent.gui_attrs.get('contexts',{}).get('15',150), name='15')
            columns[4] = f_col(_('Source'), 0, 4, start_width=self.parent.gui_attrs.get('contexts',{}).get('4',200), name='4')
            columns[5] = f_col(_('Title'), 0, 5, start_width=self.parent.gui_attrs.get('contexts',{}).get('5',650), name='5')
            columns[19] = f_col(_('Flag'), 1, 19, start_width=self.parent.gui_attrs.get('contexts',{}).get('19',150), name='19')
            columns[7] = f_col(_('Publ. Timestamp'), 0, 7, start_width=self.parent.gui_attrs.get('contexts',{}).get('7',200), name='7')
            columns[9] = f_col(_('Read?'), 0, 9, start_width=self.parent.gui_attrs.get('contexts',{}).get('9',200), name='9')
            columns[10] = f_col(_('Flag ID'), 0, 10, start_width=self.parent.gui_attrs.get('contexts',{}).get('10',200), name='10')
            columns[11] = f_col(_('Importance'), 0, 11, start_width=self.parent.gui_attrs.get('contexts',{}).get('11',200), name='11')
            columns[12] = f_col(_('Weight'), 0, 12, start_width=self.parent.gui_attrs.get('contexts',{}).get('12',200), name='12')
            columns[13] = f_col(_('Readability'), 0, 13, start_width=self.parent.gui_attrs.get('contexts',{}).get('13',200), name='13')
            columns[14] = f_col(_('Word Count'), 0, 14, start_width=self.parent.gui_attrs.get('contexts',{}).get('14',200), name='14')
            columns[6] = f_col(_('Link'), 0, 6, start_width=self.parent.gui_attrs.get('contexts',{}).get('6',400), name='6')
            columns[15] = f_col(_('Term Count'), 0, 15, start_width=self.parent.gui_attrs.get('contexts',{}).get('15',200), name='15')
            columns[16] = f_col(_('Search Rank'), 0, 16, start_width=self.parent.gui_attrs.get('contexts',{}).get('16',200), name='16')
            for c in self.parent.gui_attrs.get('contexts_order', FX_DEF_COLS_CONTEXTS): self.result_list.append_column(columns[c])

            self.result_list.set_tooltip_markup(_("""Search phrase in context is shown here.
Double-click to open the entry containing a context.
Right-click for more options
Hit <b>Ctrl-F</b> for interactive search by Title"""))

            self.result_list.connect("row-activated", self.parent.on_activate_result)
            self.result_list.connect("button-press-event", self._rbutton_press, FX_TAB_CONTEXTS)

            self.result_list.set_enable_search(True)
            self.result_list.set_search_equal_func(self.parent.quick_find_case_ins, 5)





        elif self.type == FX_TAB_TERM_NET:

            columns = {}
            columns[1] = f_col(_('Term'), 0, 0, start_width=self.parent.gui_attrs.get('terms',{}).get('1',200), name='1')
            columns[2] = f_col(_('Weight'), 0, 1, start_width=self.parent.gui_attrs.get('terms',{}).get('2',200), name='2')
            columns[3] = f_col(_('Count'), 0, 2, start_width=self.parent.gui_attrs.get('terms',{}).get('3',100), name='3')
            for c in self.parent.gui_attrs.get('terms_order', FX_DEF_COLS_TERM_NET): self.result_list.append_column(columns[c])

            self.result_list.set_tooltip_markup(_("""These are terms from read entries related to the one queries for. Hit <b>Ctrl-F</b> for interactive search""") )

            self.result_list.connect("button-press-event", self._rbutton_press, FX_TAB_TERM_NET)
            
            self.result_list.set_enable_search(True)
            self.result_list.set_search_equal_func(self.parent.quick_find_case_ins, 0)






        elif self.type in (FX_TAB_TIME_SERIES, FX_TAB_REL_TIME):

            columns = {}
            columns[1] = f_col(_('Time'), 0, 0, start_width=self.parent.gui_attrs.get('time_series',{}).get('1',200), name='1')
            columns[2] = f_col('', 1, 1, start_width=self.parent.gui_attrs.get('time_series',{}).get('2',800), name='2', clickable=False)
            columns[3] = f_col(_('Count'), 0, 2, start_width=self.parent.gui_attrs.get('time_series',{}).get('3',100), name='3')
            for c in self.parent.gui_attrs.get('time_series_order', FX_DEF_COLS_TIME_SERIES): self.result_list.append_column(columns[c])

            self.result_list.set_tooltip_markup("Right-click for more options")
            self.result_list.connect("button-press-event", self._rbutton_press, self.type)





        elif self.type == FX_TAB_RULES:

            columns = {}
            columns[1] = f_col(_('Name'), 0, 1, color_col=10, start_width=self.parent.gui_attrs.get('rules',{}).get('1',200), name='1')
            columns[2] = f_col(_('Search String'), 0, 2, color_col=10, start_width=self.parent.gui_attrs.get('rules',{}).get('2',200), name='2')
            columns[3] = f_col(_('Weight'), 0, 3, color_col=10, start_width=self.parent.gui_attrs.get('rules',{}).get('3',100), name='3')
            columns[4] = f_col(_('Case ins.'), 0, 4, color_col=10, start_width=self.parent.gui_attrs.get('rules',{}).get('4',50), name='4')
            columns[5] = f_col(_('Type'), 0, 5, color_col=10, start_width=self.parent.gui_attrs.get('rules',{}).get('5',200), name='5')
            columns[6] = f_col(_('Learned?'), 0, 6, color_col=10, start_width=self.parent.gui_attrs.get('rules',{}).get('6',50), name='6')
            columns[7] = f_col(_('Flag'), 0, 7, color_col=10, start_width=self.parent.gui_attrs.get('rules',{}).get('7',50), name='7')
            columns[8] = f_col(_('On Field'), 0, 8, color_col=10, start_width=self.parent.gui_attrs.get('rules',{}).get('8',150), name='8')
            columns[9] = f_col(_('On Feed/Category'), 0, 9, color_col=10, start_width=self.parent.gui_attrs.get('rules',{}).get('9',450), name='9')
            for c in self.parent.gui_attrs.get('rules_order', FX_DEF_COLS_RULES): self.result_list.append_column(columns[c])

            self.result_list.set_tooltip_markup(_("""These are manually added rules used for ranking and flagging. 
Double-click to edit. 
Right-click for more options
Hit <b>Ctrl-F</b> for interactive search""") )

            self.result_list.connect("button-press-event", self._rbutton_press, FX_TAB_RULES)
            self.result_list.connect("row-activated", self._on_activate_rule)

            self.result_list.set_enable_search(True)
            self.result_list.set_search_equal_func(self.parent.quick_find_case_ins, 2)


        elif self.type == FX_TAB_FLAGS:

            columns = {}
            columns[1] = f_col(_('Id'), 0, 0, color_col=3, start_width=self.parent.gui_attrs.get('flags',{}).get('1',50), name='1')
            columns[2] = f_col(_('Name'), 0, 1, color_col=3, start_width=self.parent.gui_attrs.get('flags',{}).get('2',200), name='2')
            columns[3] = f_col(_('Description'), 0, 2, color_col=3, start_width=self.parent.gui_attrs.get('flags',{}).get('3',400), name='3')
            for c in self.parent.gui_attrs.get('flags_order', FX_DEF_COLS_FLAGS): self.result_list.append_column(columns[c])

            self.result_list.set_tooltip_markup(_("""Flags used in rules and for manual marking of Entries
Right-click for more options""") )
            self.result_list.connect("button-press-event", self._rbutton_press, self.type)
            self.result_list.connect("row-activated", self._on_activate_flag)



        self.result_selection = self.result_list.get_selection()

        list_box = Gtk.ScrolledWindow()
        list_box.add(self.result_list)

        self.main_box.pack_start(list_box, True, True, 1)

        self.result_list.connect("cursor-changed", self.load_selection)


        if self.debug in (1,7): print(f'Tab created (id: {self.tab_id}, type:{self.type})')






    def _expand_all(self, *args):
        if self.type == FX_TAB_TREE: self.result_list.expand_all()
    def _collapse_all(self, *args):
        if self.type == FX_TAB_TREE: self.result_list.collapse_all()




    def _on_activate_rule(self, *args): self.parent.on_edit_rule(False)
    def _on_activate_flag(self, *args): self.parent.on_edit_flag(False)


    

    def _clear_query_entry(self, *args, **kargs): self.query_entry.set_text('')

    def save_layout(self, *args, **kargs):
        """ Change QUI attributes to save in main class if something changes in here """
        order = []
        sizes = {}
        for c in self.result_list.get_columns():
            name = c.get_name()
            if name is None: continue
            sizes[name] = c.get_width()
            order.append(int(name))

        if self.type in (FX_TAB_PLACES, FX_TAB_SEARCH, FX_TAB_SIMILAR, FX_TAB_TREE):
            self.parent.gui_attrs['results'] = sizes
            self.parent.gui_attrs['results_order'] = order
        elif self.type == FX_TAB_CONTEXTS:
            self.parent.gui_attrs['contexts'] = sizes
            self.parent.gui_attrs['contexts_order'] = order
        elif self.type == FX_TAB_TERM_NET:
            self.parent.gui_attrs['terms'] = sizes
            self.parent.gui_attrs['temrs_order'] = order
        elif self.type == FX_TAB_RULES:
            self.parent.gui_attrs['rules'] = sizes
            self.parent.gui_attrs['rules_order'] = order
        elif self.type == FX_TAB_FLAGS:
            self.parent.gui_attrs['flags'] = sizes
            self.parent.gui_attrs['flags_order'] = order
        elif self.type == FX_TAB_NOTES:
            self.parent.gui_attrs['notes'] = sizes
            self.parent.gui_attrs['notes_order'] = order
        elif self.type in (FX_TAB_TIME_SERIES, FX_TAB_REL_TIME):
            self.parent.gui_attrs['time_series'] = sizes
            self.parent.gui_attrs['time_series_order'] = order
        self.parent.update_status(0, -('Layout saved as default for this tab type') )
        if self.debug in (1,7): print(f'Layout saved: {self.parent.gui_attrs}')


    def save_filters(self, *args, **kargs):
        """ Save current search filters as default for the future """
        if self.type in (FX_TAB_SEARCH, FX_TAB_CONTEXTS, FX_TAB_TIME_SERIES, FX_TAB_REL_TIME, FX_TAB_TREE, FX_TAB_NOTES):
            self.get_search_filters()
            self.parent.default_search_filters = self.search_filters.copy()
            self.parent.gui_attrs['default_search_filters'] = self.search_filters.copy()
            self.parent.update_status(0, _('Filters saved as defaults') )
            if self.debug in (1,7): print(f"Changed default filters: {self.parent.gui_attrs['default_search_filters']}")




    def on_close(self, *args, **kargs): self.parent.remove_tab(self.tab_id)


    def reload_history(self, *args, **kargs):
        """ Refresh search history from DB """
        self.history.clear()
        for h in self.parent.FX.MC.search_history: self.history.append((h[0],))



    def add_date_str_to_combo(self, date_string):
            new_d = (f'_{date_string}', date_string)
            model = self.qtime_combo.get_model()
            for d in model:
                if d[0] == new_d[0]: return 0
            model.append(new_d)
            self.qtime_combo.set_model(model)
            self.qtime_combo.set_active(len(model)-1)
            self.parent.date_store_added.append(new_d)
        

    def on_date_changed(self, *args):
        """ React when user requests a calendar """
        if f_get_combo(self.qtime_combo) == 'choose_dates':
            
            dialog = CalendarDialog(self.parent)
            dialog.run()
            if dialog.response == 1:
                self.add_date_str_to_combo(dialog.result["date_string"])
                dialog.destroy()
            else:
                self.qtime_combo.set_active(0)
                dialog.destroy()
                return -1




    def on_filters_changed(self, *args, **krags):
        """ Update dictionary if filters change"""
        if self.type != FX_TAB_REL_TIME:  
            if f_get_combo(self.qtype_combo) in (1,2):
                self.qlang_combo.set_sensitive(True)
                self.query_entry.set_tooltip_markup(_("""Enter your search phrase here
Wildcard: <b>*</b> or <b>.</b> (single character)
Field beginning: <b>^</b>
Field end: <b>$</b>
Near: <b>~(number of words)</b>
Escape: \ (only if before wildcard)""") )
            else:
                self.qlang_combo.set_sensitive(False)
                self.query_entry.set_tooltip_markup(_("""Enter your search string here
Wildcard: <b>*</b> or <b>.</b> (single character)
Field beginning: <b>^</b>
Field end: <b>$</b>
Escape: \ (only if before wildcard)""") )

            if self.debug in (1,7): print('Search filters changed...')




 

    def get_search_filters(self, **kargs):
        """ Get search filters state and put it into global dictionary """
        self.search_filters = {}

        time = f_get_combo(self.qtime_combo)
        if time.startswith('_') and time != '__dummy':
            time = time[1:]
            dts = time.split(' --- ')
            if dts[0] != '...': self.search_filters['date_from'] = dts[0]
            if dts[1] != '...': self.search_filters['date_to'] = dts[1]
        else:
            self.search_filters[time] = True
        
        self.search_filters[f_get_combo(self.qtime_combo)] = True
        self.search_filters['feed_or_cat'] = f_get_combo(self.cat_combo)
        
        if self.type != FX_TAB_REL_TIME:
            self.search_filters[f_get_combo(self.read_combo)] = True
            self.search_filters[f_get_combo(self.case_combo)] = True

            self.search_filters['flag'] = f_get_combo(self.flag_combo)
            self.search_filters['handler'] = f_get_combo(self.qhandler_combo)
            self.search_filters['note'] = f_get_combo(self.notes_combo, null_val=-1)

            self.search_filters['field'] = f_get_combo(self.qfield_combo)
            self.search_filters['lang'] = f_get_combo(self.qlang_combo)
            self.search_filters['qtype'] = f_get_combo(self.qtype_combo)

        if self.type in (FX_TAB_TIME_SERIES, FX_TAB_REL_TIME): 
            self.search_filters['group'] = f_get_combo(self.time_series_combo)

        if self.type == FX_TAB_TREE:
            self.search_filters['group'] = f_get_combo(self.group_combo)
            self.search_filters['depth'] = f_get_combo(self.depth_combo)            
            self.search_filters['default_sort'] = f_get_combo(self.sort_combo)

        if self.debug in (1,7): print(f'Search filters updated: {self.search_filters}')
        return 0
        
 


    def on_restore(self, *args, **kargs):
        """ Restore default filters """
        if self.type == FX_TAB_REL_TIME:
            f_set_combo(self.time_series_combo, self.parent.default_search_filters.get('group'))
            f_set_combo_from_bools(self.qtime_combo, self.parent.default_search_filters)
            f_set_combo(self.cat_combo, self.parent.default_search_filters.get('feed_or_cat'), null_val=-1)

        else:
            f_set_combo_from_bools(self.qtime_combo, self.parent.default_search_filters)
            f_set_combo_from_bools(self.read_combo, self.parent.default_search_filters)
            f_set_combo_from_bools(self.case_combo, self.parent.default_search_filters)
    
            f_set_combo(self.flag_combo, self.parent.default_search_filters.get('flag'))
            f_set_combo(self.qhandler_combo, self.parent.default_search_filters.get('handler'))

            f_set_combo(self.notes_combo, self.parent.default_search_filters.get('note'), null_val=-1)
        
            f_set_combo(self.cat_combo, self.parent.default_search_filters.get('feed_or_cat'), null_val=-1)
            f_set_combo(self.qfield_combo, self.parent.default_search_filters.get('field'))
            f_set_combo(self.qlang_combo, self.parent.default_search_filters.get('lang'))
            f_set_combo(self.qtype_combo, self.parent.default_search_filters.get('qtype'))

            if self.type == FX_TAB_TIME_SERIES:
                f_set_combo(self.time_series_combo, self.parent.default_search_filters.get('group'))
            if self.type == FX_TAB_TREE:
                f_set_combo(self.group_combo, self.parent.default_search_filters.get('group'))
                f_set_combo(self.depth_combo, self.parent.default_search_filters.get('depth'))
                f_set_combo(self.sort_combo, self.parent.default_search_filters.get('default_sort'))

        self.on_filters_changed()











    def block_search(self, tab_text:str):
        """ Do some maintenance on starting a search """
        if self.type in (FX_TAB_SEARCH, FX_TAB_CONTEXTS, FX_TAB_TERM_NET, FX_TAB_TIME_SERIES, FX_TAB_TREE, FX_TAB_NOTES):
            self.search_button.set_sensitive(False)
            self.query_combo.set_sensitive(False)
        elif self.type == FX_TAB_REL_TIME:
            self.search_button.set_sensitive(False)

        self.spinner.show()
        self.spinner.start()
        self.header.set_markup(tab_text)




    def finish_search(self):
        """ This is called by main window when it receives signals of finished search thread
            Performs maintenance, beautifies etc.
        """
        self.processing_flag = False

        if self.type in (FX_TAB_SEARCH, FX_TAB_CONTEXTS, FX_TAB_TERM_NET, FX_TAB_TIME_SERIES, FX_TAB_TREE, FX_TAB_NOTES):
            self.reload_history()
            self.search_button.set_sensitive(True)
            self.query_combo.set_sensitive(True)
        
        elif self.type == FX_TAB_REL_TIME:
            self.search_button.set_sensitive(True)

        self.result_store = self.tmp_store
        self.result_list.set_model(self.result_store)
        if self.type == FX_TAB_TREE: self.result_list.expand_all()

        self.spinner.hide()
        self.spinner.stop()
        if self.type == FX_TAB_TREE: 
            sum = 0
            for r in self.results:
                if r[0] is not None: sum += 1
            self.header.set_markup( f'{self.final_status} ({sum})' )
        else: self.header.set_markup( f'{self.final_status} ({len(self.result_store)})' )

        if self.parent.curr_upper == self.tab_id and self.refresh_feeds: 
            self.parent.feed_win.feed_aggr = self.feed_aggr
            self.parent.feed_win.reload_feeds()







    def _query(self, qr, filters, **kargs):
        """ Wrapper for sending queries """
        add_top_entry = False
        # DB interface for queries

        FX = Feeder(self.parent.MC, config=self.config, debug=self.debug, ignore_images=True, gui=True, load_icons=False, print=False)



        if self.type in (FX_TAB_SEARCH, FX_TAB_NOTES):

            feed_name = f_get_combo(self.cat_combo, name=True)

            filters['rev'] = True
            filters['default_sort'] = '+pubdate'
            self.results = FX.QP.query(qr, filters)

            if self.type == FX_TAB_NOTES: marker = '*'
            else: marker = ''

            if FX.QP.phrase.get('empty',False):
                if feed_name is None: self.final_status = f"""{marker}{_('Results')}"""
                else: self.final_status = f'<b>{marker}{esc_mu(feed_name, ell=50)}</b>'
            else: 
                if feed_name is None: self.final_status = f'{marker}{_("Search for ")}<b>{esc_mu(qr, ell=50)}</b>'
                else: self.final_status = f'{marker}{_("Search for ")}<b>{esc_mu(qr, ell=50)}</b> {_("in")} <b><i>{esc_mu(feed_name, ell=50)}</i></b>'




        elif self.type == FX_TAB_PLACES:
 
            if qr == FX_PLACE_STARTUP:
                self.results = FX.QP.query('*', {'last':True, 'sort':'-importance'})
                if len(self.results) <= 2:
                    self.results = FX.QP.query('*', {'last_hour':True, 'sort':'-importance'})
                    if len(self.results) <= 2:
                        self.results = FX.QP.query('*', {'today':True, 'sort':'-importance'})
                        if len(self.results) <= 2:
                            self.results = FX.QP.query('*', {'last_n':2, 'sort':'-importance'})

                self.final_status = 'News'


            elif qr == FX_PLACE_TRASH_BIN:

                self.results = FX.QP.query('*', {'deleted_entries':True, 'sort':'-pubdate'}, no_history=True)
                self.final_status = _('Trash bin')

            else:
                filters = {'sort':'-importance'}
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

                self.results = FX.QP.query('*', filters, no_history=True)


        elif self.type == FX_TAB_SIMILAR:

            self.final_status = _('Similar to ...')            
            filters['rev'] = True
            self.results = FX.QP.find_similar(self.top_entry['id'], **filters)
            add_top_entry = True

        elif self.type == FX_TAB_REL_TIME:
            self.final_status = f"{_('Relevance in Time ')}(<b>{self.top_entry['id']}</b>)..."            
            self.results = FX.QP.relevance_in_time(self.top_entry['id'], **filters)

        elif self.type == FX_TAB_CONTEXTS:
            self.final_status = f'{_("Contexts for ")}<b>{esc_mu(qr, ell=50)}</b>'
            filters['rev'] = True
            self.results = FX.QP.term_context(qr, **filters)

        elif self.type == FX_TAB_TERM_NET:
            self.final_status = f'{_("Terms related to ")}<b>{esc_mu(qr, ell=50)}</b>'
            self.results = FX.QP.term_net(qr, print=False, lang=filters.get('lang'), rev=True)

        elif self.type == FX_TAB_TIME_SERIES:
            self.final_status = f'{_("Time Series for ")}<b>{esc_mu(qr, ell=50)}</b>'
            self.results = FX.QP.term_in_time(qr, **filters)

        elif self.type == FX_TAB_TREE:

            if qr == FX_PLACE_STARTUP:
                
                self.final_status = f'{_("Summary - latest")}'
                group = filters.get('group','category')
                self.results = FX.QP.query('*', {'last':True, 'sort':'+importance', 'group':group, 'rev':True}, allow_group=True)
                if len(self.results) <= 5:
                    self.results = FX.QP.query('*', {'last_hour':True, 'sort':'+importance', 'group':group, 'rev':True}, allow_group=True)
                    if len(self.results) <= 5:
                        self.results = FX.QP.query('*', {'today':True, 'sort':'+importance', 'group':group, 'rev':True}, allow_group=True)
                        if len(self.results) <= 6:
                            self.results = FX.QP.query('*', {'last_n':2, 'sort':'+importance', 'group':group, 'rev':True}, allow_group=True)
            else:
                self.final_status = f'{_("Summary ")}<b>{esc_mu(qr, ell=50)}</b>'
                filters['rev'] = True
                self.results = FX.QP.query(qr, filters, allow_group=True)

        if FX.db_error is not None: 
            self.final_status = f'<span foreground="red">{self.final_status}</span>'
            self.parent.message_q.append( (0, (-2, _('DB error: %a'), FX.db_error),) )
        else: self.parent.message_q.append( (0, '') )
        
        FX.close()
        self._create_list(True, (0,), True, add_top_entry=add_top_entry)







    def query(self, phrase, filters):
        """ As above, threading"""
        if self.processing_flag: return -1
        self.processing_flag = True
        
        self.block_search(_("Searching...") )
        self.refresh_feeds = True
        self.feed_filter_id = 0
        self.search_thread = threading.Thread(target=self._query, args=(phrase, filters)   )
        self.search_thread.start()


    def on_query(self, *args):
        """ Wrapper for executing query from the tab """
        if self.type != FX_TAB_TERM_NET: self.get_search_filters()
        if self.type != FX_TAB_REL_TIME: self.query(self.query_entry.get_text(), self.search_filters)
        else: self.query('', self.search_filters)








    def _rbutton_press(self, widget, event, from_where):
        self.load_selection(clear=True)
        self.parent._rbutton_press(widget, event, from_where)


    def load_selection(self, *args, **kargs):
        """ Wrapper for loading result data from feeder class results by id and populating SQL container"""
        if self.processing_flag: return -1

        model, treeiter = self.result_selection.get_selected()
        if treeiter is None:
            if kargs.get('clear',False):
                if self.type in (FX_TAB_PLACES, FX_TAB_SEARCH, FX_TAB_SIMILAR, FX_TAB_TREE, FX_TAB_NOTES): self.parent.selection_res.clear()
                elif self.type == FX_TAB_CONTEXTS: self.parent.selection_res.clear()
                elif self.type == FX_TAB_TERM_NET: self.parent.selection_term = None
                elif self.type == FX_TAB_RULES: self.parent.selection_rule.clear()
                elif self.type == FX_TAB_FLAGS: self.parent.selection_flag.clear()
                elif self.type == (FX_TAB_TIME_SERIES, FX_TAB_REL_TIME): self.parent.selection_time_series = None

            if self.debug in (1,7): print('Empty selection...')
            return -1
        
        ix = model[treeiter][-1]

        if self.type in (FX_TAB_PLACES, FX_TAB_SEARCH, FX_TAB_SIMILAR, FX_TAB_NOTES):            
            self.parent.selection_res.populate(self.results[ix])
            self.parent.on_changed_selection(type=self.type)
            if self.debug in (1,7): print(f'Selection (res): {self.parent.selection_res["id"]}')

        elif self.type == FX_TAB_TREE:
            if self.results[ix][0] is not None:            
                self.parent.selection_res.populate(self.results[ix][:-1])
                self.parent.on_changed_selection(type=self.type)
                if self.debug in (1,7): print(f'Selection (res): {self.parent.selection_res["id"]}')
            else: self.parent.selection_res.clear()

        elif self.type == FX_TAB_CONTEXTS:
            self.parent.selection_res.populate(self.results[ix][:-1])
            self.parent.on_changed_selection(type=self.type)
            if self.debug in (1,7): print(f'Selection (context): {self.parent.selection_res["id"]}')

        elif self.type == FX_TAB_RULES:
            self.parent.selection_rule.populate(self.results[ix])
            if self.debug in (1,7): print(f'Selection (rule): {self.parent.selection_rule["id"]}')

        elif self.type == FX_TAB_FLAGS:
            self.parent.selection_flag.populate(self.results[ix])
            if self.debug in (1,7): print(f'Selection (flag): {self.parent.selection_flag["id"]}')

        elif self.type == FX_TAB_TERM_NET:
            self.parent.selection_term = self.results[ix][0]
            if self.debug in (1,7): print(f'Selection (term): {self.parent.selection_term}')

        elif self.type in (FX_TAB_TIME_SERIES, FX_TAB_REL_TIME):
            self.parent.selection_time_series['start_date'] = self.results[ix][0]
            self.parent.selection_time_series['group'] = self.search_filters.get('group')
            if self.debug in (1,7): print(f'Selection (time_series): {self.parent.selection_time_series}')

        return 0
        















    def _create_list(self, feed_sum, feed_filter, ignore_filters, **kargs):
        """ Wrapper for processing given raw results thread"""

        if self.type == FX_TAB_TREE: self.tmp_store = Gtk.TreeStore(*self.column_types)
        else: self.tmp_store = Gtk.ListStore(*self.column_types)

        if self.type in (FX_TAB_PLACES, FX_TAB_SEARCH, FX_TAB_SIMILAR):

            if kargs.get('add_top_entry', False):
                for i,r in enumerate(self.results):
                    if r[self.result.get_index('id')] == self.top_entry['id']:
                       del self.results[i]
                       break
                self.tmp_store.append(self._result_store_item(self.top_entry, len(self.results), new=True) )
                
            self.create_results_list(feed_sum=feed_sum, feed_filter=feed_filter, ignore_filters=ignore_filters)
            
            if kargs.get('add_top_entry', False): self.results.append(self.top_entry.tuplify())

        elif self.type == FX_TAB_NOTES:
            self.create_results_list(feed_sum=feed_sum, feed_filter=feed_filter, ignore_filters=ignore_filters)

        elif self.type == FX_TAB_CONTEXTS:
            self.create_contexts_list(feed_sum=feed_sum, feed_filter=feed_filter, ignore_filters=ignore_filters)

        elif self.type == FX_TAB_TERM_NET:
            self.create_terms_list()

        elif self.type in (FX_TAB_TIME_SERIES, FX_TAB_REL_TIME):
            self.create_time_series()

        elif self.type == FX_TAB_RULES:
            self.create_rules_list()

        elif self.type == FX_TAB_FLAGS:
            self.create_flags_list()

        elif self.type == FX_TAB_TREE:
            self.create_results_tree(feed_sum=feed_sum, feed_filter=feed_filter, ignore_filters=ignore_filters)

        self.parent.lock.acquire()
        self.parent.action_q.append((self.uid, FX_ACTION_FINISHED_SEARCH))
        self.parent.lock.release()




    def create_list(self, feed_sum, feed_filter, ignore_filters, **kargs):
        """ As above - thread execution and notification """
        if self.processing_flag: return -1
        if len(self.results) == 0: return 0
        
        if kargs.get('results') is not None:
            if self.type != FX_TAB_RULES: self.results = kargs.get('results').copy()

        self.block_search(_('Filtering...') )
        self.refresh_feeds = False
            
        self.processing_flag = True
        self.search_thread = threading.Thread(target=self._create_list, args=(feed_sum, feed_filter, ignore_filters,)   )
        self.search_thread.start()





    def _result_store_item(self, result, res_idx, **kargs):
        """ Generate result item for table """
        icon = self.parent.icons.get(result["feed_id"],self.parent.icons['default'])
        source = result["feed_name"]

        desc = scast(result.get("desc",''),str,'')
        desc = (desc[:75] + '...') if len(desc) > 75 else desc  
        if result.get('read',0) >= 1 or kargs.get('new',False): weight = 700
        else: weight = 400

        if kargs.get('new',False): color = self.config.get('gui_new_color','#0FDACA')
        elif result.get('deleted',0) == 1: color = self.config.get('gui_deleted_color','grey')
        elif result.get('deleted',0) == 2: color = 'red'
        elif result.get('flag',0) > 0: color = self.parent.FX.get_flag_color(result.get('flag',0)) 
        else: color = None

        return (icon, 
                result.get("id",0),
                result.get("feed_id",0), 
                source,
                result.get("title",'').replace('\n',' '), 
                desc.replace('\n',' '), 
                result.get("link",''),
                result.get("author",''), 
                result.get("publisher",''), 
                result.get("category",''),
                result.get("pubdate_r",''), 
                result.get("pubdate",0), 
                result.get("adddate_str",''), 
                result.get("adddate",0),
                result.get("read",0), 
                result.get("flag",0), 
                result.get("importance",0), 
                result.get("weight",0),
                result.get("readability",0), 
                result.get("word_count",0),
                result.get('rank',0), 
                result.get('count',0), 
                result.get('similarity',0),
                weight,
                color,
                humanize_date(result.get('pubdate_short',''), self.parent.today, self.parent.yesterday, self.parent.year),
                result.get("flag_name",''),
                res_idx,
                )


    def _notes_store_item(self, result, res_idx, **kargs):
        """ Build note list item """
        icon = self.parent.icons.get(result["feed_id"],self.parent.icons['default'])
        source = result["feed_name"]

        desc = scast(result.get("desc",''),str,'')
        desc = (desc[:500] + '...') if len(desc) > 500 else desc

        title = result.get("title",'').replace('\n',' ')

        if result.get('flag',0) > 0: 
            color = self.parent.FX.get_flag_color(result.get('flag',0)) 
            flag_str = f"""<b><span foreground="{color}">{esc_mu(result.get("flag_name",''))}</span></b>: """
        else: flag_str = ''



        entry = f"""---------------------------------------------------------------------------------
{flag_str}<b>{esc_mu(title)}</b>
{esc_mu(desc)
}"""

        date = humanize_date(result.get('pubdate_short',''), self.parent.today, self.parent.yesterday, self.parent.year)

        return (icon, result.get("id",0), entry, f'<b>{esc_mu(date)}</b>', f'<b>{esc_mu(source)}</b>', result.get("link",''), result.get("pubdate",0), 
                result.get('importance',0), result.get('readability',0), result.get('word_count',0), result.get('rank',0), result.get('count',0), res_idx)





    def create_results_list(self, **kargs):
        """ Gets result from Feeder subclass and generates display"""
        feed_filter = kargs.get('feed_filter')
        ignore_filters = kargs.get('ignore_filters',False)
        feed_sum = kargs.get('feed_sum',False)
        notes = kargs.get('notes',False)

        if feed_sum: self.feed_aggr = {}

        for ix,r in enumerate(self.results):

            self.result.populate(r)
            # Apply feed/category filters
            if not ignore_filters and self.result["feed_id"] != feed_filter and self.result["parent_id"] != feed_filter: continue

            if feed_sum: 
                self.feed_aggr[self.result['feed_id']] = self.feed_aggr.get(self.result['feed_id'],0) + 1
                if self.result['parent_id'] is not None: self.feed_aggr[self.result['parent_id']] = self.feed_aggr.get(self.result['parent_id'],0) + 1

            if self.type != FX_TAB_NOTES: self.tmp_store.append(self._result_store_item(self.result, ix))
            else: self.tmp_store.append(self._notes_store_item(self.result, ix))




    def _tree_group_item(self, result, res_idx, **kargs):
        """ Grouping item for tree display (feed, category or flag)"""
        icon = self.parent.icons.get(result["feed_id"], self.parent.icons.get(result['flag_name']))
        if icon is None: icon = self.parent.icons['doc']

        title = result.get("title",'').replace('\n',' ')

        return (icon, 0,0, None, f"""<b><u>{esc_mu(title)}</u></b>""", None, None,None, None, None,None, 0, None, 0,0, 0, 0, 0,0, 0,0, 0, 0, 700, None,None,None,res_idx,)
        


    def create_results_tree(self, **kargs):
        """ As stated in name """
        feed_filter = kargs.get('feed_filter')
        ignore_filters = kargs.get('ignore_filters',False)
        feed_sum = kargs.get('feed_sum',False)

        if feed_sum: self.feed_aggr = {}

        current_node = None

        for ix,r in enumerate(self.results):

            self.tree_result.populate(r)

            if self.tree_result['is_node'] == 1:
                current_node = self.tmp_store.append( None, self._tree_group_item(self.tree_result, ix) )
                continue

            # Apply feed/category filters
            if not ignore_filters and self.tree_result["feed_id"] != feed_filter and self.tree_result["parent_id"] != feed_filter: continue

            if feed_sum: 
                self.feed_aggr[self.tree_result['feed_id']] = self.feed_aggr.get(self.tree_result['feed_id'],0) + 1
                if self.tree_result['parent_id'] is not None: self.feed_aggr[self.tree_result['parent_id']] = self.feed_aggr.get(self.tree_result['parent_id'],0) + 1

            self.tree_result['title'] = esc_mu(self.tree_result['title'])
            self.tmp_store.append(current_node, self._result_store_item(self.tree_result, ix))








    def _contexts_store_item(self, context, con_idx):
        """ Generates context item for table display """
        icon = self.parent.icons.get(context["feed_id"], self.parent.icons['default'])
        source = context["feed_name"]
        desc = scast(context.get("desc",''),str,'')
        desc = (desc[:75] + '...') if len(desc) > 75 else desc

        #if context.get('flag',0) >= 1: color = self.config.get('gui_flag_color','blue')
        flag_id = coalesce(context.get('flag'),0)
        if coalesce(flag_id,0) != 0: flag_name = esc_mu(self.parent.FX.get_flag_name(flag_id))
        else: flag_name = None
        flag_col = self.parent.FX.get_flag_color(flag_id)
        if flag_col is not None: flag_name = f'<span foreground="{flag_col}">{flag_name}</span>'

        if context.get('deleted',0) == 1: color = self.config.get('gui_deleted_color','grey')
        elif context.get('deleted',0) == 2: color = 'red'
        else: color = None


        return (    icon, 
                    context.get("id",0),
                    context.get("feed_id",0),
                    sanitize_snippet(context.get("context",(None,))[0]),
                    source,
                    context.get("title",''),
                    context.get("link",''),
                    context.get("pubdate_r",''),
                    context.get("pubdate",0),
                    context.get("read",0),
                    flag_id,
                    context.get("importance",0),
                    context.get("weight",0),
                    context.get("readability",0),
                    context.get("word_count",0),
                    context.get("count",0),
                    context.get("rank",0),                    
                    humanize_date(context.get('pubdate_short',''), self.parent.today, self.parent.yesterday, self.parent.year),
                    color,
                    flag_name,
                    con_idx,
                )



    def create_contexts_list(self, **kargs):
        """ Reload context store """
        feed_filter = kargs.get('feed_filter')
        ignore_filters = kargs.get('ignore_filters',False)
        feed_sum = kargs.get('feed_sum',False)

        if feed_sum: self.feed_aggr = {}

        for ix, r in enumerate(self.results): 

            self.context.populate(r)
            
            # Apply filters fro feeds/categories
            if not ignore_filters and self.context["feed_id"] != feed_filter and self.context["parent_id"] != feed_filter: continue

            if feed_sum: 
                self.feed_aggr[self.context['feed_id']] = self.feed_aggr.get(self.context['feed_id'],0) + 1
                if self.context['parent_id'] is not None: self.feed_aggr[self.context['parent_id']] = self.feed_aggr.get(self.context['parent_id'],0) + 1

            self.tmp_store.append(self._contexts_store_item(self.context, ix))   
        





    def create_time_series(self, **kargs):
        """ Display time series """

        color = self.config.get('gui_hilight_color','blue')

        max = 0
        for r in self.results:
            if max < r[1]: max = r[1]

        unit = dezeroe(max,1)/200

        for ix, r in enumerate(self.results):

            time = r[0]
            count = r[1]
            length = int(count/unit)
            magn = ""
            for l in range(length):
                magn = f'{magn} ' 
            magn = f'<span background="{color}">{magn}</span>'

            self.tmp_store.append((time, magn, count, ix))





    def create_terms_list(self):
        """ Reload terms store"""
        for ix, r in enumerate(self.results):
            term = scast(r[0], str, '')
            weight = scast(r[1], float, 0)
            count = scast(r[2], int, 0)

            self.tmp_store.append( (term, weight, count, ix) )
        



    def _flags_store_item(self, flag, ix, **kargs):
        id = scast(flag[self.flag.get_index('id')],int,0)
        name = scast(flag[self.flag.get_index('name')],str,'')
        desc = scast(flag[self.flag.get_index('desc')],str,'')
        color = scast(flag[self.flag.get_index('color')],str,'')
        color_cli = scast(flag[self.flag.get_index('color_cli')],str,'')
        return (id, name, desc, color, color_cli, ix)

    def create_flags_list(self):
        """ Reload flags store """
        self.tmp_store = Gtk.ListStore(*self.column_types)
        self.results = []
        i = 0
        for id, f in self.parent.FX.MC.flags.items():
            f = list(f)
            f.insert(0, id)
            self.tmp_store.append( self._flags_store_item(f, i) )
            self.results.append(f)
            i += 1

        self.result_store = self.tmp_store
        self.result_list.set_model(self.result_store)
        self.header.set_markup(f'{_("Flags ")}({len(self.result_store)})')




    def _rules_store_item(self, rule, ix, **kargs):
        self.rule.populate(rule)
        name = scast(self.rule.get('name',''), str, '')
        name = (name[:75] + '...') if len(name) > 75 else name
        string = scast(self.rule.get('string',''), str, '')
        string = (string[:75] + '...') if len(string) > 75 else string
        weight = round(scast(self.rule.get('weight',-1), float, 0), 3)
        
        flag = coalesce(self.rule['flag'],0)
        if flag != 0: color = self.parent.FX.get_flag_color(flag)
        else: color = None

        return (self.rule['id'], name, string, weight, self.rule['case_insensitive'], self.rule['query_type'], self.rule['learned'], 
        self.rule['flag_name'], self.rule['field_name'], self.rule['feed_name'], color, ix)
    


    def create_rules_list(self):
        """ Reload rules store """
        self.tmp_store = Gtk.ListStore(*self.column_types)
        tmp_results = self.parent.FX.QP.show_rules(results=self.parent.FX.qr_sql("""select * from rules where learned <> 1 order by id desc""", all=True) )
        self.results = tmp_results.copy()
        if self.parent.FX.db_error is not None: self.parent.message_q.append((-2, _('DB Error: %a') ,self.parent.FX.db_error))

        for ix, r in enumerate(self.results): self.tmp_store.append( self._rules_store_item(r, ix) )

        self.result_store = self.tmp_store
        self.result_list.set_model(self.result_store)
        self.header.set_markup(f'{_("Rules ")}({len(self.results)})')






    def _tree_apply(self, model, path, iter, ix):
        if model[iter][-1] == ix:
            self.result['title'] = f"""{esc_mu(self.result['title'])}"""
            self.result_store.insert(model.iter_parent(iter), path[-1], self._result_store_item(self.result, ix) )
            self.result_store.remove(iter)
            return True
        return False



    def apply_changes(self, entry, action, **kargs):
        """ Updates local stores for display - needed for large query sets not to clog performance with separate searches 
            Called by parent function on entry edited/deleted/added
        """
        if self.type in (FX_TAB_TERM_NET, FX_TAB_TIME_SERIES, FX_TAB_REL_TIME): return -1
        if self.processing_flag: return 0

        if self.type in (FX_TAB_PLACES, FX_TAB_SEARCH, FX_TAB_SIMILAR, FX_TAB_CONTEXTS, FX_TAB_TREE, FX_TAB_NOTES):
            if entry.get('pubdate_short') is None: 
                pubdate_short = datetime.fromtimestamp(entry.get('pubdate',0))
                entry['pubdate_short'] = datetime.strftime(pubdate_short, '%Y.%m.%d')


        if action == FX_ACTION_EDIT:

            id = entry['id']
            
            if self.type in (FX_TAB_PLACES, FX_TAB_SEARCH, FX_TAB_SIMILAR, FX_TAB_CONTEXTS, FX_TAB_TREE, FX_TAB_NOTES):
                feed = FeedContainer(self.parent.FX, id=entry['feed_id'])
                entry['feed_name'] = feed.name(id=False)
                entry['feed_name_id'] = feed.name(id=True)

            for ix,r in enumerate(self.results):
                if r[0] == id:

                    if self.type in (FX_TAB_PLACES, FX_TAB_SEARCH, FX_TAB_SIMILAR, FX_TAB_TREE, FX_TAB_NOTES):
                        self.result.merge(entry)
                        if self.type in (FX_TAB_SEARCH, FX_TAB_TREE): self.result['snippets'] = scast( slist(self.results[ix], self.result.get_index('snippets'), None), list, []).copy()
                        self.results[ix] = self.result.tuplify()

                    elif self.type == FX_TAB_CONTEXTS:
                        self.context.merge(entry)
                        self.context['snippets'] = scast( slist(self.results[ix], self.context.get_index('snippets'), None), list, []).copy()
                        self.context['context'] = scast(self.results[ix][self.context.get_index('context')], list, []).copy()

                    elif self.type == FX_TAB_RULES:
                        self.rule.merge(entry)
                        entry_tmp = slist( self.parent.FX.QP.show_rules(results=(self.rule.tuplify(),), print=False), 0, ())
                        self.results[ix] = entry_tmp

                    elif self.type == FX_TAB_FLAGS:
                        self.flag.merge(entry)
                        self.result[ix] = self.flag.tuplify()

                    if self.type in (FX_TAB_PLACES, FX_TAB_SEARCH, FX_TAB_SIMILAR, FX_TAB_NOTES):
                        for ixx, rs in enumerate(self.result_store):
                            if rs[1] == id:
                                itr = self.result_store.get_iter(ixx)
                                self.result_store.remove(itr)

                                if self.type == FX_TAB_NOTES:
                                    if coalesce(self.result.get('read'),0) < 0: self.result_store.append( self._notes_store_item(self.result, ix ) )
                                    else: self.result_store.insert(ixx, self._notes_store_item(self.result, ix))
                                else:
                                    if coalesce(self.result.get('read'),0) < 0: self.result_store.append( self._result_store_item(self.result, ix ) )
                                    else: self.result_store.insert(ixx, self._result_store_item(self.result, ix))
                                break
                        break

                    elif self.type == FX_TAB_TREE:
                        self.result_store.foreach(self._tree_apply, ix)
                        break


                    elif self.type == FX_TAB_CONTEXTS:
                        for ixx, rs in enumerate(self.result_store):
                            if rs[-1] == ix:
                                itr = self.result_store.get_iter(ixx)
                                self.result_store.remove(itr)
                                self.result_store.insert(ixx, self._contexts_store_item(self.context, ix))
                                break
                    
                    elif self.type == FX_TAB_RULES:
                        for ixx, rs in enumerate(self.result_store):
                            if rs[0] == id:
                                itr = self.result_store.get_iter(ixx)
                                self.result_store.remove(itr)
                                self.result_store.insert(ixx, self._rules_store_item(entry_tmp, ix))
                                break
                        break

                    elif self.type == FX_TAB_FLAGS:
                        for ixx, rs in enumerate(self.result_store):
                            if rs[0] == id:
                                itr = self.result_store.get_iter(ixx)
                                self.result_store.remove(itr)
                                self.result_store.insert(ixx, self._flags_store_item(self.flag.tuplify(), ix))
                                break
                        break



    
        elif action == FX_ACTION_DELETE and self.type in (FX_TAB_RULES, FX_TAB_FLAGS):
            id = entry['id']
            for ix, r in enumerate(self.results):
                if r[0] == id:
                    self.results[ix] = list(self.results[ix])
                    self.results[ix][0] = None
                    for ixx, rs in enumerate(self.result_store):
                        if rs[0] == id:
                            itr = self.result_store.get_iter(ixx)
                            if self.type == FX_TAB_RULES: self.result_store[itr][-2] = self.config.get('gui_deleted_color','grey')
                            elif self.type == FX_TAB_FLAGS:
                                self.result_store[itr][-3] = self.config.get('gui_deleted_color','grey')
                                self.result_store[itr][0] = None
                            break
                    break


        elif action == FX_ACTION_ADD and self.type in (FX_TAB_PLACES, FX_TAB_SEARCH, FX_TAB_NOTES):

            entry = list(self.parent.FX.qr_sql(f"select {RESULTS_COLUMNS_SQL}\nwhere e.id = ?",(entry['id'],), one=True) )
            if self.parent.FX.db_error is not None: self.parent.message_q.append((-2, self.parent.FX.db_error))
                    
            self.result.populate(entry + [None,None])

            self.results.append(self.result.listify(all=True))

            if self.type == FX_TAB_NOTES: new_result = self._notes_store_item(self.result, len(self.results)-1, new=True)
            else: new_result = self._result_store_item(self.result, len(self.results)-1, new=True) 
            
            self.result_store.insert(0, new_result)


