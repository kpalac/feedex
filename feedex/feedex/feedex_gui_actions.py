# -*- coding: utf-8 -*-
""" GUI session class for FEEDEX """



from feedex_gui_utils import *










class FeedexGUIActions:
    """ This is the main container for Feedex GUI actions """
    def __init__(self, parent, **kargs) -> None:
        self.MW = parent
        self.DB = self.MW.DB
        self.config = self.MW.config



    def start_thread(self, **kargs):
        aargs = []
        aargs.append(kargs.get('target'))
        for a in kargs.get('args', ()): aargs.append(a)

        fdx.task_counter += 1

        t = threading.Thread(target=self.run_thread, args=tuple(aargs))
        t.start()


    def run_thread(self, *args):
        """ Wrapper for running threads """
        aargs = []
        target = None
        for a in args:
            if target is None: target = a
            else: aargs.append(a)

        if target is None: return 0
        ret_code = target(*aargs)
        fdx.task_counter -= 1
        return ret_code


    def _lock_info(self, *args):
        """ Check and informa about locks """
        m, st = None, None
        if FX_LOCK_FETCH in args and fdx.db_fetch_lock: m, st = _('Database locked for fetching'), _('Metadata edits are not allowed now')
        if FX_LOCK_ENTRY in args and fdx.db_entry_lock: m, st = _('Entry editting is locked'), _('Please wait for previous action to finish')
        if FX_LOCK_FEED in args and fdx.db_feed_lock: m, st = _('Channel/Category editting is locked'), _('Please wait for previous action to finish')
        if FX_LOCK_RULE in args and fdx.db_rule_lock: m, st = _('Rule editting is locked'), _('Please wait for previous action to finish')
        if FX_LOCK_FLAG in args and fdx.db_flag_lock: m, st = _('Flag editting is locked'), _('Please wait for previous action to finish')

        if m is None: return True

        self.MW._run_dialog(BasicDialog(self.MW, st, f"<b>{st}</b>", 
                                subtitle=_("<i>If this message is due to some unforseen error, restart application to lift the locks</i>"), 
                                emblem='system-lock-screen-symbolic')
                            )
        return False









    def on_load_news_feed(self, *args):
        if not self._lock_info(FX_LOCK_FETCH): return 0
        self.start_thread(target=self.load_news_thr, args=(args[-1],))

    def on_load_news_all(self, *args):
        if not self._lock_info(FX_LOCK_FETCH): return 0
        self.start_thread(target=self.load_news_thr, args=(None,))

    def on_load_news_background(self, *args):
        if not self._lock_info(FX_LOCK_FETCH): return 0
        self.start_thread(target=self.load_news_thr, args=(0,))




    def load_news_thr(self, *args):
        """ Fetching news/articles from feeds """
        msg(_('Checking for news ...'))
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
                fdx.bus_append(FX_ACTION_UNBLOCK_FETCH)
                return -1
        else:
            return -1

        DB = FeedexDatabase(connect=True)
        DB.fetch(id=feed_id, force=ignore_modified, ignore_interval=ignore_interval)


        if DB.new_items > 0:

            self.MW.new_items = scast(self.MW.new_items, int, 0) + DB.new_items
            self.MW.new_n = scast(self.MW.new_n, int, 0) + 1
            self.MW.feed_tab.redecorate_new()

            if self.config.get('gui_desktop_notify', True):
                DB.connect_QP()
                if self.config.get('gui_notify_group','feed') == 'number':
                    fdx.DN.notify(f'{DB.new_items} {_("new articles fetched...")}', None, -3)
                else:

                    filters = {'last':True,
                    'group':self.config.get('gui_notify_group','feed'), 
                    'depth':self.config.get('gui_notify_depth',5)
                    }
                    DB.Q.query('', filters , rev=False, print=False, allow_group=True)
                    fdx.DN.load(DB.Q.results)
                    fdx.DN.show()

        DB.close()
        fdx.bus_append(FX_ACTION_UNBLOCK_FETCH)
        fdx.bus_append(FX_ACTION_RELOAD_FEEDS)





    def on_update_feed(self, *args):
        """ Wrapper for feed updating """
        item = args[-1]
        if item['is_category'] == 1: return 0
        if not self._lock_info(FX_LOCK_FETCH, FX_LOCK_FEED): return 0
        msg(_('Updating channel...'))
        self.start_thread(target=self.update_feed_thr, args=(item['id'],))



    def on_update_feed_all(self, *args):
        if not self._lock_info(FX_LOCK_FETCH, FX_LOCK_FEED): return 0
        msg(_('Updating all channels...'))
        self.start_thread(target=self.update_feed_thr, args=(None,))


    def update_feed_thr(self, *args):
        """ Updates metadata for all/selected feed """
        fdx.bus_append(FX_ACTION_BLOCK_FETCH)

        feed_id = args[-1]
        DB = FeedexDatabase(connect=True)
        DB.fetch(id=feed_id, update_only=True, force=True)

        self.MW.lock.acquire()
        self.MW.get_icons()
        self.MW.lock.release()

        DB.close()
        fdx.bus_append(FX_ACTION_UNBLOCK_FETCH)
        fdx.bus_append(FX_ACTION_RELOAD_FEEDS)




    def add_from_url_thr(self, item):
        """ Add from URL - threading """
        msg(_('Adding Channel...') )
        fdx.bus_append(FX_ACTION_BLOCK_FETCH)

        DB = FeedexDatabase(connect=True)
        item.set_interface(DB)
        err = item.add_from_url(item.vals.copy())
        
        if DB.new_items > 0:
            self.MW.new_items = scast(self.MW.new_items, int, 0) + DB.new_items
            self.MW.new_n = scast(self.MW.new_n, int, 1) + 1
            self.MW.feed_tab.redecorate_new()
        
        self.MW.lock.acquire()
        if err == 0: self.MW.new_feed_url.clear()
        self.MW.lock.release()

        DB.close()
        fdx.bus_append(FX_ACTION_UNBLOCK_FETCH)
        fdx.bus_append(FX_ACTION_RELOAD_FEEDS)



    def on_add_from_url(self, *args):
        """ Adds a new feed from URL - dialog """
        if not self._lock_info(FX_LOCK_FETCH, FX_LOCK_FEED): return 0

        item = FeedexFeed(self.DB)
        item.merge(self.MW.new_feed_url)
        item.deraw_vals()

        dialog = self.MW._run_dialog(NewFromURL(self.MW, item))
        self.MW.new_feed_url = item.vals.copy()
        if dialog.response == 1:
            if not self._lock_info(FX_LOCK_FETCH, FX_LOCK_FEED): return 0
            self.start_thread(target=self.add_from_url_thr, args=(item,))






#######################################################################
#
#       Entries

    def on_edit_entry(self, *args):
        """ Add / Edit Entry """
        item = args[-1]
        if item is None:
            new = True
            item = FeedexEntry(self.DB)
            item.merge(self.MW.new_entry)
            item.deraw_vals()
        else: 
            item = item.convert(FeedexEntry, self.DB, id=item['id'])
            if not item.exists: return -1
            new = False

        if not self._lock_info(FX_LOCK_ENTRY): return 0
        dialog = self.MW._run_dialog(EditEntry(self.MW, item, new=new))
        if new: self.MW.new_entry = item.vals.copy()
        if dialog.response == 1:
            if new: msg(_('Adding entry...') )
            else: msg(_('Writing changes to Entry...') )
            self.start_thread(target=self.edit_entry_thr, args=(new, item, dialog.new_image) )



    def edit_entry_thr(self, new:bool, item:FeedexEntry, new_image):
        """ Add/Edit Entry low-level interface for threading """
        DB = FeedexDatabase(connect=True)
        item.set_interface(DB)

        if new:
            err = item.add(validate=False, no_commit=False)
            if err == 0:
                fdx.bus_append( (FX_ACTION_ADD, item.vals.copy(), FX_TT_ENTRY, ) )
                self.MW.lock.acquire()
                self.MW.new_entry.clear()
                self.MW.lock.release()
        else:
            err = item.update(validate=False, no_commit=False)
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






    def on_del_entry(self, *args):
        """ Deletes selected entry"""
        if not self._lock_info(FX_LOCK_ENTRY): return 0
        item = args[-1]
        if item['deleted'] != 1: dialog = self.MW._run_dialog( YesNoDialog(self.MW, _('Delete Entry'), f'{_("Are you sure you want to delete")} <i><b>{esc_mu(item.name())}</b></i>?') )
        else: dialog = self.MW._run_dialog( YesNoDialog(self.MW, _('Delete Entry permanently'), f'{_("Are you sure you want to permanently delete")} <i><b>{esc_mu(item.name())}</b></i> {_("and associated rules?")}') ) 
        if dialog.response == 1: self.on_mark('delete', item)


    def on_restore_entry(self, *args):
        """ Restore entry """
        if not self._lock_info(FX_LOCK_ENTRY): return 0
        item = args[-1]
        dialog = self.MW._run_dialog( YesNoDialog(self.MW, _('Restore Entry'), f'{_("Are you sure you want to restore")} <i><b>{esc_mu(item.name())}</b></i>?') )
        if dialog.response == 1: self.on_mark('restore', item)




    def mark_thr(self, mode, item):
        """ Marks entry as read """
        DB = FeedexDatabase(connect=True)
        item = item.convert(FeedexEntry, DB, id=item['id'])
        if not item.exists: return -1

        if mode == 'read': idict = {'read': scast(item['read'],int,0)+1}
        elif mode == 'read+5': idict = {'read': scast(item['read'],int,0)+5}
        elif mode == 'unread': idict = {'read': 0}
        elif mode == 'unflag': idict = {'flag': 0}
        elif mode == 'restore': idict = {}
        elif mode == 'delete' : idict = {}
        elif type(mode) is int: idict = {'flag': mode}
        else: return -1

        if mode == 'delete': err = item.delete(no_commit=False)
        elif mode == 'restore': err = item.restore()
        else: err = item.update(idict, validate=True, no_commit=False)
        
        DB.close()
        if err == 0: fdx.bus_append( (FX_ACTION_EDIT, item.vals.copy(), FX_TT_ENTRY,) )



    def on_mark(self, *args):
        if not self._lock_info(FX_LOCK_ENTRY): return 0
        item = args[-1]
        mode = args[-2]
        msg(_('Updating ...') )
        self.start_thread(target=self.mark_thr, args=(mode, item,))


    def open_entry_thr(self, item, *args):
        """ Wrappper for opening entry and learning in a separate thread """
        DB = FeedexDatabase(connect=True)
        item = item.convert(FeedexEntry, DB, id=item['id'])
        item.open()
        DB.close()
        fdx.bus_append((FX_ACTION_EDIT, item.vals.copy(), FX_TT_ENTRY,))
        msg(_('Done...'))



    def on_open_entry(self, *args, **kargs):
        """ Run in browser and learn """
        msg(_('Opening ...'))
        item = args[-1]
        self.start_thread(target=self.open_entry_thr, args=(item,))






#######################################################################
#
#       Feeds and Categories

    def on_feed_cat(self, *args):
        """ Edit feed/category """
        if not self._lock_info(FX_LOCK_FEED, FX_LOCK_FETCH): return 0        
        item = args[-1]
        action = args[-2]

        if action == 'new_category':
            new = True
            item = FeedexFeed(self.DB)
            item.merge(self.MW.new_category)
            item.deraw_vals()
            dialog = self.MW._run_dialog( EditCategory(self.MW, item, new=new) )

        elif action == 'new_channel': 
            new = True
            item = FeedexFeed(self.DB)
            item.merge(self.MW.new_feed)
            item.deraw_vals()
            dialog = self.MW._run_dialog( EditFeed(self.MW, item, new=new) )

        elif action == 'edit':
            item = item.convert(FeedexFeed, self.DB, id=item['id'])
            new = False
            if not item.exists: return -1
            if item['is_category'] == 1: dialog = self.MW._run_dialog( EditCategory(self.MW, item, new=new) )
            else: dialog = self.MW._run_dialog( EditFeed(self.MW, item, new=new) )

        if action == 'new_category': self.MW.new_category = item.vals.copy()
        elif action == 'new_channel': self.MW.new_feed = item.vals.copy()

        if dialog.response == 1:
            if new: err = item.add(validate=False, no_commit=False)
            else:
                if item['is_category'] == 1: err = item.update(validate=True, no_commit=False)
                else: err = item.update(validate=False, no_commit=False)

            if err == 0:
                if action == 'new_category': self.MW.new_category.clear()
                elif action == 'new_channel': self.MW.new_feed.clear()

                self.MW.feed_tab.reload(load=True)





    def on_del_feed(self, *args):
        """ Deletes feed or category """
        if not self._lock_info(FX_LOCK_FETCH, FX_LOCK_FEED): return 0
        item = args[-1]

        if coalesce(item['is_category'],0) == 0 and coalesce(item['deleted'],0) == 0:
            dialog = self.MW._run_dialog( YesNoDialog(self.MW, _('Delete Channel'), f'{_("Are you sure you want to delete")} <i><b>{esc_mu(item.name())}</b></i>{_("?")}') )

        elif coalesce(item['is_category'],0) == 0 and coalesce(item['deleted'],0) == 1:
            dialog = self.MW._run_dialog( YesNoDialog(self.MW, _('Delete Channel permanently'), f'{_("Are you sure you want to permanently delete")} <i><b>{esc_mu(item.name())}</b></i>{_("?")}') )

        elif coalesce(item['is_category'],0) == 1 and coalesce(item['deleted'],0) == 0:
            dialog = self.MW._run_dialog( YesNoDialog(self.MW, _('Delete Category'), f'{_("Are you sure you want to delete")} <i><b>{esc_mu(item.name())}</b></i> {_("category?")}') )

        elif coalesce(item['is_category'],0) == 1 and coalesce(item['deleted'],0) == 1:
            dialog = self.MW._run_dialog( YesNoDialog(self.MW, _('Delete Category'), f'{_("Are you sure you want to permanently delete")} <i><b>{esc_mu(item.name())}</b></i> {_("category?")}') )

        if dialog.response == 1:
            item = item.convert(FeedexFeed, self.DB, id=item['id'])
            err = item.delete()
            if err == 0: self.MW.feed_tab.reload()





    def on_restore_feed(self, *args):
        """ Restores selected feed/category """
        if not self._lock_info(FX_LOCK_FETCH, FX_LOCK_FEED): return 0
        item = args[-1]

        if coalesce(item['is_category'],0) == 1: dialog = self.MW._run_dialog( YesNoDialog(self.MW, _('Restore Category'), f'{_("Restore ")}<i><b>{esc_mu(item.name())}</b></i>{_(" Category?")}') )
        else: dialog = self.MW._run_dialog( YesNoDialog(self.MW, _('Restore Channel'), f'{_("Restore ")}<i><b>{esc_mu(item.name())}</b></i>{_(" Channel?")}') )
        if dialog.response == 1:
            item = item.convert(FeedexFeed, self.DB, id=item['id'])
            err = item.restore()
            if err == 0: self.MW.feed_tab.reload()




    def on_mark_healthy(self, *args):
        """ Marks a feed as healthy -> zeroes the error count """
        if not self._lock_info(FX_LOCK_FETCH, FX_LOCK_FEED): return 0
        item = args[-1]
        item = item.convert(FeedexFeed, self.DB, id=item['id'])
        err = item.update({'error': 0})
        if err == 0: self.MW.feed_tab.reload()






#######################################################################
#
#       Rules

    def on_del_rule(self, *args):
        """ Deletes rule - wrapper """
        if not self._lock_info(FX_LOCK_FETCH, FX_LOCK_RULE): return 0
        item = args[-1]

        dialog = self.MW._run_dialog( YesNoDialog(self.MW, _('Delete Rule'), f'{_("Are you sure you want to permanently delete ")}<b><i>{esc_mu(item.name())}</i></b>{_(" Rule?")}')  )
        if dialog.response == 1:
            item = item.convert(FeedexRule, self.DB, id=item['id'])
            err = item.delete()
            if err == 0:
                if self.MW.rules_tab != -1: self.MW._get_upn_page_obj(self.MW.rules_tab).apply(FX_ACTION_DELETE, item.vals.copy())

        


    def on_edit_rule(self, *args):
        """ Edit / Add Rule with dialog """
        if not self._lock_info(FX_LOCK_FETCH, FX_LOCK_RULE): return 0
        item = args[-1]

        if item is None:
            new = True
            item = FeedexRule(self.DB)
            item.merge(self.MW.new_rule)
            item.deraw_vals()
        else: 
            new = False
            item = item.convert(FeedexRule, self.DB, id=item['id'])
            if not item.exists: return -1

        dialog = self.MW._run_dialog( EditRule(self.MW, item, new=new) )
        if new: self.MW.new_rule = item.vals.copy()
        if dialog.response == 1:
            if new: err = item.add(validate=False, no_commit=False)
            else: err = item.update(validate=False, no_commit=False)

            if err == 0:
                if self.MW.rules_tab != -1: 
                    if new: 
                        self.MW.new_rule.clear()
                        self.MW._get_upn_page_obj(self.MW.rules_tab).apply(FX_ACTION_ADD, item.vals.copy())
                    else: self.MW._get_upn_page_obj(self.MW.rules_tab).apply(FX_ACTION_EDIT, item.vals.copy())




#######################################################################
#
#       Flags


    def on_del_flag(self, *args):
        """ Deletes flag - wrapper """
        if not self._lock_info(FX_LOCK_FETCH, FX_LOCK_FLAG): return 0
        item = args[-1]

        dialog = self.MW._run_dialog( YesNoDialog(self.MW, _('Delete Flag'), f'{_("Are you sure you want to permanently delete ")}<b><i>{esc_mu(item.name())}</i></b>{_(" Flag?")}')  )
        if dialog.response == 1:
            item = item.convert(FeedexFlag, self.DB, id=item['id'])
            err = item.delete()
            if err == 0:
                if self.MW.flags_tab != -1: self.MW._get_upn_page_obj(self.MW.flags_tab).apply(FX_ACTION_DELETE, item.vals.copy())
                self.reload_flag_combos()

        

    def on_edit_flag(self, *args):
        """ Edit / Add Flag with dialog """
        if not self._lock_info(FX_LOCK_FETCH, FX_LOCK_FLAG): return 0
        item = args[-1]

        if item is None:
            new = True
            item = FeedexFlag(self.DB)
            item.merge(self.MW.new_flag)
            item.deraw_vals()
        else: 
            new = False
            item = item.convert(FeedexFlag, self.DB, id=item['id'])
            if not item.exists: return -1

        dialog = self.MW._run_dialog( EditFlag(self.MW, item, new=new) )
        if new: self.MW.new_flag = item.vals.copy()
        if dialog.response == 1:
            if new: err = item.add(validate=False, no_commit=False) 
            else: err = item.update(validate=False, no_commit=False)

            if err == 0:
                if self.MW.flags_tab != -1:
                    if new:
                        self.MW._get_upn_page_obj(self.MW.flags_tab).apply(FX_ACTION_ADD, item.vals.copy()) 
                        self.MW.new_flag.clear()
                    else: self.MW._get_upn_page_obj(self.MW.flags_tab).apply(FX_ACTION_EDIT, item.vals.copy())
                    self.reload_flag_combos()








###################################################################
#
#       Mass Operations

    def on_multi_thr(self, oper, result, ids, *args):
        DB = FeedexDatabase(connect=True)

        if isinstance(result, ResultEntry):
            ent = FX_ENT_ENTRY
            item = FeedexEntry(DB)
            compat = FX_TT_ENTRY
        elif isinstance(result, ResultRule):
            ent = FX_ENT_RULE
            item = FeedexRule(DB)
            compat = (FX_TAB_RULES,)
        elif isinstance(result, ResultFlag):
            ent = FX_ENT_FLAG
            item  = FeedexFlag(DB)
            compat = (FX_TAB_FLAGS,)
        elif isinstance(result, ResultFeed):
            ent = FX_ENT_FEED
            item  = FeedexFeed(DB)
            compat = (FX_TAB_FEEDS,)
        else:
            DB.close()
            return 0


        if oper == FX_ENT_ACT_DEL: 
            if ent in (FX_ENT_ENTRY, FX_ENT_FEED,): err = item.delete_many(ids)
            else: err = item.delete_perm_many(ids, perm=True)
        elif oper == FX_ENT_ACT_DEL_PERM: err = item.delete_perm_many(ids, perm=True)
        elif oper == FX_ENT_ACT_RES: err = item.restore_many(ids)
        elif type(oper) is dict: err = item.update_many(oper, ids)
        if err != 0: 
            DB.close()
            return err
        
        if ent == FX_ENT_FEED: fdx.bus_append(FX_ACTION_RELOAD_FEEDS)
        else:
            deltas = []
            for id in ids:
                if oper == FX_ENT_ACT_DEL: deltas.append( {'id':id, 'deleted':1} )
                elif oper == FX_ENT_ACT_DEL_PERM: deltas.append( {'id':id, 'deleted':2} )
                elif type(oper) is dict:
                    doper = oper.copy()
                    doper['id'] = id 
                    deltas.append(doper)

            if oper in (FX_ENT_ACT_DEL, FX_ENT_ACT_DEL_PERM,): fdx.bus_append( (FX_ACTION_DELETE, deltas, compat) )
            elif type(oper) is dict: fdx.bus_append( (FX_ACTION_EDIT, deltas, compat) )

        DB.close()
        return 0




    def on_multi(self, *args):
        """ Multi-actions on items"""
        if not self._lock_info(FX_LOCK_ENTRY, FX_LOCK_FETCH, FX_LOCK_FLAG, FX_LOCK_RULE): return 0
        oper = args[-1]
        result = args[-2]
        ids = result.toggled_ids
        item_no = len(ids)
        if oper == FX_ENT_ACT_UPD:
            dialog = self.MW._run_dialog( MassEditDialog(self.MW, result, item_no), unblock=False )
            if dialog.response == 1:
                if dialog.result == {}: return msg(_('Nothing to do...'))
                dialog2 = self.MW._run_dialog( YesNoDialog(self.MW, _('Mass Edit...'), f'{_("Are you sure you want to update ")}<b><i>{item_no}</i></b>{_(" items?")}', buttons=2, emblem='dialog-warning-symbolic') )
                if dialog2.response == 1:
                    self.start_thread(target=self.on_multi_thr, args=(dialog.result, result, ids,))


        elif oper == FX_ENT_ACT_DEL:
            dialog = self.MW._run_dialog( YesNoDialog(self.MW, _('Delete'), f'{_("Are you sure you want to remove ")}<b><i>{item_no}</i></b>{_(" items?")}', buttons=2, emblem='dialog-warning-symbolic')  )
            if dialog.response == 1: 
                self.start_thread(target=self.on_multi_thr, args=(FX_ENT_ACT_DEL,result, ids,))

        elif oper == FX_ENT_ACT_RES:
            dialog = self.MW._run_dialog( YesNoDialog(self.MW, _('Restore'), f'{_("Are you sure you want to restore ")}<b><i>{item_no}</i></b>{_(" items?")}', buttons=2, emblem='dialog-warning-symbolic')  )
            if dialog.response == 1: 
                self.start_thread(target=self.on_multi_thr, args=(FX_ENT_ACT_RES,result, ids,))

        elif oper == FX_ENT_ACT_DEL_PERM:
            dialog = self.MW._run_dialog( YesNoDialog(self.MW, _('Delete'), f'{_("Are you sure you want to permanently remove ")}<b><i>{item_no}</i></b>{_(" items?")}', buttons=2, emblem='dialog-warning-symbolic')  )
            if dialog.response == 1: 
                self.start_thread(target=self.on_multi_thr, args=(FX_ENT_ACT_DEL_PERM,result, ids,))
        



################################################################################3
#
#       Plugins

    def on_del_plugin(self, *args):
        """ Delete plugin """
        item = args[-1]
        item = item.convert(FeedexPlugin, main_win=self.MW, id=item['id'])
        if not item.exists: return -1

        dialog = self.MW._run_dialog( YesNoDialog(self.MW, _('Delete Plugin'), f'{_("Are you sure you want to remove ")}<b><i>{esc_mu(item.name())}</i></b>{_(" Plugin?")}', buttons=2)   )
        if dialog.response == 1:
            err = item.delete()
            if err == 0:
                if self.MW.plugins_tab != -1: self.MW._get_upn_page_obj(self.MW.plugins_tab).apply(FX_ACTION_DELETE, item.vals.copy())



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

        dialog = self.MW._run_dialog( EditPlugin(self.MW, item, new=new) )
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

        

    def on_run_plugin(self, *args):
        """ Execute plugin in context """
        plugin = FeedexPlugin(id=args[-2], main_win=self.MW)
        if not plugin.exists: return -1
        item = args[-1]
        plugin.run(item)



###############################################################################
#
#       Utilities




    def on_empty_trash_thr(self, *args):
        DB = FeedexDatabase(connect=True)
        DB.empty_trash()        
        DB.close()
        fdx.bus_append(FX_ACTION_RELOAD_TRASH)
        fdx.bus_append(FX_ACTION_RELOAD_FEEDS)
        fdx.bus_append(FX_ACTION_UNBLOCK_DB)


    def on_empty_trash(self, *args):
        """ Empty all Trash items """
        if not self._lock_info(FX_LOCK_FETCH, FX_LOCK_FEED, FX_LOCK_ENTRY): return 0
        dialog = self.MW._run_dialog( YesNoDialog(self.MW, _('Empty Trash'), f'<b>{_("Do you really want to permanently remove Trash content?")}</b>', emblem='edit-delete-symbolic') )
        if dialog.response == 1:
            fdx.bus_append(FX_ACTION_BLOCK_DB)            
            self.start_thread(target=self.on_empty_trash_thr, args=())
 


    def on_clear_history(self, *args):
        """ Clears search history """
        dialog = self.MW._run_dialog( YesNoDialog(self.MW, _('Clear Search History'), _('Are you sure you want to clear <b>Search History</b>?'), emblem='edit-clear-all-symbolic' ) )
        if dialog.response == 1:
            err = self.DB.clear_history()
            if err == 0: self.reload_history_all()


    def reload_history_all(self, *args):
        """ Reloads history in all tabs containing query combo """
        for i in range(self.MW.upper_notebook.get_n_pages()):
            tab = self.MW.upper_notebook.get_nth_page(i)
            if tab is None: continue
            if hasattr(tab, 'query_combo'): tab.reload_history()

    def reload_flag_combos(self, *args):
        """ Reloads flag combos in all tabs """
        store = f_list_store(f_flag_store_filters(), types=(str, str, str,) )
        for i in range(self.MW.upper_notebook.get_n_pages()):
            tab = self.MW.upper_notebook.get_nth_page(i)
            if tab is None: continue
            if hasattr(tab, 'flag_combo'):
                curr_flag = f_get_combo(tab.flag_combo)
                tab.flag_combo.set_model(store)
                f_set_combo(tab.flag_combo, curr_flag)


    def reload_cat_combos(self, *args):
        """ Reloads all cat/feed combos after changes took place """
        store = f_feed_store(self.MW, with_feeds=True)
        for i in range(self.MW.upper_notebook.get_n_pages()):
            tab = self.MW.upper_notebook.get_nth_page(i)
            if tab is None: continue
            if hasattr(tab, 'cat_combo'):
                curr_cat = f_get_combo(tab.cat_combo)
                tab.cat_combo.set_model(store)
                f_set_combo(tab.cat_combo, curr_cat)

    def reload_loc_combos(self, *args):
        """ Reload all location combos """
        store = f_location_store()
        for i in range(self.MW.upper_notebook.get_n_pages()):
            tab = self.MW.upper_notebook.get_nth_page(i)
            if tab is None: continue
            if hasattr(tab, 'loc_combo'): tab.loc_combo.set_model(store)



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
        dialog = self.MW._run_dialog( PreferencesDialog(self.MW), unblock=False )
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

        self.MW._run_dialog( BasicDialog(self.MW, _('Main Log'), log_str, width=600, height=500, justify=FX_ATTR_JUS_LEFT, selectable=True, scrolled=True, markup=False) )






    def on_show_detailed(self, *args):
        """ Shows dialog with entry's detailed technical info """
        mode = args[-2]
        item = args[-1]
        if mode == 'entry': item = item.convert(FeedexEntry, self.DB, id=item['id'])
        elif mode == 'feed': item = item.convert(FeedexFeed, self.DB, id=item['id'])
        else: return -1
        if not item.exists: return -1

        self.MW._run_dialog( BasicDialog(self.MW, _('Tech details'), esc_mu(item.__str__()), width=600, height=500, justify=FX_ATTR_JUS_LEFT, selectable=True, scrolled=True) )





    def on_show_stats(self, *args):
        """ Shows dialog with SQLite DB statistics """
        stats = self.DB.stats()
        stats_str = stats.mu_str()
        self.MW._run_dialog( BasicDialog(self.MW, _("Database Statistics"), stats_str, width=600, height=500, pixbuf=self.MW.icons.get('db'), justify=FX_ATTR_JUS_LEFT, selectable=True) )



    def on_show_session_log(self, *args):
        """ Show dialog with current session log """
        self.MW._run_dialog( BasicDialog(self.MW, _('Session log'), self.MW.log_string, width=600, height=500, justify=FX_ATTR_JUS_LEFT, selectable=True, scrolled=True) )



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
        self.MW._run_dialog( BasicDialog(self.MW, _('About...'), about_str, image='feedex.png', selectable=True) )














##########################################
#   DB Maintenance Stuff

    def on_maintenance_thr(self, *args, **kargs):
        """ DB Maintenance thread """
        DB = FeedexDatabase(connect=True)
        err = DB.maintenance()
        DB.close()
        fdx.bus_append(FX_ACTION_UNBLOCK_DB)


    def on_maintenance(self, *args, **kargs):
        """ BD Maintenance """
        if not self._lock_info(FX_LOCK_FETCH, FX_LOCK_ENTRY, FX_LOCK_FEED, FX_LOCK_RULE, FX_LOCK_FLAG): return 0
        
        dialog = self.MW._run_dialog( YesNoDialog(self.MW, _('DB Maintenance'), _('Are you sure you want to DB maintenance? This may take a long time...'), emblem='system-run-symbolic' )  )
        if dialog.response == 1:
            fdx.bus_append(FX_ACTION_BLOCK_DB)
            self.start_thread(target=self.on_maintenance_thr)



    def on_clear_cache_thr(self, *args, **kargs):
        DB = FeedexDatabase(connect=True)
        DB.clear_cache(-1)
        DB.close()
        fdx.bus_append(FX_ACTION_UNBLOCK_DB)


    def on_clear_cache(self, *args, **kargs):
        """ Clear image cache """
        dialog = self.MW._run_dialog( YesNoDialog(self.MW, _('Clear Cache'), _('Do you want to delete all downloaded and cached images/thumbnails?'),  emblem='edit-clear-all-symbolic')  )
        if dialog.response == 1:
            fdx.bus_append(FX_ACTION_BLOCK_DB)
            self.start_thread(target=self.on_clear_cache_thr)

    
    def del_learned_keywords(self, *args):
        """ Wrapper for deleting learned keywords from DB """
        dialog = self.MW._run_dialog(YesNoDialog(self.MW, _('Delete Learned Keywords?'), _('Do you want delete all learned Keywords used for recommendations?'), 
                             subtitle=_('<i>This action is permanent. Relearning can be time consuming</i>'),  emblem='dialog-warning-symbolic'), unblock=False)
        if dialog.response == 1:
            dialog2 = self.MW._run_dialog(YesNoDialog(self.MW, _('Delete Learned Keywords?'), _('Are you sure?'), emblem='dialog-warning-symbolic') )
            if dialog2.response == 1:
                err = self.DB.delete_learned_terms()
                if err == 0: 
                    if self.MW.learned_tab != -1: self.MW._get_upn_page_obj(self.MW.learned_tab).query(None, None)
        



    def recalc_thr(self, act, *args):
        DB = FeedexDatabase(connect=True)
        if act == 'relearn': DB.recalculate('..', learn=True, rank=False, index=False)
        elif act == 'reindex': DB.recalculate('..', learn=False, rank=False, index=True)
        elif act == 'rerank': DB.recalculate('..', learn=False, rank=True, index=False)
        DB.close()
        if self.MW.learned_tab != -1: self.MW._get_upn_page_obj(self.MW.learned_tab).query(None, None)
        fdx.bus_append(FX_ACTION_UNBLOCK_DB)


    def relearn_keywords(self, *args):
        """ Wrapper for relearning keywords """
        dialog = self.MW._run_dialog( YesNoDialog(self.MW, _('Relearn Keywords?'), _('Do you want to relearn Keywords for recommendations?'), 
                             subtitle=_('<i>This may take a long time</i>'),  emblem='applications-engineering-symbolic')
                            )
        if dialog.response == 1:
            fdx.bus_append(FX_ACTION_BLOCK_DB)
            self.start_thread(target=self.recalc_thr, args=('relearn',))






    ####################################################
    # Porting
    #           Below are wrappers for porting data



    def export_feeds(self, *args):
        filename = f_chooser(self.MW, self.MW, action='save', header=_('Export Feed data to...') )
        if filename is False: return 0
        fdx.connect_CLP()
        fdx.CLP.output = 'json_dict'
        fdx.CLP.ofile = filename
        self.DB.Q.list_feeds(all=True)
        fdx.CLP.out_table(self.DB.Q)


    def export_rules(self, *args):
        filename = f_chooser(self.MW, self.MW, action='save', header=_('Export Rules to...') )
        if filename is False: return 0
        fdx.connect_CLP()
        fdx.CLP.output = 'json_dict'
        fdx.CLP.ofile = filename
        self.DB.Q.list_rules()
        fdx.CLP.out_table(self.DB.Q)



    def export_flags(self, *args):
        filename = f_chooser(self.MW, self.MW, action='save', header=_('Export Flags to...') )
        if filename is False: return 0
        fdx.connect_CLP()
        fdx.CLP.output = 'json_dict'
        fdx.CLP.ofile = filename
        self.DB.Q.list_flags(all=True)
        fdx.CLP.out_table(self.DB.Q)

    def export_plugins(self, *args):
        filename = f_chooser(self.MW, self.MW, action='save', header=_('Export Plugins to...') )
        if filename is False: return 0
        save_json(filename, self.MW.gui_plugins)




    def import_feeds(self, *args):
        if not self._lock_info(FX_LOCK_FETCH, FX_LOCK_FEED): return 0

        filename = f_chooser(self.MW, self.MW, action='open_file', header=_('Import Feeds from...') )
        if filename is False: return 0

        err = self.DB.import_feeds(filename)
        self.MW.feed_tab.reload()


    def import_rules(self, *args):
        if not self._lock_info(FX_LOCK_FETCH, FX_LOCK_RULE): return 0

        filename = f_chooser(self.MW, self.MW, action='open_file', header=_('Import Rules from...') )
        if filename is False: return 0

        err = self.DB.import_rules(filename) 
        if self.MW.rules_tab != -1: self.MW._get_upn_page_obj(self.MW.rules_tab).query('',{})


    def import_flags(self, *args):
        if not self._lock_info(FX_LOCK_FETCH, FX_LOCK_FLAG): return 0

        filename = f_chooser(self.MW, self.MW, action='open_file', header=_('Import Flags from...') )
        if filename is False: return 0

        err = self.DB.import_flags(filename)
        if self.MW.flags_tab != -1: self.MW._get_upn_page_obj(self.MW.flags_tab).query('',{})



    def import_entries_thr(self, efile, **kargs):
        DB = FeedexDatabase(connect=True)
        err = DB.import_entries(efile=efile)
        DB.close()
        fdx.bus_append(FX_ACTION_UNBLOCK_DB)


    def import_entries(self, *args):
        filename = f_chooser(self.MW, self.MW, action='open_file', header=_('Import Entries from...') )
        if filename is False: return 0
        if not self._lock_info(FX_LOCK_FETCH, FX_LOCK_ENTRY): return 0
        fdx.bus_append(FX_ACTION_BLOCK_DB)
        self.start_thread(target=self.import_entries_thr, args=(filename,))



    def import_plugins(self, *args):
        filename = f_chooser(self.MW, self.MW, action='open_file', header=_('Import Plugins from...') )
        if filename is False: return 0

        new_plugins = self.MW.validate_gui_plugins( load_json(filename, [], create_file=False) )
        if len(new_plugins) > 0:
            self.MW.gui_plugins = list(self.MW.gui_plugins)
            max_id = len(self.MW.gui_plugins) + 1
            for p in new_plugins:
                p[FX_PLUGIN_TABLE.index('id')] = max_id
                max_id += 1
                self.MW.gui_plugins.append(p)
            
            err = save_json(self.MW.gui_plugins_path, self.MW.gui_plugins)
            if err == 0: msg(_('Plugins imported successfully...'))
            if self.MW.plugins_tab != -1: self.MW._get_upn_page_obj(self.MW.plugins_tab).query('',{})




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

        fdx.connect_CLP()
        fdx.CLP.output = format
        fdx.CLP.ofile = filename
        fdx.CLP.out_table(query)



    def import_catalog_thr(self, item, **args):
        """ Import feeds from catalog - threading """
        DB = FeedexDatabase(connect=True)
        item.DB = DB
        item.feed.set_interface(DB)
        item.do_import()
        DB.close()
        fdx.bus_append(FX_ACTION_UNBLOCK_DB)
        fdx.bus_append(FX_ACTION_RELOAD_FEEDS)


    def import_catalog(self, *args, **kargs):
        """ Import feeds from Catalog """
        if not self._lock_info(FX_LOCK_FETCH, FX_LOCK_FEED): return 0
        ids = args[-1]
        item = FeedexCatalog(db=self.DB)
        item.prep_import(ids)
        if item.queue_len == 0: return 0

        dialog = self.MW._run_dialog( YesNoDialog(self.MW, _('Subscribe...'), f"""{_('Subscribe to')} <b>{item.queue_len}</b> {_('Channels?')}""", emblem='rss-symbolic') )
        if dialog.response == 1:
            if not self._lock_info(FX_LOCK_FETCH, FX_LOCK_FEED): return 0
            fdx.bus_append(FX_ACTION_BLOCK_DB)
            self.start_thread(target=self.import_catalog_thr, args=(item,))



#########################################################################33
#           
#           Request handling from pipe


    def edit_entry_req_thr(self, item:FeedexEntry):
        """ Add Entry from ext. request low-level interface for threading """
        DB = FeedexDatabase(connect=True)
        item.set_interface(DB)
        err = item.add(validate=False, no_commit=False)
        if err == 0: 
            fdx.dnotify('edit', _('Note added'))
            fdx.bus_append( (FX_ACTION_ADD, item.vals.copy(), FX_TT_ENTRY, ) )
        else: fdx.dnotify('error', _('Error adding new Note!'))
        DB.close()



    def on_handle_req(self, req, *args, **kargs):
        """ Handles a request read from pipe """
        if req is None: return 0        
        if req.ent == FX_ENT_ENTRY and req.act == FX_ENT_ACT_ADD:
            entry = FeedexEntry(self.DB)
            entry.strict_merge(req.body)
            fdx.dnotify('edit', _('Adding new Note...'))
            self.start_thread(target=self.edit_entry_req_thr, args=(entry,) )

        elif req.ent == FX_ENT_FEED and req.act == FX_ENT_ACT_ADD:
            feed = FeedexFeed(self.DB)
            feed.merge(req.body)
            fdx.dnotify('rss', _('Adding new Feed...'))
            err = feed.add()
            if err == 0:
                fdx.dnotify('rss', _('Feed added')) 
                self.MW.feed_tab.reload(load=True)
            else: fdx.dnotify('error', _('Error adding new Feed!'))

        elif req.ent == FX_ENT_RULE and req.act == FX_ENT_ACT_ADD:
            rule = FeedexRule(self.DB)
            rule.merge(req.body)
            fdx.dnotify('script', _('Adding new Rule...'))
            err = rule.add()
            if err == 0:
                fdx.dnotify('script', _('Rule added'))
                if self.MW.rules_tab != -1:  self.MW._get_upn_page_obj(self.MW.rules_tab).apply(FX_ACTION_ADD, rule.vals.copy())
            else: fdx.dnotify('error', _('Error adding new Rule!'))

        return 0