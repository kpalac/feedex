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
        id = scast(id, int, -1)
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


    def get_doc_count(self, **kargs):
        return scast( slist(self.DB.qr_sql("select count(id) from entries where feed_id = :feed_id", {'feed_id':coalesce(self.vals['id'],-1)}, one=True), 0, -1), int, 0)



    def open(self, **kargs):
        """ Open in browser """
        if not self.exists: return FX_ERROR_NOT_FOUND
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
        if not self.exists: return FX_ERROR_NOT_FOUND

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

            if not fdx.single_run: self.DB.load_feeds(ignore_lock=True)

            if restoring:
                err = self.DB.update_stats({'dc':self.get_doc_count()})
                if err == 0: err = self.DB.load_terms()
                if err != 0: return err

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



    def update(self, idict, **kargs): return self.DB.run_fetch_locked(self._update, idict, **kargs)
    def _update(self, idict, **kargs):
        """ Quick update with a value dictionary """
        if not self.exists: return -8
        err = self.add_to_update(idict)
        if err == 0: err = self.do_update(validate=True)
        return err


    def delete(self, **kargs): return self.DB.run_fetch_locked(self._delete, **kargs)
    def _delete(self, **kargs):
        """ Remove channel/cat with entries and keywords if required """
        if not self.exists: return FX_ERROR_NOT_FOUND

        stats_delta = {}

        deleted = self.vals['deleted']

        id = {'id': self.vals['id']}
        if deleted == 1:
            # Delete irreversably with all data and icon
            err = self.DB.run_sql_multi_lock( \
                (("delete from terms where context_id in (select e.id from entries e where e.feed_id = :id)", id ),\
                ("delete from entries where feed_id = :id", id),\
                ("update feeds set parent_id = NULL where parent_id = :id", id),\
                ("delete from feeds where id = :id", id)) )
            
            if err == 0:
                if fdx.icons_cache == {}: self.DB.load_icons(ignore_lock=True)
                icon = fdx.icons_cache.get(self.vals['id'])
                if icon is not None and icon.startswith(os.path.join(self.DB.icon_path,'feed_')) and os.path.isfile(icon): os.remove(icon)
            
                # Remove from index ...
                self.DB.connect_ixer()
                try: self.DB.ixer_db.delete_document(f'FEED_ID {self.vals["id"]}')
                except xapian.DatabaseError as e:
                    self.DB.close_ixer(rollback=True)
                    return msg(FX_ERROR_DB, _('Index error: %a'), e)
                self.DB.close_ixer()
            
            if err != 0: return err


        else:
            # Simply mark as deleted
            err = self.DB.run_sql_lock("update feeds set deleted = 1 where id = :id", id)
            if err != 0: return err
            # ... and update general doc count stats
            stats_delta['dc'] = -self.get_doc_count()          



        if self.DB.rowcount > 0:

            if not fdx.single_run: self.DB.load_feeds(ignore_lock=True)
            err = self.DB.update_stats(stats_delta)
            if err != 0: return err

            if self.vals['is_category'] == 1: stype = _('Category')
            else: stype = _('Channel')

            if deleted == 1:
                self.vals['deleted'] == 2
                self.exists = False
                return msg(f'{stype} {_("%a deleted permanently (with entries and learned keywords)")}', f'{self.name()} ({self.vals["id"]})', log=True)
            else:
                self.vals['deleted'] = 1
                return msg(f'{stype} {_("%a deleted")}', f'{self.name(with_id=False)} ({self.vals["id"]})', log=True)
        
        else:
            return msg(_('Nothing done'))




    def add(self, **kargs): return self.DB.run_fetch_locked(self._add, **kargs)
    def _add(self, **kargs):
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

        if not fdx.single_run and not kargs.get('no_reload', False): self.DB.load_feeds(ignore_lock=True)

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
        if err != 0: return err

        if kargs.get('no_fetch',False): return 0 # Sometimes fetching must be ommitted to allow further editing (e.g. authentication)
        if self.vals['handler'] in ('local','html','script'): return 0 # ...also, don't fetch if channel is not RSS etc.

        self.DB.load_feeds()
        err = self.DB.fetch(id=self.vals['id'], force=True, ignore_interval=True)        
        return err










    def update_feed_order(self, **kargs): return self.DB.run_fetch_locked(self.update_feed_order, **kargs)
    def _update_feed_order(self, **kargs):
        """ Updates feed order to DB according to current loaded list """
        update_list = []
        for i,f in enumerate(fdx.feeds_cache):
            id = f[self.get_index('id')]
            update_list.append({'display_order':i, 'id':id})
        err = self.DB.run_sql_lock('update feeds set display_order = :display_order where id = :id', update_list, many=True)
        if err != 0: return msg(FX_ERROR_DB, _('DB error while updating feed list order!'))
        
        if not fdx.single_run:
            err = self.DB.load_feeds(ignore_lock=True)
            if err != 0: return msg(FX_ERROR_DB, _('Error while reloading Feeds after successful reorder!'))
        return 0





    def order_insert(self, target:int, **kargs): return self.DB.run_fetch_locked(self._order_insert, target, **kargs)
    def _order_insert(self, target:int, **kargs):
        """ Insert (display order) before target, or assign to category """
        if not self.exists: return FX_ERROR_NOT_FOUND

        target = FeedexFeed(self.DB, id=target)
        if not target.exists: return FX_ERROR_NOT_FOUND

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
                    except (ValueError, IndexError) as e: return msg(FX_ERROR_VAL, _('Error insering Channel/Category: %a'), e)
                    break

            err = self._update_feed_order()
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
            err = self.DB.load_feeds(ignore_lock=True)
            if err != 0: return msg(FX_ERROR_DB, _('Error reloading Feeds after successfull operation!'))

        return msg(_('Display order changed successfully...'))















class ResultCatItem(SQLContainer):
    def __init__(self, **kargs):
        SQLContainer.__init__(self, 'catalog', FEEDEX_CATALOG_TABLE)
        self.col_names = FEEDEX_CATALOG_TABLE_NAMES
        self.types = FEEDEX_CATALOG_TABLE_TYPES

    def humanize(self): pass
    def fill(self): pass





class FeedexCatalog(ResultCatItem):
    """ Store item from """
    def __init__(self, **kargs) -> None:
        ResultCatItem.__init__(self, **kargs)
        self.DB = kargs.get('db', None)


    def parse_ids(self, ids_str, **kargs):
        """ Parse ids from comma-separated string """
        ids = []
        for id in ids_str.split(','):
            id = scast(id, int, None)
            if id is None: continue
            elif id <= 0: continue
            ids.append(id)
        return ids


    def prep_import(self, ids, **kargs):
        """ Mass import of toggled items """
        if type(ids) is str: ids = self.parse_ids(ids)
        ids = scast(ids, list, [])
        if ids == []: return msg(FX_ERROR_VAL, _('No valid IDs given!'))
        fdx.load_catalog()

        self.feed = FeedexFeed(self.DB)
        self.queue = []
        self.url_q = []
        self.cat_q = []
        self.cat_im_dict = {}
        
        self.present_feeds = []
        for f in fdx.feeds_cache:
            if f[self.feed.get_index('is_category')] != 1 and f[self.feed.get_index('deleted')] != 1 and f[self.feed.get_index('url')] not in (None, ''):
                self.present_feeds.append(f[self.feed.get_index('url')])
        
        for ci in fdx.catalog:
            if ci[self.get_index('is_node')] == 1: 
                self.cat_im_dict[ci[self.get_index('name')]] = ci[self.get_index('thumbnail')]
                continue
            if ci[self.get_index('id')] in ids:
                if ci[self.get_index('link_res')] in self.present_feeds: continue
                if ci[self.get_index('link_res')] not in self.url_q:
                    c = ci.copy()
                    parent_name = ''
                    for pi in fdx.catalog:
                        if pi[self.get_index('is_node')] != 1: continue
                        if pi[self.get_index('id')] == c[self.get_index('parent_id')]:
                            parent_name = pi[self.get_index('name')]
                            break
                    c.append(parent_name)
                    if parent_name not in self.cat_q and parent_name != '': self.cat_q.append(parent_name)
                    self.queue.append(c)
                    self.url_q.append(ci[self.get_index('link_res')])
        self.queue_len = len(self.queue)
        if self.queue_len == 0: msg(_('Nothing to import...'))




    def do_import(self, **kargs):
        # Create categories if needed
        cat_dict = {}
        for c in self.cat_q:
            exists = False
            for f in fdx.feeds_cache:
                if f[self.feed.get_index('is_category')] != 1: continue
                if f[self.feed.get_index('name')] == c or f[self.feed.get_index('title')] == c:
                    exists = True
                    cat_dict[c] = f[self.feed.get_index('id')]
                    break
            
            if not exists:
                self.feed.clear()
                self.feed['is_category'] = 1
                self.feed['name'] = c
                self.feed['title'] = c
                self.feed['icon_name'] = self.cat_im_dict[c]
                self.feed.add(no_reload=True)
                cat_dict[c] = self.feed['id']

        self.DB.load_feeds()

        # Import feeds themselves
        for f in self.queue:
            self.feed.clear()
            self.feed['name'] = f[self.get_index('name')]
            self.feed['title'] = self['name']
            self.feed['url'] = f[self.get_index('link_res')]
            self.feed['link'] = f[self.get_index('link_home')]
            self.feed['subtitle'] = f[self.get_index('desc')]
            self.feed['handler'] = f[self.get_index('handler')]
            self.feed['interval'] = self.DB.config.get('default_interval', 45)
            self.feed['parent_id'] = cat_dict.get(f[-1])
            self.feed['autoupdate'] = 1
            self.feed['fetch'] = 1
            self.feed['is_category'] = 0
            err = self.feed.add(no_reload=True)
            if err == 0:
                thumbnail = os.path.join(FEEDEX_FEED_CATALOG_CACHE, 'thumbnails', f[self.get_index('thumbnail')])
                if os.path.isfile(thumbnail):
                    try: copyfile(thumbnail, os.path.join(self.DB.icon_path, f"""feed_{self.feed['id']}.ico""" ))
                    except (IOError, OSError,) as e: msg(FX_ERROR_IO, f"""{_('Error creating thumbnail for %a:')} {e}""", self.feed.name())

        if not fdx.single_run: self.DB.load_feeds()









    def catalog_add_category(self, name, id, children_no, icon, **kargs):
        """ Add single category item """
        self.curr_id += 1
        self.clear()
        self['id'] = id
        self['name'] = name
        self['parent_id'] = None
        self['children_no'] = children_no
        self['is_node'] = 1
        self['thumbnail'] = icon
        self.results.append(self.tuplify())
        return self.curr_id



    def catalog_download_category(self, name, url, icon, **kargs):
        """ Build a category node for Feed cache """
        msg(_('Processing %a'), f'{name} ({url})')
        response, html = fdx.download_res(url, output_pipe='', user_agent=FEEDEX_USER_AGENT, mimetypes=FEEDEX_TEXT_MIMES)
        if type(response) is int or type(html) is not str: return FX_ERROR_HANDLER

        parent_id = self.curr_id
        count = 0
        node_tmp = []

        entries = re.findall('<h3 id=(.*?<p class=.*?)</p>', html, re.DOTALL)
        for i, e in enumerate(entries):
            self.clear()
            self.curr_id += 1
            count += 1
            self['id'] = self.curr_id
            sname = slist( re.findall('<img src=".*?" data-lazy-src=".*?" class="thumb.*?" alt="(.*?)"', e), 0, '')
            self['name'] = fdx.strip_markup(sname)[0]
            desc1 = slist( re.findall('<span class="feed_desc ">(.*?)<span class="feed_desc_more">', e), 0, '')
            desc2 = slist( re.findall('<span class="feed_desc_mrtxt">(.*?)</span>', e), 0, '')
            self['desc'] = fdx.strip_markup(f'{desc1}{desc2}')[0]
            self['link_home'] = slist( re.findall('<a class=" extdomain ext" href="(.*?)"', e), 0, '')
            self['link_res'] = slist( re.findall('<a class="ext" href="(.*?)"', e), 0, '')
            if self['link_res'] == '': continue
            self['link_img'] = slist( re.findall('<img src=".*?" data-lazy-src="(.*?)" class="thumb.*?" alt=".*?"', e), 0, '')
            self['location'] = slist( re.findall('<span class="location_new">(.*?)</span>', e), 0, '')
            self['freq'] = slist( re.findall('<span class="fs-frequency">.*?title="Frequency"></i> <span class="eng_v">(.*?)</span></span>', e), 0, '')
            self['rank'] = i
            self['handler'] = 'rss'
            self['parent_id'] = parent_id
            self['is_node'] = 0

            thumbnail_base = f"""{fdx.hash_url(self['link_res'])}.img"""
            path_tmp = os.path.join(self.odir_thumbnails, thumbnail_base)
            if not os.path.isfile(path_tmp): fdx.download_res(self['link_img'], ofile=path_tmp, verbose=True)
            self['thumbnail'] = thumbnail_base
            node_tmp.append(self.tuplify())

        self.catalog_add_category(name, parent_id, count, icon)
        self.results = self.results + node_tmp
        return 0



    def build_catalog(self, **kargs):
        """ Build Feed catalog JSON cache from web resource """        
        msg(_('Building catalog...'))
        self.odir = kargs.get('odir', None)
        if self.odir is None: return msg(FX_ERROR_IO, _('No output dir provided!'))
        if not os.path.isdir(self.odir):
            if os.path.exists(self.odir): msg(FX_ERROR_IO, _('Not a directory (%a)!'))
            try: os.mkdir(self.odir)
            except (OSError, IOError,) as e: return msg(FX_ERROR_IO, _('Error creating directory:'), e)

        self.odir_thumbnails = os.path.join(self.odir, 'thumbnails')
        if not os.path.isdir(self.odir_thumbnails):
            if os.path.exists(self.odir_thumbnails): msg(FX_ERROR_IO, _('Not a directory (%a)!'))
            try: os.mkdir(self.odir_thumbnails)
            except (OSError, IOError,) as e: return msg(FX_ERROR_IO, _('Error creating thumbnails directory:'), e)
                
        self.curr_id = 0
        self.results = []
        self.catalog_download_category('World News', 'https://blog.feedspot.com/world_news_rss_feeds/', 'www')
        self.catalog_download_category('US News', 'https://rss.feedspot.com/usa_news_rss_feeds/', 'radio')
        self.catalog_download_category('Europe News', 'https://rss.feedspot.com/european_news_rss_feeds/', 'radio')
        self.catalog_download_category('Indian News', 'https://rss.feedspot.com/indian_news_rss_feeds/', 'radio')
        self.catalog_download_category('Asian News', 'https://rss.feedspot.com/asian_news_rss_feeds/', 'radio')
        self.catalog_download_category('Chinese News', 'https://rss.feedspot.com/chinese_news_rss_feeds/?_src=tagcloud', 'radio')
        self.catalog_download_category('UK News', 'https://rss.feedspot.com/uk_news_rss_feeds/?_src=tagcloud', 'radio')
        self.catalog_download_category('Russian News', 'https://rss.feedspot.com/russian_news_rss_feeds/', 'radio')
        
        self.catalog_download_category('Technology', 'https://rss.feedspot.com/technology_rss_feeds/', 'electronics')
        self.catalog_download_category('Science', 'https://rss.feedspot.com/science_rss_feeds/', 'science')
        self.catalog_download_category('Music', 'https://rss.feedspot.com/music_rss_feeds/', 'audio')
        self.catalog_download_category('Books', 'https://rss.feedspot.com/book_review_rss_feeds/', 'bookmark')
        self.catalog_download_category('Movies', 'https://rss.feedspot.com/movie_rss_feeds/?_src=rss_directory', 'player')
        self.catalog_download_category('Travel', 'https://rss.feedspot.com/travel_rss_feeds/', 'travel')
        self.catalog_download_category('Food', 'https://rss.feedspot.com/food_rss_feeds/?_src=rss_directory', 'health')
        self.catalog_download_category('Gaming', 'https://rss.feedspot.com/video_game_rss_feeds/', 'game')
        self.catalog_download_category('Pets', 'https://rss.feedspot.com/pet_rss_feeds/?_src=rss_directory', 'heart')
        self.catalog_download_category('Education', 'https://rss.feedspot.com/education_rss_feeds/?_src=rss_directory', 'education')
        self.catalog_download_category('Art', 'https://rss.feedspot.com/art_rss_feeds/?_src=rss_directory', 'image')
        self.catalog_download_category('Economics', 'https://rss.feedspot.com/economics_rss_feeds/?_src=rss_directory', 'money')
        self.catalog_download_category('Sports', 'https://rss.feedspot.com/sports_news_rss_feeds/', 'sport')
        self.catalog_download_category('Science Fiction', 'https://rss.feedspot.com/science_fiction_rss_feeds/', 'engineering')
        self.catalog_download_category('Parenting', 'https://rss.feedspot.com/parenting_rss_feeds/?_src=rss_directory_p', 'heart')
        self.catalog_download_category('Mental Health', 'https://rss.feedspot.com/mental_health_rss_feeds/?_src=rss_directory_m', 'community')


        err = save_json(os.path.join(self.odir,'catalog.json'), self.results)
        return err



    def open(self, *args, **kargs):
        """ Visit homepage """
        link = scast(self.vals.get('link_home'), str, '')
        if link is not None: err = fdx.ext_open('browser', link)
        else: return msg(FX_ERROR_VAL, _('Empty URL!'))

        if err == 0: return msg(_('Sent to browser (%a)'), link)
        else: return err




