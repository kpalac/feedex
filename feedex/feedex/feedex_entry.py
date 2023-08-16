# -*- coding: utf-8 -*-
""" Entities classes: entries

"""


from feedex_headers import *



class FeedexEntry(SQLContainerEditable):
    """ Container for Entries """

    def __init__(self, db, **kargs):
        SQLContainerEditable.__init__(self, db, FX_ENT_ENTRY, **kargs)
        self.index = False # These flags mark the need to reindex and relearn keywords
        self.learn = False
        self.rank = False

        self.feed = ResultFeed()
        self.term = FeedexKwTerm()

        if kargs.get('id') is not None: self.get_by_id(kargs.get('id'))
        elif kargs.get('url') is not None: self.get_by_url(kargs.get('url'))

        # Strings to index in Xapian
        self.ix_strings = {}
        # Strings used for full text ranking
        self.rank_string = ''
        # String to extract features from
        self.learning_string = ''

        # Source link (useful as a feature and independent of db structure)
        self.source_url = None

        self.terms = [] # Keywords extracted by LP

        # Queues for mass inserts
        self.terms_oper_q = []
        self.reindex_oper_q = []
        self.context_ids = [] # This are index ids for operating on learned terms




    def get_by_url(self, url:str):
        url = scast(url, str, -1)
        content = self.DB.qr_sql("select * from entries e where e.link = :url", {'url':url}, one=True )
        if content in (None, (None,), ()):
            self.exists = False
            return msg(FX_ERROR_NOT_FOUND, f"""{_('Entry with url')} %a {_('not found!')}""", url)
        else:
            self.exists = True
            self.populate(content)
            return 0

    def get_by_ix_id(self, id:int):
        id = scast(id, int, -1)
        content = self.DB.qr_sql("select * from entries e where e.ix_id = :id", {'id':id}, one=True )
        if content in (None, (None,), ()):
            self.exists = False
            return msg(FX_ERROR_NOT_FOUND, f"""{_('Entry')} indexed as %a {_('not found!')}""", id)
        else:
            self.exists = True
            self.populate(content)
            return 0




    def set_feed(self, **kargs):
        """ Setup feed for processing """
        if kargs.get('feed') is not None:
            feed = kargs.get('feed')
            if feed[self.feed.get_index('id')] != self.feed['id']: self.feed.populate(feed)
        else:
            if self.feed['id'] != self.vals['feed_id']:
                feed = fdx.load_parent(self.vals['feed_id'])
                if feed != -1: self.feed.populate(feed)



    def clear_q(self, **kargs):
        """ Clear all queues """
        SQLContainerEditable.clear_q(self, **kargs)
        self.terms_oper_q.clear()
        self.reindex_oper_q.clear()
        self.context_ids.clear()








    def open(self, **kargs):
        """ Open in browser """
        if not self.exists: return FX_ERROR_NOT_FOUND

        read = coalesce(self.vals['read'],0)
        link = scast(self.vals.get('link'), str, '').strip()

        if link != '':
            err = fdx.ext_open('browser', self.vals.get('link'), background=kargs.get('background',True))
            if err != 0: return err
            else: msg(_('Opening in browser (%a) ...'), self.vals.get('link', '<UNKNOWN>'))

        else: return msg(FX_ERROR_NOT_FOUND, _('No link found. Aborting...'))

        #now = datetime.now()
        #now_raw = int(now.timestamp())
        #now = now.strftime('%Y-%m-%d %H:%M:%S')
        if coalesce(self.vals['deleted'],0) == 0: err = self.update({'read':read+1}, no_commit=False)
        return err








    def _hook(self, stage, **kargs):


        if stage == FX_ENT_STAGE_PRE_VAL:

            if self.action == FX_ENT_ACT_ADD: 
                self.vals['id'] = None
                self.vals['read'] = coalesce(self.vals.get('read'), self.config.get('default_entry_weight',2))

            if self.vals.get('feed_id') is not None: pass
            elif self.vals.get('feed') is not None: self.vals['feed_id'] = scast(self.vals['feed'], int, -1)
            elif self.vals.get('cat') is not None: self.vals['feed_id'] = fdx.res_cat_name(self.vals['cat'])
            elif self.vals.get('cat_id') is not None: self.vals['feed_id'] = scast(self.vals['cat_id'], int, -1)
            elif self.vals.get('parent_id') is not None: self.vals['feed_id'] = scast(self.vals['parent_id'], int, -1)

            if self.vals.get('flag_id') is not None: self.vals['flag'] = scast(self.vals['flag_id'], int, -1)
            elif self.vals.get('flag') is not None:
                if type(self.vals['flag']) is str: self.vals['flag'] = fdx.res_flag_name(self.vals['flag'])

            return 0



        elif stage == FX_ENT_STAGE_POST_VAL:
            
            feed = fdx.load_parent(self.vals.get('feed_id'))
            if feed == -1: return FX_ERROR_VAL, _('Channel/Category %a not found!'), self.vals['feed_id']
            else: 
                self.feed.populate(feed)
                self.vals['feed_id'] = self.feed['id']            
            
            if self.vals['flag'] not in (0, None):
                if not fdx.is_flag(self.vals['flag']): return FX_ERROR_VAL, _('Flag not found!')

            if self.vals.get('link') is not None and not check_url(self.vals.get('link')):
                return FX_ERROR_VAL, _('Not a valid url! (%a)'), self.vals.get('link', '<???>')

            if self.vals['deleted'] not in (None, 0, 1): return FX_ERROR_VAL, _('Deleted flag must be 0 or 1!')
            if self.vals['note'] not in (None, 0,1): return FX_ERROR_VAL, _('Note marker must be 0 or 1!')
            if coalesce(self.vals['read'],0) < 0: return FX_ERROR_VAL, _('Read marker must be >= 0!')

            self.vals['importance'] = coalesce(self.vals.get('importance'),0)

            if self.vals['pubdate'] is None:
                date = convert_timestamp(self.vals['pubdate_str'])
                if date is None: return FX_ERROR_VAL, _('Invalid published date string (pubdate_str)!')
                else: self.vals['pubdate'] = date

            if self.vals['adddate_str'] is not None:
                date = convert_timestamp(self.vals['adddate_str'])
                if date is None: return FX_ERROR_VAL, _('Invalid adding date string (%a)!'), self.vals['adddate_str']
                else: self.vals['adddate'] = date
            return 0
        


        #####################################################
        #       Adding
        if self.action == FX_ENT_ACT_ADD:



            if stage == FX_ENT_STAGE_INIT_OPER:

                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.vals['id'] = None
                self.vals['adddate_str'] = now
                self.vals['pubdate_str'] = coalesce(self.vals.get('pubdate_str', None), now)
                self.vals['read'] = coalesce(self.vals.get('read'), self.vals['weight'], self.config.get('default_entry_weight',2))
                self.vals['weight'] = None
                self.vals['note'] = coalesce(self.vals['note'],1)
                return 0




            elif stage == FX_ENT_STAGE_PRE_OPER:
                
                self.index, self.learn = True, False

                read = scast(self.vals['read'], int, 0)

                if self.config.get('use_keyword_learning', True): 
                    if read > 0: self.learn = True

                if self.vals.get('flag') not in (None, 0) or self.vals.get('importance') not in (None,0): self.rank = False
                else: self.rank = True

                err = self.ling(index=True, rank=self.rank, learn=self.learn, counter=kargs.get('counter',0))
                if err != 0:
                    self.DB.close_ixer(rollback=True)
                    return err

                self.sd_add('dc', 1)
                if read > 0: self.sd_add(self.vals['feed_id'], read)
                return 0



            elif stage == FX_ENT_STAGE_POST_OPER:

                if self.learn:
                    for t in self.terms: self.terms_oper_q.append(t.copy())
                return 0



        ####################################################
        # Updating
        elif self.action == FX_ENT_ACT_UPD:




            if stage == FX_ENT_STAGE_PRE_OPER:
                
                self.learn, self.index = False, False
        
                for f in self.to_update:
                    if f in REINDEX_LIST:
                        self.index = True
                        break

                read = coalesce(self.vals['read'],0)
                old_read = coalesce(self.backup_vals['read'],0)
                if read != old_read: self.sd_add(self.vals['feed_id'], read - old_read)

                if self.config.get('use_keyword_learning', True):
                    if read > 0:
                        for f in self.to_update:
                            if f in LING_TEXT_LIST:
                                self.learn = True
                                break
                        if old_read <= 0: self.learn = True


                if self.learn or self.index:
                    err = self.ling(index=self.index, rank=False, learn=self.learn)
                    if err != 0:
                        self.restore()
                        self.DB.close_ixer(rollback=True)
                        return err
                return 0






            elif stage == FX_ENT_STAGE_POST_OPER:

                if self.learn:
                    for t in self.terms: self.terms_oper_q.append(t.copy())
                return 0



        #######################################################
        # Deleteing
        elif self.action == FX_ENT_ACT_DEL:

            if stage == FX_ENT_STAGE_POST_OPER:
                self.DB.connect_ixer()
                try: ix_doc = self.DB.ixer_db.get_document(self.vals['ix_id'])
                except (xapian.DocNotFoundError,): ix_doc = None
                if isinstance(ix_doc, xapian.Document):
                    uuid = ix_doc.get_data()
                    try: self.DB.ixer_db.delete_document(f"""UUID {uuid}""")
                    except xapian.DatabaseError as e:
                        self.DB.close_ixer(rollback=True)
                        return msg(FX_ERROR_INDEX, _('Index error: %a'), e)

                self.sd_add('dc', -1)
                self.sd_add(self.vals['feed_id'], -scast(self.vals.get('read'),int, 0))

                return 0



        elif self.action == FX_ENT_ACT_RES:

            if stage == FX_ENT_STAGE_POST_OPER:
                err = self.ling(index=True, rank=False, learn=False)
                if err != 0:
                    self.restore()
                    self.DB.close_ixer(rollback=True)
                    return err

            self.sd_add('dc', 1)
            self.sd_add(self.vals['feed_id'], scast(self.vals.get('read'),int, 0))

            return 0



        elif self.action == FX_ENT_ACT_DEL_PERM:
            
            if stage == FX_ENT_STAGE_POST_OPER:

                self.context_ids.append({'context_id':self.vals['id']})

                im_file = os.path.join(self.DB.img_path, f"""{self.vals['id']}.img""")
                tn_file = os.path.join(self.DB.cache_path, f"""{self.vals['id']}.img""")
                if os.path.isfile(im_file):
                    try: os.remove(im_file)
                    except (OSError, IOError,) as e: msg(FX_ERROR_IO, _('Error removing image %a: %b'), im_file, e)
                if os.path.isfile(tn_file):
                    try: os.remove(tn_file)
                    except (OSError, IOError,) as e: msg(FX_ERROR_IO, _('Error removing thumbnail %a: %b'), tn_file, e)

                return 0


        ##################################################
        #   COMMIT
        if stage == FX_ENT_STAGE_POST_COMMIT:

            err = self.DB.close_ixer()
            if err != 0:
                self.DB.close_ixer(rollback=True)
                return FX_ERROR_INDEX
            else:
                if len(self.reindex_oper_q) > 0:
                    msg(_('Updating indexed stats...'))
                    err = self.DB.run_sql_lock(self.update_sql(filter=REINDEX_LIST_RECALC + ('id',), wheres='id = :id'), self.reindex_oper_q)
                    if err != 0: return err


            if err == 0:

                cid_len = len(self.context_ids)
                if cid_len > 0:
                    
                    if self.action == FX_ENT_ACT_ADD:

                        if cid_len == 1 and self.act_singleton and self.last_id not in (0,None,): # For singleton operation we simply update cached terms with last inserted id
                            cid = self.context_ids[0]
                            for t in self.terms_oper_q:
                                if t == cid: t['context_id'] = self.last_id

                        else: # Here starts a switcharoo by getting newly addded entries by ix_ids and then swapping terms context ids for proper ids
                            id_ixs = self.DB.qr_sql(f'select ix_id, id from entries where e.ix_id in ({ids_cs_string(self.context_ids)})', all=True)
                            for ii in id_ixs:
                                ix_id, id = ii[0], ii[1]
                                for t in self.terms_oper_q:
                                    if t['context_id'] == ix_id: t['context_id'] = id

                    else:

                        msg(_('Removing old keywords...'))
                        err = self.DB.run_sql_lock("delete from terms where context_id = :context_id", self.context_ids)
                        if err != 0: return err
                        debug(8, 'Keywords removed')



                    # ... and save new keyword set to database
                    if len(self.terms_oper_q) > 0:
                        msg(_('Saving learned keywords...'))
                        if fdx.debug_level in (1,4): 
                            for r in self.terms: print(r)
            
                        err = self.DB.run_sql_lock(self.term.insert_sql(all=True), self.terms_oper_q)
                        if err != 0:
                            self.DB.last_term_id = self.DB.lastrowid
                            return err

                        debug(8, 'Keyword terms saved')
            return 0




        if stage == FX_ENT_STAGE_RECACHE:
            
            err = 0
            if self.learn: err = self.DB.load_terms()
            if err  != 0: return err
            return 0

        return 0










    # Messages 
    def _upd_msg(self, field, **kargs):
        if field == 'read' and self.vals.get(field, 0) > 0: 
            return _('Entry %a marked as read'), self.vals['id']
        elif field == 'read' and self.vals.get(field, 0) < 0: 
            return _('Entry %a marked as read'), self.vals['id']
        elif field == 'read' and self.vals.get(field) in (0, None): 
            return _('Entry %a marked as unread'), self.vals['id']
        elif field == 'flag' and self.vals.get(field) in (0,None): 
            return _('Entry %a unflagged'), self.vals['id']
        elif field == 'flag' and self.vals.get(field) not in (0, None):
            return _('Entry %a flagged as %b'), self.vals['id'], fdx.get_flag_name(self.vals.get(field))       
        elif field == 'note' and self.vals.get(field) in (0, None): 
            return _('Entry %a marked as news item'), self.vals['id']
        elif field == 'note' and self.vals.get(field) == 1: 
            return _("""Entry %a marked as a user's note"""), self.vals['id']
        elif field == 'feed_id':
            return _("Entry %a assigned to %b"), self.vals['id'], self.feed.name(with_id=True)
        elif field == 'images':
            return _("Updated image(s) for entry %a"), self.vals['id']
        elif field == 'node_id' and self.vals.get(field) in (0, None): 
            return _('Entry %a unassigned from node')
        elif field == 'node_id' and self.vals.get(field) not in (0, None): 
            return _('Entry %a assigned to entry %b'),self.vals["id"], self.vals['node_id']
        else: return f"""{self.ent_name} %a {_('updated: %b changed to %c')}""", self.vals['id'], self.get_col_name(field), self.vals.get(field,_("<NONE>"))


    def _upd_msg_generic(self, **kargs): return f"""{self.ent_name} %a {_('updated successfully')}""", self.vals['id']
    def _add_msg(self, **kargs): return f"""{self.ent_name} %a {_('added successfully')}""", self.vals['id']
    def _del_msg(self, **kargs): return f"""{self.ent_name} %a {_('deleted successfully')}""", self.vals['id']
    def _del_perm_msg(self, **kargs): return f"""{self.ent_name} %a {_('deleted permanently')}""", self.vals['id']









    ###############################################
    #  Linguistic and indexing processing methods

    def ling(self, **kargs):
        """ Linguistic processing coordinator """

        learn = kargs.get('learn',False)
        stats = kargs.get('stats',True)
        rank = kargs.get('rank',True)
        index = kargs.get('index', stats)
        to_disp = kargs.get('to_disp',False)
        counter = kargs.get('counter',0) # Counter for generating UUIDs
        rebuilding = kargs.get('rebuilding',False) # This tells if we are creating index anew and, if yes, we clear IX_IDs

        # LP lazy load and caching
        self.DB.connect_LP()
        if rank: self.DB.cache_rules()
        if learn: self.DB.cache_terms()

        # Setup language and remember if detection was tried
        if self.action == FX_ENT_ACT_ADD:
            self.vals['lang'] = self.DB.LP.set_model(self.vals['lang'], sample=f"""{self.vals['title']} {self.vals['desc']}  {self.vals['text']} """[:4000])
        elif self.action == FX_ENT_ACT_UPD:
            if scast(self.backup_vals['desc'], str, '').strip() == '' and scast(self.backup_vals['text'], str, '').strip() == '' and self.backup_vals['lang'] == self.vals['lang']:
                self.vals['lang'] = self.DB.LP.set_model(self.DB.LP.detect_lang( sample=f"""{self.vals['title']} {self.vals['desc']}  {self.vals['text']} """[:4000]) )
            

        self.set_feed()


        if index or rank: 
            self.ix_strings, self.rank_string = self.DB.LP.index(self.vals)
            if stats: 
                self.DB.LP.calculate_stats()
                self.merge(self.DB.LP.stats)            
        

        
        
        if rank:
            # Perform ranking based on rules. Construct ranking string for stemmed rules
            if not to_disp:
                self.vals['importance'], self.vals['flag'] = self.DB.LP.rank(self.vals, self.rank_string, to_disp=False)
            else:
                return self.DB.LP.rank(self.vals, self.rank_string, to_disp=True)     
            


            
        if index:
            self.DB.connect_ixer()

            # Remove doc if exists ...
            if rebuilding or self.vals['ix_id'] is None: ix_doc = None
            else:
                try: ix_doc = self.DB.ixer_db.get_document(self.vals['ix_id'])
                except (xapian.DocNotFoundError,): ix_doc = None
                except (xapian.DatabaseError,) as e: return msg(FX_ERROR_INDEX, _('Index error: %a'), e)

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



            self.DB.ixer.set_document(ix_doc)

            # Add UUID
            ix_doc.add_boolean_term(f"""UUID {uuid}""")
            # Add feed tag for easier deletes later on
            ix_doc.add_boolean_term(f'FEED_ID {self.vals["feed_id"]}')
            if scast(self.vals["note"], int, 0) >= 1: ix_doc.add_boolean_term(f"""NOTE 1""")
            else: ix_doc.add_boolean_term(f"""NOTE 0""")
            if scast(self.vals["read"], int, 0) >= 1: ix_doc.add_boolean_term(f"""READ 1""")
            else: ix_doc.add_boolean_term(f"""READ 0""")

            ix_doc.add_value(0, xapian.sortable_serialise(scast(self.vals['pubdate'], int, 0)) )
            ix_doc.add_value(1, xapian.sortable_serialise(scast(self.vals['adddate'], int, 0)) )
            ix_doc.add_value(2, xapian.sortable_serialise(scast(self.vals['flag'], int, 0)) )

            # Index token strings, restarting term position after each one to facilitate mixed searches ...
            for k in ('',PREFIXES['exact'],):
                self.DB.ixer.set_termpos(0)
                for f in self.ix_strings[k]: self.DB.ixer.index_text( scast(f[1], str, ''), scast(f[0], int, 1), k)
            last_pos = self.DB.ixer.get_termpos() + 100
                
            # Add semantic postings one by one not to spam ...
            for f in self.ix_strings[PREFIXES['sem']]:
                sems = f[1]
                weight = scast(f[0], int, 1)
                for s,ps in sems.items():
                    for p in ps:
                        ix_doc.add_posting(f"""{PREFIXES['sem']}{s.lower()}""", p, weight)
    
            # Index meta fields
            self.DB.ixer.set_termpos(last_pos)
            for k in META_PREFIXES:
                for f in self.ix_strings[k]: self.DB.ixer.index_text( scast(f[1], str, ''), scast(f[0], int, 1), k)
            self.DB.ixer.set_termpos(last_pos)
            for k in META_PREFIXES_EXACT:
                for f in self.ix_strings[k]: self.DB.ixer.index_text( scast(f[1], str, ''), scast(f[0], int, 1), k)

            # Save stemming variants
            for k,v in self.DB.LP.variants.items():
                for s in v: self.DB.ixer_db.add_synonym(k,s)

            # Add/Replace in Database
            if exists:
                try: self.vals['ix_id'] = self.DB.ixer_db.replace_document(f'UUID {uuid}', ix_doc)
                except (xapian.DatabaseError, xapian.DocNotFoundError,) as e: 
                    return msg(FX_ERROR_INDEX, _('Index error: %a'), e)
                debug(2, f'Replaced Xapian doc {uuid}: {self.vals["ix_id"]}')
            else:            
                try: self.vals['ix_id'] = self.DB.ixer_db.add_document(ix_doc)
                except (xapian.DatabaseError,) as e: 
                    return msg(FX_ERROR_INDEX, _('Index error: %a'), e)
                debug(2, f"""Added Xapian doc {uuid}: {self.vals['ix_id']}""")

            self.DB.lastxapdocid = self.vals['ix_id']

            if self.action in (FX_ENT_ACT_UPD, FX_ENT_ACT_RES, FX_ENT_ACT_REINDEX,):
                self.reindex_oper_q.append(self.filter_cast(self.vals, REINDEX_LIST_RECALC + ('id',)))




        if learn:
            # Learn text features by creating a learning string and running smallsem on it...
            self.learning_string = ''
            for f in LING_TEXT_LIST: self.learning_string = f"""{self.learning_string}  {scast(self.vals[f], str, '')}"""
            depth = kargs.get('learning_depth', MAX_FEATURES_PER_ENTRY)
            terms_tmp = self.DB.LP.extract_features(self.learning_string, depth=depth)


            model = self.DB.LP.get_model()

            self.terms.clear()
            if self.action in (FX_ENT_ACT_ADD,):
                context_id = self.vals['ix_id']
                self.context_ids.append(context_id)
            else:
                context_id = self.vals['id']
                self.context_ids.append({'context_id':context_id})

            for r in terms_tmp:
                self.term.clear()
                self.term['term'] = scast(r[2], str, '')
                self.term['weight'] = scast(r[1], float, 0) #* self.vals['weight']
                self.term['model'] = model
                self.term['form'] = scast(r[0], str, '')
                self.term['context_id'] = context_id

                self.terms.append(self.term.vals.copy())
        
        return 0








    def reindex(self, **kargs):
        """ Reindex this entry """
        if not self.exists: return FX_ERROR_NOT_FOUND
        self.action = FX_ENT_ACT_REINDEX
        no_commit = kargs.get('no_commit', False)

        msg(_('Reindexing %a...'), self.vals['id'])
        self.index = True
        err = self.ling(index=self.index, rank=False, learn=False)
        if err != 0: 
            self.DB.close_ixer(rollback=True)
            return err

        if no_commit: return 0
        err = self.commit()
        if err != 0: return err
        return msg(_('Entry %a reindexed'), self.vals['id'])


    def rerank(self, **kargs):
        """ Rerank this entry against rules """
        if not self.exists: return FX_ERROR_NOT_FOUND
        self.action = FX_ENT_ACT_RERANK
        no_commit = kargs.get('no_commit', False)

        msg(_('Ranking %a...'), self.vals['id'])
        self.rank = True
        err = self.ling(index=False, rank=True, learn=False)
        if err != 0: return err
        if self.sql_str is None: self.sql_str = 'update entries set importance = :importance, flag = :flag where id = :id'
        self.oper_q.append({'importance':self.vals['importance'], 'flag':self.vals['flag'], 'id':self.vals['id']})

        if no_commit: return 0
        err = self.commit()
        if err != 0: return err
        return msg(_('Entry %a reranked'), self.vals['id'])


    def relearn(self, **kargs):
        """ Relearn keywords for this entry """
        if not self.exists: return FX_ERROR_NOT_FOUND
        if coalesce(self.vals['read'], 0) == 0: return 0
        self.action = FX_ENT_ACT_RELEARN
        no_commit = kargs.get('no_commit', False)

        msg(_('Relearning %a...'), self.vals['id'])
        self.learn = True
        err = self.ling(index=False, rank=False, learn=self.learn)
        if err != 0: return err
        for t in self.terms: self.terms_oper_q.append(t.copy())

        if no_commit: return 0
        err = self.commit()
        if err != 0: return err
        return msg(_('Keywords relearned for entry %a'), self.vals['id'])






    def summarize(self, level, **kargs):
        """ Summarize this entry """
        self.DB.connect_LP()
        self.DB.LP.summarize_entry(self.vals, level, **kargs)







    def __str__(self):
        ostring = SQLContainerEditable.__str__(self)
        terms = []
        try: ix_doc = self.DB.ix.get_document(self.vals['ix_id'])
        except (xapian.DatabaseError, xapian.DocNotFoundError) as e: ix_doc = None
        if isinstance(ix_doc, xapian.Document):
            for t in ix_doc.termlist(): terms.append(t.term.decode('utf-8')) 
        term_str = ''
        for t in terms: term_str = f"""{term_str}{t} """
        ostring = f"""{ostring}
-----------------------------------------------------------------------------------------------------------
{term_str}
"""
        return ostring
    


