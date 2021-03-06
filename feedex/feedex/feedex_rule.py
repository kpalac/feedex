# -*- coding: utf-8 -*-
""" Entities classes: rules

"""


from feedex_headers import *




class RuleContainerBasic(SQLContainerEditable):
    """ Basic container for Feeds - in case no DB interface is needed """
    def __init__(self, **kargs):
        if kargs.get('result',False): SQLContainerEditable.__init__(self, 'rules', RULES_SQL_TABLE_RES, **kargs)
        else: SQLContainerEditable.__init__(self, 'rules', RULES_SQL_TABLE, types=RULES_SQL_TYPES, **kargs)


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




class RuleContainer(RuleContainerBasic):
    """ Container for Feeds """

    def __init__(self, FX, **kargs):
        RuleContainerBasic.__init__(self, **kargs)

        self.set_interface(FX)        
        self.debug = self.FX.debug
        self.config = self.FX.config

        self.feed = FeedContainerBasic()

        if kargs.get('id') is not None: self.get_by_id(kargs.get('id'))

        self.immutable = RULES_TECH_LIST


    
    def get_by_id(self, id:int):
        content = self.FX.qr_sql("select * from rules r where r.id = :id and coalesce(r.learned, 0) <> 1", {'id':id}, one=True )
        if content in (None, (None,), ()):
            self.exists = False
            cli_msg( (-1, _('Rule %a not found!'), id) )
            return -1
        else:
            self.exists = True
            self.populate(content)
            return 0




    def validate(self, **kargs):
        """ Validate current values """
        if self.vals['flag'] not in (None,0): self.vals['flag'] = self.FX.resolve_flag(self.vals['flag'])
        if self.vals['flag'] == -1: return -7, _('Flag not found!')

        err = self.validate_types()
        if err != 0: return -7, _('Invalid data type for %a'), err

        if self.vals['string'] is None or self.vals['string'] == '': return -7, _('Search string cannot be empty!')

    
        if self.vals.get('qtype') is not None:
            qtype = self.FX.resolve_qtype(self.vals['qtype'])
            if qtype == -1: return -7, _('Invalid query type! Must be string(0), full-text (1), exact (2) or regex (3)')
            else: self.vals['type'] = qtype

        if self.vals.get('type') not in (0,1,2,3): return -7, _('Invalid query type! Must be string(0), full-text (1), exact (2) or regex (3)')

        
        if 'feed' in self.vals.keys():
            if self.vals.get('feed') is not None:
                feed = self.FX.resolve_feed(self.vals['feed'], load=True)
                if feed == -1: return -7, _('Channel %a not found!'), self.vals.get('feed', _('<UNKNOWN>'))
                else: 
                    self.feed.populate(feed)
                    self.vals['feed_id'] = self.feed['id']
            else: self.vals['feed_id'] = None

        elif 'category' in self.vals.keys(): 
            if self.vals.get('category') is not None:
                feed = self.FX.resolve_category(self.vals['category'], load=True)
                if feed == -1: return -7, _('Category %a not found!'), self.vals.get('category', _('<UNKNOWN>'))
                else: 
                    self.feed.populate(feed)
                    self.vals['feed_id'] = self.feed['id']
            else: self.vals['feed_id'] = None

        elif 'feed_or_cat' in self.vals.keys():
            if self.vals.get('feed_or_cat') is not None:
                feed = self.FX.resolve_f_o_c(self.vals['feed_or_cat'], load=True)
                if feed == -1: return -7, _('Channel/Category %a not found!'), self.vals.get('feed', _('<UNKNOWN>'))
                else: 
                    self.feed.populate(feed)
                    self.vals['feed_id'] = self.feed['id']
            else: self.vals['feed_id'] = None

        elif 'feed_id' in self.vals.keys():
            if self.vals.get('feed_id') is not None:
                feed = self.FX.resolve_f_o_c(self.vals['feed_id'], load=True)
                if feed == -1: return -7, _('Channel/Category %a not found!'), self.vals.get('feed', _('<UNKNOWN>'))
                else: 
                    self.feed.populate(feed)
                    self.vals['feed_id'] = self.feed['id']
            else: self.vals['feed_id'] = None
        else:
            self.vals['feed_id'] = None


        if 'field' in self.vals.keys():
            if self.vals.get('field') is not None:
                field = self.FX.resolve_field(self.vals['field'])
                if field == -1: return -7, _('Field to search not valid!')
                else: self.vals['field_id'] = field
            else: self.vals['field_id'] = None

        elif 'field_id' in self.vals.keys():
            if self.vals.get('field_id') is not None:
                field = self.FX.resolve_field(self.vals['field_id'])
                if field == -1: return -7, _('Field to search not valid!')
                else: self.vals['field_id'] = field
            else: self.vals['field_id'] = None
        else: 
            self.vals['field_id'] = None


        if self.vals['type'] == 3 and not check_if_regex(self.vals['string']): return -7, _('Not a valid regex string!')

        if self.vals.get('case_insensitive') is not None:
            if self.vals.get('case_insensitive') not in (0,1): return -7, _('Case insensitivity must be 0 or 1!') 
        elif self.vals.get('case_ins') is not None:
            if self.vals['case_ins'] in (True, 1): self.vals['case_insensitive'] = 1
            else: self.vals['case_insensitive'] = 0

        elif self.vals.get('case_sens') is not None:
            if self.vals['case_sens'] in (True, 1): self.vals['case_insensitive'] = 0
            else: self.vals['case_insensitive'] = 1
    
        else: self.vals['case_insensitive'] = 1

        if self.vals['case_insensitive'] not in (0,1): return -7, _('Case insensitivity must be 0 or 1!')

        return 0







    def do_update(self, **kargs): self.FX.MC.ret_status = cli_msg(self.r_do_update(**kargs)) 
    def r_do_update(self, **kargs):
        """ Apply edit changes to DB """
        if not self.updating: return 0, _('Nothing to do')
        if not self.exists: return -8, _('Nothing to do. Aborting...')

        if kargs.get('validate', True): 
            err = self.validate()
            if err != 0:
                self.restore()
                return err

        err = self.constr_update()
        if err != 0:
            self.restore()
            return err

        err = self.FX.run_sql_lock(self.to_update_sql, self.filter(self.to_update))
        if err != 0:
            self.restore()
            return -2, _('DB error: %a'), err


        if self.FX.rowcount > 0:

            if not self.FX.single_run: 
                err = self.FX.load_rules()
                if err != 0: return -2, _('Error reloading rules after successfull update: %a'), err
            
            for i,u in enumerate(self.to_update):
                if u in self.immutable or u == 'id': del self.to_update[i]

            if len(self.to_update) > 1:
                self.FX.log(False, f'Rule {self.vals["id"]} updated')
                return 0, _('Rule %a updated successfuly!'), self.name()
            else:
                for f in self.to_update:
                    self.FX.log(False, f'Rule {self.name()} updated:  {f} -> {self.vals.get(f,"<NULL>")}')
                    return 0, f'{_("Rule %a updated")}:  {f} -> {self.vals.get(f,_("<NULL>"))}', self.name()
            
            return 0, _('Nothing done')

        else:
            return 0, _('Nothing done')





    def update(self, idict, **kargs): self.FX.MC.ret_status = cli_msg(self.r_update(idict, **kargs))
    def r_update(self, idict, **kargs):
        """ Quick update with a value dictionary"""
        if not self.exists: return -8, _('Nothing to do. Aborting...')

        err = self.add_to_update(idict)
        if err != 0: return err

        err = self.r_do_update(validate=True)
        return err
      



    def delete(self, **kargs): self.FX.MC.ret_status = cli_msg(self.r_delete(**kargs))
    def r_delete(self, **kargs):
        """ Delete rule by ID """
        if not self.exists: return -8, _('Nothing to do. Aborting...')

        err = self.FX.run_sql_lock("delete from rules where id = :id and learned <> 1", {'id':self.vals['id']} )
        if err != 0: return -2, _('DB Error: %a'), err
        
        if self.FX.rowcount > 0: 
            if not self.FX.single_run: 
                err = self.FX.load_rules()
                if err != 0: return -2, _('Error reloading rules after successfull delete: %a'), err

            self.FX.log(False, f'Rule {self.vals["id"]} deleted')
            return 0, _('Rule %a deleted'), self.vals['id']

        else: return 0, _('Nothing done.')





    def add(self, **kargs): self.FX.MC.ret_status = cli_msg(self.r_add(**kargs))
    def r_add(self, **kargs):
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
            if err != 0: return err

        self.clean()
        err = self.FX.run_sql_lock(self.insert_sql(all=True), self.vals)
        if err != 0: return -2, _('DB error: %a'), err
        
        self.vals['id'] = self.FX.lastrowid
        self.FX.last_rule_id = self.vals['id']

        if not self.FX.single_run: 
            err = self.FX.load_rules()
            if err != 0: return -2, _('Error reloading rules after successfull add: %a'), err

        self.FX.log(False, f'Rule {self.name(id=True)} added')
        return 0, _('Rule %a added successfully'), self.name(id=True)








class HistoryItem(SQLContainerEditable):
    """ Basic container for Feeds - in case no DB interface is needed """
    def __init__(self, FX, **kargs):
        SQLContainerEditable.__init__(self, 'search_history', HISTORY_SQL_TABLE, types=HISTORY_SQL_TYPES, **kargs)
        self.FX = FX

    def validate(self, **kargs):
        err_fld = self.validate_types()
        if err_fld != 0: return -7, _('Invalid type for field %a'), err_fld

        if self.vals['feed_id'] is not None:
            feed_id = self.FX.resolve_f_o_c(self.vals.get('feed_id'))
            if feed_id == -1: return -7, _('Channel/Category %a not found!'), self.vals.get('feed_id')
        return 0


    def add(self, phrase:dict, feed:int, **kargs):
        """ Wrapper for adding item to search history """
        if self.FX.config.get('no_history', False): return 0
        
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
            if err != 0: return err

        err = self.FX.run_sql_lock(self.insert_sql(all=True), self.vals)
        if err != 0: return -2 , _('DB error: %a'), err
        self.FX.last_history_id = self.FX.lastrowid

        # Add to local container to avoid querying database
        for i, h in enumerate(self.FX.MC.search_history):
            if h[0] == string: del self.FX.MC.search_history[i]
        self.FX.MC.search_history = [(string, now_str ,now_raw)] + self.FX.MC.search_history
        return 0










class FlagContainerBasic(SQLContainerEditable):
    """ Basic container for Flags - in case no DB interface is needed """
    def __init__(self, **kargs):
        SQLContainerEditable.__init__(self, 'flags', FLAGS_SQL_TABLE, types=FLAGS_SQL_TYPES, **kargs)


    def name(self, **kargs):
        id = kargs.get('id',False)
        if id: id_str = f' ({self.vals["id"]})'
        else: id_str = ''

        name = coalesce(self.vals['name'],'')
        sname = f'{name}{id_str}'
        if name.strip() == '':
            sname = scast(self.vals['id'], str, _('<UNKNOWN>'))
        else:
            if len(name) > 75: sname = f'{sname[:75]}...'

        return sname








class FlagContainer(FlagContainerBasic):
    """ Container for Flags """

    def __init__(self, FX, **kargs):
        FlagContainerBasic.__init__(self, **kargs)

        self.set_interface(FX)        
        self.debug = self.FX.debug
        self.config = self.FX.config

        if kargs.get('id') is not None: self.get_by_id(kargs.get('id'))


    def get_by_id(self, id:int):
        content = self.FX.qr_sql("select * from flags where id = :id", {'id':id}, one=True )
        if content in (None, (None,), ()):
            self.exists = False
            cli_msg( (-1, _('Flag %a not found!'), id) )
            return -1
        else:
            self.exists = True
            self.populate(content)
            return 0



    def validate(self, **kargs):
        """ Validate current values """
        err = self.validate_types()
        if err != 0: return -7, _('Invalid data type for %a'), err

        if self.vals['id'] in self.FX.MC.flags.keys() and self.vals['id'] != self.backup_vals['id']: return -7, _('ID taken by another flag')
        if self.vals['name'] is None or self.vals['name'] == '': return -7, _('Flag name cannot be empty!')
        if self.vals['color_cli'] is not None and self.vals['color_cli'] not in TCOLS.keys(): return -7, _('Invalid CLI color name!')

        return 0





    def do_update(self, **kargs): self.FX.MC.ret_status = cli_msg(self.r_do_update(**kargs)) 
    def r_do_update(self, **kargs):
        """ Apply edit changes to DB """
        if not self.updating: return 0, _('Nothing to do')
        if not self.exists: return -8, _('Nothing to do. Aborting...')

        if kargs.get('validate', True): 
            err = self.validate()
            if err != 0:
                self.restore()
                return err

        err = self.constr_update(allow_id=True, wheres='id = :old_id')
        if err != 0:
            self.restore()
            return err

        # This is needed because Flags can have their IDs changed ...
        to_update_filtered = self.filter(self.to_update)
        to_update_filtered['old_id'] = self.backup_vals['id']

        err = self.FX.run_sql_lock(self.to_update_sql, to_update_filtered)
        if err != 0:
            self.restore()
            return -2, _('DB error: %a'), err


        if self.FX.rowcount > 0:

            if not self.FX.single_run: 
                err = self.FX.load_flags()
                if err != 0: return -2, _('Error reloading flags after successfull update: %a'), err
            
            for i,u in enumerate(self.to_update):
                if u in self.immutable: del self.to_update[i]

            if len(self.to_update) > 1:
                self.FX.log(False, f'Flag {self.vals["id"]} updated')
                return 0, _('Flag %a updated successfuly!'), self.name()
            else:
                for f in self.to_update:
                    if f == 'id':
                        self.FX.log(False, f'Flag {self.name()}: ID changed from {self.backup_vals.get("id","<UNKNOWN>")} to {self.vals.get("id","<UNKNOWN>")}')
                        return 0, f'{_("Flag %a: ID changed from")} {self.backup_vals.get("id",_("<UNKNOWN>"))} {_("to")} {self.vals.get("id",_("<UNKNOWN>"))}', self.name()
                    else:
                        self.FX.log(False, f'Flag {self.name()} updated:  {f} -> {self.vals.get(f,"<NULL>")}')
                        return 0, f'{_("Flag %a updated")}:  {f} -> {self.vals.get(f,_("<NULL>"))}', self.name()
            
            return 0, _('Nothing done')

        else:
            return 0, _('Nothing done')




    def update(self, idict, **kargs): self.FX.MC.ret_status = cli_msg(self.r_update(idict, **kargs))
    def r_update(self, idict, **kargs):
        """ Quick update with a value dictionary"""
        if not self.exists: return -8, _('Nothing to do. Aborting...')

        err = self.add_to_update(idict, allow_id=True)
        if err != 0: return err

        err = self.r_do_update(validate=True)
        return err
      



    def delete(self, **kargs): self.FX.MC.ret_status = cli_msg(self.r_delete(**kargs))
    def r_delete(self, **kargs):
        """ Delete rule by ID """
        if not self.exists: return -8, _('Nothing to do. Aborting...')

        err = self.FX.run_sql_lock("delete from flags where id = :id", {'id':self.vals['id']} )
        if err != 0: return -2, _('DB Error: %a'), err
        
        if self.FX.rowcount > 0: 
            if not self.FX.single_run: 
                err = self.FX.load_flags()
                if err != 0: return -2, _('Error reloading flags after successfull delete: %a'), err

            self.FX.log(False, f'Flag {self.vals["id"]} deleted')
            return 0, _('Flag %a deleted'), self.vals['id']

        else: return 0, _('Nothing done.')





    def add(self, **kargs): self.FX.MC.ret_status = cli_msg(self.r_add(**kargs))
    def r_add(self, **kargs):
        """ Add feed to database """
        idict = kargs.get('new')
        if idict is not None:
            self.clear()
            self.merge(idict)
        
        if kargs.get('validate',True):
            err = self.validate()
            if err != 0: return err

        self.vals['learned'] = 0

        self.clean()
        err = self.FX.run_sql_lock(self.insert_sql(all=True), self.vals)
        if err != 0: return -2, _('DB error: %a'), err
        
        self.vals['id'] = self.FX.lastrowid
        self.FX.last_rule_id = self.vals['id']

        if not self.FX.single_run: 
            err = self.FX.load_flags()
            if err != 0: return -2, _('Error reloading flags after successfull add: %a'), err

        self.FX.log(False, f'Flag {self.name(id=True)} added')
        return 0, _('Flag %a added successfully'), self.name(id=True)
