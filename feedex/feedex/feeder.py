# -*- coding: utf-8 -*-
""" 
Main engine for Feedex news reader. Database interface and REST handling, main Fetching mechanism, interface with ling processor

"""

from feedex_headers import *







class Feeder:
    """ Main engine for Feedex. Handles SQLite3 interface, feed and entry data"""

    def __init__(self, top_parent, **kargs):

        # Make sure we are feeding metadata to and getting it from the right place ...
        if isinstance(top_parent, FeedexMainDataContainer): self.MC = top_parent
        else: raise FeedexTypeError(_('Top_parent should be an instance of FeedexMainDataContainer class!'))


        # Main configuration
        self.config = kargs.get('config', DEFAULT_CONFIG)
        self.db_path = kargs.get('db_path', self.config.get('db_path'))

        # DB errors and status 
        self.db_error = None
        self.db_status = 0

        if self.db_path is None:  
            self.db_error = _("No database given!")
            self.db_status = _("No database given!")

        # SQL rowcount etc
        self.rowcount = 0
        self.lastrowid = 0

        self.main_thread = kargs.get('main_thread', False) # Only instance in main thread is allowed actions like updating DB version, creating DB etc.
        self.allow_create = kargs.get('allow_create',False) # But sometimes we need to simply create DB :)   

        # Overload config passed in arguments
        self.debug = kargs.get('debug') # Triggers additional info at runtime
        self.timeout = kargs.get('timeout', self.config.get('timeout',15)) # Wait time if DB is locked

        self.ignore_images = kargs.get('ignore_images', self.config.get('ignore_images',False))
        self.wait_indef = kargs.get('wait_indef',False)

        # Should defaults be uploaded to newly created DB?
        self.no_defaults = kargs.get('no_defaults',False)

        # Load icons on init?
        self.load_icons = kargs.get('load_icons', False)

        # Global db lock flag
        self.ignore_lock = kargs.get('ignore_lock',False)

        # Id it a single CLI run? Needed for reloading flag
        self.single_run = kargs.get('single_run',False)

        # Hash for DB path for ID
        if self.MC.db_hash is None:
            self.MC.db_hash = hashlib.sha1(self.config.get('db_path').encode())
            self.MC.db_hash = self.MC.db_hash.hexdigest()
        self.db_hash = self.MC.db_hash

        # Is it currently fetching?
        self.is_fetching = 0

        # Last inserted ids
        self.last_entry_id = 0
        self.last_feed_id = 0
        self.last_rule_id = 0
        self.last_history_id = 0	

        # new item count
        self.new_items = 0

        self.entry = SQLContainer('entries', ENTRIES_SQL_TABLE) # Containers for entryand field processing
        self.feed = FeedContainerBasic()
        self.rule = SQLContainer('rules', RULES_SQL_TABLE)
        self.flag = SQLContainer('flags', FLAGS_SQL_TABLE)

        self.entries = [] # List of pending entries (e.g. for mass-insert)

        # ... start 
        self._connect_db()
        if self.db_status != 0: 
            self.log(True, self.db_status)
            return None
        
        if self.main_thread:
            self.refresh_data()
            if self.load_icons: self.do_load_icons()
            if not self.single_run: self.load_history()
            if self.debug in (1,2): print('Main connection established...')

        # initialize linguistic processor for tokenizing and stemming
        self.LP = LingProcessor(self.MC, **kargs)
        # And query parser ...
        if not kargs.get('no_qp', False): self.QP = FeederQueryParser(self, **kargs)






####################################################################
#   DB HANDLING
#
    



    def log(self, err:bool, *args, **kargs):
        """Handle adding log entry (add timestamp and ERROR bit)"""
        if err: err = 'ERROR: '
        else: err=''
        log_str = ''
        for a in args:
            log_str = f'{log_str} {scast(a, str, "")}'
        log_str = f"{str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}\t{err}{log_str}\n"

        try:
            with open(self.config.get('log'),'a') as logf:
                logf.write(log_str)
        except (OSError, TypeError) as e:
            cli_msg( (-1,f"{_('Could not open log file')} {self.config.get('log','<UNKNOWN>')}: %a", f'{e}') ) 




    def _connect_db(self): 
        for m in self._g_connect_db(): cli_msg(m)
    def _g_connect_db(self):
        """ Connect to SQLite and handle errors """
        db_path = self.db_path
        first_run = False # Trigger if DB is not present

        # Copy database from shared dir to local dir if not present (e.g. fresh install)
        if not os.path.isfile(db_path):
            if not self.main_thread and not self.allow_create: 
                self.db_status = f"""{_('Could not connect to')} {db_path}"""
                return -1

            first_run = True
            yield 0, _('SQLite Database not found. Creating new one at %a'), db_path
            # Create directory if needed
            db_dir = os.path.dirname(db_path)
            if not os.path.isdir(db_dir) and db_dir != '':
                err = os.makedirs(db_dir)
                if err == 0: yield 0, _('Folder %a created...'), db_dir
                else: 
                    yield -1, _('Error creating DB foler %a'), db_dir
                    return -1

        try:
            self.conn = sqlite3.connect(db_path)
            self.curs = self.conn.cursor()
        except (sqlite3.Error, sqlite3.OperationalError, OSError) as e: 
            yield -2, _('DB connection error: %a'), e
            self.db_status = f"""{_('Error connecting to:')} {db_path}"""
            return -2

        # Update connection number and aquire ID
        self.MC.conns += 1
        self.conn_id = self.MC.conns

        if self.debug in (1,2): print(f"{_('Connected to')} {db_path} ({self.conn_id})")

        # Some technical stuff...
        try:
            with self.conn:
                self.curs.execute("PRAGMA case_sensitive_like=true")
        except sqlite3.Error as e:
            yield -2, f'{_("Error setting up PRAGMA")} ({self.conn_id}): %a', e
            return -2

        # If not in main thread - not do version checks and other maintenance
        if not self.main_thread and not self.allow_create: return 0

        if first_run:

            # Run DDL on fresh DB
            try:
                with open(f'{FEEDEX_SYS_SHARED_PATH}{DIR_SEP}data{DIR_SEP}db_scripts{DIR_SEP}base{DIR_SEP}feedex_db_ddl.sql', 'r') as sql:
                    sql_ddl = sql.read()
                with self.conn:
                    self.curs.executescript(sql_ddl)
            except (sqlite3.Error, sqlite3.OperationalError, OSError) as e:
                yield -2, _('Error writing DDL scripts to database! %a'), e
                self.db_status = f"""{_('Error writing DDL scripts to database!')} {e}"""
                return -2

            yield 0, _('Database structure created')

            if not self.no_defaults:
                try:
                    with open(f'{FEEDEX_SYS_SHARED_PATH}{DIR_SEP}data{DIR_SEP}db_scripts{DIR_SEP}base{DIR_SEP}feedex_db_defaults.sql', 'r') as sql:
                        sql_ddl = sql.read()
                    with self.conn:
                        self.curs.executescript(sql_ddl)
                except (sqlite3.Error, sqlite3.OperationalError, OSError) as e:
                    yield -2, _('Error writing defaults to database: %a'), e
                    self.db_status = f"""{_("Error writing defaults to database:")} {e}"""
                    return -2

                yield 0, 'Added some defaults...'

        # Checking versions and updating if needed
        try: version = slist(self.curs.execute("select val from params where name = 'version'").fetchone(), 0, None)
        except (sqlite3.Error, sqlite3.OperationalError, OSError) as e:
                yield -2, _('Error getting version from DB: %a'), e
                self.db_status = f"""{_("Error getting version from DB:")} {e}"""
                return -2
            
        ver_diff = check_version(version, FEEDEX_VERSION)
        if ver_diff == -1:
            yield -1, _('Application version too old for %a Database! Aborting'), db_path
            self.db_status = f'{_("Application version too old for")} {db_path} {_("Database! Aborting")}'
            return -1    

        elif ver_diff == 1:

            if not self.main_thread:
                self.db_status = _('Cannot update DB from this instance')
                return -1

            yield 0, _('Database %a version too old... Updating...'), db_path

            #Run DDL scripts if file is fresly created and then add some default data to tables (feeds and prefixes) """
            # ... and attempt to update it ...

            # ... make a clean backup
            self.conn.rollback()
            self.conn.close()
            try:
                copyfile(db_path, f'{db_path }.bak')
            except OSError as e:
                self.db_status = f"""{_('Error creating database backup to')} {db_path}.bak: {e}"""
                yield -1, f"""{_("Error creating database backup to")} {db_path}.bak: %a""", e
                return -1
            
            try:
                self.conn = sqlite3.connect(db_path)
                self.curs = self.conn.cursor()
            except (sqlite3.Error, sqlite3.OperationalError, OSError) as e: 
                yield -2, _('DB reconnection error: %a'), e
                self.db_status = f'{_("DB reconnection error:")} {e}'
                return -2

            for d in sorted( os.listdir(f'{FEEDEX_SYS_SHARED_PATH}{DIR_SEP}data{DIR_SEP}db_scripts') ):

                if d != 'base' and d <= FEEDEX_VERSION:
                    ver_path = os.path.join(f'{FEEDEX_SYS_SHARED_PATH}{DIR_SEP}data{DIR_SEP}db_scripts',d)
                    for f in sorted( os.listdir(ver_path) ):
                        scr_path = os.path.join(ver_path, f)
                        if os.path.isfile(scr_path):
                            yield 0, _('Running update script... %a'), scr_path 
                            try:
                                with open(scr_path) as sql_file:
                                    update_script = sql_file.read()
                                with self.conn:
                                    self.curs.executescript(update_script)
                            except (sqlite3.Error, sqlite3.OperationalError, OSError) as e:
                                yield -2, f"""{_('Error running %a script')} ({e})! {_('Attempting to restore database')}""", scr_path
                                # Restore backup...
                                self.close()
                                try:
                                    os.remove(db_path)
                                    copyfile(db_path + '.bak', db_path)
                                except OSError as e:
                                    self.log(True, f'{_("Error restoring")} {db_path} {_("database!")} {e}' )
                                    yield -1, f'{_("Error restoring %a database!")} {e}', db_path
                                finally: 
                                    self.log(False, f'{_("Database")} {db_path} {_("restored ...")}')
                                    yield 0, _('Database %a restored ...'), db_path

                                self.db_status = _('Version update error')
                                return -1
            
            yield 0, _('Database updated successfully')
            yield 0, _('Deleting backup ...')
            try: os.remove(f'{db_path }.bak')
            except OSError as e:
                self.db_status = f'{_("Error removing")} {db_path}.bak: {e}'
                yield -1, f'{_("Error removing")} {db_path}.bak: %a', e
                return -1 
            yield 0, _('Backup database removed successfully')


    def _reset_connection(self, **kargs):
        """ Reset connection to database, rollback all hanging transactions and unlock"""
        try:
            self.conn.rollback()
            self.conn.close()
            self._connect_db()
            self.unlock()
            if kargs.get('log',False): self.log(False, f"{_('Connection')} {self.conn_id} {_('reset')}")
        except (sqlite3.Error, sqlite3.OperationalError) as e:
            if kargs.get('log',False): self.log(True, f"{_('Connection')} {self.conn_id} {_('reset failed')}")
            cli_msg( (-2, _('Connection %a reset failed!'), self.conn_id) )






    # Database lock and handling it with timeout - waiting for availability
    def lock(self, **kargs):
        """ Locks DB """
        try:
            with self.conn:
                self.curs.execute("insert into params values('lock', 1)")
        except (sqlite3.Error, sqlite3.OperationalError) as e:
            if hasattr(e, 'message'): err = e.message 
            else: err = e
            self.db_error = err
            self.MC.ret_status = -2
            self.log(True, f'{_("DB error")} ({self.conn_id} - {_("locking")}): {err}')
            cli_msg( (-2, f'{_("DB error")} ({self.conn_id} - {_("locking")}): %a', err) )
            return e
            
        self.MC.db_lock = True
        if kargs.get('verbose', False): cli_msg( (0, _('Database locked')) )
        return 0

    def unlock(self, **kargs):
        """ Unlocks DB """
        if kargs.get('ignore',False): return 0
        # Need to do a loop to make sure DB is unlocked no matter what
        tm = 0
        while tm <= self.timeout or self.wait_indef:        
            try:
                with self.conn:
                    self.curs.execute("delete from params where name='lock'")
                self.MC.db_lock = False
                if kargs.get('verbose', False): cli_msg( (0, _('Database unlocked')) )
                return 0
            except (sqlite3.Error, sqlite3.OperationalError) as e:
                if hasattr(e, 'message'): err = e.message 
                else: err = e
                self.db_error = err
                self.MC.ret_status = -2
                self.log(True, f'{_("DB error")} ({self.conn_id} - {_("unlocking")}): {err}')
                cli_msg( (-2, f'{_("DB error")} ({self.conn_id} - {_("unlocking")}): %a', err) )
            tm = tm + 1
            time.sleep(1)
        
        cli_msg((-1, f'{_("Failed to unlock DB")} ({self.conn_id})'))
        self.MC.ret_status = -4
        return -1

    
    def locked(self, **kargs):
        """ Checks if DB is locked and waits the timeout checking for availability before aborting"""
        if kargs.get('ignore',False): return False
        if self.ignore_lock: return False
        timeout = kargs.get('timeout', self.timeout)

        tm = 0
        while tm <= timeout or self.wait_indef:
            if not self.MC.db_lock: lock = self.qr_sql("select * from params where name = 'lock'", one=True)
            else: lock = 1

            if lock is not None or self.db_error is not None: 
                cli_msg( (-4, f"{_('Database locked')} ({self.conn_id})... {_('Waiting')}... {tm}") )     
            else:
                self.lock()
                return False
            tm = tm + 1
            time.sleep(1)

        self.MC.ret_status = cli_msg( (-4, f'{_("Timeout reached")} ({self.conn_id}). {_("Aborting")}...') )
        return True




    def _run_sql(self, query:str, vals:list, **kargs):
        """ Safely run a SQL insert/update """
        many = kargs.get('many',False)
        try:
            if many:
                with self.conn: self.curs.executemany(query, vals)
            else: 
                with self.conn: self.curs.execute(query, vals)
            self.rowcount = self.curs.rowcount
            self.lastrowid = self.curs.lastrowid
            self.db_error = None
            return 0
        except (sqlite3.Error, sqlite3.OperationalError) as e:
            if hasattr(e, 'message'): err = e.message
            else: err = e
            self.db_error = err
            self.MC.ret_status = -2
            self.log(True, f'{_("DB error")} ({self.conn_id} - {_("write")}): {err} ({query})')
            cli_msg( (-2, f'{_("DB error")} ({self.conn_id} - {_("write")}): %a ({query})', err) )
            

    # Below are 2 methods of safely inserting to and updating
    # All actions on DB should be performed using them!
    def run_sql_lock(self, query:str, vals:list, **kargs):
        """ Run SQL with locking and error catching """
        if self.locked(ignore=kargs.get('ignore_lock', False)): return _('Database busy')
        e = self._run_sql(query, vals, **kargs)
        self.unlock()
        return e

    def run_sql_multi_lock(self, qs:list, **kargs):
        """ Run list of queries with locking """
        if self.locked(ignore=kargs.get('ignore_lock', False)): return _('Datbase busy')
        e = 0
        for q in qs:
            e = self._run_sql(q[0], q[1], many=False)
            if e != 0: break
        self.unlock()
        return e





    def qr_sql(self, sql:str,*args, **kargs):
        """ Query databasse - no locking """
        many = kargs.get('many', False)
        fetch_one = kargs.get('one', False)
        fetch_all = kargs.get('all', False)
        if kargs.get('ignore_errors', True): self.db_error = None
        elif self.db_error is not None: return ()

        tm=0
        ready = False
        while tm <= LOCAL_DB_TIMEOUT: # This will queue the query if there is something else going on locally...
            if not self.MC.db_lock: 
                ready = True
                break
            elif self.debug in (1,2): cli_msg ( (-2, f'DB locked locally (sql: {sql}) ({self.conn_id})... waiting {tm}') )
            tm += 1
            time.sleep(1)

        if not ready: 
            cli_msg( (-2, f'{_("DB error")} ({self.conn_id} - {_("read")}): %a ({sql})', _('Local lock timeout reached')) )
            self.db_error = _('Local lock timeout reached')
            self.MC.ret_status = -2
            return ()
        

        try:
            self.MC.db_lock = True        
            if many: 
                with self.conn: return self.curs.executemany(sql, *args)
            else:
                if fetch_all: 
                    with self.conn: return self.curs.execute(sql, *args).fetchall()
                elif fetch_one: 
                    with self.conn: return self.curs.execute(sql, *args).fetchone()
            
            
        except (sqlite3.Error, sqlite3.OperationalError) as e:            
            if hasattr(e, 'message'): err = e.message 
            else: err = e
            self.db_error = err
            self.MC.ret_status = -2
            self.log(True, f'{_("DB error")} ({self.conn_id} - {_("read")}): {err} ({sql})')
            cli_msg( (-2, f'{_("DB error")} ({self.conn_id} - {_("read")}): %a ({sql})', err) )
            self.conn.rollback()
            self.MC.db_lock = False
            return ()

        finally: self.MC.db_lock = False 



    def update_ret_code(self, status):
        """ Updates main return code if error occurred """
        if status != 0: self.MC.ret_status = status


    def _disconnect(self):
        """ Wrapper for updating connection count """
        if self.debug in (1,2): print(f'Disconnecting connection {self.conn_id}')
        self.MC.conns -= 1

    def close(self, **kargs):
        """ Closes connection. Probably not required, but still """
        try:
            self.conn.rollback()
            self.conn.close()
        except (sqlite3.Error, sqlite3.OperationalError) as e:
            self.MC.ret_status = cli_msg( (-2, f'{_("DB error")}: %a ({_("on close")})', err) )

    def __del__(self):
        self._disconnect()




############################################################3
#  FEEDEX-specific entities hanlding
#

    def load_feeds(self):
        """Get feed data from database"""
        if self.debug in (2,): print('Loading feeds ...')
        feeds = self.qr_sql(f'{GET_FEEDS_SQL}', all=True)
        if self.db_error is None: 
            self.MC.feeds = feeds
            return 0
        else: return self.db_error


    def do_load_icons(self):
        """ Loads icon paths for feeds """
        self.MC.icons = {}

        for f in self.MC.feeds:
            id = f[self.feed.get_index('id')]
            handler = f[self.feed.get_index('handler')]
            is_category = f[self.feed.get_index('is_category')]
            icon_name = scast(f[self.feed.get_index('icon_name')], str, '')
            
            if icon_name != '':
                if os.path.isfile(f'{FEEDEX_SYS_ICON_PATH}{DIR_SEP}{icon_name}.svg'):
                    self.MC.icons[id] = f'{FEEDEX_SYS_ICON_PATH}{DIR_SEP}{icon_name}.svg'
                    continue
                elif os.path.isfile(icon_name):
                    self.MC.icons[id] = icon_name
                    continue

            if is_category == 1:
                self.MC.icons[id] = f'{FEEDEX_SYS_ICON_PATH}{DIR_SEP}document.svg'
            
            elif handler == 'rss':
                if os.path.isfile(f'{FEEDEX_ICON_PATH}{DIR_SEP}feed_{id}_{self.db_hash}.ico'):
                    self.MC.icons[id] = f'{FEEDEX_ICON_PATH}{DIR_SEP}feed_{id}_{self.db_hash}.ico'
                else: 
                    self.MC.icons[id] = f'{FEEDEX_SYS_ICON_PATH}{DIR_SEP}news-feed.svg'
            elif handler == 'html':
                if os.path.isfile(f'{FEEDEX_ICON_PATH}{DIR_SEP}feed_{id}_{self.db_hash}.ico'):
                    self.MC.icons[id] = f'{FEEDEX_ICON_PATH}{DIR_SEP}feed_{id}_{self.db_hash}.ico'
                else: 
                    self.MC.icons[id] = f'{FEEDEX_SYS_ICON_PATH}{DIR_SEP}www.svg'
            elif handler == 'script':
                if os.path.isfile(f'{FEEDEX_ICON_PATH}{DIR_SEP}feed_{id}_{self.db_hash}.ico'):
                    self.MC.icons[id] = f'{FEEDEX_ICON_PATH}{DIR_SEP}feed_{id}_{self.db_hash}.ico'
                else: 
                    self.MC.icons[id] = f'{FEEDEX_SYS_ICON_PATH}{DIR_SEP}script.svg'

            elif handler == 'local':
                self.MC.icons[id] = f'{FEEDEX_SYS_ICON_PATH}{DIR_SEP}mail.svg'


    def load_rules(self, **kargs):
        """Get learned and saved rules from DB"""
        if self.debug in (2,): print('Loading rules ...')
        no_limit = kargs.get('no_limit',False)
        limit = scast(self.config.get('rule_limit'), int, 50000)

        if not self.config.get('use_keyword_learning', True):  #This config flag tells if we should learn and rank autoatically or by manual rules only
            rules = self.qr_sql(GET_RULES_NL_SQL, all=True)
        else:
            if no_limit or limit == 0:
                rules = self.qr_sql(GET_RULES_SQL, all=True)
            else:
                rules = self.qr_sql(f'{GET_RULES_SQL}LIMIT :limit', {'limit':limit} , all=True)           

        if self.db_error is None: 
            self.MC.rules = rules
            return 0
        else: return self.db_error


    def load_history(self, **kargs):
        """ Get search history """
        history = self.qr_sql(f'{SEARCH_HISTORY_SQL} desc', all=True)
        if self.db_error is None:
            self.MC.search_history = history
            return 0
        else: return self.db_error


    def load_flags(self, **kargs):
        """ Build Flag dictionary """
        flag_list = self.qr_sql(f'select * from flags', all=True)
        if self.db_error is None:
            flag_dict = {}
            for fl in flag_list:
                flag_dict[fl[self.flag.get_index('id')]] = ( fl[self.flag.get_index('name')], fl[self.flag.get_index('desc')], fl[self.flag.get_index('color')], fl[self.flag.get_index('color_cli')] )
            self.MC.flags = flag_dict.copy()
            return 0
        else: return self.db_error



    def resolve_flag(self, val:str, **kargs):
        """ Resolve flag by name or ID """
        if val is None: return None
        if type(val) is int:
            if val in self.MC.flags.keys(): return val
        val = scast(val, str, -1)
        if val == -1: return -1
        if val.isdigit():
            if int(val) in self.MC.flags.keys(): return int(val)
        for k,v in self.MC.flags.items():
            if val == v[self.flag.get_index('name')-1]: return k
        return -1

    def get_flag_name(self, id:int, **kargs):
        if id not in self.MC.flags.keys(): return '<UNKNOWN>' 
        name = self.MC.flags.get(id, (None,))[0]
        if name in (None, ''): return f'{id}'
        else: return name


    def get_flag_color(self, id:int, **kargs):
        if id not in self.MC.flags.keys(): return None
        color = self.MC.flags.get(id, (None,None,self.config.get('gui_default_flag_color',None)))[2]
        if color in (None, ''): return None
        else: return color


    def get_flag_color_cli(self, id:int, **kargs):
        if id not in self.MC.flags.keys(): return ''
        color = self.MC.flags.get(id, (None,None,None,self.config.get('TERM_FLAG', TERM_FLAG)))[3]
        if color in (None, ''): return self.config.get('TERM_FLAG', TERM_FLAG)
        else: return color
        





    def resolve_category(self, val:str, **kargs):
        """ Resolve entry type depending on whether ID or name was given"""
        if val is None: return None
        load = kargs.get('load', False)
        if scast(val, str, '').isdigit():
            val = int(val)
            for f in self.MC.feeds:
                if f[self.feed.get_index('id')] == val and f[self.feed.get_index('is_category')] == 1: 
                    if load: return f
                    else: return f[self.feed.get_index('id')]
        else:
            val = str(val)
            for f in self.MC.feeds:
                if f[self.feed.get_index('name')] == val and f[self.feed.get_index('is_category')] == 1: 
                    if load: return f
                    else: return f[self.feed.get_index('id')]
        return -1

    def resolve_feed(self, val:int, **kargs):
        """ check if feed with given ID is present """
        if val is None: return None
        load = kargs.get('load', False)
        val = scast(val, int, None)
        if val is None: return -1
        if val < 0: return -1
        for f in self.MC.feeds:
            if val == f[self.feed.get_index('id')] and f[self.feed.get_index('is_category')] != 1: 
                if load: return f
                else: return f[self.feed.get_index('id')]
        return -1

    def resolve_f_o_c(self, val, **kargs):
        """ Resolve feed or category """
        if val is None: return None
        if type(val) is not int: return -1
        if val < 0: return -1
        load = kargs.get('load', False)
        for f in self.MC.feeds:
            if f[self.feed.get_index('id')] == val:
                if load: return f
                if f[self.feed.get_index('is_category')] == 1: return -1, val
                return val, -1
        return -1



    def resolve_field(self, val:str):
        """ Resolve field ID depending on provided field name. Returns -1 if field is not in prefixes """
        if val is None: return None
        if val in PREFIXES.keys(): return val
        return -1


    def resolve_qtype(self, qtype, **kargs):
        """ Resolve query type from string to int """
        if qtype is None: 
            if kargs.get('no_null', False): return -1
            return 1
        if type(qtype) is int and qtype in (0,1,2,3,4,5,): return qtype
        if type(qtype) is str:
            if qtype.lower() in ('string','str',):
                return 0
            elif qtype.lower() in ('full', 'fts', 'full-text','fulltext',):
                return 1
            elif qtype.lower() in ('exact','fts-exact','exact-fts',):
                return 2
            else: return 1

        return -1




    def refresh_data(self, **kargs):
        """Refresh all data (wrapper)"""
        err = self.load_feeds()
        if err == 0: err = self.load_rules()
        if err == 0: err = self.load_flags()
        return err
		





    # Database statistics...
    def update_stats(self):
        """ Get DB statistics and save them to params table for quick retrieval"""

        if self.debug in (1,2): print("Updating database document statistics...")

        doc_count = scast( self.qr_sql(DOC_COUNT_SQL, one=True)[0], int, 0)
        if self.db_error is not None: return self.db_error

        self.MC.doc_count = doc_count
        err = self.run_sql_multi_lock(  (("delete from params where name = 'doc_count'", () ),\
                                    ("insert into params values('doc_count', :doc_count)", {'doc_count':doc_count} )) \
                                )

        if self.debug in (1,2):
            print("Done:")
            print("Doc count: ", doc_count, " ")
        return err


    def get_doc_count(self, **kargs):
        """ Retrieve entry count from params"""
        if self.MC.doc_count is not None: return self.MC.doc_count
        doc_count = self.qr_sql("select val from params where name = 'doc_count'", one=True)
        if doc_count in (None, (None,),()):
            self.update_stats()
            doc_count = self.qr_sql("select val from params where name = 'doc_count'", one=True)
            if doc_count in (None, (None,),()): return self.MC.doc_count
        doc_count = scast(doc_count[0], int, 1)
        self.MC.doc_count = doc_count
        return doc_count





###############################################
# ENTRIES


    def add_entries(self, **kargs):
        for m in self.g_add_entries(**kargs): self.update_ret_code( cli_msg(m) )
    def g_add_entries(self, **kargs):
        """ Wraper for inseting entries from list of dicts or a file """
        learn = kargs.get('learn', self.config.get('use_keyword_learning', True))
        pipe = kargs.get('pipe',False)
        efile = kargs.get('efile')
        elist = kargs.get('elist')

        contents = ''
        if elist is None:
            if pipe:
                for line in sys.stdin: contents = f"{contents}\n{line}"
            elif efile is not None:
                try:
                    with open(efile, "r") as f:
                        contents = f.read()
                except OSError as e: 
                    yield -6, f'{_("Error reading file")} {efile}: %a', e
                    return -6

            try:
                elist = json.loads(contents)
            except (json.JSONDecodeError) as e:
                yield -6, _('Error parsing JSON: %a'), e
                return -6

        # Validate data received from json
        if not isinstance(elist, (list, tuple)): 
            yield -6, _('Invalid input: must be a list of dicts!')
            return -6

        
        entry = EntryContainer(self)
        elist_len = len(elist)        
        num_added = 0

        # Queue processing
        for i,e in enumerate(elist):

            if not isinstance(e, dict):
                if elist_len > 1: self.log(True, f'Error mass-adding entries! Input entry no. {i} is not a dictionary!')
                yield -6, _('Input entry no. %a is not a dictionary!'), i
                continue

            entry.clear()
            entry.merge(e)
            entry.learn = learn
            
            err = False
            for msg in entry.g_add(new=e, update_stats=False): 
                if msg[0] != 0: 
                    if elist_len > 1: self.log(True, f'Error mass-adding entries! Input entry no. {i}: {err}')
                    err = True
                yield msg
            if not err: num_added += 1

        # stat
        if num_added > 0:
            self.update_stats()
            if not self.single_run: self.load_rules()

        if num_added > 1: 
            self.log(False, f'Added {num_added} new entries')
            yield 0, _('Added %a new entries'), num_added
        return 0








######################################
#       Fetching


    def get_last(self, **kargs):
        """ Get timestamp of last news check """
        ord = scast(kargs.get('ord'), int, 1) - 1
        if self.MC.fetches is None:
            self.MC.fetches = self.qr_sql("select time, datetime(time,'unixepoch', 'localtime') from actions where name = 'fetch' order by time DESC limit :limit", {'limit':MAX_LAST_UPDATES}, all=True)
            if self.db_error is not None: return -1

        if ord < 0: return -1
        row = slist(self.MC.fetches, ord, None)
        if row is None: return 0
        fetch = slist(row, 0, None)
        if row is None: return -1
        return scast(fetch, int, -1)



    def lock_fetching(self, **kargs):
        """ Check if someone is currently fetching to DB """
        self.is_fetching = self.qr_sql("select val from params where name = 'is_fetching'", one=True)
        if self.db_error is not None: return -1
        if self.is_fetching in (None, (None,)): 
            self.is_fetching = 0
            self.run_sql_lock("insert into params values('is_fetching','0')", ())

        self.is_fetching = scast(self.is_fetching, int, 0)
        if kargs.get('check_only',False): return self.is_fetching

        if self.is_fetching == 0:
            self.run_sql_lock("update params set val='1' where name = 'is_fetching'", ())
            if kargs.get('verbose',False): print(_('Database locked for fetching!'))
            return 0
        else: 
            if kargs.get('verbose',False): print(_('Database already locked for fetching!'))
            return -1


    def unlock_fetching(self, **kargs):
        """ Unmark 'is_fetching' flag """
        err = self.run_sql_lock("update params set val='0' where name = 'is_fetching'", ())
        if self.rowcount == 0: 
            err = self.run_sql_lock("insert into params values('fetching','0')", ())
        if err != 0:
            cli_msg((-2, _('Error while unlocking for fetching: %a'), err))
            return -2, _('Error while unlocking for fetching: %a'), err

        self.is_fetching = 0
        if kargs.get('verbose',False): print(_('Database unlocked for fetching!'))
        return 0








    def fetch(self, **kargs): 
        for m in self.g_fetch(**kargs): self.update_ret_code( cli_msg(m) )
    def g_fetch(self, **kargs):
        """ Check for news taking into account specified intervals and defaults as well as ETags and Modified tags"""

        if self.lock_fetching() != 0:
            yield -4, _('Someone else is currently fetching to the database?')
            return -4


        feed_ids = scast(kargs.get('ids'), tuple, None)
        feed_id = scast(kargs.get('id'), int, 0)

        force = kargs.get('force', False)
        ignore_interval = kargs.get('ignore_interval', True)

        skip_ling = kargs.get('skip_ling',False)
        update_only = kargs.get('update_only', False)

        started_raw = datetime.now()
        started = int(started_raw.timestamp())
        started_str = started_raw.strftime("%Y.%m.%d %H:%M:%S")
        self.new_items = 0

        tech_counter = 0
        meta_updated = False

        handler = None
        # Data handlers init - to load later...
        rss_handler = None
        html_handler = None
        script_handler = None
        
        for feed in self.MC.feeds:

            self.feed.clear()
            self.feed.populate(feed)

            # Check for processing conditions...
            if self.feed['deleted'] == 1 and not update_only and feed_id == 0: continue
            if self.feed['fetch'] in (None,0) and feed_id == 0 and feed_ids is None: continue
            if feed_id != 0 and feed_id != self.feed['id']: continue
            if feed_ids is not None and self.feed['id'] not in feed_ids: continue
            if self.feed['is_category'] not in (0,None) or self.feed['handler'] in ('local'): continue

            # Ignore unhealthy feeds...
            if scast(self.feed['error'],int,0) >= self.config.get('error_threshold',5) and not kargs.get('ignore_errors',False):
                yield 0, _('Feed %a ignored due to previous errors'), self.feed.name(id=True)
                continue

            #Check if time difference exceeds the interval
            last_checked = scast(self.feed['lastchecked'], int, 0)
            if not ignore_interval:
                diff = (started - last_checked)/60
                if diff < scast(self.feed['interval'], int, self.config.get('default_interval',45)):
                    if self.debug in (1,): print(f'Feed {self.feed["id"]} ignored (interval: {self.feed["interval"]}, diff: {diff})')
                    continue

            yield 0, _('Processing %a ...'), self.feed.name()

            entries_sql = []

            now = datetime.now()
            now_raw = int(now.timestamp())
            last_read = scast(self.feed['lastread'], int, 0)
            
            
            # Choose/lazy-load appropriate handler           
            if self.feed['handler'] == 'rss':
                if rss_handler is None: rss_handler = FeedexRSSHandler(self)
                handler = rss_handler
            
            elif self.feed['handler'] == 'html':
                if html_handler is None: html_handler = FeedexHTMLHandler(self)
                handler = html_handler
            
            elif self.feed['handler'] == 'script':
                if script_handler is None: script_handler = FeedexScriptHandler(self)
                handler = script_handler

            elif self.feed['handler'] == 'local':
                yield 0, _('Channel handled locally... Ignoring...')
                continue
            
            else:
                yield -3, _('Handler %a not recognized!'), self.feed['handler']
                continue     

            # Set up feed-specific user agent
            if self.feed['user_agent'] not in (None, ''):
                yield 0, _('Using custom User Agent: %a'), self.feed['user_agent']
                handler.set_agent(self.feed['user_agent'])
            else: handler.set_agent(None)

            # Start fetching ...
            if not update_only:

                pguids = self.qr_sql("""select distinct guid from entries e where e.feed_id = :feed_id""", {'feed_id':self.feed['id']} , all=True)
                if handler.compare_links:
                    plinks = self.qr_sql("""select distinct link from entries e where e.feed_id = :feed_id""", {'feed_id':self.feed['id']} , all=True, ignore_errors=False)
                else:
                    plinks = ()
                
                if self.db_error is not None: 
                    self.log(True, f'{_("Feed")} {self.feed.name()} {_("ignored due to DB error")}: {self.db_error}')
                    yield -2, f'{_("Feed")} {self.feed.name()} {_("ignored due to DB error")}: %a', self.db_error
                    continue

                handler.set_feed(self.feed)
                for item in handler.fetch(self.feed, force=force, pguids=pguids, plinks=plinks, last_read=last_read, last_checked=last_checked):
                    
                    if isinstance(item, EntryContainer):
                        self.new_items += 1
                        err = item.validate_types()
                        if err != 0: 
                            yield -7, f'{_("Error while processing entry")} {self.new_items}: {_("Invalid data type for")} %a', err
                            continue
                        
                        if not skip_ling:
                            item.ling(index=True, stats=True, rank=True)
                            vals = item.vals.copy()
                            if isinstance(vals, dict): entries_sql.append(vals)
                            else: yield -1, _('Error while linguistic processing %a!'), item
                        else:
                            entries_sql.append(item.vals.copy())

                        # Track new entries and take care of massive insets by dividing them into parts
                        tech_counter += 1
                        if tech_counter >= self.config.get('max_items_per_transaction', 300):
                            err = self.run_sql_lock(self.entry.insert_sql(all=True), entries_sql, many=True)
                            if err != 0: yield -2, _('DB error: %a'), err
                            else: entries_sql = []                # If error occurs do not clear the pipeline in hope that it will succeed on next try

                            tech_counter = 0  


                    elif isinstance(item, (tuple, list)):
                        yield item
                    else:
                        yield -3, _('Unknown error: %a'), item


                # Push final entries to DB
                if len(entries_sql) > 0:
                    err = self.run_sql_lock(self.entry.insert_sql(all=True), entries_sql, many=True)
                    if err != 0: yield -2, _('DB error: %a'), err


            else:
                handler.set_feed(self.feed)
                msg = handler.download(force=force)
                if msg != 0: yield -3, _('Handler error: %a'), msg



            if handler.error:
                # Save info about errors if they occurred
                if update_only:
                    err = self.run_sql_lock("""update feeds set http_status = :status, error = coalesce(error,0)+1 where id = :id""", {'status': handler.status, 'id': self.feed['id']} )
                else:
                    err = self.run_sql_lock("""update feeds set lastchecked = :now, http_status = :status, error = coalesce(error,0)+1 where id = :id""", {'now':now_raw, 'status':handler.status, 'id': self.feed['id']} )
                if err != 0: yield -2, _('DB error: %a'), err

                continue

            else:				
                #Update feed last checked date and other data
                if update_only:
                    err = self.run_sql_lock("""update feeds set http_status = :status, error = 0  where id = :id""", {'status':handler.status, 'id': self.feed['id']} )
                else:
                    err = self.run_sql_lock("""update feeds set lastread = :now, lastchecked = :now, etag = :etag, modified = :modified, http_status = :status, error = 0  where id = :id""", 
                    {'now':now_raw, 'etag':handler.etag, 'modified':handler.modified, 'status':handler.status, 'id':self.feed['id']} )
                if err != 0: yield -2, _('DB error: %a'), err


            # Inform about redirect
            if handler.redirected: 
                self.log(False, f"{_('Channel redirected')} ({self.feed['url']})")
                yield 0, f'{_("Channel redirected")} (%a)', self.feed['url']

            # Save permanent redirects to DB
            if handler.feed_raw.get('href',None) != self.feed['url'] and handler.status == 301:
                self.feed['url'] = rss_handler.feed_raw.get('href',None)
                if not update_only and kargs.get('save_perm_redirects', self.config.get('save_perm_redirects', False) ):
                    err = self.run_sql_lock('update feeds set url = :url where id = :id', {'url':self.feed['url'], 'id':self.feed['id']} )    
                    if err != 0: yield -2, _('DB error: %a'), err

            # Mark deleted as unhealthy to avoid unnecessary fetching
            if handler.status == 410 and self.config.get('mark_deleted',False):
                err = self.run_sql_lock('update feeds set error = :err where id = :id', {'err':self.config.get('error_threshold',5), 'id':self.feed['id']})
                if err != 0: yield -2, _('DB error: %a'), err



            # Autoupdate metadata if needed or specified by 'forced' or 'update_only'
            if (scast(self.feed['autoupdate'], int, 0) == 1 or update_only) and not handler.no_updates:

                yield 0, _('Updating metadata for %a'), self.feed.name()

                msg = handler.update(self.feed, ignore_images=self.config.get('ignore_images',False))
                if msg != 0: yield -3, _('Handler error: %a'), msg
                else:

                    updated_feed = handler.feed

                    if updated_feed == -1:
                        yield -3, _('Error updating metadata for feed %a'), self.feed.name(id=True)
                        continue
                    elif updated_feed == 0:
                        continue
                    
                    err = updated_feed.validate_types()
                    if err != 0: yield -7, _('Invalid data type for %a'), err
                    else:
                        err = self.run_sql_lock(updated_feed.update_sql(wheres=f'id = :id'), updated_feed.vals)
                        if err != 0: yield -2, _('DB Error: %a'), err
        
                    meta_updated = True
                    yield 0, _('Metadata updated for feed %a'), self.feed.name()


            # Stop if this was the specified feed...
            if feed_id != 0: break



        if meta_updated and not self.single_run: self.load_feeds()

        if self.new_items > 0:
            err = self.run_sql_lock("""insert into actions values('fetch', :started)""", {'started':started} )
            if err != 0: yield -2, _('DB Error: %a'), err
            else: 
                if self.MC.fetches is None: self.get_last()
                self.MC.fetches.insert(0, (started, started_str) )

        if kargs.get('update_stats',True):
            if self.new_items > 0: self.update_stats()

        if not update_only: yield 0, _('Finished fetching (%a new articles)'), self.new_items
        else: yield 0, _('Finished updating metadata')

        self.unlock_fetching()
        return 0







#################################################
# Utilities 


    def clear_history(self, **kargs): self.MC.ret_status = cli_msg(self.r_clear_history(**kargs))
    def r_clear_history(self, **kargs):
        """ Clears search history """
        err = self.run_sql_lock("delete from search_history",())
        if err != 0: return -2, _('DB error: %a'), err
        else: items_deleted = self.rowcount
        self.load_history()
        return 0, _('Deleted %a items from search history'), items_deleted
        
        



    def delete_learned_rules(self, **kargs): self.MC.ret_status = cli_msg(self.r_delete_learned_rules(**kargs))
    def r_delete_learned_rules(self, **kargs):
        """ Deletes all learned rules """
        err = self.run_sql_lock("""delete from rules where learned = 1""",[])
        if err != 0: return -2, _('DB error: %a'), err
        else:
            if not self.single_run: self.load_rules()
            deleted_rules = self.rowcount
            return 0, _('Deleted %a learned rules'), deleted_rules




    def empty_trash(self, **kargs): self.MC.ret_status = cli_msg(self.r_empty_trash(**kargs))
    def r_empty_trash(self, **kargs):
        """ Removes all deleted items permanently """
        # Delete permanently with all data
        rules_deleted = 0
        entries_deleted = 0
        feeds_deleted = 0
        err = self.run_sql_lock(EMPTY_TRASH_RULES_SQL,[])
        rules_deleted = self.rowcount
        if err == 0: 
            err = self.run_sql_lock(EMPTY_TRASH_ENTRIES_SQL,[])
            entries_deleted = self.rowcount
        if err == 0: err = self.run_sql_lock(EMPTY_TRASH_FEEDS_SQL1,[])
        if err == 0:
            feeds_to_remove = self.qr_sql('select id from feeds where deleted = 1', all=True)
            if self.db_error is not None: return -2, _('DB error: %a'), self.db_error
            for f in feeds_to_remove:
                if self.MC.icons == {}: self._load_icons()
                icon = self.MC.icons.get(f)
                if icon is not None and icon.startswith(f'{FEEDEX_ICON_PATH}{DIR_SEP}feed_') and os.path.isfile(icon): os.remove(icon)
        else: return -2, _('DB error: %a'), err

        err = self.run_sql_lock(EMPTY_TRASH_FEEDS_SQL2,[])
        feeds_deleted = self.rowcount
        if err != 0: return -2, _('DB error: %a'), err
 
        if not self.single_run: self.refresh_data()
        self.log(False, f'{_("Trash emptied")}: {feeds_deleted} {_("channels/categories")}, {entries_deleted} {_("entries")}, {rules_deleted} {_("rules removed")}' )
        return 0, _('Trash emptied: %a'), f'{feeds_deleted} {_("channels/categories")}, {entries_deleted} {_("entries")}, {rules_deleted} {_("rules removed")}' 








    def recalculate(self, **kargs):
        for msg in self.g_recalculate(**kargs): self.update_ret_code( cli_msg(msg) )
    def g_recalculate(self, **kargs):
        """ Utility to recalculate, retokenize, relearn, etc. 
            Useful for mass operations """

        entry_id = scast(kargs.get('id'), int, 0)
        learn = kargs.get('learn',False)
        rank = kargs.get('rank',False)
        stats = kargs.get('stats',False)

        if entry_id in (0, None):
            many = True
            self.log(False, "Mass recalculation started...")
            yield 0, _("Mass recalculation started...")
            if rank: self.log(False,"Ranking according to saved rules...")
            if learn: self.log(False,"Learning keywords ...")
            if stats: self.log(False,"Recalculating entries' stats ...")

            entries = self.qr_sql("""
select 
e.* 
from entries e 
join feeds f on f.id = e.feed_id 
left join feeds ff on ff.id = f.parent_id
where coalesce(e.deleted,0) <> 1 
and coalesce(f.deleted,0) <> 1 
and coalesce(ff.deleted,0) <> 1
            """, all=True)

        else:
            many = False
            yield 0, f'{_("Recalculating entry")} {entry_id} ...'
            entries = self.qr_sql("select * from entries where id=:id", {"id":entry_id} , all=True)

        if self.db_error is not None:
            yield -2, _('DB error: %a'), self.db_error
            return -2

        entry = EntryContainer(self)

        entry_q = []
        rules_q = []
        rules_ids_q = []

        entries_len = len(entries)

        i = 0
        j = 0
        for e in entries:
    
            i +=1
            j +=1

            entry.populate(e)
            yield 0, _("Processing entry %a ..."), entry['id']
    
            if many and learn and coalesce(entry['read'],0) == 0: continue

            entry.ling(learn=learn, index=stats, stats=stats, rank=rank, save_rules=False)
            
            vals = {'id':entry['id']}
            if stats:
                for f in LING_TECH_LIST: vals[f] = entry[f] 
            if rank:
                vals['importance'] = entry['importance']
                vals['flag'] = entry['flag']

            if learn:
                entry.learn_rules(entry.FX.LP.features, save_rules=False)
                for r in entry.rules: rules_q.append(r)
                rules_ids_q.append({'id': entry['id']})

            entry_q.append(vals)


            if i >= self.config.get('max_items_per_transaction', 500) or j >= entries_len - 1:

                yield 0, _('Committing batch ...')
                err = self.run_sql_lock(self.entry.update_sql(filter=vals.keys(), wheres='id = :id'), entry_q, many=True)
                if err != 0:
                    yield -2, _('DB error: %a'), err
                    return -2

                if learn:
                    yield 0, _('Learning rule batch ...')
                    err = self.run_sql_lock('delete from rules where context_id = :id', rules_ids_q, many=True)
                    if err == 0:
                        err = self.run_sql_lock(self.rule.insert_sql(all=True), rules_q, many=True)
                    
                    if err != 0:
                        yield -2, _('DB error: %a'), err
                        return -2

                i = 0
                entry_q.clear()
                rules_q.clear()
                rules_ids_q.clear()

                yield 0, _('Batch committed')


        self.log(False, "Recalculation finished")
        yield 0, _('Recalculation finished!')

        self.update_stats()
        if learn: 
            if not self.single_run: self.load_rules()
        return 0





    def db_stats(self, **kargs):
        """ Displays database statistics """
        version = self.qr_sql("select val from params where name='version'", one=True)
        db_size = sanitize_file_size(os.path.getsize(self.db_path))
        doc_count = self.qr_sql("select val from params where name='doc_count'", one=True, ignore_errors=False)
        last_update = self.qr_sql("select max(time) from actions where name = 'fetch'", one=True, ignore_errors=False)
        first_update = self.qr_sql("select min(time) from actions where name = 'fetch'", one=True, ignore_errors=False)
        rule_count = self.qr_sql("select count(id) from rules where learned = 1", one=True, ignore_errors=False)
        user_rule_count = self.qr_sql("select count(id) from rules where learned <> 1", one=True, ignore_errors=False)

        feed_count = self.qr_sql("select count(id) from feeds where coalesce(is_category,0) = 0 and coalesce(deleted,0) = 0", one=True, ignore_errors=False)
        cat_count = self.qr_sql("select count(id) from feeds  where coalesce(is_category,0) = 1 and coalesce(deleted,0) = 0", one=True, ignore_errors=False)

        lock = self.qr_sql("select * from params where name = 'lock'", one=True, ignore_errors=False)
        if lock is not None: lock=_('DATABASE LOCKED!')
        else: lock=''

        fetch_lock = self.qr_sql("select val from params where name = 'is_fetching'", one=True, ignore_errors=False)

        if self.db_error is not None: stat_str = f'{_("ERROR FETCHING DB STATISTICS!")}:<b>{self.db_error}</b>'
        else:

            if fetch_lock not in (('0',),(0,), 0, None, (None,)): fetch_lock = _('\nDATABASE LOCKED FOR FETCHING!\n\n')
            else: fetch_lock = ''

            last_time = scast(slist(last_update,0,None),int,None)
            if last_time is not None: last_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_time))
            else: last_time_str = _('NOT FOUND')

            first_time = scast(slist(first_update,0,None),int,None)
            if first_time is not None: first_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(first_time))
            else: first_time_str = _('NOT FOUND')


            if kargs.get('markup',False) and not kargs.get('print',True):
                mb = '<b>'
                me = '</b>'
            else:
                mb = ''
                me = ''

            stat_str=f"""

{_('Statistics for database')}: {mb}{self.db_path}{me}

{_('FEEDEX version')}:         {mb}{slist(version,0,_('NOT FOUND'))}{me}

{_('Database size')}:          {mb}{db_size}{me}

{_('Entry count')}:            {mb}{slist(doc_count,0,_('NOT FOUND'))}{me}

{_('Learned rule count')}:     {mb}{slist(rule_count,0,'0')}{me}
{_('Manual rule count')}:      {mb}{slist(user_rule_count,0,'0')}{me}

{_('Feed count')}:             {mb}{slist(feed_count,0,'0')}{me}
{_('Category count')}:         {mb}{slist(cat_count,0,'0')}{me}

{_('Last news update')}:       {mb}{last_time_str}{me}
{_('First news update')}:      {mb}{first_time_str}{me}

{fetch_lock}
{lock}

"""
        
            if self.check_due_maintenance(): stat_str=f"{stat_str}{_('DATABASE MAINTENANCE ADVISED!')}\n{_('Use')} {mb}feedex --db-maintenance{me} {_('command')}"
            stat_str=f"{stat_str}\n\n"

        if kargs.get('print',True):
            help_print(stat_str)
        
        return stat_str




    def check_due_maintenance(self):
        last_maint = slist(self.qr_sql("""select max(coalesce(time,0)) from actions where name = 'maintenance' """, one=True), 0, 0)
        doc_count = self.get_doc_count()
        if doc_count - scast(last_maint, int, 0) >= 50000: return True
        else: return False


    def db_maintenance(self, **kargs):
        for m in self.g_db_maintenance(**kargs): self.update_ret_code( cli_msg(m) )        
    def g_db_maintenance(self, **kargs):
        """ Performs database maintenance to increase performance at large sizes """
        if self.locked(ignore=kargs.get('ignore_lock',False)):
            yield -4, _('DB locked!')
            return -4

        self.MC.db_lock = False
        yield 0, _('Starting DB miantenance')

        yield 0, _('Performing VACUUM')
        self.qr_sql('VACUUM', one=True, ignore_errors=False)
        yield 0, _('Performing ANALYZE')
        self.qr_sql('ANALYZE', one=True, ignore_errors=False)
        yield 0, _('REINDEXING all tables')
        self.qr_sql('REINDEX', one=True, ignore_errors=False)

        yield 0, _('Updating document statistics')
        doc_count = slist(self.qr_sql(DOC_COUNT_SQL, one=True, ignore_errors=False),0, 0)
        doc_count = scast(doc_count, int, 0)

        self.qr_sql("insert into params values('doc_count', :doc_count)", {'doc_count':doc_count}, one=True, ignore_errors=False)
        self.qr_sql("""insert into actions values('maintenance',:doc_count)""", {'doc_count':doc_count}, one=True, ignore_errors=False)
        
        if self.db_error is None:
            self.conn.commit
            self.log(False, 'DB maintenance completed')
            yield 0, _('DB maintenance completed')
        else:
            self.log(True, f'DB maintenance failed! ({self.db_error})')
            yield -2, _('DB maintenance failed! (%a)'), self.db_error

        self.unlock(ignore=kargs.get('ignore_lock',False))





    def port_data(self, ex:bool, pfile:str, mode:str, **kargs): self.MC.ret_status = cli_msg(self.r_port_data(ex, pfile, mode, **kargs))
    def r_port_data(self, ex:bool, pfile:str, mode:str, **kargs):
        """ Handles exporting and importing data to/from text files """
        if ex:
            if os.path.isfile(pfile): return -6, _('File already exists!')

            if mode == 'feeds':
                if self.debug in (1,6): print("Exporting feeds...")
                ldata = list(self.MC.feeds)
            elif mode == 'rules':
                if self.debug in (1,6): print("Exporting rules...")
                ldata = list(self.qr_sql("select * from rules r where coalesce(r.learned,0) = 0", all=True))
            elif mode == 'flags':
                if self.debug in (1,6): print("Exporting flags...")
                ldata = list(self.qr_sql("select * from flags", all=True))
            
            if self.db_error is not None: return -2, _('DB Error: %a'), self.db_error

            if save_json(pfile, ldata) == 0: return 0, _('Data successfully exported')
            else: return -6, _('Error writing JSON data to %a'), pfile

        else:
            ldata = load_json(pfile,())
            if ldata == (): return -6, _('Error reading data from %a'), pfile
            if type(ldata) not in (list, tuple): return -6, _('Invalid data format (not a list)')

            if mode == 'feeds':
                if self.debug in (1,6): print("Importing feeds...")
                
                # Max ID will be added to imported ids to prevent ID collision
                max_id = self.qr_sql('select max(id) from feeds', one=True)
                if self.db_error is not None: return -2, _('DB Error: %a'), self.db_error

                max_id = slist(max_id, 0, 0)
                ldata_sql = []
                if max_id in (None, (None), ()): max_id = 0
                if self.debug in (1,6): print(f'Max ID: {max_id}') 
                for l in ldata:
                    self.feed.populate(l)
                    if self.feed['parent_id'] is not None: self.feed['parent_id'] = self.feed['parent_id'] + max_id
                    self.feed['id'] = coalesce(self.feed['id'],0) + max_id
                    ldata_sql.append(self.feed.vals.copy())

                
                err = self.run_sql_lock(self.feed.insert_sql(all=True), ldata_sql, many=True)
                if err != 0: return -2, _('DB error: %a'), err
                else: 
                    if not self.single_run: self.load_feeds()
                    self.log(False, f'Feed data imported from {pfile}')
                    return 0, _('Feed data successfully imported from %a'), pfile 


            elif mode == 'rules':
                if self.debug in (1,6): print("Importing rules...")
                # Nullify IDs to avoid conflicts
                ldata_sql = []
                for l in ldata:
                    self.rule.populate(l)
                    self.rule['id'] = None
                    ldata_sql.append(self.rule.vals.copy())

                err = self.run_sql_lock(self.rule.insert_sql(all=True), ldata_sql, many=True)
                if err != 0: return -2, _('DB error: %a'), err
                else:
                    if not self.single_run: self.load_rules()
                    self.log(False, f'Rules successfully imported from {pfile}')
                    return 0, _('Rules successfully imported from %a'), pfile


            elif mode == 'flags':
                if self.debug in (1,6): print("Importing flags...")
                # Nullify IDs to avoid conflicts
                ldata_sql = []
                for l in ldata:
                    self.flag.populate(l)
                    self.flag['id'] = None
                    ldata_sql.append(self.flag.vals.copy())

                err = self.run_sql_lock(self.flag.insert_sql(all=True), ldata_sql, many=True)
                if err != 0: return -2, _('DB error: %a'), err
                else:
                    if not self.single_run: self.load_rules()
                    self.log(False, f'Flags successfully imported from {pfile}')
                    return 0, _('Flags successfully imported from %a'), pfile








    def archive(self, time, target_db, **kargs):
        for m in self.g_archive(time, target_db, **kargs): self.update_ret_code( cli_msg(m) ) 
    def g_archive(self, time, target_db, **kargs):
        """ This function archives current database to a new one """
        with_rules = kargs.get('with_rules',False)
        no_read = kargs.get('no_read',False)
        no_flag = kargs.get('no_flagged',False)
        
        if os.path.isfile(target_db) or os.path.isdir(target_db): 
            yield -6, _('File already exists! Aborting...')
            return -6
        
        db_backup = f'{self.db_path}.bak'
        yield 0, _("Making safety backup to %a"), db_backup
        self.conn.rollback()
        self.conn.close()
        try: copyfile(self.db_path, db_backup)
        except OSError as e:
            self.db_status = f'Error creating database backup to {db_path}.bak: {e}'
            yield -2, f'{_("Error creating database backup to")} {db_path}.bak: %a', e
            return -1
        finally:
            self._connect_db()


        target_db_conn = Feeder(self.MC, db_path=target_db, config=self.config, ignore_images=True, debug=self.debug, no_qp=True, load_icons=False, no_defaults=True, allow_create=True)
        if target_db_conn.db_error is not None:
            yield -2, _('Target DB error: %a'), target_db_conn.db_error            
            return -2
        else: yield 0, _('Database %a created ...'), target_db
        
        if type(time) is int: timestamp = time
        else: timestamp = convert_timestamp(time)
        if timestamp is None: 
            yield -7, _('Error converting time: %a'), time
            return -7


        yield 0, _('Counting entries to be archived ...')

        # Adding additional sql conditions for unread- and unflagged-only params
        add_sql = ''
        add_sql1 = ''
        add_sql2 = ''
        if no_read: 
            add_sql = f'{add_sql} and coalesce(e.read,0) <= 0'
            add_sql1 = f'{add_sql1} and coalesce(ee.read,0) <= 0'
            add_sql2 = f'{add_sql2} and coalesce(read,0) <= 0'
        if no_flag: 
            add_sql = f'{add_sql} and coalesce(e.flag,0) = 0'
            add_sql1 = f'{add_sql1} and coalesce(ee.flag,0) = 0'
            add_sql2 = f'{add_sql2} and coalesce(flag,0) = 0'

        entry_count = self.qr_sql(f"""select count(e.id) from entries e where e.pubdate <= :timestamp{add_sql}""",{'timestamp':timestamp}, one=True)
        entry_count = slist(entry_count, 0, 0)
        if entry_count == 0: 
            yield 0, _('Nothing to be archived ... Aborting ...')
            return 0

        if not with_rules:

            yield 0, _('Calculating archive weights for rules\' contexts...')
            

            err = self.run_sql_lock(f"""update rules
set archive = ( select coalesce(e.weight,0) * coalesce(e.read,0) from entries e where context_id = e.id )
where id in (
SELECT rr.id from rules rr
join entries ee on ee.id = rr.context_id
where ee.pubdate <= :timestamp{add_sql1} and rr.learned = 1)""", {'timestamp':timestamp})
            if err != 0: 
                yield -2, _('DB Error: %a'), err
                return -2


        else:

            yield 0, _('Transferring rules to archived DB ...')
            rules = self.qr_sql(f"""SELECT rr.* from rules rr
join entries ee on ee.id = rr.context_id
where ee.pubdate <= :timestamp{add_sql1} and rr.learned = 1""", {'timestamp':timestamp}, all=True)

            if len(rules) == 0: yield 0, _('No rules to archive ...')
            else:
                err = target_db_conn.run_sql_lock(self.rule.insert_sql(all=True), rules, many=True)
                if err != 0: 
                    yield -2, _('DB Error while transferring rules: %a'), err
                    return -2
            
        
        yield 0, _('Transferring entries...')

        for offset in range(0, entry_count, 500):
            entries = self.qr_sql(f"""select * from entries where pubdate <= :timestamp{add_sql2} LIMIT 500 OFFSET :offset""", {'timestamp':timestamp, "offset":offset}, all=True)
            yield 0, f'{_("Moving")} {offset}/{entry_count}'
            err = target_db_conn.run_sql_lock(self.entry.insert_sql(all=True), entries, many=True)
            if err != 0: 
                yield -2, _('DB Error while transferring entries: %a'), err
                return -2

        yield 0, _('Transferring feed data ...')
        feeds = self.qr_sql(GET_FEEDS_SQL, all=True)
        err = target_db_conn.run_sql_lock(self.feed.insert_sql(all=True), feeds, many=True)
        if err != 0: 
            yield -2, _('DB Error while transferring feeds: %a'), err
            return -2

        yield 0, _('Transferring flags ...')
        flags = self.qr_sql("""select * from flags""", all=True)
        flag = FlagContainerBasic()
        err = target_db_conn.run_sql_lock(flag.insert_sql(all=True), flags, many=True)
        if err != 0: 
            yield -2, _('DB Error while transferring flags: %a'), err
            return -2

        yield 0, _('Transferring manual rules ...')
        rules = self.qr_sql("""select * from rules where coalesce(learned,0) = 0""", all=True)
        err = target_db_conn.run_sql_lock(self.rule.insert_sql(all=True), rules, many=True)
        if err != 0: 
            yield -2, _('DB Error while transferring manual rules: %a'), err
            return -2


        if with_rules:
            yield 0, _('Removing rules from current DB...')
            err = self.run_sql_lock(f"""delete from rules where id in
(SELECT rr.id from rules rr
join entries ee on ee.id = rr.context_id
where ee.pubdate <= :timestamp{add_sql1} and rr.learned = 1)""", {'timestamp':timestamp})
            if err != 0: 
                yield -2, _('DB Error: %a'), err
                return -2

        yield 0, _('Removing old entries from current DB...')
        err = self.run_sql_lock(f"""delete from entries where pubdate <= :timestamp{add_sql2}""", {'timestamp':timestamp})
        if err != 0:
            yield -2, _('DB Error: %a'), err
            return -2
        
        yield 0, _('Deleting temporary backup ...')
        try: os.remove(db_backup)
        except OSError as e:
            self.db_status = f'{_("Error removing")} {db_backup}: {e}'
            yield -1, f'{_("Error removing")} {db_backup}: %a', e
            return -1 
        yield 0, _('Temporary backup database removed successfully')

        if not err:
            yield 0, _('DB successfully archived to %a'), target_db
            return 0



