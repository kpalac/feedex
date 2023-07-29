# -*- coding: utf-8 -*-
""" GUI session class for FEEDEX """



from feedex_gui_utils import *




class FeedexGUIActions:
    """ This is the main container for Feedex GUI actions """
    def __init__(self, parent, **kargs) -> None:
        self.MW = parent
        self.DB = self.MW.DB
        self.config = self.MW.config





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
        if self.DB.locked_fetching():
            dialog = BasicDialog(self.MW, _("Database is Locked for Fetching"), f"<b>{_('Metadata edits are not allowed')}</b>", 
                                subtitle=_("<i>If this message is due to some unforseen error, you can manually unlock database in Preferences->Database->Unlock</i>"), emblem='system-lock-screen-symbolic')
            dialog.run()
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

            self.MW.new_items = scast(self.MW.new_items, int, 0) + DB.new_items
            self.MW.new_n = scast(self.MW.new_n, int, 0) + 1
            self.MW.feed_tab.redecorate_new()

            if self.config.get('gui_desktop_notify', True):
                DB.connect_QP()
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

        self.MW.lock.acquire()
        self.get_icons()
        self.MW.lock.release()

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
            self.MW.new_items = scast(self.MW.new_items, int, 0) + DB.new_items
            self.MW.new_n = scast(self.MW.new_n, int, 1) + 1
            self.MW.feed_tab.redecorate_new()
        
        self.MW.lock.acquire()
        if err == 0: self.MW.new_feed_url.clear()
        self.MW.lock.release()

        DB.close()
        fdx.busy = False
        fdx.bus_append(FX_ACTION_UNBLOCK_FETCH)
        fdx.bus_append(FX_ACTION_RELOAD_FEEDS)



    def on_add_from_url(self, *args):
        """ Adds a new feed from URL - dialog """
        if fdx.busy: return 0
        if not self._fetch_lock(): return 0

        item = FeedexFeed(self.DB)
        item.strict_merge(self.MW.new_feed_url)

        dialog = NewFromURL(self.MW, item)
        dialog.run()
        self.MW.new_feed_url = item.vals.copy()
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
            item.strict_merge(self.MW.new_entry)
        else: 
            item = item.convert(FeedexEntry, self.DB, id=item['id'])
            if not item.exists: return -1
            new = False

        dialog = EditEntry(self.MW, item, new=new)
        dialog.run()
        if new: self.MW.new_entry = item.vals.copy()
        if dialog.response == 1:
            if new: msg(_('Adding entry...') )
            else: msg(_('Writing changes to Entry...') )
            fdx.busy = True
            t = threading.Thread(target=self.edit_entry_thr, args=(new, item, dialog.new_image) )
            t.start()
        dialog.destroy()



    def edit_entry_thr(self, new:bool, item:FeedexEntry, new_image):
        """ Add/Edit Entry low-level interface for threading """
        DB = FeedexDatabase(connect=True)
        item.set_interface(DB)

        if new:
            err = item.add()
            if err == 0:
                fdx.bus_append( (FX_ACTION_ADD, item.vals.copy(), FX_TT_ENTRY, ) )
                self.MW.lock.acquire()
                self.MW.new_entry.clear()
                self.MW.lock.release()
        else:
            err = item.do_update()
            if err == 0: fdx.bus_append( (FX_ACTION_EDIT, item.vals.copy(), FX_TT_ENTRY, ) )
        
        if err == 0:
            if new_image is not None:
                im_file = os.path.join(self.MW.DB.img_path, f"""{item['id']}.img""")
                tn_file = os.path.join(self.MW.DB.cache_path, f"""{item['id']}.img""")
                try:
                    if os.path.isfile(im_file): 
                        os.remove(im_file)
                        os.remove(tn_file)
                    if new_image != -1: copyfile(new_image, im_file)
                except (OSError, IOError,) as e: msg(FX_ERROR_IO, f"""{_('Error importing %a file: ')}{e}""", new_image)

        DB.close()
        fdx.busy = False






    def on_del_entry(self, *args):
        """ Deletes selected entry"""
        item = args[-1]
        if item['deleted'] != 1: dialog = YesNoDialog(self.MW, _('Delete Entry'), f'{_("Are you sure you want to delete")} <i><b>{esc_mu(item.name())}</b></i>?')
        else: dialog = YesNoDialog(self.MW, _('Delete Entry permanently'), f'{_("Are you sure you want to permanently delete")} <i><b>{esc_mu(item.name())}</b></i> {_("and associated rules?")}')
        dialog.run()
        if dialog.response == 1: self.on_mark('delete', item)
        dialog.destroy()


    def on_restore_entry(self, *args):
        """ Restore entry """
        item = args[-1]
        dialog = YesNoDialog(self.MW, _('Restore Entry'), f'{_("Are you sure you want to restore")} <i><b>{esc_mu(item.name())}</b></i>?')
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
            item.merge(self.MW.new_category)
            dialog = EditCategory(self.MW, item, new=new)

        elif action == 'new_channel': 
            new = True
            item = FeedexFeed(self.DB)
            item.merge(self.MW.new_feed)
            dialog = EditFeed(self.MW, item, new=new)

        elif action == 'edit':
            item = item.convert(FeedexFeed, self.DB, id=item['id'])
            new = False
            if not item.exists: return -1
            if item['is_category'] == 1: dialog = EditCategory(self.MW, item, new=new)
            else: dialog = EditFeed(self.MW, item, new=new)

        dialog.run()
        if action == 'new_category': self.MW.new_category = item.vals.copy()
        elif action == 'new_channel': self.MW.new_feed = item.vals.copy()

        if dialog.response == 1:
            if new: err = item.add(validate=False)
            else:
                if item['is_category'] == 1: err = item.do_update(validate=True)
                else: err = item.do_update(validate=False)

            if err == 0:
                if action == 'new_category': self.MW.new_category.clear()
                elif action == 'new_channel': self.MW.new_feed.clear()

                self.MW.feed_tab.reload()

        dialog.destroy()






    def on_del_feed(self, *args):
        """ Deletes feed or category """
        if not self._fetch_lock(): return 0
        item = args[-1]

        if coalesce(item['is_category'],0) == 0 and coalesce(item['deleted'],0) == 0:
            dialog = YesNoDialog(self.MW, _('Delete Channel'), f'{_("Are you sure you want to delete")} <i><b>{esc_mu(item.name())}</b></i>{_("?")}')

        elif coalesce(item['is_category'],0) == 0 and coalesce(item['deleted'],0) == 1:
            dialog = YesNoDialog(self.MW, _('Delete Channel permanently'), f'{_("Are you sure you want to permanently delete")} <i><b>{esc_mu(item.name())}</b></i>{_("?")}')

        elif coalesce(item['is_category'],0) == 1 and coalesce(item['deleted'],0) == 0:
            dialog = YesNoDialog(self.MW, _('Delete Category'), f'{_("Are you sure you want to delete")} <i><b>{esc_mu(item.name())}</b></i> {_("category?")}')

        elif coalesce(item['is_category'],0) == 1 and coalesce(item['deleted'],0) == 1:
            dialog = YesNoDialog(self.MW, _('Delete Category'), f'{_("Are you sure you want to permanently delete")} <i><b>{esc_mu(item.name())}</b></i> {_("category?")}')

        dialog.run()
        if dialog.response == 1:
            item = item.convert(FeedexFeed, self.DB, id=item['id'])
            err = item.delete()
            if err == 0: self.MW.feed_tab.reload()
        
        dialog.destroy()





    def on_restore_feed(self, *args):
        """ Restores selected feed/category """
        if not self._fetch_lock(): return 0
        item = args[-1]

        if coalesce(item['is_category'],0) == 1: dialog = YesNoDialog(self.MW, _('Restore Category'), f'{_("Restore ")}<i><b>{esc_mu(item.name())}</b></i>{_(" Category?")}')
        else: dialog = YesNoDialog(self.MW, _('Restore Channel'), f'{_("Restore ")}<i><b>{esc_mu(item.name())}</b></i>{_(" Channel?")}')
        dialog.run()

        if dialog.response == 1:
            item = item.convert(FeedexFeed, self.DB, id=item['id'])
            err = item.update({'deleted': 0}) 
            if err == 0: self.MW.feed_tab.reload()
        
        dialog.destroy()





    def on_empty_trash(self, *args):
        """ Empty all Trash items """
        dialog = YesNoDialog(self.MW, _('Empty Trash'), f'<b>{_("Do you really want to permanently remove Trash content?")}</b>', emblem='edit-delete-symbolic')
        dialog.run()
        if dialog.response == 1:
            err = self.DB.empty_trash()
            if err == 0: self.MW.feed_tab.reload()
        dialog.destroy()



    def on_clear_history(self, *args):
        """ Clears search history """
        dialog = YesNoDialog(self.MW, _('Clear Search History'), _('Are you sure you want to clear <b>Search History</b>?'), emblem='edit-clear-all-symbolic' )           
        dialog.run()
        if dialog.response == 1:
            err = self.DB.clear_history()
            if err == 0: self.MW.reload_history_all()
        dialog.destroy()


    def reload_history_all(self, *args):
        """ Reloads history in all tabs containing query combo """
        for i in range(self.MW.upper_notebook.get_n_pages()):
            tab = self.MW.upper_notebook.get_nth_page(i)
            if tab is None: continue
            if hasattr(tab, 'query_combo'): tab.reload_history()

    def reload_flag_combos(self, *args):
        """ Reloads flag combos in all tabs """
        for i in range(self.MW.upper_notebook.get_n_pages()):
            tab = self.MW.upper_notebook.get_nth_page(i)
            if tab is None: continue
            if hasattr(tab, 'flag_combo'):
                curr_flag = f_get_combo(tab.flag_combo)
                tab.flag_combo.set_model(f_flag_store(list_store=True))
                f_set_combo(tab.flag_combo, curr_flag)


    def reload_cat_combos(self, *args):
        """ Reloads all cat/feed combos after changes took place """
        for i in range(self.MW.upper_notebook.get_n_pages()):
            tab = self.MW.upper_notebook.get_nth_page(i)
            if tab is None: continue
            if hasattr(tab, 'cat_combo'):
                curr_cat = f_get_combo(tab.cat_combo)
                tab.cat_combo.set_model(f_feed_store(self.MW, with_feeds=True))
                f_set_combo(tab.cat_combo, curr_cat)






    def on_mark_healthy(self, *args):
        """ Marks a feed as healthy -> zeroes the error count """
        if not self._fetch_lock(): return 0
        item = args[-1]
        item = item.convert(FeedexFeed, self.DB, id=item['id'])
        err = item.update({'error': 0})
        if err == 0: self.MW.feed_tab.reload()








    

    def on_del_rule(self, *args):
        """ Deletes rule - wrapper """
        if not self._fetch_lock(): return 0
        item = args[-1]

        dialog = YesNoDialog(self.MW, _('Delete Rule'), f'{_("Are you sure you want to permanently delete ")}<b><i>{esc_mu(item.name())}</i></b>{_(" Rule?")}')           
        dialog.run()
        if dialog.response == 1:
            item = item.convert(FeedexRule, self.DB, id=item['id'])
            err = item.delete() 
            if err == 0:
                if self.MW.rules_tab != -1: self.MW._get_upn_page_obj(self.MW.rules_tab).apply(FX_ACTION_DELETE, item.vals.copy())
        dialog.destroy()

        


    def on_edit_rule(self, *args):
        """ Edit / Add Rule with dialog """
        if not self._fetch_lock(): return 0
        item = args[-1]

        if item is None:
            new = True
            item = FeedexRule(self.DB)
            item.strict_merge(self.MW.new_rule)
        else: 
            new = False
            item = item.convert(FeedexRule, self.DB, id=item['id'])
            if not item.exists: return -1

        dialog = EditRule(self.MW, item, new=new)
        dialog.run()
        if new: self.MW.new_rule = item.vals.copy()
        if dialog.response == 1:
            if new: err = item.add(validate=False)
            else: err = item.do_update(validate=False)

            if err == 0:
                if self.MW.rules_tab != -1: 
                    if new: 
                        self.MW.new_rule.clear()
                        self.MW._get_upn_page_obj(self.MW.rules_tab).apply(FX_ACTION_ADD, item.vals.copy())
                    else: self.MW._get_upn_page_obj(self.MW.rules_tab).apply(FX_ACTION_EDIT, item.vals.copy())
        dialog.destroy()





    def on_del_flag(self, *args):
        """ Deletes flag - wrapper """
        if not self._fetch_lock(): return 0
        item = args[-1]

        dialog = YesNoDialog(self.MW, _('Delete Flag'), f'{_("Are you sure you want to permanently delete ")}<b><i>{esc_mu(item.name())}</i></b>{_(" Flag?")}')           
        dialog.run()
        if dialog.response == 1:
            item = item.convert(FeedexFlag, self.DB, id=item['id'])
            err = item.delete()
            if err == 0:
                if self.MW.flags_tab != -1: self.MW._get_upn_page_obj(self.MW.flags_tab).apply(FX_ACTION_DELETE, item.vals.copy())
                self.reload_flag_combos()
        dialog.destroy()

        

    def on_edit_flag(self, *args):
        """ Edit / Add Flag with dialog """
        if not self._fetch_lock(): return 0
        item = args[-1]

        if item is None:
            new = True
            item = FeedexFlag(self.DB)
            item.strict_merge(self.MW.new_flag)
        else: 
            new = False
            item = item.convert(FeedexFlag, self.DB, id=item['id'])
            if not item.exists: return -1

        dialog = EditFlag(self.MW, item, new=new)
        dialog.run()
        if new: self.MW.new_flag = item.vals.copy()
        if dialog.response == 1:
            if new: err = item.add(validate=False) 
            else: err = item.do_update(validate=False)

            if err == 0:
                if self.MW.flags_tab != -1:
                    if new:
                        self.MW._get_upn_page_obj(self.MW.flags_tab).apply(FX_ACTION_ADD, item.vals.copy()) 
                        self.new_flag.clear()
                    else: self.MW._get_upn_page_obj(self.MW.flags_tab).apply(FX_ACTION_EDIT, item.vals.copy())
                    self.reload_flag_combos()
        dialog.destroy()   








    def on_del_plugin(self, *args):
        """ Delete plugin """
        item = args[-1]
        item = item.convert(FeedexPlugin, main_win=self.MW, id=item['id'])
        if not item.exists: return -1

        dialog = YesNoDialog(self.MW, _('Delete Plugin'), f'{_("Are you sure you want to remove ")}<b><i>{esc_mu(item.name())}</i></b>{_(" Plugin?")}', buttons=2)           
        dialog.run()
        if dialog.response == 1:
            err = item.delete()
            if err == 0:
                if self.MW.plugins_tab != -1: self.MW._get_upn_page_obj(self.MW.plugins_tab).apply(FX_ACTION_DELETE, item.vals.copy())
        dialog.destroy()



    def on_edit_plugin(self, *args):
        """ Edit/Add Plugin with Dialog"""
        item = args[-1]

        if item is None:
            new = True
            item = FeedexPlugin(main_win=self.MW)
            item.strict_merge(self.MW.new_plugin)
        else: 
            new = False
            item = item.convert(FeedexPlugin, main_win=self.MW, id=item['id'])
            if not item.exists: return -1

        dialog = EditPlugin(self.MW, item, new=new)
        dialog.run()
        if new: self.MW.new_plugin = item.vals.copy()
        if dialog.response == 1:
            if new: err = item.add(validate=False) 
            else: err = item.edit(validate=False)

            if err == 0:
                if self.MW.plugins_tab != -1:
                    if new:
                        self.MW._get_upn_page_obj(self.MW.plugins_tab).apply(FX_ACTION_ADD, item.vals.copy()) 
                        self.MW.new_plugin.clear()
                    else: self.MW._get_upn_page_obj(self.MW.plugins_tab).apply(FX_ACTION_EDIT, item.vals.copy())
        dialog.destroy()   

        

    def on_run_plugin(self, *args):
        """ Execute plugin in context """
        plugin = FeedexPlugin(id=args[-2], main_win=self.MW)
        if not plugin.exists: return -1
        item = args[-1]
        plugin.run(item)





    def on_go_home(self, *args):
        """ Executes browser on channel home page """
        item = args[-1]
        if isinstance(item, FeedexCatalog): item.open()
        else:
            item = item.convert(FeedexFeed, self.DB, id=item['id'])
            item.open()




    def on_prefs(self, *args):
        """ Run preferences dialog """
        restart = False
        dialog = PreferencesDialog(self.MW)
        dialog.run()
        dialog.destroy()
        if dialog.response == 2:
            dialog2 = BasicDialog(self.MW, _('Restart Required'), _('Restart is required for all changes to be applied.'), button_text=_('OK'), emblem='dialog-warning-symbolic' )
            dialog2.run()
            dialog2.destroy()





    def on_view_log(self, *args):
        """ Shows dialog for reviewing log """
        log_str = ''
        try:        
            with open(self.config.get('log',''), 'r') as f: log_str = f.read()
        except OSError as e:
            return msg(FX_ERROR_IO, f'{_("Error reading log file (%a)")} {e}', self.config.get('log',''))

        dialog = BasicDialog(self.MW, _('Main Log'), log_str, width=600, height=500, justify=FX_ATTR_JUS_LEFT, selectable=True, scrolled=True, markup=False)
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

        dialog = BasicDialog(self.MW, _('Tech details'), esc_mu(item.__str__()), width=600, height=500, justify=FX_ATTR_JUS_LEFT, selectable=True, scrolled=True)
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

{_('Rule count')}:              <b>{stats['rule_count']}</b>
{_('Learned Keyword count')}:   <b>{stats['learned_kw_count']}</b>

{_('Feed count')}:              <b>{stats['feed_count']}</b>
{_('Category count')}:          <b>{stats['cat_count']}</b>

{_('Last news update')}:        <b>{stats['last_update']}</b>
{_('First news update')}:       <b>{stats['first_update']}</b>

"""

        if stats['fetch_lock']: 
            stat_str = f"""{stat_str}
{_('DATABASE LOCKED FOR FETCHING')}"""

        if stats['due_maintenance']: 
            stat_str = f"""{stat_str}
{_('DATABASE MAINTENANCE ADVISED')}
{_('Use')} <b>feedex --db-maintenance</b> {_('command')}

"""

        dialog = BasicDialog(self.MW, _("Database Statistics"), stats_str, width=600, height=500, pixbuf=self.MW.icons.get('db'), justify=FX_ATTR_JUS_LEFT, selectable=True)
        dialog.run()
        dialog.destroy()



    def on_show_session_log(self, *args):
        """ Show dialog with current session log """
        dialog = BasicDialog(self.MW, _('Session log'), self.MW.log_string, width=600, height=500, justify=FX_ATTR_JUS_LEFT, selectable=True, scrolled=True)
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
        dialog = BasicDialog(self.MW, _('About...'), about_str, image='feedex.png', selectable=True)
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
        if not self._fetch_lock(): return 0
        if fdx.busy: return -1
        
        dialog = YesNoDialog(self.MW, _('DB Maintenance'), _('Are you sure you want to DB maintenance? This may take a long time...'), emblem='system-run-symbolic' )  
        dialog.run()
        dialog.destroy()
        if dialog.response == 1:
            fdx.bus_append(FX_ACTION_BLOCK_DB)
            fdx.busy = True
            t = threading.Thread(target=self.on_maintenance_thr)
            t.start()



    def on_clear_cache_thr(self, *args, **kargs):
        DB = FeedexDatabase(connect=True)
        DB.clear_cache(-1)
        DB.close()
        fdx.busy = False
        fdx.bus_append(FX_ACTION_UNBLOCK_DB)


    def on_clear_cache(self, *args, **kargs):
        """ Clear image cache """
        if fdx.busy: return -1
        dialog = YesNoDialog(self.MW, _('Clear Cache'), _('Do you want to delete all downloaded and cached images/thumbnails?'),  emblem='edit-clear-all-symbolic')
        dialog.run()
        if dialog.response == 1:
            dialog.destroy()
            fdx.bus_append(FX_ACTION_BLOCK_DB)
            fdx.busy = True
            t = threading.Thread(target=self.on_clear_cache_thr)
            t.start()

    
    def del_learned_keywords(self, *args):
        """ Wrapper for deleting learned keywords from DB """
        if fdx.busy: return -1
        if not self._fetch_lock(): return 0
        dialog = YesNoDialog(self.MW, _('Delete Learned Keywords?'), _('Do you want delete all learned Keywords used for recommendations?'), 
                             subtitle=_('<i>This action is permanent. Relearning can be time consuming</i>'),  emblem='dialog-warning-symbolic')
        dialog.run()
        dialog.destroy()
        if dialog.response == 1:
            dialog2 = YesNoDialog(self.MW, _('Delete Learned Keywords?'), _('Are you sure?'), emblem='dialog-warning-symbolic')
            dialog2.run()
            dialog2.destroy()
            if dialog2.response == 1:
                err = self.DB.delete_learned_terms()
                if err == 0: 
                    if self.MW.learned_tab != -1: self.MW._get_upn_page_obj(self.MW.learned_tab).query(None, None)
        



    def relearn_keywords_thr(self, *args):
        DB = FeedexDatabase(connect=True)
        DB.recalculate(learn=True, rank=False, index=False)
        DB.load_terms()
        DB.close()
        if self.MW.learned_tab != -1: self.MW._get_upn_page_obj(self.MW.learned_tab).query(None, None)
        fdx.busy = False
        fdx.bus_append(FX_ACTION_UNBLOCK_DB)


    def relearn_keywords(self, *args):
        """ Wrapper for relearning keywords """
        if fdx.busy: return -1
        if not self._fetch_lock(): return 0
        dialog = YesNoDialog(self.MW, _('Relearn Keywords?'), _('Do you want to relearn Keywords for recommendations?'), 
                             subtitle=_('<i>This may take a long time</i>'),  emblem='applications-engineering-symbolic')
        dialog.run()
        dialog.destroy()
        if dialog.response == 1:
            fdx.bus_append(FX_ACTION_BLOCK_DB)
            fdx.busy = True
            t = threading.Thread(target=self.relearn_keywords_thr)
            t.start()


    def on_unlock_fetching(self, *args):
        """ Wrapper for manually lifting fetch lock """
        dialog = YesNoDialog(self.MW, _('Lift Fetching Lock?'), _('Are you sure? If Feedex is currently fetchin/importing it may cause data inconsistency'),  emblem='dialog-warning-symbolic')
        dialog.run()
        dialog.destroy()
        if dialog.response == 1:
            err = self.DB.unlock_fetching()
            if err == 0: return msg(_('Database unlocked for fetching'))
            else: return err
        return 0



    ####################################################
    # Porting
    #           Below are wrappers for porting data



    def export_feeds(self, *args):
        filename = f_chooser(self.MW, self.MW, action='save', header=_('Export Feed data to...') )
        if filename is False: return 0
        feedex_cli = FeedexCLI()
        feedex_cli.output = 'json_dict'
        feedex_cli.ofile = filename
        self.DB.Q.list_feeds(all=True)
        feedex_cli.out_table(self.DB.Q)


    def export_rules(self, *args):
        filename = f_chooser(self.MW, self.MW, action='save', header=_('Export Rules to...') )
        if filename is False: return 0
        feedex_cli = FeedexCLI()
        feedex_cli.output = 'json_dict'
        feedex_cli.ofile = filename
        self.DB.Q.list_rules()
        feedex_cli.out_table(self.DB.Q)



    def export_flags(self, *args):
        filename = f_chooser(self.MW, self.MW, action='save', header=_('Export Flags to...') )
        if filename is False: return 0
        feedex_cli = FeedexCLI()
        feedex_cli.output = 'json_dict'
        feedex_cli.ofile = filename
        self.DB.Q.list_flags(all=True)
        feedex_cli.out_table(self.DB.Q)

    def export_plugins(self, *args):
        filename = f_chooser(self.MW, self.MW, action='save', header=_('Export Plugins to...') )
        if filename is False: return 0
        save_json(filename, self.MW.gui_plugins)




    def import_feeds(self, *args):
        if not self._fetch_lock(): return 0
        if fdx.busy: return -1

        filename = f_chooser(self.MW, self.MW, action='open_file', header=_('Import Feeds from...') )
        if filename is False: return 0

        err = self.DB.import_feeds(filename)
        if err == 0: 
            self.MW.feed_tab.reload()

            dialog = YesNoDialog(self.MW, _('Update Feed Data'), _('New feed data has been imported. Download Metadata now?') )
            dialog.run()
            if dialog.response == 1: self.on_update_feed_all()
            dialog.destroy()


    def import_rules(self, *args):
        if not self._fetch_lock(): return 0
        if fdx.busy: return -1

        filename = f_chooser(self.MW, self.MW, action='open_file', header=_('Import Rules from...') )
        if filename is False: return 0

        err = self.DB.import_rules(filename)
        if err == 0: 
            if self.MW.rules_tab != -1: self.MW._get_upn_page_obj(self.MW.rules_tab).query('',{})


    def import_flags(self, *args):
        if not self._fetch_lock(): return 0
        if fdx.busy: return -1

        filename = f_chooser(self.MW, self.MW, action='open_file', header=_('Import Flags from...') )
        if filename is False: return 0

        err = self.DB.import_flags(filename)
        if err == 0: 
            if self.MW.flags_tab != -1: self.MW._get_upn_page_obj(self.MW.flags_tab).query('',{})



    def import_entries_thr(self, efile, **kargs):
        DB = FeedexDatabase(connect=True)
        err = DB.import_entries(efile=efile)
        DB.close()
        fdx.busy = False
        fdx.bus_append(FX_ACTION_UNBLOCK_DB)


    def import_entries(self, *args):
        filename = f_chooser(self.MW, self.MW, action='open_file', header=_('Import Entries from...') )
        if filename is False: return 0
        if not self._fetch_lock(): return 0
        fdx.busy = True
        fdx.bus_append(FX_ACTION_BLOCK_DB)
        t = threading.Thread(target=self.import_entries_thr, args=(filename,))
        t.start()



    def import_plugins(self, *args):
        filename = f_chooser(self.MW, self.MW, action='open_file', header=_('Import Plugins from...') )
        if filename is False: return 0

        new_plugins = self.validate_gui_plugins( load_json(filename, [], create_file=False) )
        if len(new_plugins) > 0:
            self.MW.gui_plugins = list(self.MW.gui_plugins)
            max_id = len(self.MW.gui_plugins) + 1
            for p in new_plugins:
                p[FX_PLUGIN_TABLE.index('id')] = max_id
                max_id += 1
                self.MW.gui_plugins.append(p)
            
            err = save_json(self.MW.gui_plugins_path, self.MW.gui_plugins)
            if err == 0: 
                if self.MW.plugins_tab != -1: self.MW._get_upn_page_obj(self.MW.plugins_tab).query('',{})
                msg(_('Plugins imported successfully...'))




    def export_results(self, *args, **kargs):
        """ Export results from current tab to JSON for later import """
        if self.MW.curr_upper.type in (FX_TAB_RULES, FX_TAB_FLAGS): return 0
        format = args[-1]

        if not isinstance(self.MW.curr_upper.table.result, (ResultEntry, ResultContext, ResultTerm, ResultTimeSeries,)): return -1
        if isinstance(self.MW.curr_upper.table.result, ResultEntry): result = ResultEntry()
        elif isinstance(self.MW.curr_upper.table.result, ResultContext): result = ResultContext()
        elif isinstance(self.MW.curr_upper.table.result, ResultTerm): result = ResultTerm()
        elif isinstance(self.MW.curr_upper.table.result, ResultTimeSeries): result = ResultTimeSeries()
        else: return 0

        query = FeedexQueryInterface()        
        query.result =  result
        query.results = self.MW.curr_upper.table.results
        query.result_no = len(query.results)
        query.result_no2 = 0
        
        if query.result_no == 0:
            msg(_('Nothing to export.') )
            return 0
        
        if kargs.get('filename') is None:
            filename = f_chooser(self.MW, self.MW, action='save', header=_('Export to...') )
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
        if not self._fetch_lock(): return 0
        ids = args[-1]
        item = FeedexCatalog(db=self.DB)
        item.prep_import(ids)
        if item.queue_len == 0: return 0

        dialog = YesNoDialog(self.MW, _('Subscribe...'), f"""{_('Subscribe to')} <b>{item.queue_len}</b> {_('Channels?')}""", emblem='rss-symbolic')
        dialog.run()
        if dialog.response == 1:
            if not self._fetch_lock(): return 0
            fdx.busy = True
            fdx.bus_append(FX_ACTION_BLOCK_DB)
            t = threading.Thread(target=self.import_catalog_thr, args=(item,))
            t.start()
        dialog.destroy()





########################################################################################33
#
#       Utilities
#




    def validate_gui_cache(self, gui_attrs):
        """ Validate GUI attributes in case the config file is not right ( to prevent crashing )"""
    
    
        new_gui_attrs = {}
    
        new_gui_attrs['win_width'] = scast(gui_attrs.get('win_width'), int, 1500)
        new_gui_attrs['win_height'] = scast(gui_attrs.get('win_height'), int, 800)
        new_gui_attrs['win_maximized'] = scast(gui_attrs.get('win_maximized'), bool, True)

        new_gui_attrs['div_horiz'] = scast(gui_attrs.get('div_horiz'), int, 400)
        new_gui_attrs['div_vert2'] = scast(gui_attrs.get('div_vert2'), int, 700)
        new_gui_attrs['div_vert'] = scast(gui_attrs.get('div_vert'), int, 250)

        new_gui_attrs['div_entry_edit'] = scast(gui_attrs.get('div_entry_edit'), int, 500)

        new_gui_attrs['new_items'] = scast(gui_attrs.get('new_items'), int, 0)
        new_gui_attrs['new_n'] = scast(gui_attrs.get('new_n'), int, 1)

        new_gui_attrs['last_dir'] = scast(gui_attrs.get('last_dir'), str, '')


        new_gui_attrs['feeds_expanded'] = scast(gui_attrs.get('feeds_expanded',{}).copy(), dict, {})
        for v in new_gui_attrs['feeds_expanded'].values():
            if type(v) is not bool: 
                new_gui_attrs['feeds_expanded'] = {}
                msg(FX_ERROR_VAL, _('Expanded feeds invalid. Defaulting...') )
                break

        new_gui_attrs['layouts'] = scast(gui_attrs.get('layouts'), dict, {})
        if new_gui_attrs['layouts'] == {}:
            msg(FX_ERROR_VAL, _('No valid layouts found. Defaulting...'))
            new_gui_attrs['layouts'] = FX_DEF_LAYOUTS.copy()

        if new_gui_attrs['layouts'].keys() != FX_DEF_LAYOUTS.keys(): 
            msg(FX_ERROR_VAL, _('Invalid layout list. Defaulting...'))
            new_gui_attrs['layouts'] = FX_DEF_LAYOUTS.copy()
    
        for k,v in new_gui_attrs['layouts'].items():
            if type(v) not in (tuple, list) or len(v) == 0:
                msg(FX_ERROR_VAL, _('Invald %a layout. Defaulting...'), k)
                new_gui_attrs['layouts'][k] = FX_DEF_LAYOUTS[k]
                continue

            for i,c in enumerate(v):
                if type(c) not in (tuple, list): 
                    msg(FX_ERROR_VAL, _('Invald %a layout. Defaulting...'), k)
                    new_gui_attrs['layouts'][k] = FX_DEF_LAYOUTS[k]
                    break
                if type(slist(c,0,None)) is not str or type(slist(c,1,None)) is not int or slist(c,1,0) <= 0:
                    msg(FX_ERROR_VAL, _('Invald %a layout. Defaulting...'), k)
                    new_gui_attrs['layouts'][k] = FX_DEF_LAYOUTS[k]
                    break


    
        new_gui_attrs['default_search_filters'] = scast(gui_attrs.get('default_search_filters',FEEDEX_GUI_DEFAULT_SEARCH_FIELDS).copy(), dict, {})    
        new_gui_attrs['tabs'] = gui_attrs.get('tabs',[]).copy()

        return new_gui_attrs








    def validate_gui_plugins(self, gui_plugins):
        """ Initial validation of plugin list """
        new_gui_plugins = []
        plugin = FeedexPlugin()
        plugin_len = len(plugin.fields)
        for p in gui_plugins:
            if type(p) not in (list, tuple): 
                msg(FX_ERROR_VAL, _('Plugin item %a not a valid list! Ommiting'), p)
                continue
            if len(p) != plugin_len:
                msg(FX_ERROR_VAL, _('Invalid plugin item %a! Ommiting'), p)
                continue
            plugin.populate(p)
            if plugin.validate() != 0: continue
            new_gui_plugins.append(p)
    
        return new_gui_plugins







    def get_icons(self, **kargs):
        """ Sets up a dictionary with feed icon pixbufs for use in lists """
        self.MW.icons = {}
        self.MW.icons['large'] = {}
        for f,ic in fdx.icons_cache.items():
            try: 
                self.MW.icons[f] = GdkPixbuf.Pixbuf.new_from_file_at_size(ic, 16, 16)
            except Exception as e:
                try: os.remove(ic)
                except OSError as ee: msg(FX_ERROR_IO, f"""_('Error removing %a:'){ee}""", ic)
                msg(FX_ERROR_IO, _('Image error: %a'), e)
                continue

            try: self.MW.icons['large'][f] = GdkPixbuf.Pixbuf.new_from_file_at_size(ic, 32, 32)
            except Exception as e: self.MW.icons['large'][f] = self.MW.icons.get(f)



        self.MW.icons['main']  = GdkPixbuf.Pixbuf.new_from_file_at_size(        os.path.join(FEEDEX_SYS_ICON_PATH, 'feedex.png'), 64, 64)
        self.MW.icons['large']['main_emblem'] = Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_size(  os.path.join(FEEDEX_SYS_ICON_PATH,'feedex.png'), 64, 64))
        self.MW.icons['db'] = GdkPixbuf.Pixbuf.new_from_file_at_size(           os.path.join(FEEDEX_SYS_ICON_PATH, 'db.svg'), 64, 64)

        self.MW.icons['default']  = GdkPixbuf.Pixbuf.new_from_file_at_size(     os.path.join(FEEDEX_SYS_ICON_PATH, 'news-feed.svg'), 16, 16)
        self.MW.icons['error'] = GdkPixbuf.Pixbuf.new_from_file_at_size(        os.path.join(FEEDEX_SYS_ICON_PATH, 'error.svg'), 16, 16)
        self.MW.icons['doc'] = GdkPixbuf.Pixbuf.new_from_file_at_size(          os.path.join(FEEDEX_SYS_ICON_PATH, 'document.svg'), 16, 16)
        self.MW.icons['trash'] = GdkPixbuf.Pixbuf.new_from_file_at_size(        os.path.join(FEEDEX_SYS_ICON_PATH, 'trash.svg'), 16, 16)
        self.MW.icons['new'] = GdkPixbuf.Pixbuf.new_from_file_at_size(          os.path.join(FEEDEX_SYS_ICON_PATH, 'new.svg'), 16, 16)
        self.MW.icons['flag'] = GdkPixbuf.Pixbuf.new_from_file_at_size(         os.path.join(FEEDEX_SYS_ICON_PATH, 'flag.svg'), 16, 16)

        self.MW.icons['large']['default']  = GdkPixbuf.Pixbuf.new_from_file_at_size(     os.path.join(FEEDEX_SYS_ICON_PATH, 'news-feed.svg'), 32, 32)
        self.MW.icons['large']['error'] = GdkPixbuf.Pixbuf.new_from_file_at_size(        os.path.join(FEEDEX_SYS_ICON_PATH, 'error.svg'), 32, 32)
        self.MW.icons['large']['doc'] = GdkPixbuf.Pixbuf.new_from_file_at_size(          os.path.join(FEEDEX_SYS_ICON_PATH, 'document.svg'), 32, 32)
        self.MW.icons['large']['trash'] = GdkPixbuf.Pixbuf.new_from_file_at_size(        os.path.join(FEEDEX_SYS_ICON_PATH, 'trash.svg'), 32, 32)
        self.MW.icons['large']['new'] = GdkPixbuf.Pixbuf.new_from_file_at_size(          os.path.join(FEEDEX_SYS_ICON_PATH, 'new.svg'), 32, 32)
        self.MW.icons['large']['flag'] = GdkPixbuf.Pixbuf.new_from_file_at_size(         os.path.join(FEEDEX_SYS_ICON_PATH, 'flag.svg'), 32, 32)


        for ico in FEEDEX_GUI_ICONS:
            self.MW.icons[ico] = GdkPixbuf.Pixbuf.new_from_file_at_size(           os.path.join(FEEDEX_SYS_ICON_PATH, f'{ico}.svg'), 16, 16)
            self.MW.icons['large'][ico] = GdkPixbuf.Pixbuf.new_from_file_at_size(           os.path.join(FEEDEX_SYS_ICON_PATH, f'{ico}.svg'), 32, 32)
        

        return 0
