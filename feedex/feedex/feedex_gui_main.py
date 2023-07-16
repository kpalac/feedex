# -*- coding: utf-8 -*-
""" GUI classes for FEEDEX """



from feedex_gui_utils import *









class FeedexMainWin(Gtk.Window):
    """ Main window for Feedex """

    def __init__(self, *args, **kargs):
    
        self.config = kargs.get('config', fdx.config)

        self.gui_cache = validate_gui_cache( load_json(FEEDEX_GUI_ATTR_CACHE, {}) ) #Load cached GUI settings/layouts/tabs from previous session
        self.gui_plugins = validate_gui_plugins( load_json(FEEDEX_GUI_PLUGINS, FX_DEFAULT_PLUGINS, create_file=True) ) # Load and validate plugin list

        # Main DB interface - init and check for lock and/or DB errors
        self.DB = FeedexDatabase( db_path=kargs.get('db_path', self.config.get('db_path')), ignore_images=self.config.get('ignore_images', False), allow_create=True)
        try:
            self.DB.connect(defaults=True, default_feeds=False)
            self.DB.load_all()
            self.DB.cache_icons()
            self.DB.connect_LP()
            self.DB.connect_QP()
        except (FeedexDatabaseError, FeedexDataError,) as e:
            dialog = BasicDialog(None, _("Feedex: Critical Error!"), _('Error occurred that precludes execution.\nApplication could not be started. I am sorry for inconvenienve :('), 
                            subtitle=f'\n<i>{_("See application log for further details")}</i>', emblem='dialog-error-symbolic')
            dialog.run()
            dialog.destroy()            
            sys.exit(e.code)
            
        if self.DB.locked(timeout=2):
            dialog = YesNoDialog(None, _("Feedex: Database is Locked"), f"<b>{_('Database is Locked! Proceed and unlock?')}</b>", emblem='system-lock-screen-symbolic',
                                        subtitle=_("Another instance can be performing operations on Database or Feedex did not close properly last time. Proceed anyway?"))
            dialog.run()
            if dialog.response == 1:
                self.DB.unlock()
                dialog.destroy()
            else:
                dialog.destroy()
                self.DB.close()
                sys.exit(4)
    
        self.DB.unlock()

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
        self.new_n = scast( self.gui_cache.get('new_n'), int, 1 ) # Last nth unread update

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
        self.curr_prev = None

        # Image handling
        self.icons = get_icons(fdx.feeds_cache, fdx.icons_cache)

        # Action flags for caching and comparing with main bus
        self.busy = fdx.busy # Mainly for spinner display

        # String containing all log messages from this session
        self.log_string = ''

        # Places
        self.curr_place = FX_PLACE_LAST

        # Start threading and main window
        Gdk.threads_init()
        Gtk.Window.__init__(self, title=f"Feedex {FEEDEX_VERSION}")
        self.lock = threading.Lock()

        self.set_border_width(10)
        self.set_icon(self.icons['main'])
        self.set_resizable(True)
        self.set_position(Gtk.WindowPosition.CENTER)

        GLib.timeout_add(interval=250, function=self._on_timer)




        # Lower status bar
        self.status_bar = f_label('', justify=FX_ATTR_JUS_LEFT, wrap=True, markup=True, selectable=True, ellipsize=FX_ATTR_ELL_END) 
        self.status_spinner = Gtk.Spinner()
        lstatus_box = Gtk.Box()
        lstatus_box.set_orientation(Gtk.Orientation.HORIZONTAL)
        lstatus_box.set_homogeneous(False)
        lstatus_box.pack_start(self.status_spinner, False, False, 10)
        lstatus_box.pack_start(self.status_bar, False, False, 10)


        # Header bar and top menus
        hbar = Gtk.HeaderBar()
        hbar.set_show_close_button(True)
        hbar.props.title = f"Feedex {FEEDEX_VERSION}"
        
        if self.config.get('profile_name') is not None: hbar.props.subtitle = f"{self.config.get('profile_name')}"
        
        self.hbar_button_menu = Gtk.MenuButton()
        self.hbar_button_menu.set_popup(self.main_menu())
        self.hbar_button_menu.set_tooltip_markup(_("""Main Menu"""))
        hbar_button_menu_icon = Gtk.Image.new_from_icon_name('open-menu-symbolic', Gtk.IconSize.BUTTON)
        self.hbar_button_menu.add(hbar_button_menu_icon)         
        self.set_titlebar(hbar)

        self.button_new = Gtk.MenuButton()
        self.button_new.set_popup(self.add_menu())
        self.button_new.set_tooltip_markup(_("Add item ..."))
        button_new_icon = Gtk.Image.new_from_icon_name('list-add-symbolic', Gtk.IconSize.BUTTON)
        self.button_new.add(button_new_icon)
        
        self.button_feeds_download   = f_button(None,'rss-symbolic', connect=self.on_load_news_all, tooltip=f'<b>{_("Fetch")}</b> {_("news for all Channels")}')
       
        self.button_search = Gtk.MenuButton()
        self.button_search.set_popup(self.new_tab_menu())
        self.button_search.set_tooltip_markup(_("""Open a new tab for Searches..."""))
        button_search_icon = Gtk.Image.new_from_icon_name('edit-find-symbolic', Gtk.IconSize.BUTTON)
        self.button_search.add(button_search_icon)

    

        # Upper notebook stuff 
        self.rules_tab = -1
        self.flags_tab = -1
        self.plugins_tab = -1
        self.learned_rules_tab = -1
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
        main_box = Gtk.VBox(homogeneous=False)
 
        # Set up layout    
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

            main_box.add(self.div_vert)

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

            main_box.add(self.div_vert)

            self.div_vert.set_position(self.gui_cache['div_vert'])
            self.div_vert2.set_position(self.gui_cache['div_vert2'])

        main_top_box = Gtk.VBox()
        main_top_box.pack_start(main_box, True, True, 3)
        main_top_box.pack_start(lstatus_box, False, False, 3)
        self.add(main_top_box)

        hbar.pack_start(self.button_feeds_download)
        hbar.pack_start(self.button_new)
        hbar.pack_start(self.button_search)
        
        hbar.pack_end(self.hbar_button_menu)



        self.connect("destroy", self._on_close)
        self.connect("key-press-event", self._on_key_press)

        self.set_default_size(self.gui_cache.get('win_width'), self.gui_cache.get('win_height'))
        if self.gui_cache.get('win_maximized', False): self.maximize()
        
        self.connect('window-state-event', self._on_state_event)
        self.connect('delete-event', self._on_delete_event)



        # Launch startup tabs
        self.add_tab({'type':FX_TAB_PLACES, 'query':FX_PLACE_LAST, 'do_search':True})

        for i, tb in enumerate(self.gui_cache.get('tabs',[])):
            if tb in (None, (), []): continue
            self.add_tab({'type':tb.get('type',FX_TAB_SEARCH), 'query':tb.get('phrase',''), 'filters':tb.get('filters',{}), 'title':tb.get('title')})

        self.upper_notebook.set_current_page(0)
 

        # Run onboarding after DB creation
        if self.DB.created: self.add_tab({'type':FX_TAB_CATALOG, 'do_search':True})




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

        # Save current tabs if preferred
        if self.config.get('gui_startup_page',0) == 4:
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

        err = save_json(FEEDEX_GUI_ATTR_CACHE, self.gui_cache)
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
                if not self.busy: self.status_bar.set_markup('')
                uid = m[1]
                for i in range(self.upper_notebook.get_n_pages()):
                    tb = self.upper_notebook.get_nth_page(i)
                    if tb is None: continue
                    if tb.uid == uid:
                        tb.finish_search()
                        if hasattr(tb, 'query_combo'): self.reload_history_all()
                        break

            elif code == FX_ACTION_FINISHED_FILTERING:
                if not self.busy: self.status_bar.set_markup('')
                uid = m[1]
                for i in range(self.upper_notebook.get_n_pages()):
                    tb = self.upper_notebook.get_nth_page(i)
                    if tb is None: continue
                    if tb.uid == uid:
                        tb.finish_filtering()
                        break

            elif code == FX_ACTION_HANDLE_IMAGES:
                if self.prev_entry.get('id') == m[1]: 
                    self.handle_images(self.prev_entry.get('id', None), f"""{self.prev_entry.get('images','')}\n{self.links}""")

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

        # Update processing spinner and handle main bus flag chnges
        if fdx.busy is not self.busy:
            self.busy = fdx.busy
            if self.busy:
                self.status_spinner.show()
                self.status_spinner.start()
            else:
                self.status_spinner.stop()
                self.status_spinner.hide()
 
        return True






    def _on_key_press(self, widget, event):
        """ When keyboard is used ... """
        key = event.keyval
        key_name = Gdk.keyval_name(key)
        state = event.state
        ctrl = (state & Gdk.ModifierType.CONTROL_MASK)        
        if ctrl and key_name == self.config.get('gui_key_new_entry','n'): self.on_edit_entry(None)
        elif ctrl and key_name == self.config.get('gui_key_new_rule','r'): self.on_edit_rule(None)
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
        menu.append( f_menu_item(1, _('Export Feed data to JSON'), self.export_feeds, icon='application-rss+xml-symbolic'))  
        menu.append( f_menu_item(1, _('Export Rules to JSON'), self.export_rules, icon='view-list-compact-symbolic'))  
        menu.append( f_menu_item(1, _('Export Flags to JSON'), self.export_flags, icon='marker-symbolic'))  
        menu.append( f_menu_item(1, _('Export Plugins to JSON'), self.export_plugins, icon='extension-symbolic'))  
        return menu

    def import_menu(self, *args):
        menu = Gtk.Menu()
        menu.append( f_menu_item(1, _('Import Feed data from JSON'), self.import_feeds, icon='application-rss+xml-symbolic'))  
        menu.append( f_menu_item(1, _('Import Rules data from JSON'), self.import_rules, icon='view-list-compact-symbolic'))  
        menu.append( f_menu_item(1, _('Import Flags data from JSON'), self.import_flags, icon='marker-symbolic'))  
        menu.append( f_menu_item(1, _('Import Plugin data from JSON'), self.import_plugins, icon='extension-symbolic'))  
        menu.append( f_menu_item(0, 'SEPARATOR', None) )
        menu.append( f_menu_item(1, _('Import Entries from JSON'), self.import_entries, icon='document-import-symbolic'))  
        return menu

    def db_menu(self, *args):
        menu = Gtk.Menu()
        menu.append( f_menu_item(1, _('Maintenance...'), self.on_maintenance, icon='system-run-symbolic', tooltip=_("""Maintenance can improve performance for large databases by doing cleanup and reindexing.
It will also take some time to perform""") ))  
        menu.append( f_menu_item(0, 'SEPARATOR', None) )
        menu.append( f_menu_item(1, _('Clear cache'), self.on_clear_cache, icon='edit-clear-all-symbolic', tooltip=_("""Clear downloaded temporary files with images/thumbnails to reclaim disk space""") ) )
        menu.append( f_menu_item(0, 'SEPARATOR', None) )
        menu.append( f_menu_item(1, _('Database statistics'), self.on_show_stats, icon='drive-harddisk-symbolic') )
        return menu

    def log_menu(self, *args):
        menu = Gtk.Menu()
        menu.append( f_menu_item(1, _('View session log'), self.on_show_session_log, icon='text-x-generic-symbolic') )
        menu.append( f_menu_item(1, _('View main log'), self.on_view_log, icon='text-x-generic-symbolic') )
        return menu


    def main_menu(self, *args):
        menu = Gtk.Menu()
        menu.append( f_menu_item(1, _('Rules'), self.add_tab, kargs={'type':FX_TAB_RULES, 'do_search':True}, icon='view-list-compact-symbolic', tooltip=_('Open a new tab showing Saved Rules') ) )
        menu.append( f_menu_item(1, _('Flags'), self.add_tab, kargs={'type':FX_TAB_FLAGS, 'do_search':True}, icon='marker-symbolic', tooltip=_('Open a new tab showing Flags') ) )
        menu.append( f_menu_item(0, 'SEPARATOR', None) )
        menu.append( f_menu_item(1, _('Plugins'), self.add_tab, kargs={'type':FX_TAB_PLUGINS, 'do_search':True}, icon='extension-symbolic', tooltip=_('Open a new tab showing Plugins') ) )
        menu.append( f_menu_item(0, 'SEPARATOR', None) )
        menu.append( f_menu_item(1, _('Preferences'), self.on_prefs, icon='preferences-system-symbolic') )
        menu.append( f_menu_item(0, 'SEPARATOR', None) )
        menu.append( f_menu_item(3, _('Export...'), self.export_menu(), icon='document-export-symbolic'))
        menu.append( f_menu_item(3, _('Import...'), self.import_menu(), icon='document-import-symbolic'))  
        menu.append( f_menu_item(0, 'SEPARATOR', None) )
        menu.append( f_menu_item(3, _('Database...'), self.db_menu(), icon='drive-harddisk-symbolic') )
        menu.append( f_menu_item(0, 'SEPARATOR', None) )
        menu.append( f_menu_item(3, _('Logs...'), self.log_menu(), icon='text-x-generic-symbolic'))  
        menu.append( f_menu_item(0, 'SEPARATOR', None) )
        menu.append( f_menu_item(1, _('About Feedex...'), self.on_show_about, icon='help-about-symbolic') )
        menu.show_all()
        return menu

    def add_menu(self, *args):
        menu = Gtk.Menu()
        menu.append( f_menu_item(1, _('Add Channel from URL'), self.on_add_from_url, icon='application-rss+xml-symbolic', tooltip=f'<b>{_("Add Channel")}</b> {_("from URL")}' )  )
        menu.append( f_menu_item(0, 'SEPARATOR', None) )
        menu.append( f_menu_item(1, _('Add Entry'), self.on_edit_entry, args=(None,), icon='list-add-symbolic', tooltip=_('Add new Entry') ))   
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
        menu.append( f_menu_item(1, _('Trending'), self.add_tab, kargs={'type':FX_TAB_TRENDING}, icon='globe-symbolic', tooltip=_('Show trending Articles') ))  
        menu.append( f_menu_item(1, _('Trends'), self.add_tab, kargs={'type':FX_TAB_TRENDS}, icon='comment-symbolic', tooltip=_('Show most talked about terms for Articles') ))  

        menu.append( f_menu_item(0, 'SEPARATOR', None) )
        menu.append( f_menu_item(1, _('Show Contexts for a Term'), self.add_tab, kargs={'type':FX_TAB_CONTEXTS}, icon='view-list-symbolic', tooltip=_('Search for Term Contexts') ))  
        menu.append( f_menu_item(1, _('Show Time Series for a Term'), self.add_tab, kargs={'type':FX_TAB_TIME_SERIES, 'filters':{'...-...':True, 'logic':'phrase', 'group':'monthly'}}, icon='histogram-symbolic', tooltip=_('Generate time series plot') ))  
        menu.append( f_menu_item(0, 'SEPARATOR', None) )
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
                menu.append( f_menu_item(1, p[FX_PLUGIN_TABLE.index('name')], self.on_run_plugin, args=(p[FX_PLUGIN_TABLE.index('id')], item,), tooltip=scast(p[FX_PLUGIN_TABLE.index('desc')], str, '') ))
            return menu
        else: return None





    def action_menu(self, item, tab, event, **kargs):
        """ Main action menu construction"""
        menu = None
        plugin_filter = []

        if tab.type == FX_TAB_RULES:
            menu = Gtk.Menu()
            menu.append( f_menu_item(1, _('Add Rule'), self.on_edit_rule, args=(None,), icon='list-add-symbolic') )
        elif tab.type == FX_TAB_FLAGS:
            menu = Gtk.Menu()
            menu.append( f_menu_item(1, _('Add Flag'), self.on_edit_flag, args=(None,), icon='list-add-symbolic') )
        elif tab.type == FX_TAB_PLUGINS:
            menu = Gtk.Menu()
            menu.append( f_menu_item(1, _('Add Plugin'), self.on_edit_plugin, args=(None,), icon='list-add-symbolic') )
        elif tab.type in (FX_TAB_CONTEXTS, FX_TAB_SEARCH, FX_TAB_NOTES, FX_TAB_TREE, FX_TAB_SIMILAR,) or (tab.type == FX_TAB_PLACES and self.curr_place != FX_PLACE_TRASH_BIN):
            menu = Gtk.Menu()
            menu.append( f_menu_item(1, _('Add Entry'), self.on_edit_entry, args=(None,), icon='list-add-symbolic') )
            if tab.table.result_no > 0: plugin_filter.append(FX_PLUGIN_RESULTS)
        elif tab.type not in (FX_TAB_FEEDS,):
            if tab.table.result_no > 0: plugin_filter.append(FX_PLUGIN_RESULTS)




        if isinstance(item, (ResultEntry, ResultContext,)):
            
            if menu is None: menu = Gtk.Menu()
            else: menu.append( f_menu_item(0, 'SEPARATOR', None) )
            
            if coalesce(item.get('is_deleted'),0) == 0:
                mark_menu = Gtk.Menu()
                mark_menu.append( f_menu_item(1, _('Read (+1)'), self.on_mark, args=('read', item,), icon='bookmark-new-symbolic', tooltip=_("Number of reads if counted towards this entry keyword's weight when ranking incoming articles") ) )
                mark_menu.append( f_menu_item(1, _('Unread'), self.on_mark, args=('unread', item,), icon='edit-redo-rtl-symbolic', tooltip=_("Unread document does not contriute to ranking rules") ) )
                mark_menu.append( f_menu_item(1, _('Unimportant'), self.on_mark, args=('unimp', item,), icon='edit-redo-rtl-symbolic', tooltip=_("Mark this as unimportant and learn negative rules") ) )
                menu.append( f_menu_item(3, _('Mark as...'), mark_menu, icon='bookmark-new-symbolic') )

                flag_menu = Gtk.Menu()
                for fl, v in fdx.flags_cache.items():
                    fl_name = esc_mu(v[0])
                    fl_color = v[2]
                    fl_desc = esc_mu(v[1])
                    if fl_color in (None, ''): fl_color = self.config.get('gui_default_flag_color','blue')
                    if fl_name in (None, ''): fl_name = f'{_("Flag")} {fl}'
                    flag_menu.append( f_menu_item(1, fl_name, self.on_mark, args=(fl, item,), color=fl_color, icon='marker-symbolic', tooltip=fl_desc) )
                flag_menu.append( f_menu_item(1, _('Unflag Entry'), self.on_mark, args=('unflag', item,), icon='edit-redo-rtl-symbolic', tooltip=_("Remove Flags from Entry") ) )
                flag_menu.append( f_menu_item(0, 'SEPARATOR', None) )
                flag_menu.append( f_menu_item(1, _('Show Flags...'), self.add_tab, kargs={'type':FX_TAB_FLAGS, 'do_search':True}, icon='marker-symbolic', tooltip=_('Open a new tab showing Flags') ) )
                menu.append( f_menu_item(3, _('Flag as...'), flag_menu, icon='marker-symbolic', tooltip=f"""{_("Flag is a user's marker/bookmark for a given article independent of ranking")}\n<i>{_("You can setup different flag colors in Preferences")}</i>""") )
                
                menu.append( f_menu_item(1, _('Edit Entry'), self.on_edit_entry, args=(item,), icon='edit-symbolic') )
                menu.append( f_menu_item(1, _('Delete'), self.on_del_entry, args=(item,), icon='edit-delete-symbolic') )

            elif coalesce(item.get('is_deleted'),0) > 0:
                menu.append( f_menu_item(1, _('Restore'), self.on_restore_entry, args=(item,), icon='edit-redo-rtl-symbolic') )
                menu.append( f_menu_item(1, _('Delete permanently'), self.on_del_entry, args=(item,), icon='edit-delete-symbolic') )

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

            detail_menu = Gtk.Menu()
            detail_menu.append( f_menu_item(1, _('Show Keywords for Entry'), self.add_tab, kargs={'type':FX_TAB_KEYWORDS, 'top_entry':item, 'do_search':True, 'filters':{'depth':50} }, icon='system-run-symbolic') )
            detail_menu.append( f_menu_item(1, _('Show Ranking for Entry'), self.add_tab, kargs={'type':FX_TAB_RANK, 'top_entry':item, 'do_search':True}, icon='applications-engineering-symbolic') )
            if fdx.debug_level not in (0, None): 
                detail_menu.append( f_menu_item(0, 'SEPARATOR', None) )
                detail_menu.append( f_menu_item(1, _('Technical details...'), self.on_show_detailed, args=('entry', item,), icon='system-run-symbolic', tooltip=_("Show all entry's technical data") ) )
            menu.append( f_menu_item(3, _('Details...'), detail_menu, icon='zoom-in-symbolic') ) 

            plugin_filter.append(FX_PLUGIN_ENTRY)
            plugin_filter.append(FX_PLUGIN_RESULT)        
            




        elif isinstance(item, ResultRule) and tab.type != FX_TAB_LEARNED:
            
            if menu is None: menu = Gtk.Menu()
            else: menu.append( f_menu_item(0, 'SEPARATOR', None) )

            if item['id'] is not None:
                menu.append( f_menu_item(1, _('Edit Rule'), self.on_edit_rule, args=(item,), icon='edit-symbolic') )
                menu.append( f_menu_item(1, _('Delete Rule'), self.on_del_rule, args=(item,), icon='edit-delete-symbolic') )
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
                menu.append( f_menu_item(1, _('Edit Flag'), self.on_edit_flag, args=(item,), icon='edit-symbolic') )
                menu.append( f_menu_item(1, _('Delete Flag'), self.on_del_flag, args=(item,), icon='edit-delete-symbolic') )
                menu.append( f_menu_item(0, 'SEPARATOR', None) )
                menu.append( f_menu_item(1, _('Search for this Flag'), self.add_tab, kargs={'type':FX_TAB_SEARCH, 'filters':{'flag':item['id']}}, icon='edit-find-symbolic'))  
                menu.append( f_menu_item(1, _('Time Series search for this Flag'), self.add_tab, kargs={'type':FX_TAB_TIME_SERIES, 'filters':{'flag':item['id']}}, icon='histogram-symbolic'))  



        elif isinstance(item, FeedexPlugin):

            if menu is None: menu = Gtk.Menu()
            else: menu.append( f_menu_item(0, 'SEPARATOR', None) )

            if item['id'] is not None:
                menu.append( f_menu_item(1, _('Edit Plugin'), self.on_edit_plugin, args=(item,), icon='edit-symbolic') )
                menu.append( f_menu_item(1, _('Delete Plugin'), self.on_del_plugin, args=(item,), icon='edit-delete-symbolic') )



        elif isinstance(item, FeedexCatItem):

            if menu is None: menu = Gtk.Menu()
            else: menu.append( f_menu_item(0, 'SEPARATOR', None) )

            if item['id'] is not None:
                menu.append( f_menu_item(1, _('Visit Homepage'), self.on_go_home, args=(item,), icon='user-home-symbolic') )



        elif isinstance(item, ResultFeed):

            if menu is None: menu = Gtk.Menu()
            else: menu.append( f_menu_item(0, 'SEPARATOR', None) )

            if coalesce(item['deleted'],0) == 0:
                menu.append( f_menu_item(1, _('Show from newest...'), self.add_tab, kargs={'type':FX_TAB_SEARCH, 'do_search':True, 'filters':{'feed_or_cat':item['id'], '...-...':True}}, icon='edit-find-symbolic', tooltip=_("Show articles for this Channel or Category sorted from newest") ) )
                menu.append( f_menu_item(1, _('Show from newest (wide view)...'), self.add_tab, kargs={'type':FX_TAB_NOTES, 'do_search':True, 'filters':{'feed_or_cat':item['id'], '...-...':True}}, icon='format-unordered-list-symbolic', tooltip=_("Show articles sorted from newest in an extended view") ) )
                menu.append( f_menu_item(1, _('Summary...'), self.add_tab, kargs={'type':FX_TAB_TREE, 'do_search':True, 'filters':{'feed_or_cat':item['id'], 'last':True, 'group':'daily', 'fallback_sort':'trends'}}, icon='view-filter-symbolic', tooltip=_("Show item's Summary Tree ranked by Trends") ) )

                if not fdx.busy and tab.type == FX_TAB_FEEDS:
                    menu.append( f_menu_item(0, 'SEPARATOR', None) )
                    menu.append( f_menu_item(1, _('Add Channel'), self.on_feed_cat, args=('new_channel', None), icon='list-add-symbolic') )
                    menu.append( f_menu_item(1, _('Add Category'), self.on_feed_cat, args=('new_category', None), icon='folder-new-symbolic') )
                    
                    menu.append( f_menu_item(0, 'SEPARATOR', None) )
                    if item['is_category'] == 1: menu.append( f_menu_item(1, _('Move Category...'), self.feed_tab.copy_feed, icon='edit-cut-symbolic') ) 
                    else: menu.append( f_menu_item(1, _('Move Feed...'), self.feed_tab.copy_feed, icon='edit-cut-symbolic') ) 
                    
                    if not fdx.busy and self.feed_tab.copy_selected.get('id') is not None:
                        if self.feed_tab.copy_selected['is_category'] == 1:
                            if item['is_category'] == 1:
                                menu.append( f_menu_item(1, f'{_("Insert")} {esc_mu(self.feed_tab.copy_selected.get("name",""))} {_("here ...")}', self.feed_tab.insert_feed, args=(item,), icon='edit-paste-symbolic') )
                        else:
                            if item['is_category'] == 1:
                                menu.append( f_menu_item(1, f'{_("Assign")} {esc_mu(self.feed_tab.copy_selected.get("name",""))} {_("here ...")}', self.feed_tab.insert_feed, args=(item,), icon='edit-paste-symbolic') ) 
                            else:
                                menu.append( f_menu_item(1, f'{_("Insert")} {esc_mu(self.feed_tab.copy_selected.get("name",""))} {_("here ...")}', self.feed_tab.insert_feed, args=(item,), icon='edit-paste-symbolic') )
                

                if item['is_category'] != 1:
                    menu.append( f_menu_item(1, _('Go to Channel\'s Homepage'), self.on_go_home, args=(item,), icon='user-home-symbolic') )
        
                    if not fdx.busy:
                        menu.append( f_menu_item(0, 'SEPARATOR', None) )
                        menu.append( f_menu_item(1, _('Fetch from selected Channel'), self.on_load_news_feed, args=(item,), icon='rss-symbolic') )
                        menu.append( f_menu_item(1, _('Update metadata for Channel'), self.on_update_feed, args=(item,), icon='system-run-symbolic') )
                        menu.append( f_menu_item(1, _('Update metadata for All Channels'), self.on_update_feed_all, icon='system-run-symbolic') )
                        menu.append( f_menu_item(0, 'SEPARATOR', None) )

                        menu.append( f_menu_item(1, _('Edit Channel'), self.on_feed_cat, args=('edit', item,), icon='edit-symbolic') )
                        menu.append( f_menu_item(1, _('Mark Channel as healthy'), self.on_mark_healthy, args=(item,), icon='go-jump-rtl-symbolic', tooltip=_("This will nullify error count for this Channel so it will not be ommited on next fetching") ) )
                        menu.append( f_menu_item(0, 'SEPARATOR', None) )
                        menu.append( f_menu_item(1, _('Remove Channel'), self.on_del_feed, args=(item,), icon='edit-delete-symbolic') )
                        if fdx.debug_level not in (0, None): 
                            menu.append( f_menu_item(0, 'SEPARATOR', None) )
                            menu.append( f_menu_item(1, _('Technical details...'), self.on_show_detailed, args=('feed', item,), icon='zoom-in-symbolic', tooltip=_("Show all technical information about this Channel") ) )

                    plugin_filter.append(FX_PLUGIN_FEED)

                elif not fdx.busy:
                    menu.append( f_menu_item(1, _('Edit Category'), self.on_feed_cat, args=('edit',item,), icon='edit-symbolic') )
                    menu.append( f_menu_item(1, _('Remove Category'), self.on_del_feed, args=(item,), icon='edit-delete-symbolic') )

                    plugin_filter.append(FX_PLUGIN_CATEGORY)


            elif item['deleted'] == 1 and tab.type == FX_TAB_FEEDS:
                menu.append( f_menu_item(1, _('Restore...'), self.on_restore_feed, args=(item,), icon='edit-redo-rtl-symbolic') )
                menu.append( f_menu_item(1, _('Remove Permanently'), self.on_del_feed, args=(item,), icon='edit-delete-symbolic') )





        if ( (isinstance(item, SQLContainer) and coalesce(item['deleted'],0) > 0 ) or \
            (self.curr_place == FX_PLACE_TRASH_BIN and self.curr_upper.type == FX_TAB_PLACES)) and not fdx.busy:
            
            if menu is None: menu = Gtk.Menu()
            else: menu.append( f_menu_item(0, 'SEPARATOR', None) )
            menu.append( f_menu_item(1, _('Empty Trash'), self.on_empty_trash, icon='edit-delete-symbolic') )

        else:

            if tab.type == FX_TAB_RULES:
                if menu is None: menu = Gtk.Menu()
                else: menu.append( f_menu_item(0, 'SEPARATOR', None) )
                menu.append( f_menu_item(1, _('Show Learned Rules'), self.add_tab, kargs={'type':FX_TAB_LEARNED, 'top_entry':item, 'do_search':True}, icon='applications-engineering-symbolic', tooltip=_('Display rules learned from User\'s habits along with weights') ) )
            
            elif tab.type == FX_TAB_LEARNED:
                if menu is None: menu = Gtk.Menu()
                else: menu.append( f_menu_item(0, 'SEPARATOR', None) )
                menu.append( f_menu_item(1, _('Delete Learned Rules'), self.del_learned_rules, icon='dialog-warning-symbolic', tooltip=_('Remove all learned rules from database. Be careful!') ) )
                menu.append( f_menu_item(1, _('Relearn All Rules'), self.relearn_rules, icon='applications-engineering-symbolic', tooltip=_('Relearn rules from all read/marked items') ) )


            if tab.type not in (FX_TAB_FEEDS, FX_TAB_RULES, FX_TAB_FLAGS, FX_TAB_PLUGINS,) and tab.table.result_no > 0:
                port_menu = Gtk.Menu()
                port_menu.append( f_menu_item(1, _('Save results to CSV'), self.export_results, args=('csv',), icon='x-office-spreadsheet-symbolic', tooltip=_('Save results from current tab') ))  
                port_menu.append( f_menu_item(1, _('Export results to JSON'), self.export_results, args=('json_dict',), icon='document-export-symbolic', tooltip=_('Export results from current tab') ))  
            
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
        menu.append( f_menu_item(1, _('Fetch...'), self.on_load_news_all, icon='rss-symbolic', tooltip=f'<b>{_("Fetch")}</b> {_("news for all Channels")}' )  )
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
        self.on_edit_rule(None)






###########################################################3
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
        if tp == FX_TAB_LEARNED and self.learned_rules_tab != -1:
            self._show_upn_page(self.learned_rules_tab)
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
            self.learned_rules_tab = tab.uid
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

        if hasattr(tp, 'query_entry'): tab.query_entry.grab_focus()





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
        elif type == FX_TAB_LEARNED: self.learned_rules_tab = -1
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

        if self.curr_upper.top_entry_prev: self.load_preview(self.curr_upper.top_entry, footer=self.curr_upper.prev_footer)
        elif isinstance(self.curr_upper.table.result, (ResultEntry, ResultContext, ResultRule, FeedexCatItem,)): self.curr_upper._on_changed_selection()
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
        desc = esc_mu(result.get("desc",''))
        text = esc_mu(result.get("text",''))

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

        link_text = ''
        l_text = scast(result.get('link'), str, '').replace('<','').replace('>','')
        if l_text.endswith('/'): l_label = slist(l_text.split('/'), -2, l_text)
        else: l_label = slist(l_text.split('/'), -1, l_text)
        l_text = esc_mu(l_text)
        l_label = esc_mu(l_label)
        if l_text != '': link_text=f"""<a href="{l_text}" title="{_('Click to open link')} : <b>{l_text}</b>">{l_label}</a>"""
        
        self.links = ''
        for l in result.get('links','').splitlines() + result.get('enclosures','').splitlines():
            if l.strip() == '' or l == result.get('link'): continue
            self.links = f'{self.links}{l}\n'
            l_text = l.replace('<','').replace('>','')
            if l_text.endswith('/'): l_label = slist(l_text.split('/'), -2, l_text)
            else: l_label = slist(l_text.split('/'), -1, l_text)
            l_label = ellipsize(l_label, 75)
            l_text = esc_mu(l_text)
            l_label = esc_mu(l_label)
            link_text = f"""{link_text}
<a href="{l_text}" title="{_('Click to open link')}: <b>{l_text}</b>">{l_label}</a>"""
        
        if link_text != '': link_text = f"\n\n{_('Links:')}\n{link_text}"

        if result.get('prev_footer') is not None:
            footer = f"""
<small>-------------------------------------
{result.get('prev_footer')}</small>
"""
        else: footer = ''

        stat_str = f"""{snip_str}\n\n<small>-------------------------------------\n{_("Word count")}: <b>{result['word_count']}</b>
{_("Character count")}: <b>{result['char_count']}</b>
{_("Sentence count")}: <b>{result['sent_count']}</b>
{_("Capitalized word count")}: <b>{result['caps_count']}</b>
{_("Common word count")}: <b>{result['com_word_count']}</b>
{_("Polysyllable count")}: <b>{result['polysyl_count']}</b>
{_("Numeral count")}: <b>{result['numerals_count']}</b>\n
{_("Importance")}: <b>{round(result['importance'],3)}</b>
{_("Weight")}: <b>{round(result['weight'],3)}</b>
{_("Readability")}: <b>{round(result['readability'],3)}</b></small>\n"""

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


        if not self.config.get('ignore_images',False):
            self.handle_images(result.get('id', None), f"""{result.get('images','')}\n{self.links}""")






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

        if result['learned'] == 1: learned_str = _('This rule was learned by algorithm from openned or added item')
        else: learned_str = _('This rule was manually added by user')

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

<i><b>{learned_str}</b></i>

"""
        self.preview_label.set_line_wrap(False)
        self.preview_label.set_markup(prev_text)











    def load_preview_catalog(self, result, *args, **kargs):
        """ Load a catalog item into preview window """
        adj = self.preview_box.get_vadjustment()
        adj.set_value(0)

        self.prev_entry = {}

        for c in self.prev_images.get_children(): self.prev_images.remove(c)
        try: image = Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_size(result['thumbnail'], 64, 64))
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




    def handle_image(self, widget, event, url, title, alt, user_agent):
        """ Wrapper for showing full-size image in chosen external viewer """
        if event.button == 1:
            hash_obj = hashlib.sha1(url.encode())
            filename = os.path.join(self.DB.cache_path, f'{hash_obj.hexdigest()}_large.img' )
            if not os.path.isfile(filename):                
                err, plhdr = fdx.download_res(url, ofile=filename, mimetypes=FEEDEX_IMAGE_MIMES, user_agent=user_agent)
                if err != 0: return err

            err = fdx.ext_open('image_viewer', filename, title=title, alt=alt, file=True)
            if err != 0: return err
        return 0


    def download_images(self, id, user_agent, queue):
        """ Image download wrapper for separate thread"""
        for i in queue:
            url = i[0]
            filename = i[1]
            create_thumbnail(url, filename, user_agent=user_agent)

        fdx.bus_append((FX_ACTION_HANDLE_IMAGES, id,))




    def handle_images(self, id:int, string:str, **kargs):
        """ Handle preview images """
        for c in self.prev_images.get_children():
            self.prev_images.remove(c)

        urls = []
        boxes = []
        download_q = []
        for i in string.splitlines():
            im = process_res_links(i, self.DB.cache_path)
            if im == 0: continue
            if im['url'] in urls: continue
            if im['url'] in fdx.download_errors: continue

            urls.append(im['url'])
            if os.path.isfile(im['filename']) and os.path.getsize(im['filename']) > 0:
                pass
            else:
                download_q.append((im['url'], im['filename']))
                continue

            if id != self.prev_entry.get('id', None): continue

            eventbox = Gtk.EventBox()
            try:
                pixb = GdkPixbuf.Pixbuf.new_from_file(im['filename'])
                image = Gtk.Image.new_from_pixbuf(pixb)
            except GLib.Error as e:
                fdx.add_error(im['url'])
                msg(FX_ERROR_HANDLER, _('Image error: %a'), e)
                continue
            
            image.set_tooltip_markup(f"""{im.get('tooltip')}
Click to open in image viewer""")

            eventbox.add(image)
            eventbox.connect("button-press-event", self.handle_image, im['url'], im['title'], im['alt'], self.prev_entry.get('user_agent'))
            image.show()
            eventbox.show()
            boxes.append(eventbox)

        if len(download_q) > 0:
            t = threading.Thread(target=self.download_images, args=(self.prev_entry['id'], self.prev_entry.get('user_agent'), download_q))
            t.start()

        for b in boxes:
            self.prev_images.pack_start(b, True, True, 3)















#########################################################3
# DIALOGS ADN ACTIONS FROM MENUS OR BUTTONS



        




    def on_load_news_feed(self, *args):
        if not self._fetch_lock(): return 0
        t = threading.Thread(target=self.load_news_thr, args=(args[-1],))
        t.start()

    def on_load_news_all(self, *args):
        if not self._fetch_lock(): return 0
        t = threading.Thread(target=self.load_news_thr, args=(None,))
        t.start()

    def on_load_news_background(self, *args):
        if not self._fetch_lock(): return 0
        t = threading.Thread(target=self.load_news_thr, args=(0,))
        t.start()

    def _fetch_lock(self, *args):
        """ Handle fetching lock gracefully """
        if self.DB.locked_fetching(just_check=True):
            dialog = YesNoDialog(self, _("Database is Locked for Fetching"), f"<b>{_('Database is Locked for Fetching! Proceed and unlock?')}</b>", 
                                subtitle=_("Another instance may be fetching news right now. If not, proceed with operation. Proceed?"), emblem='system-lock-screen-symbolic')
            dialog.run()
            if dialog.response == 1:
                dialog.destroy()
                err = self.DB.unlock_fetching()
                if err == 0:
                    msg(_('Database manually unlocked for fetching...') )
                    return True
                else: return False
            else:
                dialog.destroy()
                return False
        else: return True


    def load_news_thr(self, *args):
        """ Fetching news/articles from feeds """
        msg(_('Checking for news ...'))
        fdx.busy = True
        fdx.bus_append(FX_ACTION_BLOCK_FETCH)

        item = args[-1]
        if item is None:
            feed_id=None
            ignore_interval = True
            ignore_modified = self.config.get('ignore_modified',True)
        elif item == 0:
            feed_id=None
            ignore_interval = False
            ignore_modified = self.config.get('ignore_modified',True)
        elif isinstance(item, SQLContainer):
            if item['is_category'] != 1:
                feed_id = item['id']
                ignore_interval = True
                ignore_modified = True
            else: 
                fdx.busy = False
                fdx.bus_append(FX_ACTION_UNBLOCK_FETCH)
                return -1
        else: 
            fdx.busy = False
            return -1

        DB = FeedexDatabase(connect=True)
        DB.fetch(id=feed_id, force=ignore_modified, ignore_interval=ignore_interval)


        if DB.new_items > 0:

            self.new_items = scast(self.new_items, int, 0) + DB.new_items
            self.new_n = scast(self.new_n, int, 1) + 1
            self.feed_tab.redecorate_new()

            if self.config.get('gui_desktop_notify', True):
                fx_notifier = DesktopNotifier(parent=self, icons=fdx.icons_cache)

                if self.config.get('gui_notify_group','feed') == 'number':
                    fx_notifier.notify(f'{DB.new_items} {_("new articles fetched...")}', None, -3)
                else:

                    filters = {'last':True,
                    'group':self.config.get('gui_notify_group','feed'), 
                    'depth':self.config.get('gui_notify_depth',5)
                    }
                    DB.Q.query('', filters , rev=False, print=False, allow_group=True)
                    fx_notifier.load(DB.Q.results)
                    fx_notifier.show()

        DB.close()
        fdx.busy = False
        fdx.bus_append(FX_ACTION_UNBLOCK_FETCH)
        fdx.bus_append(FX_ACTION_RELOAD_FEEDS)





    def on_update_feed(self, *args):
        """ Wrapper for feed updating """
        item = args[-1]
        if item['is_category'] == 1: return 0
        if not self._fetch_lock(): return 0
        msg(_('Updating channel...'))
        t = threading.Thread(target=self.update_feed_thr, args=(item['id'],))
        t.start()



    def on_update_feed_all(self, *args):
        if not self._fetch_lock(): return 0
        msg(_('Updating all channels...'))
        t = threading.Thread(target=self.update_feed_thr, args=(None,))
        t.start()


    def update_feed_thr(self, *args):
        """ Updates metadata for all/selected feed """
        fdx.busy = True
        fdx.bus_append(FX_ACTION_BLOCK_FETCH)

        feed_id = args[-1]
        DB = FeedexDatabase(connect=True)
        DB.fetch(id=feed_id, update_only=True, force=True)

        icons = get_icons(fdx.feeds_cache, fdx.icons_cache)      
        self.lock.acquire()
        self.icons = icons
        self.lock.release()

        DB.close()
        fdx.busy = False
        fdx.bus_append(FX_ACTION_UNBLOCK_FETCH)
        fdx.bus_append(FX_ACTION_RELOAD_FEEDS)




    def add_from_url_thr(self, item):
        """ Add from URL - threading """
        msg(_('Adding Channel...') )
        fdx.busy = True
        fdx.bus_append(FX_ACTION_BLOCK_FETCH)

        DB = FeedexDatabase(connect=True)
        item.set_interface(DB)
        err = item.add_from_url()
        
        if DB.new_items > 0:
            self.new_items = scast(self.new_items, int, 0) + DB.new_items
            self.new_n = scast(self.new_n, int, 1) + 1
            self.feed_tab.redecorate_new()
        
        self.lock.acquire()
        if err == 0: self.new_feed_url.clear()
        self.lock.release()

        DB.close()
        fdx.busy = False
        fdx.bus_append(FX_ACTION_UNBLOCK_FETCH)
        fdx.bus_append(FX_ACTION_RELOAD_FEEDS)



    def on_add_from_url(self, *args):
        """ Adds a new feed from URL - dialog """
        if fdx.busy: return 0
        if not self._fetch_lock(): return 0

        item = FeedexFeed(self.DB)
        item.strict_merge(self.new_feed_url)

        dialog = NewFromURL(self, item)
        dialog.run()
        self.new_feed_url = item.vals.copy()
        if dialog.response == 1:
            if not self._fetch_lock(): return 0
            t = threading.Thread(target=self.add_from_url_thr, args=(item,))
            t.start()
        dialog.destroy()









    def on_edit_entry(self, *args):
        """ Add / Edit Entry """
        item = args[-1]
        if item is None:
            new = True
            item = FeedexEntry(self.DB)
            item.strict_merge(self.new_entry)
        else: 
            item = item.convert(FeedexEntry, self.DB, id=item['id'])
            if not item.exists: return -1
            new = False

        dialog = EditEntry(self, item, new=new)
        dialog.run()
        if new: self.new_entry = item.vals.copy()
        if dialog.response == 1:
            if new: msg(_('Adding entry...') )
            else: msg(_('Writing changes to Entry...') )
            fdx.busy = True
            t = threading.Thread(target=self.edit_entry_thr, args=(new, item) )
            t.start()
        dialog.destroy()



    def edit_entry_thr(self, new:bool, item:FeedexEntry):
        """ Add/Edit Entry low-level interface for threading """
        DB = FeedexDatabase(connect=True)
        item.set_interface(DB)

        if new:
            err = item.add()
            if err == 0:
                fdx.bus_append( (FX_ACTION_ADD, item.vals.copy(), FX_TT_ENTRY, ) )
                self.lock.acquire()
                self.new_entry.clear()
                self.lock.release()
        else:
            err = item.do_update()
            if err == 0: fdx.bus_append( (FX_ACTION_EDIT, item.vals.copy(), FX_TT_ENTRY, ) )
        
        DB.close()
        fdx.busy = False






    def on_del_entry(self, *args):
        """ Deletes selected entry"""
        item = args[-1]
        if item['deleted'] != 1: dialog = YesNoDialog(self, _('Delete Entry'), f'{_("Are you sure you want to delete")} <i><b>{esc_mu(item.name())}</b></i>?')
        else: dialog = YesNoDialog(self, _('Delete Entry permanently'), f'{_("Are you sure you want to permanently delete")} <i><b>{esc_mu(item.name())}</b></i> {_("and associated rules?")}')
        dialog.run()
        if dialog.response == 1: self.on_mark('delete', item)
        dialog.destroy()


    def on_restore_entry(self, *args):
        """ Restore entry """
        item = args[-1]
        dialog = YesNoDialog(self, _('Restore Entry'), f'{_("Are you sure you want to restore")} <i><b>{esc_mu(item.name())}</b></i>?')
        dialog.run()
        if dialog.response == 1: self.on_mark('restore', item)
        dialog.destroy()



    def mark_thr(self, mode, item):
        """ Marks entry as read """
        DB = FeedexDatabase(connect=True)
        item = item.convert(FeedexEntry, DB, id=item['id'])
        if not item.exists:
            fdx.busy = False
            return -1

        if mode == 'read': 
            if coalesce(item['read'],0) < 0: idict = {'read': scast(item['read'],int,0)+1}
            else: idict = {'read': scast(item['read'],int,0)+1}
        elif mode == 'unimp': idict = {'read': -1}
        elif mode == 'unread': idict = {'read': 0}
        elif mode == 'unflag': idict = {'flag': 0}
        elif mode == 'restore': idict = {'deleted': 0}
        elif mode == 'delete' : idict = {}
        elif type(mode) is int: idict = {'flag': mode}
        else:
            fdx.busy = False
            return -1

        if mode == 'delete': err = item.delete()
        else: err = item.update(idict)
        
        DB.close()
        fdx.busy = False
        if err == 0: fdx.bus_append( (FX_ACTION_EDIT, item.vals.copy(), FX_TT_ENTRY,) )



    def on_mark(self, *args):
        item = args[-1]
        mode = args[-2]
        fdx.busy = True
        msg(_('Updating ...') )
        t = threading.Thread(target=self.mark_thr, args=(mode, item,))
        t.start()


    def open_entry_thr(self, item, *args):
        """ Wrappper for opening entry and learning in a separate thread """
        DB = FeedexDatabase(connect=True)
        item = item.convert(FeedexEntry, DB, id=item['id'])
        item.open()
        DB.close()
        fdx.busy = False
        fdx.bus_append((FX_ACTION_EDIT, item.vals.copy(), FX_TT_ENTRY,))
        msg(_('Done...'))



    def on_open_entry(self, *args, **kargs):
        """ Run in browser and learn """
        fdx.busy = True
        msg(_('Opening ...'))
        item = args[-1]
        t = threading.Thread(target=self.open_entry_thr, args=(item,))
        t.start()








    def on_feed_cat(self, *args):
        """ Edit feed/category """
        if not self._fetch_lock(): return 0        
        item = args[-1]
        action = args[-2]

        if action == 'new_category':
            new = True
            item = FeedexFeed(self.DB)
            item.merge(self.new_category)
            dialog = EditCategory(self, item, new=new)

        elif action == 'new_channel': 
            new = True
            item = FeedexFeed(self.DB)
            item.merge(self.new_feed)
            dialog = EditFeed(self, item, new=new)

        elif action == 'edit':
            item = item.convert(FeedexFeed, self.DB, id=item['id'])
            new = False
            if not item.exists: return -1
            if item['is_category'] == 1: dialog = EditCategory(self, item, new=new)
            else: dialog = EditFeed(self, item, new=new)

        dialog.run()
        if action == 'new_category': self.new_category = item.vals.copy()
        elif action == 'new_channel': self.new_feed = item.vals.copy()

        if dialog.response == 1:
            if new: err = item.add(validate=False)
            else:
                if item['is_category'] == 1: err = item.do_update(validate=True)
                else: err = item.do_update(validate=False)

            if err == 0:
                if action == 'new_category': self.new_category.clear()
                elif action == 'new_channel': self.new_feed.clear()

                self.feed_tab.reload()

        dialog.destroy()






    def on_del_feed(self, *args):
        """ Deletes feed or category """
        if not self._fetch_lock(): return 0
        item = args[-1]

        if coalesce(item['is_category'],0) == 0 and coalesce(item['deleted'],0) == 0:
            dialog = YesNoDialog(self, _('Delete Channel'), f'{_("Are you sure you want to delete")} <i><b>{esc_mu(item.name())}</b></i>{_("?")}')

        elif coalesce(item['is_category'],0) == 0 and coalesce(item['deleted'],0) == 1:
            dialog = YesNoDialog(self, _('Delete Channel permanently'), f'{_("Are you sure you want to permanently delete")} <i><b>{esc_mu(item.name())}</b></i>{_("?")}')

        elif coalesce(item['is_category'],0) == 1 and coalesce(item['deleted'],0) == 0:
            dialog = YesNoDialog(self, _('Delete Category'), f'{_("Are you sure you want to delete")} <i><b>{esc_mu(item.name())}</b></i> {_("category?")}')

        elif coalesce(item['is_category'],0) == 1 and coalesce(item['deleted'],0) == 1:
            dialog = YesNoDialog(self, _('Delete Category'), f'{_("Are you sure you want to permanently delete")} <i><b>{esc_mu(item.name())}</b></i> {_("category?")}')

        dialog.run()
        if dialog.response == 1:
            item = item.convert(FeedexFeed, self.DB, id=item['id'])
            err = item.delete()
            if err == 0: self.feed_tab.reload()
        
        dialog.destroy()





    def on_restore_feed(self, *args):
        """ Restores selected feed/category """
        if not self._fetch_lock(): return 0
        item = args[-1]

        if coalesce(item['is_category'],0) == 1: dialog = YesNoDialog(self, _('Restore Category'), f'{_("Restore ")}<i><b>{esc_mu(item.name())}</b></i>{_(" Category?")}')
        else: dialog = YesNoDialog(self, _('Restore Channel'), f'{_("Restore ")}<i><b>{esc_mu(item.name())}</b></i>{_(" Channel?")}')
        dialog.run()

        if dialog.response == 1:
            item = item.convert(FeedexFeed, self.DB, id=item['id'])
            err = item.update({'deleted': 0}) 
            if err == 0: self.feed_tab.reload()
        
        dialog.destroy()





    def on_empty_trash(self, *args):
        """ Empty all Trash items """
        dialog = YesNoDialog(self, _('Empty Trash'), f'<b>{_("Do you really want to permanently remove Trash content?")}</b>', emblem='edit-delete-symbolic')
        dialog.run()
        if dialog.response == 1:
            err = self.DB.empty_trash()
            if err == 0: self.feed_tab.reload()
        dialog.destroy()


    def reload_history_all(self, *args):
        """ Reloads history in all tabs containing query combo """
        for i in range(self.upper_notebook.get_n_pages()):
            tab = self.upper_notebook.get_nth_page(i)
            if tab is None: continue
            if hasattr(tab, 'query_combo'): tab.reload_history()

    def on_clear_history(self, *args):
        """ Clears search history """
        dialog = YesNoDialog(self, _('Clear Search History'), _('Are you sure you want to clear <b>Search History</b>?'), emblem='edit-clear-all-symbolic' )           
        dialog.run()
        if dialog.response == 1:
            err = self.DB.clear_history()
            if err == 0: self.reload_history_all()
        dialog.destroy()



    def on_mark_healthy(self, *args):
        """ Marks a feed as healthy -> zeroes the error count """
        if not self._fetch_lock(): return 0
        item = args[-1]
        item = item.convert(FeedexFeed, self.DB, id=item['id'])
        err = item.update({'error': 0})
        if err == 0: self.feed_tab.reload()








    

    def on_del_rule(self, *args):
        """ Deletes rule - wrapper """
        item = args[-1]

        dialog = YesNoDialog(self, _('Delete Rule'), f'{_("Are you sure you want to permanently delete ")}<b><i>{esc_mu(item.name())}</i></b>{_(" Rule?")}')           
        dialog.run()
        if dialog.response == 1:
            item = item.convert(FeedexRule, self.DB, id=item['id'])
            err = item.delete() 
            if err == 0:
                if self.rules_tab != -1: self._get_upn_page_obj(self.rules_tab).apply(FX_ACTION_DELETE, item.vals.copy())
        dialog.destroy()

        


    def on_edit_rule(self, *args):
        """ Edit / Add Rule with dialog """
        item = args[-1]

        if item is None:
            new = True
            item = FeedexRule(self.DB)
            item.strict_merge(self.new_rule)
        else: 
            new = False
            item = item.convert(FeedexRule, self.DB, id=item['id'])
            if not item.exists: return -1

        dialog = EditRule(self, item, new=new)
        dialog.run()
        if new: self.new_rule = item.vals.copy()
        if dialog.response == 1:
            if new: err = item.add(validate=False)
            else: err = item.do_update(validate=False)

            if err == 0:
                if self.rules_tab != -1: 
                    if new: 
                        self.new_rule.clear()
                        self._get_upn_page_obj(self.rules_tab).apply(FX_ACTION_ADD, item.vals.copy())
                    else: self._get_upn_page_obj(self.rules_tab).apply(FX_ACTION_EDIT, item.vals.copy())
        dialog.destroy()





    def on_del_flag(self, *args):
        """ Deletes flag - wrapper """
        item = args[-1]

        dialog = YesNoDialog(self, _('Delete Flag'), f'{_("Are you sure you want to permanently delete ")}<b><i>{esc_mu(item.name())}</i></b>{_(" Flag?")}')           
        dialog.run()
        if dialog.response == 1:
            item = item.convert(FeedexFlag, self.DB, id=item['id'])
            err = item.delete()
            if err == 0:
                if self.flags_tab != -1: self._get_upn_page_obj(self.flags_tab).apply(FX_ACTION_DELETE, item.vals.copy())
        dialog.destroy()

        

    def on_edit_flag(self, *args):
        """ Edit / Add Flag with dialog """
        item = args[-1]

        if item is None:
            new = True
            item = FeedexFlag(self.DB)
            item.strict_merge(self.new_flag)
        else: 
            new = False
            item = item.convert(FeedexFlag, self.DB, id=item['id'])
            if not item.exists: return -1

        dialog = EditFlag(self, item, new=new)
        dialog.run()
        if new: self.new_flag = item.vals.copy()
        if dialog.response == 1:
            if new: err = item.add(validate=False) 
            else: err = item.do_update(validate=False)

            if err == 0:
                if self.flags_tab != -1:
                    if new:
                        self._get_upn_page_obj(self.flags_tab).apply(FX_ACTION_ADD, item.vals.copy()) 
                        self.new_flag.clear()
                    else: self._get_upn_page_obj(self.flags_tab).apply(FX_ACTION_EDIT, item.vals.copy())
        dialog.destroy()   








    def on_del_plugin(self, *args):
        """ Delete plugin """
        item = args[-1]
        item.get_by_id(item['id'])
        item.main_win = self

        dialog = YesNoDialog(self, _('Delete Plugin'), f'{_("Are you sure you want to remove ")}<b><i>{esc_mu(item.name())}</i></b>{_(" Plugin?")}', buttons=2)           
        dialog.run()
        if dialog.response == 1:
            err = item.delete()
            if err == 0:
                if self.plugins_tab != -1: self._get_upn_page_obj(self.plugins_tab).apply(FX_ACTION_DELETE, item.vals.copy())
        dialog.destroy()



    def on_edit_plugin(self, *args):
        """ Edit/Add Plugin with Dialog"""
        item = args[-1]

        if item is None:
            new = True
            item = FeedexPlugin(main_win=self)
            item.strict_merge(self.new_plugin)
        else: 
            new = False
            item.get_by_id(item['id'])
            if not item.exists: return -1

        dialog = EditPlugin(self, item, new=new)
        dialog.run()
        if new: self.new_plugin = item.vals.copy()
        if dialog.response == 1:
            if new: err = item.add(validate=False) 
            else: err = item.edit(validate=False)

            if err == 0:
                if self.plugins_tab != -1:
                    if new:
                        self._get_upn_page_obj(self.plugins_tab).apply(FX_ACTION_ADD, item.vals.copy()) 
                        self.new_plugin.clear()
                    else: self._get_upn_page_obj(self.plugins_tab).apply(FX_ACTION_EDIT, item.vals.copy())
        dialog.destroy()   

        

    def on_run_plugin(self, *args):
        """ Execute plugin in context """
        plugin = FeedexPlugin(id=args[-2], main_win=self)
        if not plugin.exists: return -1
        item = args[-1]
        plugin.run(item)





    def on_go_home(self, *args):
        """ Executes browser on channel home page """
        item = args[-1]
        if isinstance(item, FeedexCatItem): item.open()
        else:
            item = item.convert(FeedexFeed, self.DB, id=item['id'])
            item.open()




    def on_prefs(self, *args):
        """ Run preferences dialog """
        restart = False
        dialog = PreferencesDialog(self)
        dialog.run()
        if dialog.response == 1:
            restart = dialog.result.get('restart',False)            
            reload = dialog.result.get('reload',False)
            reload_lang = dialog.result.get('reload_lang',False)            
            dialog.result.pop('restart')
            dialog.result.pop('reload')
            dialog.result.pop('reload_lang')

            new_config = fdx.save_config(FEEDEX_CONFIG, config=dialog.result)
            if new_config != -1:
                if reload_lang:
                    if self.config.get('lang') not in (None,'en'):
                        lang = gettext.translation('feedex', languages=[self.config.get('lang')])
                        lang.install(FEEDEX_LOCALE_PATH)
                if reload:
                    self.DB.load_all()
                if restart:
                    dialog.destroy()
                    dialog2 = BasicDialog(self, _('Restart Required'), _('Restart is required for all changes to be applied.'), button_text=_('OK'), emblem='dialog-warning-symbolic' )
                    dialog2.run()
                    dialog2.destroy()

                self.config = fdx.parse_config(None, config_str=new_config)
                
        if not restart: dialog.destroy()





    def on_view_log(self, *args):
        """ Shows dialog for reviewing log """
        log_str = ''
        try:        
            with open(self.config.get('log',''), 'r') as f: log_str = f.read()
        except OSError as e:
            return msg(FX_ERROR_IO, f'{_("Error reading log file (%a)")} {e}', self.config.get('log',''))

        dialog = BasicDialog(self, _('Main Log'), log_str, width=600, height=500, justify=FX_ATTR_JUS_LEFT, selectable=True, scrolled=True, markup=False)
        dialog.run()
        dialog.destroy()






    def on_show_detailed(self, *args):
        """ Shows dialog with entry's detailed technical info """
        mode = args[-2]
        item = args[-1]
        if mode == 'entry': item = item.convert(FeedexEntry, self.DB, id=item['id'])
        elif mode == 'feed': item = item.convert(FeedexFeed, self.DB, id=item['id'])
        else: return -1
        if not item.exists: return -1

        dialog = BasicDialog(self, _('Tech details'), esc_mu(item.__str__()), width=600, height=500, justify=FX_ATTR_JUS_LEFT, selectable=True, scrolled=True)
        dialog.run()
        dialog.destroy()





    def on_show_stats(self, *args):
        """ Shows dialog with SQLite DB statistics """
        stats = self.DB.stats()
        stats_str = f"""

{_('Statistics for database')}: <b>{stats['db_path']}</b>

{_('FEEDEX version')}:          <b>{stats['version']}</b>

{_('Main database size')}:      <b>{stats['db_size']}</b>
{_('Index size')}:              <b>{stats['ix_size']}</b>
{_('Cache size')}:              <b>{stats['cache_size']}</b>

{_('Total size')}:              <b>{stats['total_size']}</b>



{_('Entry count')}:             <b>{stats['doc_count']}</b>
{_('Last entry ID')}:           <b>{stats['last_doc_id']}</b>

{_('Learned rule count')}:      <b>{stats['rule_count']}</b>
{_('Manual rule count')}:       <b>{stats['user_rule_count']}</b>

{_('Feed count')}:              <b>{stats['feed_count']}</b>
{_('Category count')}:          <b>{stats['cat_count']}</b>

{_('Last news update')}:        <b>{stats['last_update']}</b>
{_('First news update')}:       <b>{stats['first_update']}</b>

"""
        if stats['lock']: 
            stat_str = f"""{stat_str}
{_('DATABASE LOCKED')}"""
        if stats['fetch_lock']: 
            stat_str = f"""{stat_str}
{_('DATABASE LOCKED FOR FETCHING')}"""

        if stats['due_maintenance']: 
            stat_str = f"""{stat_str}
{_('DATABASE MAINTENANCE ADVISED')}
{_('Use')} <b>feedex --db-maintenance</b> {_('command')}

"""

        dialog = BasicDialog(self, _("Database Statistics"), stats_str, width=600, height=500, pixbuf=self.icons.get('db'), justify=FX_ATTR_JUS_LEFT, selectable=True)
        dialog.run()
        dialog.destroy()



    def on_show_session_log(self, *args):
        """ Show dialog with current session log """
        dialog = BasicDialog(self, _('Session log'), self.log_string, width=600, height=500, justify=FX_ATTR_JUS_LEFT, selectable=True, scrolled=True)
        dialog.run()
        dialog.destroy()



    def on_show_about(self, *args):
        """ Shows 'About...' dialog """
        about_str=f"""
<b>FEEDEX v. {FEEDEX_VERSION}</b>

{FEEDEX_DESC}
<i>{FEEDEX_SUBDESC}</i>

{_('Release')}: {FEEDEX_RELEASE}

<i>{_('Author')}: {FEEDEX_AUTHOR}
{FEEDEX_CONTACT}</i>

{_('Website')}: <a href="{esc_mu(FEEDEX_WEBSITE)}">{esc_mu(FEEDEX_WEBSITE)}</a>


"""        
        dialog = BasicDialog(self, _('About...'), about_str, image='feedex.png', selectable=True)
        dialog.run()
        dialog.destroy()







    def on_show_rules_for_entry(self, *args, **kargs):
        """ Show dialog with rules matched for entry """
        item = args[-1]
        item = item.convert(FeedexEntry, self.DB, id=item['id'])
        if not item.exists: return -1
                                    
        dialog = DisplayMatchedRules(self, item)
        dialog.run()
        dialog.destroy() 



    def show_learned_rules(self, *args):
        """ Shows learned rules with weights in a separate window """
        dialog = DisplayRules(self)
        dialog.run()
        dialog.destroy()




    def on_show_keywords(self, *args, **kargs):
        """ Shows keywords for entry """
        item = args[-1]
        item = item.convert(FeedexEntry, self.DB, id=item['id'])
        if not item.exists: return -1

        dialog = DisplayKeywords(self, item, width=600, height=500)
        dialog.run()
        dialog.destroy()









##########################################
#   DB Maintenance Stuff

    def on_maintenance_thr(self, *args, **kargs):
        """ DB Maintenance thread """
        DB = FeedexDatabase(connect=True)
        err = DB.maintenance()
        DB.close()
        fdx.bus_append(FX_ACTION_UNBLOCK_DB)
        fdx.busy = False


    def on_maintenance(self, *args, **kargs):
        """ BD Maintenance """
        if fdx.busy: return -1
        if not self._fetch_lock(): return 0
        
        dialog = YesNoDialog(self, _('DB Maintenance'), _('Are you sure you want to DB maintenance? This may take a long time...'), emblem='system-run-symbolic' )  
        dialog.run()
        if dialog.response == 1:
            fdx.bus_append(FX_ACTION_BLOCK_DB)
            fdx.busy = True
            t = threading.Thread(target=self.on_maintenance_thr)
            t.start()
        dialog.destroy()



    def on_clear_cache_thr(self, *args, **kargs):
        DB = FeedexDatabase(connect=True)
        DB.clear_cache(-1)
        DB.close()
        fdx.busy = False
        fdx.bus_append(FX_ACTION_UNBLOCK_DB)


    def on_clear_cache(self, *args, **kargs):
        """ Clear image cache """
        if fdx.busy: return -1
        dialog = YesNoDialog(self, _('Clear Cache'), _('Do you want to delete all downloaded and cached images/thumbnails?'),  emblem='edit-clear-all-symbolic')
        dialog.run()
        if dialog.response == 1:
            fdx.bus_append(FX_ACTION_BLOCK_DB)
            fdx.busy = True
            t = threading.Thread(target=self.on_clear_cache_thr)
            t.start()
        dialog.destroy()

    
    def del_learned_rules(self, *args):
        """ Wrapper for deleting learned rules from DB """
        if fdx.busy: return -1
        if not self._fetch_lock(): return 0
        dialog = YesNoDialog(self, _('Delete Learned Rules?'), _('Do you want delete all learned rules used for ranking?'), 
                             subtitle=_('<i>This action is permanent. Relearning rules can be time consuming</i>'),  emblem='dialog-warning-symbolic')
        dialog.run()
        if dialog.response == 1:
            dialog.destroy()
            dialog2 = YesNoDialog(self, _('Delete Learned Rules?'), _('Are you sure?'), emblem='dialog-warning-symbolic')
            dialog2.run()
            if dialog2.response == 1:
                err = self.DB.delete_learned_rules()
                if err == 0: 
                    if self.learned_rules_tab != -1: self._get_upn_page_obj(self.learned_rules_tab).query(None)
            dialog2.destroy()
        else: dialog.destroy()
        



    def relearn_rules_thr(self, *args):
        DB = FeedexDatabase(connect=True)
        DB.recalculate(learn=True, rank=False, index=False)
        DB.close()
        if self.learned_rules_tab != -1: self._get_upn_page_obj(self.learned_rules_tab).query(None)
        fdx.busy = False
        fdx.bus_append(FX_ACTION_UNBLOCK_DB)


    def relearn_rules(self, *args):
        """ Wrapper for relearning rules """
        if fdx.busy: return -1
        if not self._fetch_lock(): return 0
        dialog = YesNoDialog(self, _('Relearn Ranking Rules?'), _('Do you want to relearn rules for Ranking from read/marked entries?'), 
                             subtitle=_('<i>This may take a long time</i>'),  emblem='applications-engineering-symbolic')
        dialog.run()
        if dialog.response == 1:
            fdx.bus_append(FX_ACTION_BLOCK_DB)
            fdx.busy = True
            t = threading.Thread(target=self.relearn_rules_thr)
            t.start()
        dialog.destroy()








    ####################################################
    # Porting
    #           Below are wrappers for porting data


    def chooser(self, parent, *args, **kargs):
        """ File chooser for porting """
        action = kargs.get('action', 'open_file')
        start_dir = kargs.get('start_dir', os.getcwd())

        if action == 'save':
            header = kargs.get('header',_('Save as...'))
            dialog = Gtk.FileChooserDialog(header, parent=parent, action=Gtk.FileChooserAction.SAVE)
            dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        elif action == 'open_file':
            header = kargs.get('header',_('Open File'))
            dialog = Gtk.FileChooserDialog(header, parent=parent, action=Gtk.FileChooserAction.OPEN)
            dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        elif action == 'open_dir':
            header = kargs.get('header',_('Open Folder'))
            dialog = Gtk.FileChooserDialog(header, parent=parent, action=Gtk.FileChooserAction.SELECT_FOLDER)
            dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)

        dialog.set_current_folder(kargs.get('start_dir', os.getcwd()))
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
        else: filename = False
        dialog.destroy()

        if action == 'save':
            if os.path.isfile(filename):
                dialog = YesNoDialog(self, f'{_("Overwrite?")}', f'{_("File ")}<b>{esc_mu(filename)}</b>{_(" already exists!   Do you want to overwrite it?")}')
                dialog.run()
                if dialog.response == 1: os.remove(filename)
                else: filename = False
                dialog.destroy()
            elif os.path.isdir(filename):
                msg(FX_ERROR_IO, _('Target %a is a directory!'), filename)
                filename = False

        if filename in ('',None,False,): filename = False
        else: self.gui_cache['last_dir'] = os.path.dirname(filename)

        return filename




    def export_feeds(self, *args):
        filename = self.chooser(self, action='save', start_dir=self.gui_cache.get('last_dir', os.getcwd()), header=_('Export Feed data to...') )
        if filename is False: return 0
        feedex_cli = FeedexCLI()
        feedex_cli.output = 'json_dict'
        feedex_cli.ofile = filename
        self.DB.Q.list_feeds(all=True)
        feedex_cli.out_table(self.DB.Q)


    def export_rules(self, *args):
        filename = self.chooser(self, action='save', start_dir=self.gui_cache.get('last_dir', os.getcwd()), header=_('Export Rules to...') )
        if filename is False: return 0
        feedex_cli = FeedexCLI()
        feedex_cli.output = 'json_dict'
        feedex_cli.ofile = filename
        self.DB.Q.list_rules()
        feedex_cli.out_table(self.DB.Q)



    def export_flags(self, *args):
        filename = self.chooser(self, action='save', start_dir=self.gui_cache.get('last_dir', os.getcwd()), header=_('Export Flags to...') )
        if filename is False: return 0
        feedex_cli = FeedexCLI()
        feedex_cli.output = 'json_dict'
        feedex_cli.ofile = filename
        self.DB.Q.list_flags(all=True)
        feedex_cli.out_table(self.DB.Q)

    def export_plugins(self, *args):
        filename = self.chooser(self, action='save', start_dir=self.gui_cache.get('last_dir', os.getcwd()), header=_('Export Plugins to...') )
        if filename is False: return 0
        save_json(filename, self.gui_plugins)




    def import_feeds(self, *args):
        if not self._fetch_lock(): return 0
        if fdx.busy: return -1

        filename = self.chooser(self, action='open_file', start_dir=self.gui_cache.get('last_dir', os.getcwd()), header=_('Import Feeds from...') )
        if filename is False: return 0

        err = self.DB.import_feeds(filename)
        if err == 0: 
            self.feed_tab.reload()

            dialog = YesNoDialog(self, _('Update Feed Data'), _('New feed data has been imported. Download Metadata now?') )
            dialog.run()
            if dialog.response == 1: self.on_update_feed_all()
            dialog.destroy()


    def import_rules(self, *args):
        if not self._fetch_lock(): return 0
        if fdx.busy: return -1

        filename = self.chooser(self, action='open_file', start_dir=self.gui_cache.get('last_dir', os.getcwd()), header=_('Import Rules from...') )
        if filename is False: return 0

        err = self.DB.import_rules(filename)
        if err == 0: 
            if self.rules_tab != -1: self._get_upn_page_obj(self.rules_tab).query('',{})


    def import_flags(self, *args):
        if not self._fetch_lock(): return 0
        if fdx.busy: return -1

        filename = self.chooser(self, action='open_file', start_dir=self.gui_cache.get('last_dir', os.getcwd()), header=_('Import Flags from...') )
        if filename is False: return 0

        err = self.DB.import_flags(filename)
        if err == 0: 
            if self.flags_tab != -1: self._get_upn_page_obj(self.flags_tab).query('',{})



    def import_entries_thr(self, efile, **kargs):
        DB = FeedexDatabase(connect=True)
        err = DB.import_entries(efile=efile)
        DB.close()
        fdx.busy = False
        fdx.bus_append(FX_ACTION_UNBLOCK_DB)


    def import_entries(self, *args):
        filename = self.chooser(self, action='open_file', start_dir=self.gui_cache.get('last_dir', os.getcwd()), header=_('Import Entries from...') )
        if filename is False: return 0
        if not self._fetch_lock(): return 0
        fdx.busy = True
        fdx.bus_append(FX_ACTION_BLOCK_DB)
        t = threading.Thread(target=self.import_entries_thr, args=(filename,))
        t.start()



    def import_plugins(self, *args):
        filename = self.chooser(self, action='open_file', start_dir=self.gui_cache.get('last_dir', os.getcwd()), header=_('Import Plugins from...') )
        if filename is False: return 0

        new_plugins = validate_gui_plugins( load_json(filename, [], create_file=False) )
        if len(new_plugins) > 0:
            self.gui_plugins = list(self.gui_plugins)
            max_id = len(self.gui_plugins) + 1
            for p in new_plugins:
                p[FX_PLUGIN_TABLE.index('id')] = max_id
                max_id += 1
                self.gui_plugins.append(p)
            
            err = save_json(FEEDEX_GUI_PLUGINS, self.gui_plugins)
            if err == 0: 
                if self.plugins_tab != -1: self._get_upn_page_obj(self.plugins_tab).query('',{})
                msg(_('Plugins imported successfully...'))




    def export_results(self, *args, **kargs):
        """ Export results from current tab to JSON for later import """
        if self.curr_upper.type in (FX_TAB_RULES, FX_TAB_FLAGS): return 0
        format = args[-1]

        if not isinstance(self.curr_upper.table.result, (ResultEntry, ResultContext, ResultTerm, ResultTimeSeries,)): return -1
        if isinstance(self.curr_upper.table.result, ResultEntry): result = ResultEntry()
        elif isinstance(self.curr_upper.table.result, ResultContext): result = ResultContext()
        elif isinstance(self.curr_upper.table.result, ResultTerm): result = ResultTerm()
        elif isinstance(self.curr_upper.table.result, ResultTimeSeries): result = ResultTimeSeries()
        else: return 0

        query = FeedexQueryInterface()        
        query.result =  result
        query.results = self.curr_upper.table.results
        query.result_no = len(query.results)
        query.result_no2 = 0
        
        if query.result_no == 0:
            msg(_('Nothing to export.') )
            return 0
        
        if kargs.get('filename') is None:
            filename = self.chooser(self, action='save', start_dir=self.gui_cache.get('last_dir', os.getcwd()), header=_('Export to...') )
        else:
            filename = kargs.get('filename')
        
        if filename in (False,None): return 0

        feedex_cli = FeedexCLI()
        feedex_cli.output = format
        feedex_cli.ofile = filename
        feedex_cli.out_table(query)



    def import_catalog_thr(self, item, **args):
        """ Import feeds from catalog - threading """
        DB = FeedexDatabase(connect=True)
        item.DB = DB
        item.feed.set_interface(DB)
        item.do_import()
        DB.close()
        fdx.busy = False
        fdx.bus_append(FX_ACTION_UNBLOCK_DB)
        fdx.bus_append(FX_ACTION_RELOAD_FEEDS)


    def import_catalog(self, *args, **kargs):
        """ Import feeds from Catalog """
        item = args[-1]
        if not isinstance(item, FeedexCatItem): return 0
        item.prep_import()
        if item.queue_len == 0: return 0

        dialog = YesNoDialog(self, _('Subscribe...'), f"""{_('Subscribe to')} <b>{item.queue_len}</b> {_('Channels?')}""", emblem='rss-symbolic')
        dialog.run()
        if dialog.response == 1:
            if not self._fetch_lock(): return 0
            fdx.busy = True
            fdx.bus_append(FX_ACTION_BLOCK_DB)
            t = threading.Thread(target=self.import_catalog_thr, args=(item,))
            t.start()
        dialog.destroy()






#################################################
#       UTILITIES
#

    def quick_find_case_ins(self, model, column, key, rowiter, *args):
        """ Guick find 'equals' fundction - case insensitive """
        column=args[-1]
        row = model[rowiter]
        if key.lower() in scast(list(row)[column], str, '').lower(): return False
        return True

    def quick_find_case_ins_tree(self, model, column, key, rowiter, *args):
        """ Quick find 'equals' function - basically case insensitivity """
        column = args[-1]
        tree = args[-2]
        row = model[rowiter]
        if key.lower() in scast(list(row)[column], str, '').lower(): return False

        # Search in child rows.  If one of the rows matches, expand the row so that it will be open in later checks.
        for inner in row.iterchildren():
            if key.lower() in scast(list(inner)[column], str, '').lower():
                tree.expand_to_path(row.path)
                return False
        return True




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














def feedex_run_main_win(*args, **kargs):
    """ Runs main Gtk loop with main Feedex window"""
    win = FeedexMainWin(*args, **kargs)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
