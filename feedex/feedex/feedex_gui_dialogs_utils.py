# -*- coding: utf-8 -*-
""" GUI dialog windows classes for FEEDEX """


from feedex_gui_utils import *







class BasicDialog(Gtk.Dialog):
    """Info Dialog - no choice """

    def __init__(self, parent, title, text, **kargs):

        Gtk.Dialog.__init__(self, title=title, transient_for=parent, flags=0)
        self.set_default_size(kargs.get('width',400), kargs.get('height',50))        
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_border_width(10)

        self.response = 0


        justify = kargs.get('justify', FX_ATTR_JUS_CENTER)
        if justify in (FX_ATTR_JUS_CENTER, FX_ATTR_JUS_FILL,): xalign = 0.5
        elif justify == FX_ATTR_JUS_LEFT: xalign = 0
        elif justify == FX_ATTR_JUS_RIGHT: xalign = 1
        else: xalign = 0.5

        selectable = kargs.get('selectable', False)
        markup = kargs.get('markup', True)

        subt = kargs.get('subtitle')
        scrolled = kargs.get('scrolled', False)
        emblem = kargs.get('emblem')
        image = kargs.get('image')
        pixbuf = kargs.get('pixbuf')
        buttons = kargs.get('buttons', 1)


        box = self.get_content_area()
        box.set_homogeneous(False)

        top_box = Gtk.VBox()
        top_box.set_homogeneous(False)
        top_box.set_border_width(5)

        if scrolled: wrap = False
        else: wrap = True

        if emblem is not None:
            image = Gtk.Image.new_from_icon_name(emblem, Gtk.IconSize.DIALOG)
            top_box.pack_start(image, False, False, 3)
        elif image is not None:
            pb = GdkPixbuf.Pixbuf.new_from_file_at_size(os.path.join(FEEDEX_SYS_ICON_PATH,image), 64, 64)
            image = Gtk.Image.new_from_pixbuf(pb)
            top_box.pack_start(image, False, False, 3)
        elif pixbuf is not None:
            image = Gtk.Image.new_from_pixbuf(pixbuf)
            top_box.pack_start(image, False, False, 3)

        if scrolled: text = f"""{text}\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n"""
        label = f_label(text, justify=justify, selectable=selectable, wrap=wrap, markup=markup, xalign=xalign)
        if not scrolled:
            top_box.pack_start(label, True, False, 3)
            if subt is not None:
                sublabel = f_label(subt, justify=justify, selectable=selectable, wrap=True, markup=markup, xalign=xalign)
                top_box.pack_start(sublabel, True, False, 3)
             
        else:
            scr_window = Gtk.ScrolledWindow()
            scr_window.add(label)
            top_box.pack_start(scr_window, True, True, 3)



        bottom_box = Gtk.HBox()
        bottom_box.set_border_width(10)

        if buttons == 1: # Single-button info version
            bottom_box.set_homogeneous(True)
            button = f_button(kargs.get('button_text',_('Done')),'object-select-symbolic', connect=self.on_close)
            bottom_box.pack_end(button, False, False, 3)
        
        elif buttons == 2: # Yes/No version
            bottom_box.set_homogeneous(False)
            yes_button = f_button(_('Yes'),'object-select-symbolic', connect=self.on_yes)
            no_button = f_button(_('No'),'action-unavailable-symbolic', connect=self.on_no)
            bottom_box.pack_start(no_button, False, False, 5)
            bottom_box.pack_end(yes_button, False, False, 5)

        box.pack_start(top_box, True, True, 3)
        box.pack_start(bottom_box, False, False, 3)
            
        self.show_all()



    def on_close(self, *args):
        self.response = None
        self.close()

    def on_yes(self, *args):
        self.response = 1
        self.close()

    def on_no(self, *args):
        self.response = 0
        self.close()




class YesNoDialog(BasicDialog):
    def __init__(self, parent, title, text, **kargs):
        kargs['buttons'] = 2
        super().__init__(parent, title, text, **kargs)





























class PreferencesDialog(Gtk.Dialog):
    """ Edit preferences dialog """
    def __init__(self, parent, **kargs):

        self.parent = parent
        self.config = parent.config.copy()
        self.config_def = parent.config.copy()

        Gtk.Dialog.__init__(self, title=_('FEEDEX Preferences'), transient_for=parent, flags=0)
        box = self.get_content_area()

        self.set_border_width(10)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)


        self.result = {}
        self.response = 0        

        # Markers if reloads, restarts etc. are required
        self.restart = False
        self.reload = False
        self.reload_lang = False
        self.reload_decor = False


        self.desktop_notify_button = Gtk.CheckButton.new_with_label(_('Enable desktop notifications?') )
        self.desktop_notify_button.connect('clicked', self.on_changed)
        self.desktop_notify_button.set_tooltip_markup(_('Should Feedex send desktop notifications on incomming news?') )
        self.fetch_in_background_button = Gtk.CheckButton.new_with_label(_('Fetch news in the background?') )
        self.fetch_in_background_button.set_tooltip_markup(_('News will be checked in background and downloaded if Channels\'s fetching interval is exceeded'))
        
        default_interval_label = f_label(_('Default check interval:'))
        self.default_interval_entry = Gtk.Entry()
        self.default_interval_entry.set_tooltip_markup(_('Default fetching interval for newly added feeds'))
        
        rule_limit_label = f_label(_('Ranking rules limit:'))
        self.rule_limit_entry = Gtk.Entry()
        self.rule_limit_entry.set_tooltip_markup(_("""When ranking incomming news you can 
limit the number of rules to match.
Only those with N top weight will be checked.
This can help avoid unimportant terms influencing ranking
and prevent scaling problems for large datasets
Enter <b>0</b> for <b>no rule limit</b> (every rule will be checked)"""))

        self.learn_button = Gtk.CheckButton.new_with_label(_('Enable Keyword learning?'))
        self.learn_button.set_tooltip_markup(_("""If enabled, keywords are extracted and learned 
every time an article is read or marked as read.
Incomming news are then ranked agains the rules from those extracted keywords.
Feedex uses this ranking to get articles most likely interesting to you on top.
If disabled, no learning will take place and ranking will be done only against rules
that were manually added by user."""))


        self.notify_group_combo = f_group_combo(with_empty=True, with_number=True, connect=self.on_changed, tooltip=_("""Should incoming news be grouped? How?
<b>No grouping</b> - all results will be pushed
<b>Just number</b> - just a notification about the number of new articles""") )

        self.notify_depth_combo = f_depth_combo(tooltip=_("""How many results should be shown for each grouping?
If no grouping is selected, it will simply show top results"""))

        default_entry_weight_label = f_label(_('New Entry default weight:'))
        self.default_entry_weight_entry = Gtk.Entry()
        self.default_entry_weight_entry.set_tooltip_markup(_('Default weight/read value for manually added Entries for rule learning. If 0 then no learning will take place when adding new article'))

        default_rule_weight_label = f_label(_('Rule default weight:'))
        self.default_rule_weight_entry = Gtk.Entry()
        self.default_rule_weight_entry.set_tooltip_markup(_('Default weight assigned to manually added rule (if not provided)'))

        default_similar_wieght_label = f_label(_('Weight for similarity search:'))
        self.default_similar_weight_entry = Gtk.Entry()
        self.default_similar_weight_entry.set_tooltip_markup(_('How much weight for ranking should items for which similar ones are searched for be given. Zero to disable'))
        
        ranking_scheme_label = f_label(_('Incomming articles ranking scheme:'))
        self.ranking_scheme_combo = f_ranking_scheme_combo()


        new_color_label = f_label(_('Added entry color:'))
        new_color = Gdk.color_parse(self.config.get('gui_new_color','#0FDACA'))
        self.new_color_button = Gtk.ColorButton(color=new_color)

        del_color_label = f_label(_('Deleted color:'))
        del_color = Gdk.color_parse(self.config.get('gui_deleted_color','grey'))
        self.del_color_button = Gtk.ColorButton(color=del_color)

        hl_color_label = f_label(_('Search hilight color:'))
        hl_color = Gdk.color_parse(self.config.get('gui_deleted_color','grey'))
        self.hl_color_button = Gtk.ColorButton(color=hl_color)

        def_flag_color_label = f_label(_('Default flag color:'))
        def_flag_color = Gdk.color_parse(self.config.get('gui_default_flag_color','blue'))
        self.def_flag_color_button = Gtk.ColorButton(color=def_flag_color)


        key_new_entry_label = f_label(_('Hotkey, add New Entry: Ctrl + '))
        self.key_new_entry_entry = Gtk.Entry()

        key_new_rule_label = f_label(_('Hotkey, add New Rule: Ctrl + '))
        self.key_new_rule_entry = Gtk.Entry()

        key_add_label = f_label(_('Hotkey, add new Item in a tab: Ctrl + '))
        self.key_add_entry = Gtk.Entry()

        key_edit_label = f_label(_('Hotkey, edit item from a tab: Ctrl + '))
        self.key_edit_entry = Gtk.Entry()

        key_search_label = f_label(_('Hotkey, start search from a tab: Ctrl + '))
        self.key_search_entry = Gtk.Entry()



        layout_label = f_label(_('Layout:'))
        self.layout_combo = f_layout_combo(tooltip=_('How main window panes should be displayed? Requires restart'))

        orientation_label = f_label(_('Orientation:'))
        self.orientation_combo = f_orientation_combo(tooltip=_('Pane horizontal sequence'))

        lang_label = f_label(_('Language:'))
        self.lang_combo = f_loc_combo()

        browser_label = f_label(_('Default WWW browser:'))
        self.browser_entry = Gtk.Entry()
        self.browser_entry.set_tooltip_markup(_('Command for opening in browser. Use <b>u%</b> symbol to substitute for URL'))
        browser_application_button = f_button(None,'view-app-grid-symbolic', connect=self.on_app_choose_browser, tooltip=_("Choose from installed applications"))

        self.external_iv_application_button = f_button(None,'view-app-grid-symbolic', connect=self.on_app_choose_iv, tooltip=_("Choose from installed applications"))
        external_iv_label = f_label(_('External image viewer:'))
        self.external_iv_entry = Gtk.Entry()
        self.external_iv_entry.set_tooltip_markup(_('Command for viewing images by clicking on them.\nUse <b>%u</b> symbol to substitute for temp filename\n<b>%t</b> symbol will be replaced by <b>title</b>\n<b>%a</b> symbol will be replaced by <b>alt</b> field'))


        search_engine_label = f_label(_('Default WWW search engine:'))
        search_engine_combo, self.search_engine_entry = f_search_engine_combo()
        

        similarity_limit_label = f_label(_('Similarity query limit:'))
        self.similarity_limit_entry = Gtk.Entry()
        self.similarity_limit_entry.set_tooltip_markup(_('Limit similarity query items for improved query performance'))

        max_context_length_label = f_label(_('Max context length:'))
        self.max_context_length_entry = Gtk.Entry()
        self.max_context_length_entry.set_tooltip_markup(_('If the length of a context/snippet is greater than this number, it will not be shown in query results. Needed to avoid long snippets for wildcard searches'))

        default_depth_label = f_label(_('Default grouping depth:'))
        self.default_depth_entry = Gtk.Entry()
        self.default_depth_entry.set_tooltip_markup(_('How many results to show when grouping in a tree? If <b>0</b>, every result will be displayed'))


        error_threshold_label = f_label(_('Error threshold:'))
        self.error_threshold_entry = Gtk.Entry()
        self.error_threshold_entry.set_tooltip_markup(_('After how many download errors should a Channel be marked as unhealthy and ignored while fetching?'))

        self.ignore_modified_button = Gtk.CheckButton.new_with_label(_('Ignore modified Tags?'))
        self.ignore_modified_button.set_tooltip_markup(_('Should ETags and Modified fields be ignored while fetching? If yes, Feedex will fetch news even when publisher suggest not to (e.g. no changes where made to feed)'))

        clear_cache_label = f_label(_('Clear cached files older than how many days?'))
        self.clear_cache_entry = Gtk.Entry()
        self.clear_cache_entry.set_tooltip_markup(_('Files in cache include thumbnails and images. It is good to keep them but older items should release space'))

        db_label = f_label(_('Database:'))
        db_choose_button = f_button(None,'folder-symbolic', connect=self.on_file_choose_db, tooltip=_("Search filesystem"))
        self.db_entry = Gtk.Entry()
        self.db_entry.set_tooltip_markup(f"{_('Feedex database to be used.')}\n<i>{_('Changes require application restart')}</i>")

        db_timeout_label = f_label(_('Timeout:'))
        self.db_timeout_entry = Gtk.Entry()
        self.db_timeout_entry.set_tooltip_markup(_("""This timeout tells after how many seconds should operation on busy database be aborted"""))

        log_label = f_label('Log file:')
        log_choose_button = f_button(None,'folder-symbolic', connect=self.on_file_choose_log, tooltip=_("Search filesystem"))
        self.log_entry = Gtk.Entry()
        self.log_entry.set_tooltip_markup(_("Path to log file"))

        user_agent_label = f_label(_('User Agent:'))
        user_agent_combo, self.user_agent_entry = f_user_agent_combo(tooltip=f"""{_('User Agent string to be used when requesting URLs. Be careful, as some publishers are very strict about that.')} 
{_('Default is:')} {FEEDEX_USER_AGENT}
<b>{_('Changing this tag is not recommended and for debugging purposes only')}</b>""")

        fetch_timeout_label = f_label(_('Timeout:'))
        self.fetch_timeout_entry = Gtk.Entry()
        self.fetch_timeout_entry.set_tooltip_markup(_("Timeout for fetching remote resources"))
    
        profile_name_label = f_label(_('Profile name:'))
        self.profile_name_entry = Gtk.Entry()
        self.profile_name_entry.set_tooltip_markup(_("""Name of this configuration profile.
If configuration has a name, its sessions are treated as separate with regards to caching, attributes and plugins"""))

        win_name_excl_label = f_label(_('Exclude from Window Name:'))
        self.win_name_excl_entry = Gtk.Entry()
        self.win_name_excl_entry.set_tooltip_markup(_("""These are comma-separated phrases to exclude when using window name with --clipboard option.
It will prevent littering database with Mozilla, Chrome, Safar headers when adding entries by a Hotkey script.        
"""))

        self.do_redirects_button = Gtk.CheckButton.new_with_label(_('Redirect?'))
        self.do_redirects_button.set_tooltip_markup(_('Should HTTP redirects (codes:301, 302) be followed when fetching?'))

        self.save_redirects_button = Gtk.CheckButton.new_with_label(_('Save permanent redirects?'))
        self.save_redirects_button.set_tooltip_markup(_('Should permanent HTTP redirects (code: 301) be saved to DB?'))

        self.mark_deleted_button = Gtk.CheckButton.new_with_label(_('Mark deleted channels as unhealthy?'))
        self.mark_deleted_button.set_tooltip_markup(_('Should deleted channels (HTTP code 410) be marked as unhealthy to avoid fetching in the future?'))

        self.no_history_button = Gtk.CheckButton.new_with_label(_('Do not save queries in History?'))
        self.no_history_button.set_tooltip_markup(_('Should saving search phrases to History be ommitted?'))


        self.err_label = f_label('', markup=True)

        self.save_button = f_button(_('Save'),'object-select-symbolic', connect=self.on_save, tooltip=_("Save configuration") )
        self.cancel_button = f_button(_('Cancel'),'action-unavailable-symbolic', connect=self.on_cancel)
        self.restore_button = f_button(_('Restore'),'edit-redo-rtl-symbolic', connect=self.on_restore, tooltip=_("Restore preferences to defaults") )


        def create_grid():
            grid = Gtk.Grid()
            grid.set_column_spacing(8)
            grid.set_row_spacing(8)
            grid.set_column_homogeneous(False)
            grid.set_row_homogeneous(False)
            grid.set_border_width(5)
            return grid
        
        interface_grid = create_grid()    
        interface_grid.attach(lang_label, 1, 1, 3, 1)
        interface_grid.attach(self.lang_combo, 4, 1, 4,1)        
        interface_grid.attach(layout_label, 1, 2, 3, 1)
        interface_grid.attach(self.layout_combo, 4, 2, 4,1)        
        interface_grid.attach(orientation_label, 1, 3, 3, 1)
        interface_grid.attach(self.orientation_combo, 4, 3, 4,1)        
        interface_grid.attach(new_color_label, 1,5, 3,1)
        interface_grid.attach(self.new_color_button, 4,5, 1,1)
        interface_grid.attach(del_color_label, 1,6, 3,1)
        interface_grid.attach(self.del_color_button, 4,6, 1,1)
        interface_grid.attach(hl_color_label, 1,7, 3,1)
        interface_grid.attach(self.hl_color_button, 4,7, 1,1)
        interface_grid.attach(def_flag_color_label, 1,8, 3,1)
        interface_grid.attach(self.def_flag_color_button, 4,8, 1,1)

        interface_grid.attach(key_new_entry_label, 7, 5, 3, 1)
        interface_grid.attach(self.key_new_entry_entry, 10, 5, 1,1)
        interface_grid.attach(key_new_rule_label, 7, 6, 3, 1)
        interface_grid.attach(self.key_new_rule_entry, 10, 6, 1,1)        
        interface_grid.attach(key_add_label, 7, 7, 3, 1)
        interface_grid.attach(self.key_add_entry, 10, 7, 1,1)
        interface_grid.attach(key_edit_label, 7, 8, 3, 1)
        interface_grid.attach(self.key_edit_entry, 10, 8, 1,1)        
        interface_grid.attach(key_search_label, 7, 9, 3, 1)
        interface_grid.attach(self.key_search_entry, 10, 9, 1,1)        

        fetching_grid = create_grid()
        fetching_grid.attach(self.desktop_notify_button, 1,1, 4,1)
        fetching_grid.attach(self.notify_group_combo, 5,1, 5,1)
        fetching_grid.attach(self.notify_depth_combo, 11,1, 4,1)
        fetching_grid.attach(self.fetch_in_background_button, 1,2, 4,1)
        fetching_grid.attach(default_interval_label, 1,3, 2,1)
        fetching_grid.attach(self.default_interval_entry, 4,3, 3,1)
        fetching_grid.attach(self.do_redirects_button, 1,4, 4,1)
        fetching_grid.attach(self.save_redirects_button , 1,5, 4,1)
        fetching_grid.attach(self.mark_deleted_button, 1,6, 4,1)
        fetching_grid.attach(self.ignore_modified_button, 1,7, 5,1)
        fetching_grid.attach(error_threshold_label, 1,8, 2,1)
        fetching_grid.attach(self.error_threshold_entry, 4,8, 3,1)
        fetching_grid.attach(user_agent_label, 1,9, 2,1)
        fetching_grid.attach(user_agent_combo, 4,9, 3,1)
        fetching_grid.attach(fetch_timeout_label, 1,10, 2,1)
        fetching_grid.attach(self.fetch_timeout_entry, 4,10, 2,1)


        learn_grid = create_grid()
        learn_grid.attach(self.learn_button, 1,1, 6,1)
        learn_grid.attach(rule_limit_label, 1,2, 3,1)
        learn_grid.attach(self.rule_limit_entry, 4,2, 3,1)
        learn_grid.attach(similarity_limit_label, 1,5, 4,1)
        learn_grid.attach(self.similarity_limit_entry, 5,5, 3,1)
        learn_grid.attach(max_context_length_label, 1,6,4,1)
        learn_grid.attach(self.max_context_length_entry, 5,6,3,1)
        learn_grid.attach(default_depth_label, 1,7,4,1)
        learn_grid.attach(self.default_depth_entry, 5,7,2,1)
        
        learn_grid.attach(default_entry_weight_label, 1,8, 3,1)
        learn_grid.attach(self.default_entry_weight_entry, 4,8, 3,1)
        learn_grid.attach(default_rule_weight_label, 1, 9, 3,1)
        learn_grid.attach(self.default_rule_weight_entry, 4, 9, 3,1)
        learn_grid.attach(default_similar_wieght_label, 1,10,4,1)
        learn_grid.attach(self.default_similar_weight_entry, 5, 10, 3,1)
        learn_grid.attach(ranking_scheme_label, 1,11,4,1)
        learn_grid.attach(self.ranking_scheme_combo, 5, 11, 3,1)


        system_grid = create_grid()
        system_grid.attach(db_label, 1,1, 3,1)
        system_grid.attach(db_choose_button, 4,1, 1,1)
        system_grid.attach(self.db_entry, 5,1, 10,1)
        system_grid.attach(db_timeout_label, 16,1, 2,1)
        system_grid.attach(self.db_timeout_entry, 18,1, 3,1)

        system_grid.attach(log_label, 1,2, 3,1)
        system_grid.attach(log_choose_button, 4,2, 1,1)
        system_grid.attach(self.log_entry, 5,2, 10,1)
        system_grid.attach(self.no_history_button, 1,4, 7,1)

        system_grid.attach(browser_label, 1,5, 4,1)
        system_grid.attach(browser_application_button, 5,5, 1,1)
        system_grid.attach(self.browser_entry, 6,5, 20,1)
        system_grid.attach(external_iv_label, 1,6, 4,1)
        system_grid.attach(self.external_iv_application_button, 5,6, 1,1)
        system_grid.attach(self.external_iv_entry, 6,6, 20,1)
        system_grid.attach(search_engine_label, 1,8, 4,1)
        system_grid.attach(search_engine_combo, 6,8, 20,1)
        system_grid.attach(win_name_excl_label, 1,9, 4,1)
        system_grid.attach(self.win_name_excl_entry, 6,9, 20,1)

        system_grid.attach(clear_cache_label, 1,10, 5,1)
        system_grid.attach(self.clear_cache_entry, 7,10, 3,1)

        system_grid.attach(profile_name_label, 1,11, 5,1)
        system_grid.attach(self.profile_name_entry, 7,11, 3,1)



        self.notebook = Gtk.Notebook()
        self.notebook.append_page(interface_grid, Gtk.Label(label=_("Interface")))
        self.notebook.append_page(fetching_grid, Gtk.Label(label=_("Fetching")))    
        self.notebook.append_page(learn_grid, Gtk.Label(label=_("Learning and Ranking")))
        self.notebook.append_page(system_grid, Gtk.Label(label=_("System")))    
    
        grid = create_grid()
        grid.attach(self.notebook, 1,1, 18,13)
        grid.attach(self.err_label, 1,14, 16,1)

        vbox = Gtk.Box()
        vbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        vbox.set_homogeneous(False)
        vbox.set_border_width(5)

        vbox.pack_start(self.cancel_button, False, False, 5)
        vbox.pack_start(self.restore_button, False, False, 5)
        vbox.pack_end(self.save_button, False, False, 5)
            
        box.add(grid)
        box.add(vbox)

        self.on_restore()
        self.on_changed()

        self.show_all()



    def on_changed(self, *args):
        if self.desktop_notify_button.get_active(): 
            self.notify_group_combo.set_sensitive(True)
            self.notify_depth_combo.set_sensitive(True)
        else:
            self.notify_group_combo.set_sensitive(False)
            self.notify_depth_combo.set_sensitive(False)



    def on_file_choose_db(self, *args): 
        filename = f_chooser(self, self.parent, action='open_dir', start_dir=os.path.dirname(self.config.get('db_path')), header=_('Choose Database...'))
        if filename is not False: self.db_entry.set_text(filename)       

    def on_file_choose_log(self, *args):
        filename = f_chooser(self, self.parent, action='open_file', start_dir=os.path.dirname(self.config.get('log')), header=_('Choose Log File...'))
        if filename is not False: self.log_entry.set_text(filename)       



    def on_app_choose_browser(self, *args): self.app_choose('browser')
    def on_app_choose_iv(self, *args): self.app_choose('iv')


    def app_choose(self, target):

        if target == 'browser':
            heading = _("Choose Default Browser")
            content_type = "text/html"
        elif target == 'iv':
            heading = _("Choose Image Viewer")
            content_type = "image/jpeg"

        dialog = Gtk.AppChooserDialog(parent=self, content_type=content_type)
        dialog.set_heading(heading)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            app = dialog.get_app_info()
            command = app.get_string('Exec')
            if type(command) is str:
                if target == 'browser':
                    self.browser_entry.set_text(command)
                elif target == 'iv':
                    self.external_iv_entry.set_text(command)
        dialog.destroy()





    def on_restore(self, *args):

        self.profile_name_entry.set_text(scast(self.config.get('profile_name'), str, ''))

        if self.config.get('use_keyword_learning', True): self.learn_button.set_active(True)
        else: self.learn_button.set_active(False)

        self.rule_limit_entry.set_text(scast(self.config.get('rule_limit', 50000), str, _('<<ERROR>>')))

        if self.config.get('gui_desktop_notify',True): self.desktop_notify_button.set_active(True)
        else: self.desktop_notify_button.set_active(False)

        f_set_combo(self.notify_group_combo, self.config.get('gui_notify_group','feed'))
        f_set_combo(self.notify_depth_combo, self.config.get('gui_notify_depth',5))

        if self.config.get('gui_fetch_periodically',False): self.fetch_in_background_button.set_active(True)
        else: self.fetch_in_background_button.set_active(False)

        if self.config.get('do_redirects', False): self.do_redirects_button.set_active(True)
        else: self.do_redirects_button.set_active(False)

        if self.config.get('save_perm_redirects', False): self.save_redirects_button.set_active(True)
        else: self.save_redirects_button.set_active(False)

        if self.config.get('mark_deleted', False): self.mark_deleted_button.set_active(True)
        else: self.mark_deleted_button.set_active(False)


        self.default_interval_entry.set_text(scast(self.config.get('default_interval',45), str, _('<<ERROR>>')))

        self.default_entry_weight_entry.set_text(scast(self.config.get('default_entry_weight',2), str, _('<<ERROR>>')))

        self.default_rule_weight_entry.set_text(scast(self.config.get('default_rule_weight',2), str, _('<<ERROR>>')))

        self.default_similar_weight_entry.set_text(scast(self.config.get('default_similar_weight',2), str, _('<<ERROR>>')))

        f_set_combo(self.ranking_scheme_combo, self.config.get('ranking_scheme','simple'))

        self.max_context_length_entry.set_text(scast(self.config.get('max_context_length',500), str, _('<<ERROR>>')))
        self.default_depth_entry.set_text(scast(self.config.get('default_depth',5), str, _('<<ERROR>>')))


        new_color = Gdk.color_parse(self.config.get('gui_new_color','#0FDACA'))
        self.new_color_button.set_color(new_color)
        del_color = Gdk.color_parse(self.config.get('gui_deleted_color','grey'))
        self.del_color_button.set_color(del_color)
        hl_color = Gdk.color_parse(self.config.get('gui_hilight_color','blue'))
        self.hl_color_button.set_color(hl_color)
        def_flag_color = Gdk.color_parse(self.config.get('gui_default_flag_color','blue'))
        self.def_flag_color_button.set_color(def_flag_color)

        f_set_combo(self.layout_combo, self.config.get('gui_layout',0))        
        f_set_combo(self.orientation_combo, self.config.get('gui_orientation',0))        
        f_set_combo(self.lang_combo, self.config.get('lang'))

        self.key_new_entry_entry.set_text(coalesce(self.config.get('gui_key_new_entry','n'), ''))
        self.key_new_rule_entry.set_text(coalesce(self.config.get('gui_key_new_rule','r'), ''))
        self.key_add_entry.set_text(coalesce(self.config.get('gui_key_add','a'), ''))
        self.key_edit_entry.set_text(coalesce(self.config.get('gui_key_edit','e'), ''))
        self.key_search_entry.set_text(coalesce(self.config.get('gui_key_search','e'), ''))

        self.browser_entry.set_text(coalesce(self.config.get('browser',''),''))
        self.external_iv_entry.set_text(coalesce(self.config.get('image_viewer',''),''))
        self.search_engine_entry.set_text(coalesce(self.config.get('search_engine',''),''))

        self.similarity_limit_entry.set_text(scast(self.config.get('default_similarity_limit',''),str,_('<<ERROR>>')))

        self.error_threshold_entry.set_text(scast(self.config.get('error_threshold',''), str,_('<<ERROR>>')))

        self.clear_cache_entry.set_text(scast(self.config.get('gui_clear_cache',30),str,_('<<ERROR>>')))

        if self.config.get('ignore_modified',True): self.ignore_modified_button.set_active(True)
        else: self.ignore_modified_button.set_active(False)

        self.db_entry.set_text(scast(self.config.get('db_path',''), str, _('<<ERROR>>')))
        self.db_timeout_entry.set_text(scast(self.config.get('timeout',''), str, _('<<ERROR>>')))

        self.log_entry.set_text(scast(self.config.get('log',''), str, _('<<ERROR>>')))

        self.user_agent_entry.set_text(scast(self.config.get('user_agent'), str, FEEDEX_USER_AGENT))
        self.fetch_timeout_entry.set_text(scast(self.config.get('fetch_timeout'), str, '0'))

        if self.config.get('no_history', False): self.no_history_button.set_active(True)
        else: self.no_history_button.set_active(False)

        self.win_name_excl_entry.set_text(coalesce(self.config.get('window_name_exclude'),'Firefox,firefox,chrome,Chrome,Mozilla,mozilla,Thunderbird,thunderbird'))

        self.on_changed()


    def validate_entries(self, *args):
        self.get_data()
        err = fdx.validate_config(config=self.result, strict=True, load=False)
        if err != 0:
            self.err_label.set_markup(gui_msg(*err))
            return False
        else: return True




    def get_data(self, *args):

        self.result['profile_name'] = self.profile_name_entry.get_text()

        if self.learn_button.get_active(): self.result['use_keyword_learning'] = True
        else: self.result['use_keyword_learning'] = False

        self.result['rule_limit'] = nullif(self.rule_limit_entry.get_text(),'')

        if self.desktop_notify_button.get_active(): self.result['gui_desktop_notify'] = True
        else: self.result['gui_desktop_notify'] = False
        if self.fetch_in_background_button.get_active(): self.result['gui_fetch_periodically'] = True
        else: self.result['gui_fetch_periodically'] = False

        self.result['default_interval'] = nullif(self.default_interval_entry.get_text(),'')

        self.result['gui_notify_group'] = f_get_combo(self.notify_group_combo)
        self.result['gui_notify_depth'] = f_get_combo(self.notify_depth_combo)

        self.result['default_entry_weight'] = nullif(self.default_entry_weight_entry.get_text(),'')

        if self.do_redirects_button.get_active(): self.result['do_redirects'] = True
        else: self.result['do_redirects'] = False

        if self.save_redirects_button.get_active(): self.result['save_perm_redirects'] = True
        else: self.result['save_perm_redirects'] = False

        if self.mark_deleted_button.get_active(): self.result['mark_deleted'] = True
        else: self.result['mark_deleted'] = False

        self.result['default_rule_weight'] = nullif(self.default_rule_weight_entry.get_text(),'')

        self.result['default_similar_weight'] = nullif(self.default_similar_weight_entry.get_text(),'')

        self.result['ranking_scheme'] = f_get_combo(self.ranking_scheme_combo)

        self.result['max_context_length'] = nullif(self.max_context_length_entry.get_text(),'')
        self.result['default_depth'] = nullif(self.default_depth_entry.get_text(),'')

        color = self.new_color_button.get_color()
        self.result['gui_new_color'] = color.to_string()
        color = self.del_color_button.get_color()
        self.result['gui_deleted_color'] = color.to_string()
        color = self.hl_color_button.get_color()
        self.result['gui_hilight_color'] = color.to_string()
        color = self.def_flag_color_button.get_color()
        self.result['gui_default_flag_color'] = color.to_string()

        self.result['gui_key_new_entry'] = self.key_new_entry_entry.get_text()
        self.result['gui_key_new_rule'] = self.key_new_rule_entry.get_text()
        self.result['gui_key_add'] = self.key_add_entry.get_text()
        self.result['gui_key_edit'] = self.key_edit_entry.get_text()
        self.result['gui_key_search'] = self.key_search_entry.get_text()

        self.result['gui_layout'] = f_get_combo(self.layout_combo)
        self.result['gui_orientation'] = f_get_combo(self.orientation_combo)
        self.result['lang'] = f_get_combo(self.lang_combo)

        self.result['browser'] = nullif(self.browser_entry.get_text(),'')
        self.result['image_viewer'] = nullif(self.external_iv_entry.get_text(),'')
        self.result['search_engine'] = nullif(self.search_engine_entry.get_text(),'')

        self.result['default_similarity_limit'] = nullif(self.similarity_limit_entry.get_text(),'')
        self.result['error_threshold'] = nullif(self.error_threshold_entry.get_text(),'')
        self.result['gui_clear_cache'] = nullif(self.clear_cache_entry.get_text(),'')

        if self.ignore_modified_button.get_active(): self.result['ignore_modified'] = True
        else: self.result['ignore_modified'] = False

        self.result['db_path'] = nullif(self.db_entry.get_text(),'')
        self.result['timeout'] = scast(self.db_timeout_entry.get_text(), int, 120)
        self.result['log'] = nullif(self.log_entry.get_text(),'')
        self.result['user_agent'] = coalesce(nullif(self.user_agent_entry.get_text(),''), FEEDEX_USER_AGENT)
        self.result['fetch_timeout'] = scast(self.fetch_timeout_entry.get_text(), int, 0)
        self.result['window_name_exclude'] = self.win_name_excl_entry.get_text()

        if self.no_history_button.get_active(): self.result['no_history'] = True
        else: self.result['no_history'] = False



    def on_save(self, *args):
        if self.validate_entries():
            if self.result.get('db_path') !=  self.config.get('db_path'): self.restart = True
            if self.result.get('gui_layout') !=  self.config.get('gui_layout'): self.restart = True
            if self.result.get('gui_orientation') !=  self.config.get('gui_orientation'): self.restart = True

            if self.result.get('use_keyword_learning') !=  self.config.get('use_keyword_learning'): self.reload = True
            if self.result.get('rule_limit') !=  self.config.get('rule_limit'): self.reload = True

            if self.result.get('profile_name') !=  self.config.get('profile_name'): self.reload_decor = True

            if self.result.get('lang') !=  self.config.get('lang'): 
                self.restart = True
                self.reload_lang = True

            self.response = 1
            self.close()

    def on_cancel(self, *args):
        self.response = 0
        self.result = {}
        self.close()










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

        self.result['date_string'] = f"""{coalesce(self.result['from_date'], '...')} - {coalesce(self.result['to_date'], '...')}"""
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



















