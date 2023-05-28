# -*- coding: utf-8 -*-
""" GUI classes for FEEDEX """



from feedex_gui_utils import *









class FeedexMainWin(Gtk.Window):
    """ Main window for Feedex """

    def __init__(self, feedex_main_container, **kargs):
    
        #Maint. stuff
        if isinstance(feedex_main_container, FeedexMainDataContainer): self.MC = feedex_main_container
        else: raise FeedexTypeError(_('feedex_main_container should be an instance of FeedexMainDataContainer class!'))

        self.config = kargs.get('config', DEFAULT_CONFIG)
        self.debug = kargs.get('debug')

        self.gui_attrs = validate_gui_attrs( load_json(FEEDEX_GUI_ATTR_CACHE, {}) )

        # Main DB interface - init and check for lock and/or DB errors
        self.FX = Feeder(self.MC, config=self.config, debug=self.debug, ignore_images=self.config.get('ignore_images', False), gui=True, load_icons=True, main_thread=True)

        # Timer related ...
        self.sec_frac_counter = 0
        self.sec_counter = 0
        self.minute_counter = 0

        self.today = 0
        self._time()

        # Default fields for edit and new items
        self.default_search_filters = self.gui_attrs.get('default_search_filters', FEEDEX_GUI_DEFAULT_SEARCH_FIELDS).copy()

        self.new_feed_url = FeedContainer(self.FX)
        self.new_entry = EntryContainer(self.FX)
        self.new_category = FeedContainer(self.FX)
        self.new_feed = FeedContainer(self.FX)
        self.new_rule = RuleContainer(self.FX)
        self.new_rule['additive'] = 1       # Convenience
        self.new_flag = FlagContainer(self.FX)

        self.date_store_added = []

        # Selection references
        self.selection_res = ResultContainer(replace_nones=True)
        self.selection_term = ''
        self.selection_feed = FeedContainerBasic(replace_nones=True)
        self.selection_rule = RuleContainerBasic(result=True, replace_nones=True)
        self.selection_flag = FlagContainerBasic(replace_nones=True)
        self.selection_time_series = {}
        self.selection_text = ''


        if self.FX.locked(timeout=2):
            dialog = YesNoDialog(None, _("Feedex: Database is Locked"), f"<b>{_('Database is Locked! Proceed and unlock?')}</b>", 
                                        subtitle=_("Another instance can be performing operations on Database or Feedex did not close properly last time. Proceed anyway?"))
            dialog.run()
            if dialog.response == 1:
                self.FX.unlock()
                dialog.destroy()
            else:
                dialog.destroy()
                self.FX.close()
                sys.exit(4)
    
        self.FX.unlock()
        if self.FX.db_status != 0:
            dialog = InfoDialog(None, _("Feedex: Database Error!"), gui_msg(self.FX.db_status), subtitle=_("Application could not be started! I am sorry for inconvenience :("))
            dialog.run()
            dialog.destroy()
            self.FX.close()
            sys.exit(2)
        if self.FX.ix_status != 0:
            dialog = InfoDialog(None, _("Feedex: Database Index Error!"), gui_msg(self.FX.db_status), subtitle=_("Application could not be started! I am sorry for inconvenience :("))
            dialog.run()
            dialog.destroy()
            self.FX.close()
            sys.exit(2)


        # Image handling
        self.icons = get_icons(self.FX.MC.feeds, self.FX.MC.icons)

        self.download_errors = [] #Error list to prevent multiple downloads from faulty links

        # Display queues for threading
        self.message_q = [(0, None)]
        self.images_q = []
        self.action_q = []

        # Action flags and Places
        self.flag_fetch = False
        self.flag_feed_update = False
        self.flag_edit_entry = False
        self.flag_db_blocked = False

        self.flag_attrs_blocked = False

        self.curr_place = FX_PLACE_LAST

        # Start threading and main window
        Gdk.threads_init()
        Gtk.Window.__init__(self, title=f"Feedex {FEEDEX_VERSION}")
        self.lock = threading.Lock()

        self.set_border_width(10)
        self.set_icon(self.icons['main'])
        self.set_resizable(True)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_default_size(self.gui_attrs.get('win_width'), self.gui_attrs.get('win_height'))

        GLib.timeout_add(interval=250, function=self._on_timer)




        # Lower status bar
        self.status_bar = f_label('', justify=FX_ATTR_JUS_LEFT, wrap=True, markup=True, selectable=True, ellipsize=FX_ATTR_ELL_END) 
        self.status_spinner = Gtk.Spinner()
        lstatus_box = Gtk.Box()
        lstatus_box.set_orientation(Gtk.Orientation.HORIZONTAL)
        lstatus_box.set_homogeneous(False)
        lstatus_box.pack_start(self.status_spinner, False, False, 10)
        lstatus_box.pack_start(self.status_bar, False, False, 10)

        # Import/Export Menus...
        self.export_menu = Gtk.Menu()
        self.export_menu.append( f_menu_item(1, _('Export Feed data to JSON'), self.export_feeds, icon='application-rss+xml-symbolic'))  
        self.export_menu.append( f_menu_item(1, _('Export Rules to JSON'), self.export_rules, icon='view-list-compact-symbolic'))  
        self.export_menu.append( f_menu_item(1, _('Export Flags to JSON'), self.export_flags, icon='marker-symbolic'))  
        self.export_menu.show_all()

        self.import_menu = Gtk.Menu()
        self.import_menu.append( f_menu_item(1, _('Import Feed data from JSON'), self.import_feeds, icon='application-rss+xml-symbolic'))  
        self.import_menu.append( f_menu_item(1, _('Import Rules data from JSON'), self.import_rules, icon='view-list-compact-symbolic'))  
        self.import_menu.append( f_menu_item(1, _('Import Flags data from JSON'), self.import_flags, icon='marker-symbolic'))  
        self.import_menu.append( f_menu_item(0, 'SEPARATOR', None) )
        self.import_menu.append( f_menu_item(1, _('Import Entries from JSON'), self.import_entries, icon='document-import-symbolic'))  
        self.import_menu.show_all()

        self.db_menu = Gtk.Menu()
        self.db_menu.append( f_menu_item(1, _('Maintenance...'), self.on_maintenance, icon='preferences-system-symbolic', tooltip=_("""Maintenance can improve performance for large databases by doing cleanup and reindexing.
It will also take some time to perform""") ))  
        self.db_menu.append( f_menu_item(0, 'SEPARATOR', None) )
        self.db_menu.append( f_menu_item(1, _('Clear cache'), self.on_clear_cache, icon='edit-clear-symbolic', tooltip=_("""Clear downloaded temporary files with images/thumbnails to reclaim disk space""") ) )
        self.db_menu.append( f_menu_item(0, 'SEPARATOR', None) )
        self.db_menu.append( f_menu_item(1, _('Database statistics'), self.on_show_stats, icon='drive-harddisk-symbolic') )


        # Main Menu
        self.main_menu = Gtk.Menu()
        self.main_menu.append( f_menu_item(1, _('Rules'), self.add_tab, kargs={'type':FX_TAB_RULES}, icon='view-list-compact-symbolic', tooltip=_('Open a new tab showing Saved Rules') ) )
        self.main_menu.append( f_menu_item(1, _('Flags'), self.add_tab, kargs={'type':FX_TAB_FLAGS}, icon='marker-symbolic', tooltip=_('Open a new tab showing Flags') ) )
        self.main_menu.append( f_menu_item(0, 'SEPARATOR', None) )
        self.main_menu.append( f_menu_item(1, _('Preferences'), self.on_prefs, icon='preferences-system-symbolic') )
        self.main_menu.append( f_menu_item(0, 'SEPARATOR', None) )
        self.main_menu.append( f_menu_item(3, _('Export...'), self.export_menu, icon='document-export-symbolic'))  
        self.main_menu.append( f_menu_item(3, _('Import...'), self.import_menu, icon='document-import-symbolic'))  
        self.main_menu.append( f_menu_item(0, 'SEPARATOR', None) )
        self.main_menu.append( f_menu_item(3, _('Database...'), self.db_menu, icon='drive-harddisk-symbolic') )
        self.main_menu.append( f_menu_item(0, 'SEPARATOR', None) )
        self.main_menu.append( f_menu_item(1, _('View log'), self.on_view_log, icon='text-x-generic-symbolic') )
        self.main_menu.append( f_menu_item(0, 'SEPARATOR', None) )
        self.main_menu.append( f_menu_item(1, _('About Feedex...'), self.on_show_about, icon='help-about-symbolic') )
        self.main_menu.show_all()

        # Add menu
        self.add_menu = Gtk.Menu()
        self.add_menu.append( f_menu_item(1, _('Add Channel'), self.on_add_from_url, icon='application-rss+xml-symbolic', tooltip=f'<b>{_("Add Channel")}</b> {_("from URL")}' )  )
        self.add_menu.append( f_menu_item(1, _('Add Entry'), self.on_edit_entry, args=(True,), icon='list-add-symbolic', tooltip=_('Add new Entry') ))  
        self.add_menu.append( f_menu_item(1, _('Add Rule'), self.on_edit_rule, args=(True,), icon='view-list-compact-symbolic', tooltip=_('Add new Rule') ))  

        # Search Menu
        self.search_menu = Gtk.Menu()
        self.search_menu.append( f_menu_item(1, _('Summary'), self.add_tab, kargs={'type': FX_TAB_TREE}, icon='view-filter-symbolic', tooltip=_('Search entries grouping them in a tree summary') ))  
        self.search_menu.append( f_menu_item(1, _('Search'), self.add_tab, kargs={'type': FX_TAB_SEARCH}, icon='edit-find-symbolic', tooltip=_('Search entries') ))  
        self.search_menu.append( f_menu_item(1, _('Search (wide view)'), self.add_tab, kargs={'type': FX_TAB_NOTES}, icon='edit-find-symbolic', tooltip=_('Search entries in extended view') ))  

        self.search_menu.append( f_menu_item(0, 'SEPARATOR', None) )
        self.search_menu.append( f_menu_item(1, _('Trending'), self.add_tab, kargs={'type': FX_TAB_TRENDING}, icon='gtk-network', tooltip=_('Show trending Articles') ))  
        self.search_menu.append( f_menu_item(1, _('Trends'), self.add_tab, kargs={'type': FX_TAB_TRENDS}, icon='emblem-shared-symbolic', tooltip=_('Show most talked about terms for Articles') ))  

        self.search_menu.append( f_menu_item(0, 'SEPARATOR', None) )
        self.search_menu.append( f_menu_item(1, _('Show Contexts for a Term'), self.add_tab, kargs={'type': FX_TAB_CONTEXTS}, icon='view-list-symbolic', tooltip=_('Search for Term Contexts') ))  
        self.search_menu.append( f_menu_item(1, _('Show Time Series for a Term'), self.add_tab, kargs={'type': FX_TAB_TIME_SERIES}, icon='office-calendar-symbolic', tooltip=_('Generate time series plot') ))  
        self.search_menu.append( f_menu_item(0, 'SEPARATOR', None) )
        self.search_menu.append( f_menu_item(1, _('Search for Related Terms'), self.add_tab, kargs={'type': FX_TAB_TERM_NET}, icon='emblem-shared-symbolic', tooltip=_('Search for Related Terms from read/opened entries') ))  
        

        self.search_menu.show_all()
        self.add_menu.show_all()

        # Header bar
        hbar = Gtk.HeaderBar()
        hbar.set_show_close_button(True)
        hbar.props.title = f"Feedex {FEEDEX_VERSION}"
        
        if self.config.get('profile_name') is not None: hbar.props.subtitle = f"{self.config.get('profile_name')}"
        
        self.hbar_button_menu = Gtk.MenuButton()
        self.hbar_button_menu.set_popup(self.main_menu)
        self.hbar_button_menu.set_tooltip_markup(_("""Main Menu"""))
        hbar_button_menu_icon = Gtk.Image.new_from_icon_name('open-menu-symbolic', Gtk.IconSize.BUTTON)
        self.hbar_button_menu.add(hbar_button_menu_icon)         
        self.set_titlebar(hbar)

        self.button_new = Gtk.MenuButton()
        self.button_new.set_popup(self.add_menu)
        self.button_new.set_tooltip_markup(_("Add item ..."))
        button_new_icon = Gtk.Image.new_from_icon_name('list-add-symbolic', Gtk.IconSize.BUTTON)
        self.button_new.add(button_new_icon)
        
        self.button_feeds_download   = f_button(None,'application-rss+xml-symbolic', connect=self.on_load_news_all, tooltip=f'<b>{_("Fetch")}</b> {_("news for all Channels")}')
       
        self.button_search = Gtk.MenuButton()
        self.button_search.set_popup(self.search_menu)
        self.button_search.set_tooltip_markup(_("""Open a new tab for Searches..."""))
        button_search_icon = Gtk.Image.new_from_icon_name('edit-find-symbolic', Gtk.IconSize.BUTTON)
        self.button_search.add(button_search_icon)

    

        # Upper notebook stuff 
        self.rules_tab = -1
        self.flags_tab = -1
        self.curr_upper = None
        
        self.upper_notebook = Gtk.Notebook()
        self.upper_notebook.set_scrollable(True)
        self.upper_notebook.popup_enable()
        self.upper_nb_last_page = 0

        self.upper_notebook.connect('switch-page', self._on_unb_changed)





        # Lower pane (entry preview)
        prev_images_box = Gtk.ScrolledWindow()
        prev_images_box.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self.prev_images = Gtk.Box()
        self.prev_images.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.prev_images.set_homogeneous(False)
        prev_images_box.add_with_viewport(self.prev_images)

        self.preview_label = f_label(None, justify=FX_ATTR_JUS_FILL, xalign=0, selectable=True, wrap=True, markup=True)
        self.preview_label.set_halign(0)
        self.preview_label.connect("populate-popup", self._on_right_click_prev)

        self.preview_box = f_pack_page((prev_images_box, self.preview_label))

        # Feed section
        self.feed_win = FeedexFeedWindow(self)

        # Build layout
        self.Grid = Gtk.Grid()
        self.add(self.Grid)
        self.Grid.set_column_spacing(5)
        self.Grid.set_row_spacing(5)
        self.Grid.set_column_homogeneous(True)
        self.Grid.set_row_homogeneous(True)
        
        main_box = Gtk.VBox(homogeneous=False)
 
        # Set up layout    
        if self.config.get('gui_layout',0) in (0,1):
            self.div_horiz = Gtk.VPaned()
            self.div_vert = Gtk.HPaned()

            if self.config.get('gui_layout',0) == 0:
                self.div_horiz.pack1(self.upper_notebook, resize=True, shrink=True)
                self.div_horiz.pack2(self.preview_box, resize=True, shrink=True)
            else:
                self.div_horiz.pack1(self.preview_box, resize=True, shrink=True)
                self.div_horiz.pack2(self.upper_notebook, resize=True, shrink=True)

            if self.config.get('gui_orientation',0) == 0:
                self.div_vert.pack1(self.feed_win, resize=True, shrink=True)
                self.div_vert.pack2(self.div_horiz, resize=True, shrink=True)
            else:
                self.div_vert.pack1(self.div_horiz, resize=True, shrink=True)
                self.div_vert.pack2(self.feed_win, resize=True, shrink=True)

            main_box.add(self.div_vert)

            self.div_horiz.set_position(self.gui_attrs['div_horiz'])
            self.div_vert.set_position(self.gui_attrs['div_vert'])


        else:
            self.div_vert = Gtk.HPaned()
            self.div_vert2 = Gtk.HPaned()
            

            if self.config.get('gui_orientation',0) == 0:

                self.div_vert2.pack1(self.upper_notebook, resize=True, shrink=True)
                self.div_vert2.pack2(self.preview_box, resize=True, shrink=True)

                self.div_vert.pack1(self.feed_win, resize=True, shrink=True)
                self.div_vert.pack2(self.div_vert2, resize=True, shrink=True)
            
                if self.gui_attrs['div_vert'] >= self.gui_attrs['div_vert2']:
                    self.gui_attrs['div_vert'], self.gui_attrs['div_vert2'] = self.gui_attrs['div_vert2'], self.gui_attrs['div_vert']

            else:

                self.div_vert2.pack1(self.preview_box, resize=True, shrink=True)
                self.div_vert2.pack2(self.upper_notebook, resize=True, shrink=True)
                
                self.div_vert.pack1(self.div_vert2, resize=True, shrink=True)
                self.div_vert.pack2(self.feed_win, resize=True, shrink=True)

                if self.gui_attrs['div_vert2'] >= self.gui_attrs['div_vert']:
                    self.gui_attrs['div_vert'], self.gui_attrs['div_vert2'] = self.gui_attrs['div_vert2'], self.gui_attrs['div_vert']

            main_box.add(self.div_vert)

            self.div_vert.set_position(self.gui_attrs['div_vert'])
            self.div_vert2.set_position(self.gui_attrs['div_vert2'])


        self.Grid.attach(main_box, 1, 1, 31, 18)
        self.Grid.attach(lstatus_box, 1, 19, 31, 1)

        hbar.pack_start(self.button_feeds_download)
        hbar.pack_start(self.button_new)
        hbar.pack_start(self.button_search)
        
        hbar.pack_end(self.hbar_button_menu)

        self.connect("destroy", self._on_close)
        self.connect("key-press-event", self._on_key_press)

        self.add_tab({'type': FX_TAB_PLACES})
        self.curr_upper.query(FX_PLACE_STARTUP, {})

        startup_page = self.config.get('gui_startup_page',0)
        if startup_page == 1:
            self.add_tab({'type': FX_TAB_TREE, 'phrase':FX_PLACE_STARTUP})
            self.curr_upper.query(FX_PLACE_STARTUP,{'group':'category'})
        elif startup_page == 2:
            self.add_tab({'type': FX_TAB_TREE, 'phrase':FX_PLACE_STARTUP})
            self.curr_upper.query(FX_PLACE_STARTUP,{'group':'feed'})
        elif startup_page == 3:
            self.add_tab({'type': FX_TAB_TREE, 'phrase':FX_PLACE_STARTUP})
            self.curr_upper.query(FX_PLACE_STARTUP,{'group':'flag'})
        elif startup_page == 4:
            for i, tb in enumerate(self.gui_attrs.get('tabs',[])):
                if tb.get('type') in (FX_TAB_SIMILAR, FX_TAB_REL_TIME, FX_TAB_RULES, FX_TAB_FLAGS, FX_TAB_TERM_NET,): continue
                self.add_tab({'type': tb.get('type',FX_TAB_SEARCH), 'phrase': tb.get('phrase',''), 'filters': tb.get('filters',{}), 'from_startup':True, 'title':tb.get('title')})

            self.upper_notebook.set_current_page(0)

        self.startup_decor()
 



    def _on_close(self, *args):
        self.FX.close()
        self._save_gui_attrs()

    def _save_gui_attrs(self, *args):
        # Get layout
        self.gui_attrs['div_vert'] = self.div_vert.get_position()
        if hasattr(self, 'div_horiz'): self.gui_attrs['div_horiz'] = self.div_horiz.get_position()
        if hasattr(self, 'div_vert2'): self.gui_attrs['div_vert2'] = self.div_vert2.get_position()

        # Save current tabs if preferred
        if self.config.get('gui_startup_page',0) == 4:
            self.gui_attrs['tabs'] = []
            
            for i in range(self.upper_notebook.get_n_pages()):
                if i == 0: continue
                tb = self.upper_notebook.get_nth_page(i)
                
                if tb.type in (FX_TAB_SIMILAR, FX_TAB_REL_TIME, FX_TAB_RULES, FX_TAB_FLAGS, FX_TAB_TERM_NET): continue

                if hasattr(tb, 'query_entry'): phrase = tb.query_entry.get_text()
                else: phrase = None
                if hasattr(tb, 'search_filters'):
                    tb.get_search_filters()
                    search_filters = tb.search_filters
                else: search_filters = {}
                title = tb.header.get_label()

                tab_dc = {'type':tb.type, 'title':title, 'phrase': phrase, 'filters':search_filters}
                self.gui_attrs['tabs'].append(tab_dc)

        err = save_json(FEEDEX_GUI_ATTR_CACHE, self.gui_attrs)
        if self.debug in (1,7): 
            if err == 0: print('Saved GUI attributes: ', self.gui_attrs)





    def _housekeeping(self): 
        for m in clear_im_cache(self.config.get('gui_clear_cache',30), self.FX.cache_path, debug=self.debug): cli_msg(m)
    def _time(self, *kargs):
        """ Action on changed minute/day (e.g. housekeeping, changed parameters used for date display """
        old_today = self.today
        self.now = date.today()
        self.yesterday = self.now - timedelta(days=1)
        self.year = self.now.strftime("%Y")
        self.year = f'{self.year}.'
        self.today = self.now.strftime("%Y.%m.%d")
        self.yesterday = self.yesterday.strftime("%Y.%m.%d")
        if old_today != self.today:
            t = threading.Thread(target=self._housekeeping, args=())
            t.start()




    def _on_key_press(self, widget, event):
        """ When keyboard is used ... """
        key = event.keyval
        key_name = Gdk.keyval_name(key)
        state = event.state
        ctrl = (state & Gdk.ModifierType.CONTROL_MASK)
        if ctrl and key_name == self.config.get('gui_key_search','s'): self.add_tab({'type': FX_TAB_SEARCH}) 
        elif ctrl and key_name == self.config.get('gui_key_new_entry','n'): self.on_edit_entry(True)
        elif ctrl and key_name == self.config.get('gui_key_new_rule','r'): self.on_edit_rule(True)







    def _rbutton_press(self, widget, event, from_where):
        """ Button press event catcher and menu construction"""
        if event.button == 3:
            menu = None

            # This gets tedious ...
            if from_where in (FX_TAB_RESULTS, FX_TAB_CONTEXTS, FX_TAB_TREE, FX_TAB_NOTES):
                menu = Gtk.Menu()
                
                if not (self.curr_upper.type == FX_TAB_PLACES and self.curr_place == FX_PLACE_TRASH_BIN) and from_where != FX_TAB_TREE:
                    menu.append( f_menu_item(1, _('Add Entry'), self.on_edit_entry, args=(True,), icon='list-add-symbolic') )

                if self.selection_res['id'] is not None:

                    if (not self.flag_edit_entry) and self.selection_res['deleted'] != 1 and not (self.curr_upper.type == FX_TAB_PLACES and self.curr_place == FX_PLACE_TRASH_BIN):

                        mark_menu = Gtk.Menu()
                        mark_menu.append( f_menu_item(1, _('Read (+1)'), self.on_mark_recalc, args=('read',), icon='bookmark-new-symbolic', tooltip=_("Number of reads if counted towards this entry keyword's weight when ranking incoming articles") ) )
                        mark_menu.append( f_menu_item(1, _('Unread'), self.on_mark, args=('unread',), icon='edit-redo-rtl-symbolic', tooltip=_("Unread document does not contriute to ranking rules") ) )
                        mark_menu.append( f_menu_item(1, _('Unimportant'), self.on_mark_recalc, args=('unimp',), icon='edit-redo-rtl-symbolic', tooltip=_("Mark this as unimportant and learn negative rules") ) )

                        menu.append( f_menu_item(3, _('Mark as...'), mark_menu, icon='bookmark-new-symbolic') )

                        flag_menu = Gtk.Menu()
                        for fl, v in self.FX.MC.flags.items():
                            fl_name = esc_mu(v[0])
                            fl_color = v[2]
                            if fl_color in (None, ''): fl_color = self.config.get('gui_default_flag_color','blue')
                            if fl_name in (None, ''): fl_name = f'{_("Flag")} {fl}'
                            flag_menu.append( f_menu_item(1, fl_name, self.on_mark, args=(fl,), color=fl_color, icon='marker-symbolic') )
                        flag_menu.append( f_menu_item(1, _('Unflag Entry'), self.on_mark, args=('unflag',), icon='edit-redo-rtl-symbolic', tooltip=_("Remove Flags from Entry") ) )

                        menu.append( f_menu_item(3, _('Flag...'), flag_menu, icon='marker-symbolic', tooltip=f"""{_("Flag is a user's marker/bookmark for a given article independent of ranking")}\n<i>{_("You can setup different flag colors in Preferences")}</i>""") )
                        menu.append( f_menu_item(1, _('Edit Entry'), self.on_edit_entry, args=(False,), icon='edit-symbolic') )
                        

                    if self.selection_res['deleted'] == 1: 
                        menu.append( f_menu_item(1, _('Restore'), self.on_restore_entry, icon='edit-redo-rtl-symbolic') )
                        menu.append( f_menu_item(1, _('Delete permanently'), self.on_del_entry, icon='edit-delete-symbolic') )
                    else: menu.append( f_menu_item(1, _('Delete'), self.on_del_entry, icon='edit-delete-symbolic') )
                           
                    similar_menu = Gtk.Menu()
                    similar_menu.append( f_menu_item(1, _('Last update'), self.on_from_entry, args=('last',FX_TAB_SIMILAR) ) )
                    similar_menu.append( f_menu_item(1, _('Today'), self.on_from_entry, args=('today',FX_TAB_SIMILAR) ) )
                    similar_menu.append( f_menu_item(1, _('Last Week'), self.on_from_entry, args=('last_week',FX_TAB_SIMILAR) ) )
                    similar_menu.append( f_menu_item(1, _('Last Month'), self.on_from_entry, args=('last_month',FX_TAB_SIMILAR) ) )
                    similar_menu.append( f_menu_item(1, _('Last Quarter'), self.on_from_entry, args=('last_quarter',FX_TAB_SIMILAR) ) )
                    similar_menu.append( f_menu_item(1, _('Last Year'), self.on_from_entry, args=('last_year',FX_TAB_SIMILAR) ) )
                    similar_menu.append( f_menu_item(1, _('Select Range...'), self.on_from_entry, args=('range',FX_TAB_SIMILAR) ) )
                        
                    menu.append( f_menu_item(0, 'SEPARATOR', None) )

                    search_menu = Gtk.Menu()

                    search_menu.append( f_menu_item(3, _('Find Similar Entries'), similar_menu, icon='edit-copy-symbolic', tooltip=_("Find Entries similar to the one selected") ) )
                    search_menu.append( f_menu_item(1, _('Show Time Relevance'), self.add_tab, kargs={'type': FX_TAB_REL_TIME}, icon='office-calendar-symbolic', tooltip=_("Search for this Entry's Keywords in time") ) )

                    if from_where not in (FX_TAB_NOTES,):
                        author_menu = Gtk.Menu()
                        author_menu.append( f_menu_item(1, _('Articles'), self.add_tab, kargs={'type': FX_TAB_SEARCH, 'author': True}, icon='edit-find-symbolic', tooltip=_("Search for other documents by this Author") ) )
                        author_menu.append( f_menu_item(1, _('Activity in Time'), self.add_tab, kargs={'type': FX_TAB_TIME_SERIES, 'author': True}, icon='office-calendar-symbolic', tooltip=_("Search for other documents by this Author in Time Series") ) )
                        author_menu.append( f_menu_item(0, 'SEPARATOR', None) )
                        author_menu.append( f_menu_item(1, _('Search WWW'), self._on_www_search_auth, icon='www-symbolic', tooltip=_("Search WWW for this Author's info") ) )
                    
                        search_menu.append( f_menu_item(3, _('Other by this Author...'), author_menu, icon='emblem-shared-symbolic', tooltip=_("Search for this Author") ) )

                    menu.append( f_menu_item(3, _('Search...'), search_menu, icon='emblem-shared-symbolic') ) 
                    menu.append( f_menu_item(0, 'SEPARATOR', None) )
                    
                    detail_menu = Gtk.Menu()
                    detail_menu.append( f_menu_item(1, _('Show Keywords for Entry'), self.on_show_keywords, icon='zoom-in-symbolic') )
                    detail_menu.append( f_menu_item(1, _('Show Matched Rules for Entry'), self.on_show_rules_for_entry, icon='zoom-in-symbolic') )
                    if self.debug is not None: detail_menu.append( f_menu_item(1, _('Details...'), self.on_show_detailed, icon='zoom-in-symbolic', tooltip=_("Show all entry's technical data") ) )
                    menu.append( f_menu_item(3, _('Details...'), detail_menu, icon='zoom-in-symbolic') ) 


                if from_where != FX_TAB_TREE:
                    menu.append( f_menu_item(0, 'SEPARATOR', None) )
                    menu.append( f_menu_item(1, _('Save results to CSV'), self.export_results_csv, icon='x-office-spreadsheet-symbolic', tooltip=_('Save results from current tab') ))  
                    if from_where == FX_TAB_RESULTS:
                        menu.append( f_menu_item(1, _('Export results to JSON'), self.export_results_json, icon='document-export-symbolic', tooltip=_('Export results from current tab') ))  


                if self.curr_upper.type in (FX_TAB_SEARCH, FX_TAB_CONTEXTS, FX_TAB_TREE, FX_TAB_NOTES):
                    menu.append( f_menu_item(0, 'SEPARATOR', None) )
                    menu.append( f_menu_item(1, _('Clear Search History'), self.on_clear_history, icon='edit-clear-symbolic') )
                
                if self.curr_upper.type == FX_TAB_PLACES and self.curr_place == FX_PLACE_TRASH_BIN: menu.append( f_menu_item(1, _('Empty Trash'), self.on_empty_trash, icon='edit-delete-symbolic') ) 
                menu.append( f_menu_item(0, 'SEPARATOR', None) )
                menu.append( f_menu_item(1, _('Save layout'), self.curr_upper.save_layout, icon='document-page-setup-symbolic', tooltip=_('Save column layout and sizing for current tab.\nIt will be used as default in the future') ) )
                if self.curr_upper.type in (FX_TAB_SEARCH, FX_TAB_CONTEXTS, FX_TAB_TREE, FX_TAB_NOTES):
                    menu.append( f_menu_item(1, _('Save filters'), self.curr_upper.save_filters, icon='view-column-symbolic', tooltip=_('Save current search filters as defaults for future') ) )

                if self.curr_upper.type == FX_TAB_TREE:
                    menu.append( f_menu_item(0, 'SEPARATOR', None) )
                    menu.append( f_menu_item(1, _('Expand all'), self.curr_upper._expand_all, icon='list-add-symbolic') )
                    menu.append( f_menu_item(1, _('Collapse all'), self.curr_upper._collapse_all, icon='list-remove-symbolic') )




            elif from_where == FX_TAB_RULES:
                menu = Gtk.Menu()
                menu.append( f_menu_item(1, _('Add Rule'), self.on_edit_rule, args=(True,), icon='list-add-symbolic') )
                if self.selection_rule['id'] is not None:
                    menu.append( f_menu_item(1, _('Edit Rule'), self.on_edit_rule, args=(False,), icon='edit-symbolic') )
                    menu.append( f_menu_item(1, _('Delete Rule'), self.on_del_rule, icon='edit-delete-symbolic') )
                    menu.append( f_menu_item(0, 'SEPARATOR', None) )
                    menu.append( f_menu_item(1, _('Search for this Rule'), self.add_tab, kargs={'type': FX_TAB_SEARCH, 'phrase':self.selection_rule['string'], 'qtype':self.selection_rule['type'], 'case_ins':self.selection_rule['case_insensitive']}, icon='edit-find-symbolic'))  
                    menu.append( f_menu_item(1, _('Show this Term\'s Contexts'), self.add_tab, kargs={'type': FX_TAB_CONTEXTS, 'phrase':self.selection_rule['string'], 'qtype':self.selection_rule['type'], 'case_ins':self.selection_rule['case_insensitive']}, icon='view-list-symbolic'))  
                    menu.append( f_menu_item(1, _('Show Terms related to this Term'), self.add_tab, kargs={'type': FX_TAB_TERM_NET, 'phrase':self.selection_rule['string']}, icon='emblem-shared-symbolic'))  
                    menu.append( f_menu_item(1, _('Show Time Series for this Term'), self.add_tab,kargs={'type': FX_TAB_TIME_SERIES, 'phrase':self.selection_rule['string'], 'qtype':self.selection_rule['type'], 'case_ins':self.selection_rule['case_insensitive']}, icon='office-calendar-symbolic'))  
                    menu.append( f_menu_item(0, 'SEPARATOR', None) )

                menu.append( f_menu_item(1, _('Clear Search History'), self.on_clear_history, icon='edit-clear-symbolic') )
                menu.append( f_menu_item(1, _('Show Learned Rules'), self.show_learned_rules, icon='zoom-in-symbolic', tooltip=_('Display rules learned from User\'s habits along with weights') ) )
                menu.append( f_menu_item(1, _('Save layout'), self.curr_upper.save_layout, icon='view-column-symbolic', tooltip=_('Save column layout and sizing for current tab.\nIt will be used as default in the future') ) )

            elif from_where  == FX_TAB_TERM_NET:            
                menu = Gtk.Menu()
                if self.selection_term not in (None,''):
                    menu.append( f_menu_item(1, _('Search for this Term'), self.add_tab, kargs={'type': FX_TAB_SEARCH, 'phrase':self.selection_term}, icon='edit-find-symbolic'))  
                    menu.append( f_menu_item(1, _('Show this Term\'s Contexts'), self.add_tab, kargs={'type': FX_TAB_CONTEXTS, 'phrase':self.selection_term}, icon='view-list-symbolic'))  
                    menu.append( f_menu_item(1, _('Show Terms related to this Term'), self.add_tab, kargs={'type': FX_TAB_TERM_NET, 'phrase':self.selection_term}, icon='emblem-shared-symbolic'))  
                    menu.append( f_menu_item(1, _('Show Time Series for this Term'), self.add_tab,kargs={'type': FX_TAB_TIME_SERIES, 'phrase':self.selection_term}, icon='office-calendar-symbolic'))  
                    menu.append( f_menu_item(0, 'SEPARATOR', None) )
                
                menu.append( f_menu_item(1, _('Save results to CSV'), self.export_results_csv, icon='x-office-spreadsheet-symbolic', tooltip=_('Save results from current tab') ))  
                menu.append( f_menu_item(0, 'SEPARATOR', None) )
                menu.append( f_menu_item(1, _('Clear Search History'), self.on_clear_history, icon='edit-clear-symbolic') )
                menu.append( f_menu_item(0, 'SEPARATOR', None) )
                menu.append( f_menu_item(1, _('Save layout'), self.curr_upper.save_layout, icon='view-column-symbolic', tooltip=_('Save column layout and sizing for current tab.\nIt will be used as default in the future') ) )

            elif from_where  in (FX_TAB_TIME_SERIES, FX_TAB_REL_TIME):            
                menu = Gtk.Menu()
                if self.selection_time_series not in (None, {}):
                    menu.append( f_menu_item(1, _('Search this Time Range'), self.add_tab, kargs={'type': FX_TAB_SEARCH, 'date_range':True, 'phrase':self.curr_upper.query_entry.get_text()}, icon='edit-find-symbolic'))  
                    menu.append( f_menu_item(0, 'SEPARATOR', None) )  
                menu.append( f_menu_item(1, _('Save results to CSV'), self.export_results_csv, icon='x-office-spreadsheet-symbolic', tooltip=_('Save results from current tab') ))  
                menu.append( f_menu_item(0, 'SEPARATOR', None) )
                menu.append( f_menu_item(1, _('Clear Search History'), self.on_clear_history, icon='edit-clear-symbolic') )
                menu.append( f_menu_item(0, 'SEPARATOR', None) )
                menu.append( f_menu_item(1, _('Save layout'), self.curr_upper.save_layout, icon='view-column-symbolic', tooltip=_('Save column layout and sizing for current tab.\nIt will be used as default in the future') ) )
                if from_where == FX_TAB_TIME_SERIES:
                    menu.append( f_menu_item(1, _('Save filters'), self.curr_upper.save_filters, icon='gtk-find-and-replace', tooltip=_('Save current search filters as defaults for future') ) )


            elif from_where == FX_TAB_FLAGS:
                menu = Gtk.Menu()
                menu.append( f_menu_item(1, _('Add Flag'), self.on_edit_flag, args=(True,), icon='list-add-symbolic') )
                if self.selection_flag['id'] is not None:
                    menu.append( f_menu_item(1, _('Edit Flag'), self.on_edit_flag, args=(False,), icon='edit-symbolic') )
                    menu.append( f_menu_item(1, _('Delete Flag'), self.on_del_flag, icon='edit-delete-symbolic') )
                    menu.append( f_menu_item(0, 'SEPARATOR', None) )
                    menu.append( f_menu_item(1, _('Search for this Flag'), self.add_tab, kargs={'type': FX_TAB_SEARCH, 'flag':self.selection_flag['id']}, icon='edit-find-symbolic'))  
                    menu.append( f_menu_item(1, _('Time Series search for this Flag'), self.add_tab,kargs={'type': FX_TAB_TIME_SERIES, 'flag':self.selection_flag['id']}, icon='office-calendar-symbolic'))  
                    menu.append( f_menu_item(0, 'SEPARATOR', None) )

                menu.append( f_menu_item(1, _('Clear Search History'), self.on_clear_history, icon='edit-clear-symbolic') )
                menu.append( f_menu_item(1, _('Save layout'), self.curr_upper.save_layout, icon='view-column-symbolic', tooltip=_('Save column layout and sizing for current tab.\nIt will be used as default in the future') ) )


            elif from_where == FX_TAB_FEEDS:
                menu = Gtk.Menu()

                if self.selection_feed.get('id',0) > 0 and self.selection_feed['deleted'] != 1:
                    menu.append( f_menu_item(1, _('Show from newest...'), self.add_tab, kargs={'type': FX_TAB_SEARCH, 'from_feed':True}, icon='edit-find-symbolic', tooltip=_("Show articles for this Channel or Category sorted from newest") ) )
                    menu.append( f_menu_item(1, _('Show from newest (wide view)...'), self.add_tab, kargs={'type': FX_TAB_NOTES, 'from_feed':True}, icon='edit-find-symbolic', tooltip=_("Show articles sorted from newest in an extended view") ) )

                if not self.flag_feed_update:
                    menu.append( f_menu_item(1, _('Add Channel'), self.on_feed_cat, args=('new_channel',), icon='list-add-symbolic') )
                    menu.append( f_menu_item(1, _('Add Category'), self.on_feed_cat, args=('new_category',), icon='folder-new-symbolic') )


                if self.selection_feed.get('id',0) > 0:
                    menu.append( f_menu_item(0, 'SEPARATOR', None) )
                    if self.selection_feed['is_category'] == 1:
                        menu.append( f_menu_item(1, _('Move Category...'), self.feed_win.copy_feed, icon='edit-cut-symbolic') ) 
                    else: menu.append( f_menu_item(1, _('Move Feed...'), self.feed_win.copy_feed, icon='edit-cut-symbolic') ) 
                    
                    if self.feed_win.copy_selected.get('id') is not None and not self.flag_fetch and not self.flag_feed_update:
                        if self.feed_win.copy_selected['is_category'] == 1:
                            if self.selection_feed['is_category'] == 1:
                                menu.append( f_menu_item(1, f'{_("Insert")} {esc_mu(self.feed_win.copy_selected.name())} {_("here ...")}', self.feed_win.insert_feed, icon='edit-paste-symbolic') )
                        else:
                            if self.selection_feed['is_category'] == 1:
                                menu.append( f_menu_item(1, f'{_("Assign")} {esc_mu(self.feed_win.copy_selected.name())} {_("here ...")}', self.feed_win.insert_feed, icon='edit-paste-symbolic') ) 
                            else:
                                menu.append( f_menu_item(1, f'{_("Insert")} {esc_mu(self.feed_win.copy_selected.name())} {_("here ...")}', self.feed_win.insert_feed, icon='edit-paste-symbolic') )
                    menu.append( f_menu_item(0, 'SEPARATOR', None) )
                    if self.selection_feed['deleted'] == 1:
                        menu.append( f_menu_item(1, _('Restore...'), self.on_restore_feed, icon='edit-redo-rtl-symbolic') )
                        menu.append( f_menu_item(1, _('Remove Permanently'), self.on_del_feed, icon='edit-delete-symbolic') )


                    elif self.selection_feed['is_category'] != 1:
                        
                        menu.append( f_menu_item(1, _('Go to Channel\'s Homepage'), self.on_go_home, icon='user-home-symbolic') )
                        
                        if not self.flag_fetch:
                            menu.append( f_menu_item(0, 'SEPARATOR', None) )
                            menu.append( f_menu_item(1, _('Fetch from selected Channel'), self.on_load_news_feed, icon='application-rss+xml-symbolic') )
                            menu.append( f_menu_item(1, _('Update metadata for Channel'), self.on_update_feed, icon='preferences-system-symbolic') )
                            menu.append( f_menu_item(1, _('Update metadata for All Channels'), self.on_update_feed_all, icon='preferences-system-symbolic') )
                            menu.append( f_menu_item(0, 'SEPARATOR', None) )

                        menu.append( f_menu_item(1, _('Edit Channel'), self.on_feed_cat, args=('edit',), icon='edit-symbolic') )
                        menu.append( f_menu_item(1, _('Mark Channel as healthy'), self.on_mark_healthy, icon='go-jump-rtl-symbolic', tooltip=_("This will nullify error count for this Channel so it will not be ommited on next fetching") ) )
                        menu.append( f_menu_item(0, 'SEPARATOR', None) )
                        menu.append( f_menu_item(1, _('Remove Channel'), self.on_del_feed, icon='edit-delete-symbolic') )
                        if self.debug is not None: menu.append( f_menu_item(1, _('Technical details...'), self.on_feed_details, icon='zoom-in-symbolic', tooltip=_("Show all technical information about this Channel") ) )

                    elif self.selection_feed['is_category'] == 1:
                        menu.append( f_menu_item(1, _('Edit Category'), self.on_feed_cat, args=('edit',), icon='edit-symbolic') )
                        menu.append( f_menu_item(1, _('Remove Category'), self.on_del_feed, icon='edit-delete-symbolic') )
                    

                elif self.feed_win.selected_feed_id < 0:
                    if self.feed_win.selected_place == FX_PLACE_TRASH_BIN: 
                        menu.append( f_menu_item(1, _('Empty Trash'), self.on_empty_trash, icon='edit-delete-symbolic') )




            if menu is not None:
                menu.show_all()
                menu.popup(None, None, None, None, event.button, event.time)





    def _on_right_click_prev(self, widget, menu, *args, **kargs):
        """ Add some option to the popup menu of preview box """
        selection = widget.get_selection_bounds()
        
        summ_menu = Gtk.Menu()
        summ_menu.append( f_menu_item(1, _('90%'), self._on_summarize, kargs={'level':90} ) )
        summ_menu.append( f_menu_item(1, _('80%'), self._on_summarize, kargs={'level':80} ) )
        summ_menu.append( f_menu_item(1, _('70%'), self._on_summarize, kargs={'level':70} ) )
        summ_menu.append( f_menu_item(1, _('60%'), self._on_summarize, kargs={'level':60} ) )
        summ_menu.append( f_menu_item(1, _('50%'), self._on_summarize, kargs={'level':50} ) )
        summ_menu.append( f_menu_item(1, _('40%'), self._on_summarize, kargs={'level':40} ) )
        summ_menu.append( f_menu_item(1, _('30%'), self._on_summarize, kargs={'level':30} ) )
        summ_menu.append( f_menu_item(1, _('20%'), self._on_summarize, kargs={'level':20} ) )
        summ_menu.append( f_menu_item(1, _('10%'), self._on_summarize, kargs={'level':10} ) )
        menu.append( f_menu_item(0, 'SEPARATOR', None) )
        menu.append( f_menu_item(3, _('Summarize...'), summ_menu, icon='filter-symbolic')) 
        
        if not (selection == () or len(selection) != 3):
            text = widget.get_text()
            self.selection_text = text[selection[1]:selection[2]]
            self.selection_text = scast( self.selection_text, str, '')
            if self.debug in (1,7): print(f'Selected text: {self.selection_text}')
            if self.selection_text != '':
                menu.append( f_menu_item(0, 'SEPARATOR', None) )
                menu.append( f_menu_item(1, _('Search for this Term'), self.add_tab, kargs={'type': FX_TAB_SEARCH, 'phrase':self.selection_text}, icon='edit-find-symbolic'))  
                menu.append( f_menu_item(1, _('Show this Term\'s Contexts'), self.add_tab, kargs={'type': FX_TAB_CONTEXTS, 'phrase':self.selection_text}, icon='view-list-symbolic'))  
                menu.append( f_menu_item(1, _('Show Terms related to this Term'), self.add_tab, kargs={'type': FX_TAB_TERM_NET, 'phrase':self.selection_text}, icon='emblem-shared-symbolic'))  
                menu.append( f_menu_item(1, _('Show Time Series for this Term'), self.add_tab,kargs={'type': FX_TAB_TIME_SERIES, 'phrase':self.selection_text}, icon='office-calendar-symbolic'))  
                menu.append( f_menu_item(0, 'SEPARATOR', None) )
                menu.append( f_menu_item(1, _('Search WWW'), self._on_www_search_sel, icon='www-symbolic', tooltip=_("Search WWW for selected text") ) )
                menu.append( f_menu_item(0, 'SEPARATOR', None) )
                menu.append( f_menu_item(1, _('Add as Rule'), self._on_add_as_rule, icon='view-list-compact-symbolic'))  
        menu.show_all()





    def _on_summarize(self, *args, **kargs):
        level = args[-1].get('level',0)
        summarized_text = self.FX.LP.summarize_entry(self.selection_res, level, separator=" (...) \n\n (...) ")
        if self.debug in (1,): print(f'Summarize level: {level}')
        if type(summarized_text) is str and summarized_text.strip() != '':
            self.selection_res['text'] = ''
            self.selection_res['desc'] = summarized_text
            self.on_changed_selection()



    def _on_www_search_auth(self, *args, **kargs): ext_open(self.config, 'search_engine', self.selection_res.get('author',None))
    def _on_www_search_sel(self, *args, **kargs): ext_open(self.config, 'search_engine', scast(self.selection_text, str, ''))

    def _on_add_as_rule(self, *args):
        """ Adds selected phrase to rules (dialog)"""
        self.new_rule['string'] = self.selection_text
        self.new_rule['name'] = self.selection_text
        self.on_edit_rule(True)


    def _on_timer(self, *kargs):
        """ Check for status updates from threads on time interval  """
        self.sec_frac_counter += 1
        if self.sec_frac_counter > 4:
            self.sec_frac_counter = 0
            self.sec_counter += 1

        # Fetch news if specified in config
        if self.sec_counter > 60:
            self.sec_counter = 0
            self.minute_counter += 1
            self._time()
            if self.config.get('gui_fetch_periodically', False):
                self.on_load_news_background()

        # Show queued messages from threads
        if len(self.message_q) > 0:
            m = self.message_q[0]
            self.update_status(slist(m,0,3), slist(m,1,-1))
            del self.message_q[0]

 
        # Apply changes on tabs 
        if len(self.action_q) > 0:
            m = self.action_q[0]

            if type(m) in (tuple, list):
                action = slist( m, 1, None)
                uid = slist(m, 0, None)
            else: 
                action = m
                uid = None

            if action == FX_ACTION_FINISHED_SEARCH:
                for i in range(self.upper_notebook.get_n_pages()):
                    tb = self.upper_notebook.get_nth_page(i)
                    if tb is None: continue
                    if tb.uid == uid:
                        tb.finish_search()
                        self.upper_notebook.set_menu_label_text( tb, tb.header.get_text() )

                        if tb.uid == self.curr_upper.uid:
                            if tb.type in (FX_TAB_PLACES, FX_TAB_SEARCH, FX_TAB_CONTEXTS, FX_TAB_SIMILAR, FX_TAB_TREE, FX_TAB_NOTES, FX_TAB_TRENDING,):
                                self.feed_win.feed_aggr = self.curr_upper.feed_aggr
                            self.feed_win.reload_feeds()
                        break

            elif action == FX_ACTION_RELOAD_FEEDS: 
                self.feed_win.reload_feeds()

            elif action == FX_ACTION_RELOAD_FEEDS_DB:
                self.feed_win.reload_feeds(load=True)                

            elif action == FX_ACTION_BLOCK_FETCH:
                self.button_feeds_download.set_sensitive(False)
                self.button_new.set_sensitive(False)

            elif action == FX_ACTION_UNBLOCK_FETCH:
                self.button_feeds_download.set_sensitive(True)
                self.button_new.set_sensitive(True)

            elif action == FX_ACTION_BLOCK_DB:
                self.button_feeds_download.set_sensitive(False)
                self.button_new.set_sensitive(False)
                self.button_search.set_sensitive(False)
                self.hbar_button_menu.set_sensitive(False)
                self.upper_notebook.set_sensitive(False)
                self.feed_win.set_sensitive(False)
                self.preview_box.set_sensitive(False)

            elif action == FX_ACTION_UNBLOCK_DB:
                self.button_feeds_download.set_sensitive(True)
                self.button_new.set_sensitive(True)
                self.button_search.set_sensitive(True)
                self.hbar_button_menu.set_sensitive(True)
                self.upper_notebook.set_sensitive(True)
                self.feed_win.set_sensitive(True)
                self.preview_box.set_sensitive(True)

            else:
                self.curr_upper.apply_changes(uid, action)

            del self.action_q[0]

                
        # Show images processed by threads
        if len(self.images_q) > 0:
            if self.selection_res['id'] == self.images_q[0]:
                self.handle_images(self.selection_res.get('id', None), f"""{self.selection_res.get('images','')}\n{self.links}""")
            del self.images_q[0]

        return True






    def on_from_entry(self, *args):
        """ Open a new tab to find entries similar to selected """
        time = args[-2]
        type = args[-1]
        filters = {}

        if time == 'range':

                dialog = CalendarDialog(self)
                dialog.run()
                if dialog.response == 1:
                    if self.debug in (1,7): print(dialog.results)
                    filters = {'date_from': dialog.result['date_from'], 'date_to': dialog.result['date_to']}
                    dialog.destroy()
                else:
                    dialog.destroy()
                    return 0

        else: filters[time] = True

        self.add_tab({'type': type, 'filters': filters})









    def add_tab(self, *args):
        """ Deal with adding tabs and requesting initial queries if required. Accepts args as a dictionary """
        kargs = args[-1]

        type = kargs.get('type', FX_TAB_SEARCH)
        
        phrase = kargs.get('phrase')
        qtype = kargs.get('qtype')
        if qtype in (3,4,5): qtype = 0
        flag = kargs.get('flag',None)

        case_ins = kargs.get('case_ins')
        if case_ins == 1: case = 'case_ins'
        else: case = 'case_sens'
        
        date_range = kargs.get('date_range', False)
        from_feed = kargs.get('from_feed',False)
        author = kargs.get('author',False)
        if author: phrase = self.selection_res['author']

        from_startup = kargs.get('from_startup',False)
        filters = kargs.get('filters',None)

        tab = FeedexTab(self, type=type, title=kargs.get('title',''), results=kargs.get('results',[]))
        if from_startup: tab.on_restore(filters=filters)

        # Keep track of which tab contains rules
        if type == FX_TAB_RULES and self.rules_tab != -1:
            self._show_upn_page(self.rules_tab)
            return 0
        elif type == FX_TAB_RULES and self.rules_tab == -1:
            self.rules_tab = tab.uid

        # ... and Flags ...
        if type == FX_TAB_FLAGS and self.flags_tab != -1:
            self._show_upn_page(self.flags_tab)
            return 0
        elif type == FX_TAB_FLAGS and self.flags_tab == -1:
            self.flags_tab = tab.uid


        self.upper_notebook.append_page(tab, tab.header_box)
        self.upper_notebook.set_tab_reorderable(tab, True) 
        
        tab.header_box.show_all()

        # Quick launch a query if launched from a menu
        if type == FX_TAB_NOTES and from_feed and not from_startup:
            f_set_combo(tab.cat_combo, self.selection_feed['id'])
            f_set_combo(tab.qtime_combo, 'last_month')
            tab.query('', {'feed_or_cat':self.selection_feed['id'], 'deleted':False} )

        if type == FX_TAB_SEARCH and from_feed and not from_startup: 
            f_set_combo(tab.cat_combo, self.selection_feed['id'])
            f_set_combo(tab.qtime_combo, 'last_month')
            tab.query('', {'feed_or_cat':self.selection_feed['id'], 'deleted':False } )
        
        elif type == FX_TAB_RULES: tab.create_rules_list()
        elif type == FX_TAB_FLAGS: tab.create_flags_list()
        elif type == FX_TAB_TREE and not from_startup:  
            tab.qtime_combo.set_active(0)
            tab.group_combo.set_active(0)
            tab.sort_combo.set_active(0)
            if phrase != FX_PLACE_STARTUP: tab.query('', kargs.get('filters',{'last':True, 'deleted':False, 'group': 'category', 'sort':'+importance'}))
        elif type == FX_TAB_SIMILAR and not from_startup: 
            tab.top_entry.populate(self.selection_res.tuplify())
            tab.query('', kargs.get('filters',{}))
        elif type == FX_TAB_REL_TIME: tab.top_entry.populate(self.selection_res.tuplify())

        elif type in (FX_TAB_SEARCH, FX_TAB_TIME_SERIES) and author:
            f_set_combo(tab.qtype_combo, 1)
            f_set_combo(tab.case_combo, 'case_ins')
            f_set_combo(tab.qfield_combo, 'author')


        # Fill up search phrase and filters if provided
        if phrase is not None and type in (FX_TAB_SEARCH, FX_TAB_CONTEXTS, FX_TAB_TERM_NET, FX_TAB_TIME_SERIES, FX_TAB_NOTES): 
            tab.query_entry.set_text(scast(phrase, str, ''))
        if qtype is not None and type in (FX_TAB_SEARCH, FX_TAB_CONTEXTS, FX_TAB_TERM_NET, FX_TAB_TIME_SERIES, FX_TAB_NOTES): 
            f_set_combo( tab.qtype_combo, qtype )
        if case_ins is not None and type in (FX_TAB_SEARCH, FX_TAB_CONTEXTS, FX_TAB_TERM_NET, FX_TAB_TIME_SERIES, FX_TAB_NOTES): 
            f_set_combo( tab.case_combo, case )
        if flag is not None and type in (FX_TAB_SEARCH, FX_TAB_CONTEXTS, FX_TAB_TERM_NET, FX_TAB_TIME_SERIES, FX_TAB_NOTES): 
            f_set_combo( tab.flag_combo, scast(flag, str, None) )

        # Add date range to filters if provided
        if date_range and type in (FX_TAB_SEARCH, FX_TAB_CONTEXTS, FX_TAB_TERM_NET, FX_TAB_TIME_SERIES, FX_TAB_NOTES):
            start_date = self.selection_time_series.get('start_date')
            group = self.selection_time_series.get('group')

            if group in ('hourly', 'daily', 'monthly'):
                dmonth = relativedelta(months=+1)
                dday = relativedelta(days=+1)
                dhour = relativedelta(hours=+1)
                dsecond_minus = relativedelta(seconds=-1)

                end_date = None
                if group == 'hourly': 
                    start_date = datetime.strptime(start_date, "%Y-%m-%d %H:%M")
                    end_date = start_date + dhour + dsecond_minus
                elif group == 'daily': 
                    start_date = datetime.strptime(start_date, "%Y-%m-%d")
                    end_date = start_date + dday + dsecond_minus
                elif group == 'monthly': 
                    start_date = datetime.strptime(start_date, "%Y-%m")
                    end_date = start_date + dmonth + dsecond_minus
            

                date_str = f'{start_date.strftime("%Y/%m/%d %H:%M:%S")} --- {end_date.strftime("%Y/%m/%d %H:%M:%S")}'
                tab.add_date_str_to_combo(date_str)
                f_set_combo(tab.qtime_combo, f'_{date_str}')


        self.upper_notebook.show_all()
        self.curr_upper = tab

        self._show_upn_page(tab.uid)

        if type in (FX_TAB_SEARCH, FX_TAB_CONTEXTS, FX_TAB_TERM_NET, FX_TAB_TIME_SERIES, FX_TAB_NOTES): tab.query_entry.grab_focus()

        self.upper_notebook.set_menu_label_text( tab, tab.header.get_text() )



    def _get_upn_page(self, uid):
        for i in range(self.upper_notebook.get_n_pages()):
            tb = self.upper_notebook.get_nth_page(i)
            if tb is None: return -1
            if tb.uid == uid: return i

    def _get_upn_page_obj(self, uid):
        i = self._get_upn_page(uid)
        return self.upper_notebook.get_nth_page(i)
    
    def _get_upn_page_uid(self, i):
        tb = self.upper_notebook.get_nth_page(i)
        if tb is None: return -1
        return tb.uid

    def _show_upn_page(self, uid):
        i = self._get_upn_page(uid)
        if i >= 0: self.upper_notebook.set_current_page(i)



    def remove_tab(self, uid, type):
        """ Deal with removing tabs and cleaning up """
        if type == FX_TAB_PLACES: return -1
        elif type == FX_TAB_RULES: self.rules_tab = -1
        elif type == FX_TAB_FLAGS: self.flags_tab = -1

        i = self._get_upn_page(uid)
        if i >= 0: self.upper_notebook.remove_page(i) 




    def _reload_rules(self):
        """ Reload rules if rules tab is open """
        if self.rules_tab != -1: 
            i = self._get_upn_page(self.rules_tab)
            tab = self.upper_notebook.get_nth_page(i)
            tab.create_rules_list()

    def _reload_flags(self):
        """ Reload flags if relevant tab is open """
        if self.flags_tab != -1: 
            i = self._get_upn_page(self.flags_tab)
            tab = self.upper_notebook.get_nth_page(i)
            tab.create_rules_list()



    def update_status(self, *args):
        """ Updates lower status bar and busy animation for actions """
        # Parse message tuple and construct text
        msg = args[-1]
        # Handle spinner
        spin = args[-2]
        if spin == 1:
            self.status_spinner.show()
            self.status_spinner.start()
        elif spin in (0,3):
            self.status_spinner.stop()
            self.status_spinner.hide()
        if spin != 3:
            self.status_bar.set_markup(gui_msg(msg, debug=self.debug))

 


    def _on_unb_changed(self, *args):
        """ Action on changing upper tab """    
        self.curr_upper = self.upper_notebook.get_nth_page(args[-1])
        if self.curr_upper is None: type = -1
        else: type = self.curr_upper.type

        if type in (FX_TAB_PLACES, FX_TAB_SEARCH, FX_TAB_CONTEXTS, FX_TAB_SIMILAR, FX_TAB_TREE, FX_TAB_NOTES, FX_TAB_TRENDING,):
            self.feed_win.feed_aggr = self.curr_upper.feed_aggr
        else: self.feed_win.feed_aggr = {}

        self.feed_win.reload_feeds()

        if type == FX_TAB_REL_TIME:
            self.selection_res.populate(self.curr_upper.top_entry.tuplify())
            self.on_changed_selection()

        if self.curr_upper.feed_filter_id > 0:
            self.feed_win._add_underline( self.curr_upper.feed_filter_id )

        self.curr_upper.load_selection()





    def on_changed_selection(self, *args, **kargs):
        """ Generates result preview when result cursor changes """
        adj = self.preview_box.get_vadjustment()
        adj.set_value(0)

        title = esc_mu(self.selection_res.get("title",''))
        author = esc_mu(self.selection_res.get('author',''))
        publisher = esc_mu(self.selection_res.get('publisher',''))
        contributors = esc_mu(self.selection_res.get('contributors',''))
        category = esc_mu(self.selection_res.get('category',''))
        desc = esc_mu(self.selection_res.get("desc",''))
        text = esc_mu(self.selection_res.get("text",''))

        # Hilight query using snippets
        col = self.config.get('gui_hilight_color','blue')
        snip_str = ''
        if self.selection_res.get('snippets',[]) not in ([],()):
            snip_str = f"""\n\n{_('Snippets:')}\n<small>----------------------------------------------------------</small>\n"""
            srch_str = []
            snips = self.selection_res.get('snippets',[])
            for s in snips:
                if len(s) == 3:
                    snip_str = f"""{snip_str}\n\n{esc_mu(s[0])}<span foreground="{col}">{esc_mu(s[1])}</span>{esc_mu(s[2])}"""
                    s1 = s[1].strip()
                    s1 = esc_mu(s1)
                    if s1 not in srch_str: srch_str.append(s1)
                     
            for s in srch_str:
                title = title.replace(s, f'<span foreground="{col}">{s}</span>')
                author = author.replace(s, f'<span foreground="{col}">{s}</span>')
                publisher = publisher.replace(s, f'<span foreground="{col}">{s}</span>')
                contributors = contributors.replace(s, f'<span foreground="{col}">{s}</span>')
                category = category.replace(s, f'<span foreground="{col}">{s}</span>')
                desc = desc.replace(s, f'<span foreground="{col}">{s}</span>')
                text = text.replace(s, f'<span foreground="{col}">{s}</span>')

        link_text = ''
        l_text = esc_mu(scast(self.selection_res['link'], str, '').replace('<','').replace('>',''))
        if l_text.endswith('/'): l_label = slist(l_text.split('/'), -2, l_text)
        else: l_label = slist(l_text.split('/'), -1, l_text)
        if l_text != '': link_text=f"""<a href="{l_text}" title="{_('Click to open link')} : {l_text}">{l_label}</a>"""
        self.links = ''
        for l in self.selection_res.get('links','').splitlines() + self.selection_res.get('enclosures','').splitlines():

            if l.strip() == '' or l == self.selection_res['link']: continue
            self.links = f'{self.links}{l}\n'
            l_text = esc_mu(l.replace('<','').replace('>',''))
            if l_text.endswith('/'): l_label = slist(l_text.split('/'), -2, l_text)
            else: l_label = slist(l_text.split('/'), -1, l_text)
            link_text = f"""{link_text}
<a href="{l_text}" title="{_('Click to open link')}: {l_text}">{l_label}</a>"""
        
        if link_text != '': link_text = f"\n\n{_('Links:')}\n{link_text}"


        stat_str = f"""{snip_str}\n\n<small>-------------------------------------\n{_("Word count")}: <b>{self.selection_res['word_count']}</b>
{_("Character count")}: <b>{self.selection_res['char_count']}</b>
{_("Sentence count")}: <b>{self.selection_res['sent_count']}</b>
{_("Capitalized word count")}: <b>{self.selection_res['caps_count']}</b>
{_("Common word count")}: <b>{self.selection_res['com_word_count']}</b>
{_("Polysyllable count")}: <b>{self.selection_res['polysyl_count']}</b>
{_("Numeral count")}: <b>{self.selection_res['numerals_count']}</b>\n
{_("Importance")}: <b>{round(self.selection_res['importance'],3)}</b>
{_("Weight")}: <b>{round(self.selection_res['weight'],3)}</b>
{_("Readability")}: <b>{round(self.selection_res['readability'],3)}</b></small>\n"""

        if author != '' or publisher != '' or contributors != '': author_section = f"""

<i>{author} {publisher} {contributors}</i>        
"""
        else: author_section = ''

        if category != '': category = f"""

{category}
"""

        self.preview_label.set_markup(f"""
<b>{title}</b>{author_section}{category}

{desc}

{text}

{link_text}

{stat_str}
                                                                                                                                                        """)


        if not self.config.get('ignore_images',False):
            self.handle_images(self.selection_res.get('id', None), f"""{self.selection_res.get('images','')}\n{self.links}""")









    


############################################
#   IMAGE HANDLING




    def handle_image(self, widget, event, url, title, alt, user_agent):
        """ Wrapper for showing full-size image in chosen external viewer """
        if event.button == 1:
            user_agent = coalesce(user_agent, self.config.get('user_agent', FEEDEX_USER_AGENT))
            hash_obj = hashlib.sha1(url.encode())
            filename = os.path.join(self.FX.cache_path, f'{hash_obj.hexdigest()}_full.img' )
            if not os.path.isfile(filename):                
                err = download_res(url, filename, no_thumbnail=True, user_agent=user_agent)
                if err != 0:
                    self.update_status(0, err)
                    return -1

            err = ext_open(self.config, 'image_viewer', filename, title=title, alt=alt, file=True, debug=self.debug)
            if err != 0:
                self.update_status(0, err)
                return -1


    def download_images(self, id, user_agent, queue):
        """ Image download wrapper for separate thread"""
        user_agent = coalesce(user_agent, self.config.get('user_agent', FEEDEX_USER_AGENT))
        for i in queue:
            url = i[0]
            filename = i[1]
            if url not in self.download_errors:
                err = download_res(url, filename, user_agent=user_agent)
                if  err != 0:
                    self.lock.acquire()
                    self.download_errors.append(url)
                    if err[0] < 0: self.message_q.append( (0, err) )
                    self.lock.release()

        self.lock.acquire()        
        self.images_q.append(id)
        self.lock.release()




    def handle_images(self, id:int, string:str, **kargs):
        """ Handle preview images """
        for c in self.prev_images.get_children():
            self.prev_images.remove(c)

        urls = []
        boxes = []
        download_q = []
        for i in string.splitlines():
            im = res(i, self.FX.cache_path)
            if im == 0: continue
            if im['url'] in urls: continue
            if im['url'] in self.download_errors: continue

            urls.append(im['url'])
            if os.path.isfile(im['filename']) and os.path.getsize(im['filename']) > 0:
                pass
            else:
                download_q.append((im['url'], im['filename']))
                continue

            if id != self.selection_res.get('id', None): continue

            eventbox = Gtk.EventBox()
            try:
                pixb = GdkPixbuf.Pixbuf.new_from_file(im['filename'])
                image = Gtk.Image.new_from_pixbuf(pixb)
            except GLib.Error as e:
                self.download_errors.append(im['url'])
                self.message_q.append( (0, (-1, _('Image error: %a'), err) ) )
                continue
            
            image.set_tooltip_markup(f"""{im.get('tooltip')}
Click to open in image viewer""")

            eventbox.add(image)
            eventbox.connect("button-press-event", self.handle_image, im['url'], im['title'], im['alt'], self.selection_res['user_agent'])
            image.show()
            eventbox.show()
            boxes.append(eventbox)

        if len(download_q) > 0:
            t = threading.Thread(target=self.download_images, args=(self.selection_res['id'], self.selection_res['user_agent'], download_q))
            t.start()

        for b in boxes:
            self.prev_images.pack_start(b, True, True, 3)















#########################################################3
# DIALOGS ADN ACTIONS FROM MENUS OR BUTTONS



        




    def on_load_news_feed(self, *args):
        if self.flag_fetch or self.flag_feed_update: return -2
        if not self._fetch_lock(): return 0
        self.update_status(1, _('Checking for news ...') )
        self.flag_fetch = True
        self.action_q.append(FX_ACTION_BLOCK_FETCH)
        t = threading.Thread(target=self.load_news_thr, args=('feed',))
        t.start()

    def on_load_news_all(self, *args):
        if self.flag_fetch or self.flag_feed_update: return -2
        if not self._fetch_lock(): return 0
        self.update_status(1, _('Checking for news ...') )
        self.flag_fetch = True
        self.action_q.append(FX_ACTION_BLOCK_FETCH)
        t = threading.Thread(target=self.load_news_thr, args=('all',))
        t.start()

    def on_load_news_background(self, *args):
        if self.flag_fetch or self.flag_feed_update: return -2
        if not self._fetch_lock(): return 0
        self.update_status(1, _('Checking for news ...') )
        self.flag_fetch = True
        self.action_q.append(FX_ACTION_BLOCK_FETCH)
        t = threading.Thread(target=self.load_news_thr, args=('background',))
        t.start()

    def _fetch_lock(self, *args):
        """ Handle fetching lock gracefully """
        if self.FX.lock_fetching(check_only=True) != 0:
            dialog = YesNoDialog(self, _("Database is Locked for Fetching"), f"<b>{_('Database is Locked for Fetching! Proceed and unlock?')}</b>", 
                                subtitle=_("Another instance may be fetching news right now. If not, proceed with operation. Proceed?") )
            dialog.run()
            if dialog.response == 1:
                dialog.destroy()
                err = self.FX.unlock_fetching()
                if err == 0: 
                    self.update_status(0, _('Database manually unlocked for fetching...') )
                    return True
                else: 
                    self.update_status(0, err)
                    return False
            else:
                dialog.destroy()
                return False
        else: return True


    def load_news_thr(self, mode):
        """ Fetching news/articles from feeds """
        if mode == 'all':
            feed_id=None
            ignore_interval = True
            ignore_modified = self.config.get('ignore_modified',True)
        elif mode == 'background':
            feed_id=None
            ignore_interval = False
            ignore_modified = self.config.get('ignore_modified',True)
        elif mode == 'feed':
            if self.selection_feed['is_category'] != 1:
                feed_id = self.selection_feed['id']
                ignore_interval = True
                ignore_modified = True
            else:
                self.lock.acquire()
                self.flag_fetch = False
                self.lock.release()
                return -1
        else:
            self.lock.acquire()
            self.flag_fetch = False
            self.lock.release()
            return -1

        FX = Feeder(self.MC, config=self.config, debug=self.debug, ignore_images=self.config.get('ignore_images',False), gui=True, timeout=1)
        for msg in FX.g_fetch(id=feed_id, force=ignore_modified, ignore_interval=ignore_interval): 
            self.lock.acquire()
            self.message_q.append((1, msg,))
            self.lock.release()

        if FX.new_items > 0:
            if self.config.get('gui_desktop_notify', True):
                fx_notifier = DesktopNotifier(parent=self, icons=self.FX.MC.icons)

                if self.config.get('gui_notify_group','feed') == 'number':
                    fx_notifier.notify(f'{FX.new_items} {_("new articles fetched...")}', None, -3)
                else:

                    filters = {'last':True,
                    'group':self.config.get('gui_notify_group','feed'), 
                    'depth':self.config.get('gui_notify_depth',0)
                    }
                    results = FX.Q.query('', filters , rev=False, print=False, allow_group=True)
                    fx_notifier.load(results)
                    fx_notifier.show()

        self.lock.acquire()
        self.message_q.append((3,None))
        self.flag_fetch = False
        self.action_q.append(FX_ACTION_UNBLOCK_FETCH)
        self.action_q.append(FX_ACTION_RELOAD_FEEDS)
        self.lock.release()



    def on_update_feed(self, *args):
        """ Wrapper for feed updating """
        if self.selection_feed['is_category'] == 1: return 0
        if self.flag_fetch or self.flag_feed_update: return -2
        if not self._fetch_lock(): return 0
        self.flag_fetch = True
        self.flag_feed_update = True
        self.action_q.append(FX_ACTION_BLOCK_FETCH)
        self.update_status(1, _('Updating channel...') )
        t = threading.Thread(target=self.update_feed_thr, args=(self.selection_feed['id'],))
        t.start()

    def on_update_feed_all(self, *args):
        if self.flag_fetch or self.flag_feed_update: return -2
        if not self._fetch_lock(): return 0
        self.flag_fetch = True
        self.flag_feed_update = True
        self.action_q.append(FX_ACTION_BLOCK_FETCH)
        self.update_status(1, _('Updating all channels...') )
        t = threading.Thread(target=self.update_feed_thr, args=(None,))
        t.start()


    def update_feed_thr(self, *args):
        """ Updates metadata for all/selected feed """
        feed_id = args[-1]
        FX = Feeder(self.MC, config=self.config, debug=self.debug, ignore_images=self.config.get('ignore_images',False), gui=True, timeout=1)
        for msg in FX.g_fetch(id=feed_id, update_only=True, force=True): 
            self.lock.acquire()
            self.message_q.append((1, msg,))
            self.lock.release()

        icons = get_icons(FX.MC.feeds, self.FX.MC.icons)      
        self.lock.acquire()
        self.icons = icons
        self.message_q.append((3, None,))
        self.flag_fetch = False
        self.flag_feed_update = False
        self.action_q.append(FX_ACTION_UNBLOCK_FETCH)
        self.action_q.append(FX_ACTION_RELOAD_FEEDS_DB)
        self.lock.release()


    def add_from_url_thr(self):
        """ Add from URL - threading """
        FX = Feeder(self.MC, config=self.config, debug=self.debug, ignore_images=self.config.get('ignore_images',False), gui=True, timeout=1)

        self.lock.acquire()
        self.new_feed_url.set_interface(FX)
        self.lock.release()

        err = False
        for msg in self.new_feed_url.g_add_from_url():
            if msg[0] < 0: err = True
            self.lock.acquire()
            self.message_q.append((1, msg,))
            self.lock.release()

        self.lock.acquire()
        self.message_q.append((3, None,))
        self.flag_fetch = False
        self.flag_feed_update = False
        if not err: self.new_feed_url.clear()
        self.new_feed_url.set_interface(self.FX)
        self.action_q.append(FX_ACTION_UNBLOCK_FETCH)
        self.action_q.append(FX_ACTION_RELOAD_FEEDS_DB)
        self.lock.release()


    def on_add_from_url(self, *args):
        """ Adds a new feed from URL - dialog """
        if self.flag_fetch or self.flag_feed_update: return 0

        dialog = NewFromURL(self, self.new_feed_url, debug=self.debug)
        dialog.run()
        if dialog.response == 1:
            self.update_status(1, _('Adding Channel...') )
            if not self._fetch_lock(): return 0
            self.flag_fetch = True
            self.flag_feed_update = True
            self.action_q.append(FX_ACTION_BLOCK_FETCH)
            t = threading.Thread(target=self.add_from_url_thr)
            t.start()
        dialog.destroy()












    def on_edit_entry(self, *args):
        """ Add / Edit Entry """
        new = args[-1]
        if not new and self.flag_edit_entry: return 0

        if new: entry = self.new_entry
        else: 
            if self.selection_res['id'] is None: return 0            
            entry = EntryContainer(self.FX, id=self.selection_res['id'])
            if not entry.exists: return -1

        if self.curr_upper.type == FX_TAB_NOTES or new: short = True
        else: short = False

        dialog = EditEntry(self, self.config, entry, new=new, short=short)
        dialog.run()

        if dialog.response == 1:
            if new: self.update_status(1, _('Adding entry...') )
            else: self.update_status(1, _('Openning entry ...') )
            
            self.flag_edit_entry = True    
            t = threading.Thread(target=self.edit_entry_thr, args=(entry, new) )
            t.start()
        dialog.destroy()


    def edit_entry_thr(self, entry, new:bool):
        """ Add/Edit Entry low-level interface for threading """
        err = False
        FX = Feeder(self.MC, config=self.config, debug=self.debug, ignore_images=self.config.get('ignore_images',False), gui=True, wait_indef=True)
        
        self.lock.acquire()
        entry.set_interface(FX)
        self.lock.release()

        if new:
            for msg in entry.g_add():
                if msg[0] < 0: err = True
                self.lock.acquire()
                self.message_q.append((1, msg,))
                self.lock.release()
            if not err:
                self.lock.acquire()
                self.action_q.append((entry.vals.copy(), FX_ACTION_ADD))
                entry.clear()
                self.lock.release()

        else: 
            for msg in entry.g_do_update():
                if msg[0] < 0: err = True
                self.lock.acquire()
                self.message_q.append((1, msg,))
                self.lock.release()
            if not err:
                self.lock.acquire()
                self.action_q.append((entry.vals.copy(), FX_ACTION_EDIT))
                self.lock.release()

        self.lock.acquire()
        self.message_q.append((3, None))
        self.flag_edit_entry = False
        self.lock.release()






    def on_del_entry(self, *args):
        """ Deletes selected entry"""
        if self.selection_res['id'] is None: return 0
        entry = EntryContainer(self.FX, id=self.selection_res['id'])
        if not entry.exists: return -1

        if entry['deleted'] != 1: 
            dialog = YesNoDialog(self, _('Delete Entry'), f'{_("Are you sure you want to delete")} <i><b>{esc_mu(entry.name())}</b></i>?')
        else:
            dialog = YesNoDialog(self, _('Delete Entry permanently'), f'{_("Are you sure you want to permanently delete")} <i><b>{esc_mu(entry.name())}</b></i> {_("and associated rules?")}')
        dialog.run()
        if dialog.response == 1:
            err = False
            msg = entry.r_delete()
            if msg[0] < 0: err = True
            self.update_status(0, msg)
            if not err: self.curr_upper.apply_changes(entry.vals.copy(), FX_ACTION_EDIT)
        dialog.destroy()

    def on_restore_entry(self, *args):
        """ Restore entry """
        if self.selection_res['id'] is None: return 0
        entry = EntryContainer(self.FX, id=self.selection_res['id'])
        if not entry.exists or entry['deleted'] == 0: return -1

        dialog = YesNoDialog(self, _('Restore Entry'), f'{_("Are you sure you want to restore")} <i><b>{esc_mu(entry.name())}</b></i>?')
        dialog.run()
        if dialog.response == 1:
            err = False
            for msg in entry.g_update({'deleted': 0}): 
                if msg[0] < 0: err = True
                self.update_status(0, msg)
            if not err: self.curr_upper.apply_changes(entry.vals.copy(), FX_ACTION_EDIT)
        dialog.destroy()





    def on_feed_cat(self, *args):
        """ Edit feed/category """
        action = args[-1]
        if action == 'new_category': 
            feed = self.new_category
            new = True
            dialog = EditCategory(self, feed, new=new)
        elif action == 'new_channel': 
            feed = self.new_feed
            new = True
            dialog = EditFeed(self, feed, new=new)
        elif action == 'edit':
            if self.selection_feed['id'] is None: return 0
            new = False
            feed = FeedContainer(self.FX, id=self.selection_feed['id'])
            if not feed.exists: return -1
            if feed['is_category'] == 1:
                dialog = EditCategory(self, feed, new=new)
            else:
                dialog = EditFeed(self, feed, new=new)

        dialog.run()

        if dialog.response == 1:

            if new: msg = feed.r_add(validate=False)
            else: 
                if feed['is_category'] == 1: msg = feed.r_do_update(validate=True)
                else: msg = feed.r_do_update(validate=False)
            self.update_status(0, msg)

            if msg[0] >= 0:
                if action == 'new_category': self.new_category.clear()
                elif action == 'new_channel': self.new_feed.clear()

                self.feed_win.reload_feeds(load=True)

        dialog.destroy()






    def on_del_feed(self, *args):
        """ Deletes feed or category """
        if self.selection_feed['id'] is None: return 0
        feed = FeedContainer(self.FX, id=self.selection_feed['id'])
        if not feed.exists: return -1

        if coalesce(feed['is_category'],0) == 0 and coalesce(feed['deleted'],0) == 0:
            dialog = YesNoDialog(self, _('Delete Channel'), f'<b>{_("Are you sure you want to delete")} <i>{esc_mu(feed.name())}</i>{_("?")}</b>')

        elif coalesce(feed['is_category'],0) == 0 and coalesce(feed['deleted'],0) == 1:
            dialog = YesNoDialog(self, _('Delete Channel permanently'), f'<b>{_("Are you sure you want to permanently delete")} <i>{esc_mu(feed.name())}</i>{_("?")}</b>')

        elif coalesce(feed['is_category'],0) == 1 and coalesce(feed['deleted'],0) == 0:
            dialog = YesNoDialog(self, _('Delete Category'), f'<b>{_("Are you sure you want to delete")} <i>{esc_mu(feed.name())}</i> {_("Category?")}</b>')

        elif coalesce(feed['is_category'],0) == 1 and coalesce(feed['deleted'],0) == 1:
            dialog = YesNoDialog(self, _('Delete Category'), f'<b>{_("Are you sure you want to permanently delete")} <i>{esc_mu(feed.name())}</i> {_("Category?")}</b>')

        dialog.run()
        if dialog.response == 1:
            msg = feed.r_delete()
            self.update_status(0, msg)
            if msg[0] >= 0: self.feed_win.reload_feeds(load=True)
        
        dialog.destroy()




    def on_restore_feed(self, *args):
        """ Restores selected feed/category """
        if self.selection_feed['id'] is None: return 0
        feed = FeedContainer(self.FX, id=self.selection_feed['id'])
        if not feed.exists: return -1

        if coalesce(feed['is_category'],0) == 1:
            dialog = YesNoDialog(self, _('Restore Category'), f'<b>{_("Restore ")}<i>{esc_mu(feed.name())}</i>{_(" Category?")}</b>')
        else:
            dialog = YesNoDialog(self, _('Restore Channel'), f'<b>{_("Restore ")}<i>{esc_mu(feed.name())}</i>{_(" Channel?")}</b>')
        
        dialog.run()

        if dialog.response == 1:
            msg = feed.r_update({'deleted': 0}) 
            self.update_status(0, msg)
            if msg[0] >= 0: self.feed_win.reload_feeds(load=True)
        
        dialog.destroy()





    def on_empty_trash(self, *args):
        """ Empt all Trash items """
        dialog = YesNoDialog(self, _('Empty Trash'), f'<b>{_("Do you really want to permanently remove Trash content?")}</b>')
        dialog.run()
        if dialog.response == 1:
            msg = self.FX.r_empty_trash() 
            self.update_status(0, msg)
            if msg[0] >= 0: self.feed_win.reload_feeds(load=True)
        dialog.destroy()

    def on_clear_history(self, *args):
        """ Clears search history """
        dialog = YesNoDialog(self, _('Clear Search History'), _('Are you sure you want to clear <b>Search History</b>?') )           
        dialog.run()
        if dialog.response == 1:
            msg = self.FX.r_clear_history()
            self.update_status(0, msg)
            for i in range(self.upper_notebook.get_n_pages()):
                tab = self.upper_notebook.get_nth_page(i)
                if tab is None: continue
                if tab.type in (FX_TAB_SEARCH, FX_TAB_CONTEXTS, FX_TAB_TERM_NET, FX_TAB_TIME_SERIES, FX_TAB_NOTES, FX_TAB_TREE): tab.reload_history()
        dialog.destroy()



    def on_mark_healthy(self, *args):
        """ Marks a feed as healthy -> zeroes the error count """
        if self.selection_feed['id'] is None: return 0
        feed = FeedContainer(self.FX, id=self.selection_feed['id'])
        if not feed.exists: return -1  
        msg = feed.r_update({'error': 0})
        self.update_status(0, msg)
        if msg[0] >= 0: self.feed_win.reload_feeds(load=True)




    def mark_recalc_thr(self, mode, *args):
        """ Marks entry as read """
        FX = Feeder(self.MC, config=self.config, debug=self.debug, ignore_images=self.config.get('ignore_images',False), gui=True)
        entry = EntryContainer(FX, id=self.selection_res['id'])
        if not entry.exists: 
            self.lock.acquire()
            self.flag_edit_entry = False
            self.lock.release()
            return -1

        if mode == 'read': 
            if coalesce(entry['read'],0) < 0: idict = {'read': scast(entry['read'],int,0)+1}
            else: idict = {'read': scast(entry['read'],int,0)+1}
        elif mode == 'unimp': idict = {'read': -1}

        err = False
        for msg in entry.g_update(idict):
            if msg[0] < 0: err = True
            self.lock.acquire()
            self.message_q.append((1, msg))
            self.lock.release()

        self.lock.acquire()
        self.message_q.append((3, None))
        self.flag_edit_entry = False
        if err: 
            self.lock.release()
            return -1
        self.action_q.append((entry.vals.copy(), FX_ACTION_EDIT))
        self.lock.release()

    
    def on_mark_recalc(self, *args):
        if self.selection_res['id'] is None: return 0
        if self.flag_edit_entry: return 0
        self.update_status(1, _('Updating ...') )
        self.flag_edit_entry = True
        mode = args[-1]
        t = threading.Thread(target=self.mark_recalc_thr, args=(mode,))
        t.start()



    def on_mark(self, *args):
        """ Marks entry as unread """
        if self.selection_res['id'] is None: return 0        
        entry = EntryContainer(self.FX, id=self.selection_res['id'])
        if not entry.exists: return -1

        action = args[-1]
        if action == 'unread': idict = {'read': 0}
        elif action == 'unflag': idict = {'flag': 0}
        elif type(action) is int: idict = {'flag': action}
        else: return -1

        err = False
        for msg in entry.g_update(idict):
            if msg[0] < 0: err = True
            self.update_status(1, msg)
        self.update_status(3, None)
        if err: return -1
        self.curr_upper.apply_changes(entry.vals.copy(), FX_ACTION_EDIT)


    

    def on_del_rule(self, *args):
        """ Deletes rule - wrapper """
        if self.selection_rule['id'] is None: return 0
        rule = RuleContainer(self.FX, id=self.selection_rule['id'])
        if not rule.exists: return -1

        dialog = YesNoDialog(self, _('Delete Rule'), f'{_("Are you sure you want to permanently delete ")}<b><i>{esc_mu(rule.name())}</i></b>{_(" Rule?")}')           
        dialog.run()
        if dialog.response == 1:
            msg = rule.r_delete() 
            self.update_status(0, msg) 
            if msg[0] >= 0: 
                if self.rules_tab != -1: self._get_upn_page_obj(self.rules_tab).apply_changes(rule.vals.copy(), FX_ACTION_DELETE)
        dialog.destroy()

        


    def on_edit_rule(self, *args):
        """ Edit / Add Rule with dialog """
        new = args[-1]

        if new: rule = self.new_rule
        else: 
            if self.selection_rule['id'] is None: return 0
            rule = RuleContainer(self.FX, id=self.selection_rule['id'])
            if not rule.exists: return -1

        dialog = EditRule(self, self.config, rule, new=new)
        dialog.run()

        if dialog.response == 1:
            if new:
                msg = rule.r_add(validate=False) 
                self.update_status(0, msg)
                if msg[0] >= 0: self.new_rule.clear()
            else:
                msg = rule.r_do_update(validate=False)
                self.update_status(0, msg)

            if msg[0] >= 0: 
                if self.rules_tab != -1: 
                    if new: self._reload_rules()
                    else: self._get_upn_page_obj(self.rules_tab).apply_changes(rule.vals.copy(), FX_ACTION_EDIT)
        dialog.destroy()   





    def on_del_flag(self, *args):
        """ Deletes flag - wrapper """
        if self.selection_flag['id'] is None: return 0
        flag = FlagContainer(self.FX, id=self.selection_flag['id'])
        if not flag.exists: return -1

        dialog = YesNoDialog(self, _('Delete Flag'), f'{_("Are you sure you want to permanently delete ")}<b><i>{esc_mu(flag.name())}</i></b>{_(" Flag?")}')           
        dialog.run()
        if dialog.response == 1:
            msg = flag.r_delete()
            self.update_status(0, msg) 
            if msg[0] >= 0: 
                if self.flags_tab != -1: self._get_upn_page_obj(self.flags_tab).apply_changes(flag.vals.copy(), FX_ACTION_DELETE)
        dialog.destroy()

        

    def on_edit_flag(self, *args):
        """ Edit / Add Flag with dialog """
        new = args[-1]

        if new: flag = self.new_flag
        else: 
            if self.selection_flag['id'] is None: return 0
            flag = FlagContainer(self.FX, id=self.selection_flag['id'])
            if not flag.exists: return -1

        dialog = EditFlag(self, self.config, flag, new=new)
        dialog.run()

        if dialog.response == 1:
            if new:
                msg = flag.r_add(validate=False) 
                self.update_status(0, msg)
                if msg[0] >= 0: self.new_flag.clear()
            else:
                msg = flag.r_do_update(validate=False)
                self.update_status(0, msg)

            if msg[0] >= 0: 
                if self.flags_tab != -1:
                    if new: self._reload_flags()
                    else: self._get_upn_page_obj(self.flags_tab).apply_changes(flag.vals.copy(), FX_ACTION_EDIT)
        dialog.destroy()   




        
    def open_entry_thr(self, entry, *args):
        """ Wrappper for opening entry and learning in a separate thread """
        FX = Feeder(self.MC, config=self.config, debug=self.debug, ignore_images=True, gui=True, desktop_notify=False)
        self.lock.acquire()
        entry.set_interface(FX)
        self.lock.release()        

        for msg in entry.g_open():
            self.lock.acquire()
            self.message_q.append((1, msg,))
            self.lock.release()

        self.lock.acquire()
        self.action_q.append((entry.vals.copy(), FX_ACTION_EDIT))
        self.message_q.append((0, _('Done...') ))
        self.flag_edit_entry = False
        self.lock.release()

    def on_activate_result(self, *args, **kargs):
        """ Run in browser and learn """
        if self.flag_edit_entry: return -2
        if self.selection_res['id'] is None: return 0
        entry = EntryContainer(self.FX, id=self.selection_res['id'])
        if not entry.exists: return -1
        if coalesce(self.selection_res['link'],'') != '':
            self.update_status(1, _('Opening ...') )
            self.flag_edit_entry = True
            t = threading.Thread(target=self.open_entry_thr, args=(entry,))
            t.start()
        else:
            self.on_edit_entry(False)


    def on_go_home(self, *args):
        """ Executes browser on channel home page """
        if self.selection_feed['id'] is None: return 0
        feed = FeedContainer(self.FX, feed_id=self.selection_feed['id'])
        if not feed.exists: return -1
        msg = feed.r_open()
        self.update_status(0, msg)




    def on_prefs(self, *args):
        """ Run preferences dialog """
        restart = False
        dialog = PreferencesDialog(self, self.config)
        dialog.run()
        if dialog.response == 1:
            restart = dialog.result.get('restart',False)            
            reload = dialog.result.get('reload',False)
            reload_lang = dialog.result.get('reload_lang',False)            
            dialog.result.pop('restart')
            dialog.result.pop('reload')
            dialog.result.pop('reload_lang')

            new_config = save_config(dialog.result, FEEDEX_CONFIG)
            if new_config == -1: self.update_status(0, (-1, _('Error saving configuration to %a'), FEEDEX_CONFIG))
            else:
                if reload_lang:
                    if self.config.get('lang') not in (None,'en'):
                        lang = gettext.translation('feedex', languages=[config.get('lang')])
                        lang.install(FEEDEX_LOCALE_PATH)
                if reload:
                    self.FX.refresh_data()
                    if self.debug in (1,7): print('Data reloaded...')
                if restart:
                    dialog.destroy()
                    dialog2 = InfoDialog(self, _('Restart Required'), _('Restart is required for all changes to be applied.'), button_text=_('OK') )
                    dialog2.run()
                    dialog2.destroy()
                self.update_status(0, _('Configuration saved successfully') )
                self.config = parse_config(None, config_str=new_config)
                if self.debug in (1,7,6): print(self.config)
        if not restart: dialog.destroy()



    def on_view_log(self, *args):
        """ Shows dialog for reviewing log """
        err = ext_open(self.config, 'text_viewer', self.config.get('log',None), file=True, debug=self.debug)
        if err != 0: self.update_status(0, err)






    def on_show_detailed(self, *args):
        """ Shows dialog with entry's detailed technical info """
        entry = EntryContainer(self.FX, id=self.selection_res['id'])
        if not entry.exists: self.update_status(0, (-2, _('Entry %a not found!'), self.selection_res['id']) ) 

        tmp_file = os.path.join(self.FX.cache_path, f'{random_str(length=5)}_entry_details.txt')
        with open(tmp_file, 'w') as f: f.write(entry.__str__())

        err = ext_open(self.config, 'text_viewer', tmp_file, file=True, debug=self.debug)
        if err != 0: self.update_status(0, err)


    def on_feed_details(self, *args):
        """ Shows feed's techical details in a dialog """
        feed = FeedContainer(self.FX, id=self.selection_feed['id'])
        if not feed.exists: self.update_status(0, (-2, _('Channel %a not found!'), self.selection_res['id']) )

        tmp_file = os.path.join(self.FX.cache_path, f'{random_str(length=5)}_feed_details.txt' )
        with open(tmp_file, 'w') as f: f.write(feed.display())

        err = ext_open(self.config, 'text_viewer', tmp_file, file=True, debug=self.debug)
        if err != 0: self.update_status(0, err)

        





    def on_show_stats(self, *args):
        """ Shows dialog with SQLite DB statistics """
        stat_str = self.FX.db_stats(print=False, markup=True)
        dialog = DisplayWindow(self, _("Database Statistics"), stat_str, width=600, height=500, emblem=self.icons.get('db'))
        dialog.run()
        dialog.destroy()

    def on_show_about(self, *args):
        """ Shows 'About...' dialog """
        dialog = AboutDialog(self)
        dialog.run()
        dialog.destroy()



    def on_show_rules_for_entry(self, *args, **kargs):
        """ Show dialog with rules matched for entry """
        if self.selection_res['id'] is None: return 0
        entry = EntryContainer(self.FX, id=self.selection_res['id'])
        if not entry.exists: return -1
            
        importance, flag, best_entries, flag_dist, rules_tmp = entry.ling(rank=True, index=False, learn=False, to_disp=True)
        footer = f"""{_('Rules matched')}: <b>{len(rules_tmp)}</b>
{_('Saved Importance')}: <b>{self.selection_res['importance']:.3f}</b>
{_('Saved Flag')}: <b>{self.selection_res['flag']:.0f}</b>

{_('Calculated Importance')}: <b>{importance:.3f}</b>
{_('Caculated Flag')}: <b>{flag:.0f}</b>

{_('Flag distribution')}:
"""
        for f,v in flag_dist.items(): footer =  f"{footer}\n{self.FX.get_flag_name(f)} ({f}): <b>{v:.3f}</b>"

        footer = f"""{footer}


{_('Most similar read Entries')}:"""
        for e in best_entries: footer = f"""{footer}{e}, """

        r = SQLContainer('rules', RULES_SQL_TABLE_RES)
        rules = self.FX.Q.show_rules(results=rules_tmp, print=False)
        store = Gtk.ListStore(str, str, int,  str, str, str, str, str, str,  float, int, str, str, int)
        for rl in rules: 
            r.populate(rl)
            store.append( (r['name'], r['string'], r['matched'], r['learned'], r['case_insensitive'], r['query_type'], r['field_name'], r['feed_name'], 
            r['lang'], r['weight'], r['flag'], r['flag_name'], r['additive'], r['context_id'] ) )
        
        dialog = DisplayMatchedRules(self, footer, store)
        dialog.run()
        dialog.destroy() 





    def show_learned_rules(self, *args):
        """ Shows learned rules with weights in a separate window """
        self.FX.load_rules(no_limit=True)
        rule = SQLContainer('rules', RULES_SQL_TABLE)        
        rule_store = Gtk.ListStore(str, str, float, int)
        weight_sum = 0

        for r in self.FX.MC.rules:
            if r[rule.get_index('learned')] == 1:
                name = r[1]
                string = r[5]
                weight = r[8]
                context_id = r[12]
                rule_store.append( (name, string, weight, context_id) )
                weight_sum += r[rule.get_index('weight')]
        rule_count = len(rule_store)
        if rule_count == 0:
            dialog =InfoDialog(None, _("Dataset Empty"), _("There are no learned rules to display") )
            dialog.run()
            dialog.destroy()
            return 0            
        avg_weight = weight_sum / rule_count
        header = f'{_("Unique Rule count")}: <b>{rule_count}</b>, {_("Avg Rule weight")}: <b>{round(avg_weight,3)}</b>'
        dialog = DisplayRules(self, header, rule_store)
        dialog.run()
        if dialog.response == 1:
            msg = self.FX.r_delete_learned_rules()
            self.update_status(0, msg)
        dialog.destroy()
        self.FX.load_rules(no_limit=False)        






    def on_show_keywords(self, *args, **kargs):
        """ Shows keywords for entry """
        title = f'{_("Keywords for entry ")}<b>{esc_mu(self.selection_res.name())}</b> ({_("id")}: {self.selection_res["id"]})'
        keywords = self.FX.Q.get_keywords(self.selection_res.get('id'), rev=True)
        if self.FX.db_error is not None:
            self.update_status(0, (-2, _('DB Error: %a'), self.FX.db_error) )
            return 0

        if len(keywords) == 0:
            self.update_status(0, _('Nothing to show') )
            return 0

        kw_store = Gtk.ListStore(str, float)
        for kw in keywords:
            kw_store.append(kw)

        dialog = DisplayKeywords(self, title, kw_store, width=600, height=500)
        dialog.run()
        dialog.destroy()



##########################################
#   DB Maintenance Stuff





    def on_maintenance_thr(self, *args, **kargs):
        """ DB Maintenance thread """
        FX = Feeder(self.MC, config=self.config, debug=self.debug, ignore_images=True, gui=True, desktop_notify=False)
        for msg in FX.g_db_maintenance():
            self.lock.acquire()
            self.message_q.append((1, msg,))
            self.lock.release()
        
        self.action_q.append(FX_ACTION_UNBLOCK_DB)
        self.flag_db_blocked = False
        self.message_q.append((3, None))

    def on_maintenance(self, *args, **kargs):
        """ BD Maintenance """
        if self.flag_db_blocked: return -1
        dialog = YesNoDialog(self, _('DB Maintenance'), _('Are you sure you want to DB maintenance? This may take a long time...') )  
        dialog.run()
        if dialog.response == 1:
            self.action_q.append(FX_ACTION_BLOCK_DB)
            self.flag_db_blocked = True
            t = threading.Thread(target=self.on_maintenance_thr)
            t.start()
        dialog.destroy()


    def on_clear_cache_thr(self, *args, **kargs):
        db_hash = self.FX.db_hash
        for msg in clear_im_cache(-1, self.FX.cache_path):
            self.lock.acquire()
            self.message_q.append((1, msg,))
            self.lock.release()
        self.action_q.append(FX_ACTION_UNBLOCK_DB)
        self.flag_db_blocked = False
        self.message_q.append((3, None))



    def on_clear_cache(self, *args, **kargs):
        """ Clear image cache """
        if self.flag_db_blocked: return -1
        dialog = YesNoDialog(self, _('Clear Cache'), _('Do you want to delete all downloaded and cached images/thumbnails?') )  
        dialog.run()
        if dialog.response == 1:
            self.action_q.append(FX_ACTION_BLOCK_DB)
            self.update_status(1, _('Clearing cache ...') )
            self.flag_db_blocked = True
            t = threading.Thread(target=self.on_clear_cache_thr)
            t.start()
        dialog.destroy()



    ####################################################
    # Porting
    #           Below are wrappers for porting data


    def _choose_file(self, *args, **kargs):
        """ File chooser for porting """
        if kargs.get('action') == 'save':
            dialog = Gtk.FileChooserDialog(_("Save as.."), parent=self, action=Gtk.FileChooserAction.SAVE)
            dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        else:
            dialog = Gtk.FileChooserDialog(_("Open file"), parent=self, action=Gtk.FileChooserAction.OPEN)
            dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)

        dialog.set_current_folder(kargs.get('start_dir', os.getcwd()))
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
        else: filename = False
        dialog.destroy()

        if kargs.get('action') == 'save' and os.path.isfile(filename):
            dialog = YesNoDialog(self, f'{_("Overwrite?")}', f'{_("File ")}<b>{esc_mu(filename)}</b>{_(" already exists!   Do you want to overwrite it?")}')
            dialog.run()
            if dialog.response == 1: os.remove(filename)
            else: filename = False
        dialog.destroy()

        if filename in ('',None,False): filename = False
        else: self.gui_attrs['last_dir'] = os.path.dirname(filename)

        return filename




    def export_feeds(self, *args):
        filename = self._choose_file(action='save', start_dir=self.gui_attrs.get('last_dir', os.getcwd()) )
        if filename is False: return 0

        msg = self.FX.r_port_data(True, filename, 'feeds')
        self.update_status(0, msg)

    def export_rules(self, *args):
        filename = self._choose_file(action='save', start_dir=self.gui_attrs.get('last_dir', os.getcwd()) )
        if filename is False: return 0

        msg = self.FX.r_port_data(True, filename, 'rules')
        self.update_status(0, msg)

    def export_flags(self, *args):
        filename = self._choose_file(action='save', start_dir=self.gui_attrs.get('last_dir', os.getcwd()) )
        if filename is False: return 0

        msg = self.FX.r_port_data(True, filename, 'flags')
        self.update_status(0, msg)



    def import_feeds(self, *args):
        filename = self._choose_file(action='open', start_dir=self.gui_attrs.get('last_dir', os.getcwd()) )
        if filename is False: return 0

        msg = self.FX.r_port_data(False, filename, 'feeds')
        self.update_status(0, msg)
        if msg[0] >= 0: 
            self.feed_win.reload_feeds(load=True)

            dialog = YesNoDialog(self, _('Update Feed Data'), _('New feed data has been imported. Download Metadata now?') )
            dialog.run()
            if dialog.response == 1: self.on_update_feed_all()
            dialog.destroy()


    def import_rules(self, *args):
        filename = self._choose_file(action='open', start_dir=self.gui_attrs.get('last_dir', os.getcwd()) )
        if filename is False: return 0

        msg = self.FX.r_port_data(False, filename, 'rules')
        if msg[0] == 0: 
            if self.rules_tab != -1: self._on_add_as_rule(self.rules_tab).create_rules_list()

    def import_flags(self, *args):
        filename = self._choose_file(action='open', start_dir=self.gui_attrs.get('last_dir', os.getcwd()) )
        if filename is False: return 0

        msg = self.FX.r_port_data(False, filename, 'flags')
        if msg[0] == 0: 
            if self.flags_tab != -1: self._get_upn_page_obj(self.flags_tab).create_flags_list()


    def import_entries(self, *args):
        filename = self._choose_file(action='open', start_dir=self.gui_attrs.get('last_dir', os.getcwd()) )
        if filename is False: return 0

        for msg in self.FX.g_add_entries(efile=filename, learn=True):
            self.update_status(0, msg)




    def export_results_json(self, *args):
        """ Export results from current tab to JSON for later import """
        if self.curr_upper.type in (FX_TAB_RULES, FX_TAB_FLAGS): return 0

        results = self.curr_upper.results
        if len(results) == 0:
            self.update_status(0, _('Nothing to save...') )
            return 0
        
        filename = self._choose_file(action='save', start_dir=self.gui_attrs.get('last_dir', os.getcwd()) )
        if filename == False: return 0        
        
        msg = self.FX.r_port_data(True, filename, 'entries', query_results=results)
        self.update_status(0, msg)





    def export_results_csv(self, *args):
        """ Export results from current tab to CSV """
        if self.curr_upper.type in (FX_TAB_RULES, FX_TAB_FLAGS): return 0

        results = self.curr_upper.results
        if len(results) == 0:
            self.update_status(0, _('Nothing to save...') )
            return 0

        filename = self._choose_file(action='save', start_dir=self.gui_attrs.get('last_dir', os.getcwd()) )
        if filename == False: return 0

 
        if self.curr_upper.type in (FX_TAB_PLACES, FX_TAB_SEARCH, FX_TAB_SIMILAR, FX_TAB_NOTES):
            columns = RESULTS_SQL_TABLE_PRINT
            mask = RESULTS_SHORT_PRINT1
        elif self.curr_upper.type == FX_TAB_CONTEXTS:
            columns = RESULTS_SQL_TABLE_PRINT + (n_("Context"),)
            mask = RESULTS_SHORT_PRINT1 + (n_("Context"),)
        elif self.curr_upper.type == FX_TAB_TERM_NET:
            columns = (n_('Term'), n_('Weight'), n_('Document Count') )
            mask = columns
        elif self.curr_upper.type == FX_TAB_TIME_SERIES:
            columns = (n_('Time'), n_('Occurrence Count') )
            mask = columns

        csv = to_csv(results, columns, mask)

        try:        
            with open(filename, 'w') as f:
                f.write(csv)
                
        except OSError as e:
            os.stderr.write(str(e))
            self.update_status(0,(-1, _('Error saving to %a'), filename))
            return -1
        self.update_status(0, (0, _('Results saved to %a...'), {filename}) )       





#################################################
#       UTILITIES
#

    def quick_find_case_ins(self, model, column, key, rowiter, *args):
        """ Guick find 'equals' fundction - case insensitive """
        column=args[-1]
        row = model[rowiter]
        if key.lower() in scast(list(row)[column], str, '').lower(): return False
        return True


    def startup_decor(self, *args):
        """ Decorate preview tab on startup """
        
        pb = GdkPixbuf.Pixbuf.new_from_file_at_size( os.path.join(FEEDEX_SYS_ICON_PATH,'feedex.png'), 64, 64)
        icon = Gtk.Image.new_from_pixbuf(pb)
        self.prev_images.pack_start(icon, True, True, 0)

        startup_text = f"""
<b>FEEDEX {FEEDEX_VERSION}</b>

<a href="{esc_mu(FEEDEX_WEBSITE)}">{esc_mu(FEEDEX_WEBSITE)}</a>

<i>{FEEDEX_CONTACT}</i>
{FEEDEX_AUTHOR}

{FEEDEX_DESC}
                                                                                """
        self.preview_label.set_markup(startup_text)














def feedex_run_main_win(feedex_main_container, **args):
    """ Runs main Gtk loop with main Feedex window"""
    win = FeedexMainWin(feedex_main_container, **args)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
