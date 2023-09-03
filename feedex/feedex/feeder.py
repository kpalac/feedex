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
        self.in_pipe = kargs.get('in_pipe')
        self.session_id = kargs.get('session_id')
        self.locks = ()

class FeedexIndexError(FeedexError):
    def __init__(self, *args, **kargs): 
        kargs['code'] = kargs.get('code', FX_ERROR_INDEX)
        super().__init__(*args, **kargs)

class FeedexPipeError(FeedexError):
    def __init__(self, *args, **kargs):
        kargs['code'] = kargs.get('code', FX_ERROR_IO)
        super().__init__(*args, **kargs)




class FeedexDatabase:
    """ Database interface for Feedex with additional maintenance and utilities """
    
    def __init__(self, **kargs):
        
        # Path to database
        self.db_path = os.path.abspath(kargs.get('db_path', fdx.config.get('db_path')))

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

        self.timeout = fdx.config.get('timeout', 120) # Wait time if DB is locked
        

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
            err = self.save_param('version', FEEDEX_VERSION)
            if err != 0:
                self.close(unlock=False)
                raise FeedexDatabaseError('Error setting DB version: %a', e)


        if self.main_conn: 
            if not create_sqlite:
            # Checking versions and aborting if needed
                version = self.get_saved_param('version')
                if self.status != 0:
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
                    return err

                elif kargs.get('lock', False):
                    err = self.lock()
                    if err == 0:
                        msg(_('Database locked'))
                        self.close(unlock=False)
                    return err

                else:
                    lock = self.locked() 
                    if lock is True:
                        in_pipe, session_id = self.get_saved_param('in_pipe'), self.get_saved_param('session_id')
                        self.close(unlock=False)
                        raise FeedexDatabaseLockedError('DB locked', in_pipe=in_pipe, session_id=session_id, locks=fdx.get_locks()) # Pass in pipe id for other processes
                    elif lock is None:
                        self.close(unlock=False)
                        raise FeedexDatabaseError('Unknown lock status!')

                self.lock()

            if not fdx.single_run: self.lock()

            debug(2, f'Connected to {self.sql_path} ({self.conn_id})')


        # Connecting XAPIAN index
        try:
            self.ix = xapian.Database(self.ix_path)
            debug(2,f"Connected to index {self.ix_path}  ({self.conn_id})")        
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
                    debug(2,f'Connected to index {self.ix_path} ({self.conn_id})')
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
                msg(_('Writing to index...'))
                try: self.ixer_db.commit_transaction()
                except (xapian.Error,) as e:
                    self.ixer_db.cancel_transaction()
                    self.ixer_db.close()
                    return msg(FX_ERROR_INDEX, _('Indexer error: %a'), e)                 
            if rollback:
                msg(_('Reverting index changes...'))
                self.ixer_db.cancel_transaction()
            
            self.ixer_db.close()

        self.ixer_db = None
        return 0





    ########################################################################
    #   
    #       Local pipe management

    def create_pipe(self, **kargs):
        """ Defines pipe's filesystem name
            type:
                0 - in
                1 - out
        """
        dir = kargs.get('type',0)

        if dir == 0 and fdx.in_pipe is not None: return 0
        elif dir == 1 and fdx.out_pipe is not None: return 0

        debug(2, f'Creating communication pipe type {dir}...')

        exists = True
        while exists:
            ts = datetime.now()
            pipe = os.path.join(self.db_path, f"""{int(round(ts.timestamp()))}{random_str(length=25)}.tmp""")
            if not os.path.exists(pipe):
                exists = False
                try:
                    os.mkfifo(pipe, 0o660)
                    if dir == 0: fdx.in_pipe = pipe 
                    elif dir == 1: fdx.out_pipe = pipe
                    debug(2, f'Pipe {pipe} created')
                except (OSError, IOError) as e: 
                    self.status = FX_ERROR_IO
                    self.error = e
                    raise FeedexPipeError('Could not create pipe type %a at %b: %c', dir, pipe, e)

        err = 0
        if dir == 0: err = self.save_param('in_pipe', fdx.in_pipe)
        elif dir == 1: err = self.save_param('out_pipe', fdx.out_pipe)
        return err




    def destroy_pipe(self, **kargs):
        """ Deletes named pipes
            type:
                0 - in
                1 - out

        """ 
        dir = kargs.get('type',0)       

        if dir == 0 and fdx.in_pipe is None: return 0
        elif dir == 1 and fdx.out_pipe is None: return 0

        try:
            if dir == 0: os.remove(fdx.in_pipe)
            elif dir == 1: os.remove(fdx.out_pipe)
        except (OSError, IOError,) as e:
            self.status = FX_ERROR_IO
            self.error = e
            raise FeedexPipeError('Could not destroy pipe type %a: %b', dir, e)

        err = 0
        if dir == 0: err = self.clear_param('in_pipe', 'session_id')
        elif dir == 1: err = self.clear_param('out_pipe', 'session_id')
        return err



    def set_session_id(self, **kargs):
        """ Set and save session ID 
            type: 0 - GUI """
        err = 0
        tp = kargs.get('type',0)
        session_id = fdx.get_session_id(type=tp)
        if session_id is not None: err = self.save_param('session_id', session_id)
        return err



    ################################################3
    #
    #           Parameter interface

    def get_saved_param(self, name, **kargs):
        """ Get parameter from DB 
            type - type to cast results to 
            default - default value if nothing is retrieved """
        tp = kargs.get('type',str)
        default = kargs.get('default')
        param = scast( slist(self.qr_sql(f"select val from params where name = :name", {'name':name}, one=True), 0, None), tp, default)
        if param == '': param = None
        return param

    def save_param(self, name, val, **kargs):
        err = self.run_sql_multi_lock(
            ("delete from params where name = :name", {'name':name}),\
            ("insert into params values(:name, :val)", {'name':name, 'val':val}),
            )
        return err

    def clear_param(self, *names, **kargs):
        qrs = []
        for n in names: qrs.append( ('delete from params where name = :name', {'name':n}) )
        return self.run_sql_multi_lock(*qrs)





    ########################################################################
    #   Locks, Fetching Locks, timeouts
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





    def run_locked(self, locks, func, *args, **kargs):
        """ Wrapper to run functions within fetching lock """
        if locks == FX_LOCK_ALL: locks = {FX_LOCK_FETCH, FX_LOCK_ENTRY, FX_LOCK_FEED, FX_LOCK_RULE, FX_LOCK_FLAG,}
        elif type(locks) is not set: locks = {locks,}

        if FX_LOCK_FETCH in locks:
            if fdx.db_fetch_lock: return msg(FX_ERROR_LOCK, _('DB locked for fetching!'))
            fdx.db_fetch_lock = True
        if FX_LOCK_ENTRY in locks:
            if fdx.db_entry_lock: return msg(FX_ERROR_LOCK, _('Entry edit locked!'))
            fdx.db_entry_lock = True
        if FX_LOCK_FEED in locks:
            if fdx.db_feed_lock: return msg(FX_ERROR_LOCK, _('Feed edit locked!'))
            fdx.db_feed_lock = True
        if FX_LOCK_RULE in locks:
            if fdx.db_rule_lock: return msg(FX_ERROR_LOCK, _('Rule edit locked!'))
            fdx.db_rule_lock = True
        if FX_LOCK_FLAG in locks:
            if fdx.db_flag_lock: return msg(FX_ERROR_LOCK, _('Flag edit locked!'))
            fdx.db_flag_lock = True

        ret = func(*args, **kargs)

        if FX_LOCK_FETCH in locks: fdx.db_fetch_lock = False
        if FX_LOCK_ENTRY in locks: fdx.db_entry_lock = False
        if FX_LOCK_FEED in locks: fdx.db_feed_lock = False
        if FX_LOCK_RULE in locks: fdx.db_rule_lock = False
        if FX_LOCK_FLAG in locks: fdx.db_flag_lock = False

        return ret



    def loc_locked(self, **kargs):
        """ Wait for local unlock """
        timeout = kargs.get('timeout', fdx.config.get('timeout',30))
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
        if isiter(vals): many = 1
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



    def qr_sql_iter(self, sql:str, *args, **kargs):
        """ Query database - iterator """
        if self.loc_locked(**kargs):
            self.status = msg(FX_ERROR_LOCK, _('DB locked locally (%a) (sql: %b)'), self.conn_id, sql, log=True)
            return self.status
        try:
            for i in self.conn.execute(sql, *args).fetchall(): yield i
        except (sqlite3.Error, sqlite3.OperationalError) as e:            
            self.error = f'{e}'
            self.status = msg(FX_ERROR_DB, _('DB error (%a) - read: %b (%c)'), self.conn_id, e, sql,  log=True)
            self.conn.rollback()
            return self.status
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

    def connect_DN(self, **kargs):
        """ Lazily connect desktop notifier to ain bus """
        if fdx.DN is None:
            from feedex_desktop_notifier import DesktopNotifier
            self.cache_icons()
            fdx.DN = DesktopNotifier(icons=fdx.icons_cache)




    def load_feeds(self, **kargs):
        """ Load feed data from database into cache """        
        debug(2, f'Loading feeds ({self.conn_id})...')
        fdx.feeds_cache = self.qr_sql('select * from feeds order by display_order asc', all=True)
        if self.status != 0: raise FeedexDataError('Error caching feeds: %a', self.error)
        return 0

    def load_rules(self, **kargs):
        """Load learned and saved rules from DB into cache"""
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
        self.cache_feeds()
        
        max_freq = 0
        feed_freq = {}
        for f in fdx.feeds_cache:
            freq = coalesce(f[FEEDS_SQL_TABLE.index('recom_weight')], 0)
            if freq < 0: freq = 0
            if freq > max_freq: max_freq = freq
            feed_freq[f[FEEDS_SQL_TABLE.index('id')]] = freq

        if max_freq > 0:
            for k,v in feed_freq.items(): feed_freq[k] = 1 - ((max_freq - v)/max_freq)
        
        fdx.feed_freq_cache = feed_freq
        #for k,v in feed_freq.items(): print(f'{k}: {v}')
        return 0


    def load_terms(self, **kargs):
        """ Load learned terms for recommendations """
        self.load_feed_freq()
        if not fdx.config.get('use_keyword_learning', True):
            fdx.terms_cache = ()
            fdx.recom_qr_str = ''
            return 0

        debug(2, f'Loading learned terms ({self.conn_id})...')
        if fdx.config.get('recom_algo') == 2: fdx.terms_cache = self.qr_sql(LOAD_TERMS_ALGO_2_SQL, all=True)
        elif fdx.config.get('recom_algo') == 3: fdx.terms_cache = self.qr_sql(LOAD_TERMS_ALGO_3_SQL, all=True)
        else: fdx.terms_cache = self.qr_sql(LOAD_TERMS_ALGO_1_SQL, all=True)
        if self.status != 0: raise FeedexDataError('Error caching learned terms: %a', self.error)

        # Build query string for recommendations (better do it once at the beginning)        
        limit = scast(fdx.config.get('recom_limit', 250), int, 250)

        qr_str = ''        
        for i,t in enumerate(fdx.terms_cache):
            s = t[0]
            if i > limit: break
            s = s.strip()
            if s in {'','~','(',')',}: continue
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
                    elif handler == 'local': fdx.icons_cache[id] = os.path.join(FEEDEX_SYS_ICON_PATH, 'disk.svg')
                
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
        debug(2, f'All data reloaded ({self.conn_id})...')
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

        debug(2, f'Housekeeping: {now}')
        for root, dirs, files in os.walk(self.cache_path):
            for name in files:
                filename = os.path.join(root, name)
                if xdays == -1 or os.stat(filename).st_mtime < now - (xdays * 86400) or name.endswith('.txt'):
                    try: os.remove(filename)
                    except OSError as e:
                        err = True
                        msg(FX_ERROR_IO, f'{_("Error removing %a:")} {e}', filename)
                    debug(2, f'Removed : {filename}')
                if err: break
            if err: break

        if not err:
            if xdays == -1: msg(_('Cache cleared successfully...'))

      


    def maintenance(self, **kargs): return self.run_locked(FX_LOCK_ALL, self._maintenance, **kargs)
    def _maintenance(self, **kargs):
        """ Performs database maintenance to increase performance at large sizes """
        msg(_('Starting DB miantenance'), log=True)

        msg(_('Performing VACUUM'))
        err = self.run_sql_lock('VACUUM')
        if err == 0:
            msg(_('Performing ANALYZE'))
            err = self.run_sql_lock('ANALYZE')
        if err == 0:
            msg(_('REINDEXING all tables'))
            err = self.run_sql_lock('REINDEX')

        if err == 0:
            err = self._update_doc_count()
            doc_count = self.get_doc_count()

            msg(_('Updating feed recomm. weights...'))            
            err = self.run_sql_lock("""update feeds set recom_weight = 0""")
            stats_delta = {}
            if err == 0:
                feed_weight_list = self.qr_sql(FEED_FREQ_MAINT_SQL, all=True)
                for w in feed_weight_list: stats_delta[w[0]] = w[1]
                err = self.update_stats(stats_delta, ignore_lock=True)

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


    def update_stats(self, idict:dict, **kargs):
        """ Get DB statistics and save them to params table for quick retrieval"""

        debug(2, "Updating DB statistics...")

        err = 0
        dc_delta = scast(idict.get('dc'), int, 0)
        if dc_delta != 0:
            doc_count = self.get_doc_count() + dc_delta
            err = self.save_param('doc_count', doc_count)            
        if err != 0: return err

        do_reload = False
        for k,v in idict.items():
            if type(k) is not int: continue
            delta = scast(v, int, 0)
            if delta != 0:
                if fdx.feeds_cache is None: self.load_feeds(**kargs)
                for i,f in enumerate(fdx.feeds_cache):
                    if f[FEEDS_SQL_TABLE.index('id')] == k and f[FEEDS_SQL_TABLE.index('is_category')] != 1:
                        do_reload = True
                        err = self.run_sql_lock('update feeds set recom_weight = coalesce(recom_weight,0) + :delta where id = :id', {'delta':delta, 'id':k})


        if not fdx.single_run and do_reload and err == 0: 
            self.load_feeds(**kargs)
            self.load_terms(**kargs)

        return err


        

    def _update_doc_count(self, **kargs):
        """ Calculate doc count and cache it in params table """
        msg(_('Calculating document count...'))
        doc_count = scast( slist(self.qr_sql(DOC_COUNT_MAINT_SQL, one=True),0, 0), int, 0)
        if self.status != 0: return FX_ERROR
        err = self.save_param('doc_count', doc_count)
        return err
        


    def get_doc_count(self, **kargs):
        """ Retrieve entry count from params"""
        if fdx.doc_count is not None: return fdx.doc_count
        
        doc_count = self.get_saved_param('doc_count', type=int)
        if doc_count is None:
            err = self._update_doc_count()
            if err == 0: doc_count = self.get_saved_param('doc_count', type=int)
            else: return 1
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

        stat_cont = FeedexDBStats()
        stat_cont['db_path'] = self.db_path

        stat_cont['version'] = self.get_saved_param('version', default='<???>')
        
        stat_cont['db_size_raw'] = os.path.getsize(os.path.join(self.db_path,'main.db'))
        stat_cont['ix_size_raw'] = get_dir_size(self.ix_path)
        stat_cont['cache_size_raw'] = get_dir_size(self.cache_path)
        stat_cont['total_size_raw'] = stat_cont['db_size_raw'] + stat_cont['ix_size_raw'] + stat_cont['cache_size_raw']

        stat_cont['db_size'] = sanitize_file_size(stat_cont['db_size_raw'])
        stat_cont['ix_size'] = sanitize_file_size(stat_cont['ix_size_raw'])
        stat_cont['cache_size'] = sanitize_file_size(stat_cont['cache_size_raw'])
        stat_cont['total_size'] = sanitize_file_size(stat_cont['total_size_raw'])

        stat_cont['doc_count'] = self.get_doc_count()
        stat_cont['last_doc_id'] = self.get_last_docid()
        stat_cont['last_update'] = slist(self.qr_sql("select max(time) from actions where name = 'fetch'", one=True, ignore_errors=False), 0, '<???>')
        stat_cont['first_update'] = slist(self.qr_sql("select min(time) from actions where name = 'fetch'", one=True, ignore_errors=False), 0, '<???>')
        stat_cont['rule_count'] = slist(self.qr_sql("select count(id) from rules", one=True, ignore_errors=False), 0, 0)
        stat_cont['learned_kw_count'] = slist(self.qr_sql("select count(id) from terms", one=True, ignore_errors=False), 0, 0)

        stat_cont['feed_count'] = slist(self.qr_sql("select count(id) from feeds where coalesce(is_category,0) = 0 and coalesce(deleted,0) = 0", one=True, ignore_errors=False), 0, 0)
        stat_cont['cat_count'] = slist(self.qr_sql("select count(id) from feeds  where coalesce(is_category,0) = 1 and coalesce(deleted,0) = 0", one=True, ignore_errors=False), 0, 0)

        stat_cont['fetch_lock'] = fdx.db_fetch_lock

        stat_cont['last_update'] = scast(stat_cont['last_update'], int, None)
        if stat_cont['last_update'] is not None: stat_cont['last_update'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat_cont['last_update']))

        stat_cont['first_update'] = scast(stat_cont['first_update'], int, None)
        if stat_cont['first_update'] is not None: stat_cont['first_update'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat_cont['first_update']))

        if self.check_due_maintenance(): stat_cont['due_maintenance'] = True
        else: stat_cont['due_maintenance'] = False
            
        return stat_cont








    #####################################################################################################
    # Mass Inesrts/Edits and Fetching





    def import_entries(self, **kargs):
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
        if not isinstance(elist, (list, tuple)):  return msg(FX_ERROR_IO, _('Invalid input: must be a list of dicts...'))
        
        if pipe: msg(_('Importing entries ...'))
        else: msg(_('Importing entries from %a...'), efile)

        entry = FeedexEntry(self)
        err = entry.add_many(elist)
        return err






    def import_feeds(self, ifile, **kargs):
        """ Import feeds from JSON file """

        feed_data = load_json(ifile, -1)
        if feed_data == -1: return -1

        self.cache_feeds()

        if not isiter(feed_data): return msg(FX_ERROR_VAL, _('Invalid input format. Should be list of dictionaries'))

        feed = FeedexFeed(self)
        msg(_('Importing feeds/categories from %a...'), ifile)
        err = feed.add_many(feed_data)
        return err
    




    def import_rules(self, ifile, **kargs):
        """ Import rules from JSON """
        rule_data = load_json(ifile, -1)
        if rule_data == -1: return -1

        if not isiter(rule_data): return msg(FX_ERROR_VAL, _('Invalid input format. Should be list of dictionaries...'))

        rule = FeedexRule(self)
        msg(_('Importing rules from %a...'), ifile)
        err = rule.add_many(rule_data)
        return err



    def import_flags(self, ifile, **kargs):
        """ Import flags from JSON """
        
        flag_data = load_json(ifile, -1)
        if flag_data == -1: return FX_ERROR_IO

        if not isiter(flag_data): return msg(FX_ERROR_VAL, _('Invalid input format. Should be list of dictionaries...'))

        flag = FeedexFlag(self)
        msg(_('Importing flags from %a...'), ifile)
        err = flag.add_many(flag_data)
        return err












    def fetch(self, **kargs): return self.run_locked(FX_LOCK_FETCH, self._fetch, **kargs) 
    def _fetch(self, **kargs):
        """ Check for news taking into account specified intervals and defaults as well as ETags and Modified tags"""
        self.cache_feeds()
        self.cache_rules()
        self.cache_flags()

        feed_ids = scast(kargs.get('ids'), tuple, None)
        feed_id = scast(kargs.get('id'), int, 0)

        force = kargs.get('force', False)
        ignore_interval = kargs.get('ignore_interval', True)

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
        
        feed = FeedexFeed(self, exists=True)
        entry = FeedexEntry(self, exists=True)

        self.cache_feeds()

        for f in fdx.feeds_cache.copy():

            feed.populate(f)

            # Check for processing conditions...
            if feed['deleted'] == 1 and not update_only and feed_id == 0: continue
            if feed['fetch'] in {None,0} and feed_id == 0 and feed_ids is None: continue
            if feed_id != 0 and feed_id != feed['id']: continue
            if feed_ids is not None and feed['id'] not in feed_ids: continue
            if feed['is_category'] not in {0,None} or feed['handler'] in {'local',}: continue

            # Ignore unhealthy feeds...
            if scast(feed['error'],int,0) >= fdx.config.get('error_threshold',5) and not kargs.get('ignore_errors',False):
                msg(_('Feed %a ignored due to previous errors'), feed.name(id=True))
                continue

            #Check if time difference exceeds the interval
            last_checked = scast(feed['lastchecked'], int, 0)
            if not ignore_interval:
                diff = (started - last_checked)/60
                if diff < scast(feed['interval'], int, fdx.config.get('default_interval',45)):
                    debug(2, f'Feed {feed["id"]} ignored (interval: {feed["interval"]}, diff: {diff})')
                    continue

            msg(_('Processing %a ...'), feed.name())

            now = datetime.now()
            now_raw = int(now.timestamp())
            last_read = scast(feed['lastread'], int, 0)
            
            
            # Choose/lazy-load appropriate handler           
            if feed['handler'] == 'rss':
                if rss_handler is None: rss_handler = FeedexRSSHandler(self)
                handler = rss_handler
            elif feed['handler'] == 'html':
                if html_handler is None: html_handler = FeedexHTMLHandler(self)
                handler = html_handler
            elif feed['handler'] == 'script':
                if script_handler is None: script_handler = FeedexScriptHandler(self)
                handler = script_handler
            elif feed['handler'] == 'local':
                msg(_('Channel handled locally... Ignoring...'))
                continue
            else:
                msg(FX_ERROR_HANDLER, _('Handler %a not recognized!'), feed['handler'])
                continue     

            # Set up feed-specific user agent
            agent = scast(feed['user_agent'], str, '').strip() 
            if agent != '':
                msg(_('Using custom User Agent: %a'), feed['user_agent'])
                handler.set_agent(agent)
            else: handler.set_agent(None)

            # Start fetching ...
            if not update_only:

                pguids = self.qr_sql("""select distinct guid from entries e where e.feed_id = :feed_id""", {'feed_id':feed['id']} , all=True)
                if handler.compare_links: plinks = self.qr_sql("""select distinct link from entries e where e.feed_id = :feed_id""", {'feed_id':feed['id']} , all=True, ignore_errors=False)
                else: plinks = ()
                
                if self.status != 0:
                    msg(FX_ERROR_DB, _('Feed %a ignored due to DB error: %b'), feed.name(), self.error, log=True)
                    continue


                handler.set_feed(feed)
                for item in handler.fetch(force=force, pguids=pguids, plinks=plinks, last_read=last_read, last_checked=last_checked):
                    
                    if isinstance(item, dict):
                        tech_counter += 1
                        item['note'], item['read'], item['deleted'], item['importance'], item['flag'] = 0, 0, 0, None, None
                        err = entry.add(item, counter=tech_counter, no_commit=True)
                        if err == 0: self.new_items += 1
                        else: return msg(err, _('Fetching aborted due to errors...'))

                        # Commit if batch size is reached
                        if tech_counter >= fdx.config.get('max_items_per_transaction', 2000):                      
                            err = entry.commit()
                            if err == 0: err = feed.commit()
                            if err != 0: return msg(err, _('Fetching aborted due to errors...'))
                            tech_counter = 0

                    else: 
                        msg(FX_ERROR_VAL, _('Invalid entry format (%a)!'), type(item))
                        continue

            else:
                # This bit is if no fetching is done (just meta update)
                handler.set_feed(feed)
                handler.download(force=force)

            #print(handler.feed_delta)
            feed.update_meta_headers(handler.feed_delta, no_commit=True)     

            # Autoupdate metadata if needed or specified by 'forced' or 'update_only'
            if (scast(feed['autoupdate'], int, 0) == 1 or update_only) and not handler.no_updates and not handler.error:
                msg(_('Updating metadata for %a'), feed.name())
                handler.update_meta()
                feed.update_meta(handler.feed_meta_delta, no_commit=True)



            # Stop if this was the specified feed (i.e. there was a feed specified and a loop was executed)...
            if feed_id != 0: break


        # Push final entries to DB (the same as when tech_counter hit before)           
        if not update_only:
            err = entry.commit()
            if err == 0: err = feed.commit()
            if err != 0: return msg(err, _('Fetching aborted due to errors...'))
        else:
            err = feed.commit()
            if err != 0: return msg(err, _('Operation aborted due to errors...'))


        # ... finally, do maintenance ....
        if meta_updated and not fdx.single_run: self.load_feeds(ignore_lock=True)

        if self.new_items > 0:
            err = self.run_sql_lock("""insert into actions values('fetch', :started)""", {'started':started} )
            if err != 0: return err
            elif not fdx.single_run: self.load_fetches()


        finished_raw = datetime.now()
        finished = int(finished_raw.timestamp())
        ddelta_raw = finished - started
        dmins = str(int(ddelta_raw/60)).zfill(2)
        dsecs = str(int(ddelta_raw % 60)).zfill(2)
        duration = f'{dmins}:{dsecs}'
        

        if not update_only: msg(_('Finished fetching (%a new articles), duration: %b'), self.new_items, duration)
        else: msg(_('Finished updating metadata, duration: %a'), duration)
        
        return 0











    def recalculate(self, ids, **kargs): 
        self.cache_feeds()
        self.cache_rules()
        self.cache_flags()        
        return self.run_locked(FX_LOCK_ALL, self._recalculate, ids, **kargs)
    def _recalculate(self, ids, **kargs):
        """ Utility to recalculate, retokenize, relearn, etc. 
            Useful for mass operations """
        learn = kargs.get('learn',False)
        rank = kargs.get('rank',False)
        index = kargs.get('index',False)

        if type(ids) is str and '..' in ids: 
            start_id = scast(slist(ids.split('..'), 0, None), int, 0)
            end_id = scast(slist(ids.split('..'), 1, None), int, self.get_last_docid())
            many = True
        else:
            ids = scast(ids, int, None)
            if ids is None: return msg(FX_ERROR_VAL, _('Invalid id/ids given! Should be ID or START_ID..END_ID'))
            many = False


        entry = FeedexEntry(self, exists=True)

        if many:
            batch_size = scast(kargs.get('batch_size'), int, fdx.config.get('max_items_per_transaction', 1000))

            if rank: msg(_("Reranking entries..."), log=True)
            if learn: msg(_("Relearning keywords for Entries..."), log=True)
            if index: msg(_("Reindexing entries..."), log=True)
        
            err = 0
            page = 0
            t_start_id = 0
            t_end_id = 0
            stop = False

            if rank: self.connect_QP() # Needed to bypass lock

            while not stop:
                t_start_id = start_id + (page * batch_size)
                page += 1
                t_end_id = start_id + (page * batch_size)
                vs = {'start_id':t_start_id, 'end_id':t_end_id}
                if t_end_id >= end_id:
                    t_end_id = end_id
                    stop = True

                for e in self.qr_sql_iter(RECALC_MULTI_SQL, vs):
                    entry.populate(e)
                    if learn: err = entry.relearn(no_commit=True)
                    elif rank: err = entry.rerank(no_commit=True)
                    elif index: err = entry.reindex(no_commit=True)
                if self.status != 0: return self.status
                err = entry.commit()
                if err != 0: return msg(err, _('Recalculation aborted due to errors'))
            
            msg(_('Recalculation finished!'), log=True)
            return 0
        
        else:
            err = 0 
            entry.get_by_id(ids)
            if learn: err = entry.relearn()
            elif rank: err = entry.rerank()
            elif index: err = entry.reindex()
            return err








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



    def empty_trash(self, **kargs): return self.run_locked({FX_LOCK_FETCH, FX_LOCK_FEED, FX_LOCK_ENTRY,}, self._empty_trash, **kargs)
    def _empty_trash(self, **kargs):
        """ Removes all deleted items permanently """
        # Delete permanently with all data
        terms_deleted = 0
        entries_deleted = 0
        feeds_deleted = 0
        err = self.run_sql_lock(EMPTY_TRASH_TERMS_SQL)
        if err != 0: return err
        terms_deleted = self.rowcount

        entry = FeedexEntry(self, exists=True)
        for e in self.qr_sql_iter('select * from entries where coalesce(deleted,0) > 0'):
            entry.populate(e)
            err = entry._oper(FX_ENT_ACT_DEL_PERM, no_commit=True)
            if err != 0: return err
            entries_deleted += 1
        if self.status != 0: return self.status
        err = entry.commit()
        if err != 0: return err
        
        feed = FeedexFeed(self, exists=True)
        for f in fdx.feeds_cache:
            if scast(f[FEEDS_SQL_TABLE.index('deleted')], int, 0) == 0: continue
            feed.populate(f)
            entries_deleted += feed.get_doc_count()
            err = feed._oper(FX_ENT_ACT_DEL_PERM, no_commit=True)
            if err != 0: return err
            feeds_deleted += 1
        if self.status != 0: return self.status
        err = feed.commit()
        if err != 0: return err

        return msg(_('Trash emptied: %a channels/categories, %b entries, %c learned keywords removed'), feeds_deleted, entries_deleted, terms_deleted, log=True)
                     








