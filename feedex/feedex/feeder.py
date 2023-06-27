# -*- coding: utf-8 -*-
""" 
Main engine for Feedex news reader. Database interface and REST handling, main Fetching mechanism, interface with ling processor

"""

from feedex_headers import *



class FeedexDatabaseError(FeedexError):
    """ Irrecoverable Feedex database error (e.g. unable to connect, corrupted database )"""
    def __init__(self, *args): super().__init__(*args)

class FeedexDataError(FeedexDatabaseError):
    """ Something went wrong with retrieving or caching data like feeds, rules, flags etc."""
    def __init__(self, *args): super().__init__(*args)


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

        # New items from last fetching/import
        self.new_items = 0

        # Database status (for error catching)
        self.status = 0

        # Flag if db creation is allowed
        self.allow_create = kargs.get('allow_create',False)
        self.no_defaults = kargs.get('no_defaults',False) # Should defaults be loaded upon creation?

        self.timeout = kargs.get('timeout', self.config.get('timeout',15)) # Wait time if DB is locked
        

        # Define SQLite interfaces
        self.conn = None
        self.curs = None
        # .. and Xapian stuff...
    

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

        # Check DB folders ...
        if not os.path.isdir(self.db_path):
            if self.allow_create:
                msg(_('DB not found. Creating one now at %a...'), self.db_path)
                try:
                    os.makedirs(self.db_path)
                    msg(_('Created %a...'), self.db_path)
                except (OSError,) as e: raise FeedexDatabaseError(FX_ERROR_DB, _('Error creating database: %a'), e)
            else: raise FeedexDatabaseError(FX_ERROR_DB, _('DB %a not found. Aborting...'), self.db_path)

        if self.allow_create:
            # Check/create cache and icon dirs
            if not os.path.isdir(self.icon_path):
                try:
                    os.makedirs(self.icon_path)
                    msg(_('Icon folder %a created...'), self.icon_path)
                except (OSError, IOError): raise FeedexDatabaseError(FX_ERROR_DB, _('Error creating icon folder %a'), self.icon_path)

            if not os.path.isdir(self.cache_path):
                try:
                    os.makedirs(self.cache_path)
                    msg(_('Cache folder %a created...'), self.cache_path)
                except (OSError, IOError): raise FeedexDatabaseError(FX_ERROR_DB, _('Error creating cache folder %a'), self.cache_path)


        # Init SQLite DB
        if not os.path.isfile(self.sql_path): 
            if self.allow_create: 
                create_sqlite = True 
                msg(_('Creating SQL DB %a...'), self.sql_path) 
            else: raise FeedexDatabaseError(-2, _('SQL DB %a not found! Aborting...'), self.sql_path)
        else: create_sqlite = False

        # Establish SQLite3 connection and cursor...
        try:
            self.conn = sqlite3.connect(self.sql_path)
            self.curs = self.conn.cursor()
        except (sqlite3.Error, sqlite3.OperationalError, OSError) as e: raise FeedexDatabaseError(FX_ERROR_DB, _('DB connection error: %a'), e)

        # Some technical stuff...
        try:
            with self.conn: self.curs.execute("PRAGMA case_sensitive_like=true")
            #with self.conn: self.curs.execute("PRAGMA cache_size=5000")
        except sqlite3.Error as e: raise FeedexDatabaseError(FX_ERROR_DB, f'{_("Error setting up PRAGMA")} ({self.sql_path}): %a', e)



        # Handle SQLite structure, if not there...
        if create_sqlite:
            # Run DDL on fresh DB
            try:
                sql_scripts_path = os.path.join(FEEDEX_SYS_SHARED_PATH,'data','db_scripts')
                with open(os.path.join(sql_scripts_path, 'feedex_db_ddl.sql'), 'r') as sql: sql_ddl = sql.read()
                with self.conn: self.curs.executescript(sql_ddl)
                msg(_('Database structure created'))
            except (sqlite3.Error, sqlite3.OperationalError, OSError) as e:
                raise FeedexDatabaseError(FX_ERROR_DB, _('Error writing DDL scripts to database! %a'), e)
            
            # Add defaults if allowed ...
            if not self.no_defaults:
                try:
                    with open( os.path.join(sql_scripts_path,'feedex_db_defaults.sql'), 'r') as sql: sql_ddl = sql.read()
                    with self.conn: self.curs.executescript(sql_ddl)
                    msg(0, _('Added defaults...'))
                except (sqlite3.Error, sqlite3.OperationalError, OSError) as e:
                    raise FeedexDatabaseError(FX_ERROR_DB, _('Error writing defaults to database: %a'), e)

        if self.allow_create:
            # Checking versions and aborting if needed
            try: version = slist(self.curs.execute("select val from params where name = 'version'").fetchone(), 0, None)
            except (sqlite3.Error, sqlite3.OperationalError, OSError) as e:
                raise FeedexDatabaseError(FX_ERROR_DB, _('Error getting version from DB: %a'), e)

            if version != FEEDEX_DB_VERSION_COMPAT:
                raise FeedexDatabaseError(FX_ERROR_DB, _('Application version incompatibile with %a Database! Aborting'), self.db_path)


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
                    raise FeedexDatabaseError(FX_ERROR_DB, f'{_("Error creating index")} {self.ix_path}: %a', e)
            
                # Final try ...
                try:
                    self.ix = xapian.Database(self.ix_path)
                    debug(2,f'Connected to index {self.ix_path}')
                except (xapian.DatabaseError,) as e:
                    raise FeedexDatabaseError(FX_ERROR_DB,  f'{_("Could not connect to index at")} {self.ix_path}: %a', e)           
            
            else: raise FeedexDatabaseError(FX_ERROR_DB,  f'{_("Could not connect to index at ")} {self.ix_path}: %a', e)

        fdx.conn_num += 1
        self.conn_id = fdx.conn_num
        return 0



    def close(self, **kargs):
        """ Close this connection """
        self.conn.close()
        self.ix.close()
        self.close_ixer()
        fdx.conn_num -= 1
        debug(2,f'Connection {self.conn_id} closed...')




    # Indexer stuff...
    def connect_ixer(self, **kargs):
        """ Connect writing indexer lazily """
        if not (isinstance(self.ixer_db, xapian.WritableDatabase) and  isinstance(self.ixer, xapian.TermGenerator)):
            while True: # We need to wait indefinitely for index to be free to avoid unindexed entries
                try: 
                    self.ixer_db = xapian.WritableDatabase(self.ix_path)
                    self.ixer = xapian.TermGenerator()
                    self.ixer_db.begin_transaction()
                    return 0
                except xapian.DatabaseLockError:
                    msg(FX_ERROR_DB, _(f"""Index locked. Waiting..."""))
                except xapian.DatabaseError as e:
                    raise FeedexDatabaseError(FX_ERROR_DB, _(f"""Error connecting to index: %a"""), e )

                time.sleep(10) # Interval is big because of long indexing time for large batches
        
            msg(FX_ERROR_LOCK, f'{_("Failed to unlock index")} ({self.conn_id})')
            return -2



    def close_ixer(self, **kargs):
        """ Cleanly disconnect indexer """
        rollback = kargs.get('rollback',False)
        commit = kargs.get('commit',True)
        if isinstance(self.ixer_db, xapian.WritableDatabase): 
            self.ixer = None
            debug(2,'Writing to Index...')
            if commit: self.ixer_db.commit_transaction()
            if rollback: 
                debug(2,'Index changes cancelled!')
                self.ixer_db.cancel_transaction()
            self.ixer_db.close()
            debug(2,'Done.')
        self.ixer_db = None






    ########################################################################
    #   Locks, Fetching Locks and Timeouts
    # 
    def lock(self, **kargs):
        """ Locks DB """
        self.status = 0
        try:
            with self.conn: self.curs.execute("insert into params values('lock', 1)")
            fdx.db_lock = True
            return 0
        except (sqlite3.Error, sqlite3.OperationalError) as e:
            self.status = msg(FX_ERROR_LOCK, f'{_("DB error")} ({self.conn_id} - {_("locking")}): %a', e, log=True)
            return -2
            

    def unlock(self, **kargs):
        """ Unlocks DB """
        if kargs.get('ignore',False): return 0
        # Need to do a loop to make sure DB is unlocked no matter what
        tm = 0
        while tm <= self.timeout or self.timeout == 0:        
            try:
                with self.conn: self.curs.execute("delete from params where name='lock'")
                fdx.db_lock = False
                return 0
            except (sqlite3.Error, sqlite3.OperationalError) as e:
                self.status = msg(FX_ERROR_LOCK, f'{_("DB error")} ({self.conn_id} - {_("unlocking")}): %a', e)
            tm = tm + 1
            time.sleep(1)
        
        self.status = msg(FX_ERROR_LOCK, f'{_("Failed to unlock DB")} ({self.conn_id})', log=True)
        return -2

    

    def locked(self, **kargs):
        """ Checks if DB is locked and waits the timeout checking for availability before aborting"""
        if kargs.get('ignore',False): return False
        check = kargs.get('just_check', False)

        tm = 0
        while tm <= self.timeout or self.timeout == 0:
            if not fdx.db_lock: lock = self.qr_sql("select * from params where name = 'lock'", one=True)
            else: lock = 1

            if lock is not None: 
                if check: return True
                msg(FX_ERROR_LOCK, f"{_('Database locked')} ({self.conn_id}). {_('Waiting')}... {tm}")     
            else: 
                if check: return False
                self.lock()
                return False
            tm = tm + 1
            time.sleep(1)

        msg(FX_ERROR_LOCK, f'{_("Timeout reached")} ({self.conn_id}). {_("Aborting")}...')
        return True



    # Fetching lock helps with large inserts/updates/indexing that take a long time
    def lock_fetching(self, **kargs):
        """ Locks DB for fetching """
        self.status = 0
        try:
            with self.conn: self.curs.execute("insert into params values('fetch_lock', 1)")
            fdx.db_fetch_lock = True
            return 0
        except (sqlite3.Error, sqlite3.OperationalError) as e:
            self.status = msg(FX_ERROR_LOCK, f'{_("DB error")} ({self.conn_id} - {_("locking for fetching")}): %a', e, log=True)
            return -2
            

    def unlock_fetching(self, **kargs):
        """ Unlocks DB for fetching """
        if kargs.get('ignore',False): return 0
        # Need to do a loop to make sure DB is unlocked no matter what
        tm = 0
        while tm <= self.timeout or self.timeout == 0:        
            try:
                with self.conn: self.curs.execute("delete from params where name='fetch_lock'")
                fdx.db_fetch_lock = False
                return 0
            except (sqlite3.Error, sqlite3.OperationalError) as e:
                self.status = msg(FX_ERROR_LOCK, f'{_("DB error")} ({self.conn_id} - {_("unlocking for fetching")}): %a', e)
            tm = tm + 1
            time.sleep(1)
        
        self.status = msg(FX_ERROR_LOCK, f'{_("Failed to unlock DB for fetching")} ({self.conn_id})', log=True)
        return -2

    

    def locked_fetching(self, **kargs):
        """ Checks if DB is locked for fetching and waits the timeout checking for availability before aborting"""
        if kargs.get('ignore',False): return False
        check = kargs.get('just_check', False)

        tm = 0
        while tm <= self.timeout or self.timeout == 0:
            if not fdx.db_fetch_lock: flock = self.qr_sql("select * from params where name = 'fetch_lock'", one=True)
            else: flock = 1

            if flock is not None: 
                if check: return True
                msg(FX_ERROR_LOCK, f"{_('Database locked')} ({self.conn_id}). {_('Waiting')}... {tm}")     
            else: 
                if check: return False
                self.lock_fetching()
                return False
            tm = tm + 1
            time.sleep(1)

        msg(FX_ERROR_LOCK, f'{_("Timeout reached")} ({self.conn_id}). {_("Aborting")}...')
        return True









    ################################################################################
    #   SQL Operations wrappers
    # 
    def _run_sql(self, query:str, vals:list, **kargs):
        """ Safely run a SQL insert/update """
        many = kargs.get('many',False)
        self.status = 0
        try:
            if many:
                with self.conn: self.curs.executemany(query, vals)
            else: 
                with self.conn: self.curs.execute(query, vals)
            self.rowcount = self.curs.rowcount
            self.lastrowid = self.curs.lastrowid
            return 0
        except (sqlite3.Error, sqlite3.OperationalError) as e:
            self.status = msg(FX_ERROR_DB, f'{_("DB error")} ({self.conn_id} - {_("write")}): %a ({query})', e, log=True)
            return -2
            


    # Below are 3 methods of safely inserting to and updating
    # All actions on DB should be performed using them!
    def run_sql_lock(self, query:str, vals:list, **kargs):
        """ Run SQL with locking and error catching """
        if self.locked(ignore=kargs.get('ignore_lock', False)): return msg(FX_ERROR_LOCK,_('Database busy'))
        e = self._run_sql(query, vals, **kargs)
        self.unlock()
        return e

    def run_sql_multi_lock(self, qs:list, **kargs):
        """ Run list of queries with locking """
        if self.locked(ignore=kargs.get('ignore_lock', False)): return msg(FX_ERROR_LOCK,_('Datbase busy'))
        e = 0
        for q in qs:
            e = self._run_sql(q[0], q[1], many=False)
            if e != 0: break
        self.unlock()
        return e



    # Gracefully return results of an SQL query
    def qr_sql(self, sql:str,*args, **kargs):
        """ Query databasse - no locking """
        many = kargs.get('many', False)
        fetch_one = kargs.get('one', False)
        fetch_all = kargs.get('all', False)
        self.status = 0

        tm=0
        ready = False
        while tm <= self.timeout or self.timeout == 0: # This will queue the query if there is something else going on locally...
            if not fdx.db_lock:
                ready = True
                break
            else: msg(FX_ERROR_LOCK, f'DB locked locally (sql: {sql}) ({self.conn_id})... waiting {tm}')
            tm += 1
            time.sleep(1)

        if not ready: 
            self.status = msg(FX_ERROR_LOCK, f'{_("DB error")} ({self.conn_id} - {_("read")}): %a ({sql})', _('Local lock timeout reached'))
            return ()
        
        try:
            fdx.db_lock = True      
            if many:
                with self.conn: return self.curs.executemany(sql, *args)
            else:
                if fetch_all:
                    with self.conn: return self.curs.execute(sql, *args).fetchall()
                elif fetch_one: 
                    with self.conn: return self.curs.execute(sql, *args).fetchone()
            
        except (sqlite3.Error, sqlite3.OperationalError) as e:            
            self.status = msg(FX_ERROR_DB, f'{_("DB error")} ({self.conn_id} - {_("read")}): %a ({sql})', e, log=True)
            self.conn.rollback()
            fdx.db_lock = False
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


    def load_feeds(self):
        """ Load feed data from database into cache """
        debug(2, f'Loading feeds ({self.conn_id})...')
        fdx.feeds_cache = self.qr_sql(f'{GET_FEEDS_SQL}', all=True)
        if fdx.feeds_cache == -1: raise FeedexDataError(FX_ERROR_DB, _('Error loading feed data from %a'), self.sql_path)
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
                elif os.path.isfile(icon_name):
                    fdx.icons_cache[id] = icon_name
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




    def load_rules(self, **kargs):
        """Load learned and saved rules from DB into cache"""
        debug(2, f'Loading rules ({self.conn_id})...')
        no_limit = kargs.get('no_limit',False)
        limit = scast(self.config.get('rule_limit'), int, 50000)

        if not self.config.get('use_keyword_learning', True):  
            fdx.rules_cache = self.qr_sql(GET_RULES_NL_SQL, all=True)
        else:
            if no_limit or limit == 0: fdx.rules_cache = self.qr_sql(GET_RULES_SQL, all=True)
            else: fdx.rules_cache = self.qr_sql(f'{GET_RULES_SQL}LIMIT :limit', {'limit':limit} , all=True)           

        if fdx.rules_cache == -1: raise FeedexDataError(FX_ERROR_DB, _('Error loading rules from %a'), self.sql_path)
        fdx.rules_validated = False
        return 0


    def load_history(self, **kargs):
        """ Get search history into cache """
        debug(2, f'Loading search history ({self.conn_id})...')
        fdx.search_history_cache = self.qr_sql(f'{SEARCH_HISTORY_SQL} desc', all=True)
        if fdx.search_history_cache == -1: raise FeedexDataError(FX_ERROR_DB, 'Error loading search history from %a', self.sql_path)
        return 0


    def load_flags(self, **kargs):
        """ Build cached Flag dictionary """
        debug(2, f'Loading flags ({self.conn_id})...')
        flag_list = self.qr_sql(f'select * from flags', all=True)
        if flag_list != -1:
            flag_dict = {}
            for fl in flag_list:
                flag_dict[fl[FLAGS_SQL_TABLE.index('id')]] = ( fl[FLAGS_SQL_TABLE.index('name')], fl[FLAGS_SQL_TABLE.index('desc')], fl[FLAGS_SQL_TABLE.index('color')], fl[FLAGS_SQL_TABLE.index('color_cli')] )
            fdx.flags_cache = flag_dict.copy()
            return 0
        else: raise FeedexDataError(FX_ERROR_DB, _('Error loading flags from %a'), self.sql_path)



    def load_all(self, **kargs):
        """Refresh all data in the cache (wrapper)"""
        self.cache_feeds()
        self.cache_rules()
        self.cache_flags()
        self.cache_history()
        debug(7, f'All data recached ({self.conn_id})...')
        return 0

    # Lazy caching to call from other classes as per need
    def cache_feeds(self):
        if fdx.feeds_cache is None: self.load_feeds()
    def cache_icons(self):
        if fdx.icons_cache is None: self.load_icons()
    def cache_rules(self):
        if fdx.rules_cache is None: self.load_rules()
    def cache_flags(self):
        if fdx.flags_cache is None: self.load_flags()
    def cache_history(self):
        if fdx.search_history_cache is None: self.load_history()





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

      



    def maintenance(self, **kargs):
        """ Performs database maintenance to increase performance at large sizes """
        if self.locked(ignore=kargs.get('ignore_lock',False)): return msg(-4, _('DB locked!'))

        fdx.db_lock = False
        msg(_('Starting DB miantenance'))

        msg(_('Performing VACUUM'))
        self.qr_sql('VACUUM', one=True, ignore_errors=False)
        msg(_('Performing ANALYZE'))
        self.qr_sql('ANALYZE', one=True, ignore_errors=False)
        msg(_('REINDEXING all tables'))
        self.qr_sql('REINDEX', one=True, ignore_errors=False)

        msg(_('Updating document statistics'))
        doc_count = slist(self.qr_sql(DOC_COUNT_SQL, one=True, ignore_errors=False),0, 0)
        doc_count = scast(doc_count, int, 0)

        self.qr_sql("insert into params values('doc_count', :doc_count)", {'doc_count':doc_count}, one=True, ignore_errors=False)
        self.qr_sql("""insert into actions values('maintenance',:doc_count)""", {'doc_count':doc_count}, one=True, ignore_errors=False)
        
        if self.status == 0:
            self.conn.commit()
            msg(_('DB maintenance completed'), log=True)
        else: msg(FX_ERROR_DB, _('DB maintenance failed!'), log=True)

        self.unlock(ignore=kargs.get('ignore_lock',False))



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
        (("delete from params where name = 'doc_count'", () ),\
        ("insert into params values('doc_count', :doc_count)", {'doc_count':doc_count} )) \
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
        doc_count = scast(doc_count[0], int, 1)
        fdx.doc_count = doc_count
        return doc_count



    def get_last_docid(self, **kargs):
        """ Get last document ID from SQL database """
        doc_id = scast( self.qr_sql("select max(id) from entries", one=True)[0], int, 0)
        if self.status != 0: return -1
        return doc_id



    def get_last(self, **kargs):
        """ Get timestamp of last news check """
        ord = scast(kargs.get('ord'), int, 1) - 1
        if fdx.fetches_cache is None:
            fdx.fetches_cache = self.qr_sql("select time, datetime(time,'unixepoch', 'localtime') from actions where name = 'fetch' order by time DESC limit :limit", {'limit':MAX_LAST_UPDATES}, all=True)
            if self.status != 0: return -1

        if ord < 0: return -1
        row = slist(fdx.fetches_cache, ord, None)
        if row is None: return 0
        fetch = slist(row, 0, None)
        if row is None: return -1
        return scast(fetch, int, -1)



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
        stat_dict['rule_count'] = slist(self.qr_sql("select count(id) from rules where learned = 1", one=True, ignore_errors=False), 0, 0)
        stat_dict['user_rule_count'] = slist(self.qr_sql("select count(id) from rules where learned <> 1", one=True, ignore_errors=False), 0, 0)

        stat_dict['feed_count'] = slist(self.qr_sql("select count(id) from feeds where coalesce(is_category,0) = 0 and coalesce(deleted,0) = 0", one=True, ignore_errors=False), 0, 0)
        stat_dict['cat_count'] = slist(self.qr_sql("select count(id) from feeds  where coalesce(is_category,0) = 1 and coalesce(deleted,0) = 0", one=True, ignore_errors=False), 0, 0)

        stat_dict['lock'] = self.locked(just_check=True)
        stat_dict['fetch_lock'] = self.locked_fetching(just_check=True)

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
        """ Wraper for inserting entries from list of dicts or a file """
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
                    with open(efile, "r") as f: contents = f.read()
                except OSError as e: return msg(FX_ERROR_IO, f'{_("Error reading file")} {efile}: %a', e)

            try: elist = json.loads(contents)
            except (json.JSONDecodeError) as e: return msg(FX_ERROR_IO, _('Error parsing JSON: %a'), e)

        # Validate data received from json
        if not isinstance(elist, (list, tuple)):  return msg(FX_ERROR_IO, _('Invalid input: must be a list of dicts!'))

        
        entry = FeedexEntry(self)
        elist_len = len(elist)
        num_added = 0

        if self.locked_fetching(ignore=kargs.get('ignore_lock', False)): return msg(FX_ERROR_LOCK,_('Database locked for fetching'))

        # Queue processing
        for i,e in enumerate(elist):

            if not isinstance(e, dict):
                msg(FX_ERROR_VAL, _('Input entry no. %a is not a dictionary!'), i)
                continue

            entry.clear()
            entry.strict_merge(e)
            entry.learn = learn
            
            err = entry.add(new=e, update_stats=False, counter=i)
            if err == 0: num_added += 1

        # stat
        if num_added > 0:
            self.update_stats()
            if not fdx.single_run: self.load_rules()

        if num_added > 1: msg(_('Added %a new entries'), num_added, log=True)
        
        self.unlock_fetching()
        return 0







    def import_feeds(self, ifile, **kargs):
        """ Import feeds from JSON file """
        feed_data = load_json(ifile, -1)
        if feed_data == -1: return -1

        self.cache_feeds()
        max_id = max(map(lambda x: x[0], fdx.feeds_cache))

        if type(feed_data) not in (list, tuple): return msg(FX_ERROR_VAL, _('Invalid input format. Should be list of dictionaries!'))

        feed = SQLContainer('feeds', FEEDS_SQL_TABLE)
        insert_sql = []
        for f in feed_data:
            if type(f) is not dict: return msg(FX_ERROR_VAL, _('Invalid input format. Should be list of dictionaries!'))
            feed.clear()
            feed.merge(f)
            feed['id'] += max_id
            if feed['parent_id'] is not None: feed['parent_id'] += max_id
            insert_sql.append(feed.vals.copy())

        if len(insert_sql) > 0:
            msg(_('Saving feeds to database...'))
            err = self.run_sql_lock(feed.insert_sql(all=True), insert_sql, many=True)
            if err == 0:
                if not fdx.single_run: err = self.load_feeds()
            if err == 0: return msg(_('Feeds imported successfully!'))
        
        return 0




    def import_rules(self, ifile, **kargs):
        """ Import rules from JSON """
        rule_data = load_json(ifile, -1)
        if rule_data == -1: return -1

        if type(rule_data) not in (list, tuple): return msg(FX_ERROR_VAL, _('Invalid input format. Should be list of dictionaries!'))

        rule = SQLContainer('rules', RULES_SQL_TABLE)
        insert_sql = []
        for r in rule_data:
            if type(r) is not dict: return msg(FX_ERROR_VAL, _('Invalid input format. Should be list of dictionaries!'))
            rule.clear()
            rule.merge(r)
            rule['id'] = None
            insert_sql.append(rule.vals.copy())

        if len(insert_sql) > 0:
            msg(_('Saving rules to database...'))
            err = self.run_sql_lock(rule.insert_sql(all=True), insert_sql, many=True)
            if err == 0:
                if not fdx.single_run: err = self.load_rules()
            if err == 0: return msg(_('Rules imported successfully!'))
        
        return 0




    def import_flags(self, ifile, **kargs):
        """ Import rules from JSON """
        flag_data = load_json(ifile, -1)
        if flag_data == -1: return -1

        if type(flag_data) not in (list, tuple): return msg(FX_ERROR_VAL, _('Invalid input format. Should be list of dictionaries!'))

        flag = SQLContainer('flags', FLAGS_SQL_TABLE)
        insert_sql = []
        for f in flag_data:
            if type(f) is not dict: return msg(FX_ERROR_VAL, _('Invalid input format. Should be list of dictionaries!'))
            flag.clear()
            flag.merge(f)
            insert_sql.append(flag.vals.copy())

        if len(insert_sql) > 0:
            msg(_('Saving flags to database...'))
            err = self.run_sql_lock(flag.insert_sql(all=True), insert_sql, many=True)
            if err == 0:
                if not fdx.single_run: err = self.load_flags()
            if err == 0: return msg(_('Flags imported successfully!'))
        
        return 0













    def fetch(self, **kargs):
        """ Check for news taking into account specified intervals and defaults as well as ETags and Modified tags"""
        if self.locked_fetching(ignore=kargs.get('ignore_lock', False)): return msg(FX_ERROR_LOCK,_('Database locked for fetching'))

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
            if self.feed['is_category'] not in (0,None) or self.feed['handler'] in ('local'): continue

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
                    msg(FX_ERROR_DB, f'{_("Feed")} {self.feed.name()} {_("ignored due to DB error")}: %a', self.db_error, log=True)
                    continue


                handler.set_feed(self.feed)
                for item in handler.fetch(self.feed, force=force, pguids=pguids, plinks=plinks, last_read=last_read, last_checked=last_checked):
                    
                    if isinstance(item, FeedexEntry):
                        self.new_items += 1
                        err = item.validate_types()
                        if err != 0: 
                            msg(FX_ERROR_VAL, f'{_("Error while processing entry")} {self.new_items}: {_("Invalid data type for")} %a', err)
                            continue
                        
                        if not skip_ling:
                            item.set_feed(feed=feed)
                            err = item.ling(index=True, stats=True, rank=True, learn=False, counter=tech_counter)
                            if err != 0:
                                self.DB.close_ixer(rollback=True) 
                                return msg(FX_ERROR_LP, _('Error while linguistic processing %a!'), item)
                            
                            vals = item.vals.copy()
                            entries_sql.append(vals)
                        else:
                            entries_sql.append(item.vals.copy())

                        # Track new entries and take care of massive insets by dividing them into parts
                        tech_counter += 1
                        if tech_counter >= self.config.get('max_items_per_transaction', 2000):
                            msg(_('Saving new items ...'))
                            err = self.run_sql_lock(self.entry.insert_sql(all=True), entries_sql, many=True)
                            if err == 0: err = self.run_sql_lock("""update feeds set lastread = :now, lastchecked = :now, etag = :etag, modified = :modified, http_status = :status, error = 0  where id = :id""", feeds_sql, many=True)
                            if err == 0:
                                feeds_sql = []
                                entries_sql = []
                                msg(_('Indexing new items ...'))
                                self.close_ixer()                 
                            else:
                                self.close_ixer(rollback=True)
                                self.unlock_fetching()
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
            if handler.redirected: msg(f'{_("Channel redirected")} (%a)', self.feed['url'], log=True)

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

                handler.update(self.feed, ignore_images=self.config.get('ignore_images',False))
                if not handler.error:

                    updated_feed = handler.feed

                    if updated_feed == -1:
                        msg(FX_ERROR_HANDLER, _('Error updating metadata for feed %a'), self.feed.name(id=True))
                        continue
                    elif updated_feed == 0:
                        continue
                    
                    err = updated_feed.validate_types()
                    if err != 0: msg(FX_ERROR_VAL, _('Invalid data type for %a'), err)
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
                err = self.run_sql_lock(self.entry.insert_sql(all=True), entries_sql, many=True)
                if err == 0: err =  self.run_sql_lock("""update feeds set lastread = :now, lastchecked = :now, etag = :etag, modified = :modified, http_status = :status, error = 0  where id = :id""", feeds_sql, many=True)
                if err == 0: 
                    msg(_('Indexing new items ...'))
                    self.close_ixer()
                else:
                    self.close_ixer(rollback=True)
                    self.unlock_fetching()
                    return msg(FX_ERROR_DB,_('Fetching aborted! DB error: %a'), err)



        # ... finally, do maintenance ....
        if meta_updated and not fdx.single_run: self.load_feeds()

        if self.new_items > 0:
            err = self.run_sql_lock("""insert into actions values('fetch', :started)""", {'started':started} )
            if err != 0: return err
            else: 
                if fdx.fetches_cache is None: self.get_last()
                fdx.fetches_cache.insert(0, (started, started_str) )

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
        

        if not update_only: msg(f"""{_('Finished fetching (%a new articles), duration: ')}{duration}""", self.new_items)
        else: msg(f"""{_('Finished updating metadata, duration: ')}{duration}""")

        self.unlock_fetching()

        del self.__dict__['feed']
        del self.__dict__['entry']
        
        return 0







    def recalculate(self, **kargs):
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
        rule = FeedexRule(self)

        entry_q = []
        rules_q = []
        rules_ids_q = []

        vals = {}
        vs = {}

        if entry_id in (0, None):
            many = True
            msg(_("Mass recalculation started..."), log=True)
            if rank: msg(_("Ranking according to saved rules..."), log=True)
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
            
            if self.locked_fetching(ignore=kargs.get('ignore_lock', False)): return msg(-2,_('Database busy fetching'))

            for i,e in enumerate(entries):

                entry.populate(e)
    
                if many and learn and coalesce(entry['read'],0) == 0: continue
                msg(_(f"Processing entry %a ({entry['read']})..."), entry['id'])

                err = entry.ling(learn=learn, index=index, rank=rank, save_rules=False, multi=True, counter=i, rebuilding=True)
                if err != 0: 
                    self.DB.close_ixer(rollback=True) 
                    return msg(FX_ERROR_LP, _('Error while linguistic processing %a!'), item)

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
                msg(_('Committing batch ...'))
                err = self.run_sql_lock(entry.update_sql(filter=vals.keys(), wheres='id = :id'), entry_q, many=True)
                if err != 0: 
                    self.DB.close_ixer(rollback=True) 
                    return err

            if learn:
                msg(_('Learning rule batch ...'))
                if len(rules_ids_q) > 0:
                    err = self.run_sql_lock('delete from rules where context_id = :id', rules_ids_q, many=True)
                if len(rules_q) > 0:
                    if err == 0: err = self.run_sql_lock(rule.insert_sql(all=True), rules_q, many=True)
                    if err != 0: return err

            if index: self.close_ixer()                    

            entry_q.clear()
            rules_q.clear()
            rules_ids_q.clear()

            msg(_('Batch committed'), log=True)


        msg(_('Recalculation finished!'), log=True)

        self.update_stats()
        if learn: 
            if not fdx.single_run: self.load_rules()

        self.unlock_fetching()
        return 0










#################################################
# Utilities 

    def clear_history(self, **kargs):
        """ Clears search history """
        err = self.run_sql_lock("delete from search_history",())
        if err != 0: return err
        else: items_deleted = self.rowcount
        if not fdx.single_run: self.load_history()
        return msg(_('Deleted %a items from search history'), items_deleted)
        
        
    def delete_learned_rules(self, **kargs):
        """ Deletes all learned rules """
        err = self.run_sql_lock("""delete from rules where learned = 1""",[])
        if err != 0: return err
        else:
            deleted_rules = self.rowcount
            if not fdx.single_run: self.load_rules()
            return msg(_('Deleted %a learned rules'), deleted_rules)



    def empty_trash(self, **kargs):
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
            if self.status != 0: return self.status
            for f in feeds_to_remove:
                if fdx.icons_cache is None: self.load_icons()
                icon = fdx.icons_cache.get(f)
                if icon is not None and icon.startswith( os.path.join(self.icon_path, 'feed_') ) and os.path.isfile(icon): os.remove(icon)
        else: return err

        err = self.run_sql_lock(EMPTY_TRASH_FEEDS_SQL2,[])
        feeds_deleted = self.rowcount
        if err != 0: return err
 
        if not fdx.single_run: self.load_all()
        return msg(_('Trash emptied: %a'), f'{feeds_deleted} {_("channels/categories")}, {entries_deleted} {_("entries")}, {rules_deleted} {_("rules removed")}', log=True) 





