# -*- coding: utf-8 -*-
""" GUI classes for FEEDEX """



from feedex_gui_utils import *








class FeedexMainWin(Gtk.Window, FeedexGUISession):
    """ Main window for Feedex """

    def __init__(self, *args, **kargs):
        
        FeedexGUISession.__init__(self, *args, **kargs)
        
        # Init main bus vars
        fdx.task_counter = 0
        

        # Main DB interface - init and check for lock and/or DB errors
        self.connect_db(None) 
        fdx.db_lock = False

        # Init action coordinator
        self.act = FeedexGUIActions(self)

        # Load and init paths, caches and profile-dependent data
        self.set_profile()
        self.gui_cache = self.validate_gui_cache( load_json(self.gui_cache_path, {}) ) #Load cached GUI settings/layouts/tabs from previous session
        self.gui_plugins = self.validate_gui_plugins( load_json(self.gui_plugins_path, FX_DEFAULT_PLUGINS, create_file=True) ) # Load and validate plugin list
        self.get_icons()
        self.cat_icons = {}


        # Timer related ...
        self.sec_frac_counter = 0
        self.sec_counter = 0
        self.minute_counter = 0

        self.today = 0
        self._time()

        # Default fields for edit and new items
        self.default_search_filters = self.gui_cache.get('default_search_filters', FEEDEX_GUI_DEFAULT_SEARCH_FIELDS).copy()

        # Keeping track of new items
        self.new_items = scast( self.gui_cache.get('new_items'), int, 0 )
        self.new_n = scast( self.gui_cache.get('new_n'), int, 0 ) # Last nth unread update

        # Caches for attempted new item add
        self.new_feed_url = {}
        self.new_feed = {}
        self.new_category = {}
        self.new_entry = {}
        self.new_rule = {'additive':1}
        self.new_flag = {}
        self.new_plugin = {}
        # ... and for preview
        self.prev_entry = {}
        self.prev_entry_links = []
        self.curr_prev = None

        # String containing all log messages from this session
        self.log_string = ''

        # Places
        self.curr_place = FX_PLACE_LAST

        # Downloaded item list
        self.downloaded = []

        # Start threading and main window
        Gdk.threads_init()
        Gtk.Window.__init__(self, title='Feedex')
        self.lock = threading.Lock()
        GLib.timeout_add(interval=250, function=self._on_timer)

        self.set_border_width(10)
        self.set_icon(self.icons['main'])
        self.set_resizable(True)
        self.set_position(Gtk.WindowPosition.CENTER)



        # Lower status bar
        self.status_bar = f_label('', justify=FX_ATTR_JUS_LEFT, wrap=True, markup=True, selectable=True, ellipsize=FX_ATTR_ELL_END) 
        self.status_spinner = Gtk.Spinner()
        lstatus_box = Gtk.Box()
        lstatus_box.set_orientation(Gtk.Orientation.HORIZONTAL)
        lstatus_box.set_homogeneous(False)
        lstatus_box.pack_start(self.status_spinner, False, False, 10)
        lstatus_box.pack_start(self.status_bar, False, False, 10)


        # Header bar and top menus
        self.hbar = Gtk.HeaderBar()
        self.hbar.set_show_close_button(True)
        self.win_decor()
        
        self.hbar_button_menu = Gtk.MenuButton()
        self.hbar_button_menu.set_popup(self.main_menu())
        self.hbar_button_menu.set_tooltip_markup(_("""Main Menu"""))
        hbar_button_menu_icon = Gtk.Image.new_from_icon_name('open-menu-symbolic', Gtk.IconSize.BUTTON)
        self.hbar_button_menu.add(hbar_button_menu_icon)         
        self.set_titlebar(self.hbar)

        self.button_new = Gtk.MenuButton()
        self.button_new.set_popup(self.add_menu())
        self.button_new.set_tooltip_markup(_("Add item ..."))
        button_new_icon = Gtk.Image.new_from_icon_name('list-add-symbolic', Gtk.IconSize.BUTTON)
        self.button_new.add(button_new_icon)
        
        self.button_feeds_download   = f_button(None,'rss-symbolic', connect=self.act.on_load_news_all, tooltip=f'<b>{_("Fetch")}</b> {_("news for all Channels")}')
       
        self.button_search = Gtk.MenuButton()
        self.button_search.set_popup(self.new_tab_menu())
        self.button_search.set_tooltip_markup(_("""Open a new tab for Searches..."""))
        button_search_icon = Gtk.Image.new_from_icon_name('edit-find-symbolic', Gtk.IconSize.BUTTON)
        self.button_search.add(button_search_icon)

    

        # Upper notebook stuff 
        self.rules_tab = -1
        self.flags_tab = -1
        self.plugins_tab = -1
        self.learned_tab = -1
        self.catalog_tab = -1
        self.curr_upper = None
        
        self.upper_notebook = Gtk.Notebook()
        self.upper_notebook.set_scrollable(True)
        self.upper_notebook.popup_disable()
        self.upper_nb_last_page = 0

        self.upper_notebook.connect('switch-page', self._on_unb_changed)
        self.upper_notebook.connect('button-release-event', self.tab_menu)





        # entry preview
        prev_images_box = Gtk.ScrolledWindow()
        prev_images_box.set_placement(Gtk.CornerType.TOP_LEFT)
        prev_images_box.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self.prev_images = Gtk.HBox()
        self.prev_images.set_homogeneous(False)
        prev_images_box.add_with_viewport(self.prev_images)

        self.preview_box = Gtk.ScrolledWindow()
        self.preview_box.set_placement(Gtk.CornerType.TOP_LEFT)
        self.preview_box.set_tooltip_markup(_("""Right-Click for more options
Hit <b>Ctrl-F2</b> for Quick Main Menu"""))

        prev_vbox = Gtk.VBox()
        prev_vbox.set_border_width(8)
        prev_vbox.set_homogeneous(False)

        prev_label_hbox = Gtk.HBox()
        prev_label_hbox.set_homogeneous(False)

        self.preview_label = f_label(None, justify=FX_ATTR_JUS_FILL, xalign=0, selectable=True, wrap=True, markup=True)
        self.preview_label.set_halign(0)
        self.preview_label.connect("populate-popup", self._on_right_click_prev)

        prev_label_hbox.pack_start(self.preview_label, False, False, 5)

        prev_vbox.pack_start(prev_images_box, False, False, 5)
        prev_vbox.pack_start(prev_label_hbox, False, False, 5)

        self.preview_box.add_with_viewport(prev_vbox)
        self.prev_box_scrbar = self.preview_box.get_vscrollbar()
        self.prev_box_scrbar.connect('value-changed', self._on_scrbar_changed)
        self.preview_box.connect('size-allocate', self._set_adj)
        #self.preview_label.connect('focus-in-event', self._on_prev_focus)
        #self.preview_label.connect('button-press-event', self._on_prev_clicked)

        # This flag is needed to turn off vadj signal handling when tab changes are made
        self.tab_changing = False


        # Feed section
        self.feed_tab = FeedexFeedTab(self)

        # Build layout        
        self.main_box = Gtk.VBox(homogeneous=False)
        self.setup_layout()

        main_top_box = Gtk.VBox()
        main_top_box.pack_start(self.main_box, True, True, 3)
        main_top_box.pack_start(lstatus_box, False, False, 3)
        self.add(main_top_box)

        self.hbar.pack_start(self.button_feeds_download)
        self.hbar.pack_start(self.button_new)
        self.hbar.pack_start(self.button_search)
        
        self.hbar.pack_end(self.hbar_button_menu)



        self.connect("destroy", self._on_close)
        self.connect("key-press-event", self._on_key_press)

        self.set_default_size(self.gui_cache.get('win_width'), self.gui_cache.get('win_height'))
        if self.gui_cache.get('win_maximized', False): self.maximize()
        
        self.connect('window-state-event', self._on_state_event)
        self.connect('delete-event', self._on_delete_event)



        # Launch startup tabs
        self.add_tab({'type':FX_TAB_PLACES, 'query':FX_PLACE_LAST, 'filters': {}, 'do_search':True})

        for i, tb in enumerate(self.gui_cache.get('tabs',[])):
            if tb in (None, (), []): continue
            self.add_tab({'type':tb.get('type',FX_TAB_SEARCH), 'query':tb.get('phrase',''), 'filters':tb.get('filters',{}), 'title':tb.get('title')})

        self.upper_notebook.set_current_page(0)
 

        # Run onboarding after DB creation
        if self.DB.created: self.add_tab({'type':FX_TAB_CATALOG, 'do_search':True})








#######################################################################################
#
#       Layout 
#

    def setup_layout(self, *args, **kargs):
        """ Sets up layout according to cache data """

        if self.config.get('gui_layout',0) in (1,2):
            self.div_horiz = Gtk.VPaned()
            self.div_vert = Gtk.HPaned()

            if self.config.get('gui_layout',1) == 1:
                self.div_horiz.pack1(self.upper_notebook, resize=True, shrink=True)
                self.div_horiz.pack2(self.preview_box, resize=True, shrink=True)
            else:
                self.div_horiz.pack1(self.preview_box, resize=True, shrink=True)
                self.div_horiz.pack2(self.upper_notebook, resize=True, shrink=True)

            if self.config.get('gui_orientation',0) == 0:
                self.div_vert.pack1(self.feed_tab, resize=True, shrink=True)
                self.div_vert.pack2(self.div_horiz, resize=True, shrink=True)
            else:
                self.div_vert.pack1(self.div_horiz, resize=True, shrink=True)
                self.div_vert.pack2(self.feed_tab, resize=True, shrink=True)

            self.main_box.add(self.div_vert)

            self.div_horiz.set_position(self.gui_cache['div_horiz'])
            self.div_vert.set_position(self.gui_cache['div_vert'])


        else:
            self.div_vert = Gtk.HPaned()
            self.div_vert2 = Gtk.HPaned()
            

            if self.config.get('gui_orientation',0) == 0:

                self.div_vert2.pack1(self.upper_notebook, resize=True, shrink=True)
                self.div_vert2.pack2(self.preview_box, resize=True, shrink=True)

                self.div_vert.pack1(self.feed_tab, resize=True, shrink=True)
                self.div_vert.pack2(self.div_vert2, resize=True, shrink=True)
            
                if self.gui_cache['div_vert'] >= self.gui_cache['div_vert2']:
                    self.gui_cache['div_vert'], self.gui_cache['div_vert2'] = self.gui_cache['div_vert2'], self.gui_cache['div_vert']

            else:

                self.div_vert2.pack1(self.preview_box, resize=True, shrink=True)
                self.div_vert2.pack2(self.upper_notebook, resize=True, shrink=True)
                
                self.div_vert.pack1(self.div_vert2, resize=True, shrink=True)
                self.div_vert.pack2(self.feed_tab, resize=True, shrink=True)

                if self.gui_cache['div_vert2'] >= self.gui_cache['div_vert']:
                    self.gui_cache['div_vert'], self.gui_cache['div_vert2'] = self.gui_cache['div_vert2'], self.gui_cache['div_vert']

            self.main_box.add(self.div_vert)

            self.div_vert.set_position(self.gui_cache['div_vert'])
            self.div_vert2.set_position(self.gui_cache['div_vert2'])






####################################################################################33
#
#       Signals, Time triggers and Events
#



    def _on_close(self, *args):
        self.DB.close()
        self._save_gui_cache()

    def _on_state_event(self, widget, event): self.gui_cache['win_maximized'] = bool(event.new_window_state & Gdk.WindowState.MAXIMIZED)

    def _on_delete_event(self, widget, event):
        win_size = self.get_size()
        self.gui_cache['win_width'] = win_size[0]
        self.gui_cache['win_height'] = win_size[1]


    def _save_gui_cache(self, *args):
        # Last items
        self.gui_cache['new_items'] = self.new_items
        self.gui_cache['new_n'] = self.new_n        

        # Get layout
        self.gui_cache['div_vert'] = self.div_vert.get_position()
        if hasattr(self, 'div_horiz'): self.gui_cache['div_horiz'] = self.div_horiz.get_position()
        if hasattr(self, 'div_vert2'): self.gui_cache['div_vert2'] = self.div_vert2.get_position()

        # Save current tabs
        self.gui_cache['tabs'] = []
            
        for i in range(self.upper_notebook.get_n_pages()):
            if i == 0: continue
            tb = self.upper_notebook.get_nth_page(i)
                
            if not tb.save_to_cache: continue

            if hasattr(tb, 'query_entry'): phrase = tb.query_entry.get_text()
            else: phrase = None
            if hasattr(tb, 'search_filters'):
                tb.get_search_filters()
                search_filters = tb.search_filters
            else: search_filters = {}
            title = tb.header.get_label()

            tab_dc = {'type':tb.type, 'title':title, 'phrase': phrase, 'filters':search_filters}
            self.gui_cache['tabs'].append(tab_dc)

        err = save_json(self.gui_cache_path, self.gui_cache)
        if err == 0: debug(7, 'Saved GUI attributes: ', self.gui_cache)





    def _housekeeping(self): self.DB.clear_cache(self.config.get('gui_clear_cache',30)) 

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

    def _on_timer(self, *kargs):
        """ Check for status updates from threads on time interval  """
        self.sec_frac_counter += 1
        if self.sec_frac_counter > 4:
            self.sec_frac_counter = 0
            self.sec_counter += 1
            
            # Update processing spinner and handle main bus flag chnges
            if fdx.task_counter == 0:
                if self.status_spinner.get_visible():
                    self.status_spinner.stop()
                    self.status_spinner.hide()
            else: 
                if not self.status_spinner.get_visible():
                    self.status_spinner.show()
                    self.status_spinner.start()


        # Fetch news if specified in config
        if self.sec_counter > 60:
            self.sec_counter = 0
            self.minute_counter += 1
            self._time()
            if self.config.get('gui_fetch_periodically', False):
                self.on_load_news_background()


        # Handle signals from main bus
        if len(fdx.bus_q) > 0:
            m = fdx.bus_q[0]
            
            if type(m) is int: code = m
            else: code = m[0]
            
            if code <= 0: 
                mssg = gui_msg(*m)
                self.status_bar.set_markup(mssg)
                self.log_string = f"""{self.log_string}\n{mssg}"""

            elif code == FX_ACTION_RELOAD_FEEDS: self.feed_tab.reload()

            elif code == FX_ACTION_BLOCK_DB:
                self.button_feeds_download.set_sensitive(False)
                self.button_new.set_sensitive(False)
                self.button_search.set_sensitive(False)
                self.hbar_button_menu.set_sensitive(False)
                self.upper_notebook.set_sensitive(False)
                self.feed_tab.set_sensitive(False)
                self.preview_box.set_sensitive(False)

            elif code == FX_ACTION_UNBLOCK_DB:
                self.button_feeds_download.set_sensitive(True)
                self.button_new.set_sensitive(True)
                self.button_search.set_sensitive(True)
                self.hbar_button_menu.set_sensitive(True)
                self.upper_notebook.set_sensitive(True)
                self.feed_tab.set_sensitive(True)
                self.preview_box.set_sensitive(True)

            elif code == FX_ACTION_FINISHED_SEARCH:
                uid = m[1]
                for i in range(self.upper_notebook.get_n_pages()):
                    tb = self.upper_notebook.get_nth_page(i)
                    if tb is None: continue
                    if tb.uid == uid:
                        tb.finish_search()
                        if hasattr(tb, 'query_combo'): self.act.reload_history_all()
                        break

            elif code == FX_ACTION_FINISHED_FILTERING:
                uid = m[1]
                for i in range(self.upper_notebook.get_n_pages()):
                    tb = self.upper_notebook.get_nth_page(i)
                    if tb is None: continue
                    if tb.uid == uid:
                        tb.finish_filtering()
                        break

            elif code == FX_ACTION_HANDLE_IMAGES:
                if self.prev_entry.get('id') == m[1]: 
                    self.handle_images(self.prev_entry.get('id', None), self.prev_entry_links)

            elif code == FX_ACTION_BLOCK_FETCH:
                self.button_feeds_download.set_sensitive(False)
                self.button_new.set_sensitive(False)

            elif code == FX_ACTION_UNBLOCK_FETCH:
                self.button_feeds_download.set_sensitive(True)
                self.button_new.set_sensitive(True)

            else:
                item = m[1]
                tab_types = m[2]
                for i in range(self.upper_notebook.get_n_pages()):
                    tb = self.upper_notebook.get_nth_page(i)
                    if tb is None: continue
                    if tb.type in tab_types: tb.apply(code, item)


            fdx.bus_del(0)


        return True






    def _on_key_press(self, widget, event):
        """ When keyboard is used ... """
        key = event.keyval
        key_name = Gdk.keyval_name(key)
        state = event.state
        ctrl = (state & Gdk.ModifierType.CONTROL_MASK)        
        if ctrl and key_name == self.config.get('gui_key_new_entry','n'): self.act.on_edit_entry(None)
        elif ctrl and key_name == self.config.get('gui_key_new_rule','r'): self.act.on_edit_rule(None)
        elif ctrl and key_name == self.config.get('gui_key_search','s'): 
            if hasattr(self.curr_upper, 'query_entry'): self.curr_upper.query_entry.grab_focus()
            elif hasattr(self.curr_upper, 'search_button'): self.curr_upper.on_query() 
        elif ctrl and key_name in ('F2',): 
            event.button = 3
            self.main_alt_menu(event)
        
        #debug(9, f"""{key_name}; {key}; {state}""")

    def _on_prev_clicked(self, *args): self.tab_changing = True

    def _on_prev_focus(self, *args): 
        self._set_adj()
        self.tab_changing = False


    def _on_scrbar_changed(self, range, *args):
        """ When preview scrollbar changes, save it to a relevant tab not to lose focus later """
        if not self.tab_changing: 
            value = range.get_value()
            self.curr_upper.prev_vadj_val = value




##########################################################################3
#   Menus
#

    def export_menu(self, *args):
        menu = Gtk.Menu()
        menu.append( f_menu_item(1, _('Export Feed data to JSON'), self.act.export_feeds, icon='application-rss+xml-symbolic'))  
        menu.append( f_menu_item(1, _('Export Flags to JSON'), self.act.export_flags, icon='marker-symbolic'))  
        menu.append( f_menu_item(1, _('Export Rules to JSON'), self.act.export_rules, icon='view-list-compact-symbolic'))  
        menu.append( f_menu_item(1, _('Export Plugins to JSON'), self.act.export_plugins, icon='extension-symbolic'))  
        return menu

    def import_menu(self, *args):
        menu = Gtk.Menu()
        menu.append( f_menu_item(1, _('Import Feed data from JSON'), self.act.import_feeds, icon='application-rss+xml-symbolic'))  
        menu.append( f_menu_item(1, _('Import Flags data from JSON'), self.act.import_flags, icon='marker-symbolic'))  
        menu.append( f_menu_item(1, _('Import Rules data from JSON'), self.act.import_rules, icon='view-list-compact-symbolic'))  
        menu.append( f_menu_item(1, _('Import Plugin data from JSON'), self.act.import_plugins, icon='extension-symbolic'))  
        menu.append( f_menu_item(0, 'SEPARATOR', None) )
        menu.append( f_menu_item(1, _('Import Entries from JSON'), self.act.import_entries, icon='document-import-symbolic'))  
        return menu

    def db_menu(self, *args):
        menu = Gtk.Menu()
        menu.append( f_menu_item(1, _('Maintenance...'), self.act.on_maintenance, icon='system-run-symbolic', tooltip=_("""Maintenance can improve performance for large databases by doing cleanup and reindexing.
It will also take some time to perform""") ))  
        menu.append( f_menu_item(0, 'SEPARATOR', None) )
        menu.append( f_menu_item(1, _('Clear cache'), self.act.on_clear_cache, icon='edit-clear-all-symbolic', tooltip=_("""Clear downloaded temporary files with images/thumbnails to reclaim disk space""") ) )
        menu.append( f_menu_item(0, 'SEPARATOR', None) )
        menu.append( f_menu_item(1, _('Unlock fetching'), self.act.on_unlock_fetching, icon='system-lock-screen-symbolic', tooltip=_("""Manually unlock DB for fetching""") ) )
        menu.append( f_menu_item(0, 'SEPARATOR', None) )
        menu.append( f_menu_item(1, _('Database statistics'), self.act.on_show_stats, icon='drive-harddisk-symbolic') )
        return menu

    def log_menu(self, *args):
        menu = Gtk.Menu()
        menu.append( f_menu_item(1, _('View session log'), self.act.on_show_session_log, icon='text-x-generic-symbolic') )
        menu.append( f_menu_item(1, _('View main log'), self.act.on_view_log, icon='text-x-generic-symbolic') )
        return menu


    def main_menu(self, *args):
        menu = Gtk.Menu()
        menu.append( f_menu_item(1, _('Rules'), self.add_tab, kargs={'type':FX_TAB_RULES, 'do_search':True}, icon='view-list-compact-symbolic', tooltip=_('Open a new tab showing Saved Rules') ) )
        menu.append( f_menu_item(1, _('Flags'), self.add_tab, kargs={'type':FX_TAB_FLAGS, 'do_search':True}, icon='marker-symbolic', tooltip=_('Open a new tab showing Flags') ) )
        menu.append( f_menu_item(1, _('Learned Keywords'), self.add_tab, kargs={'type':FX_TAB_LEARNED, 'do_search':True}, icon='applications-engineering-symbolic', tooltip=_('Open a new tab showing Learned Keywords for recommendations') ) )
        menu.append( f_menu_item(0, 'SEPARATOR', None) )
        menu.append( f_menu_item(1, _('Plugins'), self.add_tab, kargs={'type':FX_TAB_PLUGINS, 'do_search':True}, icon='extension-symbolic', tooltip=_('Open a new tab showing Plugins') ) )
        menu.append( f_menu_item(0, 'SEPARATOR', None) )
        menu.append( f_menu_item(1, _('Preferences'), self.act.on_prefs, icon='preferences-system-symbolic') )
        menu.append( f_menu_item(0, 'SEPARATOR', None) )
        menu.append( f_menu_item(3, _('Export...'), self.export_menu(), icon='document-export-symbolic'))
        menu.append( f_menu_item(3, _('Import...'), self.import_menu(), icon='document-import-symbolic'))  
        menu.append( f_menu_item(0, 'SEPARATOR', None) )
        menu.append( f_menu_item(3, _('Database...'), self.db_menu(), icon='drive-harddisk-symbolic') )
        menu.append( f_menu_item(0, 'SEPARATOR', None) )
        menu.append( f_menu_item(3, _('Logs...'), self.log_menu(), icon='text-x-generic-symbolic'))  
        menu.append( f_menu_item(0, 'SEPARATOR', None) )
        menu.append( f_menu_item(1, _('About Feedex...'), self.act.on_show_about, icon='help-about-symbolic') )
        menu.show_all()
        return menu

    def add_menu(self, *args):
        menu = Gtk.Menu()
        menu.append( f_menu_item(1, _('Add Channel from URL'), self.act.on_add_from_url, icon='application-rss+xml-symbolic', tooltip=f'<b>{_("Add Channel")}</b> {_("from URL")}' )  )
        menu.append( f_menu_item(0, 'SEPARATOR', None) )
        menu.append( f_menu_item(1, _('Add Entry'), self.act.on_edit_entry, args=(None,), icon='list-add-symbolic', tooltip=_('Add new Entry') ))   
        menu.show_all()
        return menu




    def new_tab_menu(self, *args, **kargs):
        """ Construct a new tab menu """
        menu = Gtk.Menu()
        menu.append( f_menu_item(1, _('Summary'), self.add_tab, kargs={'type':FX_TAB_TREE}, icon='view-filter-symbolic', tooltip=_('Generate ranked Summary grouped by Category/Channel/Similarity or Dates') ))  
        
        menu.append( f_menu_item(0, 'SEPARATOR', None) )
        menu.append( f_menu_item(1, _('Search'), self.add_tab, kargs={'type':FX_TAB_SEARCH}, icon='edit-find-symbolic', tooltip=_('Search entries') ))  
        menu.append( f_menu_item(1, _('Search (wide view)'), self.add_tab, kargs={'type':FX_TAB_NOTES}, icon='format-unordered-list-symbolic', tooltip=_('Search entries in extended view') ))  
        menu.append( f_menu_item(0, 'SEPARATOR', None) )
        menu.append( f_menu_item(1, _('Show Contexts for a Term'), self.add_tab, kargs={'type':FX_TAB_CONTEXTS}, icon='view-list-symbolic', tooltip=_('Search for Term Contexts') ))  
        menu.append( f_menu_item(1, _('Show Time Series for a Term'), self.add_tab, kargs={'type':FX_TAB_TIME_SERIES, 'filters':{'...-...':True, 'logic':'phrase', 'group':'monthly'}}, icon='histogram-symbolic', tooltip=_('Generate time series plot') ))  
        menu.append( f_menu_item(0, 'SEPARATOR', None) )
        menu.append( f_menu_item(1, _('Trends'), self.add_tab, kargs={'type':FX_TAB_TRENDS}, icon='comment-symbolic', tooltip=_('Show most talked about terms for Articles') ))  
        menu.append( f_menu_item(1, _('Search for Related Terms'), self.add_tab, kargs={'type':FX_TAB_TERM_NET, 'filters':{'...-...':True, 'logic':'phrase'}}, icon='emblem-shared-symbolic', tooltip=_('Search for Related Terms from read/opened entries') ))  
        menu.append( f_menu_item(0, 'SEPARATOR', None) )
        menu.append( f_menu_item(1, _('Find New Feeds'), self.add_tab, kargs={'type':FX_TAB_CATALOG, 'do_search':True, 'filters':{'depth':100, 'field':None} }, icon='rss-symbolic'))  
        menu.show_all()

        return menu
    



    def append_tabs_to_menu(self, menu):
        for i in range(self.upper_notebook.get_n_pages()):
            tb = self.upper_notebook.get_nth_page(i)
            if tb is None: continue
            title = tb.header.get_text()
            menu.append( f_menu_item(1, title, self._on_go_to_upr_page, args=(i,), icon=tb.header_icon_name ) )
        

    
    def tab_menu(self, widget, event, *args, **kargs):
        """ Menu to quick choose tabs """
        if event.button == 3:
            menu = Gtk.Menu()
            new_tab_menu = self.new_tab_menu()
            menu.append( f_menu_item(3, _('New Tab...'), new_tab_menu, icon='tab-new-symbolic') )
            menu.append( f_menu_item(0, 'SEPARATOR', None) )
            self.append_tabs_to_menu(menu)
            menu.show_all()
            menu.popup(None, None, None, None, event.button, event.time)

    def _on_go_to_upr_page(self, *args): self.upper_notebook.set_current_page(args[-1])


 


    def plugin_menu(self, event, tp, item, *args):
        """ Generate menu for running plugins according to given item """
        if type(tp) not in (tuple, list): tp = (tp,)
        av_plugins = []
        for p in self.gui_plugins:
            if p[FX_PLUGIN_TABLE.index('type')] in tp: av_plugins.append(p)
        if len(av_plugins) > 0:
            menu = Gtk.Menu()
            for p in av_plugins:
                menu.append( f_menu_item(1, p[FX_PLUGIN_TABLE.index('name')], self.act.on_run_plugin, args=(p[FX_PLUGIN_TABLE.index('id')], item,), tooltip=scast(p[FX_PLUGIN_TABLE.index('desc')], str, '') ))
            return menu
        else: return None





    def action_menu(self, item, tab, event, **kargs):
        """ Main action menu construction"""
        menu = None
        plugin_filter = []

        if tab.type == FX_TAB_RULES:
            menu = Gtk.Menu()
            if not fdx.db_fetch_lock:
                menu.append( f_menu_item(1, _('Add Rule'), self.act.on_edit_rule, args=(None,), icon='list-add-symbolic') )
        elif tab.type == FX_TAB_FLAGS:
            menu = Gtk.Menu()
            if not fdx.db_fetch_lock:
                menu.append( f_menu_item(1, _('Add Flag'), self.act.on_edit_flag, args=(None,), icon='list-add-symbolic') )
        elif tab.type == FX_TAB_PLUGINS:
            menu = Gtk.Menu()
            menu.append( f_menu_item(1, _('Add Plugin'), self.act.on_edit_plugin, args=(None,), icon='list-add-symbolic') )
        elif tab.type in (FX_TAB_CONTEXTS, FX_TAB_SEARCH, FX_TAB_NOTES, FX_TAB_TREE, FX_TAB_SIMILAR,) or (tab.type == FX_TAB_PLACES and self.curr_place != FX_PLACE_TRASH_BIN):
            menu = Gtk.Menu()
            menu.append( f_menu_item(1, _('Add Entry'), self.act.on_edit_entry, args=(None,), icon='list-add-symbolic') )
            if tab.table.result_no > 0: plugin_filter.append(FX_PLUGIN_RESULTS)
        elif tab.type not in (FX_TAB_FEEDS,):
            if tab.table.result_no > 0: plugin_filter.append(FX_PLUGIN_RESULTS)




        if isinstance(item, (ResultEntry, ResultContext,)):
            
            if menu is None: menu = Gtk.Menu()
            else: menu.append( f_menu_item(0, 'SEPARATOR', None) )
            
            if coalesce(item.get('is_deleted'),0) == 0:
                mark_menu = Gtk.Menu()
                mark_menu.append( f_menu_item(1, _('Read (+1)'), self.act.on_mark, args=('read', item,), icon='bookmark-new-symbolic', tooltip=_("Number of reads if counted towards this entry keyword's weight when ranking incoming articles") ) )
                mark_menu.append( f_menu_item(1, _('Read (+5)'), self.act.on_mark, args=('read+5', item,), icon='bookmark-new-symbolic', tooltip=_("Number of reads if counted towards this entry keyword's weight when ranking incoming articles") ) )
                mark_menu.append( f_menu_item(0, 'SEPARATOR', None) )
                mark_menu.append( f_menu_item(1, _('Unread'), self.act.on_mark, args=('unread', item,), icon='edit-redo-rtl-symbolic', tooltip=_("Unread document does not contriute to ranking rules") ) )
                menu.append( f_menu_item(3, _('Mark as...'), mark_menu, icon='bookmark-new-symbolic') )

                flag_menu = Gtk.Menu()
                for fl, v in fdx.flags_cache.items():
                    fl_name = esc_mu(v[0])
                    fl_color = v[2]
                    fl_desc = esc_mu(v[1])
                    if fl_color in (None, ''): fl_color = self.config.get('gui_default_flag_color','blue')
                    if fl_name in (None, ''): fl_name = f'{_("Flag")} {fl}'
                    flag_menu.append( f_menu_item(1, fl_name, self.act.on_mark, args=(fl, item,), color=fl_color, icon='marker-symbolic', tooltip=fl_desc) )
                flag_menu.append( f_menu_item(1, _('Unflag Entry'), self.act.on_mark, args=('unflag', item,), icon='edit-redo-rtl-symbolic', tooltip=_("Remove Flags from Entry") ) )
                flag_menu.append( f_menu_item(0, 'SEPARATOR', None) )
                flag_menu.append( f_menu_item(1, _('Show Flags...'), self.add_tab, kargs={'type':FX_TAB_FLAGS, 'do_search':True}, icon='marker-symbolic', tooltip=_('Open a new tab showing Flags') ) )
                menu.append( f_menu_item(3, _('Flag as...'), flag_menu, icon='marker-symbolic', tooltip=f"""{_("Flag is a user's marker/bookmark for a given article independent of ranking")}\n<i>{_("You can setup different flag colors in Preferences")}</i>""") )
                
                menu.append( f_menu_item(1, _('Edit Entry'), self.act.on_edit_entry, args=(item,), icon='edit-symbolic') )
                menu.append( f_menu_item(1, _('Delete'), self.act.on_del_entry, args=(item,), icon='edit-delete-symbolic') )

            elif coalesce(item.get('is_deleted'),0) > 0:
                menu.append( f_menu_item(1, _('Restore'), self.act.on_restore_entry, args=(item,), icon='edit-redo-rtl-symbolic') )
                menu.append( f_menu_item(1, _('Delete permanently'), self.act.on_del_entry, args=(item,), icon='edit-delete-symbolic') )

            menu.append( f_menu_item(0, 'SEPARATOR', None) )

            search_menu = Gtk.Menu()
            search_menu.append( f_menu_item(1, _('Find Similar Entries...'), self.add_tab,  kargs={'type':FX_TAB_SIMILAR, 'top_entry':item, 'filters':{'...-...': True, 'depth':50}, 'do_search':True}, icon='emblem-shared-symbolic', tooltip=_("Find Entries similar to the one selected") ) )
            search_menu.append( f_menu_item(1, _('Show Time Relevance...'), self.add_tab, kargs={'type':FX_TAB_REL_TIME, 'filters': {'...-...':True, 'group':'monthly'}, 'top_entry': item}, icon='histogram-symbolic', tooltip=_("Search for this Entry's Keywords in time") ) )

            if item['author'] not in (None, ''):
                author_menu = Gtk.Menu()
                author_menu.append( f_menu_item(1, _('Articles'), self.add_tab, kargs={'type':FX_TAB_SEARCH, 'filters': {'field':'author', '...-...':True, 'logic':'phrase'}, 'query': item['author']}, icon='edit-find-symbolic', tooltip=_("Search for other documents by this Author") ) )
                author_menu.append( f_menu_item(1, _('Activity in Time'), self.add_tab, kargs={'type':FX_TAB_TIME_SERIES, 'filters': {'field':'author', '...-...':True, 'logic':'phrase', 'group':'monthly'}, 'query': item['author']}, icon='histogram-symbolic', tooltip=_("Search for other documents by this Author in Time Series") ) )
                author_menu.append( f_menu_item(0, 'SEPARATOR', None) )
                author_menu.append( f_menu_item(1, _('Search WWW'), self._on_www_search_auth, args=(item['author'],), icon='www-symbolic', tooltip=_("Search WWW for this Author's info") ) )
                search_menu.append( f_menu_item(3, _('Other by this Author...'), author_menu, icon='community-symbolic', tooltip=_("Search for this Author") ) )

            menu.append( f_menu_item(3, _('Search...'), search_menu, icon='emblem-shared-symbolic') ) 
            menu.append( f_menu_item(0, 'SEPARATOR', None) )

            plugin_filter.append(FX_PLUGIN_ENTRY)
            plugin_filter.append(FX_PLUGIN_RESULT)        
            




        elif isinstance(item, ResultRule):
            
            if menu is None: menu = Gtk.Menu()
            else: menu.append( f_menu_item(0, 'SEPARATOR', None) )

            if item['id'] is not None:
                if not fdx.db_fetch_lock:
                    menu.append( f_menu_item(1, _('Edit Rule'), self.act.on_edit_rule, args=(item,), icon='edit-symbolic') )
                    menu.append( f_menu_item(1, _('Delete Rule'), self.act.on_del_rule, args=(item,), icon='edit-delete-symbolic') )
                    menu.append( f_menu_item(0, 'SEPARATOR', None) )
                menu.append( f_menu_item(1, _('Search for this Rule'), self.add_tab, kargs={'type':FX_TAB_SEARCH, 'query':item['string'], 'filters':{'qtype':item['type'], 'case_ins':item['case_insensitive']}}, icon='edit-find-symbolic'))  
                menu.append( f_menu_item(1, _('Show this Rule\'s Contexts'), self.add_tab, kargs={'type':FX_TAB_CONTEXTS, 'query':item['string'], 'filters':{'qtype':item['type'], 'case_ins':item['case_insensitive']}}, icon='view-list-symbolic'))  
                menu.append( f_menu_item(1, _('Show Terms related to this Rule'), self.add_tab, kargs={'type':FX_TAB_TERM_NET, 'query':item['string'], 'filters':{'...-...':True, 'logic':'phrase'} }, icon='emblem-shared-symbolic'))  
                menu.append( f_menu_item(1, _('Show Time Series for this Rule'), self.add_tab, kargs={'type':FX_TAB_TIME_SERIES, 'query':item['string'], 'filters': {'qtype':item['type'], 'case_ins':item['case_insensitive'], '...-...':True, 'group':'monthly'}}, icon='histogram-symbolic'))  
            





        elif isinstance(item, ResultTerm):
            
            if menu is None: menu = Gtk.Menu()
            else: menu.append( f_menu_item(0, 'SEPARATOR', None) )

            if item['term'] not in (None, ''):
                menu.append( f_menu_item(1, _('Search for this Term'), self.add_tab, kargs={'type':FX_TAB_SEARCH, 'query':item['term']}, icon='edit-find-symbolic'))  
                menu.append( f_menu_item(1, _('Show this Term\'s Contexts'), self.add_tab, kargs={'type':FX_TAB_CONTEXTS, 'query':item['term']}, icon='view-list-symbolic'))  
                menu.append( f_menu_item(1, _('Show Terms related to this Term'), self.add_tab, kargs={'type':FX_TAB_TERM_NET, 'query':item['term'], 'filters':{'...-...':True, 'logic':'phrase'}}, icon='emblem-shared-symbolic'))  
                menu.append( f_menu_item(1, _('Show Time Series for this Term'), self.add_tab, kargs={'type':FX_TAB_TIME_SERIES, 'query':item['term'], 'filters':{'...-...':True, 'logic':'phrase', 'group':'monthly'}}, icon='histogram-symbolic'))  
            plugin_filter.append(FX_PLUGIN_RESULT)





        elif isinstance(item, ResultTimeSeries):

            if menu is None: menu = Gtk.Menu()
            else: menu.append( f_menu_item(0, 'SEPARATOR', None) )

            if item['time'] not in (None, ()):
                menu.append( f_menu_item(1, _('Search this Time Range'), self.add_tab, kargs={'type':FX_TAB_SEARCH, 'filters':{'date_from':item['from'], 'date_to':item['to']}}, icon='edit-find-symbolic'))  
            plugin_filter.append(FX_PLUGIN_RESULT)




        elif isinstance(item, ResultFlag):
        
            if menu is None: menu = Gtk.Menu()
            else: menu.append( f_menu_item(0, 'SEPARATOR', None) )

            if item['id'] is not None:
                if not fdx.db_fetch_lock:
                    menu.append( f_menu_item(1, _('Edit Flag'), self.act.on_edit_flag, args=(item,), icon='edit-symbolic') )
                    menu.append( f_menu_item(1, _('Delete Flag'), self.act.on_del_flag, args=(item,), icon='edit-delete-symbolic') )
                    menu.append( f_menu_item(0, 'SEPARATOR', None) )
                menu.append( f_menu_item(1, _('Search for this Flag'), self.add_tab, kargs={'type':FX_TAB_SEARCH, 'filters':{'flag':item['id']}}, icon='edit-find-symbolic'))  
                menu.append( f_menu_item(1, _('Time Series search for this Flag'), self.add_tab, kargs={'type':FX_TAB_TIME_SERIES, 'filters':{'flag':item['id']}}, icon='histogram-symbolic'))  



        elif isinstance(item, ResultPlugin):

            if menu is None: menu = Gtk.Menu()
            else: menu.append( f_menu_item(0, 'SEPARATOR', None) )

            if item['id'] is not None:
                menu.append( f_menu_item(1, _('Edit Plugin'), self.act.on_edit_plugin, args=(item,), icon='edit-symbolic') )
                menu.append( f_menu_item(1, _('Delete Plugin'), self.act.on_del_plugin, args=(item,), icon='edit-delete-symbolic') )



        elif isinstance(item, ResultCatItem):

            if menu is None: menu = Gtk.Menu()
            else: menu.append( f_menu_item(0, 'SEPARATOR', None) )

            if item['id'] is not None:
                menu.append( f_menu_item(1, _('Visit Homepage'), self.act.on_go_home, args=(item,), icon='user-home-symbolic') )



        elif isinstance(item, ResultFeed):

            if menu is None: menu = Gtk.Menu()
            else: menu.append( f_menu_item(0, 'SEPARATOR', None) )

            if coalesce(item['deleted'],0) == 0:
                menu.append( f_menu_item(1, _('Show from newest...'), self.add_tab, kargs={'type':FX_TAB_SEARCH, 'do_search':True, 'filters':{'feed_or_cat':item['id'], '...-...':True, 'rank':FX_RANK_LATEST}}, icon='edit-find-symbolic', tooltip=_("Show articles for this Channel or Category sorted from newest") ) )
                menu.append( f_menu_item(1, _('Show from newest (wide view)...'), self.add_tab, kargs={'type':FX_TAB_NOTES, 'do_search':True, 'filters':{'feed_or_cat':item['id'], '...-...':True, 'rank':FX_RANK_LATEST}}, icon='format-unordered-list-symbolic', tooltip=_("Show articles sorted from newest in an extended view") ) )
                menu.append( f_menu_item(1, _('Summary...'), self.add_tab, kargs={'type':FX_TAB_TREE, 'do_search':True, 'filters':{'feed_or_cat':item['id'], 'last':True, 'group':'daily', 'rank':FX_RANK_TREND}}, icon='view-filter-symbolic', tooltip=_("Show item's Summary Tree ranked by Trends") ) )

                if not fdx.db_fetch_lock and tab.type == FX_TAB_FEEDS:
                    menu.append( f_menu_item(0, 'SEPARATOR', None) )
                    menu.append( f_menu_item(1, _('Add Channel'), self.act.on_feed_cat, args=('new_channel', None), icon='list-add-symbolic') )
                    menu.append( f_menu_item(1, _('Add Category'), self.act.on_feed_cat, args=('new_category', None), icon='folder-new-symbolic') )
                    
                    menu.append( f_menu_item(0, 'SEPARATOR', None) )
                    if item['is_category'] == 1: menu.append( f_menu_item(1, _('Move Category...'), self.feed_tab.copy_feed, icon='edit-cut-symbolic') ) 
                    else: menu.append( f_menu_item(1, _('Move Feed...'), self.feed_tab.copy_feed, icon='edit-cut-symbolic') ) 
                    
                    if not fdx.db_fetch_lock and self.feed_tab.copy_selected.get('id') is not None:
                        if self.feed_tab.copy_selected['is_category'] == 1:
                            if item['is_category'] == 1:
                                menu.append( f_menu_item(1, f'{_("Insert")} {esc_mu(self.feed_tab.copy_selected.get("name",""))} {_("here ...")}', self.feed_tab.insert_feed, args=(item,), icon='edit-paste-symbolic') )
                        else:
                            if item['is_category'] == 1:
                                menu.append( f_menu_item(1, f'{_("Assign")} {esc_mu(self.feed_tab.copy_selected.get("name",""))} {_("here ...")}', self.feed_tab.insert_feed, args=(item,), icon='edit-paste-symbolic') ) 
                            else:
                                menu.append( f_menu_item(1, f'{_("Insert")} {esc_mu(self.feed_tab.copy_selected.get("name",""))} {_("here ...")}', self.feed_tab.insert_feed, args=(item,), icon='edit-paste-symbolic') )
                

                if item['is_category'] != 1:
                    menu.append( f_menu_item(1, _('Go to Channel\'s Homepage'), self.act.on_go_home, args=(item,), icon='user-home-symbolic') )
        
                    if not fdx.db_fetch_lock:
                        menu.append( f_menu_item(0, 'SEPARATOR', None) )
                        menu.append( f_menu_item(1, _('Fetch from selected Channel'), self.act.on_load_news_feed, args=(item,), icon='rss-symbolic') )
                        menu.append( f_menu_item(1, _('Update metadata for Channel'), self.act.on_update_feed, args=(item,), icon='system-run-symbolic') )
                        menu.append( f_menu_item(1, _('Update metadata for All Channels'), self.act.on_update_feed_all, icon='system-run-symbolic') )
                        menu.append( f_menu_item(0, 'SEPARATOR', None) )

                        menu.append( f_menu_item(1, _('Edit Channel'), self.act.on_feed_cat, args=('edit', item,), icon='edit-symbolic') )
                        menu.append( f_menu_item(1, _('Mark Channel as healthy'), self.act.on_mark_healthy, args=(item,), icon='go-jump-rtl-symbolic', tooltip=_("This will nullify error count for this Channel so it will not be ommited on next fetching") ) )
                        menu.append( f_menu_item(0, 'SEPARATOR', None) )
                        menu.append( f_menu_item(1, _('Remove Channel'), self.act.on_del_feed, args=(item,), icon='edit-delete-symbolic') )
                        if fdx.debug_level not in (0, None): 
                            menu.append( f_menu_item(0, 'SEPARATOR', None) )
                            menu.append( f_menu_item(1, _('Technical details...'), self.act.on_show_detailed, args=('feed', item,), icon='zoom-in-symbolic', tooltip=_("Show all technical information about this Channel") ) )

                    plugin_filter.append(FX_PLUGIN_FEED)

                elif not fdx.db_fetch_lock:
                    menu.append( f_menu_item(1, _('Edit Category'), self.act.on_feed_cat, args=('edit',item,), icon='edit-symbolic') )
                    menu.append( f_menu_item(1, _('Remove Category'), self.act.on_del_feed, args=(item,), icon='edit-delete-symbolic') )

                    plugin_filter.append(FX_PLUGIN_CATEGORY)


            elif (not fdx.db_fetch_lock) and item['deleted'] == 1 and tab.type == FX_TAB_FEEDS:
                menu.append( f_menu_item(1, _('Restore...'), self.act.on_restore_feed, args=(item,), icon='edit-redo-rtl-symbolic') )
                menu.append( f_menu_item(1, _('Remove Permanently'), self.act.on_del_feed, args=(item,), icon='edit-delete-symbolic') )





        if ( (isinstance(item, SQLContainer) and coalesce(item['deleted'],0) > 0 ) or \
            (self.curr_place == FX_PLACE_TRASH_BIN and self.curr_upper.type == FX_TAB_PLACES)) and not fdx.db_fetch_lock:
            
            if menu is None: menu = Gtk.Menu()
            else: menu.append( f_menu_item(0, 'SEPARATOR', None) )
            menu.append( f_menu_item(1, _('Empty Trash'), self.act.on_empty_trash, icon='edit-delete-symbolic') )

        else:
            
            if tab.type == FX_TAB_LEARNED and not fdx.db_fetch_lock:
                if menu is None: menu = Gtk.Menu()
                else: menu.append( f_menu_item(0, 'SEPARATOR', None) )
                menu.append( f_menu_item(1, _('Delete Learned Keywords'), self.act.del_learned_keywords, icon='dialog-warning-symbolic', tooltip=_('Remove all learned rules from database. Be careful!') ) )
                menu.append( f_menu_item(1, _('Relearn All Keywords'), self.act.relearn_keywords, icon='applications-engineering-symbolic', tooltip=_('Relearn rules from all read/marked items') ) )


            if tab.type not in (FX_TAB_FEEDS, FX_TAB_RULES, FX_TAB_FLAGS, FX_TAB_PLUGINS,) and tab.table.result_no > 0:
                port_menu = Gtk.Menu()
                port_menu.append( f_menu_item(1, _('Save results to CSV'), self.act.export_results, args=('csv',), icon='x-office-spreadsheet-symbolic', tooltip=_('Save results from current tab') ))  
                port_menu.append( f_menu_item(1, _('Export results to JSON'), self.act.export_results, args=('json_dict',), icon='document-export-symbolic', tooltip=_('Export results from current tab') ))  
            
                menu.append( f_menu_item(0, 'SEPARATOR', None) )
                menu.append( f_menu_item(3, _('Export...'), port_menu, icon='document-export-symbolic') )

            pl_menu = self.plugin_menu(event, plugin_filter, item)
            if pl_menu is not None: 
                if menu is None: menu = Gtk.Menu()
                else: menu.append( f_menu_item(0, 'SEPARATOR', None) )
                menu.append( f_menu_item(3, _('Plugins...'), pl_menu, icon='extension-symbolic') )


            if tab.type not in (FX_TAB_FEEDS,) and tab.table.result_no > 0:
                if tab.table.is_tree:
                    menu.append( f_menu_item(0, 'SEPARATOR', None) )
                    menu.append( f_menu_item(1, _('Expand all'), tab.table.expand_all, icon='list-add-symbolic'))  
                    menu.append( f_menu_item(1, _('Collapse all'), tab.table.collapse_all, icon='list-remove-symbolic'))  
                    if tab.type == FX_TAB_CATALOG:
                        menu.append( f_menu_item(0, 'SEPARATOR', None) )
                        menu.append( f_menu_item(1, _('Untoggle all'), tab.table.untoggle_all, icon='list-remove-symbolic'))  


        if tab.type not in (FX_TAB_FEEDS,):
            if menu is None: menu = Gtk.Menu()
            else: menu.append( f_menu_item(0, 'SEPARATOR', None) )
            menu.append( f_menu_item(1, _('Save layout'), tab.table.save_layout, icon='view-column-symbolic', tooltip=_('Save column layout and sizing for current tab.\nIt will be used as default in the future') ) )
            if hasattr(tab, 'search_filter_box'): menu.append( f_menu_item(1, _('Save filters'), tab.save_filters, icon='filter-symbolic', tooltip=_('Save current search filters as defaults for future') ) )

        if menu is not None:
            menu.show_all()
            menu.popup(None, None, None, None, event.button, event.time)





    def _on_right_click_prev(self, widget, menu, *args, **kargs):
        """ Add some option to the popup menu of preview box """
        if self.prev_entry == {}: return 0
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
        menu.append( f_menu_item(0, 'SEPARATOR', None) )
        menu.append( f_menu_item(1, _('Show Details...'), self._on_show_details, icon='system-run-symbolic')) 
        if fdx.debug_level not in (0, None):
            entry = ResultEntry()
            entry.strict_merge(self.prev_entry) 
            menu.append( f_menu_item(0, 'SEPARATOR', None) )
            menu.append( f_menu_item(1, _('Technical details...'), self.act.on_show_detailed, args=('entry', entry,), icon='system-run-symbolic', tooltip=_("Show all entry's technical data") ) )
        
        if not (selection == () or len(selection) != 3):
            text = widget.get_text()
            selection_text = scast(text[selection[1]:selection[2]], str, '')
            debug(7, f'Selected text: {selection_text}')
            if selection_text != '':
                menu.append( f_menu_item(0, 'SEPARATOR', None) )
                menu.append( f_menu_item(1, _('Search for this Term'), self.add_tab, kargs={'type':FX_TAB_SEARCH, 'query':selection_text}, icon='edit-find-symbolic'))  
                menu.append( f_menu_item(1, _('Show this Term\'s Contexts'), self.add_tab, kargs={'type':FX_TAB_CONTEXTS, 'query':selection_text}, icon='view-list-symbolic'))  
                menu.append( f_menu_item(1, _('Show Terms related to this Term'), self.add_tab, kargs={'type':FX_TAB_TERM_NET, 'query':selection_text}, icon='emblem-shared-symbolic'))  
                menu.append( f_menu_item(1, _('Show Time Series for this Term'), self.add_tab, kargs={'type':FX_TAB_TIME_SERIES, 'query':selection_text}, icon='office-calendar-symbolic'))  
                menu.append( f_menu_item(0, 'SEPARATOR', None) )
                menu.append( f_menu_item(1, _('Search WWW'), self._on_www_search_sel, args=(selection_text,), icon='www-symbolic', tooltip=_("Search WWW for selected text") ) )
                menu.append( f_menu_item(0, 'SEPARATOR', None) )
                menu.append( f_menu_item(1, _('Add as Rule'), self._on_add_sel_as_rule, args=(selection_text,), icon='view-list-compact-symbolic'))  

                pl_menu = self.plugin_menu(None, FX_PLUGIN_SELECTION, selection_text)
                if pl_menu is not None: 
                    menu.append( f_menu_item(0, 'SEPARATOR', None) )
                    menu.append( f_menu_item(3, _('Plugins...'), pl_menu, icon='extension-symbolic') )

        menu.show_all()





    def main_alt_menu(self, event, **kargs):
        """ Generate Alternative menu for all general options (to run from keyboard only)"""
        menu = Gtk.Menu()

        tab_menu = Gtk.Menu()
        self.append_tabs_to_menu(tab_menu)

        menu.append( f_menu_item(3, _('Go to Tab...'), tab_menu, icon='tab-symbolic') )
        menu.append( f_menu_item(3, _('New Tab...'), self.new_tab_menu(), icon='tab-new-symbolic') )
        menu.append( f_menu_item(3, _('Add...'), self.add_menu(), icon='list-add-symbolic') )
        menu.append( f_menu_item(0, 'SEPARATOR', None) )
        menu.append( f_menu_item(1, _('Fetch...'), self.act.on_load_news_all, icon='rss-symbolic', tooltip=f'<b>{_("Fetch")}</b> {_("news for all Channels")}' )  )
        menu.append( f_menu_item(0, 'SEPARATOR', None) )
        menu.append( f_menu_item(3, _('System...'), self.main_menu(), icon='preferences-system-symbolic') )

        menu.show_all()
        menu.popup(None, None, None, None, event.button, event.time)





    def _on_summarize(self, *args):
        self.DB.LP.summarize_entry(self.prev_entry, args[-1].get('level',0), separator=" (...) \n\n (...) ")
        self.load_preview(self.prev_entry)


    def _on_www_search_auth(self, *args): fdx.ext_open('search_engine', args[-1])
    def _on_www_search_sel(self, *args): fdx.ext_open('search_engine', args[-1])

    def _on_add_sel_as_rule(self, *args):
        """ Adds selected phrase to rules (dialog)"""
        self.new_rule['string'] = args[-1]
        self.new_rule['name'] = args[-1]
        self.act.on_edit_rule(None)

    def _on_show_details(self, *args, **kargs):
        """ Denerate detail string for entry preview """
        entry = FeedexEntry(self.DB, id=self.prev_entry.get('id',-1))
        if not entry.exists: return 0
        
        disp_str = ''

        entry.ling(index=False, rank=False, learn=True, save_terms=False)
        kwd_str = ''
        for k in entry.terms: kwd_str = f"""{kwd_str}{esc_mu(k['form'])} (<i>{round(k['weight'],3)}</i>); """

        if kwd_str != '': disp_str = f"""{disp_str}
------------------------------------------------------------------------------------------------------------
<b>{_('Keywords')}:</b> {kwd_str}
"""
        
        importance, flag, flag_dist, results = entry.ling(index=False, rank=True, to_disp=True)
        if len(results) > 0:        
            rule = ResultRule()
            rule_str = ''
            for r in results:
                rule.populate(r)
                rule_str = f"""{rule_str}
<span foreground="{fdx.get_flag_color(rule.get('flag',0))}"><b>{esc_mu(rule.name())}</b></span> ({_('Matched:')}<b>x{rule['matched']}</b>, {_('Weight:')} <b>{rule['weight']:.4f}</b>, {_('Flag:')} <b>{esc_mu(fdx.get_flag_name(rule['flag']))}</b>)"""
            disp_str = f"""{disp_str}
------------------------------------------------------------------------------------------------------------
<b>{_('Matched rules')}:</b>
{rule_str}


{_('Calculated Importance:')} <b>{importance:.3f}</b>, {_('Calculated Flag:')} <b>{flag:.0f}</b>
{_('Boost from matched rules:')} <b>{entry.vals['weight']:.3f}</b>
--------------------------------------------------------------------------------------------------------
<b>{_('Flag distriution:')}</b>"""

            for f,v in flag_dist.items(): disp_str = f"""{disp_str} <span foreground="{fdx.get_flag_color(f)}"><b>{fdx.get_flag_name(f)} ({f})</b>:</span> {v:.3f}"""

            disp_str = f"""{disp_str}
    
"""

        self.load_preview(entry, details=disp_str)
        adj = self.prev_box_scrbar.get_adjustment()
        adj.set_value(99999999999999)




###########################################################
#
#       Tab Handling
#

    def add_tab(self, *args):
        """ Deal with adding tabs and requesting initial queries if required. Accepts args as a dictionary """
        kargs = args[-1]
        tp = kargs.get('type', FX_TAB_SEARCH)
        filters = kargs.get('filters')
        query = kargs.get('query')
        do_search = kargs.get('do_search', False)
        top_entry = kargs.get('top_entry')

        # Keep track of which tab contains rules and just show the tab if exists
        if tp == FX_TAB_RULES and self.rules_tab != -1:
            self._show_upn_page(self.rules_tab)
            return 0
        # ... and Flags ...
        if tp == FX_TAB_FLAGS and self.flags_tab != -1:
            self._show_upn_page(self.flags_tab)
            return 0
        # ... and Plugins ...
        if tp == FX_TAB_PLUGINS and self.plugins_tab != -1:
            self._show_upn_page(self.plugins_tab)
            return 0        
        # ... and learnde rules ...
        if tp == FX_TAB_LEARNED and self.learned_tab != -1:
            self._show_upn_page(self.learned_tab)
            return 0
        # ... and learnde rules ...
        if tp == FX_TAB_CATALOG and self.catalog_tab != -1:
            self._show_upn_page(self.catalog_tab)
            return 0
    


        tab = FeedexTab(self, type=tp, title=kargs.get('title',''), top_entry=top_entry)
        if filters is not None: tab.on_restore(filters=filters)
        if query is not None and type(query) is str and hasattr(tab, 'query_entry'): tab.query_entry.set_text(query)
        
        self.upper_notebook.append_page(tab, tab.header_box)
        self.upper_notebook.set_tab_reorderable(tab, True)        
        tab.header_box.show_all()

        # Save rule, flag, plugins tab IDs
        if tp == FX_TAB_RULES: 
            self.rules_tab = tab.uid
            do_search = True
        elif tp == FX_TAB_FLAGS:
            self.flags_tab = tab.uid
            do_search = True
        elif tp == FX_TAB_PLUGINS:
            self.plugins_tab = tab.uid
            do_search = True
        elif tp == FX_TAB_LEARNED:
            self.learned_tab = tab.uid
            do_search = True
        elif tp == FX_TAB_CATALOG:
            self.catalog_tab = tab.uid
            do_search = True


        # Launching search directly upon creation
        if do_search: 
            if type(query) is int: tab.query(query, filters)
            else: tab.on_query()

        self.upper_notebook.show_all()
        self.curr_upper = tab

        self._show_upn_page(tab.uid)

        if hasattr(tab, 'query_entry'): tab.query_entry.grab_focus()





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
        elif type == FX_TAB_PLUGINS: self.plugins_tab = -1
        elif type == FX_TAB_LEARNED: self.learned_tab = -1
        elif type == FX_TAB_CATALOG: self.catalog_tab = -1

        i = self._get_upn_page(uid)
        if i >= 0: self.upper_notebook.remove_page(i) 




    def _set_adj(self, *args):
        adj = self.prev_box_scrbar.get_adjustment()
        adj.set_value(self.curr_upper.prev_vadj_val)
        


    def _on_unb_changed(self, *args):
        """ Action on changing upper tab """    

        self.tab_changing = True

        self.curr_upper = self.upper_notebook.get_nth_page(args[-1])
        if self.curr_upper is None: return -1

        if isinstance(self.curr_upper.table.result, (ResultEntry, ResultContext, FeedexEntry,)): 
            self.feed_tab.redecorate(self.curr_upper.table.curr_feed_filters,  self.curr_upper.table.feed_sums)
        else: 
            self.feed_tab.redecorate((), {})

        if self.curr_upper.top_entry_prev: self.load_preview(self.curr_upper.top_entry)
        elif isinstance(self.curr_upper.table.result, (ResultEntry, ResultContext, ResultRule, ResultCatItem,)): self.curr_upper._on_changed_selection()
        else: self.startup_decor()

        self._set_adj()
        self.tab_changing = False





####################################################
#
#       Entry Preview
#




    def load_preview(self, result, *args, **kargs):
        """ Generates result preview when result cursor changes """
        adj = self.preview_box.get_vadjustment()
        adj.set_value(0)

        self.prev_entry = result.copy()
        self.curr_prev = FX_PREV_ENTRY

        title = esc_mu(result.get("title",''))
        author = esc_mu(result.get('author',''))
        publisher = esc_mu(result.get('publisher',''))
        contributors = esc_mu(result.get('contributors',''))
        category = esc_mu(result.get('category',''))

        desc = result.get("desc",'')
        desc = esc_mu(desc)

        text = result.get("text",'')
        text = esc_mu(text)


        # Hilight query using snippets
        col = self.config.get('gui_hilight_color','blue')
        snip_str = ''
        snips = scast(result.get('snippets'), tuple, ())
        if snips == (): snips = scast(result.get('context'), tuple, ())
        if snips != ():
            snip_str = f"""\n\n{_('Snippets:')}\n<small>----------------------------------------------------------</small>\n"""
            srch_str = []
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

        
        self.prev_entry_links = []
        link_list = []
        link_text = ''
        links = [scast(result.get('link'), str, '')] + \
                            scast(result.get('links'), str, '').splitlines() + \
                            scast(result.get('enclosures'), str, '').splitlines()

        if len(links) > 0 and links != ['']:
            for i,l in enumerate(links):
                if i != 0: self.prev_entry_links.append(l)
                if l in link_list: continue
                link_list.append(l)
                l_text = l.replace('<','').replace('>','')
                if l_text.endswith('/'): l_label = slist(l_text.split('/'), -2, l_text)
                else: l_label = slist(l_text.split('/'), -1, l_text)
                l_label = ellipsize(    l_label, 75)
                l_text = esc_mu(l_text)
                l_label = esc_mu(l_label)
                link_text = f"""{link_text}
<a href="{l_text}" title="{_('Click to open link')}: <b>{l_text}</b>">{l_label}</a>"""
        
            link_text = f"\n\n{_('Links:')}\n{link_text}"

        for il in scast(result.get('images'), str, '').splitlines(): self.prev_entry_links.append(il)

        if kargs.get('details') is not None: footer = f"""{kargs.get('details')}"""
        else: footer = ''

        stat_str = f"""{snip_str}\n\n<small>-------------------------------------\n{_("Word count")}: <b>{result['word_count']}</b>
{_("Character count")}: <b>{result['char_count']}</b>
{_("Sentence count")}: <b>{result['sent_count']}</b>
{_("Capitalized word count")}: <b>{result['caps_count']}</b>
{_("Common word count")}: <b>{result['com_word_count']}</b>
{_("Polysyllable count")}: <b>{result['polysyl_count']}</b>
{_("Numeral count")}: <b>{result['numerals_count']}</b>\n
{_("Importance")}: <b>{round(scast(result['importance'],float,0),3)}</b>
{_("Weight")}: <b>{round(scast(result['weight'],float,0),3)}</b>
{_("Readability")}: <b>{round(scast(result['readability'],float,0),3)}</b></small>\n"""

        if author != '' or publisher != '' or contributors != '': author_section = f"""

<i>{author} {publisher} {contributors}</i>        
"""
        else: author_section = ''

        if category != '': category = f"""

{category}
"""
        self.preview_label.set_line_wrap(True)
        self.preview_label.set_markup(f"""
<b>{title}</b>{author_section}{category}

{desc}

{text}

{link_text}

{footer}
{stat_str}
""")

        self.handle_images(result.get('id', None), self.prev_entry_links)










    def load_preview_rule(self, result, *args, **kargs):
        """ Load a rule into preview window """
        adj = self.preview_box.get_vadjustment()
        adj.set_value(0)

        self.prev_entry = {}

        if self.curr_prev != FX_PREV_RULE:
            for c in self.prev_images.get_children(): self.prev_images.remove(c)
            image = Gtk.Image.new_from_icon_name('system-run-symbolic', Gtk.IconSize.DIALOG)
            self.prev_images.pack_start(image, True, True, 0)
            image.show()

        self.curr_prev = FX_PREV_RULE

        if result['sadditive'] is None:
            result.fill()
            result.humanize()

        if result['additive'] == 1: additive_str = _('This rule adds its weight to the rest of ranking')
        else: additive_str = _('This rule supercedes wieights of other ranking rules if matched')

        if coalesce(result.get('flag'),0) > 0:
            color = fdx.get_flag_color(result.get('flag',0)) 
            flag_str = f"""<b><span foreground="{color}">{esc_mu(result["flag_name"])}</span></b>"""
        else: flag_str = ''  

        prev_text = f"""




{_('Name:')} <b>{esc_mu(result['name'])}</b>

{_('Search string:')} <b>{esc_mu(result['string'])}</b>

{_('Weight:')} <b>{esc_mu(round(result['weight'],5))}</b>

{_('Type:')} <b>{esc_mu(result['query_type'])}</b>

{_('Case insensitive?:')} <b>{esc_mu(result['scase_insensitive'])}</b>

{_('On field:')} <b>{esc_mu(result['field_name'])}</b>

{_('On Channel/Cat.:')} <b>{esc_mu(result['feed_name'])}</b>

{_('Flag:')} {flag_str}

{_('Language:')} <b>{esc_mu(result['lang'])}</b>

<i>{additive_str}</i>


"""
        self.preview_label.set_line_wrap(False)
        self.preview_label.set_markup(prev_text)








    def load_preview_catalog(self, result, *args, **kargs):
        """ Load a catalog item into preview window """
        adj = self.preview_box.get_vadjustment()
        adj.set_value(0)

        self.prev_entry = {}

        for c in self.prev_images.get_children(): self.prev_images.remove(c)
        try: image = Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_size(os.path.join(FEEDEX_FEED_CATALOG_CACHE, 'thumbnails', result['thumbnail']), 64, 64))
        except: image = Gtk.Image.new_from_icon_name('rss-symbolic', Gtk.IconSize.DIALOG)

        self.prev_images.pack_start(image, True, True, 0)
        image.show()
        
        self.curr_prev = FX_PREV_CATALOG

        prev_text = f"""




<b>{esc_mu(result['name'])}</b>

{esc_mu(result['desc'])}

<i>{esc_mu(result['location'])}</i>

<i>{esc_mu(result['freq'])}</i>

"""
        self.preview_label.set_line_wrap(True)
        self.preview_label.set_markup(prev_text)









############################################
#   IMAGE HANDLING




    def _on_image_clicked(self, widget, event, res, user_agent):
        """ Wrapper for showing full-size image in chosen external viewer """
        if event.button == 1:
            if res.get('file') is not None: filename = res['file']
            else: 
                filename = os.path.join(self.DB.cache_path, f"""{res['url_hash']}_large.img""" )
                if not os.path.isfile(filename):
                    err, _dummy = fdx.download_res(res['url'], ofile=filename, mimetypes=FEEDEX_IMAGE_MIMES, user_agent=user_agent)
                    if err != 0: return err

            err = fdx.ext_open('image_viewer', filename, title=res.get('title',''), alt=res.get('alt',''), file=True)
            if err != 0: return err

        return 0






    def _handle_images_thr(self, id, user_agent, queue):
        """ Image download wrapper for separate thread"""
        for res in queue:
            if res['url'] in self.downloaded: continue
            self.downloaded.append(res['url'])
            download_thumbnail(res['url'], res['thumbnail'], user_agent=user_agent)
        fdx.bus_append((FX_ACTION_HANDLE_IMAGES, id,))


    def _handle_local_im_thr(self, id, res, *args, **kargs):
        """ Generate thumbnail for local resource """
        local_thumbnail(res['file'], res['thumbnail'])
        fdx.bus_append((FX_ACTION_HANDLE_IMAGES, id,))




    def handle_images(self, id:int, links, **kargs):
        """ Handle preview images: detect thumbnails and load them to preview boxes or send requests for downloads """

        if id != self.prev_entry.get('id', None): return 0

        for c in self.prev_images.get_children():
            self.prev_images.remove(c)

        boxes = []
        im_file = os.path.join(self.DB.img_path, f"""{id}.img""")
        if os.path.isfile(im_file):
            tn_file = os.path.join(self.DB.cache_path, f"""{id}.img""")
            res = {'file': im_file, 'thumbnail': tn_file, 'title':'', 'alt':''}
            if not os.path.isfile(tn_file):
                t = threading.Thread(target=self._handle_local_im_thr, args=(self.prev_entry['id'], res))
                t.start()
            else:
                box = f_imagebox(res)
                if box is not None: 
                    box.connect("button-press-event", self._on_image_clicked, res, None)
                    boxes.append(box)


        urls = []
        download_q = []
        for i in links:

            if i.startswith('<local>') and i.endswith('<\local>'): continue

            res = fdx.parse_res_link(i)
            if res is None: continue
            if res['url'] in urls: continue
            if res['url'] in fdx.download_errors: continue
            urls.append(res['url'])

            res['thumbnail'] = os.path.join(self.DB.cache_path, res['thumbnail'])
            if os.path.isfile(res['thumbnail']):
                res['size'] = os.path.getsize(res['thumbnail'])
                if res['size'] > 0 and res['size'] < MAX_DOWNLOAD_SIZE:
                    box = f_imagebox(res)
                    if box is not None: 
                        box.connect("button-press-event", self._on_image_clicked, res, self.prev_entry.get('user_agent'))
                        boxes.append(box)
            else:
                download_q.append(res)


        if len(download_q) > 0:
            t = threading.Thread(target=self._handle_images_thr, args=(self.prev_entry['id'], self.prev_entry.get('user_agent'), download_q))
            t.start()

        for b in boxes: self.prev_images.pack_start(b, True, True, 3)











    def startup_decor(self, *args, **kargs):
        """ Decorate preview tab on startup """
        self.prev_entry = {}

        if self.curr_prev != FX_PREV_STARTUP:
            for c in self.prev_images.get_children(): self.prev_images.remove(c)
            self.prev_images.pack_start(self.icons['large']['main_emblem'], True, True, 0)
        self.curr_prev = FX_PREV_STARTUP

        startup_text = f"""




        
            <b>FEEDEX {FEEDEX_VERSION}</b>

            <a href="{esc_mu(FEEDEX_WEBSITE)}">{esc_mu(FEEDEX_WEBSITE)}</a>

            <i>{FEEDEX_CONTACT}</i>
            {FEEDEX_AUTHOR}

            {FEEDEX_DESC}
            <i>{FEEDEX_SUBDESC}</i>

                                                                                """
        if kargs.get('from_catalog', False):
            startup_text = f"""{startup_text}

    <b>{esc_mu(_('Welcome!'))}</b>
    <b>{esc_mu(_('Mark Feeds to subscribe to and hit "Subscribe to Selected" button to start!'))}</b>
"""     
    
        self.preview_label.set_line_wrap(False)
        self.preview_label.set_markup(startup_text)




    def win_decor(self, *args):
        """ Decorate main window """
        self.hbar.props.title = f"Feedex {FEEDEX_VERSION}"
        if self.profile_name != '': self.hbar.props.subtitle = f"{self.profile_name}"
        self.hbar.show_all()

    def set_profile(self, *args):
        """ Setup path to caches, plugins etc. """
        self.profile_name = self.config.get('profile_name','')
        if self.profile_name == '': 
            self.gui_cache_path = os.path.join(FEEDEX_SHARED_PATH, 'feedex_gui_cache.json')
            self.gui_plugins_path = os.path.join(FEEDEX_SHARED_PATH, 'feedex_plugins.json')
        else:
            self.gui_cache_path = os.path.join(FEEDEX_SHARED_PATH, f'feedex_gui_cache_{fdx.hash_url(self.profile_name)}.json')
            self.gui_plugins_path = os.path.join(FEEDEX_SHARED_PATH, f'feedex_plugins_{fdx.hash_url(self.profile_name)}.json')












def feedex_run_main_win(*args, **kargs):
    """ Runs main Gtk loop with main Feedex window"""
    win = FeedexMainWin(*args, **kargs)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
