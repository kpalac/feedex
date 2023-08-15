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
        self.entity = kargs.get('entity')


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
            if k in self.fields: self.vals[k] = v


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
        new.entity = self.entity
        new.strict_merge(self.vals)
        return new


    def validate_fields(self, **kargs):
        """ Validate field's type with given template """
        new_vals = {}
        for f, v in self.vals.items():
            if f in self.fields:
                if v is not None:
                    vv = scast(v, self.types[self.get_index(f)], None)
                    if vv is None: return FX_ERROR_VAL, _('Invalid data type for %a'), f
                    new_vals[f] = vv
                else: new_vals[f] = v

        self.vals = new_vals.copy()
        return 0

    def get_col_name(self, field:str):
        """ Returns a translated column name """
        if field in self.fields: return self.col_names[self.fields.index(field)]
        else: return field

    def humanize(self): pass
    def fill(self): pass









class SQLContainerEditable(SQLContainer):
    """ Heavy container with REST and mass operation functionalities """

    def __init__(self, db, entity, **kargs):
        

        #DB connection
        self.set_interface(db)

        self.entity = entity

        self.sql_getter = None # SQL query to get item by id (replaced by :id)
        self.sql_multi_getter = None # SQL query to get by id list that replaces %i string

        self.immutable = ('id',)
        self.locks = ()

        if self.entity == FX_ENT_ENTRY:
            SQLContainer.__init__(self, 'entries', ENTRIES_SQL_TABLE, col_names=ENTRIES_SQL_TABLE_PRINT, types=ENTRIES_SQL_TYPES, entity=self.entity)
            self.locks = (FX_LOCK_ENTRY,)
            self.immutable = tuple(['id', 'deleted'] + list(ENTRIES_TECH_LIST))
            self.ent_name = _('Entry')
            self.DB.cache_feeds()
            self.DB.cache_flags()
            self.DB.cache_rules()
            self.DB.cache_terms()
        
        elif self.entity == FX_ENT_FEED:
            SQLContainer.__init__(self, 'feeds', FEEDS_SQL_TABLE, col_names=FEEDS_SQL_TABLE_PRINT, types=FEEDS_SQL_TYPES, entity=self.entity)
            self.locks = (FX_LOCK_FETCH, FX_LOCK_FEED,)
            self.ent_name = _('Feed')
            self.immutable = ('id', 'deleted',)
            self.DB.cache_feeds()
        
        elif self.entity == FX_ENT_RULE:
            SQLContainer.__init__(self, 'rules', RULES_SQL_TABLE, col_names=RULES_SQL_TABLE_PRINT, types=RULES_SQL_TYPES, entity=self.entity)
            self.locks = (FX_LOCK_FETCH, FX_LOCK_RULE,)
            self.ent_name = _('Rule')
            self.DB.cache_rules()
            self.DB.cache_feeds()
            self.DB.cache_flags()

        elif self.entity == FX_ENT_FLAG:
            SQLContainer.__init__(self, 'flags', FLAGS_SQL_TABLE, col_names=FLAGS_SQL_TABLE_PRINT, types=FLAGS_SQL_TYPES, entity=self.entity)
            self.locks = (FX_LOCK_FETCH, FX_LOCK_FLAG,)
            self.ent_name = _('Flag')
            self.immutable = ()
            self.DB.cache_flags()


        if self.sql_getter is None: self.sql_getter = f"""select * from {self.table} where id = :id"""
        if self.sql_multi_getter is None: self.sql_multi_getter = f"""select * from {self.table} where id in (%i)"""


        self.to_update = None # List of fields to be updated (names only, for values are in main dictionary)
        self.updated_fields = [] # Fields that where updated in the end

        self.backup_vals = self.vals # Backup for faulty update

        self.exists = kargs.get('exists', False) # Was entity found in DB?
        self.updating = False # is update pending?


        # Queues for mass inserts
        self.oper_q = []

        # Current sql string
        self.sql_str = None
        
        # Changes to DB stats
        self.stats_delta = {}

        # Action flag
        self.action = None
        # Is action a one off?
        self.act_singleton = None
        
        # Last id for this item
        self.last_id = None
        self.rowcount = 0

        debug(9, f'Container created: {self.entity}; {self.ent_name}; {self.immutable}; {self.sql_getter}; {self.sql_multi_getter}')



    def _oper_commit(self, **kargs):
        """ Commit pending queue to SQL """
        err = 0
        oper_q_l = len(self.oper_q)
        if oper_q_l > 0:
            msg(_('Applying changes...'))
            if oper_q_l == 1: 
                self.act_singleton = True
                err = self.DB.run_sql_lock(self.sql_str, self.oper_q[0]) # This is needed to properly retrieve lastid
            else: 
                err = self.DB.run_sql_lock(self.sql_str, self.oper_q)
                self.act_singleton = False

            self.rowcount = self.DB.rowcount
            self.last_id = self.DB.lastrowid
            if self.entity == FX_ENT_ENTRY: self.DB.last_entry_id = self.last_id
            elif self.entity == FX_ENT_FEED: self.DB.last_feed_id = self.last_id
            elif self.entity == FX_ENT_RULE: self.DB.last_rule_id = self.last_id
            elif self.entity == FX_ENT_FLAG: self.DB.last_flag_id = self.last_id
            debug(9, f'Committed: last_id:{self.last_id}; row_count:{self.rowcount}; action:{self.action}')
        err = self.update_stats()
        return err




    # Skeleton commit methods
    def commit(self, **kargs):
        err = self._hook(FX_ENT_STAGE_PRE_COMMIT, **kargs)
        if err == 0: err = self._oper_commit(**kargs)
        if err == 0: err = self._hook(FX_ENT_STAGE_POST_COMMIT, **kargs)
        if err == 0: err = self.recache()
        if err == 0: self.clear_q()
        return err




    def update_stats(self, **kargs):
        """ Commit changes to DB stats """
        if self.stats_delta == {}: return 0
        err = self.DB.update_stats(self.stats_delta)
        debug(9, f'Stats updated: {self.stats_delta}')
        if err == 0: self.stats_delta = {}
        return err
    

    def sd_add(self, k, v):
        """ Inc/Dec stat delta value by key"""
        self.stats_delta[k] = scast(self.stats_delta.get(k), int, 0) + v


    def clear_q(self, **kargs):
        """ Clear all queues """
        self.oper_q.clear()
        self.sql_str = None
        self.stats_delta = {}
        self.to_update = None



    def set_interface(self, interface): 
        self.DB = interface
        self.config = self.DB.config


    def get_by_id(self, id):
        """ Basic method for getting item by id from assigned sql table - will be often oveloaded with caches etc."""
        id = scast(id, int, -1)
        content = self.DB.qr_sql(self.sql_getter, {'id':id}, one=True )
        if content in (None, (None,), ()):
            self.exists = False
            return msg(FX_ERROR_NOT_FOUND, f"""{self.ent_name} %a {_('not found!')}""", id)
        else:
            self.exists = True
            self.populate(content)
            return 0


    def get_by_id_many(self, ids, **kargs):
        """ Get item list generator by ids for multi operations """
        id_lst = ids_cs_string(ids)
        sql = self.sql_multi_getter.replace('%i',id_lst)
        for i in self.DB.qr_sql_iter(sql): yield i





    def backup(self): self.backup_vals = self.vals.copy()
    def restore(self): self.vals = self.backup_vals.copy()


    def filter_bak(self, filter:list, **kargs):
        """ Returns filtered dictionary of backup values"""
        odict = {}
        if not isinstance(filter, (list, tuple)): raise FeedexTypeError(_('Filter must be a list or a tuple!'))
        for f in filter: odict[f] = self.backup_vals[f]
        return odict

    def filter_cast(self, idict:dict, filter:list, **kargs):
        """ Filters and type-validates a dictionary - useful for meta updates that don't require much logic check """
        odict = {}
        for f in filter:
            if f not in self.fields: continue
            tp = self.types[self.fields.index(f)]
            odict[f] = scast(idict[f], tp, None)
        return odict
    
    def filter_cast_incr(self, idict:dict, filter:list, **kargs):
        """ Same as filter cast, but does not overwrite with empty values """
        odict = {}
        for f in filter:
            if f not in self.fields: continue
            v = idict.get(f)
            if v is None: odict[f] = self.vals.get(f)
            else:
                tp = self.types[self.fields.index(f)]
                if tp is str: cval = nullif(scast(v, str, '').strip(), '')
                else: cval = scast(idict[f], tp, None)
                if v is None: odict[f] = self.vals.get(f)
                else: odict[f] = cval
           
        return odict

   



    def set_update_fields(self, item, **kargs):
        """ Check dictionary for compatibility with update oper """
        tpi = type(item)
        if tpi is dict: chkl = item.keys()
        elif tpi in (list, tuple): chkl = item
        else: return msg(FX_ERROR_VAL, _('Invalid update input format'))

        self.to_update = []

        for f in chkl:
            if f in self.immutable: return msg(FX_ERROR_VAL, _('Editting field %a is not permitted!'), f)
            elif f in self.fields: self.to_update.append(f)
            else: return msg(FX_ERROR_VAL, _('Invalid update field: %a'), f)
        
        if len(self.to_update) == 0: return msg(FX_ERROR_VAL, _('Update list empty!'))
        self.updated_fields = self.to_update.copy()
        return 0



    def add_to_update(self, idict:dict, **kargs):
        """ Merge update queue with existing field values"""
        self.backup()
        self.updating = False

        for f, v in idict.items():
            if f in self.immutable:
                self.updating = False
                self.restore()
                return msg(FX_ERROR_VAL, _('Editting field %a is not permitted!'), f)

            self.vals[f] = v
            self.updating = True

        if self.updating: return 0
        else: return msg(_('Nothing to do'))


    def constr_update(self, **kargs):
        """ Consolidates updates list """
        wheres = kargs.get('wheres','id = :ent_id')
        self.updated_fields = []
        self.to_update = []
        for u in self.fields:
            if self.vals[u] != self.backup_vals.get(u): self.to_update.append(u)
        if len(self.to_update) == 0:
            self.updating = False
            return msg(_('No changes detected'))
        self.updated_fields = self.to_update.copy()
        return 0




    # Operation wrappers (locks, interface)
    def _run_locked(self, func, *args, **kargs): return self.DB.run_locked(self.locks, func, *args, **kargs) 


    def add(self, *args, **kargs):
        idict = slist(args, -1, None)
        tpn = type(idict)
        if tpn is dict:
            self.clear()
            self.merge(idict)
        elif tpn in (list, tuple): self.populate(idict)
        elif idict is not None: return msg(FX_ERROR_VAL, _('Invalid new item format (must be list or dict)!'))

        if kargs.get('no_commit', False): return self._oper(FX_ENT_ACT_ADD, *args, **kargs)
        else: return self._run_locked(self._oper, FX_ENT_ACT_ADD, *args, **kargs)


    def update(self, *args, **kargs):
        if not self.exists: return FX_ERROR_NOT_FOUND
        
        no_commit = kargs.get('no_commit', False)

        idict = slist(args, -1, None)
        if type(idict) is dict:
            err = self.add_to_update(idict, **kargs)
            if err != 0: return err
            if not self.updating: return 0
        else: idict = None

        if no_commit: return self._oper(FX_ENT_ACT_UPD, *args, **kargs)
        else: return self._run_locked(self._oper, FX_ENT_ACT_UPD, *args, **kargs)



    def delete(self, *args, **kargs):
        if not self.exists: return FX_ERROR_NOT_FOUND
        kargs['no_commit'] = False
        if 'deleted' in self.fields and scast(self.vals.get('deleted'), int, 0) == 0: return self._run_locked(self._oper, FX_ENT_ACT_DEL, *args, **kargs)
        else: return self._run_locked(self._oper, FX_ENT_ACT_DEL_PERM, *args, **kargs)


    def restore(self, *args, **kargs):
        if not self.exists: return FX_ERROR_NOT_FOUND
        kargs['no_commit'] = False
        if 'deleted' not in self.fields or scast(self.vals['deleted'], int, 0) <= 0: return msg(_('Nothing to do'))
        return self._run_locked(self._oper, FX_ENT_ACT_RES, *args, **kargs)



    def add_many(self, *args, **kargs): return self._run_locked(self._add_many, *args, **kargs) 
    def update_many(self, *args, **kargs): return self._run_locked(self._update_many, *args, **kargs) 
    def delete_many(self, *args, **kargs): return self._run_locked(self._delete_many, *args, **kargs) 
    def restore_many(self, *args, **kargs): return self._run_locked(self._restore_many, *args, **kargs) 
    def delete_perm_many(self, *args, **kargs): 
        kargs['perm'] = True
        return self._run_locked(self._delete_many, *args, **kargs)



    # Basic REST
    
    # Processing hook to be overloaded by descendant classes
    def _hook(self, stage, **kargs): return 0

    # Wrapper for values pre-processing
    def deraw_vals(self, **kargs): return self._hook(FX_ENT_STAGE_PRE_VAL)

    # Skeletons

    def validate(self, **kargs):
        err = self._hook(FX_ENT_STAGE_PRE_VAL, **kargs)
        if err != 0: return err
        err = self.validate_fields()
        if err != 0: return err   
        err = self._hook(FX_ENT_STAGE_POST_VAL, **kargs)
        return err

    def recache(self, **kargs):
        err = 0
        if not fdx.single_run:
            if self.entity == FX_ENT_FLAG: self.DB.load_flags()
            elif self.entity == FX_ENT_RULE: self.DB.load_rules()
            elif self.entity == FX_ENT_FEED: self.DB.load_feeds()
            err = self._hook(FX_ENT_STAGE_RECACHE, **kargs)
        return err





    def _oper(self, action, *args, **kargs):
        """ Main operation basic logic skeleton """
        self.action = action
        no_commit = kargs.get('no_commit',False)

        err = self._hook(FX_ENT_STAGE_INIT_OPER, **kargs)
        if err != 0: return err

        if self.action in (FX_ENT_ACT_ADD, FX_ENT_ACT_UPD,):
            if kargs.get('validate', True):
                err = self.validate(**kargs)
                if err != 0: return msg(*err)

        if self.action == FX_ENT_ACT_UPD and self.to_update is None:
            err = self.constr_update()
            if err != 0:
                self.restore()
                return err
            if not self.updating:
                self.restore()
                return msg(_('Nothing to do'))


        err = self._hook(FX_ENT_STAGE_PRE_OPER, **kargs)
        if err != 0: 
            if self.action == FX_ENT_ACT_UPD: self.restore()
            return err

        # Main operation queue
        if self.action == FX_ENT_ACT_ADD:
            self.clean()
            if self.sql_str is None: self.sql_str = self.insert_sql(all=True)
            self.oper_q.append(self.vals.copy())

        elif self.action == FX_ENT_ACT_DEL:
            idd = {'id':self.vals['id']}
            if self.sql_str is None: self.sql_str = f'update {self.table} set deleted = 1 where id = :id'
            self.oper_q.append(idd)
            self.vals['deleted'] = 1

        elif self.action == FX_ENT_ACT_DEL_PERM:
            if self.sql_str is None: self.sql_str = f'delete from {self.table} where id = :id'
            self.oper_q.append({'id':self.vals['id']})
            if 'deleted' in self.fields: self.vals['deleted'] = 2

        elif self.action == FX_ENT_ACT_RES:
            idd = {'id':self.vals['id']}
            if self.sql_str is None: self.sql_str = f'update {self.table} set deleted = 0 where id = :id'
            self.oper_q.append(idd)
            self.vals['deleted'] = 0

        elif self.action == FX_ENT_ACT_UPD:
            self.clean()
            if self.sql_str is None: self.sql_str = self.update_sql(filter=self.to_update, wheres='id = :ent_id')
            udict = self.filter(self.to_update)
            udict['ent_id'] = self.backup_vals['id']
            self.oper_q.append(udict)


        err = self._hook(FX_ENT_STAGE_POST_OPER, **kargs)
        if err != 0: 
            if self.action == FX_ENT_ACT_UPD: self.restore()            
            return err

        if no_commit: return 0
        err = self.commit()
        if err != 0: 
            if self.action == FX_ENT_ACT_UPD: self.restore()           
            return err


        if self.rowcount > 0:

            if self.action == FX_ENT_ACT_ADD:
                if self.act_singleton: self.vals['id'] = self.last_id
                return msg(*self._add_msg(**kargs), log=True)
            elif self.action == FX_ENT_ACT_DEL: return msg(*self._del_msg(**kargs), log=True)
            elif self.action == FX_ENT_ACT_DEL_PERM: return msg(*self._del_perm_msg(**kargs), log=True)
            elif self.action == FX_ENT_ACT_RES: return msg(*self._res_msg(**kargs), log=True)
            
            elif self.action == FX_ENT_ACT_UPD:
            
                upd = []
                for u in self.updated_fields:
                    if u not in self.immutable: upd.append(u)

                if len(upd) > 1: return msg(*self._upd_msg_generic(**kargs), log=True)
                else:
                    for f in upd: return msg(*self._upd_msg(f, **kargs), log=True)
            
                return msg(_('Nothing done'))


        else: return msg(_('Nothing done'))










    # Mass operations
    def _update_many(self, idict, ids, **kargs):
        """ Wrapper for multi update """
        err = self.set_update_fields(idict)
        if err != 0: return err

        self.exists = True
        msg(_('Updating %a items...'), len(ids))
        for i in self.get_by_id_many(ids):
            self.populate(i)
            err = self.update(idict, validate=True, no_commit=True)
            if err != 0: return msg(err, _('Operation aborted due to errors (Item: %a)'), self.vals['id'])
        err = self.commit()
        if err != 0: return err
        if self.rowcount > 0: msg(_('Updated %a items'), len(ids), log=True)
        else: msg(_('Nothing done.'))
        return 0


    def _delete_many(self, ids, **kargs):
        """ Wrapper for multi delete """
        self.exists = True
        msg(_('Deleting %a items...'), len(ids))
        for i in self.get_by_id_many(ids):
            self.populate(i)
            if kargs.get('perm', False): err = self._oper(FX_ENT_ACT_DEL_PERM, no_commit=True)
            else: err = self._oper(FX_ENT_ACT_DEL, no_commit=True)
            if err != 0: return msg(err, _('Operation aborted due to errors (Item: %a)'), self.vals['id'])
        
        err = self.commit()
        if err != 0: return err

        if self.rowcount > 0:
            if kargs.get('perm', False): msg(_('Permanently deleted %a items'), len(ids), log=True)
            else: msg(_('Deleted %a items'), len(ids), log=True)
        else: msg(_('Nothing done.'))
        return 0


    def _restore_many(self, ids, **kargs):
        """ Wrapper for multi restore"""
        self.exists = True
        msg(_('Restoring %a items...'), len(ids))
        for i in self.get_by_id_many(ids):
            self.populate(i)
            err = self._oper(FX_ENT_ACT_RES, no_commit=True)
            if err != 0: return msg(err, _('Operation aborted due to errors (Item: %a)'), self.vals['id'])
        
        err = self.commit()
        if err != 0: return err

        if self.rowcount > 0: msg(_('Restored %a items'), len(ids), log=True)
        else: msg(_('Nothing done.'))
        return 0



    def _add_many(self, ilist, **kargs):
        """ Wrapper for multi-adding """
        conditions = kargs.get('conditions')
        
        new_items = 0
        for ii,i in enumerate(ilist):

            tpi = type(i)
            if tpi in (list, tuple): self.populate(i)
            elif tpi is dict:
                self.clear()
                self.merge(i)
            else: return msg(FX_ERROR_VAL, _('Invalid item %a format (must be list or dict)!'), ii)

            debug(6, f'Processing item {ii}...')

            # Sometimes it is useful to apply conditions on mass insert
            if conditions is not None:
                for c in conditions:
                    k, op, v = c[0], c[1], c[2]
                    val = self.vals.get(k)
                    if op in ('gt','lt','ge','le'): cst_val = scast(val, type(k), 0)
                    stop = False
                    if op == 'eq' and not val == v: stop = True
                    elif op == 'ne' and not val != v: stop = True
                    elif op == 'gt' and not cst_val > v: stop = True
                    elif op == 'lt' and not cst_val < v: stop = True
                    elif op == 'ge' and not cst_val >= v: stop = True
                    elif op == 'le' and not cst_val <= v: stop = True
                    elif op == 'in' and val not in v: stop = True
                    elif op == 'nin' and val in v: stop = True
                    elif op == 'is' and val is not v: stop = True
                    elif op == 'isn' and val is v: stop = True

                    if stop:
                        debug(6, 'Ommitted.')
                        continue
                        
            
            err = self._oper(FX_ENT_ACT_ADD, validate=True, no_commit=True, counter=ii)
            if err != 0:
                msg(err, _('Failed to add item %a'), ii)
                continue
        
            new_items += 1
        
        if new_items > 0:
            err = self.commit()
            if err != 0: return err
            msg(_('Added %a items out of %b'), new_items, len(ilist), log=True)
        
        else: msg(_('Nothing to add'))
        
        return 0



    # Nice Messages for overloading, if needed
    def _upd_msg_generic(self, **kargs): return f"""{self.ent_name} %a {_('updated successfully')}""", self.name()
    def _upd_msg(self, field, **kargs): return f"""{self.ent_name} %a {_('updated: %b changed to %c')}""", self.name(), self.get_col_name(field), self.vals.get(field,_("<NULL>"))
    def _add_msg(self, **kargs): return f"""{self.ent_name} %a {_('added successfully')}""", self.vals['id']
    def _del_msg(self, **kargs): return f"""{self.ent_name} %a {_('deleted')}""", self.name()
    def _del_perm_msg(self, **kargs): return f"""{self.ent_name} %a {_('deleted permanently')}""", self.name()
    def _res_msg(self, **kargs): return f"""{self.ent_name} %a {_('restored')}""", self.vals['id']













class FeedexFlag(SQLContainerEditable):
    """ Container for Flags """

    def __init__(self, db, **kargs):
        SQLContainerEditable.__init__(self, db, FX_ENT_FLAG, **kargs)
        self.gen_id = None
        if kargs.get('id') is not None: self.get_by_id(kargs.get('id'))


    def get_by_id(self, id):
        id = scast(id, int, -1)
        if id not in fdx.flags_cache.keys():
            self.exists = False
            return msg(FX_ERROR_NOT_FOUND, f"""{self.ent_name} %a {_('not found!')}""", id)
        else:
            self.exists = True
            fl = [id] + list(fdx.flags_cache[id])
            self.populate(fl)
            return 0

    def get_by_id_many(self, ids, **kargs):
        for id in ids:
            if id in fdx.flags_cache.keys(): yield tuple([id] + list(fdx.flags_cache[id]))


    def _hook(self, stage, **kargs):
        """ Validate current values """
        if stage == FX_ENT_STAGE_POST_VAL:
            if self.action == FX_ENT_ACT_ADD: 
                if self.gen_id is None:
                    if len(fdx.flags_cache.keys()) == 0: self.gen_id = 0
                    else: self.gen_id = max(fdx.flags_cache.keys())
                        
                self.gen_id += 1
                self.vals['id'] = self.gen_id
            
            else:
                if self.vals['id'] in fdx.flags_cache.keys() and self.vals['id'] != self.backup_vals['id']: return -7, _('ID taken by another flag')
            
            if self.vals['name'] is None or self.vals['name'] == '': return -7, _('Flag name cannot be empty!')
            if self.vals['color_cli'] is not None and self.vals['color_cli'] not in TCOLS.keys(): return -7, _('Invalid CLI color name!')
    
        
        elif stage == FX_ENT_STAGE_POST_COMMIT: self.gen_id = None
        
        return 0





    










class FeedexRule(SQLContainerEditable):
    """ Container for Feeds """

    def __init__(self, db, **kargs):
        SQLContainerEditable.__init__(self, db, FX_ENT_RULE, **kargs)
        self.feed = ResultFeed()
        if kargs.get('id') is not None: self.get_by_id(kargs.get('id'))


    
    def get_by_id(self, id:int):
        id = scast(id, int, -1)
        for r in fdx.rules_cache:
            if r[self.get_index('id')] == id:
                self.exists = True
                self.populate(r)
                return 0
        self.exists = False
        return msg(FX_ERROR_NOT_FOUND, _('Rule %a not found!'), id)


    def get_by_id_many(self, ids, **kargs):
        for r in fdx.rules_cache:
            if r[self.get_index('id')] in ids: yield r




    def _hook(self, stage, **kargs):

        if stage == FX_ENT_STAGE_PRE_VAL:

            if self.action == FX_ENT_ACT_ADD: self.vals['id'] = None
            
            if self.vals.get('feed_id') is not None: pass
            elif self.vals.get('feed') is not None: self.vals['feed_id'] = self.vals['feed']
            elif self.vals.get('cat') is not None: self.vals['feed_id'] = fdx.res_cat_name(self.vals['cat'])
            elif self.vals.get('cat_id') is not None: self.vals['feed_id'] = self.vals['cat_id']
            elif self.vals.get('parent_id') is not None: self.vals['feed_id'] = self.vals['parent_id']

            if self.vals.get('flag_id') is not None: self.vals['flag'] = self.vals['flag_id']
            elif self.vals.get('flag') is not None:
                if type(self.vals['flag']) is str: self.vals['flag'] = fdx.res_flag_name(self.vals['flag'])

            self.vals['type'] = fdx.res_qtype(self.vals['type'], rule=True)
            self.vals['weight'] = coalesce(self.vals.get('weight'), self.config.get('default_rule_weight', 20))

        elif stage == FX_ENT_STAGE_POST_VAL:

            if self.vals.get('feed_id') is not None:
                feed = fdx.load_parent(self.vals['feed_id'])
                if feed == -1: return FX_ERROR_VAL, _('Channel/Category %a not found!'), self.vals.get('feed', _('<UNKNOWN>'))
                else:
                    self.feed.populate(feed)
                    self.vals['feed_id'] = self.feed['id']

            if self.vals['flag'] not in (None,0):
                if not fdx.is_flag(self.vals['flag']): return FX_ERROR_VAL, _('Flag not found!')

            if self.vals['string'] is None or self.vals['string'] == '': return FX_ERROR_VAL, _('Search string cannot be empty!')

            if self.vals['type'] not in (0,1,2): return FX_ERROR_VAL, _('Invalid query type! Must be string(0), full-text (1), or regex (2)')
            if self.vals['type'] == 2 and not check_if_regex(self.vals['string']): return FX_ERROR_VAL, _('Not a valid regex string!')
        
            if self.vals.get('field') is not None:
                field = fdx.res_field(self.vals['field'])
                if field == -1: return FX_ERROR_VAL, _('Field to search not valid!')
                else: self.vals['field'] = field

            self.vals['case_insensitive'] = coalesce(self.vals.get('case_insensitive'), 1)
            if self.vals.get('case_insensitive') not in (0,1): return FX_ERROR_VAL, _('Case insensitivity must be 0 or 1!')    

        return 0
















class ResultFetch(SQLContainer):
    """ Container for Fetch register item """
    def __init__(self, **kargs): super().__init__('actions', FETCH_TABLE, col_names=FETCH_TABLE_PRINT, types=FETCH_TABLE_TYPES, entity=FX_ENT_FETCH)


class FeedexKwTerm(SQLContainer):
    """ Keyword term extracted from read/marked entries """
    def __init__(self, **kargs): super().__init__('terms', KW_TERMS_TABLE, col_names=KW_TERMS_TABLE_PRINT, types=KW_TERMS_TYPES, entity=FX_ENT_KW_TERM)
class ResultKwTerm(SQLContainer):
    def __init__(self, **kargs): super().__init__('terms', KW_TERMS_TABLE, col_names=KW_TERMS_TABLE_PRINT, types=KW_TERMS_TYPES, entity=FX_ENT_KW_TERM)
class ResultKwTermShort(SQLContainer):
    def __init__(self, **kargs): super().__init__('terms', KW_TERMS_SHORT, col_names=KW_TERMS_SHORT_PRINT, entity=FX_ENT_KW_TERM, **kargs)
    



class ResultEntry(SQLContainer):
    """ Container for search results (standard entries)"""
    def __init__(self, **kargs):
        SQLContainer.__init__(self,'entries', RESULTS_SQL_TABLE, types=RESULTS_SQL_TYPES, col_names=RESULTS_SQL_TABLE_PRINT, entity=FX_ENT_ENTRY, **kargs)

    def humanize(self):
        """ Prepare contents for nice output """
        if coalesce(self.vals['read'],0) > 0: self.vals['sread'] = _('Yes')
        else: self.vals['sread'] = _('No')

        if self.vals['note'] == 1: self.vals['snote'] = _('Yes')
        else: self.vals['snote'] = _('No')

    def fill(self):
        """ Fill in missing data """
        f = fdx.load_parent(self.vals['feed_id'])
        feed = ResultFeed()
        if f != -1: feed.populate(f)
        
        if coalesce(feed['deleted'],0) > 0: self.vals['is_deleted'] = 1
        else: self.vals['is_deleted'] = self.vals['deleted']
        self.vals['feed_name'] = feed.name()
        self.vals['feed_name_id'] = f"""{self.vals['feed_name']} ({feed['id']})"""
        self.vals['pubdate_r'] = datetime.fromtimestamp(self.vals.get('pubdate',0))
        self.vals['pubdate_short'] = datetime.strftime(self.vals['pubdate_r'], '%Y.%m.%d')
        self.vals['pubdate_r'] = self.vals['pubdate_r'].strftime('%Y-%m-%d %H:%M:%S')
        if coalesce(self.vals['flag'],0) > 0: self.vals['flag_name'] = fdx.get_flag_name(coalesce(self.vals['flag'],0))
        self.vals['user_agent'] = feed['user_agent']
        self.vals['parent_id'] = feed['parent_id']
        self.vals['parent_name'] = fdx.get_feed_name(feed['parent_id'])




class ResultContext(SQLContainer):
    """ Container for search results (term in context)"""
    def __init__(self, **kargs):
        SQLContainer.__init__(self,'contexts', CONTEXTS_TABLE, types=CONTEXTS_TYPES, col_names=CONTEXTS_TABLE_PRINT, entity=FX_ENT_CONTEXT, **kargs)

    def humanize(self):
        """ Prepare contents for nice output """
        if coalesce(self.vals['read'],0) > 0: self.vals['sread'] = _('Yes')
        else: self.vals['sread'] = _('No')

        if self.vals['note'] == 1: self.vals['snote'] = _('Yes')
        else: self.vals['snote'] = _('No')



class ResultRule(SQLContainer):
    """ Container for search results (rules)"""
    def __init__(self, **kargs):
        SQLContainer.__init__(self,'rules', RULES_SQL_TABLE_RES, types=RULES_SQL_TYPES_RES, col_names=RULES_SQL_TABLE_RES_PRINT, entity=FX_ENT_RULE, **kargs)

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

        flag = coalesce(self.vals['flag'],0) 
        if flag == 0: self.vals['flag_name'] = _('-- None --')
        else: self.vals['flag_name'] = fdx.get_flag_name(flag)

        self.vals['field_name'] = PREFIXES.get(self.vals['field'],{}).get('name',_('-- All Fields --'))

        feed_id = self.vals['feed_id']
        if feed_id in (None,-1): self.vals['feed_name'] = _('-- All Channels/Catgs. --')
        else: self.vals['feed_name'] = fdx.get_feed_name(self.vals['feed_id'], with_id=True)

    def fill(self): pass





class ResultFeed(SQLContainer):
    """ Container for search results (feed/category)"""
    def __init__(self, **kargs):
        SQLContainer.__init__(self,'feeds', FEEDS_SQL_TABLE_RES, types=FEEDS_SQL_TYPES_RES, col_names=FEEDS_SQL_TABLE_RES_PRINT, entity=FX_ENT_FEED, **kargs)

    def humanize(self):
        if self.vals['parent_id'] is not None: self.vals['parent_category_name'] = fdx.get_feed_name(self.vals['parent_id'], with_id=True)
        if coalesce(self.vals['deleted'],0) >= 1: self.vals['sdeleted'] = _('Yes')
        else: self.vals['sdeleted'] = _('No')

        if coalesce(self.vals['autoupdate'],0) >= 1: self.vals['sautoupdate'] = _('Yes')
        else: self.vals['sautoupdate'] = _('No')

        if coalesce(self.vals['fetch'],0) >= 1: self.vals['sfetch'] = _('Yes')
        else: self.vals['sfetch'] = _('No')


    def fill(self): pass




class ResultFlag(SQLContainer):
    """ Container for search results (flag)"""
    def __init__(self, **kargs): SQLContainer.__init__(self,'flags', FLAGS_SQL_TABLE, types=FLAGS_SQL_TYPES, col_names=FLAGS_SQL_TABLE_PRINT, entity=FX_ENT_FLAG, **kargs)

class ResultTerm(SQLContainer):
    """ Container for search results (term)"""
    def __init__(self, **kargs): SQLContainer.__init__(self,'terms', TERMS_TABLE, types=TERMS_TYPES, col_names=TERMS_TABLE_PRINT, entity=FX_ENT_TERM, **kargs)


class ResultTimeSeries(SQLContainer):
    """ Container for search results (time series)"""
    def __init__(self, **kargs): SQLContainer.__init__(self,'time_series', TS_TABLE, types=TS_TYPES, col_names=TS_TABLE_PRINT, entity=FX_ENT_TS, **kargs)


class ResultHistoryItem(SQLContainer):
    """ Container for search result (history item)"""
    def __init__(self, **kargs): SQLContainer.__init__(self,'history', HISTORY_SQL_TABLE, types=HISTORY_SQL_TYPES, col_names=HISTORY_SQL_TABLE_PRINT, entity=FX_ENT_HISTORY, **kargs)









class FeedexHistoryItem(SQLContainer):
    """ Basic container for Feeds - in case no DB interface is needed """
    def __init__(self, db, **kargs):
        SQLContainer.__init__(self, 'search_history', HISTORY_SQL_TABLE, types=HISTORY_SQL_TYPES, col_names = HISTORY_SQL_TABLE_PRINT, **kargs)
        self.entity = FX_ENT_HISTORY
        self.DB = db
        self.config = self.DB.config
        self.DB.cache_history()
        self.DB.cache_feeds()
    

    def validate(self, **kargs):
        err_fld = self.validate_fields()
        if err_fld != 0: return -7, _('Invalid type for field %a'), err_fld

        if self.vals['feed_id'] is not None:
            if fdx.is_cat_feed(self.vals.get('feed_id')) not in (1,2,): return -7, _('Channel/Category %a not found!'), self.vals.get('feed_id')
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





class FeedexDBStats(SQLContainer):
    """ Container class for database statistics """
    def __init__(self, **kargs):
        super().__init__('db_stats', FEEDEX_DB_STATS, col_names=FEEDEX_DB_STATS_PRINT, types=FEEDEX_DB_STATS_TYPES, **kargs)
        self.entity = FX_ENT_DB_STATS

    def mu_str(self, **kargs):
        """ Generates marked up string with stats """
        stat_str=f"""

{self.get_col_name('db_path')}: <b>{self['db_path']}</b>

{self.get_col_name('version')}: <b>{self['version']}</b>

{self.get_col_name('db_size')}: <b>{self['db_size']}</b>
{self.get_col_name('ix_size')}: <b>{self['ix_size']}</b>
{self.get_col_name('cache_size')}: <b>{self['cache_size']}</b>

{self.get_col_name('total_size')}: <b>{self['total_size']}</b>


{self.get_col_name('doc_count')}: <b>{self['doc_count']}</b>
{self.get_col_name('last_doc_id')}: <b>{self['last_doc_id']}</b>

{self.get_col_name('rule_count')}: <b>{self['rule_count']}</b>
{self.get_col_name('learned_kw_count')}: <b>{self['learned_kw_count']}</b>

{self.get_col_name('feed_count')}: <b>{self['feed_count']}</b>
{self.get_col_name('cat_count')}: <b>{self['cat_count']}</b>

{self.get_col_name('last_update')}: <b>{self['last_update']}</b>
{self.get_col_name('first_update')}: <b>{self['first_update']}</b>

"""

        if self['fetch_lock']: 
            stat_str = f"""{stat_str}
<i>{_('DATABASE LOCKED FOR FETCHING')}</i>


"""
        if self['due_maintenance']: 
            stat_str = f"""{stat_str}
<i>{_('DATABASE MAINTENANCE ADVISED')}</i>


"""
        return stat_str