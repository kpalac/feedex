# -*- coding: utf-8 -*-
""" 
Main engine for Feedex news reader. Database interface and REST handling, main Fetching mechanism, interface with ling processor

"""

from feedex_headers import *



class FeedexDatabaseError(FeedexError):
    """ Irrecoverable Feedex database error (e.g. unable to connect, corrupted database )"""
    def __init__(self, *args, **kargs): 
        kargs['code'] = kargs.get('code', FX_ERROR_DB)
        super().__init__(*args, **kargs)

class FeedexDataError(FeedexDatabaseError):
    """ Something went wrong with retrieving or caching data like feeds, rules, flags etc."""
    def __init__(self, *args, **kargs): super().__init__(*args, **kargs)

class FeedexDatabaseNotFoundError(FeedexDatabaseError):
    """ Database does not exist and current connection is not authorized to create it """
    def __init__(self, *args, **kargs): super().__init__(*args, **kargs)

class FeedexDatabaseLockedError(FeedexDatabaseError):
    """ Database is locked. Is handled later if current process is able tu unlock it """
    def __init__(self, *args, **kargs): 
        kargs['code'] = kargs.get('code', FX_ERROR_LOCK)
        super().__init__(*args, **kargs)

class FeedexIndexError(FeedexError):
    def __init__(self, *args, **kargs): 
        kargs['code'] = kargs.get('code', FX_ERROR_INDEX)
        super().__init__(*args, **kargs)




class FeedexDatabase:
    """ Database interface for Feedex with additional maintenance and utilities """
    
    def __init__(self, **kargs):
        """ """

        # Main configuration
        self.config = kargs.get('config', fdx.config)
        
        # Path to database
        self.db_path = os.path.abspath(kargs.get('db_path', self.config.get('db_path')))

        # Paths to resources
        self.cache_path = os.path.join(self.db_path, 'cache')
        self.img_path = os.path.join(self.db_path, 'images')
        self.icon_path = os.path.join(self.db_path,'icons')
        self.sql_path = os.path.join(self.db_path,'main.db')
        self.ix_path = os.path.join(self.db_path,'index')


        # SQL rowcount etc
        self.rowcount = 0
        self.lastrowid = 0
        # Xapian stuff
        self.lastxapdocid = 0
        self.lastxapcount = 0

        # Last inserted ids
        self.last_entry_id = 0
        self.last_feed_id = 0
        self.last_rule_id = 0
        self.last_history_id = 0
        self.last_flag_id = 0
        self.last_term_id = 0

        # New items from last fetching/import
        self.new_items = 0

        # Database status (for error catching)
        self.status = 0
        self.error = None

        # Flag if db creation is allowed
        self.allow_create = kargs.get('allow_create',False)
        # Flag if this is the main connection
        self.main_conn = kargs.get('main_conn', False)
        # Flag if this connection created a new DB
        self.created = False

        self.timeout = self.config.get('timeout', 120) # Wait time if DB is locked
        

        # Define SQLite interfaces
        self.conn = None
        self.curs = None
        # .. and Xapian stuff...
        self.ix = None

        # Define writing indexer
        self.ixer_db = None
        self.ixer = None

        # Connection ID
        self.conn_id = 0

        # ... pointer to lazy loaded Language Processor
        self.LP = None
        self.Q = None

        if kargs.get('connect',False):
            # Finally, connect to DB
            self.connect()
            if kargs.get('load_all',False):
                self.load_all()
                self.connect_LP()
                self.connect_QP()





    ####################################################################################33
    #   Connection handling
    #


    def connect(self, **kargs):
        """ Establish connection to DB and/or create it if not exists """
        defaults = kargs.get('defaults', False)
        default_feeds = kargs.get('default_feeds', False)

        # Check DB folders ...
        if not os.path.isdir(self.db_path):
            if self.allow_create:
                msg(_('DB not found. Creating one now at %a...'), self.db_path)
                os.makedirs(self.db_path)
                self.created = True
                msg(_('Created %a...'), self.db_path)
            else: raise FeedexDatabaseNotFoundError(_('DB %a not found. Aborting...'), self.db_path)

        
        # Check/create cache and icon dirs
        if not os.path.isdir(self.icon_path): os.makedirs(self.icon_path)
        if not os.path.isdir(self.cache_path): os.makedirs(self.cache_path)
        if not os.path.isdir(self.img_path): os.makedirs(self.img_path)

        if not os.path.isdir(self.icon_path): raise FeedexDatabaseError('DB dir not found (icons): %a', self.icon_path)
        if not os.path.isdir(self.cache_path): raise FeedexDatabaseError('DB dir not found (cache): %a', self.cache_path)
        if not os.path.isdir(self.img_path): raise FeedexDatabaseError('DB dir not found (images): %a', self.img_path)
    

        # Init SQLite DB
        if not os.path.isfile(self.sql_path):
            if self.allow_create:
                create_sqlite = True
                self.created = True
                msg(_('Creating SQL DB %a...'), self.sql_path) 
            else: raise FeedexDatabaseNotFoundError('SQL DB not found: %a', self.sql_path)
        else: create_sqlite = False

        # Establish SQLite3 connection and cursor...
        try:
            self.conn = sqlite3.connect(self.sql_path)
            self.curs = self.conn.cursor()
        except (sqlite3.Error, sqlite3.OperationalError, OSError) as e: raise FeedexDatabaseError('DB connection error: %a', e)

        # Some technical stuff...
        try:
            with self.conn: self.curs.execute("PRAGMA case_sensitive_like=true")
            with self.conn: self.curs.execute("PRAGMA automatic_index=false")
            #with self.conn: self.curs.execute("PRAGMA cache_size=5000")
        except sqlite3.Error as e: raise FeedexDatabaseError('Error setting up PRAGMA: %a', e)



        # Handle SQLite structure, if not there...
        if create_sqlite:
            # Run DDL on fresh DB
            try:
                sql_scripts_path = os.path.join(FEEDEX_SYS_SHARED_PATH,'data','db_scripts')
                with open(os.path.join(sql_scripts_path, 'feedex_db_ddl.sql'), 'r') as sql: sql_ddl = sql.read()
                with self.conn: self.curs.executescript(sql_ddl)
                msg(_('Database structure created'))
            except (sqlite3.Error, sqlite3.OperationalError, OSError) as e:
                raise FeedexDatabaseError('Error writing DDL from %a: %b', os.path.join(sql_scripts_path, 'feedex_db_ddl.sql') , e)
            
            # Add defaults if allowed ...
            if defaults:
                try:
                    with open( os.path.join(sql_scripts_path,'feedex_db_defaults.sql'), 'r') as sql: sql_ddl = sql.read()
                    with self.conn: self.curs.executescript(sql_ddl)
                    msg(0, _('Added defaults...'))
                except (sqlite3.Error, sqlite3.OperationalError, OSError) as e:
                    self.close(unlock=False)
                    raise FeedexDatabaseError('Error writing defaults from %a: %b', os.path.join(sql_scripts_path,'feedex_db_defaults.sql'), e)

            if default_feeds:
                try:
                    with open( os.path.join(sql_scripts_path,'feedex_db_default_feeds.sql'), 'r') as sql: sql_ddl = sql.read()
                    with self.conn: self.curs.executescript(sql_ddl)
                    msg(0, _('Added default Feeds...'))
                except (sqlite3.Error, sqlite3.OperationalError, OSError) as e:
                    self.close(unlock=False)
                    raise FeedexDatabaseError('Error writing default feeds from %a: %b', os.path.join(sql_scripts_path,'feedex_db_default_feeds.sql'), e)

            # Insert verson to DB
            try: #INSERT INTO "main"."params" ("name", "val") VALUES ('version', '1.0.0');
                self.curs.execute(f"""INSERT INTO params (name, val) VALUES ('version', :version)""", {'version':FEEDEX_VERSION})
                self.conn.commit()
            except (sqlite3.Error, sqlite3.OperationalError, OSError) as e:
                self.close(unlock=False)
                raise FeedexDatabaseError('Error setting DB version: %a', e)


        if self.main_conn and not create_sqlite:
            # Checking versions and aborting if needed
            try: 
                version = slist(self.curs.execute("select val from params where name = 'version'").fetchone(), 0, None)
            except (sqlite3.Error, sqlite3.OperationalError, OSError) as e:
                self.close(unlock=False)
                raise FeedexDatabaseError('Error getting DB version: %a', e)

            if version != FEEDEX_DB_VERSION_COMPAT and version != FEEDEX_VERSION:
                self.close(unlock=False)
                raise FeedexDatabaseError('App version (%a) incompatibile with DB version (%b)', FEEDEX_VERSION, version)

            if kargs.get('unlock', False): 
                err = self.unlock()
                if err == 0:
                    msg(_('Database unlocked'))
                    self.close(unlock=False)

            elif kargs.get('lock', False):
                err = self.lock()
                if err == 0:
                    msg(_('Database locked'))
                    self.close(unlock=False)

            else:
                lock = self.locked() 
                if lock is True:
                    self.close(unlock=False)
                    raise FeedexDatabaseLockedError('DB locked')
                elif lock is None:
                    self.close(unlock=False)
                    raise FeedexDatabaseError('Unknown lock status!')


        # Connecting XAPIAN index
        try:
            self.ix = xapian.Database(self.ix_path)
            debug(2,f"Connected to index {self.ix_path}")        
        except (xapian.DatabaseError,) as e:
            if self.allow_create:
                try:
                    msg(f'{_("Creating index")} %a ...', self.ix_path)
                    self.ix = xapian.WritableDatabase(self.ix_path, xapian.DB_CREATE_OR_OPEN)
                    self.ix.close()
                except (xapian.DatabaseError,) as e:
                    self.close()
                    raise FeedexIndexError('Error creating index at %a: %b', self.ix_path, e)
            
                # Final try ...
                try:
                    self.ix = xapian.Database(self.ix_path)
                    debug(2,f'Connected to index {self.ix_path}')
                except (xapian.DatabaseError,) as e:
                    self.close()
                    raise FeedexIndexError('Error connecting to index at %a: %b', self.ix_path, e)           
            
            else: 
                self.close()
                raise FeedexIndexError('Index not found at %a', self.ix_path)

        fdx.conn_num += 1
        self.conn_id = fdx.conn_num
        return 0



    def close(self, **kargs):
        """ Close this connection """            
        if self.main_conn and kargs.get('unlock',True): self.unlock()
        if isinstance(self.conn, sqlite3.Connection): self.conn.close()
        if isinstance(self.ix, xapian.Database): self.ix.close()
        self.close_ixer()
        fdx.conn_num -= 1
        debug(2,f'Connection {self.conn_id} closed...')




    # Indexer stuff...
    def connect_ixer(self, **kargs):
        """ Connect writing indexer lazily """
        if not (isinstance(self.ixer_db, xapian.WritableDatabase) and isinstance(self.ixer, xapian.TermGenerator)):
            while True: # We need to wait indefinitely for index to be free to avoid unindexed entries
                try: 
                    self.ixer_db = xapian.WritableDatabase(self.ix_path)
                    self.ixer = xapian.TermGenerator()
                    self.ixer_db.begin_transaction()
                    return 0
                except xapian.DatabaseLockError:
                    msg(FX_ERROR_DB, _(f"""Index locked. Waiting..."""))
                except xapian.DatabaseError as e:
                    raise FeedexIndexError('Error connecting to index at %a: %b', self.ix_path, e)

                time.sleep(10) # Interval is big because of long indexing time for large batches
        
            msg(FX_ERROR_LOCK, _('Failed to unlock index at %a (%b)'), self.ix_path, self.conn_id)
            return -2



    def close_ixer(self, **kargs):
        """ Cleanly disconnect indexer """
        rollback = kargs.get('rollback',False)
        commit = kargs.get('commit',True)

        if isinstance(self.ixer_db, xapian.WritableDatabase): 
            self.ixer = None

            if commit: 
                debug(2,'Writing to Index...')
                try: self.ixer_db.commit_transaction()
                except (xapian.Error,) as e:
                    self.ixer_db.cancel_transaction()
                    self.ixer_db.close()
                    return msg(FX_ERROR_INDEX, _('Indexer error: %a'), e)                 
            if rollback:
                debug(2,'Index changes cancelled!')
                self.ixer_db.cancel_transaction()
            
            self.ixer_db.close()
            debug(2,'Done.')

        self.ixer_db = None
        return 0





    ########################################################################
    #   Locks, Fetching Locks and Timeouts
    # 
    
    
    def lock(self, **kargs):
        """ Locks DB """
        self.status = 0
        err = self.run_sql_lock("insert into params values('lock', 1)")
        if err != 0: self.status = msg(FX_ERROR_DB, _('DB error (%a): locking'), self.conn_id, log=True)
        return 0
            

    def unlock(self, **kargs):
        """ Unlocks DB """
        self.status = 0
        err = self.run_sql_lock("delete from params where name = 'lock'")
        if err != 0: self.status = msg(FX_ERROR_DB, _('DB error (%a): unlocking'), self.conn_id, log=True)
        return 0
    

    def locked(self, **kargs):
        """ Checks if DB is locked """
        lock = self.qr_sql("select * from params where name = 'lock'", all=True)
        if self.status != 0: return None
        elif lock == []: return False
        return True




    # Fetching lock helps with large inserts/updates/indexing that take a long time
    def lock_fetching(self, **kargs):
        """ Locks DB for fetching """
        fdx.db_fetch_lock = True
        return 0


    def unlock_fetching(self, **kargs):
        """ Unlocks DB for fetching """
        fdx.db_fetch_lock = False
        return 0

    
    def locked_fetching(self, **kargs):
        """ Checks if DB is locked for fetching """
        if fdx.db_fetch_lock is True: return True
        if fdx.db_fetch_lock is False: return False




    def run_fetch_locked(self, func, *args, **kargs):
        """ Wrapper to run functions within fetching lock """
        if self.locked_fetching(): return msg(FX_ERROR_LOCK, _('DB locked for fetching!'))
        if self.lock_fetching() != 0: return FX_ERROR_DB
        ret = func(*args, **kargs)
        self.unlock_fetching()
        return ret



    def loc_locked(self, **kargs):
        """ Wait for local unlock """
        timeout = kargs.get('timeout', self.config.get('timeout',30))
        check = kargs.get('check',False)
        tm = 0
        while fdx.db_lock:
            tm += 1
            if tm >= timeout or check: return True
            time.sleep(1)
        fdx.db_lock = True
        return False


    ################################################################################
    #   SQL Operations wrappers
    # 
    def _run_sql(self, query, *vals, **kargs):
        """ Safely run a SQL insert/update """
        self.status = 0

        vals = slist(vals, 0, None)
        if type(vals) in (tuple, list): many = 1
        elif type(vals) is dict: many = 0
        else: many = -1
        try:
            if many == 1:
                with self.conn: self.curs.executemany(query, vals)
            elif many == 0: 
                with self.conn: self.curs.execute(query, vals)
            else:
                with self.conn: self.curs.execute(query)
            
            self.rowcount = self.curs.rowcount
            self.lastrowid = self.curs.lastrowid
            return 0
        
        except (sqlite3.Error, sqlite3.OperationalError) as e:
            self.error = f'{e}'
            self.status = msg(FX_ERROR_DB, _('DB error (%a) - writeable: %b (%c)'), self.conn_id, e, query,  log=True)
            return FX_ERROR_DB
            


    # Below are 3 methods of safely inserting to and updating
    # All actions on DB should be performed using them!
    def run_sql_lock(self, query, *vals, **kargs):
        """ Run SQL with locking and error catching """
        ignore = kargs.get('ignore_lock',False)
        if not ignore: 
            if self.loc_locked(**kargs): return FX_ERROR_LOCK
        e = self._run_sql(query, *vals, **kargs)
        if not ignore: fdx.db_lock = False
        return e



    def run_sql_multi_lock(self, *q_query, **kargs):
        """ Run list of queries with locking """
        ignore = kargs.get('ignore_lock',False)
        if not ignore: 
            if self.loc_locked(**kargs): return FX_ERROR_LOCK
        e = 0
        for q in q_query:
            e = self._run_sql(q[0], slist(q,1,None), many=False)
            if e != 0: break
        if not ignore: fdx.db_lock = False
        return e



    # Gracefully return results of an SQL query
    def qr_sql(self, sql:str,*args, **kargs):
        """ Query databasse - no locking """
        many = kargs.get('many', False)
        fetch_one = kargs.get('one', False)
        fetch_all = kargs.get('all', False)
        self.status = 0

        if self.loc_locked(**kargs):
            self.status = msg(FX_ERROR_LOCK, _('DB locked locally (%a) (sql: %b)'), self.conn_id, sql, log=True)
            return ()
        
        try:
            if many:
                with self.conn: return self.curs.executemany(sql, *args)
            else:
                if fetch_all:
                    with self.conn: return self.curs.execute(sql, *args).fetchall()
                elif fetch_one: 
                    with self.conn: return self.curs.execute(sql, *args).fetchone()

        except (sqlite3.Error, sqlite3.OperationalError) as e:            
            self.error = f'{e}'
            self.status = msg(FX_ERROR_DB, _('DB error (%a) - read: %b (%c)'), self.conn_id, e, sql,  log=True)
            self.conn.rollback()
            return ()

        finally: fdx.db_lock = False 





    ##############################################################################
    # Data caching and lazy loading routines
    #

    def connect_LP(self, **kargs):
        """ Lazily load language processor """
        if self.LP is None: self.LP = FeedexLP(self, **kargs)

    def connect_QP(self, **kargs):
        """ Lazily load query processor """
        if self.Q is None: self.Q = FeedexQuery(self, **kargs)







    def load_feeds(self, **kargs):
        """ Load feed data from database into cache """
        if not kargs.get('ignore_lock', False):
            while self.locked_fetching(): time.sleep(1)
        
        debug(2, f'Loading feeds ({self.conn_id})...')
        fdx.feeds_cache = self.qr_sql('select * from feeds order by display_order asc', all=True)
        if self.status != 0: raise FeedexDataError('Error caching feeds: %a', self.error)
        return 0

    def load_rules(self, **kargs):
        """Load learned and saved rules from DB into cache"""
        if not kargs.get('ignore_lock',False):
            while self.locked_fetching(): time.sleep(1)
        
        debug(2, f'Loading rules ({self.conn_id})...')
        fdx.rules_cache = self.qr_sql('select * from rules order by id desc', all=True)
        if self.status != 0: raise FeedexDataError('Error caching rules: %a', self.error)
        fdx.rules_validated = False
        return 0

    def load_history(self, **kargs):
        """ Get search history into cache """
        debug(2, f'Loading search history ({self.conn_id})...')
        fdx.search_history_cache = self.qr_sql(f'{SEARCH_HISTORY_SQL} desc', all=True)
        if self.status != 0: raise FeedexDataError('Error caching history: %a', self.error)
        return 0


    def load_flags(self, **kargs):
        """ Build cached Flag dictionary """
        if not kargs.get('ignore_lock',False):
            while self.locked_fetching(): time.sleep(1)
        
        debug(2, f'Loading flags ({self.conn_id})...')
        flag_list = self.qr_sql(f'select * from flags', all=True)
        if self.status != 0: raise FeedexDataError('Error caching flags: %a', self.error)
        flag_dict = {}
        for fl in flag_list:
            flag_dict[fl[FLAGS_SQL_TABLE.index('id')]] = ( fl[FLAGS_SQL_TABLE.index('name')], fl[FLAGS_SQL_TABLE.index('desc')], fl[FLAGS_SQL_TABLE.index('color')], fl[FLAGS_SQL_TABLE.index('color_cli')] )
        fdx.flags_cache = flag_dict.copy()
        return 0


    def load_feed_freq(self, **kargs):
        """ Load feed read frequency for recommendations """
        debug(2, f'Loading marked entries freq ({self.conn_id})...')
        
        feed_freq_list = self.qr_sql(LOAD_FEED_FREQ_SQL, all=True)
        if self.status != 0: raise FeedexDataError('Error caching feed freqs: %a', self.error)
        
        # Normalize to 0-1 range
        max_freq = slist(feed_freq_list, 0, (0,0))[1]
        feed_freq_dict = {}
        for f in feed_freq_list: feed_freq_dict[f[0]] = (max_freq - f[1])/max_freq

        fdx.feed_freq_cache = feed_freq_dict


    def load_terms(self, **kargs):
        """ Load learned terms for recommendations """
        self.load_feed_freq()
        if not self.config.get('use_keyword_learning', True):
            fdx.terms_cache = ()
            fdx.recom_qr_str = ''
            return 0

        debug(2, f'Loading learned terms ({self.conn_id})...')
        if self.config.get('recom_algo') == 2: fdx.terms_cache = self.qr_sql(LOAD_TERMS_ALGO_2_SQL, all=True)
        elif self.config.get('recom_algo') == 3: fdx.terms_cache = self.qr_sql(LOAD_TERMS_ALGO_3_SQL, all=True)
        else: fdx.terms_cache = self.qr_sql(LOAD_TERMS_ALGO_1_SQL, all=True)
        if self.status != 0: raise FeedexDataError('Error caching learned terms: %a', self.error)

        # Build query string for recommendations (better do it once at the beginning)        
        limit = self.config.get('recom_limit', 250)

        qr_str = ''        
        for i,t in enumerate(fdx.terms_cache):
            s = t[0]
            if i > limit: break
            if ' ' in s: s = f"""({s.replace(' ',' ~2 ')})"""
            qr_str =f"""{qr_str} OR {s}"""
        if qr_str.startswith(' OR '): qr_str = qr_str[4:]
        qr_str = f'({qr_str})'
        fdx.recom_qr_str = qr_str
        return 0



    def load_icons(self):
        """ Loads icon paths for feeds into cache """
        debug(2, f'Loading icons ({self.conn_id})...')
        
        fdx.icons_cache = {}

        self.cache_feeds()

        for f in fdx.feeds_cache:
            id = f[FEEDS_SQL_TABLE.index('id')]
            handler = f[FEEDS_SQL_TABLE.index('handler')]
            is_category = f[FEEDS_SQL_TABLE.index('is_category')]
            icon_name = scast(f[FEEDS_SQL_TABLE.index('icon_name')], str, '')
            
            if icon_name != '':
                icon_file = os.path.join(FEEDEX_SYS_ICON_PATH, f'{icon_name}.svg')
                if os.path.isfile(icon_file):
                    fdx.icons_cache[id] = icon_file
                    continue

            if is_category == 1:
                fdx.icons_cache[id] = os.path.join(FEEDEX_SYS_ICON_PATH, 'document.svg')
            else:
                icon_file = os.path.join(self.icon_path, f'feed_{id}.ico')
                if os.path.isfile(icon_file): fdx.icons_cache[id] = icon_file
                else:
                    if handler == 'rss': fdx.icons_cache[id] = os.path.join(FEEDEX_SYS_ICON_PATH, 'news-feed.svg')
                    elif handler == 'html': fdx.icons_cache[id] = os.path.join(FEEDEX_SYS_ICON_PATH, 'www.svg')
                    elif handler == 'script': fdx.icons_cache[id] = os.path.join(FEEDEX_SYS_ICON_PATH, 'script.svg')
                    elif handler == 'local': fdx.icons_cache[id] = os.path.join(FEEDEX_SYS_ICON_PATH, 'mail.svg')
                
        return 0



    def load_fetches(self, **kargs):
        """ Load last fetches into cache """
        debug(2, f'Loading last fetches ({self.conn_id})...')
        fetches = self.qr_sql("select time, datetime(time,'unixepoch', 'localtime') from actions where name = 'fetch' order by time DESC limit :limit", {'limit':MAX_LAST_UPDATES}, all=True)
        if self.status != 0: raise FeedexDataError('Error caching fetches data: %a', self.error)
        
        fetches_cache = []
        for i,f in enumerate(fetches):
            start_ts = slist(f,0,-1)
            if i > 0: end_ts = slist( slist(fetches, i-1, ()), 0, None)
            else: end_ts = None
            label = slist(f,1,'<???>')
            fetches_cache.append( (i, label, start_ts, end_ts) )
        fdx.fetches_cache = fetches_cache


    def load_all(self, **kargs):
        """Refresh all data in the cache (wrapper)"""
        self.load_feeds()
        self.load_rules()
        self.load_terms()
        self.load_flags()
        self.load_history()
        self.load_fetches()
        debug(7, f'All data reloaded ({self.conn_id})...')
        return 0


    # Lazy caching to call from other classes as per need
    def cache_feeds(self):
        if fdx.feeds_cache is None: self.load_feeds()
    def cache_icons(self):
        if fdx.icons_cache is None: self.load_icons()
    def cache_rules(self):
        if fdx.rules_cache is None: self.load_rules()
    def cache_terms(self):
        if fdx.terms_cache is None or fdx.recom_qr_str is None: self.load_terms()
    def cache_feed_freq(self):
        if fdx.feed_freq_cache is None: self.load_feed_freq()
    def cache_flags(self):
        if fdx.flags_cache is None: self.load_flags()
    def cache_history(self):
        if fdx.search_history_cache is None: self.load_history()
    def cache_fetches(self):
        if fdx.fetches_cache is None: self.load_fetches()




    ##################################################################
    # Maintenance methods
    #

    def clear_cache(self, xdays:int, **kargs):
        """ Clear cache directory from files (images, text files etc.) older than 'xdays' days """
        # Delete old files from cache
        err = False
        now = int(datetime.now().timestamp())

        debug(6, f'Housekeeping: {now}')
        for root, dirs, files in os.walk(self.cache_path):
            for name in files:
                filename = os.path.join(root, name)
                if xdays == -1 or os.stat(filename).st_mtime < now - (xdays * 86400) or name.endswith('.txt'):
                    try: os.remove(filename)
                    except OSError as e:
                        err = True
                        msg(FX_ERROR_IO, f'{_("Error removing %a:")} {e}', filename)
                    debug(6, f'Removed : {filename}')
                if err: break
            if err: break

        if not err:
            if xdays == -1: msg(_('Cache cleared successfully...'))

      


    def maintenance(self, **kargs): return self.run_fetch_locked(self._maintenance, **kargs)
    def _maintenance(self, **kargs):
        """ Performs database maintenance to increase performance at large sizes """
        msg(_('Starting DB miantenance'))

        msg(_('Performing VACUUM'))
        err = self.run_sql_lock('VACUUM')
        if err == 0:
            msg(_('Performing ANALYZE'))
            err = self.run_sql_lock('ANALYZE')
        if err == 0:
            msg(_('REINDEXING all tables'))
            err = self.run_sql_lock('REINDEX')

        if err == 0:
            msg(_('Updating document statistics'))
            doc_count = slist(self.qr_sql(DOC_COUNT_SQL, one=True),0, 0)
            doc_count = scast(doc_count, int, 0)

            err = self.run_sql_lock("insert into params values('doc_count', :doc_count)", {'doc_count':doc_count})
            if err == 0: err = self.run_sql_lock("""insert into actions values('maintenance',:doc_count)""", {'doc_count':doc_count})
        
        if err == 0:
            self.conn.commit()
            msg(_('DB maintenance completed'), log=True)
        else: msg(FX_ERROR_DB, _('DB maintenance failed!'), log=True)




    def check_due_maintenance(self):
        """ Check if database maintenance is required """
        last_maint = slist(self.qr_sql("""select max(coalesce(time,0)) from actions where name = 'maintenance' """, one=True), 0, 0)
        doc_count = self.get_doc_count()
        if doc_count - scast(last_maint, int, 0) >= 100000: return True
        else: return False

 




    ##########################################################
    # Database statistics...
    #


    def update_stats(self):
        """ Get DB statistics and save them to params table for quick retrieval"""
        debug(2, "Updating database document statistics...")

        doc_count = scast( self.qr_sql(DOC_COUNT_SQL, one=True)[0], int, 0)
        if self.status != 0: return self.status

        fdx.doc_count = doc_count
        err = self.run_sql_multi_lock(
        ("delete from params where name = 'doc_count'",),\
        ("insert into params values('doc_count', :doc_count)", {'doc_count':doc_count})
        )

        debug(2,f"Done. Doc count: {doc_count}")
        return err



    def get_doc_count(self, **kargs):
        """ Retrieve entry count from params"""
        if fdx.doc_count is not None: return fdx.doc_count
        
        doc_count = self.qr_sql("select val from params where name = 'doc_count'", one=True)
        if doc_count in (None, (None,),()):
            self.update_stats()
            doc_count = self.qr_sql("select val from params where name = 'doc_count'", one=True)
            if doc_count in (None, (None,),()): return fdx.doc_count
        doc_count = scast(slist(doc_count,0, -1), int, 1)
        if doc_count != -1: fdx.doc_count = doc_count
        return doc_count



    def get_last_docid(self, **kargs):
        """ Get last document ID from SQL database """
        doc_id = scast( slist(self.qr_sql("select max(id) from entries", one=True), 0, -1), int, 0)
        if self.status != 0: return -1
        return doc_id



    def get_last(self, *args):
        """ Get timestamp of last news check """
        n = scast(slist(args, -1, 0), int, 0)
        self.cache_fetches()

        for f in fdx.fetches_cache:
            if f[FETCH_TABLE.index('ord')] == n: 
                return {'date_str':f[FETCH_TABLE.index('date')] ,'from':f[FETCH_TABLE.index('from')], 'to':f[FETCH_TABLE.index('to')]}
        return {'date_str': '<N/A>', 'from':None, 'to':None}


    def stats(self, **kargs):
        """ Displays database statistics """
        stat_dict = {}

        stat_dict['db_path'] = self.db_path

        stat_dict['version'] = slist(self.qr_sql("select val from params where name='version'", one=True), 0, '<???>')
        
        stat_dict['db_size'] = os.path.getsize(os.path.join(self.db_path,'main.db'))
        stat_dict['ix_size'] = get_dir_size(self.ix_path)
        stat_dict['cache_size'] = get_dir_size(self.cache_path)
        stat_dict['total_size'] = sanitize_file_size(stat_dict['db_size'] + stat_dict['ix_size'] + stat_dict['cache_size'])

        stat_dict['db_size'] = sanitize_file_size(stat_dict['db_size'])
        stat_dict['ix_size'] = sanitize_file_size(stat_dict['ix_size'])
        stat_dict['cache_size'] = sanitize_file_size(stat_dict['cache_size'])

        stat_dict['doc_count'] = slist(self.qr_sql("select val from params where name='doc_count'", one=True, ignore_errors=False), 0, 0)
        stat_dict['last_doc_id'] = self.get_last_docid()
        stat_dict['last_update'] = slist(self.qr_sql("select max(time) from actions where name = 'fetch'", one=True, ignore_errors=False), 0, '<???>')
        stat_dict['first_update'] = slist(self.qr_sql("select min(time) from actions where name = 'fetch'", one=True, ignore_errors=False), 0, '<???>')
        stat_dict['rule_count'] = slist(self.qr_sql("select count(id) from rules", one=True, ignore_errors=False), 0, 0)
        stat_dict['learned_kw_count'] = slist(self.qr_sql("select count(id) from terms", one=True, ignore_errors=False), 0, 0)

        stat_dict['feed_count'] = slist(self.qr_sql("select count(id) from feeds where coalesce(is_category,0) = 0 and coalesce(deleted,0) = 0", one=True, ignore_errors=False), 0, 0)
        stat_dict['cat_count'] = slist(self.qr_sql("select count(id) from feeds  where coalesce(is_category,0) = 1 and coalesce(deleted,0) = 0", one=True, ignore_errors=False), 0, 0)

        stat_dict['fetch_lock'] = self.locked_fetching()

        stat_dict['last_update'] = scast(stat_dict['last_update'], int, None)
        if stat_dict['last_update'] is not None: stat_dict['last_update'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat_dict['last_update']))

        stat_dict['first_update'] = scast(stat_dict['first_update'], int, None)
        if stat_dict['first_update'] is not None: stat_dict['first_update'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat_dict['first_update']))

        if self.check_due_maintenance(): stat_dict['due_maintenance'] = True
        else: stat_dict['due_maintenance'] = False
            
        return stat_dict








    #####################################################################################################
    # Mass Inesrts/Edits and Fetching






    def import_entries(self, **kargs): 
        self.cache_feeds()
        self.cache_flags()
        self.cache_terms()
        self.cache_rules()
        return self.run_fetch_locked(self._import_entries, **kargs)
    def _import_entries(self, **kargs):
        """ Wraper for inserting entries from list of dicts or a file """
        pipe = kargs.get('pipe',False)
        efile = kargs.get('efile')
        elist = kargs.get('elist')

        contents = ''
        if elist is None:
            if pipe:
                for line in sys.stdin: contents = f"{contents}\n{line}"
            elif efile is not None:
                try:
                    with open(efile, "r") as f: contents = f.read()
                except OSError as e: return msg(FX_ERROR_IO, _('Error reading %a file: %b'), efile, e)

            try: elist = json.loads(contents)
            except (json.JSONDecodeError) as e: return msg(FX_ERROR_IO, _('Error parsing JSON: %a'), e)

        # Validate data received from json
        if not isinstance(elist, (list, tuple)):  return msg(FX_ERROR_IO, _('Invalid input: must be a list of dicts!'))
        
        entry = FeedexEntry(self)
        term = FeedexKwTerm()
        elist_len = len(elist)
        now = datetime.now()
        num_added = 0


        entries_sql_q = [] # SQL statemets to be executed, adding entries
        terms_sql_d = {} # Extracted keywords 

        if pipe: msg(_('Importing entries ...'))
        else: msg(_('Importing entries from %a...'), efile)

        # Queue processing
        for i,e in enumerate(elist):

            if not isinstance(e, dict):
                msg(FX_ERROR_VAL, _('Input entry no. %a is not a dictionary!'), i)
                continue
            
            entry.clear()
            entry.strict_merge(e)

            entry['id'] = None
            entry['adddate_str'] = coalesce(entry.get('adddate_str'), now)
            entry['pubdate_str'] = coalesce(entry.get('pubdate_str'), now)

            err = entry.validate()
            if err != 0:
                msg(FX_ERROR_VAL, _('Item %a:'), i)
                msg(*err)
                continue

            learn = False
            if scast(entry['read'], int, 0) != 0: learn = True
            
            err = entry.ling(index=True, rank=True, learn=learn, save_terms=False, counter=i)
            if err != 0: 
                self.close_ixer(rollback=True)
                return msg(FX_ERROR_LP, _('Indexing or LP error in item %a precludes further actions! Aborting!'), i)

            if learn:
                terms_sql_d[entry['ix_id']] = []
                for r in entry.terms:
                    term.strict_merge(r)
                    terms_sql_d[entry['ix_id']].append(term.tuplify())
                terms_sql_d[entry['ix_id']] = tuple(terms_sql_d[entry['ix_id']])

            num_added += 1
            entries_sql_q.append(entry.vals.copy())


        if num_added > 0:
            err = self.run_sql_lock(entry.insert_sql(all=True), entries_sql_q)
            if err == 0:
                err = self.close_ixer()
                if err != 0: # Revert changes to SQL if indexing failed
                    msg(_('Reverting changes...'))
                    ix_ids = []
                    for k in terms_sql_d.keys(): ix_ids.append({'ix_id':k})
                    err = self.run_sql_lock('delete from entries where ix_id = :ix_id', ix_ids)
                    if err != 0: return msg(FX_ERROR, _('Error reverting changes! Import failed miserably'))
                    return FX_ERROR_INDEX

                # Assign context_ids to keywordss and insert them
                if len(terms_sql_d.keys()) > 0:
                    
                    terms_sql_q = []

                    ixs_list = ''
                    for ix in terms_sql_d.keys(): ixs_list = f"""{ixs_list}{ix},"""
                    if ixs_list.endswith(','): ixs_list = ixs_list[:-1]
                    ix_to_ids = self.qr_sql(f'select ix_id, id from entries where ix_id in ({ixs_list})', all=True)

                    for it in ix_to_ids:
                       ix_id = it[0]
                       id = it[1]
                       for r in terms_sql_d[ix_id]:
                           term.populate(r)
                           term['context_id'] = id
                           terms_sql_q.append(term.vals.copy())

                    if len(terms_sql_q) > 0: self.run_sql_lock(term.insert_sql(all=True), terms_sql_q, many=True)

        # stat
        if num_added > 0:
            self.update_stats()
            if not fdx.single_run: self.load_terms()
            msg(_('Added %a new entries from %b items'), num_added, elist_len, log=True)
        
        return 0






    def import_feeds(self, ifile, **kargs): 
        self.cache_feeds()
        return self.run_fetch_locked(self._import_feeds, ifile, **kargs)
    def _import_feeds(self, ifile, **kargs):
        """ Import feeds from JSON file """
        feed_data = load_json(ifile, -1)
        if feed_data == -1: return -1

        self.cache_feeds()
        if len(fdx.feeds_cache) == 0: max_id = 0
        else: max_id = max(map(lambda x: x[0], fdx.feeds_cache))

        if type(feed_data) not in (list, tuple): return msg(FX_ERROR_VAL, _('Invalid input format. Should be list of dictionaries!'))

        feed = FeedexFeed(self)
        insert_sql = []
        for i,f in enumerate(feed_data):
            if type(f) is not dict:
                msg(FX_ERROR_VAL, _('Invalid input format for item %a. Should be list of dictionaries!'), i)
                continue
            feed.clear()
            feed.strict_merge(f)
            feed_id = feed['id'] + max_id
            if scast(feed['parent_id'], int, 0) > 0: parent_id = scast(feed['parent_id'], int, 0) + max_id
            else: parent_id = None
            feed['id'] = None
            feed['parent_id'] = None
            
            err = feed.validate()
            if err != 0:
                msg(FX_ERROR_VAL, _('Item %a:'), i)
                msg(*err)
                continue

            feed['id'] = feed_id
            feed['parent_id'] = parent_id
            
            insert_sql.append(feed.vals.copy())

        if len(insert_sql) > 0:
            msg(_('Saving feeds to database...'))
            err = self.run_sql_lock(feed.insert_sql(all=True), insert_sql)
            if err == 0:
                if not fdx.single_run: err = self.load_feeds(ignore_lock=True)
            if err == 0: 
                return msg(_('Feeds imported successfully!'))

        return 0



    def import_rules(self, ifile, **kargs): 
        self.cache_rules()
        self.cache_feeds()
        self.cache_flags()
        return self.run_fetch_locked(self._import_rules, ifile, **kargs)
    def _import_rules(self, ifile, **kargs):
        """ Import rules from JSON """
        rule_data = load_json(ifile, -1)
        if rule_data == -1: return -1

        if type(rule_data) not in (list, tuple): return msg(FX_ERROR_VAL, _('Invalid input format. Should be list of dictionaries!'))

        rule = FeedexRule(self)
        insert_sql = []
        for i,r in enumerate(rule_data):
            if type(r) is not dict: 
                msg(FX_ERROR_VAL, _('Invalid input format for item %a. Should be list of dictionaries!'), i)
                continue
            rule.clear()
            rule.strict_merge(r)
            rule['id'] = None
            
            err = rule.validate()
            if err != 0: 
                msg(FX_ERROR_VAL, _('Item %a:'), i)
                msg(*err)
                continue
            
            insert_sql.append(rule.vals.copy())

        if len(insert_sql) > 0:
            msg(_('Saving rules to database...'))
            err = self.run_sql_lock(rule.insert_sql(all=True), insert_sql)
            if err == 0:
                if not fdx.single_run: err = self.load_rules(ignore_lock=True)
            if err == 0: 
                return msg(_('Rules imported successfully!'))

        return 0




    def import_flags(self, ifile, **kargs): 
        self.cache_flags()
        return self.run_fetch_locked(self._import_flags, ifile, **kargs)
    def _import_flags(self, ifile, **kargs):
        """ Import flags from JSON """
        
        flag_data = load_json(ifile, -1)
        if flag_data == -1: return FX_ERROR_IO

        if type(flag_data) not in (list, tuple): return msg(FX_ERROR_VAL, _('Invalid input format. Should be list of dictionaries!'))

        flag = FeedexFlag(self)
        insert_sql = []
        for i,f in enumerate(flag_data):
            if type(f) is not dict: 
                msg(FX_ERROR_VAL, _('Invalid input format for item %a. Should be list of dictionaries!'), i)
                continue
            flag.clear()
            flag.strict_merge(f)

            err = flag.validate()
            if err != 0: 
                msg(FX_ERROR_VAL, _('Item %a:'), i)
                msg(*err)
                continue

            insert_sql.append(flag.vals.copy())

        if len(insert_sql) > 0:
            msg(_('Saving flags to database...'))
            err = self.run_sql_lock(flag.insert_sql(all=True), insert_sql)
            if err == 0:
                if not fdx.single_run: err = self.load_flags(ignore_lock=True)
            if err == 0: return msg(_('Flags imported successfully!'))

        return 0












    def fetch(self, **kargs): 
        self.cache_feeds()
        self.cache_rules()
        self.cache_flags()
        return self.run_fetch_locked(self._fetch, **kargs) 
    def _fetch(self, **kargs):
        """ Check for news taking into account specified intervals and defaults as well as ETags and Modified tags"""

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

        self.feed = SQLContainer('feeds', FEEDS_SQL_TABLE)
        self.entry = SQLContainer('entries', ENTRIES_SQL_TABLE)

        self.cache_feeds()

        for feed in fdx.feeds_cache:

            self.feed.clear()
            self.feed.populate(feed)

            # Check for processing conditions...
            if self.feed['deleted'] == 1 and not update_only and feed_id == 0: continue
            if self.feed['fetch'] in (None,0) and feed_id == 0 and feed_ids is None: continue
            if feed_id != 0 and feed_id != self.feed['id']: continue
            if feed_ids is not None and self.feed['id'] not in feed_ids: continue
            if self.feed['is_category'] not in (0,None) or self.feed['handler'] in ('local',): continue

            # Ignore unhealthy feeds...
            if scast(self.feed['error'],int,0) >= self.config.get('error_threshold',5) and not kargs.get('ignore_errors',False):
                msg(_('Feed %a ignored due to previous errors'), self.feed.name(id=True))
                continue

            #Check if time difference exceeds the interval
            last_checked = scast(self.feed['lastchecked'], int, 0)
            if not ignore_interval:
                diff = (started - last_checked)/60
                if diff < scast(self.feed['interval'], int, self.config.get('default_interval',45)):
                    debug(f'Feed {self.feed["id"]} ignored (interval: {self.feed["interval"]}, diff: {diff})')
                    continue

            msg(_('Processing %a ...'), self.feed.name())

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
                msg(_('Channel handled locally... Ignoring...'))
                continue
            
            else:
                msg(FX_ERROR_HANDLER, _('Handler %a not recognized!'), self.feed['handler'])
                continue     

            # Set up feed-specific user agent
            if self.feed['user_agent'] not in (None, ''):
                msg(_('Using custom User Agent: %a'), self.feed['user_agent'])
                handler.set_agent(self.feed['user_agent'])
            else: handler.set_agent(None)

            # Start fetching ...
            if not update_only:

                pguids = self.qr_sql("""select distinct guid from entries e where e.feed_id = :feed_id""", {'feed_id':self.feed['id']} , all=True)
                if handler.compare_links: plinks = self.qr_sql("""select distinct link from entries e where e.feed_id = :feed_id""", {'feed_id':self.feed['id']} , all=True, ignore_errors=False)
                else: plinks = ()
                
                if self.status != 0:
                    msg(FX_ERROR_DB, _('Feed %a ignored due to DB error: %b'), self.feed.name(), self.error, log=True)
                    continue


                handler.set_feed(self.feed)
                for item in handler.fetch(self.feed, force=force, pguids=pguids, plinks=plinks, last_read=last_read, last_checked=last_checked):
                    
                    if isinstance(item, FeedexEntry):
                        self.new_items += 1
                        err = item.validate_types()
                        if err != 0: 
                            msg(FX_ERROR_VAL, _('Entry %a (feed: %b) invalid data type: %b'), self.new_items, self.feed.get('url'), err)
                            continue
                        
                        if not skip_ling:
                            item.set_feed(feed=feed)
                            err = item.ling(index=True, stats=True, rank=True, learn=False, counter=tech_counter)
                            if err != 0:
                                self.DB.close_ixer(rollback=True)
                                return msg(FX_ERROR_LP, _('Item %a (feed: %b): LP error precludes further actions!'), self.new_items, self.feed.get('url'))
                            
                            vals = item.vals.copy()
                            entries_sql.append(vals)
                        else:
                            entries_sql.append(item.vals.copy())

                        # Track new entries and take care of massive insets by dividing them into parts
                        tech_counter += 1
                        if tech_counter >= self.config.get('max_items_per_transaction', 2000):                            
                            msg(_('Saving new items ...'))
                            err = self.run_sql_lock(self.entry.insert_sql(all=True), entries_sql)
                            if err == 0: 
                                msg(_('Indexing new items ...'))
                                err = self.close_ixer()                 
                                if err != 0:
                                    msg(_('Reverting changes...'))
                                    ix_ids = []
                                    for v in entries_sql.values(): ix_ids.append({'ix_id':v.get('ix_id')})
                                    err = self.run_sql_lock('delete from entries where ix_id = :ix_id', ix_ids)
                                    if err != 0: return msg(FX_ERROR_DB, _('Error reverting changes! Fetching failed miserably'))
                                    return FX_ERROR_INDEX

                            err = self.run_sql_lock("""update feeds set lastread = :now, lastchecked = :now, etag = :etag, modified = :modified, http_status = :status, error = 0  where id = :id""", feeds_sql)
                            if err == 0:
                                feeds_sql = []
                                entries_sql = []
                            else:
                                self.close_ixer(rollback=True)
                                return msg(FX_ERROR_DB, _('Fetching aborted! DB error: %a'), err)

                            tech_counter = 0  


             


            else:
                # This bit is if no fetching is done (just meta update)
                handler.set_feed(self.feed)
                handler.download(force=force)



            if handler.error:
                # Save info about errors if they occurred
                if update_only: err = self.run_sql_lock("""update feeds set http_status = :status, error = coalesce(error,0)+1 where id = :id""", {'status': handler.status, 'id': self.feed['id']} )
                else: err = self.run_sql_lock("""update feeds set lastchecked = :now, http_status = :status, error = coalesce(error,0)+1 where id = :id""", {'now':now_raw, 'status':handler.status, 'id': self.feed['id']} )
                if err != 0: return err
                continue

            else:				
                #Update feed last checked date and other data
                if update_only: 
                    err = self.run_sql_lock("""update feeds set http_status = :status, error = 0  where id = :id""", {'status':handler.status, 'id': self.feed['id']} )
                    if err != 0: return err
                else:
                    feeds_sql.append({'now':now_raw, 'etag':handler.etag, 'modified':handler.modified, 'status':handler.status, 'id':self.feed['id']})
                


            # Inform about redirect
            if handler.redirected: msg(_('Channel redirected: %a'), self.feed['url'], log=True)

            # Save permanent redirects to DB
            if handler.feed_raw.get('href',None) != self.feed['url'] and handler.status == 301:
                self.feed['url'] = rss_handler.feed_raw.get('href',None)
                if not update_only and kargs.get('save_perm_redirects', self.config.get('save_perm_redirects', False) ):
                    err = self.run_sql_lock('update feeds set url = :url where id = :id', {'url':self.feed['url'], 'id':self.feed['id']} )    
                    if err != 0: return err

            # Mark deleted as unhealthy to avoid unnecessary fetching
            if handler.status == 410 and self.config.get('mark_deleted',False):
                err = self.run_sql_lock('update feeds set error = :err where id = :id', {'err':self.config.get('error_threshold',5), 'id':self.feed['id']})
                if err != 0: return err



            # Autoupdate metadata if needed or specified by 'forced' or 'update_only'
            if (scast(self.feed['autoupdate'], int, 0) == 1 or update_only) and not handler.no_updates:

                msg(_('Updating metadata for %a'), self.feed.name())

                handler.update(self.feed)
                if not handler.error:

                    updated_feed = handler.feed

                    if updated_feed == -1:
                        msg(FX_ERROR_HANDLER, _('Error updating metadata for feed %a'), self.feed.name(id=True))
                        continue
                    elif updated_feed == 0:
                        continue
                    
                    err = updated_feed.validate_types()
                    if err != 0: msg(FX_ERROR_VAL, _('Invalid data type: %a'), err)
                    else:
                        err = self.run_sql_lock(updated_feed.update_sql(wheres=f'id = :id'), updated_feed.vals)
                        if err != 0: return err
        
                    meta_updated = True
                    msg(_('Metadata updated for feed %a'), self.feed.name())


            # Stop if this was the specified feed (i.e. there was a feed specified and a loop was executed)...
            if feed_id != 0: break


        # Push final entries to DB (the same as when tech_counter hit before)           
        if not update_only:
            if len(entries_sql) > 0:
                msg(_('Saving new items ...'))
                err = self.run_sql_lock(self.entry.insert_sql(all=True), entries_sql)
                if err == 0: 
                    msg(_('Indexing new items ...'))
                    err = self.close_ixer()
                    if err != 0:
                        msg(_('Reverting changes...'))
                        ix_ids = []
                        for v in entries_sql.values(): ix_ids.append({'ix_id':v.get('ix_id')})
                        err = self.run_sql_lock('delete from entries where ix_id = :ix_id', ix_ids)
                        if err != 0: return msg(FX_ERROR_DB, _('Error reverting changes! Fetching failed miserably'))
                        return FX_ERROR_INDEX
                    
                    err =  self.run_sql_lock("""update feeds set lastread = :now, lastchecked = :now, etag = :etag, modified = :modified, http_status = :status, error = 0  where id = :id""", feeds_sql)
                
                else:
                    self.close_ixer(rollback=True)
                    return msg(FX_ERROR_DB,_('Fetching aborted!'))



        # ... finally, do maintenance ....
        if meta_updated and not fdx.single_run: self.load_feeds(ignore_lock=True)

        if self.new_items > 0:
            err = self.run_sql_lock("""insert into actions values('fetch', :started)""", {'started':started} )
            if err != 0: return err
            elif not fdx.single_run: self.load_fetches()

        if kargs.get('update_stats',True):
            if self.new_items > 0: 
                msg(_('Updating statistics ...'))
                self.update_stats()

        finished_raw = datetime.now()
        finished = int(finished_raw.timestamp())
        ddelta_raw = finished - started
        dmins = str(int(ddelta_raw/60)).zfill(2)
        dsecs = str(int(ddelta_raw % 60)).zfill(2)
        duration = f'{dmins}:{dsecs}'
        

        if not update_only: msg(_('Finished fetching (%a new articles), duration: %b'), self.new_items, duration)
        else: msg(_('Finished updating metadata, duration: %a'), duration)

        del self.__dict__['feed']
        del self.__dict__['entry']
        
        return 0






    def recalculate(self, **kargs): 
        self.cache_feeds()
        self.cache_rules()
        self.cache_flags()        
        return self.run_fetch_locked(self._recalculate, **kargs)
    def _recalculate(self, **kargs):
        """ Utility to recalculate, retokenize, relearn, etc. 
            Useful for mass operations """

        entry_id = scast(kargs.get('id'), int, 0)

        if entry_id == 0:
            start_id = kargs.get('start_id', 0)
            if start_id is None: start_id = 0
            end_id = kargs.get('end_id', None)
            if end_id is None:
                end_id = self.get_last_docid()
                if end_id == -1: return -2

            batch_size = kargs.get('batch_size', None)
            if batch_size is None: batch_size = self.config.get('max_items_per_transaction', 1000)

        learn = kargs.get('learn',False)
        rank = kargs.get('rank',False)
        index = kargs.get('index',False)

        entry = FeedexEntry(self)
        term = FeedexKwTerm()

        entry_q = []
        terms_q = []
        terms_ids_q = []

        vals = {}
        vs = {}

        if entry_id in (0, None):
            many = True
            msg(_("Mass recalculation started..."), log=True)
            if rank: msg(_("Ranking according to rules..."), log=True)
            if learn: msg(_("Learning keywords ..."), log=True)
            if index: msg(_("Indexing ..."), log=True)

            SQL = RECALC_MULTI_SQL

            debug(4, f"Batch size: {batch_size}\nRange: {start_id}..{end_id}")
        
        else:
            many = False
            msg(_("Recalculating entry %a ..."), entry_id)
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


            if many: msg(_('Getting entries...'))
            entries = self.qr_sql(SQL, vs, all=True)
            if self.status != 0: return self.status
            
            for i,e in enumerate(entries):

                entry.populate(e)
    
                if many and learn and coalesce(entry['read'],0) == 0: continue
                msg(_(f"Processing entry %a ({entry['read']})..."), entry['id'])

                err = entry.ling(learn=learn, index=index, rank=rank, save_terms=False, multi=True, counter=i, rebuilding=True)
                if err != 0: 
                    self.DB.close_ixer(rollback=True) 
                    return msg(FX_ERROR_LP, _('Error while linguistic processing %a!'), e['id'])

                vals = {'id': entry['id']}
                if index:
                    for f in ENTRIES_TECH_LIST: vals[f] = entry[f] 
                if rank:
                    vals['importance'] = entry['importance']
                    vals['flag'] = entry['flag']

                if learn:
                    for r in entry.terms: terms_q.append(r)
                    terms_ids_q.append({'id': entry['id']})

                entry_q.append(vals.copy())



            if len(entry_q) > 0:
                msg(_('Committing batch ...'))
                err = self.run_sql_lock(entry.update_sql(filter=vals.keys(), wheres='id = :id'), entry_q)
                if err != 0: 
                    self.DB.close_ixer(rollback=True) 
                    return err

            if learn:
                msg(_('Learning keywords from batch ...'))
                if len(terms_ids_q) > 0:
                    err = self.run_sql_lock('delete from terms where context_id = :id', terms_ids_q)
                if len(terms_q) > 0:
                    if err == 0: err = self.run_sql_lock(term.insert_sql(all=True), terms_q)
                    if err != 0: return err

            if index: self.close_ixer()                   

            entry_q.clear()
            terms_q.clear()
            terms_ids_q.clear()

            msg(_('Batch committed'), log=True)


        msg(_('Recalculation finished!'), log=True)

        self.update_stats()
        if learn: 
            if not fdx.single_run: self.load_terms()

        return 0










#################################################
# Utilities 

    def clear_history(self, **kargs):
        """ Clears search history """
        err = self.run_sql_lock("delete from search_history")
        if err != 0: return err
        else: items_deleted = self.rowcount
        if not fdx.single_run: self.load_history()
        return msg(_('Deleted %a items from search history'), items_deleted)
        
        
    def delete_learned_terms(self, **kargs):
        """ Deletes all learned keywords """
        err = self.run_sql_lock("""delete from terms""")
        if err != 0: return err
        else:
            deleted_terms = self.rowcount
            if not fdx.single_run: self.load_terms()
            return msg(_('Deleted %a learned keywords'), deleted_terms)



    def empty_trash(self, **kargs):
        """ Removes all deleted items permanently """
        # Delete permanently with all data
        terms_deleted = 0
        entries_deleted = 0
        feeds_deleted = 0
        err = self.run_sql_lock(EMPTY_TRASH_TERMS_SQL)
        terms_deleted = self.rowcount
        if err == 0:
            err = self.run_sql_lock(EMPTY_TRASH_ENTRIES_SQL)
            entries_deleted = self.rowcount
        if err == 0: err = self.run_sql_lock(EMPTY_TRASH_FEEDS_SQL1)
        if err == 0:
            feeds_to_remove = self.qr_sql('select id from feeds where deleted = 1', all=True)
            if self.status != 0: return self.status
            for f in feeds_to_remove:
                self.cache_icons()
                icon = fdx.icons_cache.get(f)
                if icon is not None and icon.startswith( os.path.join(self.icon_path, 'feed_') ) and os.path.isfile(icon): os.remove(icon)
        else: return err

        err = self.run_sql_lock(EMPTY_TRASH_FEEDS_SQL2)
        feeds_deleted = self.rowcount
        if err != 0: return err
 
        if not fdx.single_run: self.load_feeds(ignore_lock=True)

        return msg(_('Trash emptied: %a channels/categories, %b entries, %c learned keywords removed'), feeds_deleted, entries_deleted, terms_deleted, log=True)
                     




