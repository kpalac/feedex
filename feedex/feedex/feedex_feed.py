# -*- coding: utf-8 -*-
""" Entities classes:
     feeds - categories and channels

"""


from feedex_headers import *








class FeedexFeed(SQLContainerEditable):
    """ A class for Feed """

    def __init__(self, db, **kargs):
        SQLContainerEditable.__init__(self, 'feeds', FEEDS_SQL_TABLE, types=FEEDS_SQL_TYPES, col_names = FEEDS_SQL_TABLE_PRINT, **kargs)
        self.set_interface(db)
        self.DB.cache_feeds()

        self.parent_feed = ResultFeed()

        if kargs.get('id') is not None: self.get_by_id(kargs.get('id'))
        elif kargs.get('feed_id') is not None: self.get_feed_by_id(kargs.get('feed_id'))
        elif kargs.get('category_id') is not None: self.get_cat_by_id(kargs.get('category_id'))





    def get_feed_by_id(self, id:int):
        feed = fdx.find_feed(id, load=True)
        if feed == -1: 
            self.exists = False
            return msg(FX_ERROR_NOT_FOUND, _('Channel %a not found!'), id)
        else:
            self.exists = True
            self.populate(feed)
            return 0

    def get_cat_by_id(self, id:int):     
        feed = fdx.find_category(id, load=True)
        if feed == -1:
            self.exists = False
            return msg(FX_ERROR_NOT_FOUND, _('Category %a not found!'), id)
        else:
            self.exists = True
            self.populate(feed)
            return 0
    
    def get_by_id(self, id:int):
        for f in fdx.feeds_cache:
            if f[self.get_index('id')] == id:
                self.populate(f)
                self.exists = True
                return 0
        return msg(FX_ERROR_NOT_FOUND, _('Channel/Category %a not found!'), id)



    def get_parent(self, **kargs):
        """ Load parent into container """
        for f in fdx.feeds_cache:
            if f[self.parent_feed.get_index('id')] == self.vals['parent_id']:
                self.parent_feed.populate(f)
                break





    def open(self, **kargs):
        """ Open in browser """
        if not self.exists: return -8
        if self.vals['is_category'] == 1: return msg(FX_ERROR_VAL, _('Cannot open a category!'))

        if self.vals.get('link') is not None:
            err = fdx.ext_open('browser', self.vals.get('link',''))
        else: return msg(FX_ERROR_VAL, _('Empty URL!'))

        if err == 0: return msg(_('Sent to browser (%a)'), self.vals.get('link', _('<???>')))
        else: return err





    def validate_regexes(self, **kargs):
        """ Validate REGEX strings section """
        for f in FEEDS_REGEX_HTML_PARSERS:
            if self.vals[f] is not None and not check_if_regex(self.vals[f]):
                return FX_ERROR_VAL, f'{_("HTML parser: Not a valid REGEX")} ({f}): %a', self.vals[f]
        return 0

    def validate_regexes2(self, **kargs):
        """ Validate REGEX strings section (short)"""
        for f in ('rx_images','rx_link'):
            if self.vals[f] is not None and not check_if_regex(self.vals[f]):
                return FX_ERROR_VAL, f'{_("Custom entity parser: Not a valid REGEX")} ({f}): %a', self.vals[f]
        return 0



    def validate(self, **kargs):
        """ Validate present values """
        err = self.validate_types()
        if err != 0: return FX_ERROR_VAL, _('Invalid data type for %a'), err

        if self.vals['is_category'] == 1:
            if self.vals['parent_id'] not in (None, 0) and self.vals['parent_id'] == self.vals['id']: return FX_ERROR_VAL, _('Nested categories are not allowed!')
            if self.vals.get('parent_category') not in (None, 0): return FX_ERROR_VAL, _('Nested categories are not allowed!')
        else:
            if self.vals['handler'] in ('rss','html') and not check_url(self.vals['url']): return FX_ERROR_VAL, _('Not a valid URL! (%a)'), self.vals['url']
            if self.vals['link'] is not None and not check_url(self.vals['link']): return FX_ERROR_VAL, _('Not a valid URL! (%a)'), self.vals['link']

            if self.vals['handler'] == 'html':
                err = self.validate_regexes()
                if err != 0: return err
            elif self.vals['handler'] == 'rss':
                err = self.validate_regexes2()
                if err != 0: return err

            if self.vals['handler'] not in ('rss','local','html','script'): return FX_ERROR_VAL, _('Invalid handler! Must be rss, html, script or local')
            if self.vals['interval'] is None or self.vals['interval'] < 0: return FX_ERROR_VAL, _('Interval must be >= 0!')
            if self.vals['autoupdate'] not in (None, 0, 1): return FX_ERROR_VAL, _('Autoupdate flag must be 0 or 1!')
            if self.vals['fetch'] not in (None, 0, 1): return FX_ERROR_VAL, _('Fetch flag must be 0 or 1!')

            if self.vals['auth'] is not None:
                if self.vals['auth'] not in ('detect','basic','digest'): return FX_ERROR_VAL, _('Invalid authentication method (must be NONE, detect, basic or digest)')
                if self.vals['passwd'] in ('',None): return FX_ERROR_VAL, _('Password must be provided!')
                if self.vals['login'] in ('',None): return FX_ERROR_VAL, _('Login must be provided!')

            if 'parent_category' in self.vals.keys():
                if self.vals.get('parent_category') is not None:
                    feed = fdx.find_category(self.vals['parent_category'], load=True)
                    if feed == -1: return FX_ERROR_VAL, _('Category %a not found!'), self.vals['parent_category']
                    self.parent_feed.populate(feed)
                    self.vals['parent_id'] = self.parent_feed['id']
                else: self.vals['parent_id'] = None

            elif 'parent_id' in self.vals.keys():
                if self.vals['parent_id'] is not None:
                    feed = fdx.find_category(self.vals['parent_id'], load=True)
                    if feed == -1: return FX_ERROR_VAL, _('Category %a not found!'), self.vals['parent_id']
                    self.parent_feed.populate(feed)
                    self.vals['parent_id'] = self.parent_feed['id']
                else: self.vals['parent_id'] = None

        
        if self.vals['deleted'] not in (None, 0, 1): return FX_ERROR_VAL, _('Deleted flag must be 0 or 1!')

        return 0




    def do_update(self, **kargs):
        """ Apply edit changes to DB """
        if not self.updating: return 0
        if not self.exists: return -8

        if kargs.get('validate', True):
            err = self.validate()
            if err != 0:
                self.restore()
                return msg(*err)

        if coalesce(self.vals['deleted'],0) == 0 and coalesce(self.backup_vals['deleted'],0) >= 1: restoring = True
        else: restoring = False

        err = self.constr_update()
        if err != 0:
            self.restore()
            return err

        err = self.DB.run_sql_lock(self.to_update_sql, self.filter(self.to_update))
        if err != 0:
            self.restore()
            return err
        



        if self.DB.rowcount > 0:

            if not fdx.single_run: 
                err = self.DB.load_feeds()
                if err != 0: return msg(FX_ERROR_DB, _('Error reloading Feeds after successfull update!'))

            if restoring:
                err = self.DB.update_stats()
                if err != 0: return msg(FX_ERROR_DB, _('Error updating DB stats after successfull update!'))
                err = self.DB.load_rules()
                if err != 0: return msg(FX_ERROR_DB, _('Error reloading rules after successfull update!'))

            if self.vals['is_category'] == 1: stype = _('Category')
            else: stype = _('Channel')

            for i,u in enumerate(self.to_update):
                if u in self.immutable or u == 'id': del self.to_update[i]

            if len(self.to_update) > 1:
                return msg(f'{stype} {_("%a updated successfuly!")}', self.name(), log=True)
            else:
                for f in self.to_update:

                    if f == 'parent_id' and self.vals[f] not in (None, 0): 
                        return msg(f'{stype} {_("%a assigned to")} {self.parent_feed.name(with_id=True)}', self.name(with_id=True), log=True)
                    elif f == 'parent_id' and self.vals[f] in (None, 0): 
                        return msg(f'{stype} {_("%a detached from category")}', self.name(with_id=True), log=True)
                    elif f == 'error' and self.vals[f] in (None,0):
                        return msg(f'{stype} {_("%a marked as healthy")}', self.name(with_id=True), log=True)                        
                    elif f == 'deleted' and self.vals[f] in (None,0):
                        return msg(f'{stype} {_("%a restored")}', self.name(with_id=True), log=True)
                    elif f == 'fetch' and self.vals[f] in (None,0):
                        return msg(_('Fetching disabled for %a'), self.name(with_id=True), log=True)
                    elif f == 'fetch' and self.vals[f] == 1:
                        return msg(_('Fetching enabled for %a'), self.name(with_id=True), log=True)
                    elif f == 'auth':
                        return msg(_('Authentication method changed for %a'), self.name(with_id=True), log=True)
                    elif f == 'passwd':
                        return msg(_('Password changed for %a'), self.name(with_id=True), log=True)
                    elif f == 'login':
                        return msg(_('Login changed for %a'), self.name(with_id=True), log=True)
                    elif f == 'domain':
                        return msg(_('Domain (auth) changed for %a'), self.name(with_id=True), log=True)

                    else:
                        return msg(f'{stype} {_("%a updated")}:  {f} -> {self.vals.get(f,_("<NULL>"))}', self.name(with_id=True), log=True)
                return msg(_('Nothing done'))
        else:
            return msg(_('Nothing done'))




    def update(self, idict, **kargs):
        """ Quick update with a value dictionary """
        if not self.exists: return -8
        err = self.add_to_update(idict)
        if err == 0: err = self.do_update(validate=True)
        return err



    def delete(self, **kargs):
        """ Remove channel/cat with entries and rules if required """
        if not self.exists: return -8, _('Nothing to do. Aborting...')

        deleted = self.vals['deleted']

        id = {'id': self.vals['id']}
        if deleted == 1:
            # Remove from index ...
            self.DB.connect_ixer()
            try: self.DB.ixer_db.delete_document(f'FEED_ID {self.vals["id"]}')
            except xapian.DatabaseError as e:
                self.DB.close_ixer(rollback=True)
                return msg(FX_ERROR_DB, _('Index error: %a'), e)
            self.DB.close_ixer()

            # Delete irreversably with all data and icon
            err = self.DB.run_sql_multi_lock( \
                (("delete from rules where learned = 1 and context_id in (select e.id from entries e where e.feed_id = :id)", id ),\
                ("delete from entries where feed_id = :id", id),\
                ("update feeds set parent_id = NULL where parent_id = :id", id),\
                ("delete from feeds where id = :id", id)) )
            if err == 0:
                if fdx.icons_cache == {}: self.DB.load_icons()
                icon = fdx.icons_cache.get(self.vals['id'])
                if icon is not None and icon.startswith(os.path.join(self.DB.icon_path,'feed_')) and os.path.isfile(icon): os.remove(icon)

        else:
            # Simply mark as deleted
            err = self.DB.run_sql_lock("update feeds set deleted = 1 where id = :id", id)

        if err != 0: return err



        if self.DB.rowcount > 0:

            if not fdx.single_run: 
                err = self.DB.load_feeds()
                if err == 0: err = self.DB.load_rules()
                if err != 0: return msg(FX_ERROR_DB, _('Error reloading data after successfull delete!'))
            
            err = self.DB.update_stats()
            if err != 0: return msg(FX_ERROR_DB, _('Error updating DB stats after successfull delete!'))


            if self.vals['is_category'] == 1: stype = _('Category')
            else: stype = _('Channel')

            if deleted == 1:
                self.vals['deleted'] == 2
                self.exists = False
                return msg(f'{stype} {_("%a deleted permanently (with entries and rules)")}', f'{self.name()} ({self.vals["id"]})', log=True)
            else:
                self.vals['deleted'] = 1
                return msg(f'{stype} {_("%a deleted")}', f'{self.name(with_id=False)} ({self.vals["id"]})', log=True)
        
        else:
            return msg(_('Nothing done'))





    def add(self, **kargs):
        """ Add feed to database """
        if kargs.get('new') is not None: 
            self.clear()
            self.merge(kargs.get('new'))

        self.vals['id'] = None
        self.vals['display_order'] = len(fdx.feeds_cache)
        self.vals['deleted'] = 0

        if kargs.get('validate',True):
            err = self.validate()
            if err != 0: return msg(*err)

        if self.vals['is_category'] != 1:
            self.vals['error'] = 0
            self.vals['interval'] = scast(self.vals.get('interval'), int, self.config.get('default_interval',45))

        self.clean()
        err = self.DB.run_sql_lock(self.insert_sql(all=True), self.vals)
        if err != 0: return err
        
        self.vals['id'] = self.DB.lastrowid
        self.DB.last_feed_id = self.vals['id']

        if not fdx.single_run and not kargs.get('no_reload', False):
            err = self.DB.load_feeds()
            if err != 0: return msg(FX_ERROR_DB, _('Error reloading Feeds after successfull add!'))

        if self.vals['is_category'] == 1: stype = _('Category')
        else: stype = _('Channel')

        return msg(f'{stype} {_("%a added successfully")}', f'{self.name(with_id=True)}', log=True)





    def add_from_url(self, **kargs):
        """ Wrapper for adding and updating channel from URL """
        if kargs.get('new') is not None: 
            self.clear()
            self.merge(kargs.get('new'))

        self.vals['is_category'] = 0
        self.vals['url'] = self.vals['url'].strip()
        if self.vals.get('handler') is None: self.vals['handler'] = 'rss'
        if self.vals['handler'] == 'html': self.vals['link'] = self.vals.get('url')
        self.vals['interval'] = self.config.get('default_interval', 45)
        self.vals['autoupdate'] = 1
        if kargs.get('no_fetch',False): self.vals['fetch'] = 0
        else: self.vals['fetch'] = 1

        err = self.validate()
        if err != 0: return msg(*err)

        # Check if feed is already present (by URL)
        for f in fdx.feeds_cache:
            if f[self.get_index('url')] == self.vals['url'] and f[self.get_index('deleted')] != 1:
                return msg(FX_ERROR_VAL, _('Channel with this URL already exists (%a)'), f'{f[self.get_index("name")]} ({f[self.get_index("id")]})')

        err = self.add(validate=False)
        if err != 0: return -7

        if kargs.get('no_fetch',False): return 0 # Sometimes fetching must be ommitted to allow further editing (e.g. authentication)
        if self.vals['handler'] in ('local','html','script'): return 0 # ...also, don't fetch if channel is not RSS etc.

        err = self.DB.load_feeds()
        if err == 0:
            self.DB.fetch(id=self.vals['id'], force=True, ignore_interval=True)
        else:
            return msg(FX_ERROR_DB, _('Error while reloading Feeds for fetching!'))
        
        return 0








    def update_feed_order(self, **kargs):
        """ Updates feed order to DB according to current loaded list """
        update_list = []
        for i,f in enumerate(fdx.feeds_cache):
            id = f[self.get_index('id')]
            update_list.append({'display_order':i, 'id':id})
        err = self.DB.run_sql_lock('update feeds set display_order = :display_order where id = :id', update_list, many=True)
        if err != 0: return msg(FX_ERROR_DB, _('DB error while updating feed list order!'))
        
        if not fdx.single_run:
            err = self.DB.load_feeds()
            if err != 0: return msg(FX_ERROR_DB, _('Error while reloading Feeds after successful reorder!'))
        return 0


    def order_insert(self, target:int, **kargs):
        """ Insert (display order) before target, or assign to category """
        if not self.exists: return -8

        target = FeedexFeed(self.DB, id=target)
        if not target.exists: return -8

        with_cat = kargs.get('with_cat',False)            

        if (self.vals['is_category'] == 1 and target['is_category'] == 1) or (self.vals['is_category'] != 1 and target['is_category'] != 1):
            source_pos = None
            target_pos = None
            for i,f in enumerate(fdx.feeds_cache):
                if f[self.get_index('id')] == target['id']: target_pos = i
                if f[self.get_index('id')] == self.vals['id']: source_pos = i
                if source_pos is not None and target_pos is not None: break
            
            try: fdx.feeds_cache.insert(target_pos, fdx.feeds_cache[source_pos])
            except (ValueError, IndexError) as e: return msg(FX_ERROR_VAL, _('Error insering Channel/Category: %a'), e)

            for i,f in enumerate(fdx.feeds_cache):
                if f[self.get_index('id')] == self.vals['id'] and i != target_pos:
                    try: del fdx.feeds_cache[i]
                    except (ValueError, IndexError) as e:return msg(FX_ERROR_VAL, _('Error insering Channel/Category: %a'), e)
                    break

            err = self.update_feed_order()
            if err != 0: return err

            if with_cat:
                if (self.vals['is_category'] != 1 and target['is_category'] != 1) and (self.vals['parent_id'] != target['parent_id']) and (target['parent_id'] is not None):
                    err = self.update({'parent_id': target.get('parent_id')})
                    if err != 0: return err

        elif (self.vals['is_category'] != 1 and target['is_category'] == 1):
            err = self.update({'parent_id': target.get('id')})
            if err != 0: return err
        
        else:
            return msg(_('Nothing to do'))

        if not fdx.single_run:
            err = self.DB.load_feeds()
            if err != 0: return msg(FX_ERROR_DB, _('Error reloading Feeds after successfull operation!'))

        return msg(_('Display order changed successfully...'))

















