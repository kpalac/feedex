# -*- coding: utf-8 -*-
""" Entities classes: rules

"""


from feedex_headers import *







class FeedexRule(SQLContainerEditable):
    """ Container for Feeds """

    def __init__(self, db, **kargs):
        SQLContainerEditable.__init__(self, 'rules', RULES_SQL_TABLE, types=RULES_SQL_TYPES, col_names=RULES_SQL_TABLE_PRINT, **kargs)
        self.set_interface(db)        
        self.DB.cache_rules()
        self.DB.cache_feeds()
        self.DB.cache_flags()

        self.feed = ResultFeed()

        if kargs.get('id') is not None: self.get_by_id(kargs.get('id'))

        self.immutable = RULES_TECH_LIST


    
    def get_by_id(self, id:int):
        content = self.DB.qr_sql("select * from rules r where r.id = :id and coalesce(r.learned, 0) <> 1", {'id':id}, one=True )
        if content in (None, (None,), ()):
            self.exists = False
            return msg(FX_ERROR_NOT_FOUND, _('Rule %a not found!'), id)
        else:
            self.exists = True
            self.populate(content)
            return 0




    def name(self, **kargs):
        id = kargs.get('id',False)
        if id: id_str = f' ({self.vals["id"]})'
        else: id_str = ''

        name = coalesce(self.vals['name'],'')
        sname = f'{name}{id_str}'
        if name.strip() == '':
            name = coalesce(self.vals['string'],'')
            sname = f'{name}{id_str}'
            if name.strip() == '':
                sname = scast(self.vals['id'], str, _('<UNKNOWN>'))
            else:
                if len(name) > 75: sname = f'{sname[:75]}...'

        return sname
    


    def resolve_qtype(self, qtype):
        """ Resolve query type from string to int """
        if qtype is None: return -1
        if type(qtype) is int and qtype in (0,1,3): return qtype
        if type(qtype) is str:
            if qtype.lower() in ('string','str','string_matching'):
                return 0
            elif qtype.lower() in ('fts', 'full-text','fulltext',):
                return 1
            elif qtype.lower() in ('regex','REGEX',):
                return 2
            else: return 1
        return -1




    def validate(self, **kargs):
        """ Validate current values """
        if self.vals['flag'] not in (None,0): self.vals['flag'] = fdx.find_flag(self.vals['flag'])
        if self.vals['flag'] == -1: return FX_ERROR_VAL, _('Flag not found!')

        err = self.validate_types()
        if err != 0: return FX_ERROR_VAL, _('Invalid data type for %a'), err

        if self.vals['string'] is None or self.vals['string'] == '': return FX_ERROR_VAL, _('Search string cannot be empty!')

    
        if self.vals.get('qtype') is not None:
            qtype = fdx.resolve_qtype(self.vals['qtype'])
            if qtype == -1: return FX_ERROR_VAL, _('Invalid query type! Must be string(0), full-text (1), or regex (2)')
            else: self.vals['type'] = qtype
        
        if 'feed' in self.vals.keys():
            if self.vals.get('feed') is not None:
                feed = fdx.find_feed(self.vals['feed'], load=True)
                if feed == -1: return FX_ERROR_VAL, _('Channel %a not found!'), self.vals.get('feed', _('<UNKNOWN>'))
                else: 
                    self.feed.populate(feed)
                    self.vals['feed_id'] = self.feed['id']
            else: self.vals['feed_id'] = None

        elif 'category' in self.vals.keys(): 
            if self.vals.get('category') is not None:
                feed = fdx.find_category(self.vals['category'], load=True)
                if feed == -1: return FX_ERROR_VAL, _('Category %a not found!'), self.vals.get('category', _('<UNKNOWN>'))
                else: 
                    self.feed.populate(feed)
                    self.vals['feed_id'] = self.feed['id']
            else: self.vals['feed_id'] = None

        elif 'feed_or_cat' in self.vals.keys():
            if self.vals.get('feed_or_cat') is not None:
                feed = fdx.find_f_o_c(self.vals['feed_or_cat'], load=True)
                if feed == -1: return FX_ERROR_VAL, _('Channel/Category %a not found!'), self.vals.get('feed', _('<UNKNOWN>'))
                else: 
                    self.feed.populate(feed)
                    self.vals['feed_id'] = self.feed['id']
            else: self.vals['feed_id'] = None

        elif 'feed_id' in self.vals.keys():
            if self.vals.get('feed_id') is not None:
                feed = fdx.find_f_o_c(self.vals['feed_id'], load=True)
                if feed == -1: return FX_ERROR_VAL, _('Channel/Category %a not found!'), self.vals.get('feed', _('<UNKNOWN>'))
                else: 
                    self.feed.populate(feed)
                    self.vals['feed_id'] = self.feed['id']
            else: self.vals['feed_id'] = None
        else:
            self.vals['feed_id'] = None


        if 'field' in self.vals.keys():
            if self.vals.get('field') is not None:
                field = fdx.resolve_field(self.vals['field'])
                if field == -1: return FX_ERROR_VAL, _('Field to search not valid!')
                else: self.vals['field_id'] = field
            else: self.vals['field_id'] = None

        elif 'field_id' in self.vals.keys():
            if self.vals.get('field_id') is not None:
                field = fdx.resolve_field(self.vals['field_id'])
                if field == -1: return FX_ERROR_VAL, _('Field to search not valid!')
                else: self.vals['field_id'] = field
            else: self.vals['field_id'] = None
        else: 
            self.vals['field_id'] = None


        if self.vals['type'] == 3 and not check_if_regex(self.vals['string']): return FX_ERROR_VAL, _('Not a valid regex string!')

        if self.vals.get('case_insensitive') is not None:
            if self.vals.get('case_insensitive') not in (0,1): return FX_ERROR_VAL, _('Case insensitivity must be 0 or 1!') 
        elif self.vals.get('case_ins') is not None:
            if self.vals['case_ins'] in (True, 1): self.vals['case_insensitive'] = 1
            else: self.vals['case_insensitive'] = 0

        elif self.vals.get('case_sens') is not None:
            if self.vals['case_sens'] in (True, 1): self.vals['case_insensitive'] = 0
            else: self.vals['case_insensitive'] = 1
    
        else: self.vals['case_insensitive'] = 1

        if self.vals['case_insensitive'] not in (0,1): return FX_ERROR_VAL, _('Case insensitivity must be 0 or 1!')

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
                err = self.DB.load_rules()
                if err != 0: return msg(FX_ERROR_DB, _('Error reloading rules after successfull update!'))
            
            for i,u in enumerate(self.to_update):
                if u in self.immutable or u == 'id': del self.to_update[i]

            if len(self.to_update) > 1:
                return msg(_('Rule %a updated successfuly!'), self.name(), log=True)
            else:
                for f in self.to_update:
                    return msg(f'{_("Rule %a updated")}:  {f} -> {self.vals.get(f,_("<NULL>"))}', self.name(), log=True)
            
            return msg(_('Nothing done'))

        else:
            return msg(_('Nothing done'))





    def update(self, idict, **kargs):
        """ Quick update with a value dictionary"""
        if not self.exists: return -8
        err = self.add_to_update(idict)
        if err == 0: err = self.do_update(validate=True)
        return err
      



    def delete(self, **kargs):
        """ Delete rule by ID """
        if not self.exists: return -8, _('Rule %a not found!'), id

        err = self.DB.run_sql_lock("delete from rules where id = :id and learned <> 1", {'id':self.vals['id']} )
        if err != 0: return err
        
        if self.DB.rowcount > 0: 
            if not fdx.single_run: 
                err = self.DB.load_rules()
                if err != 0: return msg(FX_ERROR_DB, _('Error reloading rules after successfull delete: %a'))

            return msg(_('Rule %a deleted'), self.vals['id'], log=True)

        else: return msg(_('Nothing done.'))





    def add(self, **kargs):
        """ Add feed to database """
        idict = kargs.get('new')
        if idict is not None:
            self.clear()
            self.merge(idict)

        self.vals['id'] = None
        self.vals['learned'] = 0
        self.vals['archive'] = None
        self.vals['path'] = None
        self.vals['context_id'] = None
        
        if kargs.get('validate',True):
            err = self.validate()
            if err != 0: return msg(*err)

        self.clean()
        err = self.DB.run_sql_lock(self.insert_sql(all=True), self.vals)
        if err != 0: return err
        
        self.vals['id'] = self.DB.lastrowid
        self.DB.last_rule_id = self.vals['id']

        if not fdx.single_run: 
            err = self.DB.load_rules()
            if err != 0: return msg(FX_ERROR_DB, _('Error reloading rules after successfull add!'))

        return msg(_('Rule %a added successfully'), self.name(id=True), log=True)











