#!/usr/bin/python3
# -*- coding: utf-8 -*-



from feedex_headers import *








class FeedexLP(SmallSem):
    """ SmallSem and Indexer implementation for Feedex news reader """


    def __init__(self, MC, **kargs) -> None:

        self.MC = MC
        self.models_path = FEEDEX_MODELS_PATH

        # Utilities ...
        self.config = kargs.get('config', DEFAULT_CONFIG)
        self.debug = kargs.get('debug', False)

       # Initialize model headers...
        if self.MC.lings is None:
            self.load_lings()
            self.MC.lings = self.lings.copy()
            self.MC.lings.append(HEURISTIC_MODEL)
        
        self.lings = self.MC.lings
        self.ling = {}

        # Init stats and index strings...        
        self._clear_stats()

        # Strings for indexing
        self.ix_strings = {}
        # String for ranking
        self.rank_string = ''

        # Ranking rules
        self.rules = self.MC.rules

        # Init Xapian index pointer to connect if needed
        self.ix_db = None

        self.raw_text = ''

        self.tokens = []
        self.units = []

        # Dictionary of stemming variants
        self.variants = {}


        
        # Regex string for tokenizing query
        self.REGEX_xap_query = re.compile('''(OR|AND|NOT|XOR|NEAR\d+|~\d+|~|NEAR|<\w+>|[\\\(]|[\\\)]|\(|\)|\"|\'|\w+|\d+|[^\s]+)''')



    def _clear_stats(self):
        self.stats = {
        'word_count' : 0,
        'char_count' : 0,                
        'sent_count' : 0,
        'caps_count' : 0,
        'com_word_count' : 0,
        'polysyl_count' : 0,
        'numerals_count' : 0,
        'weight' : 0,
        'readability' : 0
        }



    def clear(self):
        for k in ('',PREFIXES['exact'],PREFIXES['sem']): self.ix_strings[k] = []
        for k in META_PREFIXES: self.ix_strings[k] = []
        for k in META_PREFIXES_EXACT: self.ix_strings[k] = []
        self.rank_string = ''
        self.variants.clear()
        self._clear_stats()



    def gen_index_strings(self, text:str, **kwargs):
        """ Tokenize with tagging and statistics for indexing. 
                prefix      Provide prefix to add it to tokens
                stem        Should tokens be stemmed? """
        split = kwargs.get('split',False)
        prefix = kwargs.get('prefix','')
        field_offset = kwargs.get('field_offset',0)
        field_len = 0

        if split: raw_tokens = scast(text, str, '').split(' ')
        else: raw_tokens = self._simple_tokenize(scast(text, str, ''))

        ix_token_str = ''
        ix_exact_token_str = ''
        
        # Dictionary of pos lists for semantic stuff
        sems = {} 
        for p in SEM_TERMS: sems[p] = []

        
        # Iterate over all tokens
        for ipos, t in enumerate(raw_tokens):

            tlen = len(t)
            if tlen < 1: continue

            to_rank = False # Flag marking a token for later ranking 

            # Needed to accurately position semantic wildcards
            ipos = field_offset + ipos
            field_len += 1

            tok = ''
            extok = ''

            if t in self.divs:

                tok = t
                extok = tok
                sems[PREFIXES['div']].append(ipos)
                if t in self.sent_end: self.stats['sent_count'] += 1


            elif t in self.punctation:
                tok = t
                extok = tok
                sems[PREFIXES['div']].append(ipos)

            elif self._isnum(t):
                tok = t
                extok = tok
                sems[PREFIXES['num']].append(ipos)
                self.stats['numerals_count'] += 1
                self.stats['word_count'] += 1




            else:
                self.stats['word_count'] += 1

                if self.writing_system == 1: 
                    self.stats['char_count'] += len(t)

                    case = self._case(t)
                    if case > 0:
                        self.stats['caps_count'] += 1
                        if case == 1: sems[PREFIXES['cap']].append(ipos)
                        else: sems[PREFIXES['allcap']].append(ipos)

                    syls = len(self.pyphen.inserted(t).split('-'))
                    if syls >= 3:
                        self.stats['polysyl_count'] += 1
                        sems[PREFIXES['polysyl']].append(ipos)

                    cextok = t
                    t = t.lower()
                    extok = t
                    tok = self.stemmer.stemWord(t)
                    if tok not in self.variants.keys(): self.variants[tok] = []
                    self.variants[tok].append(t)

                    to_rank = True


                elif self.writing_system == 2:
                    syls = 1
                    self.stats['char_count'] += 1
                    case = self.case(t)
                    if case > 0: 
                        self.stats['caps_count'] += 1
                        sems[PREFIXES['cap']].append(ipos)
                    t = t.lower()

                    if t in self.commons:
                        self.stats['com_word_count'] += 1

                    tok = t
                    extok = tok

                    to_rank = True


                if tok in self.commons:
                    self.stats['com_word_count'] += 1
                elif extok in self.stops:
                    self.stats['com_word_count'] += 1
                    to_rank = False
                elif extok in self.swadesh:
                    self.stats['com_word_count'] += 1
                else:
                    sems[PREFIXES['uncomm']].append(ipos)
                
                    # This is a good rule of thumb for 'wild' symbols
                    if syls <= 1:
                        if self._isrnum(extok): sems[PREFIXES['rnum']].append(ipos)
                        elif cextok in UNIT_ENTS: sems[PREFIXES['unit']].append(ipos)
                        elif cextok in CURRENCY_ENTS: sems[PREFIXES['curr']].append(ipos)
                        elif self._contains_item(extok, CURRENCY_SHORT_ENTS): sems[PREFIXES['curr']].append(ipos)
                        elif self._contains_item(extok, GREEK_ENTS): sems[PREFIXES['greek']].append(ipos)
                        elif self._contains_item(extok, MATH_ENTS): sems[PREFIXES['math']].append(ipos)



            ix_token_str = f"""{ix_token_str} {tok}"""
            ix_exact_token_str = f""" {ix_exact_token_str} {extok}"""

            if to_rank: 
                self.rank_string = f'''{self.rank_string}{tok} '''

        return (ix_token_str, ix_exact_token_str, sems, field_len)







    def calculate_stats(self):
        """ Calculates document's statistics """
        if self.stats['word_count'] == 0: 
            self.stats['readability'] = 0
            self.stats['weight'] = 0
            return 0

        if self.writing_system == 0: self.stats['polysyl_count'] = 0

        if self.stats['sent_count'] == 0: self.stats['sent_count'] = 1

        # Calculate readability
        common_freq = self.stats['com_word_count']/self.stats['word_count']
        long_freq = self.stats['polysyl_count']/self.stats['word_count']

        avg_word_len = self.stats['char_count']/self.stats['word_count']
        avg_sent_len = self.stats['word_count']/self.stats['sent_count']

        if self.writing_system == 2: readability = common_freq * 1.25   +  1/avg_sent_len * 0.7
        else: readability = common_freq * 1  +  long_freq * 0.25  +  1/avg_word_len * 0.50   +   1/avg_sent_len * 0.25                             
        self.stats['readability'] = readability * 100

        # Calculate document weight (smaller with word count adjusted by uncommon words)
        # Needed to decrease rankings for very long documents
        self.stats['weight'] = 1/log10(coalesce(self.stats['com_word_count'],0)+2)




    
    
    
    



    def index(self, entry, **kargs):
        """ Generate indexing strings for all relevant fields of a given entry and calculate stats """        
        
        self.clear()
        field_offset = 0
        for f in LING_TEXT_LIST:
            # Incrementally generate strings ...
            prefix = PREFIXES[f]['prefix']
            ex_prefix = f"""{prefix}{PREFIXES['exact']}"""
            split = PREFIXES[f]['meta']
            weight = PREFIXES[f]['weight']

            token_str, exact_token_str, sems, field_len = self.gen_index_strings(entry[f], split=split, prefix=prefix, field_offset=field_offset)
            field_offset += field_len

            self.ix_strings[''].append( (weight, token_str) )
            self.ix_strings[PREFIXES['exact']].append( (weight, exact_token_str) )
            self.ix_strings[PREFIXES['sem']].append( (weight, sems) )

            if prefix != '':
                self.ix_strings[prefix].append( (weight, token_str) )
                self.ix_strings[ex_prefix].append( (weight, exact_token_str) )

        return self.ix_strings, self.rank_string
        





    def validate_rules(self): 
        """ This routine validates all rules once to ensure one does not have to do it every time later """
        if self.MC.rules_validated: return 0

        if self.debug in (1,4): print('Validating rules...')
        remember_lang = self.get_model()

        if type(self.MC.rules) is not list: self.MC.rules = list(self.MC.rules)
        for i,r in enumerate(self.MC.rules):
            # Stem and prefix all user's FTS rules
            qtype = scast(r[2], int, 0)
            learned = scast(r[10], int, 0) 
            string = scast(r[5], str, '')
            field = scast(r[4], str, None)

            if learned != 1:
                if qtype == 1:
                    self.set_model(r[7])
                    phrase = self.build_phrase(string, str_match_stem=True, sql=False)
                    string = phrase['str_match_stem']

                elif qtype == 0:
                    if r[6] == 1: case_ins = True
                    else: case_ins = False
                    phrase = self.build_phrase(string, str_match=True, sql=False, case_ins=case_ins)
                    string = phrase.copy()

                elif qtype == 2:
                    if r[6] == 1: case_ins = True
                    else: case_ins = False
                    if case_ins: re.compile(string, re.IGNORECASE)
                    else: re.compile(string)
            
            else:
                string = f' {string} '

            # Validate data types ...
            self.rules[i] = (
                r[0], 
                r[1],
                qtype, 
                scast(r[3], int, -1),
                field,
                string,
                scast(r[6], int, 0),
                r[7],
                scast(r[8], float, 0),
                scast(r[9], int, 1),
                learned,
                scast(r[11], int, 0),
                scast(r[12], int, 0),               
            )

        self.set_model(remember_lang)
        
        self.MC.rules_validated = True
        if self.debug in (1,4): print('Rules validated...')









    def rank(self, entry, ranking_token_str:str, **kargs):
        """ Match rules for entry """
        to_var = kargs.get('to_var',False)
        if to_var:
            display_list = []
            rule = SQLContainer('rules', RULES_SQL_TABLE_RES, replace_nones=True)   

        importance = 0
        flag = 0

        flag_freq_dist = {}
        context_freq_dist = {}

        self.validate_rules()

        for r in self.rules:
            name    = r[1]
            qtype   = r[2]
            feed    = r[3]
            if feed is not None and feed != -1 and entry['feed_id'] != feed: continue

            field   = r[4]
            string  = r[5]
            if type(string) is str and len(string) < 1: continue

            if r[6] == 1: case_ins = True
            else: case_ins = False

            lang = r[7]
            if lang is not None and lang != self.get_model(): continue

            rweight     = r[8]
            additive    = r[9]
            learned     = r[10]
            rflag       = r[11]
            context_id  = r[12]

            if learned == 1:
                matched = ranking_token_str.count(string)

            elif qtype == 1:
                matched = ranking_token_str.count(string)

            elif qtype in (0,2):
                if field in (None, -1): field_lst = LING_TEXT_LIST
                else: field_lst = (field,)


                if qtype == 2:

                    matched = 0
                    for f in field_lst:
                        if type(entry[f]) is not str: continue

                        if case_ins: matches = re.findall(string, entry[f], re.IGNORECASE)
                        else: matches = re.findall(string, entry[f])
                        matched += len(matches)


                elif qtype == 0:

                    matched = 0
                    for f in field_lst:
                        if type(entry[f]) is not str: continue
                        f = entry[f]
                        if case_ins: fs = f.lower()
                        else: fs = f

                        new_matched = self.str_matcher(string['spl_string'], string['spl_string_len'], string['beg'], string['end'], fs, snippets=False)[0]
                        matched += new_matched




            if matched > 0:

                if additive == 1: context_freq_dist[context_id] = context_freq_dist.get(context_id,0) + (matched * rweight)
                else: context_freq_dist[context_id] = matched * rweight

                if learned != 1 and rflag > 0: flag_freq_dist[rflag] = flag_freq_dist.get(rflag,0) + (rweight * matched)

                # Create list for display
                if to_var: 
                    rule.clear()
                    rule['learned'] = learned
                    rule['case_insensitive'] = case_ins
                    rule['additive'] = additive
                    
                    if learned == 1: rule['string'] = str(string)
                    elif qtype == 0: rule['string'] = string['raw']
                    elif qtype == 1: rule['string'] = string
                    elif qtype == 2: rule['string'] = str(string)
                    else: str(string)

                    rule['name'] = name
                    rule['matched'] = matched
                    rule['type'] = qtype
                    rule['field_id'] = field
                    rule['feed_id'] = feed
                    rule['flag'] = rflag
                    rule['lang'] = lang
                    rule['weight'] = rweight
                    rule['context_id'] = context_id

                    display_list.append( rule.tuplify() )

        importance = context_freq_dist.get(0,0)

        context_freq_dist[0] = 0
        context_freq_dist[entry['id']] = 0

        contexts_sorted = sorted(context_freq_dist.items(), key=lambda x:abs(x[1]), reverse=True)
        
        best_contexts = []
        
        for i,cx in enumerate(contexts_sorted):
            if i > MAX_RANKING_DEPTH: break
            importance = importance + cx[1]
            best_contexts.append(cx[0])

        importance = importance * entry['weight']
        
        if flag_freq_dist != {}: flag = max(flag_freq_dist, key=flag_freq_dist.get)

        if to_var: return importance, flag, best_contexts, flag_freq_dist, display_list
        else: return importance, flag
             









    def get_bed_end(self, string):
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







    def build_phrase(self, string, **kargs):
        """ Check if string is marked with beginning and end regex markers """
        case_ins = kargs.get('case_ins',False)
        stem = kargs.get('stem',False)
        field = kargs.get('field')

        phrase = {}

        beg = False
        end = False

        raw = string

        if kargs.get('str_match', False):       

            beg, end, string = self.get_bed_end(string)
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
            for t in self._str_match_split(string):
                if type(t) is str: t = t.replace(rstr,'*')
                spl_string.append(t)

            return {'empty':False, 'beg':beg, 'end':end, 'sql':sql, 'fts': None, 'spl_string':spl_string, 'spl_string_len':len(spl_string), 'has_wc':has_wc, 'raw':raw}






        # This is only for splitting into tokens and stemming for simple learned rule search
        elif kargs.get('str_match_stem', False):

            beg, end, string = self.get_bed_end(string)

            if string.replace(' ','').replace('*','') == '': 
                return {'empty':True, 'beg':False, 'end':False, 'sql':None, 'fts': '', 'spl_string':[], 'spl_string_len':0, 'has_wc':has_wc}

            toks = ''
            for t in self._simple_tokenize(string):
                t = self.stemmer.stemWord(t.lower())
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
                if t in ('AND','OR','NEAR','(',')','~'): pass
                elif t.startswith('~') and t.replace('~','').isdigit(): pass
                elif t.startswith('<') and t.endswith('>'):
                    tt = t.replace('<','').replace('>','')
                    if tt in SEM_TERMS: 
                        empty = False
                        t = f"""{PREFIXES['sem']}:{tt.lower()}"""
                else: 
                    empty = False
                    prefix = fprefix
                    if self._case(t) == 0: t = self.stemmer.stemWord(t)
                    else: prefix = f"""{prefix}{PREFIXES['exact']}""" 
                    if prefix != '': t = f'''{prefix}:{t.lower()}'''
                    else: t = t.lower()
                toks = f'{toks} {t}'

            if toks != '': toks = toks.lstrip()

            if empty: raw = None
            return {'empty':empty, 'beg':beg, 'end':end, 'sql':None, 'fts': toks, 'spl_string':[], 'spl_string_len':0, 'has_wc':False, 'raw':raw}













    def _str_match_split(self, string):
        """ A crude routine to match patterns in a list of string """
        sm = []
        for s in string.split('*'):
            if s in ('',None): 
                sm.append(1)
                continue
            for ss in s.split('*'):
                if ss in ('',None): 
                    sm.append(1)
                    continue
                sm.append(ss)
                sm.append(1)
            if sm[-1] == 1: del sm[-1]
            sm.append(0)
        if sm[-1] == 0: del sm[-1]
        return sm





    
    def str_matcher(self, string:list, ls:int, beg:bool, end:bool, field:str, **kargs):
        """ Simply matches string and extracts snippets if needed """
        snippets = kargs.get('snippets',True)
        orig_field = kargs.get('orig_field', field)

        field = field.replace('\n',' ').replace('\r',' ')
        orig_field = orig_field.replace('\n',' ').replace('\r',' ')

        snips = []
        matches = 0
        fl = len(field)

        idx = 0
        abs_idx = 0
        tmp_field = field
        
        snip_start = 0
        snip_end = 0
        stop = False
        one_plus = False
        matched = False
        
        start_wc = False
        start_wc_seq = 0

        i = 0
        while not stop:
            matched = False
            s = string[i]
            if s == 0:
                one_plus = False
                if i == ls-1:
                    if not end: matched = True
                    i = 0
                else: i += 1


            elif type(s) is int:
                if s > 0:
                    if i == 0: start_wc = True
                    if start_wc: start_wc_seq += s
                    else: 
                        tmp_field = tmp_field[s:]
                        abs_idx += s
                        one_plus = True
                    
                    if i == ls-1:
                        if end and len(tmp_field) == 0:
                            matched = True
                        elif beg:
                            matched = True
                            stop = True
                        elif not end: matched = True
                        start_wc = False
                        start_wc_seq = 0
                        i = 0
                    else: i += 1

            else:
                if one_plus:
                    if tmp_field.startswith(s): idx = 0
                    else: idx = -1
                else:
                    idx = tmp_field.find(s)

                one_plus = False               
                if idx != -1:
                    l = len(s)
                    abs_idx += idx

                    if i == 0: snip_start = abs_idx
                    elif start_wc:
                        snip_start = abs_idx - start_wc_seq
                        start_wc = False
                        start_wc_seq = 0

                    abs_idx += l
                    tmp_field = tmp_field[idx+l:]

                    if i == ls-1: 
                        i = 0
                        if end and len(tmp_field) == 0: matched = True
                        elif beg:
                            matched = True
                            stop = True
                        elif not end: matched = True
                    else: i += 1

                else:
                    if i == 0: stop = True
                    else: i = 0

            if matched:
                snip_end = abs_idx
                if (beg and snip_start == 0) or not beg:
                    if snippets and matches <= MAX_SNIPPET_COUNT: snips.append( self.srange(orig_field, snip_start, snip_end-snip_start, fl, 70) )
                    matches += 1

            if tmp_field == '': stop = True
            if start_wc_seq >= fl: stop = True 
                    
        return matches, snips








    def srange(self, string:str, idx:int, l:int, sl:int, rng:int):
        """ Get range from string - for extracting snippets"""
        string=string.replace(BOLD_MARKUP_BEG,'').replace(BOLD_MARKUP_END,'').replace('\n','').replace('\r','')

        llimit = idx - rng
        if llimit < 0:
            llimit = 0
        if llimit > 0:
            beg = '...'
        else:
            beg = ''

        rlimit = idx + l + rng
        if rlimit > sl:
            rlimit = sl
        if rlimit < sl:
            end = '...'
        else:
            end = ''
    
        return f'{beg}{string[llimit:idx]}', f'{string[idx:idx+l]}', f'{string[idx+l:rlimit]}{end}'


    #######################################################################33
    #   Utilities
    #

    def _sqlize(self, string:str, **kargs):
        """ Escapes SQL wildcards """
        #   sql = string.replace('\\', '\\\\')
        sql = string.replace('%', '\%')
        sql = sql.replace('_', '\_')
        return sql


    def _isrnum(self, string, **kargs):
        """ Checks if a string i  roman numeral """
        tmp_str = string
        for n in RNUM_ENTS:
            tmp_str = tmp_str.replace(n,'')
        if tmp_str == '': return True
        else: return False


    def _contains_item(self, string, lst, **kargs):
        """ Check if string contains any list item """
        for i in lst:
            if i in string: return True
        return False