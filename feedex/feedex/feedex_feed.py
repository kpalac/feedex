# -*- coding: utf-8 -*-
""" Entities classes:
     feeds - categories and channels

"""


from feedex_headers import *








class FeedexFeed(SQLContainerEditable):
    """ A class for Feed """

    def __init__(self, db, **kargs):
        SQLContainerEditable.__init__(self, db, FX_ENT_FEED)

        self.parent_feed = ResultFeed()

        self.header_oper_q = [] # Headers metadata from fetching
        self.url_redir_oper_q = [] # Url redirects
        self.meta_oper_q = [] # Textual metadata

        self.doc_count = None #Statistics for DB

        if kargs.get('id') is not None: self.get_by_id(kargs.get('id'))
        elif kargs.get('feed_id') is not None: self.get_feed_by_id(kargs.get('feed_id'))
        elif kargs.get('category_id') is not None: self.get_cat_by_id(kargs.get('category_id'))



    def get_feed_by_id(self, id:int, **kargs):
        feed = fdx.load_feed(id)
        if feed == -1:
            self.exists = False
            return msg(FX_ERROR_NOT_FOUND, _('Feed %a not found!'), id)
        else:
            self.exists = True
            self.populate(feed)
            self.ent_name = _('Feed')
            return 0

    def get_cat_by_id(self, id:int):
        feed = fdx.load_cat(id)
        if feed == -1:
            self.exists = False
            return msg(FX_ERROR_NOT_FOUND, _('Category %a not found!'), id)
        else:
            self.exists = True
            self.populate(feed)
            self.ent_name = _('Category')
            return 0
    
    def get_by_id(self, id:int):
        id = scast(id, int, -1)
        for f in fdx.feeds_cache:
            if f[self.get_index('id')] == id:
                self.populate(f)
                if self.vals['is_category'] != 1: self.ent_name = _('Feed')
                else: self.ent_name = _('Category')
                self.exists = True
                return 0
        return msg(FX_ERROR_NOT_FOUND, _('Channel/Category %a not found!'), id)


    def get_by_id_many(self, ids, **kargs):
        for f in fdx.feeds_cache:
            if f[self.get_index('is_category')] == 1: continue
            if f[self.get_index('id')] in ids: yield f



    def get_parent(self, **kargs):
        """ Load parent into container """
        for f in fdx.feeds_cache:
            if f[self.parent_feed.get_index('id')] == self.vals['parent_id']:
                self.parent_feed.populate(f)
                break

    def get_doc_count(self, **kargs):
        if self.doc_count is not None: return self.doc_count
        self.doc_count = scast( slist(self.DB.qr_sql("select count(id) from entries where feed_id = :feed_id", {'feed_id':coalesce(self.vals['id'],-1)}, one=True), 0, -1), int, 0)
        return self.doc_count

    

    def open(self, **kargs):
        """ Open in browser """
        if not self.exists: return FX_ERROR_NOT_FOUND
        if self.vals['is_category'] == 1: return msg(FX_ERROR_VAL, _('Cannot open a category!'))

        if self.vals.get('link') is not None:
            err = fdx.ext_open('browser', self.vals.get('link',''))
        else: return msg(FX_ERROR_VAL, _('No URL to open...'))
        return err





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


    def clear_q(self, **kargs):
        """ Clear all queues """
        SQLContainerEditable.clear_q(self, **kargs)
        self.header_oper_q.clear()
        self.meta_oper_q.clear()
        self.url_redir_oper_q.clear()





    def _hook(self, stage, **kargs):

        if stage == FX_ENT_STAGE_PRE_VAL:

            if self.action == FX_ENT_ACT_ADD: 
                self.vals['id'] = None
                self.vals['fetch'] = coalesce(self.vals.get('fetch'), 1)
                self.vals['handler'] = coalesce(self.vals.get('handler'), 'rss')

            if self.vals.get('parent_id') is not None: pass
            elif self.vals.get('cat') is not None: self.vals['parent_id'] = fdx.res_cat_name(self.vals['cat'])
            elif self.vals.get('cat_id') is not None: self.vals['parent_id'] = self.vals['cat_id']

            self.vals['interval'] = coalesce(self.vals.get('interval'), self.config.get('default_interval', 45))


        elif stage == FX_ENT_STAGE_POST_VAL:

            if self.vals['is_category'] == 1:
                if self.vals['parent_id'] not in (None, 0): return FX_ERROR_VAL, _('Nested categories are not allowed!')
            else:
                if self.vals['parent_id'] is not None:
                    cat = fdx.load_cat(self.vals['parent_id'])
                    if cat == -1: return FX_ERROR_VAL, _('Category %a not found!'), self.vals['parent_id']
                    self.parent_feed.populate(cat)
                    self.vals['parent_id'] = self.parent_feed['id']

                if self.vals['handler'] not in ('rss','local','html','script'): return FX_ERROR_VAL, _('Invalid handler! Must be rss, html, script or local')
                if self.vals['handler'] in ('rss','html') and not check_url(self.vals['url']): return FX_ERROR_VAL, _('Not a valid URL! (%a)'), self.vals['url']
                if self.vals['link'] is not None and not check_url(self.vals['link']): return FX_ERROR_VAL, _('Not a valid URL! (%a)'), self.vals['link']

                if self.vals['handler'] == 'html':
                    err = self.validate_regexes()
                    if err != 0: return err
                elif self.vals['handler'] == 'rss':
                    err = self.validate_regexes2()
                    if err != 0: return err

                if self.vals['interval'] is None or self.vals['interval'] < 0: return FX_ERROR_VAL, _('Interval must be >= 0!')
                if self.vals['autoupdate'] not in (None, 0, 1): return FX_ERROR_VAL, _('Autoupdate flag must be 0 or 1!')
                if self.vals['fetch'] not in (None, 0, 1): return FX_ERROR_VAL, _('Fetch flag must be 0 or 1!')

                if self.vals['auth'] is not None:
                    if self.vals['auth'] not in ('detect','basic','digest'): return FX_ERROR_VAL, _('Invalid authentication method (must be NONE, detect, basic or digest)')
                    if self.vals['passwd'] in ('',None): return FX_ERROR_VAL, _('Password must be provided!')
                    if self.vals['login'] in ('',None): return FX_ERROR_VAL, _('Login must be provided!')

            if self.vals['deleted'] not in (None, 0, 1): return FX_ERROR_VAL, _('Deleted marker must be 0 or 1!')

            if self.action == FX_ENT_ACT_ADD:
                self.vals['display_order'] = len(fdx.feeds_cache) + scast(self.vals.get('display_order'), int, 1)
                self.vals['deleted'] = 0

                if self.vals['is_category'] != 1:
                    self.vals['error'] = 0
                    self.vals['interval'] = scast(self.vals.get('interval'), int, self.config.get('default_interval',45))
        
                    if self.vals['handler'] in ('rss', 'html',):
                        for f in fdx.feeds_cache:
                            if f[self.get_index('url')] == self.vals['url'] and f[self.get_index('deleted')] != 1 :
                                return FX_ERROR_VAL, _('Channel with this URL already exists (%a)'), f'{f[self.get_index("name")]}:{f[self.get_index("id")]}'
                
                    self.ent_name = _('Feed')

                else: self.ent_name = _('Category')



            elif self.action == FX_ENT_ACT_UPD:
                if self.vals['is_category'] != 1: self.ent_name = _('Feed')
                else: self.ent_name = _('Category')





        elif stage == FX_ENT_STAGE_POST_OPER:

            if self.action == FX_ENT_ACT_DEL: self.sd_add('dc', -self.get_doc_count())
            elif self.action == FX_ENT_ACT_RES: self.sd_add('dc', self.get_doc_count())
        
            elif self.action == FX_ENT_ACT_DEL_PERM:

                debug(9, 'Removing icon...')            
                im_file = os.path.join(self.DB.icon_path, f'feed_{id}.ico')
                if os.path.isfile(im_file):
                    try: os.remove(im_file)
                    except (OSError, IOError,) as e: msg(FX_ERROR_IO, _('Error removing %a: %b'), im_file, e)

                debug(9, 'Removing images...')
                ent_ids = self.DB.qr_sql('select id from entries where feed_id = :id', {'id':self.vals['id']}, all=True)
                for eid in ent_ids:
                    eid = slist(eid, 0, -1)
                    im_file = os.path.join(self.DB.img_path, f'{id}.img')
                    tn_file = os.path.join(self.DB.cache_path, f'{id}.img')
                    if os.path.isfile(im_file):
                        try: os.remove(im_file)
                        except (OSError, IOError,) as e: msg(FX_ERROR_IO, _('Error removing image %a: %b'), im_file, e)
                    if os.path.isfile(tn_file):
                        try: os.remove(tn_file)
                        except (OSError, IOError,) as e: msg(FX_ERROR_IO, _('Error removing thumbnail %a: %b'), tn_file, e)

                debug(9, 'Removing from index...')
                self.DB.connect_ixer()
                try: self.DB.ixer_db.delete_document(f'FEED_ID {self.vals["id"]}')
                except xapian.DatabaseError as e: return msg(FX_ERROR_DB, _('Index error: %a'), e)  





        elif stage == FX_ENT_STAGE_PRE_COMMIT:
            
            if self.action == FX_ENT_ACT_DEL_PERM:
                msg(_('Saving changes...'))
                err = self.DB.run_sql_lock('delete from terms where context_id in (select e.ix_id from entries e where e.feed_id = :id)', self.oper_q)
                if err == 0: err = self.DB.run_sql_lock('delete from entries where feed_id = :id', self.oper_q)
                if err == 0: err = self.DB.run_sql_lock('update feeds set parent_id = NULL where parent_id = :id', self.oper_q)
                if err == 0: err = self.DB.run_sql_lock('delete from feeds where id = :id', self.oper_q)
                if err == 0: err = self.DB.close_ixer()
                if err == 0: self.oper_q.clear()
                self.rowcount = self.DB.rowcount
                return err


        elif stage == FX_ENT_STAGE_POST_COMMIT:

            if len(self.header_oper_q) > 0:
                msg(_('Saving headers...'))
                err = self.DB.run_sql_lock(self.update_sql(filter=FEEDS_HEADERS, wheres='id = :id'), self.header_oper_q)
                if err != 0: return err
            if len(self.url_redir_oper_q) > 0:
                msg(_('Saving redirects...'))
                err = self.DB.run_sql_lock('update feeds set url = :url where id = :id', self.url_redir_oper_q)
                if err != 0: return err
            if len(self.meta_oper_q) > 0:
                msg(_('Saving meta...'))
                err = self.DB.run_sql_lock(self.update_sql(filter=FEEDS_META, wheres='id = :id'), self.meta_oper_q)
                if err != 0: return err

        return 0








    def _upd_msg(self, field, **kargs):
        if field == 'parent_id' and self.vals[field] not in (None, 0): 
            return f'{self.ent_name} {_("%a assigned to")} %b', self.name(with_id=True), self.parent_feed.name(with_id=True)
        elif field == 'parent_id' and self.vals[field] in (None, 0): 
            return f'{self.ent_name} {_("%a detached from category")}', self.name(with_id=True)
        elif field == 'error' and self.vals[field] in (None,0):
            return f'{self.ent_name} {_("%a marked as healthy")}', self.name(with_id=True)                        
        elif field == 'deleted' and self.vals[field] in (None,0):
            return f'{self.ent_name} {_("%a restored")}', self.name(with_id=True)
        elif field == 'fetch' and self.vals[field] in (None,0):
            return _('Fetching disabled for %a'), self.name(with_id=True)
        elif field == 'fetch' and self.vals[field] == 1:
            return _('Fetching enabled for %a'), self.name(with_id=True)
        elif field == 'auth':
            return _('Authentication method changed for %a'), self.name(with_id=True)
        elif field == 'passwd':
            return _('Password changed for %a'), self.name(with_id=True)
        elif field == 'login':
            return _('Login changed for %a'), self.name(with_id=True)
        elif field == 'domain':
            return _('Domain (auth) changed for %a'), self.name(with_id=True)
        elif field == 'icon_name':
            return _('Icon changed for %a'), self.name(with_id=True)
        else: return SQLContainerEditable._upd_msg(self, field)

    def _del_perm_msg(self, **kargs): return f"""{self.ent_name} %a {_('deleted permanently with entries, keywords and images')}""", self.name()





    def update_meta_headers(self, delta, **kargs):
        """ Quickly update web meta headers """
        no_commit = kargs.get('no_commit', False)
        
        udict = self.filter_cast_incr(delta, FEEDS_HEADERS)
        udict['id'] = self.vals['id']
        self.header_oper_q.append(udict)
        
        url = scast(delta.get('url'), str, '').strip()
        if url != '' and check_url(url): self.url_redir_oper_q.append({'url':url, 'id':self.vals['id']})

        if no_commit: return 0
        
        err = self.commit()
        if err != 0: return 0
        return msg(_('Metadata headers updated...'))
    



    def update_meta(self, delta, **kargs):
        """ Quickly update textual metadata  """
        no_commit = kargs.get('no_commit', False)
        
        udict = self.filter_cast_incr(delta, FEEDS_META)
        udict['id'] = self.vals['id']
        self.meta_oper_q.append(udict)

        if no_commit: return 0
        
        err = self.commit()
        if err != 0: return 0
        return msg(_('Metadata updated...'))






    def add_from_url(self, idict, **kargs):
        """ Wrapper for adding and updating channel from URL """
        
        idict['is_category'] = 0
        idict['url'] = scast(idict.get('url'), str, '').strip()
        if idict.get('handler') is None: idict['handler'] = 'rss'
        if idict['handler'] == 'html': idict['link'] = idict['url']
        idict['autoupdate'] = 1
        idict['fetch'] = 1

        err = self.add(idict, validate=True)
        if err != 0: return err

        if kargs.get('no_fetch',False): return 0 # Sometimes fetching must be ommitted to allow further editing (e.g. authentication)
        if self.vals['handler'] not in ('rss',): return 0 # ...also, don't fetch if channel is not RSS etc.

        err = self.DB.fetch(id=self.vals['id'], force=True, ignore_interval=True)
        return err







    def _add_many(self, ilist, **kargs):
        """ Wrapper for multi-adding """
        self.action = FX_ENT_ACT_ADD

        msg(_('Adding new categories...'))
        cat_names_ids = {}
        tmp_ilist = []
        new_cats = 0
        new_feeds = 0

        for ii,i in enumerate(ilist):
            tpi = type(i)
            if tpi in (list, tuple): self.populate(i)
            elif tpi is dict:
                self.clear()
                self.merge(i)
            else: return msg(FX_ERROR_VAL, _('Invalid item %a format (must be list or dict)!'), ii)

            if self.vals['is_category'] == 1: 
                name = self.vals['name']
                cat_names_ids[self.vals['id']] = name
                
                found = False
                for f in fdx.feeds_cache:
                    if f[FEEDS_SQL_TABLE.index('is_category')] == 1:
                        if f[FEEDS_SQL_TABLE.index('name')] == name:
                            found = True
                            break
                if not found:
                    err = self.add(validate=True, no_commit=True)
                    if err != 0: 
                        msg(err, _('Item %a skipped...'), ii)
                        continue
                    new_cats += 1

            tmp_ilist.append(self.vals.copy())

        if new_cats > 0:
            err = self.commit()
            if err != 0: return msg(err, _('Operation aborted due to errors...'))
            else: 
                if fdx.single_run: self.DB.load_feeds()
                msg(_('Added %a new Categories out of %b items...'), new_cats, len(ilist))
        else: msg(_('No new Categories added...'))

        cat_name_id_map = {}
        for f in fdx.feeds_cache:
            if f[FEEDS_SQL_TABLE.index('is_category')] == 1:
                cat_name_id_map[f[FEEDS_SQL_TABLE.index('name')]] = f[FEEDS_SQL_TABLE.index('id')]

        msg(_('Adding new Feeds...'))
        for i in tmp_ilist:
            self.clear()
            self.merge(i)

            if self.vals['is_category'] == 1: continue

            if self.vals['parent_id'] is not None:
                name = cat_names_ids.get(self.vals['parent_id'])
                self.vals['parent_id'] = cat_name_id_map[name]

            err = self.add(validate=True, no_commit=True)
            if err != 0: 
                msg(err, _('Item %a skipped...'), ii)
                continue
            new_feeds += 1

        if new_feeds > 0:
            err = self.commit()
            if err != 0: return msg(err, _('Operation aborted due to errors...'))
            else: msg(_('Added %a new Feeds out of %b items...'), new_feeds, len(ilist))











    def insert(self, *args, **kargs): return self._run_locked(self._insert, *args, **kargs)
    def _insert(self, source_id, target_id):
        """ Reorder two feeds/cats and change category if needed """
        source_tpl = fdx.load_parent(source_id)
        target_tpl = fdx.load_parent(target_id)
        if source_tpl == -1: return msg(FX_ERROR_NOT_FOUND, _('Source not found'))
        if target_tpl == -1: return msg(FX_ERROR_NOT_FOUND, _('Target not found'))
        source, target = ResultFeed(), ResultFeed()
        source.populate(source_tpl)
        target.populate(target_tpl)

        tmp_list = []
        for f in fdx.feeds_cache: 
            if f[FEEDS_SQL_TABLE.index('is_category')] == 1: tmp_list.append( f[FEEDS_SQL_TABLE.index('id')] )
        for f in fdx.feeds_cache: 
            if f[FEEDS_SQL_TABLE.index('is_category')] != 1: tmp_list.append( f[FEEDS_SQL_TABLE.index('id')] )

        cat_change = {}
        if source['is_category'] == 1 and target['is_category'] == 1:
            tmp_list.remove(source['id'])
            tmp_list.insert(tmp_list.index(target['id']), source['id'])
        elif source['is_category'] != 1 and target['is_category'] == 1:
            cat_change = {'id':source['id'], 'parent_id':target['id']}
            tmp_list.remove(source['id'])
            tmp_list.insert(tmp_list.index(target['id'])+1, source['id'])
        elif source['is_category'] != 1 and target['is_category'] != 1:
            tmp_list.remove(source['id'])
            tmp_list.insert(tmp_list.index(target['id']), source['id'])
            if source['parent_id'] != target['parent_id']: cat_change = {'id':source['id'], 'parent_id':target['parent_id']}
        else: return msg(FX_ERROR_NOT_FOUND,_('Nothing to do'))

        ord_oper = []
        for i, id in enumerate(tmp_list): ord_oper.append( {'id':id, 'display_order':i} )

        err = 0
        if cat_change != {}: err = self.DB.run_sql_lock('update feeds set parent_id = :parent_id where id = :id', cat_change)
        if err == 0: err = self.DB.run_sql_lock('update feeds set display_order = :display_order where id = :id', ord_oper)
        if err == 0: 
            if not fdx.single_run: self.DB.load_feeds()
            msg(_('Feeds/Categories reorderred'))
        return err
















class ResultCatItem(SQLContainer):
    def __init__(self, **kargs): SQLContainer.__init__(self, 'catalog', FEEDEX_CATALOG_TABLE, types=FEEDEX_CATALOG_TABLE_TYPES, col_names=FEEDEX_CATALOG_TABLE_NAMES, entity=FX_ENT_CAT_ITEM)

class FeedexCatalog(ResultCatItem):
    """ Feed Catalog Item witgh import functionality """
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
                self.feed.add(self.feed.vals.copy())
                cat_dict[c] = self.feed['id']
        
        if fdx.single_run: self.DB.load_feeds()

        # Import feeds themselves
        for f in self.queue:
            self.feed.clear()
            self.feed['name'] = f[self.get_index('name')]
            self.feed['title'] = self['name']
            self.feed['url'] = f[self.get_index('link_res')]
            self.feed['link'] = f[self.get_index('link_home')]
            self.feed['subtitle'] = f[self.get_index('desc')]
            self.feed['handler'] = f[self.get_index('handler')]
            self.feed['location'] = f[self.get_index('location')]
            self.feed['interval'] = self.DB.config.get('default_interval', 45)
            self.feed['parent_id'] = cat_dict.get(f[-1])
            self.feed['autoupdate'] = 1
            self.feed['fetch'] = 1
            self.feed['is_category'] = 0
            err = self.feed.add(self.feed.vals.copy(), validate=True)
            if err == 0:
                thumbnail = os.path.join(FEEDEX_FEED_CATALOG_CACHE, 'thumbnails', f[self.get_index('thumbnail')])
                if os.path.isfile(thumbnail):
                    try: copyfile(thumbnail, os.path.join(self.DB.icon_path, f"""feed_{self.feed['id']}.ico""" ))
                    except (IOError, OSError,) as e: msg(FX_ERROR_IO, f"""{_('Error creating thumbnail for %a:')} {e}""", self.feed.name())
        return err









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




