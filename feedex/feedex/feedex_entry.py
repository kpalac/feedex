# -*- coding: utf-8 -*-
""" Entities classes: entries

"""


from feedex_headers import *




class ResultContainer(SQLContainerEditable):
    """ Container for search results """
    def __init__(self, **kargs):
        SQLContainerEditable.__init__(self,'entries', RESULTS_SQL_TABLE, types=RESULTS_SQL_TYPES, **kargs)

    def name(self):
        return ellipsize(self.vals.get('title', self.vals.get('id', '<UNKNOWN>')), 300)



class EntryContainer(SQLContainerEditable):
    """ Container for Entries """

    def __init__(self, FX, **kargs):
        SQLContainerEditable.__init__(self, 'entries', ENTRIES_SQL_TABLE, types=ENTRIES_SQL_TYPES, **kargs)

        self.set_interface(FX)
        self.debug = self.FX.debug
        self.config = self.FX.config

        self.recalculate = False # These flags mark the need to recalculate linguistics and relearn rules
        self.relearn = False
        
        self.learn = True # This switch can disable learning conditions on adding and updating

        self.feed = FeedContainerBasic()

        self.rule = SQLContainer('rules', RULES_SQL_TABLE)

        self.immutable = ENTRIES_TECH_LIST

        if kargs.get('id') is not None: self.get_by_id(kargs.get('id'))
        elif kargs.get('url') is not None: self.get_by_url(kargs.get('url'))

        # Strings to index in Xapian
        self.ix_strings = {}
        # Strings used for full text ranking
        self.rank_string = ''
        # String to extract features from
        self.learning_string = ''

        # Last Xapian doc id
        self.last_xap_doc = 0

        # Source link (useful as a feature and independent of db structure)
        self.source_url = None

        self.rules = [] # Rules extracted by LP




    def get_by_id(self, id:int): 
        content = self.FX.qr_sql("select * from entries e where e.id = :id", {'id':id}, one=True )
        if content in (None, (None,), ()):
            self.exists = False
            cli_msg( (-1, _('Entry %a not found!'), id) )
            return -1
        else:
            self.exists = True
            self.populate(content)
            return 0

    def get_by_url(self, url:str): 
        content = self.FX.qr_sql("select * from entries e where e.link = :url", {'url':url}, one=True )
        if content in (None, (None,), ()):
            self.exists = False
            cli_msg( (-1, _('Entry %a not found!'), url) )
            return -1
        else:
            self.exists = True
            self.populate(content)
            return 0

    def get_by_ix_id(self, id:int): 
        content = self.FX.qr_sql("select * from entries e where e.ix_id = :id", {'id':id}, one=True )
        if content in (None, (None,), ()):
            self.exists = False
            cli_msg( (-1, _('Entry %a not found!'), id) )
            return -1
        else:
            self.exists = True
            self.populate(content)
            return 0



    def name(self):
        return ellipsize(coalesce(self.vals.get('title'), scast(self.vals.get('id'), str, '<UNKNOWN>')), 300)

    def set_feed(self, **kargs):
        """ Setup feed for processing """
        if kargs.get('feed') is not None:
            feed = kargs.get('feed')
            if feed[self.feed.get_index('id')] != self.feed['id']: self.feed.populate(feed)
        else:
            if self.feed['id'] != self.vals['feed_id']:
                feed = self.FX.resolve_f_o_c(self.vals['feed_id'], load=True)
                if feed != -1: self.feed.populate(feed)





    def open(self, **kargs): 
        for msg in self.g_open(**kargs): self.FX.update_ret_code( cli_msg(msg) )
    def g_open(self, **kargs):
        """ Open in browser """
        if not self.exists:
            yield -8, _('Nothing to open. Aborting...')
            return -8

        read = coalesce(self.vals['read'],0)
        if kargs.get('update_read',True):
            
            now = datetime.now()
            now_raw = int(now.timestamp())
            now = now.strftime('%Y-%m-%d %H:%M:%S')

            if read >= 0: err = self.FX.run_sql_lock('update entries set read = coalesce(read,0) + 1, adddate = :now_raw, adddate_str = :now where id = :id', 
                                                    {'id':self.vals['id'], 'now':now, 'now_raw':now_raw})
            else: err = self.FX.run_sql_lock('update entries set read = 1, adddate = :now_raw, adddate_str = :now  where id = :id', 
                                            {'id':self.vals['id'], 'now':now, 'now_raw':now_raw})
            if err != 0: 
                yield -2, _('DB error: %a'), err
                return -2
            self.vals['read'] = read + 1
            self.vals['adddate'] = now_raw
            self.vals['adddate_str'] = now

        if self.vals.get('link') is not None:
            err = ext_open(self.config, 'browser', self.vals.get('link'), debug=self.debug, background=kargs.get('background',True))
            if err != 0:
                yield err
                return -1
            else: 
                yield 0, _('Opening in browser (%a) ...'), self.vals.get('link', '<UNKNOWN>')



        if kargs.get('learn',True) and self.learn and self.config.get('use_keyword_learning', True) and read == 0: learn = True
        else: learn = False

        # Reindex and learn
        if learn: yield 0, _('Reindexing and learning keywords...')
        else: yield 0, _('Reindexing ...')
        
        err = self.ling(learn=learn, index=True, rank=False, save_rules=kargs.get('save_rules', True))
        if err != 0: yield -2, _('DB error: %a'), err
        else: 
            yield 0, _('Keywords learned')
            if not self.FX.single_run: 
                err = self.FX.load_rules()
                if err != 0: 
                    yield -2, _('Error reloading rules after successfull open: %a'), err
                    return -2

        return 0                        







    def validate(self, **kargs):
        """ Field validation """
        if self.vals['flag'] not in (0,None): self.vals['flag'] = self.FX.resolve_flag(self.vals['flag'])
        if self.vals['flag'] == -1: return -7, _('Flag not found!')

        err_fld = self.validate_types()
        if err_fld != 0: return -7, _('Invalid type for field %a'), err_fld

        if self.vals.get('feed_or_cat') is not None:
            feed = self.FX.resolve_f_o_c(self.vals.get('feed_or_cat'), load=True)
            if feed == -1: return -7, _('Channel or Category %a not found!'), self.vals.get('feed_or_cat', '<UNKNOWN>')
            self.feed.populate(feed)
            self.vals['feed_id'] = self.feed['id']

        elif self.vals.get('feed_id') is not None:
            feed = self.FX.resolve_f_o_c(self.vals.get('feed_id'), load=True)
            if feed == -1: return -7, _('Channel or Category %a not found!'), self.vals.get('feed_id', '<UNKNOWN>')
            self.feed.populate(feed)
            self.vals['feed_id'] = self.feed['id']

        elif self.vals.get('parent_id') is not None:
            feed = self.FX.resolve_f_o_c(self.vals.get('parent_id'), load=True)
            if feed == -1: return -7, _('Channel or Category %a not found!'), self.vals.get('parent_id', '<UNKNOWN>')
            self.feed.populate(feed)
            self.vals['feed_id'] = self.feed['id']

        elif self.vals.get('parent_category') is not None:
            feed = self.FX.resolve_category(self.vals.get('parent_category'), load=True)
            if feed == -1: return -7, _('Category %a not found!'), self.vals.get('parent_category', '<UNKNOWN>')
            self.feed.populate(feed)
            self.vals['feed_id'] = self.feed['id']

        else:
            if self.vals.get('feed') is not None: self.vals['feed_id'] = self.vals.get('feed')
            feed = self.FX.resolve_feed(self.vals.get('feed_id'), load=True)
            if feed is None: return -7, _('Every entry needs to be assigned to a Channel or a Category!')
            if feed == -1: return -7, _('Channel %a not found!'), self.vals['feed_id']
            self.feed.populate(feed)
            self.vals['feed_id'] = self.feed['id']


        if self.vals.get('link') is not None and not check_url(self.vals.get('link')):
            return -7, _('Not a valid url! (%a)'), self.vals.get('link', '<UNKNOWN>')

        if self.vals['deleted'] not in (None, 0, 1): return -7, _('Deleted flag must be 0 or 1!')
        
        if self.vals['note'] not in (None, 0,1): return -7, _('Note marker must be 0 or 1!')

        date = convert_timestamp(self.vals['pubdate_str'])
        if date is None: return -7, _('Invalid published date string (pubdate_str)!')
        else: self.vals['pubdate'] = date

        if self.vals['adddate_str'] is not None:
            date = convert_timestamp(self.vals['adddate_str'])
            if date is None: return -7, _('Invalid adding date string (%a)!'), self.vals['adddate_str']
            else: self.vals['adddate'] = date

        return 0






    def do_update(self, **kargs): 
        for msg in self.g_do_update(**kargs): self.FX.update_ret_code( cli_msg(msg) )
    def g_do_update(self, **kargs):
        """ Apply edit changes to DB """
        if not self.updating: 
            yield 0, _('Nothing to do')
            return 0
        if not self.exists: 
            yield -8, _('Nothing to do. Aborting...')
            return -8


        self.vals['adddate_str'] = datetime.now()

        if kargs.get('validate', True): 
            err = self.validate()
            if err != 0: 
                yield err
                self.restore()
                return -7


        if coalesce(self.vals['deleted'],0) == 0 and coalesce(self.backup_vals['deleted'],0) >= 1: restoring = True
        else: restoring = False

        self.relearn = False
        self.recalculate = False

        err = self.constr_update()
        if err != 0:
            self.restore()
            yield err
            return -1

        for f in self.to_update:
            if f in REINDEX_LIST: self.recalculate = True
            
        if self.learn and self.config.get('use_keyword_learning', True):
            if self.recalculate and coalesce(self.vals['read'],0) > 0: self.relearn = True
            if coalesce(self.vals['read'],0) > 0 and coalesce(self.backup_vals['read'],0) == 0: self.relearn = True
            if coalesce(self.vals['read'],0) < 0 and coalesce(self.backup_vals['read'],0) == 0: self.relearn = True
            if coalesce(self.vals['read'],0) >= 0 and coalesce(self.backup_vals['read'],0) < 0: self.relearn = True

        if self.recalculate or self.relearn:
            if self.recalculate:  yield 0, _('Recalculating statistics ...')
            if self.relearn: yield 0, _('Extracting and learning keywords ...')

            err = self.ling(index=True, rank=self.recalculate, learn=self.relearn, save_rules=self.relearn)
            if err != 0: 
                self.restore()
                yield -1, _('Error processing linguistic data: %a'), err
                return -1

        if coalesce(self.vals['read'], 0) < 0: self.vals['importance'] = 0

        # Construct second time, to include recalculated fields
        err = self.constr_update()
        if err != 0:
            self.restore()
            yield err
            return -1

        err = self.FX.run_sql_lock(self.to_update_sql, self.filter(self.to_update))
        if err != 0:
            self.restore()
            yield -2, _('DB error: %a'), err
            return -2


        if self.FX.rowcount > 0:

            for i,u in enumerate(self.to_update):
                if u in self.immutable or u == 'id': del self.to_update[i]

            if self.relearn and not self.FX.single_run: 
                err = self.FX.load_rules()
                if err != 0: 
                    yield -2, _('Error reloading rules after successfull update: %a'), err
                    return -2
            if restoring: 
                err = self.FX.update_stats()
                if err != 0: 
                    yield -2, _('Error updating DB stats after successfull update: %a'), err
                    return -2

            if len(self.to_update) > 1:
                self.FX.log(False, f'Entry {self.vals["id"]} updated')
                yield 0, _('Entry %a updated successfuly!'), self.vals['id']
            else:
                for f in self.to_update:
                    if f == 'read' and self.vals.get(f,0) > 0: 
                        self.FX.log(False, f'Entry {self.vals["id"]} marked as read')
                        yield 0, _('Entry %a marked as read'), self.vals['id']
                    elif f == 'read' and self.vals.get(f,0) < 0: 
                        self.FX.log(False, f'Entry {self.vals["id"]} marked as unimportant')
                        yield 0, _('Entry %a marked as read'), self.vals['id']
                    elif f == 'read' and self.vals.get(f) in (0, None): 
                        self.FX.log(False, f'Entry {self.vals["id"]} marked as unread')
                        yield 0, _('Entry %a marked as unread'), self.vals['id']
                    elif f == 'flag' and self.vals.get(f) in (0,None): 
                        self.FX.log(False, f'Entry {self.vals["id"]} unflagged')
                        yield 0, _('Entry %a unflagged'), self.vals['id']
                    elif f == 'flag' and self.vals.get(f) not in (0, None): 
                        self.FX.log(False, f'Entry {self.vals["id"]} flagged')
                        yield 0, _('Entry %a flagged'), self.vals['id']
                    elif f == 'deleted' and self.vals.get(f) in (0, None): 
                        self.FX.log(False, f'Entry {self.vals["id"]} restored')
                        yield 0, _('Entry %a restored'), self.vals['id']
                    elif f == 'note' and self.vals.get(f) in (0, None): 
                        self.FX.log(False, f'Entry {self.vals["id"]} marked as News item')
                        yield 0, _('Entry %a marked as news item'), self.vals['id']
                    elif f == 'note' and self.vals.get(f) == 1: 
                        self.FX.log(False, f"""Entry {self.vals["id"]} marked as a user's Note""")
                        yield 0, _("""Entry %a marked as a user's Note"""), self.vals['id']
                    elif f == 'feed_id': 
                        self.FX.log(False, f'Entry {self.vals["id"]} assigned to {self.feed.name(id=True)}')
                        yield 0, f'{_("Entry %a assigned to")} {self.feed.name(id=True)}', self.vals['id']
                    elif f == 'node_id' and self.vals.get(f) in (0, None): 
                        self.FX.log(False, f'Entry {self.vals["id"]} unassigned from node')
                        yield 0, _('Entry %a unassigned from node')
                    elif f == 'node_id' and self.vals.get(f) not in (0, None): 
                        self.FX.log(False, f'Entry {self.vals["id"]} assigned to entry {self.vals["node_id"]}')
                        yield 0, _(f'Entry {{self.vals["id"]}} assigned to entry %a'), self.vals['node_id']
                    else:
                        self.FX.log(False, f'Entry {self.vals["id"]} updated:  {f} -> {self.vals.get(f,_("<NULL>"))}')
                        yield 0, f'{_("Entry %a updated")}:  {f} -> {self.vals.get(f,_("<NULL>"))}', self.vals['id']
            return 0

        else:
            yield 0, 'Nothing done'
            return 0





    def update(self, idict, **kargs): 
        for msg in self.g_update(idict, **kargs): self.FX.update_ret_code( cli_msg(msg) )
    def g_update(self, idict, **kargs):
        """ Quick update with a value dictionary"""
        if not self.exists:
            yield -8, _('Nothing to do. Aborting...')
            return -8

        err = self.add_to_update(idict)
        if err != 0:
            yield err
            print(err)
            return -1

        for msg in self.g_do_update(validate=True): yield msg
        return 0
        






    def delete(self, **kargs): self.FX.MC.ret_status = cli_msg(self.r_delete(**kargs))
    def r_delete(self, **kargs):
        """ Delete from DB with rules if necessary """
        if not self.exists: return -8, _('Nothing to do. Aborting...')

        id = kargs.get('id', None)
        if id is not None and self.vals['id'] is None: self.get_by_id(id)

        id = self.vals.get('id')

        if id is None: return -8, _('Entry %a not found!'), id

        if self.vals.get('deleted',0) == 1:
            err = self.FX.run_sql_multi_lock( \
                (("delete from rules where context_id = :id", {'id':id}),\
                ("delete from entries where id = :id", {'id':id}) ))
        else:
            now = datetime.now()
            now_raw = convert_timestamp(now)
            err = self.FX.run_sql_lock("update entries set deleted = 1, adddate = :now_raw, adddate_str = :now where id = :id", {'id':id, 'now':now, 'now_raw':now_raw} )
            if err == 0:
                # Remove from index ...
                self.FX.connect_ixer()
                try: ix_doc = self.FX.ixer_db.get_document(self.vals['ix_id'])
                except (xapian.DocNotFoundError,): ix_doc = None
                if isinstance(ix_doc, xapian.Document):
                    uuid = ix_doc.get_data()
                    try: self.FX.ixer_db.delete_document(f"""UUID {uuid}""")
                    except xapian.DatabaseError as e: return -2, _('Index error: %a'), e
                self.FX.close_ixer()


        if err != 0: return -2, _('DB error: %a'), err



        if self.FX.rowcount > 0:

            if not self.FX.single_run: 
                err = self.FX.load_rules()
                if err != 0: return -2, _('Error reloading rules after successfull delete: %a'), err
            err = self.FX.update_stats()
            if err != 0: return -2, _('Error updating DB stats after successfull delete: %a'), err

            if self.vals.get('deleted',0) == 1:
                self.vals['deleted'] = 2
                self.exists = False 
                self.FX.log(False, f'Entry {id} deleted permanently with rules')
                return 0, _('Entry %a deleted permanently with rules'), id
            else:
                self.vals['deleted'] = 1
                self.FX.log(False, f'Entry {id} deleted')
                return 0, _('Entry %a deleted'), id
        else:                
            return 0, _('Nothing done')







    def add(self, **kargs):
        for msg in self.g_add(**kargs): self.FX.update_ret_code( cli_msg(msg) )
    def g_add(self, **kargs):

        counter = kargs.get('counter',0)

        idict = kargs.get('new')
        if idict is not None:
            self.clear()
            self.merge(idict)

        now = datetime.now()
        
        if self.vals.get('learn') is not None:
            if self.vals.get('learn',True) is True: self.learn = True
            else: self.learn = False

        self.vals['id'] = None
        self.vals['adddate_str'] = now
        self.vals['pubdate_str'] = coalesce(self.vals.get('pubdate_str', None), now)
        self.vals['read'] = coalesce(self.vals.get('read'), self.config.get('default_entry_weight',2))
        self.vals['note'] = coalesce(self.vals['note'],1)

        if kargs.get('validate',True):
            err = self.validate()
            if err != 0:
                yield err
                return -7

        if not self.learn: learn = False
        elif not self.config.get('use_keyword_learning', True): learn = False
        elif (kargs.get('learn', False) or coalesce(self.vals['read'], 0) > 0) and self.vals.get('learn',True): learn = True
        else: learn = False

        if kargs.get('ling',True): self.ling(index=True, rank=True, learn=learn, save_rules=False, counter=counter)
        else: learn = False

        self.clean()

        err = self.FX.run_sql_lock(self.insert_sql(all=True), self.vals)
        if err != 0: 
            yield -2, _('DB error: %a'), err
            return -2
        
        self.vals['id'] = self.FX.lastrowid
        self.FX.last_entry_id = self.vals['id']
    
        if learn:
            yield 0, _('Extracting and learning keywords ...')
            err = self.save_rules()
            if err != 0:
                yield -1, _('Error saving keywords: %a'), err
                return -1
            else:
                yield 0, _('Keywords learned for entry %a'), self.vals['id']

        if kargs.get('update_stats',True):
            if not self.FX.single_run: 
                err = self.FX.load_rules()
                if err != 0: return -2, _('Error reloading rules after successfull add: %a'), err

            err = self.FX.update_stats()
            if err != 0: return -2, _('Error updating DB stats after successfull add: %a'), err

        if self.vals['note'] in (0,None): yield 0, _('Entry %a added as News item'), self.vals['id']
        else: yield 0, _('Entry %a added as a Note'), self.vals['id']
        return 0











    ###############################################
    #  Linguistic processing methods

    def ling(self, **kargs):
        """ Linguistic processing coordinator """

        multi = kargs.get('multi',False)  # are we in the middle of multiple insert/update? If yes, then no need to disconnect indexer
        learn = kargs.get('learn',False)
        stats = kargs.get('stats',True)
        rank = kargs.get('rank',True)
        save_rules = kargs.get('save_rules', learn)
        index = kargs.get('index', stats)
        to_var = kargs.get('to_var',False)
        counter = kargs.get('counter',0) # Counter for generating UUIDs
        rebuilding = kargs.get('rebuilding',False) # This tells if we are creating index anew and, if yes, we clear IX_IDs

        # Setup language and remember if detection was tried
        self.vals['lang'] = self.FX.LP.set_model(self.vals['lang'], sample=f"""{self.vals['title']} {self.vals['desc']}"""[:1000])

        self.set_feed()


        if index or rank:

            self.ix_strings, self.rank_string = self.FX.LP.index(self.vals)
            
            if index:
                self.FX.connect_ixer()

                # Remove doc if exists ...
                if rebuilding or self.vals['ix_id'] is None: ix_doc = None
                else:
                    try: ix_doc = self.FX.ixer_db.get_document(self.vals['ix_id'])
                    except (xapian.DocNotFoundError,): ix_doc = None

                if isinstance(ix_doc, xapian.Document):
                    exists = True
                    ix_doc.clear_terms()
                    ix_doc.clear_values()
                    uuid = ix_doc.get_data()
                else:
                    exists = False
                    ix_doc = xapian.Document()
                    uuid = None
                    
                if uuid in (None, ''):
                    # Generating UUID... A desperate fight against coincidence
                    ts = datetime.now()
                    uuid = f"""{int(round(ts.timestamp()))}{counter}{random_str(length=10)}{len(scast(self.vals['title'], str, 'a'))}"""
                    ix_doc.set_data(uuid)



                self.FX.ixer.set_document(ix_doc)

                # Add UUID
                ix_doc.add_boolean_term(f"""UUID {uuid}""")
                # Add feed tag for easier deletes later on
                ix_doc.add_boolean_term(f'FEED_ID {self.vals["feed_id"]}')
                # ... and other filters
                ix_doc.add_boolean_term(f"""HANDLER {self.feed.get("handler",'')}""")
                if coalesce(self.vals["note"],0) >= 1: ix_doc.add_boolean_term(f"""NOTE 1""")
                else: ix_doc.add_boolean_term(f"""NOTE 0""")
                if coalesce(self.vals["read"],0) >= 1: ix_doc.add_boolean_term(f"""READ 1""")
                else: ix_doc.add_boolean_term(f"""READ 0""")

                ix_doc.add_value(0, xapian.sortable_serialise(scast(self.vals['pubdate'], int, 0)) )
                ix_doc.add_value(1, xapian.sortable_serialise(scast(self.vals['adddate'], int, 0)) )
                ix_doc.add_value(2, xapian.sortable_serialise(scast(self.vals['flag'], int, 0)) )

                # Index token strings, restarting term position after each one to facilitate mixed searches ...
                for k in ('',PREFIXES['exact'],):
                    self.FX.ixer.set_termpos(0)
                    for f in self.ix_strings[k]: self.FX.ixer.index_text( scast(f[1], str, ''), scast(f[0], int, 1), k)
                last_pos = self.FX.ixer.get_termpos() + 100
                
                # Add semantic postings one by one not to spam ...
                for f in self.ix_strings[PREFIXES['sem']]:
                    sems = f[1]
                    weight = scast(f[0], int, 1)
                    for s,ps in sems.items():
                        for p in ps:
                            ix_doc.add_posting(f"""{PREFIXES['sem']}{s.lower()}""", p, weight)
    
                # Index meta fields
                self.FX.ixer.set_termpos(last_pos)
                for k in META_PREFIXES:
                    for f in self.ix_strings[k]: self.FX.ixer.index_text( scast(f[1], str, ''), scast(f[0], int, 1), k)
                self.FX.ixer.set_termpos(last_pos)
                for k in META_PREFIXES_EXACT:
                    for f in self.ix_strings[k]: self.FX.ixer.index_text( scast(f[1], str, ''), scast(f[0], int, 1), k)

                # Save stemming variants
                for k,v in self.FX.LP.variants.items():
                    for s in v: self.FX.ixer_db.add_synonym(k,s)

                # Add/Replace in Database
                if exists:
                    try: self.vals['ix_id'] = self.FX.ixer_db.replace_document(f'UUID {uuid}', ix_doc)
                    except (xapian.DatabaseError, xapian.DocNotFoundError,) as e: return e
                    if self.debug in (1,2,): print(f'Replaced Xapian doc: {self.vals["ix_id"]}')
                else:            
                    try: self.vals['ix_id'] = self.FX.ixer_db.add_document(ix_doc)
                    except (xapian.DatabaseError,) as e: return e
                    if self.debug in (1,2,): print(f"""Added Xapian doc: {self.vals['ix_id']}""")

                if stats: 
                    self.FX.LP.calculate_stats()
                    self.merge(self.FX.LP.stats)

                if not multi: self.FX.close_ixer()



        if rank:
            # Perform ranking based on saved rules. Construct laerning string for stemmed rules
            if self.feed['url'] not in (None, ''): self.rank_string = f"""  {self.rank_string}  URL:{self.feed['url']}  """
            if not to_var:
                self.vals['importance'], self.vals['flag'] = self.FX.LP.rank(self.vals, self.rank_string, to_var=False)
            else: 
                return self.FX.LP.rank(self.vals, self.rank_string, to_var=True)


        if learn:
            # Learn text features by creating a learning string and running smallsem on it...
            self.learning_string = ''
            for f in LING_TEXT_LIST: self.learning_string = f"""{self.learning_string}  {scast(self.vals[f], str, '')}"""
            depth = MAX_FEATURES_PER_ENTRY
            rules_tmp = self.FX.LP.extract_features(self.learning_string, depth=depth)

            # Append link to source as a feature
            if self.feed['url'] not in (None, ''): rules_tmp.append([f"""URL:{self.feed['url']}""", SOURCE_URL_WEIGHT, f"""URL:{self.feed['url']}"""])

            self.rules.clear()
            for r in rules_tmp:
                self.rule.clear()
                self.rule['string'] = f"""{scast(r[2], str, '')}"""
                self.rule['weight'] = scast(r[1], float, 0) #* self.vals['weight']
                self.rule['name'] = scast(r[0], str, '')
                self.rule['type'] = 1
                self.rule['case_insensitive'] = 0
                self.rule['lang'] = self.vals['lang']
                self.rule['learned'] = 1
                self.rule['flag'] = 0
                self.rule['additive'] = 1
                self.rule['context_id'] = self.vals['id']

                self.rules.append(self.rule.vals.copy())

            # Sometimes we need to temporarily skip saving rules to DB
            if save_rules:
                err = self.save_rules()
                if err != 0: return err
        
        return 0






    def save_rules(self, **kargs):
        """ Save pending rules """
        # Build rule list ...
        if self.debug in (1,4): 
            for r in self.rules: print(r)

        # ... delete existing rules for this entry ...
        err = self.FX.run_sql_lock("delete from rules where context_id = :id and learned = 1", {'id': self.vals['id']} )
        if err != 0: return err

        # ... and save new rule set to database
        err = self.FX.run_sql_lock(self.rule.insert_sql(all=True), self.rules, many=True)
        if err != 0: return err

        if self.debug in (1,4): print('Rules learned')
        return 0







