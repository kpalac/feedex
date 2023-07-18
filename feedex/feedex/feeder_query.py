# -*- coding: utf-8 -*-
""" Query Parser for Feedex"""

from feedex_headers import *



class FeedexQueryInterface:
    """ A query interface """
    def __init__(self) -> None:
        self.result = None # Result template to unpack the list
        self.results = [] # Result list
        self.result_no = 0 
        self.result_no2 = 0 # Sometimes two result numbers are needed
        self.result_max = 0 # Max value is needed for plots

    def clear(self):
        """ Clear interface """
        self.result.clear()
        self.results.clear()
        self.result_no = 0
        self.result_no2 = 0
        self.result_max = 0

    def _empty(self, **kargs):
        """ Clears results and result numbers """
        self.result = kargs.get('result')
        self.results = ()
        self.result_no = 0
        self.result_no2 = 0
        self.result_max = 0





class FeedexQuery(FeedexQueryInterface):
    """ Class for query parsing, searching and rule matching for Feedex """

    def __init__(self, db, **kargs):
        
        FeedexQueryInterface.__init__(self)

        # Setup parent classes and lazy load caches
        self.DB = db
        self.DB.connect_LP()
        self.DB.cache_feeds()
        self.DB.cache_flags()
        self.DB.cache_history()
        self.LP = self.DB.LP

        # Config
        self.config = kargs.get('config', self.DB.config)


        # Query parser for Xapian
        self.ix_qp = xapian.QueryParser()
        # Init and map needed prefixes
        for p in META_PREFIXES + META_PREFIXES_EXACT + SEM_PREFIXES + (PREFIXES['exact'],): self.ix_qp.add_prefix(p,p)
        # And add range processors
        self.ix_qp.add_rangeprocessor(xapian.NumberRangeProcessor(0, 'XPUB', xapian.RP_SUFFIX))
        self.ix_qp.add_rangeprocessor(xapian.NumberRangeProcessor(1, 'XADD', xapian.RP_SUFFIX))
        self.ix_qp.add_rangeprocessor(xapian.NumberRangeProcessor(2, 'XFLG', xapian.RP_SUFFIX))
        for p in BOOLEAN_PREFIXES: self.ix_qp.add_boolean_prefix(p.strip(),p)

        self.ix_results = {}
        self.ix_results_ids = []

        # Processed search phrase
        self.phrase = {}

        # Interface for managing history items
        self.history_item = FeedexHistoryItem(self.DB)

        # Container for query results
        self.result = ResultEntry()

        self.snippets_lst = [] # Snippet lists for query results (string search)

        # Regex string for tokenizing query
        self.REGEX_xap_query = re.compile('''(OR|AND|NOT|XOR|NEAR\d+|~\d+|~|NEAR|<\w+>|[\\\(]|[\\\)]|\(|\)|\"|\'|\w+|\d+|[^\s]+)''')








######################################################################
#   
#       BASIC QUERY
#




    def query(self, string:str, filters:dict, **kargs):
        """ Main Query method
            Queries database with search string. """

        ret = self._validate_filters(string, filters)
        if type(ret) is not tuple:
            self._empty(result=ResultEntry())
            return FX_ERROR_QUERY
        else: filters, qtype, rev, sort, case_ins = ret



        rank =  kargs.get('rank',True)
        cnt = kargs.get('cnt',False)
        snippets = kargs.get('snippets',True)
        
        max_context_length = self.config.get('max_context_length', 500)

        # Construct phrase if needed
        if kargs.get('phrase') is None:
            if qtype == 0:      self.phrase = self.parse_query(string, case_ins=case_ins, field=filters.get('field'), sql=True, str_match=True)
            elif qtype == 1:    self.phrase = self.parse_query(string, case_ins=case_ins, field=filters.get('field'), sql=False, fts=True)
        
        else: self.phrase = kargs.get('phrase',{})

        # Some queries do not work with wildcards
        if kargs.get('no_wildcards',False) and self.phrase.get('has_wc',False):
            self._empty(result=ResultEntry())
            return msg(FX_ERROR_QUERY, _('Wildcards are not allowed with this type of query!'))



        self.result = ResultEntry()
        self.results = []

        # Query index if needed
        if qtype == 1 and not self.phrase['empty']:
            
            ret = self._build_xapian_qr(self.phrase, filters)
            if type(ret) is not tuple: 
                self._empty(result=ResultEntry())
                return -5
            else: ix_qr, enquire = ret


            ix_matches = enquire.get_mset( filters['start_n'],  filters['page_len'] )

            self.ix_results.clear()
            self.ix_results_ids.clear()
            
            for ixm in ix_matches:
                self.ix_results_ids.append(ixm.docid)
                
                if cnt or rank:
                    snips = []
                    if snippets:
                        for t in enquire.matching_terms(ixm):
                            t = t.decode("utf-8")
                            if len(t) >=2 and t[1] == PREFIXES['exact']: snips.append(t[2:])
                            elif len(t) > 1 and t[0] == PREFIXES['exact']: snips.append(t[1:])
                            elif t.startswith(PREFIXES['sem']): continue
                            else:
                                if t[0] in META_PREFIXES: t = t[1:]
                                for v in self.DB.ix.synonyms(t): snips.append(v.decode("utf-8"))
                    count = ixm.rank
                else: 
                    count = None
                    snips = ()

                self.ix_results[ixm.docid] = (ixm.weight, ixm.rank, count, snips)



            if len(self.ix_results_ids) == 0:
                self._empty(result=ResultEntry())
                return 0

            filters['IX_ID_list'] = self.ix_results_ids.copy() # This list will be appended to SQL query to extract Xapian results






        # Query SQL database
        (query, vals) = self._build_sql(self.phrase, filters)
        results_tmp = self.DB.qr_sql(query, vals, all=True)
        if self.DB.status != 0: 
            self._empty(result=ResultEntry())
            return FX_ERROR_QUERY
        
        debug(5, "Results: ", len(results_tmp))



        # Merge Xapian stats with SQL results
        ranked = False #Are results ranked?
        if qtype ==  1 and not self.phrase['empty']:
            ranked = True
            for r in results_tmp:
                self.result.populate(r)

                # Append Xapian ranking to SQL results                
                if rank: self.result['rank'] = self.ix_results[self.result['ix_id']][0]
                if cnt: self.result['count'] = self.ix_results[self.result['ix_id']][0]

                if snippets:  # ... and try to extract snippets 
                    
                    if filters.get('field') is not None: field_lst = (filters.get('field'),)
                    else: field_lst = LING_TEXT_LIST
                        
                    snips = []
                    vars = self.ix_results[self.result['ix_id']][3].copy()
                        
                    for f in field_lst:
                        f = self.result[f]
                        if type(f) is not str: continue
                        lf = f.lower()
                        for v in vars:
                            (c, sn) = self.LP.str_matcher((v,), 1, False, False, lf, snippets=snippets, orig_field=f)
                            if snippets:
                                for s in sn:
                                    if len(s) == 3 and (len(s[1]) <= max_context_length or max_context_length == 0): # check this to avoid showing long matches
                                        snips.append(tuple(s))


                    self.result['snippets'] = tuple(snips)

                self.results.append(self.result.tuplify(all=True))


        # Rank string matching results (if needed)
        # For this we will use last returned column and then replace it with ranking - a little crude, but works
        # Pure SQL has its limitations and we need something beyond boolean matching
        elif qtype == 0 and not self.phrase['empty']:
            ranked = True
            # No point doing this if no string was given or there was only one result
            matched_docs_count = len(results_tmp)
            if rank and matched_docs_count > 0:
                doc_count = kargs.get('doc_count', self.DB.get_doc_count())
                idf = log10(doc_count/matched_docs_count)

            # Calculate ranking for each result
            for r in results_tmp:

                self.result.populate(r)

                if snippets: 
                    snips = []
                    sn = []
                if rank or cnt:
                    if filters.get('field') is not None: field_lst = (filters.get('field'),)
                    else: field_lst = LING_TEXT_LIST

                    count = 0
                    for f in field_lst:
                        f = self.result[f]
                        if type(f) is not str: continue
                        if case_ins: lf = f.lower()
                        else: lf = f
                        (c, sn) = self.LP.str_matcher(self.phrase['spl_string'], self.phrase['spl_string_len'], self.phrase['beg'], self.phrase['end'], lf, snippets=snippets, orig_field=f)
                        count += c
                        if snippets: 
                            for s in sn:
                                if len(s) == 3 and (len(s[1]) <= max_context_length or max_context_length == 0): # check this to avoid showing long wildcard matches        
                                    snips.append(s)
                            

                if snippets: self.result['snippets'] = tuple(snips)

                # Append TF-IDF rank or match count - depending on what option was chosen
                if rank: # Construct TF-IDF
                    doc_len = scast(self.result["word_count"], int, 1)
                    if doc_len == 0: rnk = 0
                    else:
                        tf = count/doc_len
                        # Final ranking measure - modify at your fancy
                        rnk = tf * idf
                    # append...
                    self.result['rank'] = rnk
                    self.result['count'] = count

                if cnt:
                    # Append count if it was specified...
                    self.result['count'] = count

                self.results.append(self.result.tuplify(all=True))

        else: self.results = results_tmp


        # Sort results by rank or count if no other sorting method was chosen
        if (not sort) and ranked:
            if cnt: self.results.sort(key=lambda x: x[self.result.get_index('count')], reverse=True)
            elif rank: self.results.sort(key=lambda x: x[self.result.get_index('rank')], reverse=True)

        # Add technical info ...
        self.result_no = len(self.results)
        self.result_no2 = 0

        # Save phrase to history        
        if not kargs.get('no_history',False):
            err = self.history_item.add(self.phrase, filters.get('feed'))
            if err != 0: msg(*err)
        
        # Group results, if needed
        if kargs.get('allow_group',False):
            if filters.get('group') is not None:
                self.result_no2 = self.result_no
                self.group_results(**filters)
                self.result_no = len(self.results)
            elif filters.get('depth') is not None:
                self.result_no2 = self.result_no
                self.results = self.results[:filters['depth']]
                self.result_no = len(self.results)


        if rev: self.results.reverse()
        self.results = tuple(self.results)

        return 0








 




####################################################################################################3
#
#       COMPOSITE QUERIES
#

    def get_trends(self, qr, filters, **kargs):
        """ Extract trends from group of entries (can get time consuming) """
        rev = kargs.get('rev', filters.get('rev',False))
        filters['rev'] = False

        qr = scast(qr, str, '')
        flang = filters.get('lang')

        self.query(qr, filters, rank=False, cnt=False, snippets=False, no_history=True, allow_group=False)
        
        self.results = list(self.results)
        self.results.sort(key=lambda x: x[self.result.get_index('lang')]) # Sort results by language to minimize language model reloading

        keywords = {}
        for r in self.results:
            lang = r[self.result.get_index('lang')]
            self.LP.set_model(lang)
            if flang is not None:
                if self.LP.get_model() != flang: continue

            raw_text = ''
            for f in LING_TEXT_LIST:
                raw_text = f"""{raw_text}
{scast(r[self.result.get_index(f)], str, '')}"""

            kwds = self.LP.extract_features(raw_text, MAX_FEATURES_PER_ENTRY)
            for kw in kwds:
                weight = keywords.get(kw[0],(0,0))[0]
                keywords[kw[0]] = (weight + kw[1], kw[2])

        self.result = ResultTerm()
        self.results = []
        for k,v in keywords.items(): self.results.append( (k, round(v[0],3), v[1]) )
        
        self.results.sort(key=lambda x: x[1], reverse=True)

        if rev: self.results.reverse()
        self.results = tuple(self.results)

        self.result_no = len(self.results)
        self.result_no2 = 0

        return 0




    def get_trending(self, qr, filters, **kargs):
        """ Get trending articles from given filters"""
        rev = kargs.get('rev', filters.get('rev',False))
        filters['rev'] = False

        depth = filters.get('depth',100)

        self.get_trends(qr, filters, no_history=True, allow_group=False)

        qr_string = ''
        for i,r in enumerate(self.results):
            if i >= depth: break
            s = str(r[2]).strip()
            if ' ' is s: s = f"""({s.replace(' ','~3')})"""
            qr_string = f"""{qr_string} OR {r[0].lower()}"""
        if qr_string.startswith(' OR '): qr_string = qr_string[4:]
        
        filters['qtype'] = 1
        filters['rev'] = rev
        err = self.query(qr_string, filters, rank=True, cnt=True, snippets=False, no_history=True, no_wildcards=True, allow_group=kargs.get('allow_group',True))
        return err





    def find_similar(self, id, **kargs):
        """ Find entry similar to specified by ID based on extracted features """
        id = scast(id, int, 0)
        self.result = ResultEntry()
        entry = FeedexEntry(self.DB, id=id)
        rule = SQLContainer('rules', RULES_SQL_TABLE)
        if not entry.exists:
            self._empty(result=ResultEntry())
            return -7

        depth = kargs.get('depth',self.config.get('default_similarity_limit',30)) # Limit results

        # Get or generate rules
        if self.config.get('use_keyword_learning', True): 
            rules = self.DB.qr_sql("select * from rules where context_id=:id order by weight desc", {'id':id} , all=True)
            if self.DB.status != 0: 
                self._empty(result=ResultEntry())
                return -2
        else: rules = None

        if rules in (None, [], [None], (), (None,)):
            if self.config.get('default_similar_weight', 2) > 0 and not kargs.get('no_weight',False):
                err = entry.ling(index=False, rank=False, learn=True, save_rules=True)
            else:
                err = entry.ling(index=False, rank=False, learn=True, save_rules=False)
            if err != 0: 
                self._empty(result=ResultEntry())
                return -2
            rules = entry.rules.copy()

        if rules in (None, [], [None], ()):
            debug(5, "Nothing to find...")
            self._empty(result=ResultEntry())
            return 0

        # Update entry as read (if so configured)
        if self.config.get('default_similar_weight', 2) > 0 and not kargs.get('no_weight',False):
            self.DB.run_sql_lock(f"update entries set read = coalesce(read,0) + {self.config.get('default_similar_weight', 2)}  where id = :id", {'id':id} )

        # Search for keywords in entries ...
        filters = kargs.copy()
        filters['lang'] = entry.get('lang','heuristic')
        filters['case_ins'] = True
        filters['qtype'] = 1
        filters['page'] = 1
        filters['page_len'] = depth
        filters['exclude_id'] = id
        doc_cnt = self.DB.get_doc_count()

        # ... and to do this construct a single query string from rules
        qr_string = ''
        for i,r in enumerate(rules):
            if i >= depth: break
            
            if type(r) in (list, tuple): rule.populate(r)
            elif type(r) is dict:
                rule.clear()
                rule.merge(r)
            else: continue

            s = str(rule['string']).strip()
            if ' ' in s: s = f"""({s.replace(' ',' ~3 ')})"""
            qr_string =f"""{qr_string} OR {s}"""
        if qr_string.startswith(' OR '): qr_string = qr_string[4:]

        # Execute final query using combined long composite phrase
        err = self.query(qr_string, filters, rank=True, cnt=True, doc_count=doc_cnt, snippets=False, no_history=True, no_wildcards=True, allow_group=kargs.get('allow_group',True))
        return err







    def _build_time_series(self, group, rev, do_rank, **kargs):
        """ Converts frequency dictionary to time series """
        result = ResultEntry()

        # Count results by specific date keys
        freq_dict = {}
        for r in self.results:
            result.clear()
            result.populate(r)
            if do_rank: rnk = scast(result['rank'], float, 0)
            else: rnk = scast(result['count'], int, 0)
            dtetime = scast(result['pubdate'], int, 0)

            if group == 'hourly':
                hour = time.strftime('%Y-%m-%d %H', time.localtime(dtetime)) + ":00:00"
                freq_dict[hour] = freq_dict.get(hour,0) + rnk

            elif group == 'daily':
                day = time.strftime('%Y-%m-%d', time.localtime(dtetime)) + " 00:00:00"
                freq_dict[day] = freq_dict.get(day,0) + rnk
                    
            elif group == 'monthly':
                month = time.strftime('%Y-%m', time.localtime(dtetime)) + "-01 00:00:00"
                freq_dict[month] = freq_dict.get(month,0) + rnk                    


        # Construct time series from frequency dictionary
        data_points = []
        mx = 0
        for f in freq_dict.keys():
            freq = freq_dict.get(f,0)
            if freq > mx: mx = freq
            data_points.append([f, round(freq, 3)])

        data_points.sort(key=lambda x: x[0], reverse=False)

        date_start = data_points[0][0]
        date_end = data_points[-1][0]

        time_series = []
        ts = date_start

        mon_rel = relativedelta(months=1)
        day_rel = relativedelta(days=1)
        
        if group == "hourly": 
            ts_from = datetime.strptime(date_start, "%Y-%m-%d %H:%M:%S")
            ts_to = ts_from + timedelta(hours=1) - timedelta(seconds=1)
            ts_from = ts_from.strftime("%Y-%m-%d %H:%M:%S")
            ts_to = ts_to.strftime("%Y-%m-%d %H:%M:%S")
            time_series.append([date_start[:-3], ts_from, ts_to, freq_dict[date_start]])
        
        elif group == "daily": 
            ts_from = datetime.strptime(date_start, "%Y-%m-%d %H:%M:%S")
            ts_to = ts_from + day_rel - timedelta(seconds=1)
            ts_from = ts_from.strftime("%Y-%m-%d %H:%M:%S")
            ts_to = ts_to.strftime("%Y-%m-%d %H:%M:%S")
            time_series.append([date_start[:-9], ts_from, ts_to, freq_dict[date_start]])
        
        elif group == "monthly": 
            ts_from = datetime.strptime(date_start, "%Y-%m-%d %H:%M:%S")
            ts_to = ts_from + mon_rel - timedelta(seconds=1)
            ts_from = ts_from.strftime("%Y-%m-%d %H:%M:%S")
            ts_to = ts_to.strftime("%Y-%m-%d %H:%M:%S")
            time_series.append([date_start[:-12], ts_from, ts_to, freq_dict[date_start]])

        # Populate every step on date, even if there were 0 occurences
        while ts != date_end:
            tst = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            if group == "hourly":
                tst += timedelta(hours=1)
                ts_disp = tst.strftime("%Y-%m-%d %H:%M")
                ts_from = tst.strftime("%Y-%m-%d %H:%M:%S")
                ts_to = tst + timedelta(hours=1) - timedelta(seconds=1)
                ts_to = ts_to.strftime("%Y-%m-%d %H:%M:%S")
            elif group == "daily":
                tst += day_rel
                ts_disp = tst.strftime("%Y-%m-%d")
                ts_from = tst.strftime("%Y-%m-%d %H:%M:%S")
                ts_to = tst + day_rel - timedelta(seconds=1)
                ts_to = ts_to.strftime("%Y-%m-%d %H:%M:%S")
            elif group == "monthly":
                tst += mon_rel
                ts_disp = tst.strftime("%Y-%m")
                ts_from = tst.strftime("%Y-%m-%d %H:%M:%S")
                ts_to = tst + mon_rel - timedelta(seconds=1)
                ts_to = ts_to.strftime("%Y-%m-%d %H:%M:%S")

            ts = tst.strftime("%Y-%m-%d %H:%M:%S")
            fr = freq_dict.get(ts,0)
            time_series.append( (ts_disp, ts_from, ts_to, fr,) )

        time_series.sort(key=lambda x: x[0], reverse=True)

        self.results = time_series.copy()
        
        if rev: self.results.reverse()
        self.results = tuple(self.results)

        self.result = ResultTimeSeries()
        self.result_no = len(self.results)
        self.result_max = mx
 
        return 0
 




    def relevance_in_time(self, id, **kargs):
        """ Gets keywords from entry and produces time series for them """
        id = scast(id, int, 0)

        # Get similar items
        filters = kargs.copy()
        filters['depth'] = 500
        filters['allow_group'] = False
        
        self.find_similar(id, **filters)
        
        if len(self.results) == 0:
            self._empty(result=ResultTimeSeries())
            return 0
        else: self.result_no2 = len(self.results)

        group = kargs.get('group','daily')
        rev = kargs.get('rev',False)  # Reverse sort order

        self._build_time_series(group, rev, True)
        return 0
 
                








    def term_context(self, string:str, **kargs):
        """ Get term's context (find entries and print immediate surroundings) """
        string = scast(string, str, '')
        if string == '': 
            self._empty(result=ResultContext())
            return 0
        
        rev = kargs.get('rev',False)
        kargs['rev'] = False
        self.query(string, kargs, count=False, rank=True, snippets=True, allow_group=False)

        self.result_no2 = len(self.results)

        self.result = ResultContext()
        result = ResultEntry()
        results_tmp = []
        # Build context list around extracted snippets - for multiple snippets in one document, results are duplicated
        for r in self.results:
            result.populate(r) 
            for s in result['snippets']:
                self.result.clear()
                self.result.merge(result.vals)
                self.result['snippets'] = None
                self.result['context'] = (s,)
                results_tmp.append(self.result.tuplify())

        self.results = results_tmp.copy()
        
        if rev: self.results.reverse()
        self.results = tuple(self.results)

        self.result_no = len(self.results)
        return 0












    def term_net(self, term:str, **kargs):
        """ Show terms/features connected to a given term by analising contexts """
        # Check for empty term
        result = ResultEntry()
        term = scast(term, str, '').strip()
        if term == '':
            self._empty(result=ResultTerm())
            return 0

        doc_count = kargs.get('doc_count', self.DB.get_doc_count())

        # Query for containing docs
        rev = kargs.get('rev',False)
        kargs['rev'] = False
        self.query(term, kargs, rank=True, cnt=True, doc_count=doc_count, snippets=False, no_history=True, no_wildcards=True, allow_group=False)
        self.result_no2 = len(self.results)

        kwd_list = []
        # Generate keywords for fist N best matches
        for i,r in enumerate(self.results):
            if i > TERM_NET_DEPTH: break

            result.populate(r)
            self.LP.set_model(result['lang'], sample=f"""{result['title']} {result['desc']}"""[:1000])          

            learning_string = ''
            for f in LING_TEXT_LIST: learning_string = f"""{learning_string}  {scast(self.result[f], str, '')}"""

            # ... and collect them to result list
            kwds = self.LP.extract_features(learning_string, depth=MAX_FEATURES_PER_ENTRY)
            for kw in kwds: kwd_list.append( (kw[0],kw[1]) )

        # Consolidate results
        freq_dist = {}
        for kw in kwd_list: freq_dist[kw[0]] = freq_dist.get(kw[0],0) + kw[1] 

        self.results = []
        for k,v in freq_dist.items(): self.results.append( (k,v) )

        self.results.sort(key=lambda x: x[1], reverse=True)

        if rev: self.results.reverse()
        self.results = tuple(self.results)

        self.result = ResultTerm()
        self.result_no = len(self.results)

        # Save term to history        
        if not kargs.get('no_history',False):
            err = self.history_item.add(self.phrase, None)
            if err != 0: msg(*err) 
        return 0       







    def term_in_time(self, term:str, **kargs):
        """ Get term frequency in time and output as a table of data points or a plot in terminal """
        term = scast(term, str, '')
        if term == '':
            self._empty(result=ResultTimeSeries())
            return 0

        group = kargs.get('group','daily')
        rev = kargs.get('rev', False)
        kargs['rev'] = False
        self.query(term, kargs, rank=False, cnt=True, snippets=False, allow_group=False)

        if len(self.results) == 0:
            self._empty(result=ResultTimeSeries())
            return 0
        else: self.result_no2 = len(self.results)

        self._build_time_series(group, rev, False)
        return 0






    def group_results(self, **kargs):
        """ Creates and prints a tree with results grouped by a column """
        group_by = kargs.get('group','category')
        depth = kargs.get('depth',self.config.get('default_depth',5))

        results_tmp = []
        node_tmp = []
        count = 0


        if group_by in ('category','feed'):
            feed = ResultFeed()
            feeds = fdx.feeds_cache.copy()
            feeds.sort(key=lambda x: coalesce(x[feed.get_index('display_order')],0), reverse=False)



        if group_by == 'category':
            parent_id_ix = self.result.get_index('parent_id')
            for f in feeds:
                if coalesce(f[feed.get_index('is_category')],0) == 1:
                    node_tmp = []
                    count = 0
                    feed.populate(f)
                    for r in self.results:
                        if r[parent_id_ix] == feed['id']:
                            count += 1
                            node_tmp.append(list(r))
                            if count >= depth: break

                    if count > 0:
                        self.result.clear()
                        self.result['title'] = f'{fdx.get_feed_name(feed["id"], with_id=False)}'
                        self.result['desc'] = f[feed.get_index('subtitle')]
                        self.result['feed_id'] = f[feed.get_index('id')]
                        self.result['is_node'] = 1
                        self.result['children_no'] = count
                        results_tmp.append(self.result.listify())
                        results_tmp = results_tmp + node_tmp

        elif group_by == 'feed':
            feed_id_ix = self.result.get_index('feed_id')            
            for f in feeds:
                if coalesce(f[feed.get_index('is_category')],0) != 1:
                    node_tmp = []
                    count = 0
                    feed.populate(f)
                    for r in self.results:
                        if r[feed_id_ix] == feed['id']:
                            count += 1
                            node_tmp.append(list(r))
                            if count >= depth: break

                    if count > 0:
                        self.result.clear()
                        self.result['title'] = f'{fdx.get_feed_name(feed["id"], with_id=False)}'
                        self.result['desc'] = f[feed.get_index('subtitle')]
                        self.result['feed_id'] = f[feed.get_index('id')]
                        self.result['is_node'] = 1
                        self.result['children_no'] = count
                        results_tmp.append(self.result.listify())
                        results_tmp = results_tmp + node_tmp

        elif group_by == 'flag':
            flag_ix = self.result.get_index('flag')
            for f in fdx.flags_cache.keys():
                node_tmp = []
                count = 0
                for r in self.results:
                    if r[flag_ix] == f:
                        count += 1
                        node_tmp.append(list(r))
                        if count >= depth: break

                if count > 0:
                    self.result.clear()
                    self.result['title'] = f'{fdx.get_flag_name(f)}'
                    self.result['desc'] = f'{fdx.get_flag_desc(f)}'
                    self.result['flag'] = f
                    self.result['is_node'] = 1
                    self.result['children_no'] = count
                    results_tmp.append(self.result.listify())
                    results_tmp = results_tmp + node_tmp





        elif group_by == 'similar':

            tmp_result = ResultEntry()
            matched_ids = []
            ungrouped_tmp = self.results.copy()

            id_ix = self.result.get_index('id')

            filters = kargs.copy()
            filters['no_weight'] = True
            filters['group'] = None
            filters['allow_group'] = False
            filters['rank'] = True
            filters['cnt'] = True
            filters['snippets'] = False
            filters['config'] = None
            filters['rev'] = False
            filters['sort'] = None
            filters['fallback_sort'] = 'id'
            filters['depth'] = int(len(self.results) / depth)

            node_count = 0

            for r in ungrouped_tmp:
                if node_count > depth: break
                if r[id_ix] not in matched_ids:
                    count = 0
                    node_tmp = []
                    tmp_result.clear()
                    tmp_result.populate(r)
                    tmp_result['is_node'] = 1
                    node_count += 1
                    self.find_similar(r[id_ix], **filters)
                    for t in self.results:
                        if t[id_ix] not in matched_ids and r[id_ix] != t[id_ix]: 
                            count += 1
                            matched_ids.append(t[id_ix])
                            if count >= depth: break
                            node_tmp.append(list(t))

                    tmp_result['children_no'] = count
                    results_tmp.append(tmp_result.listify())
                    results_tmp = results_tmp + node_tmp
                




        elif group_by in ('hourly', 'daily', 'monthly'):

            pubdate_ix = self.result.get_index('pubdate')
            timetable = []
            tt_added = []

            dmonth = relativedelta(months=+1)
            dday = relativedelta(days=+1)
            dhour = relativedelta(hours=+1)
            dsecond_minus = relativedelta(seconds=-1)

            for r in self.results:

                dtetime = scast(r[pubdate_ix], int, 0)

                if group_by == 'hourly':
                    hour = f"{time.strftime('%Y-%m-%d %H', time.localtime(dtetime))}:00"
                    if hour in tt_added: continue
                    beg = datetime.strptime(hour, "%Y-%m-%d %H:%M")
                    end = beg + dhour + dsecond_minus
                    timetable.append( (beg.timestamp(), end.timestamp(), hour) )
                    tt_added.append(hour)

                elif group_by == 'daily':
                    day_disp = time.strftime('%Y-%m-%d', time.localtime(dtetime))
                    day =  f"{day_disp} 00:00:00"
                    if day in tt_added: continue
                    beg = datetime.strptime(day, "%Y-%m-%d %H:%M:%S")
                    end = beg + dday + dsecond_minus
                    timetable.append( (beg.timestamp(), end.timestamp(), day_disp) )
                    tt_added.append(day)

                elif group_by == 'monthly':
                    month_disp = time.strftime('%Y-%m', time.localtime(dtetime))
                    month = f"{month_disp}-01 00:00:00"
                    if month in tt_added: continue
                    beg = datetime.strptime(month, "%Y-%m-%d %H:%M:%S")
                    end = beg + dmonth + dsecond_minus
                    timetable.append( (beg.timestamp(), end.timestamp(), month_disp) )
                    tt_added.append(month)

            timetable.sort(key=lambda x: x[2], reverse=True)

            for t in timetable:
                node_tmp = []
                count = 0
                
                beg = t[0]
                end = t[1]
                ts = t[2]

                for r in self.results:
                    pubdate = scast(r[pubdate_ix], int, 0)
                    if pubdate >= beg and pubdate <= end:
                        count += 1
                        node_tmp.append(list(r))
                        if count >= depth: break
                    
                if count > 0:
                    self.result.clear()
                    self.result['title'] = ts
                    self.result['pubdate_str'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(beg))
                    self.result['adddate_str'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end))
                    self.result['flag_name'] = 'calendar'
                    self.result['feed_name'] = group_by
                    self.result['is_node'] = 1
                    self.result['children_no'] = count
                    results_tmp.append(self.result.listify())
                    results_tmp = results_tmp + node_tmp


        self.results = tuple(results_tmp.copy())





#####################################################################
#
#       Technical Queries
#
#

    def list_feeds(self, **kargs):
        """ Lists feeds in DB """
        cats_only = kargs.get('cats_only',False)
        feeds_only = kargs.get('feeds_only',False)
        all = kargs.get('all',True)
        if cats_only or feeds_only: all = False

        self.result = ResultFeed()
        self.results = []

        for f in fdx.feeds_cache:
            self.result.populate(f)
            if feeds_only and self.result['is_category'] != 1: self.results.append(f)
            elif cats_only and self.result['is_category'] == 1: self.results.append(f)
            elif all: self.results.append(f) 
        
        if kargs.get('rev',False): self.results.reverse()
        self.results = tuple(self.results)

        self.result_no = len(self.results)
        self.result_no2 = 0
        return 0





    def feed_tree(self, **kargs):
        """ Generate Feed/Category tree """
        self.result = ResultFeed()
        result_tmp = ResultFeed()
        node_tmp = []
        self.results = []
        feeds_tmp = fdx.feeds_cache
        feeds_tmp.sort(key=lambda x: coalesce(x[self.result.get_index('display_order')],0), reverse=True)

        for f in feeds_tmp:        
            self.result.populate(f)
            if self.result['is_category'] != 1 and coalesce(self.result['parent_id'],0) == 0:
                self.results.append(self.result.tuplify())

        for f in feeds_tmp:
            result_tmp.clear()
            result_tmp.populate(f)
            if result_tmp['is_category'] == 1: 
                count = 0
                result_tmp['is_node'] = 1
                node_tmp = []
                for ff in feeds_tmp:
                    self.result.populate(ff)
                    if self.result['is_category'] != 1 and self.result['parent_id'] == f[self.result.get_index('id')]:
                        count += 1
                        self.result['is_node'] = 0
                        node_tmp.append(self.result.tuplify())

                result_tmp['children_no'] = count
                self.results.append(result_tmp.tuplify())
                self.results = self.results + node_tmp



        if kargs.get('rev',False): self.results.reverse()
        self.results = tuple(self.results)

        self.result_no = len(self.results)
        self.result_no2 = 0
        return 0




    def list_rules(self, **kargs):
        """ List user's rules in DB """
        self.result = ResultRule()
        if kargs.get('learned',False): self.results = self.DB.qr_sql(SHOW_RULES_LEARNED_SQL, {}, all=True)
        else: self.results = self.DB.qr_sql("select * from rules where learned <> 1 order by id desc", {}, all=True)
        if kargs.get('rev',False): self.results.reverse()
        self.results = tuple(self.results)
        self.result_no = len(self.results)
        self.result_no2 = 0
        return 0

    def list_flags(self, **kargs):
        """ Lists flags in DB """
        self.result = ResultFlag()
        self.results = []
        for k,v in fdx.flags_cache.items(): self.results.append( (k,) + v )
        if kargs.get('rev',False): self.results.reverse()
        self.results = tuple(self.results)
        self.result_no = len(self.results)
        self.result_no2 = 0
        return 0

    def list_history(self, **kargs):
        """ List saved history items """
        self.result = ResultHistoryItem()
        self.results = fdx.search_history_cache.copy()
        if kargs.get('rev',False): self.results.reverse()
        self.results = tuple(self.results)
        self.result_no = len(self.results)
        self.result_no2 = 0
        return 0









#####################################################################
#
#       QUERY BUILDING
#



    def _validate_filters(self, string:str, filters:dict, **kargs):
        """ Validate and process query filters into single standard """
       
        qtype = fdx.resolve_qtype(filters.get('qtype'))
        if qtype == -1: return msg(FX_ERROR_QUERY, _('Invalid query type!'))
        filters['qtype'] = qtype
        
        lang = coalesce( filters.get('lang'), 'heuristic' )

        if qtype in (1,): self.LP.set_model(lang)

        if filters.get('field') is not None:
            filters['field'] = fdx.resolve_field(filters.get('field'))
            if filters['field'] == -1: return msg(FX_ERROR_QUERY, _('Invalid search field value!'))
            
        if filters.get('category') is not None:
            filters['category'] = fdx.find_category(filters.get('category'))
            if filters['category'] == -1: return msg(FX_ERROR_QUERY, _('Category not found!'))

        if filters.get('feed') is not None:
            filters['feed'] = fdx.find_feed(filters.get('feed'))
            if filters['feed'] == -1: return msg(FX_ERROR_QUERY, _('Channel not found!'))

        if filters.get('feed_or_cat') is not None:
            filters['feed_or_cat'] = fdx.find_f_o_c(filters.get('feed_or_cat'))
            if filters['feed_or_cat'] == -1: return msg(FX_ERROR_QUERY, _('Category or Channel not found!'))
            elif filters['feed_or_cat'][0] == -1:
                filters['category'] = filters['feed_or_cat'][1]
                filters['feed_or_cat'] = None
            elif filters['feed_or_cat'][1] == -1:
                filters['feed'] = filters['feed_or_cat'][0]
                filters['feed_or_cat'] = None
        
        case_ins = None
        if filters.get('case_ins') is True:
            case_ins = True
            filters['case_ins'] = True
        if filters.get('case_sens') is True: 
            case_ins = False
            filters['case_ins'] = False

        if case_ins is None:
            if self._has_caps(string):
                case_ins = False
                filters['case_ins'] = False
            else:
                case_ins = True
                filters['case_ins'] = True
        
        filters['flag'] = self._resolve_flag(filters.get('flag'))

        # Resolve date ranges
        if filters.get('date_from') is not None:
            date = convert_timestamp(filters['date_from'])
            if date is None: return msg(FX_ERROR_QUERY, _('Could not parse date (date_from)!'))
            filters['raw_pubdate_from'] = date

        if filters.get('date_to') is not None:
            date = convert_timestamp(filters['date_to'])
            if date is None: return msg(FX_ERROR_QUERY, _('Could not parse date (date_to)!'))
            filters['raw_pubdate_to'] = date

        if filters.get('date_add_from') is not None:
            date = convert_timestamp(filters['date_add_from'])
            if date is None: return msg(FX_ERROR_QUERY, _('Could not parse date (date_add_from)!'))
            filters['raw_adddate_from'] = date

        if filters.get('date_add_to') is not None:
            date = convert_timestamp(filters['date_add_to'])
            if date is None: return msg(FX_ERROR_QUERY, _('Could not parse date (date_add_to)!'))
            filters['raw_adddate_to'] = date




        # Resolve preset date filters
        if filters.get('last',False): filters['raw_adddate_from'] = self.DB.get_last()

        if filters.get('last_n') is not None:
            last_upd = self.DB.get_last(ord=filters['last_n'])
            if last_upd < 0: return msg(FX_ERROR_QUERY, _('Invalid value for last Nth update!'))
            else: filters['raw_adddate_from'] = last_upd


        if filters.get("today", False):
            date = int(datetime.now().timestamp()) - 86400
            if date > 0: filters['raw_pubdate_from'] = date

        elif filters.get("last_week", False):
            date = int(datetime.now().timestamp()) - 604800
            if date > 0: filters['raw_pubdate_from'] = date

        elif filters.get("last_month", False):
            date = int(datetime.now().timestamp()) - (86400*31)
            if date > 0: filters['raw_pubdate_from'] = date
        
        elif filters.get("last_quarter", False):
            date = int(datetime.now().timestamp()) - (86400*31*3)
            if date > 0: filters['raw_pubdate_from'] = date

        elif filters.get("last_six_months", False):
            date = int(datetime.now().timestamp()) - (86400*31*6)
            if date > 0: filters['raw_pubdate_from'] = date

        elif filters.get("last_year", False):
            date = int(datetime.now().timestamp()) - (86400*31*12)
            if date > 0: filters['raw_pubdate_from'] = date

        elif filters.get('last_hour', False):
            date = int(datetime.now().timestamp()) - (60*60)
            if date > 0: filters['raw_pubdate_from'] = date

        # Resolve pages
        page_len = scast(filters.get('page_len'), int, self.config.get('page_length',3000))
        page = scast(filters.get('page'), int, 1)
        if page <= 1: page = 1
        if page_len <= 1: page_len = 3000
        filters['start_n'] = page_len * (page - 1)
        filters['page_len'] = page_len

        if filters.get('group') is not None: 
            if filters.get('group') not in ('category', 'feed', 'flag', 'hourly', 'daily', 'monthly', 'similar'): 
                return msg(FX_ERROR_QUERY, _('Invalid grouping! Must be: %a'), 'category, feed, flag, similar, hourly, daily or monthly')

        if filters.get('depth') is not None:
            filters['depth'] = scast(filters.get('depth'), int, -1)
            if not filters['depth'] > 0: return msg(FX_ERROR_QUERY, _('Depth must be a positive integer!'))

        rev = filters.get('rev',False)

        # Resolve sorting fields
        if filters.get('sort') is not None:
            sort = True
            filters['sort'] = scast(filters['sort'], str, '')
            sort_tmp = []
            for s in filters['sort'].split(','):
                rv = False
                if s.startswith('-'):
                    rv = True
                    s = s[1:]
                elif s.startswith('+'):
                    s = s[1:]
                if s not in ENTRIES_SQL_TABLE: return msg(FX_ERROR_QUERY, _('Invalid sorting field: %a!'), s)
                if rv: s = f'e.{s} ASC'
                else: s = f'e.{s} DESC'
                sort_tmp.append(s)

            filters['sort'] = sort_tmp.copy()

        else: sort = False

        if filters.get('fallback_sort') is not None:
            filters['fallback_sort'] = scast(filters['fallback_sort'], str, '')
            sort_tmp = []
            for s in filters['fallback_sort'].split(','):
                rv = False
                if s.startswith('-'):
                    rv = True
                    s = s[1:]
                elif s.startswith('+'):
                    s = s[1:]
                if s not in ENTRIES_SQL_TABLE: return msg(FX_ERROR_QUERY, _('Invalid fallback sorting field: %a!'), s)
                if rv: s = f'e.{s} ASC'
                else: s = f'e.{s} DESC'
                sort_tmp.append(s)

            filters['fallback_sort'] = sort_tmp.copy()

        return filters, qtype, rev, sort, case_ins







    def _build_sql(self, phrase:dict, filters:dict, **kargs):
        """ Builds SQL query to get basic lists of results """

        # Construct condition string if search phrase is not empty 
        # Haldle wildcards, beginnings, endings, case sensitivity and such...
        vals = {}
        if not phrase['empty']:

            qtype = filters.get('qtype',0)
            field = filters.get('field')

            vals['phrase'] = phrase['sql']

            # String matching
            if qtype == 0:

                if not filters.get('case_ins', False):
                    if field is None: cond = "\n(e.title LIKE :phrase  ESCAPE '\\' OR e.desc LIKE :phrase  ESCAPE '\\' OR e.category LIKE :phrase  ESCAPE '\\' OR e.text LIKE :phrase  ESCAPE '\\')\n"
                    else: cond = f"\n( {PREFIXES[field]['sql']} LIKE :phrase ESCAPE '\\')\n"
                else:
                    if field is None: cond = "\n(lower(e.title) LIKE lower(:phrase)  ESCAPE '\\' OR lower(e.desc) LIKE lower(:phrase)  ESCAPE '\\' OR lower(e.category) LIKE lower(:phrase)  ESCAPE '\\' OR lower(e.text) LIKE lower(:phrase)  ESCAPE '\\')\n"
                    else: cond = f"\n( lower({PREFIXES[field]['sql']}) LIKE lower(:phrase) ESCAPE '\\')\n"
            else:
                cond = "\n2=2\n"

        else: #string is empty
            cond = "\n1=1\n"


        # And this is a core of a query (with column listing from header constant)
        query = f"select {RESULTS_COLUMNS_SQL}\nwhere {cond}"

        #Add filtering according to given parameters
        if filters.get("feed") is not None:
            vals['feed_id'] = scast(filters.get('feed'), int, 0)
            query = f"{query}\nand ( f.id = :feed_id and f.is_category <> 1 )"

        elif filters.get("category") is not None:
            if filters.get("deleted", False): del_str = ''
            else: del_str = 'and coalesce(c.deleted,0) <> 1'
            vals['parent_category'] = scast(filters.get('category'), int, 0)
            query = f"""{query}\nand ((c.id = :parent_category or f.id = :parent_category) {del_str}) """
            
        if filters.get("id") is not None:
            vals['id'] = scast(filters.get('id'), int, 0)
            query = f"{query}\nand e.id = :id"

        if filters.get("raw_pubdate_from") is not None: 
            query = f"{query}\nand e.pubdate >= :raw_pubdate_from"
            vals['raw_pubdate_from'] = filters['raw_pubdate_from']
        if filters.get("raw_pubdate_to") is not None: 
            query = f"{query}\nand e.pubdate <= :raw_pubdate_to"
            vals['raw_pubdate_to'] = filters['raw_pubdate_to']
        if filters.get("raw_adddate_from") is not None: 
            query = f"{query}\nand e.adddate >= :raw_adddate_from"
            vals['raw_adddate_from'] = filters['raw_adddate_from']
        if filters.get("raw_adddate_to") is not None: 
            query = f"{query}\nand e.adddate <= :raw_adddate_to"
            vals['raw_adddate_to'] = filters['raw_adddate_to']
        


        if filters.get('handler') is not None:
            vals['handler'] = scast(filters.get('handler'), str, '').lower()
            query = f"{query}\nand f.handler = :handler"

        if filters.get('note') is not None:
            vals['note'] = scast(filters.get('note'), int, 0)
            query = f"{query}\nand e.note = :note"


        if filters.get("unread",False):
            query = f"{query}\nand coalesce(e.read,0) = 0"
        elif filters.get("read",False):
            query = f"{query}\nand coalesce(e.read,0) > 0"

        if filters.get("flag") is not None:
            if filters.get('flag') == 0:
                query = f"{query}\nand coalesce(e.flag,0) > 0"
            elif filters.get('flag') == -1:
                query = f"{query}\nand coalesce(flag,0) = 0"
            else:  
                vals['flag'] = scast(filters.get('flag',0), int, 0)
                query = f"{query}\nand coalesce(e.flag,0) = :flag"

        if filters.get("deleted",False):
            query = f"{query}\nand (coalesce(e.deleted,0) = 1 or coalesce(f.deleted,0) = 1)"
        elif filters.get("deleted_entries",False):
            query = f"{query}\nand (coalesce(e.deleted,0) = 1)"
        else:
            query = f"{query}\nand coalesce(e.deleted,0) <> 1 and coalesce(f.deleted,0) <> 1"

        ext_filter = False
        # This one is risky, so we have to be very careful every ID is a valis integer
        if filters.get('ID_list') is not None and type(filters.get('ID_list')) in (list,tuple) and len(filters.get('ID_list',[])) > 0:
            ids = ''
            for i in filters.get('ID_list',[]):
                i = scast(i, int, None)
                if i is None: continue
                ids = f'{ids}{i},'
            ids = ids[:-1]
            query = f"{query}\nand e.id in ({ids})"
            ext_filter = True

        # Build SQL comma-separated list for Xapian results. This may be very long
        if filters.get('IX_ID_list') is not None and type(filters.get('IX_ID_list')) in (list,tuple) and len(filters.get('IX_ID_list',[])) > 0:
            ids = ''
            for i in filters.get('IX_ID_list',[]):
                i = scast(i, int, None)
                if i is None: continue
                ids = f'{ids}{i},'
            ids = ids[:-1]
            query = f"{query}\nand e.ix_id in ({ids})"
            ext_filter = True

        # exclude certain id (e.g. for similarity search)
        if filters.get('exclude_id') is not None:
            query = f"{query}\n and e.id <> {scast(filters.get('exclude_id'), int, -1)}"

        # Sorting options
        if filters.get('sort') not in (None, (), []):
            sort_fields = filters['sort']
            query = f"{query}\nORDER BY"
            for sf in sort_fields: query = f'{query} {sf}, '
            query = f'{query} e.id DESC'

        elif phrase.get('empty',False):
            if filters.get('fallback_sort') not in (None, (), []):
                sort_fields = filters['fallback_sort']
                query = f"{query}\nORDER BY"
                for sf in sort_fields: query = f'{query} {sf}, '
                query = f'{query} e.id DESC'
            else:
                query = f"{query}\nORDER BY e.pubdate DESC, e.id DESC"
            


        # Pages
        if not ext_filter:            
            query = f"{query}\nLIMIT :page_len OFFSET :start_n"
            vals['start_n'] = scast(filters.get('start_n'), int, 0)
            vals['page_len'] = scast(filters.get('page_len', self.config.get('page_length',3000)), int, 3000)
        
        debug(5,f"Query: {query}\n{vals}\nPhrase: {self.phrase}")
        
        
        return query, vals












    def _build_xapian_qr(self, phrase:dict, filters:dict, *kargs):
        """ Parse filters and query to buid a proper Xapian query string """
            
        filter_qr = '' # Part of query string that handles filters
        del_filter_str = '' # Part of q.s. that handles deleted feeds/categories
        for f in fdx.feeds_cache:
            if f[FEEDS_SQL_TABLE.index('deleted')]: del_filter_str = f"""{del_filter_str} OR FEED_ID:{f[FEEDS_SQL_TABLE.index('id')]}"""
            if del_filter_str.startswith(' OR '): del_filter_str = del_filter_str[4:]
        if del_filter_str != '': filter_qr = f'{filter_qr} AND NOT ({del_filter_str})'


        if filters.get('feed') is not None: filter_qr = f"""{filter_qr} AND FEED_ID:{scast(filters.get('feed'), str, '-1')}"""
            
        if filters.get('category') is not None:
            cat_id = scast(filters.get('category'), int, -1)
            feed_str = f'FEED_ID:{cat_id}'
            for f in fdx.feeds_cache:
                if f[FEEDS_SQL_TABLE.index('parent_id')] == cat_id: feed_str = f"""{feed_str} OR FEED_ID:{f[FEEDS_SQL_TABLE.index('id')]}"""
            filter_qr = f"""{filter_qr} AND ({feed_str})"""

        if filters.get('raw_pubdate_from') is not None or filters.get('raw_pubdate_to') is not None:
            filter_qr = f"""{filter_qr} AND {scast(filters.get('raw_pubdate_from'), str, '')}..{scast(filters.get('raw_pubdate_to'), str, '')}XPUB""" 
        if filters.get('raw_adddate_from') is not None or filters.get('raw_adddate_to') is not None:
            filter_qr = f"""{filter_qr} AND {scast(filters.get('raw_adddate_from'), str, '')}..{scast(filters.get('raw_adddate_to'), str, '')}XADD""" 

        if filters.get('flag') is not None:
            if filters.get('flag') == 0: filter_qr = f"""{filter_qr} AND 1..XFLG"""
            elif filters.get('flag') == -1: filter_qr = f"""{filter_qr} AND 0..0XFLG"""
            else: filter_qr = f"""{filter_qr} AND {scast(filters.get('flag'), str, '')}..{scast(filters.get('flag'), str, '')}XFLG"""

        if filters.get('note') is not None:
            if filters['note'] == 1: filter_qr = f"""{filter_qr} AND NOTE:1"""
            else: filter_qr = f"""{filter_qr} AND NOTE:0"""

        if filters.get('read') is not None and coalesce(filters.get('read'), False): filter_qr = f"""{filter_qr} AND READ:1"""
        if filters.get('unread') is not None and coalesce(filters.get('unread'), False): filter_qr = f"""{filter_qr} AND READ:0"""

        if filters.get('handler') is not None: filter_qr = f"""{filter_qr} AND HANDLER:{filters.get('handler')}"""



        if filter_qr != '': self.phrase['fts'] = f"""( {self.phrase['fts']} ) {filter_qr}"""

        def_op = xapian.Query.OP_OR
        if filters.get('logic') is not None:
            logic = filters.get('logic')
            if logic == 'any': def_op = xapian.Query.OP_OR
            elif logic == 'all': def_op = xapian.Query.OP_AND
            elif logic == 'near': def_op = xapian.Query.OP_NEAR
            elif logic == 'phrase': def_op = xapian.Query.OP_PHRASE
            else: return msg(FX_ERROR_QUERY, _('Invalid logical operation! Must be: any, all, near, or phrase'))

        # ... handle xapian stuff now ...
        self.ix_qp.set_default_op(def_op)
        try: ix_qr = self.ix_qp.parse_query(self.phrase['fts'])
        except (xapian.QueryParserError, xapian.LogicError, xapian.RangeError, xapian.WildcardError,) as e: 
            return msg(FX_ERROR_QUERY, _('Index error: %a'), e)
        enquire = xapian.Enquire(self.DB.ix)
        enquire.set_query(ix_qr)
        
        debug(5, f"Xapian query: {self.phrase['fts']}\n{ix_qr}")

        return ix_qr, enquire









    def parse_query(self, string, **kargs):
        """ Parse query string and build a nice dictionary for different subsystems """
        case_ins = kargs.get('case_ins',False)
        stem = kargs.get('stem',False)
        field = kargs.get('field')

        beg = False
        end = False

        raw = string

        if kargs.get('str_match', False):       

            beg, end, string = self._get_bed_end(string)
            if case_ins: string = string.lower()
            rstr = random_str(string=string)
            string = string.replace('\*',rstr)
            if '*' in string: has_wc = True
            else: has_wc = False

            if string.replace(' ','').replace('*','') == '': 
                return {'empty':True, 'beg':False, 'end':False, 'sql':None, 'fts':None, 'spl_string':[], 'spl_string_len':0, 'has_wc':has_wc}

            while '**' in string: string = string.replace('**','*')

            # Construct SQL phrase
            if kargs.get('sql',False):
                sql = self._sqlize(string)
                sql = sql.replace('*','%')
                if not beg: sql = f'%{sql}'
                if not end: sql = f'{sql}%'
                sql = sql.replace(rstr,'*')
            else: sql = None

            # Split string for internal string matching
            spl_string = []
            for t in self.LP.str_match_split(string):
                if type(t) is str: t = t.replace(rstr,'*')
                spl_string.append(t)

            return {'empty':False, 'beg':beg, 'end':end, 'sql':sql, 'fts': None, 'spl_string':spl_string, 'spl_string_len':len(spl_string), 'has_wc':has_wc, 'raw':raw}






        # This is only for splitting into tokens and stemming for simple learned rule search
        elif kargs.get('str_match_stem', False):

            beg, end, string = self._get_bed_end(string)

            if string.replace(' ','').replace('*','') == '': 
                return {'empty':True, 'beg':False, 'end':False, 'sql':None, 'fts': '', 'spl_string':[], 'spl_string_len':0, 'has_wc':has_wc}

            toks = ''
            for t in self.LP._simple_tokenize(string):
                t = self.LP.stemmer.stemWord(t.lower())
                if field is not None: t = f"""{PREFIXES[field]['prefix']}{t}"""
                toks = f'{toks} {t}'
            if toks != '': toks = toks[1:]
            if beg: toks = f'  {toks}'
            if end: toks = f'{toks}  '
            
            return {'empty':False, 'beg':beg, 'end':end, 'sql':None, 'fts': toks, 'spl_string':[], 'spl_string_len':0, 'has_wc':False}

            


        # Tokenize and prefix for Xapian
        elif kargs.get('fts',True):
            if field is not None: fprefix = PREFIXES[field]['prefix']
            else: fprefix = ''

            toks = ''
            empty = True
            for t in re.findall(self.REGEX_xap_query, string):
                if t in ('AND','OR','NEAR','(',')','~','NOT'): pass
                elif t.startswith('~') and t.replace('~','').isdigit(): pass
                elif t.startswith('<') and t.endswith('>'):
                    tt = t.replace('<','').replace('>','')
                    if tt in SEM_TERMS: 
                        empty = False
                        t = f"""{PREFIXES['sem']}:{tt.lower()}"""
                else: 
                    empty = False
                    prefix = fprefix
                    if self.LP._case(t) == 0: t = self.LP.stemmer.stemWord(t)
                    else: prefix = f"""{prefix}{PREFIXES['exact']}""" 
                    if prefix != '': t = f'''{prefix}:{t.lower()}'''
                    else: t = t.lower()
                
                toks = f'{toks} {t}'

            if toks != '': toks = toks.lstrip()

            if empty: raw = None
            return {'empty':empty, 'beg':beg, 'end':end, 'sql':None, 'fts': toks, 'spl_string':[], 'spl_string_len':0, 'has_wc':False, 'raw':raw}









#######################################################################
#
#           UTILITIES
#



    def _has_caps(self, string):
        """ Checks if a string contains capital letters """
        for c in string:
            if c.isupper(): return True
        return False

    def _resolve_flag(self, flag:str):
        if flag in (None,'','all'): return None

        elif flag == 'all_flags': return 0
        elif flag == 'no': return -1
        else: return fdx.find_flag(flag)

    def _sqlize(self, string:str, **kargs):
        """ Escapes SQL wildcards """
        #   sql = string.replace('\\', '\\\\')
        sql = string.replace('%', '\%')
        sql = sql.replace('_', '\_')
        return sql
 



    def parse_json_query(self, json_str:str, **kargs):
        """ Parse json string for query phrase and filters """
        filters = {}
        try: 
            filters = json.loads(json_str)
        except (json.JSONDecodeError, TypeError) as e: return msg(FX_ERROR_QUERY, f"""{_('Invalid JSON query string!')} {e}""")
 
        phrase = filters.get('phrase','')
        return phrase, filters







    def _get_bed_end(self, string):
        """ Detects beginning/ending markers """
        beg = False
        end = False

        if string.startswith('^'):
            beg = True
            string = string[1:]
        elif string.startswith('\^'):
            string = string[1:]
        
        if string.endswith('\$'):
            string = f'{string[:-2]}$'
        elif string.endswith('$'):
            end = True
            string = string[:-1]
        
        if string.startswith('*'): 
            string = string[1:]
            beg = False
        if string.endswith('*'): 
            string = string[:-1]
            end = False

        return (beg, end, string)









class FeedexCatalogQuery(FeedexQueryInterface):
    """ Interface for querying feed import catalog """
    def __init__(self, **kargs) -> None:
        super().__init__()
        self.result = ResultCatItem()



    def resolve_cat(self, category):
        """ Resolve category to ID """
        for ci in fdx.catalog:
            if ci[self.result.get_index('is_node')] == 1:
                if ci[self.result.get_index('name')] == category or ci[self.result.get_index('id')] == category:
                    return ci[self.result.get_index('id')]
        msg(FX_ERROR_QUERY, _('Category %a not found!'), category)
        return -1



    def query(self, qr, filters, **kargs):
        """ Query Catalog """
        fdx.load_catalog()
        if fdx.catalog in (None, (), []): 
            self._empty()
            return 0

        load_all = kargs.get('load_all', False)

        qr = scast(qr, str, '').lower()

        # Resolve field
        field = filters.get('field')
        if field not in (None, 'name', 'desc', 'tags', 'location'): 
            self._empty()
            return msg(FX_ERROR_VAL, _('Invalid search field! Must be name, desc, tags or location.'))

        # Resolve category
        category = filters.get('category') 
        if category is not None:
            category = self.resolve_cat(category)
            if category == -1:
                self._empty()
                return FX_ERROR_QUERY


        self.results.clear()

        if qr.strip() == '':
            if category is None:
                if load_all: self.results = fdx.catalog
                else:
                    for ci in fdx.catalog:
                        if ci[self.result.get_index('is_node')] == 1: self.results.append(ci)

            else:
                for ci in fdx.catalog:
                    if ci[self.result.get_index('is_node')] == 1 and ci[self.result.get_index('id')] == category: self.results.append(ci)
                    if ci[self.result.get_index('is_node')] == 0 and ci[self.result.get_index('parent_id')] == category: self.results.append(ci)


        else:

            for ci in fdx.catalog:
                if category is not None:
                    if ci[self.result.get_index('id')] == category: 
                        self.results.append(ci)
                        continue
                    if ci[self.result.get_index('parent_id')] != category: 
                        continue 

                if ci[self.result.get_index('is_node')] == 1: 
                    self.results.append(ci)
                    continue 

                if field is None: search_text = f"""{ci[self.result.get_index('name')]} {ci[self.result.get_index('desc')]} {ci[self.result.get_index('tags')]} {ci[self.result.get_index('location')]}"""
                else: search_text = scast(ci[self.result.get_index(field)], str, '')
                search_text = search_text.lower()
                if qr in search_text: self.results.append(ci)


        self.result_no = len(self.results)
        return 0