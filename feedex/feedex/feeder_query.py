# -*- coding: utf-8 -*-
""" Query Parser for Feedex"""

from feedex_headers import *







class FeederQuery:
    """ Class for query parsing, searching and rule matching for Feedex """


    def __init__(self, FX, **kargs):

        # Config and parent classes
        self.config = kargs.get('config', DEFAULT_CONFIG)
        self.FX = FX

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

        # Overload config passed in arguments
        self.debug = kargs.get('debug') # Triggers additional info at runtime

        self.ignore_images = kargs.get('ignore_images', self.config.get('ignore_images',False))
        self.wait_indef = kargs.get('wait_indef',False)

        # Output flags
        self.output = kargs.get('output','cli')
        self.print = kargs.get('print',False)
        self.plot = kargs.get('plot',False)
        if self.output in ('csv','json','html','short','headlines','cli_noline'): self.print = True
        if self.plot: self.print = False

        # Processed search phrase
        self.phrase = {}

        # Interface for managing history items
        self.history_item = HistoryItem(self.FX)

        # Container for query results
        self.result = SQLContainer('entries', RESULTS_SQL_TABLE)
        self.feed = SQLContainer('feeds', FEEDS_SQL_TABLE)

        # Query results
        self.results = []

        self.snippets_lst = [] # Snippet lists for query results (string search)

        self.total_result_number = 0 #This is a result number in case a sumary is performed

        if self.print or self.plot: self.CLI = FeedexCLI(self, **kargs)






    def cli_table_print(self, *args, **kargs):
        if self.print: return self.CLI.cli_table_print(*args, **kargs)

    def cli_plot(self, *args, **kargs):
        if self.plot: return self.CLI.cli_plot(*args, **kargs)






##############################################################
#
#       QUERY PARSING AND MAIN SEARCH


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

        # Sorting options
        sort = filters.get('sort')
        default_sort = filters.get('default_sort')
        rev = filters.get('rev')
        if (sort is not None) and (type(sort) is str) and (len(sort) > 2):
            if sort.startswith('-'): desc=True
            else: desc=False
            sort = sort[1:]
            if sort not in ENTRIES_SQL_TABLE:
                cli_msg( (-5, _("%a is not a valid field! Changed to ID"), sort) )
                sort = 'id'
            query = f"{query}\norder by e.{sort}"
            if desc and not rev: query = f"{query} DESC"
            elif not desc and rev: query = f"{query} DESC"
            # Need to add additional sorting field because sorting by the same values slows down a query
            query = f"{query}, e.readability"           # Readability is a good default sorting field
            if desc and not rev: query = f"{query} DESC"
            elif not desc and rev: query = f"{query} DESC"
            query = f"{query}, e.id"
            if desc and not rev: query = f"{query} DESC"
            elif not desc and rev: query = f"{query} DESC"

        elif phrase.get('empty',False) and default_sort is not None:
            if default_sort.startswith('-'): desc=True
            else: desc=False
            default_sort = default_sort[1:]
            if default_sort not in ENTRIES_SQL_TABLE:
                cli_msg( (-5, _("%a is not a valid field! Changed to ID"), default_sort) )
                default_sort = 'id'
            query = f"{query}\norder by e.{default_sort}"
            if desc and not rev: query = f"{query} DESC"
            elif not desc and rev: query = f"{query} DESC"
            query = f"{query}, e.readability"           
            if desc and not rev: query = f"{query} DESC"
            elif not desc and rev: query = f"{query} DESC"
            query = f"{query}, e.id"
            if desc and not rev: query = f"{query} DESC"
            elif not desc and rev: query = f"{query} DESC"

        # Pages
        if not ext_filter:            
            query = f"{query}\nLIMIT :page_len OFFSET :start_n"
            vals['start_n'] = scast(filters.get('start_n'), int, 0)
            vals['page_len'] = scast(filters.get('page_len', self.config.get('page_length',3000)), int, 3000)

        return query, vals






    def parse_json_query(self, json_str:str, **kargs):
        """ Parse json string for query phrase and filters """
        filters = {}
        try: 
            filters = json.loads(json_str)
        except (json.JSONDecodeError, TypeError) as e:
            self.FX.MC.ret_status = cli_msg( (-5, f"""{_('Invalid JSON query string!')} {e}""" ) )
            return -1, {}
 
        phrase = filters.get('phrase','')
 
        return phrase, filters







######################################################################
#   BASIC QUERY
#






    def query(self, string:str, filters:dict, **kargs):
        """ Main Query method
            Queries database with search string. """

        # First we sanitize filters for SQL and Xapian ...
        qtype = self.FX.resolve_qtype(filters.get('qtype'))
        if qtype == -1:
            self.FX.MC.ret_status = cli_msg( (-5, _('Invalid query type!')) )
            return ()
        filters['qtype'] = qtype

        
        lang = coalesce( filters.get('lang'), 'heuristic' )

        if qtype in (1,): self.FX.LP.set_model(lang)

        if filters.get('field') is not None:
            filters['field'] = self.FX.resolve_field(filters.get('field'))
            if filters['field'] == -1:
                self.FX.MC.ret_status = cli_msg( (-5, _('Invalid search field value!')) )
                return ()
            

        if filters.get('category') is not None:
            filters['category'] = self.FX.resolve_category(filters.get('category'))
            if filters['category'] == -1: 
                self.FX.MC.ret_status = cli_msg( (-5, _('Category not found!')) )
                return ()

        if filters.get('feed') is not None:
            filters['feed'] = self.FX.resolve_feed(filters.get('feed'))
            if filters['feed'] == -1:
                self.FX.MC.ret_status = cli_msg( (-5, _('Channel ID not found!')) )
                return ()

        if filters.get('feed_or_cat') is not None:
            filters['feed_or_cat'] = self.FX.resolve_f_o_c(filters.get('feed_or_cat'))
            if filters['feed_or_cat'] == -1:
                self.FX.MC.ret_status = cli_msg( (-5, _('Category or Channel not found!')) )
                return ()
            elif filters['feed_or_cat'][0] == -1:
                filters['category'] = filters['feed_or_cat'][1]
            elif filters['feed_or_cat'][1] == -1:
                filters['feed'] = filters['feed_or_cat'][0]



        rev = filters.get('rev',False)
        sort = filters.get('sort')
        
        case_ins = None
        if filters.get('case_ins') is True:
            case_ins = True
        if filters.get('case_sens') is True: 
            case_ins = False

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
            if date is None: 
                self.FX.MC.ret_status = cli_msg( (-5, _('Could not parse date (date_from)!')) )
                return ()
            filters['raw_pubdate_from'] = date
        if filters.get('date_to') is not None:
            date = convert_timestamp(filters['date_to'])
            if date is None: 
                self.FX.MC.ret_status = cli_msg( (-5, _('Could not parse date (date_to)!')) )
                return ()
            filters['raw_pubdate_to'] = date

        if filters.get('date_add_from') is not None:
            date = convert_timestamp(filters['date_add_from'])
            if date is None: 
                self.FX.MC.ret_status = cli_msg( (-5, _('Could not parse date (date_add_from)!')) )
                return ()
            filters['raw_adddate_from'] = date
        if filters.get('date_add_to') is not None:
            date = convert_timestamp(filters['date_add_to'])
            if date is None: 
                self.FX.MC.ret_status = cli_msg( (-5, _('Could not parse date (date_add_to)!')) )
                return () 
            filters['raw_adddate_to'] = date




        # Resolve preset date filters
        if filters.get('last',False): filters['raw_adddate_from'] = self.FX.get_last()

        if filters.get('last_n') is not None:
            last_upd = self.FX.get_last(ord=filters['last_n'])
            if last_upd < 0:
                self.FX.MC.ret_status = cli_msg( (-5, _('Invalid value for last Nth update!')) )
                return ()
            else:
                filters['raw_adddate_from'] = last_upd


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






        ####################################
        # Resolve pages
        page_len = scast(filters.get('page_len'), int, self.config.get('page_length',3000))
        page = scast(filters.get('page'), int, 1)
        if page <= 1: page = 1
        if page_len <= 1: page_len = 3000
        filters['start_n'] = page_len * (page - 1)
        filters['page_len'] = page_len


        ####################################
        # Now we perform main query ...
        rank =  kargs.get('rank',True)
        cnt = kargs.get('cnt',False)
        snippets = kargs.get('snippets',True)
        
        max_context_length = self.config.get('max_context_length', 500)

        # Construct phrase if needed
        if kargs.get('phrase') is None:
            if qtype == 0:      self.phrase = self.FX.LP.build_phrase(string, case_ins=case_ins, field=filters.get('field'), sql=True, str_match=True)
            elif qtype == 1:    self.phrase = self.FX.LP.build_phrase(string, case_ins=case_ins, field=filters.get('field'), sql=False, fts=True)
        
        else: self.phrase = kargs.get('phrase',{})

        # Some queries do not work with wildcards
        if kargs.get('no_wildcards',False) and self.phrase.get('has_wc',False):
            self.FX.MC.ret_status = cli_msg( (-5, _('Wildcards are not allowed with this type of query!')) )
            self.results = ()
            return self.results




        self.results = []

        # Query index if needed
        if qtype == 1 and not self.phrase['empty']:

            # Handle Xapian filters and ranges (to improve recall and performance)
            filter_qr = ''
            del_filter_str = ''
            for f in self.FX.MC.feeds:
                if f[self.feed.get_index('deleted')]: del_filter_str = f"""{del_filter_str} OR FEED_ID:{f[self.feed.get_index('id')]}"""
                if del_filter_str.startswith(' OR '): del_filter_str = del_filter_str[4:]
            if del_filter_str != '': filter_qr = f'{filter_qr} AND NOT ({del_filter_str})'


            if filters.get('feed') is not None: filter_qr = f"""{filter_qr} AND FEED_ID:{scast(filters.get('feed'), str, '-1')}"""
            
            if filters.get('category') is not None:
                cat_id = scast(filters.get('category'), int, -1)
                feed_str = f'FEED_ID:{cat_id}'
                for f in self.FX.MC.feeds:
                    if f[self.feed.get_index('parent_id')] == cat_id: feed_str = f"""{feed_str} OR FEED_ID:{f[self.feed.get_index('id')]}"""
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

            if filters.get('read') is not None:
                if filters['read'] == 1: filter_qr = f"""{filter_qr} AND READ:1"""
                else: filter_qr = f"""{filter_qr} AND READ:0"""

            if filters.get('handler') is not None: filter_qr = f"""{filter_qr} AND HANDLER:{filters.get('handler')}"""



            if filter_qr != '': self.phrase['fts'] = f"""( {self.phrase['fts']} ) {filter_qr}"""

            def_op = xapian.Query.OP_OR
            if filters.get('logic') is not None:
                logic = filters.get('logic')
                if logic == 'any': def_op = xapian.Query.OP_OR
                elif logic == 'all': def_op = xapian.Query.OP_AND
                elif logic == 'near': def_op = xapian.Query.OP_NEAR
                elif logic == 'phrase': def_op = xapian.Query.OP_PHRASE
                else:
                    self.FX.MC.ret_status = cli_msg( (-5, _('Invalid logical operation! Must be: any, all, near, or phrase')) )
                    self.results = ()
                    return self.results


            # ... and go ahead with query ...
            self.ix_qp.set_default_op(def_op)
            ix_qr = self.ix_qp.parse_query(self.phrase['fts'])
            enquire = xapian.Enquire(self.FX.ix)
            enquire.set_query(ix_qr)
            
            ix_matches = enquire.get_mset( filters['start_n'],  filters['page_len'] )

            if self.debug in (1,5): print(f"""Xapian query: 
{self.phrase['fts']} 
{ix_qr}""")

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
                                for v in self.FX.ix.synonyms(t): snips.append(v.decode("utf-8"))
                    count = ixm.rank
                else: 
                    count = None
                    snips = ()

                self.ix_results[ixm.docid] = (ixm.weight, ixm.rank, count, snips)



            if len(self.ix_results_ids) == 0:
                self.results = ()
                return self.results

            filters['IX_ID_list'] = self.ix_results_ids.copy() # This list will be appended to SQL query to extract Xapian results






        # Query SQL database
        (query, vals) = self._build_sql(self.phrase, filters)

        if self.debug in (1,5):
            print(f"\n\n'Query: \n{query}\n{vals}")
            print(f"Phrase: {self.phrase}")
  
        results_tmp = self.FX.qr_sql(query, vals, all=True)
        if self.FX.db_error is not None: 
            self.results = ()
            return self.results

        if self.debug in (1,5): print("Results: ", len(results_tmp))





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
                            (c, sn) = self.FX.LP.str_matcher((v,), 1, False, False, lf, snippets=snippets, orig_field=f)
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
                doc_count = kargs.get('doc_count', self.FX.get_doc_count())
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
                        (c, sn) = self.FX.LP.str_matcher(self.phrase['spl_string'], self.phrase['spl_string_len'], self.phrase['beg'], self.phrase['end'], lf, snippets=snippets, orig_field=f)
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
        if sort is None and ranked:
            if cnt: self.results.sort(key=lambda x: x[self.result.get_index('count')], reverse=rev)
            elif rank: self.results.sort(key=lambda x: x[self.result.get_index('rank')], reverse=rev)


        # Export to JSON file, if specified
        if kargs.get('json_file') is not None: self.FX.port_data(True, 'entries', kargs.get('json_file'),  query_results=self.results)


        # Group results, if needed
        if kargs.get('print', self.print):
            node_col = -1
            node_title_col = None
            node_header = ()
            node_header_raw = ()

        if kargs.get('allow_group',False):
            if filters.get('group') is not None:
                self.results = self.group_results(self.results, **filters)
                if kargs.get('print', self.print):
                    node_col = len(RESULTS_SQL_TABLE_PRINT)
                    node_title_col = self.result.get_index('title')
                    node_header = ('Is Node?',)
                    node_header_raw = ('is_node',)

        depth = scast(filters.get('depth'), int,0)
        if depth > 0 and filters.get('group') is None: 
            self.results = self.results[:depth]

        # Save phrase to history        
        if not kargs.get('no_history',False): 
            err = self.history_item.add(self.phrase, filters.get('feed'))
            if err != 0: self.FX.MC.ret_status = cli_msg(err)


        # Display results if needed
        if kargs.get('print', self.print):
            if self.output == 'short': columns = NOTES_PRINT
            elif self.output == 'headlines': columns = HEADLINES_PRINT
            else: columns = RESULTS_SHORT_PRINT1
            self.cli_table_print(RESULTS_SQL_TABLE_PRINT + node_header, self.results, mask=columns, 
                                flag_col=self.result.get_index('flag'), read_col=self.result.get_index('read'), del_col=self.result.get_index('deleted'), 
                                date_col=self.result.get_index('pubdate_short'), node_col=node_col, node_title_col=node_title_col,
                                html_cols=RESULTS_SQL_TABLE + node_header_raw)

        return self.results








 




####################################################################################################3
#
#       COMPOSITE QUERIES
#

    def get_trends(self, qr, filters, **kargs):
        """ Extract trends from group of entries (can get time consuming) """
        rev = kargs.get('rev', filters.get('rev',False))
        qr = scast(qr, str, '')
        flang = filters.get('lang')
        filters['rev'] = False

        self.query(qr, filters, rank=False, cnt=False, snippets=False, print=False, no_history=True, allow_group=False)
        
        keywords = {}

        for r in self.results:
            lang = r[self.result.get_index('lang')]
            self.FX.LP.set_model(lang)
            if flang is not None:
                if self.FX.LP.get_model() != flang: continue

            raw_text = ''
            for f in LING_TEXT_LIST: 
                raw_text = f"""{raw_text}
{scast(r[self.result.get_index(f)], str, '')}"""

            kwds = self.FX.LP.extract_features(raw_text, filters.get('depth',100))
            for kw in kwds:
                keywords[kw[0]] = keywords.get(kw[0],0) + kw[1]

        self.results = []
        for k,v in keywords.items(): self.results.append( (k,round(v,3)) )
        self.results.sort(key=lambda x: x[1], reverse=rev)

        if kargs.get('print',self.print): self.cli_table_print([n_("Keyword"), n_("Frequency")], self.results, output='csv', html_cols=('keyword','frequency',))

        return self.results




    def get_trending(self, qr, filters, **kargs):
        """ Get trending articles from given filters"""
        rev = kargs.get('rev', filters.get('rev',False))
        filters['rev'] = False

        depth = filters.get('depth',100)

        self.get_trends(qr, filters, print=False, no_history=True, allow_group=False)

        qr_string = ''
        for i,r in enumerate(self.results):
            if i >= depth: break
            qr_string = f"""{qr_string} OR {r[0].lower()}"""
        if qr_string.startswith(' OR '): qr_string = qr_string[4:]
        
        filters['qtype'] = 1
        filters['rev'] = rev
        self.query(qr_string, filters, rank=True, cnt=True, snippets=False, print=kargs.get('print',self.print), no_history=True, no_wildcards=True, allow_group=kargs.get('allow_group',True))
        if self.FX.db_error is not None: return ()

        return self.results        





    def find_similar(self, id, **kargs):
        """ Find entry similar to specified by ID based on extracted features """
        id = scast(id, int, 0)
        entry = EntryContainer(self.FX, id=id)
        rule = SQLContainer('rules', RULES_SQL_TABLE)

        if not entry.exists:
            self.FX.MC.ret_status = cli_msg( (-8, _('Nothing to search. Aborting...')) )
            return ()

        limit = kargs.get('limit',self.config.get('default_similarity_limit',20)) # Limit results

        # Get or generate rules
        if self.config.get('use_keyword_learning', True): 
            rules = self.FX.qr_sql("select * from rules where context_id=:id order by weight desc", {'id':id} , all=True)
            if self.FX.db_error is not None: return ()
        else: rules = None

        if rules in (None, [], [None], (), (None,)):
            if self.config.get('default_similar_weight', 2) > 0 and not kargs.get('no_weight',False):
                err = entry.ling(index=False, rank=False, learn=True, save_rules=True)
            else:
                err = entry.ling(index=False, rank=False, learn=True, save_rules=False)
            if err != 0: return ()
            rules = entry.rules.copy()

        if rules in (None, [], [None], ()):
            if self.debug in (1,5): print("Nothing to find...")
            return ()

        # Update entry as read (if so configured)
        if self.config.get('default_similar_weight', 2) > 0 and not kargs.get('no_weight',False):
            self.FX.run_sql_lock(f"update entries set read = coalesce(read,0) + {self.config.get('default_similar_weight', 2)}  where id = :id", {'id':id} )

        # Search for keywords in entries ...
        filters = kargs.copy()
        filters['lang'] = entry.get('lang','heuristic')
        filters['case_ins'] = True
        filters['qtype'] = 1
        filters['page'] = 1
        filters['page_len'] = limit
        doc_cnt = self.FX.get_doc_count()

        # ... and to do this construct a single query string from rules
        qr_string = ''
        for i,r in enumerate(rules):
            if i >= limit: break
            
            if type(r) in (list, tuple): rule.populate(r)
            elif type(r) is dict:
                rule.clear()
                rule.merge(r)
            else: continue

            s = rule['name']
            qr_string =f"""{qr_string} {s.lower()}"""
        if qr_string.startswith(' OR '): qr_string = qr_string[4:]

        # Execute final query using combined long composite phrase
        self.query(qr_string, filters, rank=True, cnt=True, doc_count=doc_cnt, snippets=False, print=kargs.get('print',self.print), no_history=True, no_wildcards=True, allow_group=kargs.get('allow_group',True))
        if self.FX.db_error is not None: return ()

        return self.results






    def relevance_in_time(self, id, **kargs):
        """ Gets keywords from entry and produces time series for them """
        id = scast(id, int, 0)
        result = SQLContainer('entries', RESULTS_SQL_TABLE)

        # Get similar items
        filters = kargs.copy()
        filters['limit'] = 500
        filters['print'] = False
        filters['allow_group'] = False
        results_tmp = self.find_similar(id, **filters)
        if len(results_tmp) == 0: return ()

        # Init stuff...
        group = kargs.get('group','daily')
        col_name = n_('Month')
        term_width = kargs.get('term_width',150)
        rev = kargs.get('rev',False)  # Reverse sort order

        if group == 'hourly': col_name = n_('Hour')
        elif group == 'daily': col_name = n_('Day')
        elif group == 'monthly': col_name = n_('Month')
        else:
            self.FX.MC.ret_status = cli_msg( (-5, _('Invalid grouping! Must be: %a'), 'daily, monthly or hourly') )
            return ()


        # Count results by specific date keys
        freq_dict = {}
        for r in results_tmp:
            result.populate(r)
            rnk = scast(result['rank'], float, 0)
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
        max = 0
        for f in freq_dict.keys():
            freq = freq_dict.get(f,0)
            if max < freq:
                max = freq
            data_points.append([f, round(freq, 3)])

        data_points.sort(key=lambda x: x[0], reverse=False)

        date_start = data_points[0][0]
        date_end = data_points[-1][0]

        time_series = []
        ts = date_start

        if group == "hourly": time_series.append([date_start[:-3], freq_dict[date_start]])
        elif group == "daily": time_series.append([date_start[:-9], freq_dict[date_start]])
        elif group == "monthly": time_series.append([date_start[:-12], freq_dict[date_start]])
            
        mon_rel = relativedelta(months=1)
        day_rel = relativedelta(days=1)

        # Populate every step on date, even if there were 0 occurences
        while ts != date_end:
            tst = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            if group == "hourly":
                tst += timedelta(hours=1)
                ts_disp = tst.strftime("%Y-%m-%d %H:%M")
            elif group == "daily":
                tst += day_rel
                ts_disp = tst.strftime("%Y-%m-%d")
            elif group == "monthly":
                tst += mon_rel
                ts_disp = tst.strftime("%Y-%m")
            
            ts = tst.strftime("%Y-%m-%d %H:%M:%S")
            fr = freq_dict.get(ts,0)
            time_series.append([ts_disp,fr])

        if rev: time_series.sort(key=lambda x: x[0], reverse=True)           

        if kargs.get('print',self.print): self.cli_table_print([col_name, n_("Frequency")], time_series, output='csv', html_cols=('time','frequency',))

        if kargs.get('plot',self.plot): self.cli_plot(time_series, max, term_width)

        self.results = time_series
        return time_series
 
                








    def term_context(self, string:str, **kargs):
        """ Get term's context (find entries and print immediate surroundings) """
        string = scast(string, str, '')
        if string == '': 
            self.results = ()
            return self.results
        
        self.query(string, kargs, count=False, rank=True, snippets=True, print=False)
        if self.FX.db_error is not None: return ()

        context = SQLContainer('entries', RESULTS_SQL_TABLE_PRINT + (n_("Context"),) )
        
        results_tmp = []
        
        self.total_result_number = len(self.results)

        # Build context list around extracted snippets - for multiple snippets in one document, results are duplicated
        for r in self.results:    
            self.result.populate(r)

            for s in self.result['snippets']:
                fields = self.result.listify(all=True)
                fields.append((s,))
                context.populate(fields)
                results_tmp.append(context.tuplify())

        self.results = results_tmp

        if kargs.get('print',self.print):
            if self.output not in ('csv',): output = 'cli_noline'
            else: output = self.output
            self.cli_table_print(context.fields, self.results, output=output,
                                mask=(context.get_index('Date'), context.get_index('Context'), context.get_index('ID'), context.get_index('Source (ID)'), context.get_index('Published - Timestamp'), context.get_index('Rank'), context.get_index('Count'), ), 
                                date_col=context.get_index('Date'), del_col=context.get_index('Deleted?'), read_col=context.get_index('Read'), flag_col=context.get_index('Flag'),
                                total_number=self.total_result_number, total_number_footnote=_('entries'), number_footnote=_('contexts'),
                                html_cols=RESULTS_SQL_TABLE + ('context',))
        
        else:
            return self.results












    def term_net(self, term:str, **kargs):
        """ Show terms/features connected to a given term by analising contexts """
        # Check for empty term
        term = scast(term, str, '').strip()
        if term == '':
            self.results = ()
            return self.results

        doc_count = kargs.get('doc_count', self.FX.get_doc_count())

        # Query for containing docs
        results_tmp = self.query(term, kargs, rank=True, cnt=True, doc_count=doc_count, snippets=False, print=False, no_history=True, no_wildcards=True)
        if self.FX.db_error is not None: return ()

        kwd_list = []
        # Generate keywords for fist N best matches
        for i,r in enumerate(results_tmp):
            if i > TERM_NET_DEPTH: break

            self.result.populate(r)
            self.FX.LP.set_model(self.result['lang'], sample=f"""{self.result['title']} {self.result['desc']}"""[:1000])          

            learning_string = ''
            for f in LING_TEXT_LIST: learning_string = f"""{learning_string}  {scast(self.result[f], str, '')}"""

            # ... and collect them to result list
            kwds = self.FX.LP.extract_features(learning_string, depth=MAX_FEATURES_PER_ENTRY)
            for kw in kwds: kwd_list.append( (kw[0],kw[1]) )

        # Consolidate results
        freq_dist = {}
        for kw in kwd_list: freq_dist[kw[0]] = freq_dist.get(kw[0],0) + kw[1] 

        self.results = []
        for k,v in freq_dist.items(): self.results.append( (k,v) )

        self.results.sort(key=lambda x: x[1], reverse=kargs.get('rev',False))

        # Save term to history        
        if not kargs.get('no_history',False):
            err = self.history_item.add(self.phrase, None)
            if err != 0: self.FX.MC.ret_status = cli_msg(err)        

        if kargs.get('print',self.print):
            self.cli_table_print((n_("Term"), n_("Weight")), self.results, output='csv', html_cols=('term', 'weight',))
            if self.debug in (1,5): print(len(self.results), " results")
        else:
            return self.results









    def get_keywords(self, id:int, **kargs):
        """ Output terms/features learned from an entry """

        SQL='select r.name, r.weight from rules r where r.context_id = :id order by r.weight'
        if kargs.get('rev',False): SQL=f'{SQL} DESC'
        else: SQL=f'{SQL} ASC'

        self.results = self.FX.qr_sql(SQL, {'id':id} , all=True)
        # f no saved rules were found, generate them on the fly ...
        if self.results in ([],None,[None]) and not kargs.get('no_recalc',False):
            entry = EntryContainer(self.FX, id=id)
            if not entry.exists:
                self.FX.MC.ret_status = -8
                return ()

            err = entry.ling(index=False, rank=False, learn=True, save_rules=False)
            if err != 0: return ()
            
            self.results.clear()
            for r in entry.rules: self.results.append( (r['name'], r['weight']) )
            self.results.sort(key=lambda x: x[1], reverse=kargs.get('rev', False))

        if kargs.get('print',self.print):
            self.cli_table_print((n_("Term"), n_("Weight")), self.results, output='csv', html_cols=('term','weight',))
            if self.debug in (1,5): print(len(self.results), " results")
        else:
            return self.results
                







    def rules_for_entry(self, id:int, **kargs):
        """ Output rules that match and contributed to importance of given entry """
        entry = EntryContainer(self.FX, id=id)
        rule = SQLContainer('rules',RULES_SQL_TABLE_RES)
        if not entry.exists: 
            self.FX.MC.ret_status = -8
            return ()

        importance, flag, best_entries, flag_dist, results = entry.ling(index=False, rank=True, to_disp=True)
        self.results = self.show_rules(results=results, print=False)

        if self.output in ('csv', 'json', 'html'):
            self.cli_table_print(RULES_SQL_TABLE_RES_PRINT, self.results, mask=PRINT_RULES_FOR_ENTRY, interline=False, output='csv', html_cols=RULES_SQL_TABLE_RES)
            return self.results

        print(f"""{_('Rules matched for entry')} {entry['id']} ({entry.name()}):
--------------------------------------------------------------------------------------------------------""")

        self.cli_table_print(RULES_SQL_TABLE_RES_PRINT, self.results, mask=PRINT_RULES_FOR_ENTRY, interline=False, output='short', flag_col=rule.get_index('flag'))        

        print(f"""--------------------------------------------------------------------------------------------------------
{_('Matched rules:')} {len(self.results)}

{_('Calculated Importance:')} {importance:.3f}, {_('Calculated Flag:')} {flag:.0f}
{_('Saved Importance:')} {entry['importance']:.3f}, {_('Saved Flag:')} {entry['flag']:.0f}
{_('Weight:')} {entry['weight']:.3f}
--------------------------------------------------------------------------------------------------------
{_('Flag distriution:')}""")

        for f,v in flag_dist.items(): print(f"{self.FX.get_flag_name(f)} ({f}): {v:.3f}")

        print(f"""--------------------------------------------------------------------------------------------------------
{_('Most similar read Entries:')}""")
        
        estring=''
        for e in best_entries: 
            estring = f'{estring}{e}, '
        print(estring)

        return self.results






    def term_in_time(self, term:str, **kargs):
        """ Get term frequency in time and output as a table of data points or a plot in terminal """
        term = scast(term, str, '')
        if term == '':
            self.results = ()
            return self.results
    
        group = kargs.get('group','daily')
        col_name = n_('Month')
        plot = kargs.get('plot',False)
        term_width = kargs.get('term_width',150)
        rev = kargs.get('rev', False)
        kargs['rev'] = False

        self.query(term, kargs, rank=False, cnt=True, snippets=False, print=False)
        if self.FX.db_error is not None: return ()

        if len(self.results) == 0:
            self.results = ()
            return ()

        if group == 'hourly': col_name = n_('Hour')
        elif group == 'daily': col_name = n_('Day')
        elif group == 'monthly': col_name = n_('Month')
        else: 
            self.FX.MC.ret_status = cli_msg( (-5, _('Invalid grouping! Must be: %a'), 'daily, monthly or hourly') )
            return ()

        freq_dict = {}
        data_points = []
        # Construct data table without zeroes
        for r in self.results:

            self.result.populate(r)
            cnt = scast(self.result['count'], int, 0)
            dtetime = scast(self.result['pubdate'], int, 0)

            if group == 'hourly':
                hour = time.strftime('%Y-%m-%d %H', time.localtime(dtetime)) + ":00:00"
                freq_dict[hour] = freq_dict.get(hour,0) + cnt

            elif group == 'daily':
                day = time.strftime('%Y-%m-%d', time.localtime(dtetime)) + " 00:00:00"
                freq_dict[day] = freq_dict.get(day,0) + cnt
                    
            elif group == 'monthly':
                month = time.strftime('%Y-%m', time.localtime(dtetime)) + "-01 00:00:00"
                freq_dict[month] = freq_dict.get(month,0) + cnt


        max = 0
        for f in freq_dict.keys():
            freq = freq_dict.get(f,0)
            if max < freq:
                max = freq
            data_points.append([f, freq])

        data_points.sort(key=lambda x: x[0], reverse=False)

        date_start = data_points[0][0]
        date_end = data_points[-1][0]

        time_series = []
        ts = date_start

        if group == "hourly": time_series.append([date_start[:-3], freq_dict[date_start]])
        elif group == "daily": time_series.append([date_start[:-9], freq_dict[date_start]])
        elif group == "monthly": time_series.append([date_start[:-12], freq_dict[date_start]])
            
        mon_rel = relativedelta(months=1)
        day_rel = relativedelta(days=1)

        # Populate every step on date, even if there were 0 occurences
        while ts != date_end:
            tst = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            if group == "hourly":
                tst += timedelta(hours=1)
                ts_disp = tst.strftime("%Y-%m-%d %H:%M")
            elif group == "daily":
                tst += day_rel
                ts_disp = tst.strftime("%Y-%m-%d")
            elif group == "monthly":
                tst += mon_rel
                ts_disp = tst.strftime("%Y-%m")
            
            ts = tst.strftime("%Y-%m-%d %H:%M:%S")
            fr = freq_dict.get(ts,0)
            time_series.append([ts_disp,fr])

        if rev: time_series.sort(key=lambda x: x[0], reverse=True)  

        if kargs.get('print',self.print): self.cli_table_print([col_name, n_("Frequency")], time_series, output='csv', html_cols=('time','frequency',))

        if kargs.get('plot',self.plot): self.cli_plot(time_series, max, term_width)

        self.results = time_series
        return time_series






    def group_results(self, res_table:list, **kargs):
        """ Creates and prints a tree with results grouped by a column """
        group_by = kargs.get('group') 
        depth = kargs.get('depth',self.config.get('default_depth',5))

        if group_by not in ('category', 'feed', 'flag', 'hourly', 'daily', 'monthly', 'similar'): 
            self.FX.MC.ret_status = cli_msg( (-5, _('Invalid grouping! Must be: %a'), 'category, feed, flag, hourly, daily or monthly') )
            self.results = ()
            return ()

        results_tmp = []
        node_tmp = []
        count = 0

        table = res_table.copy()
        if self.print: table.reverse()

        if group_by in ('category','feed'):
            feed = FeedContainerBasic()
            feeds = self.FX.MC.feeds.copy()
            if self.print: feeds.sort(key=lambda x: coalesce(x[feed.get_index('display_order')],0), reverse=True)

        if group_by == 'category':
            parent_id_ix = self.result.get_index('parent_id')
            for f in feeds:
                if coalesce(f[feed.get_index('is_category')],0) == 1:
                    node_tmp = []
                    count = 0
                    feed.populate(f)
                    for r in table:
                        if r[parent_id_ix] == feed['id']:
                            count += 1
                            node_tmp.append(list(r) + [0,])
                            if count >= depth: break

                    if count > 0:
                        self.result.clear()
                        self.result['title'] = f'{feed.name()} ({count})'
                        self.result['desc'] = f[feed.get_index('subtitle')]
                        self.result['flag_name'] = f[feed.get_index('icon_name')]
                        self.result['feed_id'] = f[feed.get_index('id')]
                        results_tmp.append(self.result.listify() + [1,])
                        results_tmp = results_tmp + node_tmp

        elif group_by == 'feed':
            feed_id_ix = self.result.get_index('feed_id')            
            for f in feeds:
                if coalesce(f[feed.get_index('is_category')],0) != 1:
                    node_tmp = []
                    count = 0
                    feed.populate(f)
                    for r in table:
                        if r[feed_id_ix] == feed['id']:
                            count += 1
                            node_tmp.append(list(r) + [0,])
                            if count >= depth: break

                    if count > 0:
                        self.result.clear()
                        self.result['title'] = f'{feed.name()} ({count})'
                        self.result['desc'] = f[feed.get_index('subtitle')]
                        self.result['flag_name'] = f[feed.get_index('icon_name')]
                        self.result['feed_id'] = f[feed.get_index('id')]
                        results_tmp.append(self.result.listify() + [1,])
                        results_tmp = results_tmp + node_tmp

        elif group_by == 'flag':
            flag_ix = self.result.get_index('flag')
            for f in self.FX.MC.flags.keys():
                node_tmp = []
                count = 0
                for r in table:
                    if r[flag_ix] == f:
                        count += 1
                        node_tmp.append(list(r) + [0,])
                        if count >= depth: break

                if count > 0:
                    self.result.clear()
                    self.result['title'] = f'{self.FX.get_flag_name(f)} ({count})'
                    self.result['desc'] = f'{self.FX.get_flag_desc(f)}'
                    self.result['flag'] = f

                    results_tmp.append(self.result.listify() + [1,])
                    results_tmp = results_tmp + node_tmp






        elif group_by == 'similar':

            matched_ids = []
            tmp_res = []
            ungrouped_tmp = table.copy()

            id_ix = self.result.get_index('id')

            filters = kargs.copy()
            filters['no_weight'] = True
            filters['print'] = False
            filters['group'] = None
            filters['allow_group'] = False
            filters['rank'] = True
            filters['cnt'] = True
            filters['snippets'] = False
            filters['config'] = None

            node_count = 0
            filters['limit'] = int(len(table) / depth)

            for r in ungrouped_tmp:
                if node_count > depth: break
                if r[id_ix] not in matched_ids:
                    count = 0
                    self.result.clear()
                    self.result.populate(r)
                    results_tmp.append(self.result.listify() + [1,])
                    node_count += 1
                    tmp_res = self.find_similar(r[id_ix], **filters)
                    if type(tmp_res) not in (tuple, list): continue
                    for t in tmp_res:
                        if t[id_ix] not in matched_ids and r[id_ix] != t[id_ix]: 
                            count += 1
                            matched_ids.append(t[id_ix])
                            if count >= depth: continue
                            results_tmp.append(list(t) + [0,])
                                




        elif group_by in ('hourly', 'daily', 'monthly'):

            pubdate_ix = self.result.get_index('pubdate')
            timetable = []
            tt_added = []

            dmonth = relativedelta(months=+1)
            dday = relativedelta(days=+1)
            dhour = relativedelta(hours=+1)
            dsecond_minus = relativedelta(seconds=-1)

            for r in table:

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

            if self.print: timetable.sort(key=lambda x: x[2], reverse=False)
            else: timetable.sort(key=lambda x: x[2], reverse=True)

            for t in timetable:
                node_tmp = []
                count = 0
                
                beg = t[0]
                end = t[1]
                ts = t[2]

                for r in table:
                    pubdate = scast(r[pubdate_ix], int, 0)
                    if pubdate >= beg and pubdate <= end:
                        count += 1
                        node_tmp.append(list(r) + [0,])
                        if count >= depth: break
                    
                if count > 0:
                    self.result.clear()
                    self.result['title'] = ts
                    self.result['flag_name'] = 'calendar'
                    self.result['feed_name'] = group_by
                    results_tmp.append(self.result.listify() + [1,])
                    results_tmp = results_tmp + node_tmp


        self.results = results_tmp
        return self.results





#####################################################################
#
#       MISC DISPLAY METHODS
#
#

    def list_feeds(self, **kargs):
        """Utility for listing feeds and categories (for GUI and CLI)"""
        # This tells us if we want a CLI output
        self.reults = []
        feed = SQLContainer('feeds',FEEDS_SQL_TABLE)
        cat = FeedContainerBasic()

        cats = kargs.get('cats',False)

        feeds = self.FX.MC.feeds.copy()
        feeds.sort(key=lambda x: coalesce(x[feed.get_index('display_order')],0), reverse=True)
        
        for f in feeds:
            f = list(f)
            if cats: 
                if coalesce(f[feed.get_index('is_category')],0) == 0: continue
                id = f[feed.get_index('id')]
                count = 0
                for ff in feeds:
                    if ff[feed.get_index('parent_id')] == id and ff[feed.get_index('deleted')] != 1: count += 1
                f.append(count)

            parent_id = coalesce(f[feed.get_index('parent_id')],0)
            if parent_id != 0:
                for ff in feeds:
                    if ff[feed.get_index('id')] == parent_id: 
                        cat.clear()
                        cat.populate(ff)
                        f.append(cat.name())
            
            self.results.append(f)


        if kargs.get("print",self.print):
            if not cats:
                self.cli_table_print(FEEDS_SQL_TABLE_PRINT + (n_("Feedex Category"),), self.results, mask=FEEDS_SHORT_PRINT, number_footnote=_('rergistered channels'),
                            del_col=feed.get_index('deleted'), passwd_col=feed.get_index('passwd'), html_cols=FEEDS_SQL_TABLE + ('parent_category',))
            else:
                self.cli_table_print(FEEDS_SQL_TABLE_PRINT + (n_("No of Children"),), self.results, mask=CATEGORIES_PRINT, number_footnote=_('categories'),
                            del_col=feed.get_index('deleted'), passwd_col=feed.get_index('passwd'), html_cols=FEEDS_SQL_TABLE + ('no_of_children',))

        else: return self.results



    def cat_tree_print(self, **kargs):
        """ Display Feed/Category tree in CLI """
        self.results = []
        feed = SQLContainer('feeds',FEEDS_SQL_TABLE)

        feeds = self.FX.MC.feeds.copy()
        feeds.sort(key=lambda x: x[feed.get_index('display_order')], reverse=True)

        for c in feeds:
            if coalesce(c[feed.get_index('deleted')],0) == 1: continue
            subtable = []
            id = coalesce(c[feed.get_index('id')],0)
            if coalesce(c[feed.get_index('is_category')],0) == 1:
                cat_str = f"""\n\n======================== {id} | {c[feed.get_index('name')]} | {c[feed.get_index('subtitle')]} ===================================="""
                print(cat_str)
                for f in feeds:
                    if coalesce(f[feed.get_index('deleted')],0) == 1: continue
                    if f[feed.get_index('parent_id')] == id: subtable.append(f)
                for f in subtable:
                    feed_str = f"""{f[feed.get_index('id')]} | {f[feed.get_index('name')]} | {f[feed.get_index('title')]} | {f[feed.get_index('subtitle')]} | {f[feed.get_index('url')]} | {f[feed.get_index('link')]} | {f[feed.get_index('handler')]}"""
                    print(feed_str)

        subtable = []
        for f in feeds:
            if coalesce(f[feed.get_index('deleted')],0) == 1: continue
            if coalesce(f[feed.get_index('is_category')],0) == 1: continue
            if f[feed.get_index('parent_id')] is None: subtable.append(f)
        
        for f in subtable:
            feed_str = f"""{f[feed.get_index('id')]} | {f[feed.get_index('name')]} | {f[feed.get_index('title')]} | {f[feed.get_index('subtitle')]} | {f[feed.get_index('url')]} | {f[feed.get_index('link')]} | {f[feed.get_index('handler')]}"""
            print(feed_str)





    def list_flags(self, **kargs):
        """ List all available flags """
        self.results = []
        for f, vals in self.FX.MC.flags.items():
            flag = []
            flag.append(f)
            for v in vals: flag.append(v)
            self.results.append(flag)
 
        if kargs.get("print",self.print): self.cli_table_print(FLAGS_SQL_TABLE_PRINT, self.results, number_footnote='flags', flag_col=0, html_cols=FLAGS_SQL_TABLE) 
        return self.results









    def show_rules(self, **kargs):
        """ Show manually added rules """
        results = kargs.get('results', self.FX.qr_sql("""select * from rules r where coalesce(r.learned,0) = 0""", all=True))
        if self.FX.db_error is not None: return ()

        rule = SQLContainer('rules', RULES_SQL_TABLE_RES, replace_nones=True)
        feed = FeedContainerBasic()

        #String literals - not to do localization in the loop
        l_yes = _('YES')
        l_no = _('NO')
        l_all_fields = _('-- All Fields --')
        l_all_feeds = _('-- All Channels/Categories --')
        l_none = _('<NONE>')
        l_type_0 = _('String Matching')
        l_type_1 = _('Full Text Search')
        l_type_2 = _('REGEX')
        
        self.results.clear()

        for r in results:
            rule.clear()
            rule.populate(r)

            if coalesce(rule['case_insensitive'],0) == 0: rule['case_insensitive'] = l_no
            else: rule['case_insensitive'] = l_yes

            if coalesce(rule['additive'],0) == 0: rule['additive'] = l_no
            else: rule['additive'] = l_yes

            qtype = scast(rule['type'], int ,0)
            if qtype == 0: rule['query_type'] = l_type_0
            elif qtype == 1: rule['query_type'] = l_type_1
            elif qtype == 2: rule['query_type'] = l_type_2
            else: rule['query_type'] = l_none

            if coalesce(rule['learned'],0) == 1: rule['learned'] = l_yes
            else: rule['learned'] = l_no

            flag = coalesce(rule['flag'],0) 
            if flag == 0: rule['flag_name'] = l_none
            else: rule['flag_name'] = self.FX.get_flag_name(flag)

            rule['field_name'] = PREFIXES.get(rule['field_id'],{}).get('name',l_all_fields)

            feed_id = rule['feed_id']
            if feed_id in (None,-1): rule['feed_name'] = l_all_feeds
            else: 
                for f in self.FX.MC.feeds:
                    if feed_id == f[feed.get_index('id')]:
                        feed.populate(f)
                        rule['feed_name'] = feed.name(id=True)
                        break

            self.results.append(rule.tuplify())


        if kargs.get('print', self.print):
            self.cli_table_print(RULES_SQL_TABLE_RES_PRINT, self.results, mask=PRINT_RULES_SHORT, flag_col=rule.get_index('flag'), interline=False, output='short',
                                number_footnote=_('rules'), html_cols=RULES_SQL_TABLE_RES)
        else:
            return self.results






    def show_history(self, **kargs):
        """ Print search history """
        if self.FX.MC.search_history == []: self.FX.load_history()
        self.results = self.FX.MC.search_history

        if kargs.get('print', self.print):
            self.cli_table_print((n_('Search phrase'),n_('Date added'), n_('Date added (raw)'),), self.results, 
                                    mask=(n_('Search phrase'), n_('Date added')), interline=False, output='csv',
                                    html_cols=('search_phrase', 'date_added', 'date_added_raw') )
        else:
            return self.results





    def read_feed(self, id:int, **kargs):
        """ Print out detailed feed data """
        if not self.print: return None
        feed = FeedContainer(self.FX, id=scast(id, int, -1))
        if not feed.exists:
            self.FX.MC.ret_status = cli_msg( (-8, _('Channel/Category %a not found. Aborting...'), id) )
            return -1

        if self.output in ('csv','json','html'):
            feed.get_parent()
            self.cli_table_print(FEEDS_SQL_TABLE + ('parent_category_name',), (feed.tuplify() + (feed.parent_feed.name()),), html_cols=FEEDS_SQL_TABLE + ('parent_category_name',))
        else: print(feed.display())




    def read_entry(self, id:int, **kargs):
        """ Wrapper for displaying an entry """
        if not self.print: return None
        entry = EntryContainer(self.FX, id=scast(id, int, -1))
        if not entry.exists:
            self.FX.MC.ret_status = cli_msg( (-8, _('Entry %a not found. Aborting...'), id) )
            return -1

        if self.debug in (1,8): print(entry.__str__())
        else:
            if self.output in ('json','html','csv'):
                self.cli_table_print( ENTRIES_SQL_TABLE, (entry.tuplify(),), html_cols=ENTRIES_SQL_TABLE)
            else:
                to_disp = entry.display(**kargs)
                if type(to_disp) is str: print(to_disp)
                else:
                    self.FX.MC.ret_status = cli_msg(to_disp)
                    return -1







    def test_regexes(self, feed_id, **kargs):
        """ Display test for HTML parsing REGEXes """
        handler = FeedexHTMLHandler(self.FX)
        feed = FeedContainer(self.FX, replace_nones=True, feed_id=feed_id)
        if not feed.exists: return ()
        handler.set_feed(feed)

        feed_title, feed_pubdate, feed_img, feed_charset, feed_lang, entry_sample, entries = handler.test_download(force=True)

        demo_string = f"""{_('Feed title:')} <b>{esc_mu(feed_title)}</b>
{_('Feed Published Date:')} <b>{feed_pubdate}</b>
{_('Feed Image Link:')} <b>{feed_img}</b>
{_('Feed Character Encoding:')} <b>{feed_charset}</b>
{_('Feed Language Code:')} <b>{feed_lang}</b>
------------------------------------------------------------------------------------------------------------------------------

"""
        for e in entries:

            demo_string = f"""{demo_string}
    ------------------------------------------------------------------
    {_('Title:')} <b>{e.get('title')}</b>
    {_('Link:')} <b>{e.get('link')}</b>
    {_('GUID:')} <b>{e.get('guid')}</b>
    {_('Published:')} <b>{e.get('pubdate')}</b>
    {_('Description:')} <b>{e.get('desc')}</b>
    {_('Category:')} <b>{e.get('category')}</b>
    {_('Author:')} <b>{e.get('author')}</b>
    {_('Additional Text:')} <b>{e.get('text')}</b>
    {_('Image HREFs:')} <b>{e.get('images')}</b>"""

        demo_string = f"""{demo_string}
------------------------------------------------------------------------------------------------------------------------------
<i><b>{_('Entry sample:')}</b></i>
{entry_sample}
"""
        help_print(demo_string)






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
        else: return self.FX.resolve_flag(flag)

 














class FeedexCLI:
    """ CLI Display methods gatherred in one container """


    def __init__(self, Q, **kargs) -> None:
        
        # Parent is Feedex.Query
        self.Q = Q

        self.debug = self.Q.debug
        
        # CLI display options
        self.output = self.Q.output
        self.delim = kargs.get('delimiter','|')
        self.delim2 = kargs.get('delimiter2',';')
        self.delim_escape = kargs.get('delim_escape','\\')
        self.trunc = kargs.get('trunc',200)

        self.snip_beg = kargs.get('bold_beg', self.Q.config.get('BOLD_MARKUP_BEG', BOLD_MARKUP_BEG) )
        self.snip_end = kargs.get('bold_end', self.Q.config.get('BOLD_MARKUP_END', BOLD_MARKUP_END) )

        # HTML output options
        self.html_template = kargs.get('html_template','')
        self.to_files = kargs.get('to_files',False)
        self.to_files_dir = kargs.get('to_files_dir')
        self.to_files_names = kargs.get('to_files_names','<%id%>.html')        







    def cli_table_print(self, columns:list, table, **kargs):
        """ Clean printing of a given table (list of lists) given delimiter, truncation etc.
            Output can be filtered by mask (displayed column list) """

        # First handle JSON and HTML if globals are set...
        if self.output == 'json':
            try:
                json_string = json.dumps(table)
            except (OSError, json.JSONDecodeError, TypeError) as e:
                self.FX.MC.ret_status = cli_msg( (-1, f'{_("Error converting to JSON: %a")}', e) )
                return -1
            print(json_string)
            return 0
        
        elif self.output == 'html':
            html_cols = kargs.get('html_cols',())
            if html_cols != (): 
                err = self.to_html(html_cols, table)
                if err != 0: self.FX.MC.ret_status = cli_msg(err)
                return 0



        # ... only then fallback to preferred output
        output = kargs.get('output', self.output)

        STERM_NORMAL = self.Q.config.get('TERM_NORMAL', TERM_NORMAL)
        STERM_READ = self.Q.config.get('TERM_READ', TERM_READ)
        STERM_DELETED = self.Q.config.get('TERM_DELETED', TERM_DELETED)
        SBOLD_MARKUP_BEG = self.snip_beg
        SBOLD_MARKUP_END = self.snip_end
        STERM_SNIPPET_HIGHLIGHT = self.Q.config.get('TERM_SNIPPET_HIGHLIGHT', TERM_SNIPPET_HIGHLIGHT)


        number_footnote = kargs.get('number_footnote',_('results'))
    
        total_number = kargs.get('total_number', 0)
        total_number_footnote = kargs.get('total_number_footnote', _('entries'))

        sdelim = f" {self.delim} "
        sdelim2 = f" {self.delim2} "
        delim_escape = self.delim_escape
        if delim_escape not in ('', None): delim_escape = f'{delim_escape}{self.delim}'

        if self.debug in (1,8): mask = columns
        else: mask = kargs.get('mask',columns)

        # Colored columns
        read_col = kargs.get('read_col', -1)
        flag_col = kargs.get('flag_col', -1)
        del_col  = kargs.get('del_col', -1)

        # Date column - for nice formatting short dates
        date_col = kargs.get('date_col',-1)
        if date_col != -1 and (not self.debug in (1,5)):
            today = date.today()
            yesterday = today - timedelta(days=1)
            year = today.strftime("%Y")
            year = f'{year}.'
            today = today.strftime("%Y.%m.%d")
            yesterday = yesterday.strftime("%Y.%m.%d")

        # Column containing auth data - to be hidden
        passwd_col = kargs.get('passwd_col', -1)

        # Node columns
        node_col = kargs.get('node_col',-1)
        node_title_col = kargs.get('node_title_col',-1)

        # Print header with columns
        string = ''
        for i in mask:
            if type(i) is int: string = f'{string}{_(scast(columns[i], str, "")).replace(self.delim,delim_escape)}{sdelim}'
            else: string = f'{string}{_(scast(i, str, "")).replace(self.delim,delim_escape)}{sdelim}'
        print(string)

        if output == 'cli': print("\n----------------------------------------------------------------------------------------------------------------------------------------------------------------------------")

        # If entries are empty, then inform
        if table == [] or table is None:
            print("<<< EMPTY >>>")
        

        # ... and finally, entry list
        for entry in table:
            string = ''
            # Set text colors
            if output in ('cli', 'cli_noline','short','headlines'):
                cs_beg=STERM_NORMAL
                cs_end=STERM_NORMAL
                if flag_col != -1: flag_id = scast(slist(entry, flag_col, 0), int, 0)

                if del_col != -1 and scast(slist(entry, del_col, 0), int, 0)  >= 1:
                        cs_end = STERM_NORMAL
                        cs_beg = STERM_DELETED
                elif read_col != -1 and scast(slist(entry, read_col, 0), int, 0)  >= 1:
                        cs_end = STERM_NORMAL
                        cs_beg = STERM_READ
                elif flag_col != -1 and flag_id >= 1:
                        cs_end = STERM_NORMAL
                        cs_beg = TCOLS.get(self.Q.FX.get_flag_color_cli(flag_id),'')

                if node_col != -1:
                    if scast(slist(entry, node_col, 0), int, 0)  == 1:
                        print(f'\n\n========= {scast(slist(entry, node_title_col, None), str, _("<<UNKNOWN>>"))} ===========================\n')
                        continue

            else:
                cs_beg = ''
                cs_end = ''

            for i in mask:
                sdate = False
                spass = False
                if type(i) is not int:
                    tix = columns.index(i)
                    text = slist(entry, tix, '')
                    if tix == passwd_col:
                        spass = True
                    elif tix == date_col:
                        sdate = True
                else:
                    text = slist(entry,i,'')
                    if passwd_col != -1 and i == passwd_col:
                        spass = True
                    if date_col != -1 and i == date_col:
                        sdate = True

                if type(text) in (float, int):
                    text = scast( round(text,4), str, _('<<NUM?>>'))

                elif type(text) in (list, tuple):
                    field_str = ''
                    for s in text:
                        if type(s) is str:
                            field_str = f'{field_str}{sdelim2}{s}'
                        elif type(s) in (list, tuple) and len(s) >= 3:
                            if output  in ('cli', 'cli_noline'):
                                field_str = f'{field_str}{sdelim2}{s[0]}{STERM_SNIPPET_HIGHLIGHT}{s[1]}{cs_beg}{s[2]}'
                            else:
                                field_str = f'{field_str}{sdelim2}{s[0]}{SBOLD_MARKUP_BEG}{s[1]}{SBOLD_MARKUP_END}{s[2]}'

                    if field_str.startswith(sdelim2):
                        field_str = field_str.replace(sdelim2,'',1)

                    text = field_str

                elif text is None:
                    if output in ('cli', 'cli_noline','short','headlines'): text = _('<NONE>')
                    else: text = ''
                else:
                    text = scast(text, str, '')
                    if output in ('cli', 'cli_noline','short','headlines'):
                        if spass:
                            text = '**********'
                        elif sdate and not self.debug in (1,8):
                            text = text.replace(today, _('Today'))
                            text = text.replace(yesterday, _('Yesterday'))
                            text = text.replace(year,'')

                        text = text.replace(SBOLD_MARKUP_BEG, STERM_SNIPPET_HIGHLIGHT).replace(SBOLD_MARKUP_END, cs_beg)

                field = text
            
                # Truncate if needed
                if self.trunc > 0:
                    field = ellipsize(field, self.trunc)
                    field = field.replace("\n",' ').replace("\r",' ').replace("\t",' ')
                    field = f"{field}{cs_beg}"

                # Delimiter needs to be stripped or escaped (for csv printing etc.)
                string = f"{string}{field.replace(self.delim, delim_escape)}{sdelim}"

        
            print(f"{cs_beg}{string}{cs_end}")
            if output == 'cli': print("\n----------------------------------------------------------------------------------------------------------------------------------------------------------------------------")

        if output  in ('cli', 'cli_noline','short','headlines'):
            print(f'{len(table)} {number_footnote}')
            if total_number != 0:
                print(f'{total_number} {total_number_footnote}')






    def cli_plot(self, data_points, max, term_width):
        """ Plots a dataset in a terminal """
        unit = dezeroe(max,1)/term_width

        for dp in data_points:
            x = dp[0]
            y = dp[1]
            length = int(y/unit)
            points = ""
            for l in range(length): points = f"{points}*"
                
            print(x, "|", points, " ", y)







#############################################################################33
#   Exporting to HTML
#

    def htmlize(self, text):
        """ Convert text to html """
        if type(text) in (tuple, list):
            snips = ''
            for s in text:
                if type(s) not in (list,tuple): return ''
                if len(s) != 3: return ''
                snips = f"""{snips}{self.delim2}{self.htmlize(s[0])}{self.snip_beg}{self.htmlize(s[1])}{self.snip_end}{self.htmlize(s[2])}"""
            text = snips
        else:
            text = scast(text, str, '')
        for ent in HTML_ENTITIES_REV: 
            if ent[0] != '': text = text.replace(ent[0],ent[1])
        return text

    def fname(self, text):
        """ Sanitize file name fields """
        if type(text) in (list, tuple): return ''
        text = scast(text, str, '')
        text = text[:50]
        text = text.replace('/','_').replace('"','_').replace("'",'_').replace("""\'""",'_').replace("\n",'_').replace("\r","_").replace(' ','_')
        return text


    def to_html(self, fields:list, table:list, **kargs):
        """ Converts table into a html string from a template """
        #Read template file
        try:
            with open(self.html_template, 'r') as f:
                templ = f.read()
        except OSError:
            return -1, _("Error reading template file %a!"), self.html_template

        if self.to_files:
            if not os.path.isdir(self.to_files_dir): return -1, _("Target directory %a does not exist! Aborting..."), self.to_files_dir


        for row in table:
            text = templ
            for i,f in enumerate(fields):
                text = text.replace(f'<%{f}%>', self.htmlize( slist(row,i,'') ) )
            
            if self.to_files:
                file_name = self.to_files_names
                for i,f in enumerate(fields):
                    file_name = file_name.replace(f'<%{f}%>', self.fname( slist(row,i,'') ) )

                target_file = f'{self.to_files_dir}/{file_name}'
                if os.path.isfile(target_file) or os.path.isfile(target_file):
                    return -1, _("File %a already exists!"), 

                try:
                    with open(target_file, 'w') as ff:
                        ff.write(text)
                except OSError as e:
                    return -1, f'{_("Error writing to file ")}{target_file}: %a', e

            else: print(text)

        return 0

