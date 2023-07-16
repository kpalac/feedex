# -*- coding: utf-8 -*-
""" Container classes for Feedex """


from feedex_headers import *






class SQLContainer:
    """ Container class for SQL table. It helps to cleanly interface with SQL, output SQL statements 
        and keep data tidy. Lifts the burden of dealing with long lists with only indices as indicators,
        creates structure with named fields instead """

    def __init__(self, table:str, fields:list, **kargs):
        self.vals = {}
        self.fields = fields
        self.table = table
        self.clear()
        self.length = len(fields)

        self.replace_nones = kargs.get('replace_nones',False)
        
        self.col_names = kargs.get('col_names', ()) # Column names for print
        self.types = kargs.get('types', ()) # Field types for validation



    def clear(self):
        """ Clear data """
        for f in self.fields: self.vals[f] = None

    def copy(self):
        """ Return a copy of value dict """
        odict = {}
        for k,v in self.vals.items(): 
            if v is not None: odict[k] = v
        return odict

    def populate(self, ilist:list, **kargs):
        """ Populate container with a list (e.g. query result where fields are ordered as in DB (select * ...) """
        if not isinstance(ilist, (list, tuple)): return -1
        self.clear()
        for i,e in enumerate(ilist):
            if (kargs.get('safe', False) and i >= self.length): break
            self.vals[self.fields[i]] = e
    
    def merge(self, idict:dict):
        """ Merge a dictionary into container. Input dict keys must exist within this class """
        for k,v in idict.items(): self.vals[k] = v

    def strict_merge(self, idict:dict):
        """ Merges only fields present in the container """
        for k,v in idict.items():
            if k in self.vals.keys(): self.vals[k] = v


    def __getitem__(self, key:str):
        if isinstance(key, str): return self.vals.get(key)
        else: raise FeedexTypeError(_('Field name of an SQL container must be a str!'))

    def get(self, key:str, *args):
        """ Get item from value table, optional param.: default value """
        if len(args) >= 1: default = args[0]
        else: default = None
        val = self.vals.get(key, default)
        if self.replace_nones and val is None: val = default
        return val



    def get_index(self, field:str):
        """ Get field index - useful for processing SQL result lists without populating the class """
        try: return self.fields.index(field)
        except ValueError as e: return -1

    def index(self, field:str): return self.get_index(field)



    def __setitem__(self, key:str, value):
        if key in self.fields: self.vals[key] = value

    def __delitem__(self, key:str):
        if key in self.fields: self.vals[key] = None


    def pop(self, field:str):
        if field in self.vals.keys(): self.vals.pop(field)

    def clean(self): # Pop all undeclared fields
        keys = tuple(self.vals.keys())
        for f in keys:
            if f not in self.fields:
                self.vals.pop(f)

    def __str__(self):
        ostring = ''
        for f in self.fields:
            ostring = f"{ostring}\n{f}: {self.vals[f]}"
        return ostring


    def __len__(self):
        olen = 0
        for f in self.vals.keys():
            if self.vals.get(f) is not None: olen += 1
        
        return olen


    def insert_sql(self, **kargs):
        """ Build SQL insert statement based on all or non-Null fields """
        cols = ''
        vs = ''
        for f in self.fields:
            if kargs.get('all',False) or self.vals.get(f) is not None :
                vs = f'{vs}, :{f}'
                cols = f'{cols}, {f}'

        return f'insert into {self.table} ({cols[1:]}) values ( {vs[1:]} )'



    def update_sql(self, **kargs):
        """ Build SQL update statement with all or selected (by filter) fields """
        sets = 'set '
        filter = kargs.get('filter')
        if filter is not None: do_filter = True
        else: do_filter = False

        for f in self.fields:
            if (not do_filter and self.vals.get(f) is not None) or (do_filter and f in filter):
                sets = f'{sets}{f} = :{f},'

        return f'update {self.table} {sets[:-1]} where {kargs.get("wheres","")}'





    def filter(self, filter:list, **kargs):
        """ Returns filtered dictionary of values"""
        odict = {}
        if not isinstance(filter, (list, tuple)): raise FeedexTypeError(_('Filter must be a list or a tuple!'))
        for f in filter: odict[f] = self.vals[f]
        return odict

    
    def listify(self, **kargs):
        """ Return a sublist of fields specified by input field (key) list """
        filter = kargs.get('filter')
        if filter is None: filter = self.fields
        olist = []

        if kargs.get('in_order',True):
            for f in filter:
                if f in self.fields:
                    olist.append(self.vals[f])
        else:
            for f in self.fields:
                if f in filter:
                    olist.append(self.vals[f])
        return olist


    def tuplify(self, **kargs):
        """ Return a subtuple of fields specified by input field (key) list """
        return tuple(self.listify(in_order=kargs.get('in_order',True), filter=kargs.get('filter')))

    def name(self, **kargs):
        """ Return a nice name """
        with_id = kargs.get('with_id',False)
        name = coalesce(
        nullif(self.vals.get('name'),''),
        nullif(self.vals.get('title'),''),
        nullif(self.vals.get('url'),''),
        nullif(self.vals.get('string'),''),
        )
        if name in ('',None): name = str(self.vals.get('id','<???>'))
        else:
            name = ellipsize(name, 200)
            if with_id: name = f"""{name} ({self.vals.get('id','<???>')})"""
        return name
    
    def iscomp(self, item, **kargs):
        """ Checks object compatibility """
        if not isinstance(item, SQLContainer): return False
        if type(item) is dict: fields = item.keys()
        else: fields = item.fields

        for i,f in enumerate(self.fields):
            if fields[i] != f: return False
        return True

    def convert(self, cls, *args, **kargs):
        """ Return copy of object in subclass """
        new = cls(*args, **kargs)
        new.replace_nones = self.replace_nones
        new.strict_merge(self.vals)
        return new







class SQLContainerEditable(SQLContainer):
    """ Container with type validation and update queue """

    def __init__(self, table:str, fields:list, **kargs):

        SQLContainer.__init__(self, table, fields, **kargs)

        self.DB = None #DB connection
        if kargs.get('db') is not None: self.set_interface(kargs.get('db'))

        self.to_update_sql = '' # Update command 
        self.to_update = [] # List of fields to be updated (names only, for values are in main dictionary)

        self.backup_vals = self.vals # Backup for faulty update

        self.exists = False # Was entity found in DB?
        self.updating = False # is update pending?

        self.immutable = () # Immutable field



    def set_interface(self, interface): 
        self.DB = interface
        self.config = self.DB.config


    def validate_types(self, **kargs):
        """ Validate field's type with given template """
        for f, v in self.vals.items():
            if v is not None and f in self.fields:
                vv = scast(v, self.types[self.get_index(f)], None)
                if vv is None: return f
                self.vals[f] = vv
                
        return 0


    def backup(self): self.backup_vals = self.vals.copy()
    def restore(self): self.vals = self.backup_vals.copy()


    def add_to_update(self, idict:dict, **kargs):
        """ Merge update queue with existing field values"""
        self.to_update.clear()
        self.backup()

        allow_id = kargs.get('allow_id',False)

        for f, v in idict.items():

            if (f == 'id' and not allow_id) or f in self.immutable: 
                self.updating = False
                self.restore()
                return msg(FX_ERROR_VAL, _('Editting field %a is not permitted!'), f)

            if v in ('NULL','NONE'): self.vals[f] = None
            else: self.vals[f] = v
            self.updating = True

        if self.updating: return 0
        else: return msg(_('Nothing to do'))


    def constr_update(self, **kargs):
        """ Consolidates updates list """
        allow_id = kargs.get('allow_id',False)
        wheres = kargs.get('wheres','id = :id')

        self.to_update.clear()
        for u in self.fields:
            if u == 'id' and not allow_id: continue
            if self.vals[u] != self.backup_vals.get(u): self.to_update.append(u)
        if len(self.to_update) == 0: return msg(_('No changes detected'))

        self.to_update_sql = self.update_sql(filter=self.to_update, wheres=wheres)
        self.to_update.append('id')

        return 0









class ResultEntry(SQLContainer):
    """ Container for search results (standard entries)"""
    def __init__(self, **kargs):
        SQLContainer.__init__(self,'entries', RESULTS_SQL_TABLE, types=RESULTS_SQL_TYPES, col_names=RESULTS_SQL_TABLE_PRINT, **kargs)

    def humanize(self):
        """ Prepare contents for nice output """
        if coalesce(self.vals['read'],0) > 0: self.vals['sread'] = _('Yes')
        else: self.vals['sread'] = _('No')

        if self.vals['note'] == 1: self.vals['snote'] = _('Yes')
        else: self.vals['snote'] = _('No')

    def fill(self):
        """ Fill in missing data """
        f = fdx.find_f_o_c(self.vals['feed_id'], load=True)
        feed = ResultFeed()
        if f != -1: feed.populate(f)
        else: return -1
        
        if coalesce(feed['deleted'],0) > 0: self.vals['is_deleted'] = 1
        else: self.vals['is_deleted'] = self.vals['deleted']
        self.vals['feed_name'] = feed.name()
        self.vals['feed_name_id'] = f"""{self.vals['feed_name']} ({feed['id']})"""
        self.vals['pubdate_r'] = datetime.fromtimestamp(self.vals.get('pubdate',0))
        self.vals['pubdate_short'] = datetime.strftime(self.vals['pubdate_r'], '%Y.%m.%d')
        if coalesce(self.vals['flag'],0) > 0: self.vals['flag_name'] = fdx.get_flag_name(coalesce(self.vals['flag'],0))
        self.vals['user_agent'] = feed['user_agent']
        self.vals['parent_id'] = feed['parent_id']
        self.vals['parent_name'] = fdx.get_feed_name(feed['parent_id'])




class ResultContext(SQLContainer):
    """ Container for search results (term in context)"""
    def __init__(self, **kargs):
        SQLContainer.__init__(self,'contexts', CONTEXTS_TABLE, types=CONTEXTS_TYPES, col_names=CONTEXTS_TABLE_PRINT, **kargs)

    def humanize(self):
        """ Prepare contents for nice output """
        if coalesce(self.vals['read'],0) > 0: self.vals['sread'] = _('Yes')
        else: self.vals['sread'] = _('No')

        if self.vals['note'] == 1: self.vals['snote'] = _('Yes')
        else: self.vals['snote'] = _('No')



class ResultRule(SQLContainer):
    """ Container for search results (rules)"""
    def __init__(self, **kargs):
        SQLContainer.__init__(self,'rules', RULES_SQL_TABLE_RES, types=RULES_SQL_TYPES_RES, col_names=RULES_SQL_TABLE_RES_PRINT, **kargs)

    def humanize(self):
        """ Make field values more human-readable for display """
        if coalesce(self.vals['case_insensitive'],0) == 0: self.vals['scase_insensitive'] = _('No')
        else: self.vals['scase_insensitive'] = _('Yes')

        if coalesce(self.vals['additive'],0) == 0: self.vals['sadditive'] = _('No')
        else: self.vals['sadditive'] = _('Yes')

        qtype = scast(self.vals['type'], int ,0)
        if qtype == 0: self.vals['query_type'] = _('String Matching')
        elif qtype == 1: self.vals['query_type'] = _('Stemmed Phrase Search')
        elif qtype == 2: self.vals['query_type'] = _('REGEX')
        else: self.vals['query_type'] = '<N/A>'

        if coalesce(self.vals['learned'],0) == 1: self.vals['slearned'] = _('Yes')
        else: self.vals['slearned'] = _('No')

        flag = coalesce(self.vals['flag'],0) 
        if flag == 0: self.vals['flag_name'] = _('-- None --')
        else: self.vals['flag_name'] = fdx.get_flag_name(flag)

        self.vals['field_name'] = PREFIXES.get(self.vals['field_id'],{}).get('name',_('-- All Fields --'))

        feed_id = self.vals['feed_id']
        if feed_id in (None,-1): self.vals['feed_name'] = _('-- All Channels/Catgs. --')
        else: self.vals['feed_name'] = fdx.get_feed_name(self.vals['feed_id'], with_id=True)

    def fill(self): pass





class ResultFeed(SQLContainer):
    """ Container for search results (feed/category)"""
    def __init__(self, **kargs):
        SQLContainer.__init__(self,'feeds', FEEDS_SQL_TABLE_RES, types=FEEDS_SQL_TYPES_RES, col_names=FEEDS_SQL_TABLE_RES_PRINT, **kargs)

    def humanize(self):
        if self.vals['parent_id'] is not None: self.vals['parent_category_name'] = fdx.get_feed_name(self.vals['parent_id'], with_id=True)
        if coalesce(self.vals['deleted'],0) >= 1: self.vals['sdeleted'] = _('Yes')
        else: self.vals['sdeleted'] = _('No')

        if coalesce(self.vals['autoupdate'],0) >= 1: self.vals['sautoupdate'] = _('Yes')
        else: self.vals['sautoupdate'] = _('No')

    def fill(self): pass




class ResultFlag(SQLContainer):
    """ Container for search results (flag)"""
    def __init__(self, **kargs):
        SQLContainer.__init__(self,'flags', FLAGS_SQL_TABLE, types=FLAGS_SQL_TYPES, col_names=FLAGS_SQL_TABLE_PRINT, **kargs)
    def humanize(self): pass
    def fill(self): pass

class ResultTerm(SQLContainer):
    """ Container for search results (term)"""
    def __init__(self, **kargs):
        SQLContainer.__init__(self,'terms', TERMS_TABLE, types=TERMS_TYPES, col_names=TERMS_TABLE_PRINT, **kargs)
    def humanize(self, *args, **kargs): pass
    def fill(self): pass


class ResultTimeSeries(SQLContainer):
    """ Container for search results (time series)"""
    def __init__(self, **kargs):
        SQLContainer.__init__(self,'time_series', TS_TABLE, types=TS_TYPES, col_names=TS_TABLE_PRINT, **kargs)
    def humanize(self, *args, **kargs): pass
    def fill(self): pass


class ResultHistoryItem(SQLContainer):
    """ Container for search result (history item)"""
    def __init__(self, **kargs):
        SQLContainer.__init__(self,'history', HISTORY_SQL_TABLE, types=HISTORY_SQL_TYPES, col_names=HISTORY_SQL_TABLE_PRINT, **kargs)
    def humanize(self, *args, **kargs): pass
    def fill(self): pass









class FeedexHistoryItem(SQLContainerEditable):
    """ Basic container for Feeds - in case no DB interface is needed """
    def __init__(self, db, **kargs):
        SQLContainerEditable.__init__(self, 'search_history', HISTORY_SQL_TABLE, types=HISTORY_SQL_TYPES, col_names = HISTORY_SQL_TABLE_PRINT, **kargs)
        self.set_interface(db)
        self.DB.cache_history()
        self.DB.cache_feeds()
    

    def validate(self, **kargs):
        err_fld = self.validate_types()
        if err_fld != 0: return -7, _('Invalid type for field %a'), err_fld

        if self.vals['feed_id'] is not None:
            feed_id = fdx.find_f_o_c(self.vals.get('feed_id'))
            if feed_id == -1: return -7, _('Channel/Category %a not found!'), self.vals.get('feed_id')
        return 0


    def add(self, phrase:dict, feed:int, **kargs):
        """ Wrapper for adding item to search history """
        if self.config.get('no_history', False): return 0
        
        self.vals['id'] = None

        string = nullif(scast(phrase.get('raw'), str, '').strip(), '')

        if not phrase.get('empty',False) and (string is not None):
            self.vals['string'] = string
            self.vals['feed_id'] = None

        elif feed is not None:
            self.vals['string'] = None
            self.vals['feed_id'] = feed
        
        else: return 0

        now = datetime.now()
        now_raw = int(now.timestamp())
        now_str = now.strftime("%Y.%m.%d %H:%M:%S")
        
        
        self.vals['date'] = now_raw

        if kargs.get('validate', True):
            err = self.validate()
            if err != 0: return msg(*err)

        err = self.DB.run_sql_lock(self.insert_sql(all=True), self.vals)
        if err != 0: return err
        self.DB.last_history_id = self.DB.lastrowid

        # Add to local container to avoid querying database
        for i, h in enumerate(fdx.search_history_cache):
            if h[0] == string: del fdx.search_history_cache[i]
        fdx.search_history_cache = [(string, now_str ,now_raw)] + fdx.search_history_cache
        return 0









class FeedexFlag(SQLContainerEditable):
    """ Container for Flags """

    def __init__(self, db, **kargs):
        SQLContainerEditable.__init__(self, 'flags', FLAGS_SQL_TABLE, types=FLAGS_SQL_TYPES, col_names = FLAGS_SQL_TABLE_PRINT, **kargs)
        self.set_interface(db)
        self.DB.cache_flags()        
        if kargs.get('id') is not None: self.get_by_id(kargs.get('id'))


    def get_by_id(self, id:int):
        content = self.DB.qr_sql("select * from flags where id = :id", {'id':id}, one=True )
        if content in (None, (None,), ()):
            self.exists = False
            return msg(FX_ERROR_NOT_FOUND, _('Flag %a not found!'), id)
        else:
            self.exists = True
            self.populate(content)
            return 0



    def validate(self, **kargs):
        """ Validate current values """
        err = self.validate_types()
        if err != 0: return -7, _('Invalid data type for %a'), err

        if self.vals['id'] in fdx.flags_cache.keys() and self.vals['id'] != self.backup_vals['id']: return -7, _('ID taken by another flag')
        if self.vals['name'] is None or self.vals['name'] == '': return -7, _('Flag name cannot be empty!')
        if self.vals['color_cli'] is not None and self.vals['color_cli'] not in TCOLS.keys(): return -7, _('Invalid CLI color name!')

        return 0




    def do_update(self, **kargs):
        """ Apply edit changes to DB """
        if not self.updating: return 0, _('Nothing to do')
        if not self.exists: return -8, _('Flag %a not found!'), id

        if kargs.get('validate', True): 
            err = self.validate()
            if err != 0:
                self.restore()
                return msg(*err)

        err = self.constr_update(allow_id=True, wheres='id = :old_id')
        if err != 0:
            self.restore()
            return err

        # This is needed because Flags can have their IDs changed ...
        to_update_filtered = self.filter(self.to_update)
        to_update_filtered['old_id'] = self.backup_vals['id']

        err = self.DB.run_sql_lock(self.to_update_sql, to_update_filtered)
        if err != 0:
            self.restore()
            return err


        if self.DB.rowcount > 0:

            if not fdx.single_run:
                err = self.DB.load_flags()
                if err != 0: return msg(FX_ERROR_DB, _('Error reloading flags after successfull update!'))
            
            for i,u in enumerate(self.to_update):
                if u in self.immutable: del self.to_update[i]

            if len(self.to_update) > 1: return msg(_('Flag %a updated successfuly!'), self.name(), log=True)
            else:
                for f in self.to_update:
                    if f == 'id':
                        return msg(f'{_("Flag %a: ID changed from")} {self.backup_vals.get("id",_("<???>"))} {_("to")} {self.vals.get("id",_("<???>"))}', self.name(), log=True)
                    else:
                        return msg(f'{_("Flag %a updated")}:  {f} -> {self.vals.get(f,_("<NULL>"))}', self.name(), log=True)
            
            return msg(_('Nothing done'))

        else:
            return msg(_('Nothing done'))




    def update(self, idict, **kargs):
        """ Quick update with a value dictionary"""
        if not self.exists: return -8
        err = self.add_to_update(idict, allow_id=True)
        if err == 0: err = self.do_update(validate=True)
        return err



    def delete(self, **kargs):
        """ Delete flag by ID """
        if not self.exists: return msg(FX_ERROR_NOT_FOUND, _('Flag %a not found!'), id)

        err = self.DB.run_sql_lock("delete from flags where id = :id", {'id':self.vals['id']} )
        if err != 0: return err
        
        if self.DB.rowcount > 0: 
            if not fdx.single_run: 
                err = self.DB.load_flags()
                if err != 0: return msg(FX_ERROR_DB, _('Error reloading flags after successfull delete!'))

            return msg(_('Flag %a deleted'), self.vals['id'], log=True)

        else: return msg(_('Nothing done.'))





    def add(self, **kargs):
        """ Add flag to database """
        idict = kargs.get('new')
        if idict is not None:
            self.clear()
            self.merge(idict)
        
        if kargs.get('validate',True):
            err = self.validate()
            if err != 0: return msg(*err)

        self.vals['learned'] = 0

        self.clean()
        err = self.DB.run_sql_lock(self.insert_sql(all=True), self.vals)
        if err != 0: return err
        
        self.vals['id'] = self.DB.lastrowid
        self.DB.last_rule_id = self.vals['id']

        if not fdx.single_run: 
            err = self.DB.load_flags()
            if err != 0: return msg(FX_ERROR_DB, _('Error reloading flags after successfull add!'))

        return msg(_('Flag %a added successfully'), self.name(with_id=True), log=True)
    










