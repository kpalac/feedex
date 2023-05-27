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

        # Index errors and status
        self.ix_path = os.path.join(self.db_path, 'index')
        self.ix_error = None
        self.ix_status = 0


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

        # Init icon and image caches
        self.icon_path = os.path.join(self.db_path,'icons')
        self.cache_path = os.path.join(self.db_path,'cache')

        # ... start 
        self._connect_db()
        if self.db_status != 0: 
            self.log(True, self.db_status)
            return None
        
        # Define writing indexer
        self.ixer_db = None
        self.ixer = None


        if self.main_thread:
            self.refresh_data()
            if self.load_icons: self.do_load_icons()
            if not self.single_run: self.load_history()
            if self.debug in (1,2): print('Main connection established...')

        # initialize linguistic processor for tokenizing and stemming
        self.LP = FeedexLP(self.MC, **kargs)
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
        db_path = os.path.join(self.db_path, 'main.db')
        first_run = False # Trigger if DB is not present



        # Check/create cache and icon dirs
        if not os.path.isdir(self.icon_path):
            try:
                os.makedirs(self.icon_path)
                yield 0, _('Icon folder %a created...'), self.icon_path
            except (OSError, IOError):
                yield -1, _('Error creating icon folder %a'), self.icon_path
                return -1

        if not os.path.isdir(self.cache_path):
            try:
                os.makedirs(self.cache_path)
                yield 0, _('Cache folder %a created...'), self.cache_path
            except (OSError, IOError):
                yield -1, _('Error creating cache folder %a'), self.cache_path
                return -1
                


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
                try:
                    os.makedirs(db_dir)
                    yield 0, _('Folder %a created...'), db_dir
                except (OSError, IOError):
                    yield -1, _('Error creating DB folder %a'), db_dir
                    return -1


        try:
            self.conn = sqlite3.connect(db_path)
            self.curs = self.conn.cursor()
        except (sqlite3.Error, sqlite3.OperationalError, OSError) as e: 
            yield -2, _('DB connection error: %a'), e
            self.sql_status = f"""{_('Error connecting to:')} {db_path}"""
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
        if first_run and (self.main_thread or self.allow_create):

            # Run DDL on fresh DB
            try:
                sql_scripts_path = os.path.join(FEEDEX_SYS_SHARED_PATH,'data','db_scripts')
                with open(os.path.join(sql_scripts_path, 'feedex_db_ddl.sql'), 'r') as sql:
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
                    with open( os.path.join(sql_scripts_path,'feedex_db_defaults.sql'), 'r') as sql:
                        sql_ddl = sql.read()
                    with self.conn:
                        self.curs.executescript(sql_ddl)
                except (sqlite3.Error, sqlite3.OperationalError, OSError) as e:
                    yield -2, _('Error writing defaults to database: %a'), e
                    self.db_status = f"""{_("Error writing defaults to database:")} {e}"""
                    return -2

                yield 0, 'Added some defaults...'

        if self.main_thread:
        # Checking versions and aborting if needed
            try: version = slist(self.curs.execute("select val from params where name = 'version'").fetchone(), 0, None)
            except (sqlite3.Error, sqlite3.OperationalError, OSError) as e:
                    yield -2, _('Error getting version from DB: %a'), e
                    self.db_status = f"""{_("Error getting version from DB:")} {e}"""
                    return -2

            if version != FEEDEX_DB_VERSION_COMPAT:
                yield -1, _('Application version incompatibile with %a Database! Aborting'), db_path
                self.db_status = f'{_("Application version incompatibile with")} {db_path} {_("Database! Aborting")}'
                return -1    



        # Connecting XAPIAN index
        try:
            self.ix = xapian.Database(self.ix_path)
            self.ix_status = 0
            self.ix_error = 0
            if self.debug in (1,2): print(f"{_('Connected to index')} {self.ix_path}")
        except (xapian.DatabaseError,) as e:
            yield -1,  f'{_("Could not connect to")} {self.ix_path}: %a', e
            self.ix = None


        # Try to create Xapian DB if it doesn't exists...
        if self.ix is None:
            if self.allow_create or self.main_thread:
                try:
                    yield 0,  f'{_("Creating index")} %a ...', self.ix_path
                    self.ix = xapian.WritableDatabase(self.ix_path, xapian.DB_CREATE_OR_OPEN)
                    self.ix.close()
                    self.ix_status = 0
                    self.ix_error = 0
                except (xapian.DatabaseError,) as e:
                    yield -1, f'{_("Error creating index")} {self.ix_path}: %a', e
                    self.ix_status = f'{_("Error creating index")} {self.ix_path}: {e}'
                    self.ix_error = self.ix_status
                    return -1
            else:
                self.ix_status = _("Index error!")
                self.ix_error = self.ix_status
                return -1

            # Try to connect finally
            try:
                self.ix = xapian.Database(self.ix_path)
                self.ix_status = 0
                self.ix_error = 0
                if self.debug in (1,2): print(f"{_('Connected to index')} {self.ix_path}")
            except (xapian.DatabaseError,) as e:
                yield -1,  f'{_("Could not connect to")} {self.ix_path}: %a', e
                self.ix_status = f'{_("Error connecting to index")} {self.ix_path}: {e}'
                self.ix_error = self.ix_status
                self.ix = None
                return -1





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






    # Indexer stuff...
    def connect_ixer(self, **kargs):
        """ Connect writing indexer """
        if not isinstance(self.ixer_db, xapian.WritableDatabase):
            tm = 0
            while tm <= self.timeout or self.wait_indef:            
                try: 
                    self.ixer_db = xapian.WritableDatabase(self.ix_path)
                    self.ixer = xapian.TermGenerator()
                    self.ixer_db.begin_transaction()
                    return 0
                except xapian.DatabaseLockError:
                    cli_msg( (-4, _(f"""Index locked... Waiting... {tm}""") ) )
                except xapian.DatabaseError as e:
                    cli_msg( (-4, _(f"""Error connecting to index: %a"""), e ) )
                    self.ix_error = e
                    self.MC.ret_status = -2
                    return -1

                tm += 1
                time.sleep(1)
        
            cli_msg((-1, f'{_("Failed to unlock index")} ({self.conn_id})'))
            self.MC.ret_status = -4
            return -1


    def close_ixer(self, **kargs):
        """ Cleanly disconnect indexer """
        rollback = kargs.get('rollback',False)
        commit = kargs.get('commit',True)
        if isinstance(self.ixer_db, xapian.WritableDatabase): 
            self.ixer = None
            if self.debug in (1,2,): print('Writing to Index...')
            if commit: self.ixer_db.commit_transaction()
            if rollback: 
                if self.debug in (1,2,): print('Index changes cancelled!')
                self.ixer_db.cancel_transaction()
            self.ixer_db.close()
            if self.debug in (2,): print('Done.')
        self.ixer_db = None





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
                icon_file = os.path.join(FEEDEX_SYS_ICON_PATH, f'{icon_name}.svg')
                if os.path.isfile(icon_file):
                    self.MC.icons[id] = icon_file
                    continue
                elif os.path.isfile(icon_name):
                    self.MC.icons[id] = icon_name
                    continue

            if is_category == 1:
                self.MC.icons[id] = os.path.join(FEEDEX_SYS_ICON_PATH, 'document.svg')
            else:
                icon_file = os.path.join(self.icon_path, f'feed_{id}.ico')
                if os.path.isfile(icon_file): self.MC.icons[id] = icon_file
                else:
                    if handler == 'rss': self.MC.icons[id] = os.path.join(FEEDEX_SYS_ICON_PATH, 'news-feed.svg')
                    elif handler == 'html': self.MC.icons[id] = os.path.join(FEEDEX_SYS_ICON_PATH, 'www.svg')
                    elif handler == 'script': self.MC.icons[id] = os.path.join(FEEDEX_SYS_ICON_PATH, 'script.svg')
                    elif handler == 'local': self.MC.icons[id] = os.path.join(FEEDEX_SYS_ICON_PATH, 'mail.svg')
                



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
            self.MC.rules_validated = False
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

    def get_flag_desc(self, id:int, **kargs):
        if id not in self.MC.flags.keys(): return ''
        desc = self.MC.flags.get(id, (None,None,''))[1]
        if desc in (None, ''): return ''
        else: return desc


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
        if type(qtype) is int and qtype in (0,1,2): return qtype
        if type(qtype) is str:
            if qtype.lower() in ('string','str','string_matching','sm'):
                return 0
            elif qtype.lower() in ('full', 'fts', 'full-text','fulltext',):
                return 1
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

    def get_last_docid(self, **kargs):
        doc_id = scast( self.qr_sql("select max(id) from entries", one=True)[0], int, 0)
        if self.db_error is not None: return -1
        return doc_id



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
            entry.strict_merge(e)
            entry.learn = learn
            
            err = False
            for msg in entry.g_add(new=e, update_stats=False, counter=i): 
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
        # Data handlers init - to lazy load later...
        rss_handler = None
        html_handler = None
        script_handler = None
        
        entries_sql = []
        feeds_sql = []

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
                            item.set_feed(feed=feed)
                            item.ling(index=True, stats=True, rank=True, learn=False, multi=True, counter=tech_counter)
                            vals = item.vals.copy()
                            if isinstance(vals, dict): entries_sql.append(vals)
                            else: yield -1, _('Error while linguistic processing %a!'), item
                        else:
                            entries_sql.append(item.vals.copy())

                        # Track new entries and take care of massive insets by dividing them into parts
                        tech_counter += 1
                        if tech_counter >= self.config.get('max_items_per_transaction', 2000):
                            yield 0, _('Saving new items ...')
                            err = self.run_sql_lock(self.entry.insert_sql(all=True), entries_sql, many=True)
                            if err == 0: err =  self.run_sql_lock("""update feeds set lastread = :now, lastchecked = :now, etag = :etag, modified = :modified, http_status = :status, error = 0  where id = :id""", feeds_sql, many=True)
                            if err == 0:
                                feeds_sql = []
                                entries_sql = []
                                yield 0, _('Indexing new items ...')
                                self.close_ixer()                 
                            else:
                                yield -2, _('Fetching aborted! DB error: %a'), err
                                self.close_ixer(rollback=True)
                                self.unlock_fetching()
                                return -2

                            tech_counter = 0  


                    elif isinstance(item, (tuple, list)):
                        yield item
                    else:
                        yield -3, _('Unknown error: %a'), item

             


            else:
                # This bit is if no fetching is done (just meta update)
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
                    if err != 0: yield -2, _('DB error: %a'), err
                else:
                    feeds_sql.append({'now':now_raw, 'etag':handler.etag, 'modified':handler.modified, 'status':handler.status, 'id':self.feed['id']})
                


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


            # Stop if this was the specified feed (i.e. there was a feed specified and a loop was executed)...
            if feed_id != 0: break


        # Push final entries to DB (the same as when tech_counter hit before)           
        if not update_only:
            if len(entries_sql) > 0:
                yield 0, _('Saving new items ...')
                err = self.run_sql_lock(self.entry.insert_sql(all=True), entries_sql, many=True)
                if err == 0: err =  self.run_sql_lock("""update feeds set lastread = :now, lastchecked = :now, etag = :etag, modified = :modified, http_status = :status, error = 0  where id = :id""", feeds_sql, many=True)
                if err == 0: 
                    yield 0, _('Indexing new items ...')
                    self.close_ixer()   
                else:
                    yield -2, _('Fetching aborted! DB error: %a'), err
                    self.close_ixer(rollback=True)
                    self.unlock_fetching()
                    return -2



        # ... finally, do maintenance ....
        if meta_updated and not self.single_run: self.load_feeds()

        if self.new_items > 0:
            err = self.run_sql_lock("""insert into actions values('fetch', :started)""", {'started':started} )
            if err != 0: yield -2, _('DB Error: %a'), err
            else: 
                if self.MC.fetches is None: self.get_last()
                self.MC.fetches.insert(0, (started, started_str) )

        if kargs.get('update_stats',True):
            if self.new_items > 0: 
                yield 0, _('Updating statistics ...')
                self.update_stats()

        finished_raw = datetime.now()
        finished = int(finished_raw.timestamp())
        ddelta_raw = finished - started
        dmins = str(int(ddelta_raw/60)).zfill(2)
        dsecs = str(int(ddelta_raw % 60)).zfill(2)
        duration = f'{dmins}:{dsecs}'
        

        if not update_only: yield 0, f"""{_('Finished fetching (%a new articles), duration: ')}{duration}""", self.new_items
        else: yield 0, f"""{_('Finished updating metadata, duration: ')}{duration}"""

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
                if icon is not None and icon.startswith( os.path.join(self.icon_path, 'feed_') ) and os.path.isfile(icon): os.remove(icon)
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

        if entry_id == 0:
            start_id = kargs.get('start_id', 0)
            if start_id is None: start_id = 0
            end_id = kargs.get('end_id', None)
            if end_id is None:
                end_id = self.get_last_docid()
                if end_id == -1:
                    yield -2, _('DB error: %a'), self.db_error
                    return -2

            batch_size = kargs.get('batch_size', None)
            if batch_size is None: batch_size = self.config.get('max_items_per_transaction', 1000)

        learn = kargs.get('learn',False)
        rank = kargs.get('rank',False)
        index = kargs.get('index',False)

        entry = EntryContainer(self)

        entry_q = []
        rules_q = []
        rules_ids_q = []

        vals = {}
        vs = {}

        if entry_id in (0, None):
            many = True
            self.log(False, "Mass recalculation started...")
            yield 0, _("Mass recalculation started...")
            if rank: self.log(False,"Ranking according to saved rules...")
            if learn: self.log(False,"Learning keywords ...")
            if index: self.log(False,"Indexing ...")

            SQL = RECALC_MULTI_SQL

            if self.debug in (1,4): 
                print(f'Batch size: {batch_size}')
                print(f'Range: {start_id}..{end_id}')
        else:
            many = False
            yield 0, f'{_("Recalculating entry")} {entry_id} ...'
            SQL = "select * from entries where id=:id"

            vs = {'id':entry_id}



        page = 0
        t_start_id = 0
        t_end_id = 0
        stop = False
        while not stop:

            if many:
                t_start_id = start_id + (page * batch_size)
                page += 1
                t_end_id = start_id + (page * batch_size)
                vs = {'start_id':t_start_id, 'end_id':t_end_id}
                if t_end_id > end_id: stop = True
            else: stop = True


            if many: yield 0, _('Getting entries...')
            entries = self.qr_sql(SQL, vs, all=True)
            if self.db_error is not None:
                yield -2, _('DB error: %a'), self.db_error
                return -2
            

            for i,e in enumerate(entries):

                entry.populate(e)
    
                if many and learn and coalesce(entry['read'],0) == 0: continue
                yield 0, _(f"Processing entry %a ({entry['read']})..."), entry['id']

                entry.ling(learn=learn, index=index, rank=rank, save_rules=False, multi=True, counter=i, rebuilding=True)
            
                vals = {'id': entry['id']}
                if index:
                    for f in ENTRIES_TECH_LIST: vals[f] = entry[f] 
                if rank:
                    vals['importance'] = entry['importance']
                    vals['flag'] = entry['flag']

                if learn:
                    for r in entry.rules: rules_q.append(r)
                    rules_ids_q.append({'id': entry['id']})

                entry_q.append(vals.copy())



            if len(entry_q) > 0:
                yield 0, _('Committing batch ...')
                err = self.run_sql_lock(self.entry.update_sql(filter=vals.keys(), wheres='id = :id'), entry_q, many=True)
                if err != 0:
                    yield -2, _('DB error: %a'), err
                    return -2

            if learn:
                yield 0, _('Learning rule batch ...')
                if len(rules_ids_q) > 0:
                    err = self.run_sql_lock('delete from rules where context_id = :id', rules_ids_q, many=True)
                if len(rules_q) > 0:
                    if err == 0: err = self.run_sql_lock(self.rule.insert_sql(all=True), rules_q, many=True)
                    if err != 0:
                        yield -2, _('DB error: %a'), err
                        return -2

            if index: self.close_ixer()                    

            entry_q.clear()
            rules_q.clear()
            rules_ids_q.clear()

            self.log(False,f"Batch committed (entry id {entry['id']})")
            yield 0, _('Batch committed')



        self.log(False, "Recalculation finished")
        yield 0, _('Recalculation finished!')

        self.update_stats()
        if learn: 
            if not self.single_run: self.load_rules()
        return 0









    def _get_dir_size(self, start_path = '.'):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(start_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                # skip if it is symbolic link
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
        return total_size



    def db_stats(self, **kargs):
        """ Displays database statistics """
        version = self.qr_sql("select val from params where name='version'", one=True)
        
        db_size = os.path.getsize(os.path.join(self.db_path,'main.db'))
        ix_size = self._get_dir_size(self.ix_path)
        cache_size = self._get_dir_size(self.cache_path)

        doc_count = self.qr_sql("select val from params where name='doc_count'", one=True, ignore_errors=False)
        last_doc_id = self.get_last_docid()
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

{_('Main Database size')}:     {mb}{sanitize_file_size(db_size)}{me}
{_('Index size')}:             {mb}{sanitize_file_size(ix_size)}{me}
{_('Cache size')}:             {mb}{sanitize_file_size(cache_size)}{me}

{_('Total size')}:             {mb}{sanitize_file_size(db_size + ix_size + cache_size)}{me}



{_('Entry count')}:            {mb}{slist(doc_count,0,_('NOT FOUND'))}{me}
{_('Last entry ID')}:          {mb}{last_doc_id}{me}

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
            
            elif mode == 'entries':
                if self.debug in (1,6): print("Exporting query results ...")
                ldata = []
                for r in kargs.get('query_results',()):
                    self.entry.populate(r, safe=True)
                    ldata.append(self.entry.vals.copy())


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



