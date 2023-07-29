# -*- coding: utf-8 -*-
""" Tools and utilities for Feedex """


from feedex_headers import *



class FeedexError(Exception):
    """ Generic Feedex exception"""
    def __init__(self, *args, **kargs):
        self.code = kargs.get('code', FX_ERROR)
        self.log = kargs.get('log', True)
        self.bus_message = args
        msg(self.code, *args)        



class FeedexTypeError(FeedexError):
    """ Type given was different than expected """
    def __init__(self, *args, **kargs): 
        kargs['code'] = kargs.get('code', FX_ERROR_VAL)
        super().__init__(*args, **kargs)

class FeedexConfigError(FeedexError):
    """ Error with Fedex configuration """
    def __init__(self, *args, **kargs): 
        kargs['code'] = kargs.get('code', FX_ERROR_VAL)
        super().__init__(*args, **kargs)

class FeedexCommandLineError(FeedexError):
    """ Invalid command line arguments were given """
    def __init__(self, *args, **kargs): 
        kargs['code'] = kargs.get('code', FX_ERROR_CL)        
        super().__init__(*args, **kargs)








class FeedexMainBus:
    """ Main Data Container class for Feedex """    
    def __init__(self, **kargs):

        # Data edit lock
        self.__dict__['lock'] = threading.Lock()

        # Global configuration
        self.__dict__['config'] = kargs.get('config', DEFAULT_CONFIG)
        self.__dict__['debug_level'] = None

        # Language models
        self.__dict__['lings'] = None
        
        # Cached DB data 
        self.__dict__['feeds_cache'] = None
        self.__dict__['rules_cache'] = None
        self.__dict__['rules_val_cache'] = None
        self.__dict__['search_history_cache'] = None
        self.__dict__['flags_cache'] = None
        self.__dict__['terms_cache'] = None
        self.__dict__['feed_freq_cache'] = None

        self.__dict__['recom_qr_str'] = None # Query string used for recommendations 


        self.__dict__['icons_cache'] = None

        self.__dict__['fetches_cache'] = None

        self.__dict__['doc_count'] = None

        # Connection counter
        self.__dict__['conn_num'] = 0

        # Main return status
        self.__dict__['ret_status'] = 0

        # One-time Flags
        self.__dict__['cli'] = True
        self.__dict__['single_run'] = True

        # Message queue
        self.__dict__['bus_q'] = []


        # Download errors ( not to retry failed downloads)
        self.__dict__['download_errors'] = []
        # Invalid log
        self.__dict__['log_err'] = False
        # Invalid CLI parameters
        self.__dict__['cli_param_error'] = False

        # Action flags to manage traffic
        self.__dict__['busy'] = False

        # Local DB locks
        self.__dict__['db_lock'] = False
        self.__dict__['db_fetch_lock'] = False


    def __setattr__(self, __name: str, __value) -> None:
        """ Setter with lock """
        self.lock.acquire()
        self.__dict__[__name] = __value
        self.lock.release()

    def bus_append(self, item):
        """ Append to bus queue with locking """
        self.lock.acquire()
        self.bus_q.append(item)
        self.lock.release()

    def bus_del(self, index):
        """ Delete from bus queue with locking """
        self.lock.acquire()
        del self.bus_q[int(index)]
        self.lock.release()

    def get_last_bus(self):
        """ Fetch last message from the bus """
        if len(self.bus_q) > 0: return self.bus_q[-1]

    def add_error(self, err):
        """ Append to download error list """
        self.lock.acquire()
        self.download_errors.append(err)
        self.lock.release()



    # Logging and message methods

    def log(self, code:int, *args, **kargs):
        """Handle adding log entry (add timestamp and ERROR bit)"""
        if self.log_err is True: return -1
        if code < 0: err = 'ERROR: '
        else: err=''
        log_str = ''
        for a in args:
            a = scast(a, str, '').replace("\n",' ').replace("\t",' ').replace("\r",' ')
            log_str = f'{log_str} {a}'
        log_str = f"{str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}\t{err}{log_str}\n"

        try:
            with open(self.config.get('log'),'a') as logf: logf.write(log_str)
        except (OSError, TypeError) as e: 
            self.log_err = True
            self.msg( (FX_ERROR_IO,f"{_('Could not open log file')} {self.config.get('log','<UNKNOWN>')}: %a", f'{e}') ) 




    def parse_msg_args(self, *args, **kargs):
        """ Parses argument tuble for msg """
        code = None
        text = None
        aargs = []

        for a in args:
            if type(a) is int and text is None and code is None: 
                code = a
                continue

            if code is None: code = 0
            if text is None: 
                text = a
                continue
            else: aargs.append(a)

        return code, text, aargs





    def msg(self, *args, **kargs):
        """ Print nice CLI message, log and enqueue to bus """
        log = kargs.get('log',False)
        do_print = kargs.get('print', self.cli)
        
        code, text, aargs = self.parse_msg_args(*args, **kargs)
        if not self.single_run: self.bus_append((code, text, *aargs))

        if code < 0: self.ret_status = code
        else: self.ret_status = 0
        
        if do_print or log:
            
            cli_text = text
            base_text = text
            
            for i,a in enumerate(aargs):
                if i == 0: chks = '%a'
                elif i == 1: chks = '%b'
                elif i == 2: chks = '%c'
                elif i == 3: chks = '%d'

                if chks in base_text:
                    if do_print:
                        if code < 0: cli_text = cli_text.replace(chks, f'{TERM_ERR_BOLD}{a}{TERM_ERR}')
                        else: cli_text = cli_text.replace(chks, f'{TERM_BOLD}{a}{TERM_NORMAL}')
                    if log: base_text = base_text.replace(chks, str(a))
                else:
                    if do_print:
                        if code < 0: cli_text = f'{cli_text} {TERM_ERR_BOLD}{a}{TERM_ERR}'
                        else: cli_text = f'{cli_text} {TERM_BOLD}{a}{TERM_NORMAL}'
                    if log: base_text = f'{base_text} {a}'

            if do_print:
                if code < 0: cli_text = f'{TERM_ERR}{cli_text}{TERM_NORMAL}'


        if log: self.log(code, base_text)

        if do_print:
            if code >= 0: print(cli_text)
            else: sys.stderr.write(cli_text + "\n")
        
        return code



    def debug(self, *args):
        """ Display debug message """
        if self.debug_level in (None,0): return
        
        if type(args[0]) is int: 
            args = list(args)
            del args[0]
            level = type(args[0])
        else: level = 1

        if self.debug_level == level or self.debug_level == 1:
            debug_str = ''
            for a in args: debug_str = f"""{debug_str} {a}"""
            print(debug_str.strip())





    # Configuration methods
    def parse_config(self, cfile:str, **kargs):
        """ Parse configuration from a given file and put it to a general storage """

        self.config = {}

        try: 
            with open(cfile, 'r') as f: lines = f.readlines()
        except OSError as e:
            raise FeedexConfigError(_('Error reading config from %a: %b'), cfile, e)


        for l in lines:

            l = l.strip()
            if l == '': continue
            if l.startswith('#'): continue
            if '=' not in l: continue
        
            fields = l.split('=',1)

            option = scast(slist(fields, 0, None), str, '').strip()
            if option == '': continue
            value = scast(slist(fields, 1, None), str, '').strip()
            if value == '': continue

            vfloat = scast(value, float, None)

            if value.isdigit(): value = scast(value, int, 0)
            elif not (vfloat is None): value = vfloat
            elif value in ('True','true','Yes','yes','YES'): value = True
            elif value in ('False','false','No','no','NO'): value = False
            else:
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:]
                    value = value[:-1]
                    value = value.replace('\"','"')
                if value.startswith("'") and value.endswith("'"):
                    value = value[1:]
                    value = value[:-1]
                    value = value.replace("'","")
            
                if "/" in value and "~" in value: value = value.replace('~',os.getenv('HOME'))
            
            self.config[option] = value

        self.config_file = cfile

        debug(7, self.config)
        return 0






    def save_config(self, **kargs):
        """ Saves config dict to a file """
        contents = ''
        for k,v in self.config.items():
            if v in (None,''): v = ''
            elif v is True: v = 'True'
            elif v is False: v = 'False'
            else: v = scast(v, str, '')
            contents = f"{contents}\n{k} = {v}"

        try:        
            with open(self.config_file, 'w') as f: f.write(contents)
            self.msg(_('Configuration saved to %a'), self.config_file)  
            return 0
        except OSError as e:
            return self.msg(FX_ERROR_IO, f'{_("Error saving configuration to %a:")} {e}', self.config_file )






    def validate_config(self, **kargs):
        """ Validates config dictionary """
        config = kargs.get('config', self.config)
        strict = kargs.get('strict', False)
        load = kargs.get('load', True)

        new_config = config.copy()

        for k,v in config.items():

            if msg and v is None: continue

            v_int = scast(v, int, None)
            v_float = scast(v, float, None)
            v_str = scast(v, str, None)
            v_bool = scast(v, bool, None)

            if k in CONFIG_INTS_NZ:
                if v_int is None or v_int <= 0:
                    if strict: return FX_ERROR_VAL, _('%a must be integer > 0'), CONFIG_NAMES.get(k)
                    else: self.msg(FX_ERROR_VAL, f'{_("Invalid config option: %a; Defaulting to")} {DEFAULT_CONFIG[k]}', k)
                    new_config[k] = DEFAULT_CONFIG[k]
            if k in CONFIG_INTS_Z:
                if v_int is None or v_int < 0:
                    if strict: return FX_ERROR_VAL, _('%a must be integer >= 0'), CONFIG_NAMES.get(k)
                    else: self.msg(FX_ERROR_VAL, f'{_("Invalid config option: %a; Defaulting to")} {DEFAULT_CONFIG[k]}', k)
                    new_config[k] = DEFAULT_CONFIG[k]
            if k in CONFIG_BOOLS:
                if v_bool is None:
                    if strict: return FX_ERROR_VAL, _('%a must be True or False'), CONFIG_NAMES.get(k)
                    else: self.msg(FX_ERROR_VAL, f'{_("Invalid config option: %a; Defaulting to")} {DEFAULT_CONFIG[k]}', k)
                    new_config[k] = DEFAULT_CONFIG[k]
            if k in CONFIG_FLOATS:
                if v_float is None:
                    if strict: return FX_ERROR_VAL, _('%a must be a valid number'), CONFIG_NAMES.get(k)
                    else: self.msg(FX_ERROR_VAL, f'{_("Invalid config option: %a; Defaulting to")} {DEFAULT_CONFIG[k]}', k)
                    new_config[k] = DEFAULT_CONFIG[k]
            if k in CONFIG_STRINGS:
                if v_str is None:
                    if strict: return FX_ERROR_VAL, _('%a must be a valid string'), CONFIG_NAMES.get(k)
                    else: self.msg(FX_ERROR_VAL, f'{_("Invalid config option: %a; Defaulting to")} {DEFAULT_CONFIG[k]}', k)
                    new_config[k] = DEFAULT_CONFIG[k]
            if k in CONFIG_KEYS:
                if v_str is None or len(v) > 1:
                    if strict: return FX_ERROR_VAL, _('%a must be a single character ([a-zA-Z0-9])'), CONFIG_NAMES.get(k)
                    else: self.msg(FX_ERROR_VAL, f'{_("Invalid config option: %a; Defaulting to")} {DEFAULT_CONFIG[k]}', k)
                    new_config[k] = DEFAULT_CONFIG[k]


        # ... CLI display and markup options ...
        if config.get('normal_color') is not None and config.get('normal_color') in TCOLS.keys():
            new_config['TERM_NORMAL'] = TCOLS[config.get('normal_color')]
        if config.get('flag_color') is not None and config.get('flag_color') in TCOLS.keys():
            new_config['TERM_FLAG'] = TCOLS[config.get('flag_color')]
        if config.get('read_color') is not None and config.get('read_color') in TCOLS.keys():
            new_config['TERM_READ'] = TCOLS[config.get('read_color')]
        if config.get('deleted_color') is not None and config.get('deleted_color') in TCOLS.keys():
            new_config['TERM_DELETED'] = TCOLS[config.get('deleted_color')]
        if config.get('bold_color') is not None and config.get('bold_color') in TCOLS.keys():
            new_config['TERM_SNIPPET_HIGHLIGHT'] = TCOLS[config.get('bold_color')]

        if config.get('bold_markup_beg') is not None and type(config.get('bold_markup_beg')) is str:
            BOLD_MARKUP_BEG = config.get('bold_markup_beg')
        if config.get('bold_markup_end') is not None and type(config.get('bold_markup_end')) is str:
            BOLD_MARKUP_END = config.get('bold_markup_end')

        if load: self.config = new_config.copy()
        
        return 0
    


    def get_par(self, arg, **kargs):
        """ Sanitizes 'x=y' parameter """
        rarg = slist(scast(arg, str, '').split('='), 1, None)
        if rarg is None: self.cli_param_error = True
        return rarg

        


    def sanitize_arg(self, arg, tp, default, **kargs):
        """ Sanitize and error check command line argument """

        if kargs.get('allow_none',False) and arg is None: return None

        exit_fail = kargs.get('exit_fail',True)
        is_file = kargs.get('is_file',False)
        is_dir = kargs.get('is_dir',False)
        stripped = kargs.get('stripped',False)
        valid_list = kargs.get('valid_list')
        singleton = kargs.get('singleton',False)
        arg_name = kargs.get('arg_name','NULL')
        err_code = kargs.get('err_code',9)

        if not singleton:
            arg_list = arg.split('=',1)
            arg_name = slist(arg_list, 0, default)
            arg_val = slist(arg_list, 1, None)
        else:
            arg_val = arg


        if arg_val is None:
            self.msg(FX_ERROR_CL, _("Empty argument (%a)"), arg_name )
            end_val = None
            if exit_fail: sys.exit(err_code)
        else: end_val = scast(arg_val, tp, None)

        arg_name_str = scast(arg_name, str, '')
        end_val_str = scast(end_val, str, '')

        if end_val is None:
            self.msg(FX_ERROR_CL, _("Invalid argument type (%a)"), arg_name_str )
            if exit_fail: sys.exit(err_code)

        if (stripped or is_file or is_dir) and tp == str:
            end_val = end_val.strip()

        if is_file and not os.path.isfile(end_val):
            self.msg(FX_ERROR_CL, f"{_('File not found')} ({arg_name_str}, {end_val_str})")
            end_val = None
            if exit_fail: sys.exit(err_code)


        if is_dir and not os.path.isdir(end_val):
            self.msg(FX_ERROR_CL, f"{_('Directory not found')} ({arg_name_str}, {end_val_str})")
            end_val = None
            if exit_fail: sys.exit(err_code)


        if not (valid_list is None):
            if end_val not in valid_list:
                self.msg(FX_ERROR_CL, f"{_('Invalid argument value')} ({arg_name_str}, {end_val_str})")
                if exit_fail: sys.exit(err_code)
                else: end_val = None

        if end_val is None and not (default is None):
            self.msg(FX_ERROR_CL, _("Defaulting to %a"), scast(default, str, _('<NONE>')))
            end_val = default

        return end_val
    
    

    def ext_open(self, command_id, main_arg, **kargs):
        """ Wrapper for executing external commands """
        background = kargs.get('bakcground',True)
        if kargs.get('file',False):
            if not os.path.isfile(main_arg): return self.msg(FX_ERROR_IO, _('File %a not found!'), main_arg)

        if command_id == 'search_engine':
            command_id = 'browser'
            main_arg = self.config.get('search_engine',DEFAULT_CONFIG.get('search_engine', main_arg)).replace('%Q', main_arg)

        command = scast( coalesce( nullif(self.config.get(command_id),''), FEEDEX_DEFAULT_BROWSER), str, '')
    
        rstr = random_str(string=command)
        command = command.replace('%%',rstr)
        if '%u' not in command and '%U' not in command and '%f' not in command and '%F' not in command: 
            command = f'{command} %u'

        command = command.split(' ')
        for i,arg in enumerate(command):
            arg = arg.replace('%u', main_arg)
            arg = arg.replace('%U', main_arg)
            arg = arg.replace('%f', main_arg)
            arg = arg.replace('%F', main_arg)
            if kargs.get('title') is not None: arg = arg.replace('%t', scast(kargs['title'], str, '') )
            if kargs.get('alt') is not None: arg = arg.replace('%a', scast(kargs['alt'], str, '') )
            arg = arg.replace(rstr,'%')
            command[i] = arg

        debug(' '.join(command))
        if background: debug('Running in background...')

        try:
            if background: subprocess.Popen(command)
            else: subprocess.run(command)
        except OSError as e: return self.msg(FX_ERROR_IO, f'{_("Error opening %a:")} {e}', main_arg)

        return 0






    #################################################################
    # Finding data in cache or resolving data
    #

    def find_flag(self, val:str, **kargs):
        """ Resolve flag by name or ID """
        if val is None: return None
        if type(val) is int:
            if val in self.flags_cache.keys(): return val
        val = scast(val, str, -1)
        if val == -1: return -1
        if val.isdigit():
            if int(val) in self.flags_cache.keys(): return int(val)
        for k,v in self.flags_cache.items():
            if val == v[FLAGS_SQL_TABLE.index('id')-1]: return k
        return -1

    def get_flag_name(self, id:int, **kargs):
        with_id = kargs.get('with_id', False)
        if id not in self.flags_cache.keys(): return '<???>'
        name = self.flags_cache.get(id, (None,))[0]
        if name in (None, ''): return f'{id}'
        else: 
            name = ellipsize(name, 200)            
            if with_id: name = f"{name} ({id})"
            return name

    def get_flag_desc(self, id:int, **kargs):
        if id not in self.flags_cache.keys(): return ''
        desc = self.flags_cache.get(id, (None,None,''))[1]
        if desc in (None, ''): return ''
        else: return desc

    def get_flag_color(self, id:int, **kargs):
        if id not in self.flags_cache.keys(): return None
        color = self.flags_cache.get(id, (None,None,self.config.get('gui_default_flag_color',None)))[2]
        if color in (None, ''): return None
        else: return color

    def get_flag_color_cli(self, id:int, **kargs):
        if id not in self.flags_cache.keys(): return ''
        color = self.flags_cache.get(id, (None,None,None,self.config.get('TERM_FLAG', TERM_FLAG)))[3]
        if color in (None, ''): return self.config.get('TERM_FLAG', TERM_FLAG)
        else: return color
        



    def find_category(self, val:str, **kargs):
        """ Resolve entry type depending on whether ID or name was given"""
        if val is None: return None
        load = kargs.get('load', False)
        if scast(val, str, '').isdigit():
            val = int(val)
            for f in self.feeds_cache:
                if f[FEEDS_SQL_TABLE.index('id')] == val and f[FEEDS_SQL_TABLE.index('is_category')] == 1: 
                    if load: return f
                    else: return val
        else:
            val = str(val)
            for f in self.feeds_cache:
                if f[FEEDS_SQL_TABLE.index('name')] == val and f[FEEDS_SQL_TABLE.index('is_category')] == 1: 
                    if load: return f
                    else: return f[FEEDS_SQL_TABLE.index('id')]
        return -1


    def find_feed(self, val:int, **kargs):
        """ check if feed with given ID is present """
        if val is None: return None
        val = scast(val, int, -1)
        if val < 0: return -1
        load = kargs.get('load', False)
        for f in self.feeds_cache:
            if val == f[FEEDS_SQL_TABLE.index('id')] and f[FEEDS_SQL_TABLE.index('is_category')] != 1: 
                if load: return f
                else: return val
        return -1


    def find_f_o_c(self, val, **kargs):
        """ Resolve feed or category """
        if val is None: return None
        val = scast(val, int, -1)
        if val < 0: return -1
        load = kargs.get('load', False)
        for f in self.feeds_cache:
            if f[FEEDS_SQL_TABLE.index('id')] == val:
                if load: return f
                if f[FEEDS_SQL_TABLE.index('is_category')] == 1: return -1, val
                return val, -1
        return -1


    def get_feed_name(self, id:int, **kargs):
        """ Return name of a IDd feed/category """
        with_id = kargs.get('with_id',True)

        for f in self.feeds_cache:
            if f[FEEDS_SQL_TABLE.index('id')] == id:
                name = coalesce(
                f[FEEDS_SQL_TABLE.index('name')],
                f[FEEDS_SQL_TABLE.index('title')],
                f[FEEDS_SQL_TABLE.index('url')]
                )

                if name in ('',None): name = f"""{id}"""
                else:
                    name = ellipsize(name, 200)
                    if with_id: name = f"""{name} ({id})"""
                return name
        return '<???>'


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
            if qtype.lower() in ('string','str','string_matching','sm'): return 0
            elif qtype.lower() in ('full', 'fts', 'full-text','fulltext',): return 1
            else: return 1

        return -1







##########################################################################
#
#   Resource downloading
#

    def hash_url(self, url, **kargs):
        hash_obj = hashlib.sha1(url.encode())
        return hash_obj.hexdigest()

    def download_res(self, url:str, **kargs):
        """ Downloading resurces and error handling """
        if url in self.download_errors: return 0, None
        verbose = kargs.get('verbose', True)
    
        headers = {'User-Agent' : coalesce(kargs.get('user_agent', self.config.get('user_agent')), FEEDEX_USER_AGENT) }
        timeout = scast(kargs.get('timeout', self.config.get('fetch_timeout',0)), int, 0)
        if timeout != 0: headers['timeout'] = timeout

        ofile = kargs.get('ofile')
        mimetypes = kargs.get('mimetypes', FEEDEX_IMAGE_MIMES)
        
        output_pipe = kargs.get('output_pipe', '')

        try:
            request = urllib.request.Request(url, None, headers)
            response = urllib.request.urlopen(request)

            if response.status in (200, 201, 202, 203, 204, 205, 206):
                content_type = slist(scast(response.info().get('Content-Type'), str, '').split(';'), 0, '')
                if content_type not in mimetypes: 
                    self.add_error(url)
                    if verbose: return msg(FX_ERROR_HANDLER, _('Invalid content type (%a)!'), content_type), None
                    else: return FX_ERROR_HANDLER, None

                content_size = scast(response.info().get('Content-Length'), int, None)
                if content_size is not None and content_size > MAX_DOWNLOAD_SIZE: 
                    self.add_error(url)
                    if verbose: return msg(FX_ERROR_HANDLER, _('Resource indicated size too large (%a)!'), f'{content_size}/{MAX_DOWNLOAD_SIZE}'), None
                    else: return FX_ERROR_HANDLER, None

                i = 0
                res_data = output_pipe
                res_type = type(res_data)
                if ofile is None:
                    while True:
                        i += 1
                        res_chunk = response.read(FEEDEX_MB)
                        if not res_chunk: break
                        if i >= MAX_DOWNLOAD_SIZE: 
                            self.add_error(url)
                            if verbose: return msg(FX_ERROR_HANDLER, _('Resource too large! Should be %a max'), MAX_DOWNLOAD_SIZE), None
                            else: return FX_ERROR_HANDLER, None

                        if res_type is str: res_data = f"""{res_data}{res_chunk.decode("utf-8")}"""
                        else: res_data.write(res_chunk)

                    return response, res_data

                else:
                    with open(ofile, 'wb') as f:
                        while True:
                            i += 1
                            chunk = response.read(FEEDEX_MB)
                            if not chunk: break
                            if i >= MAX_DOWNLOAD_SIZE:
                                f.close()
                                self.add_error(url)
                                if verbose: return msg(FX_ERROR_HANDLER, _('Resource too large! Should be %a max'), MAX_DOWNLOAD_SIZE), None
                                else: return FX_ERROR_HANDLER, None
                            f.write(chunk)

                    return 0, None


 
            else: 
                self.add_error(url)
                return msg(FX_ERROR_HANDLER, f'{_("Could not download image at %a! HTTP return status:")} {response.status}', f' {url}'), None

        except (urllib.error.URLError, ValueError, TypeError, OSError, FileNotFoundError, AttributeError) as e:
            self.add_error(url)
            return msg(FX_ERROR_HANDLER, f'{_("Could not download image at %a! Error:")} {e}', f' {url}'), None




   # Utilities
    def strip_markup(self, raw_text:str, **kargs):
        """ Detect and strip HTML from text
            Extract links to images and return both"""
        raw_text = scast(raw_text, str, None)
        if raw_text is None: return None, (), ()


        # Determine content type (unless overridden)
        html = kargs.get('html',False)
        if not html:
            test = re.search(RSS_HANDLER_TEST_RE, raw_text)
            if test is None: html = False
            else: html = True

        # strip most popular HTML specials
        for ent in HTML_ENTITIES:
            raw_text = raw_text.replace(ent[0],ent[2])
            raw_text = raw_text.replace(ent[1],ent[2])

        if html:
            # Search for images
            if kargs.get('rx_images') is not None: images = re.findall(kargs.get('rx_images'), raw_text)
            else: images = re.findall(RSS_HANDLER_IMAGES_RE, raw_text)

            if kargs.get('rx_links') is not None: links = re.findall(kargs.get('rx_links'), raw_text)
            else: links = ()

            if kargs.get('test',False): return raw_text, images, links

            # Strips markup from text - a simple one for speed and convenience
            # Handle tags...
            raw_text = raw_text.replace("\n\r","\n")
            raw_text = raw_text.replace("\r","\n")
            raw_text = raw_text.replace("<table>","\n")
            raw_text = raw_text.replace("</table>","\n")
            raw_text = raw_text.replace("</tr>","\n")
            raw_text = raw_text.replace("<p>","\n")
            raw_text = raw_text.replace("</p>","\n")
            raw_text = raw_text.replace("<br>","\n")
            raw_text = raw_text.replace("<br />","\n")
            raw_text = raw_text.replace("<br/>","\n")
            raw_text = raw_text.replace('<em>','»')
            raw_text = raw_text.replace('</em>','«')
            raw_text = raw_text.replace('<b>','»')
            raw_text = raw_text.replace('</b>','«')
            raw_text = raw_text.replace('<i>','»')
            raw_text = raw_text.replace('</i>','«')
            raw_text = raw_text.replace('<u>','»')
            raw_text = raw_text.replace('</u>','«')
            raw_text = raw_text.replace('<strong>','»')
            raw_text = raw_text.replace('</strong>','«')
            stripped_text = re.sub(RSS_HANDLER_STRIP_HTML_RE, '', scast(raw_text, str, ''))
            stripped_text = stripped_text.strip()
        else:
            stripped_text = raw_text
            images = ()
            links = ()

        stripped_text = re.sub(" +", " ", stripped_text)
        stripped_text = re.sub("\t+", "\t", stripped_text)
        stripped_text = re.sub("\n\n\n", "\n\n", stripped_text)

        return stripped_text, images, links





    def parse_res_link(self, string:str, **kargs):
        """ Extracts elements and generates resource thumbnail filename for cache """
        string = string.strip()
        if string == '': return None
        res = {'url':'', 'desc':'', 'title':'', 'alt':'', 'url_hash':'', 'thumbnail':''}
        do_process_desc = False
        gui = kargs.get('gui', True)

        if string.startswith('http://') or string.startswith('https://'): res['url'] = string
        else:
            res['url'] = slist(re.findall(IM_URL_RE, string), 0, None)
            do_process_desc = True

        res['url'] = scast(res['url'], str, '')
        # This is to avoid showing icons from feedburner etc.
        if res['url'] == '': return None
        for i in FEEDEX_IGNORE_THUMBNAILS:
            if res['url'].startswith(i): return None

        if do_process_desc:
            alt = slist(re.findall(IM_ALT_RE, string), 0, '')
            title = slist(re.findall(IM_TITLE_RE, string), 0, '')
            res['alt'] = slist( self.strip_markup(scast(alt, str, ''), html=True), 0, '').strip()
            res['title'] = slist( self.strip_markup(scast(title, str,''), html=True), 0, '').strip()
            
            if not gui:
                desc=''
                if title != '': desc=f"""<b>{res['title']}</b>"""
                if alt != '': desc=f"""{desc}; <b>{res['alt']}</b>"""
                if desc != '': desc = f"""{desc}({res['url']})"""
                else: desc = res['url']
                res['desc'] = desc

        elif not gui: res['desc'] = res['url']

        res['url_hash'] = self.hash_url(res['url'])
        res['thumbnail'] = f"""{res['url_hash']}.img"""

        return res




    ######################################################################3
    #
    #       Catalog routines


    def load_catalog(self, **kargs):
        """ Load Feed catalog from JSON cache """
        if not hasattr(self, 'catalog'): self.catalog = None
        if self.catalog is None:
            self.catalog = load_json(os.path.join(FEEDEX_FEED_CATALOG_CACHE, 'catalog.json'), ())
            if self.catalog == (): return FX_ERROR_IO
        return 0











# Init main process bus 
fdx = FeedexMainBus()
# ... and alias messaging methods
def msg(*args, **kargs): return fdx.msg(*args, **kargs)
def debug(*args): return fdx.debug(*args)













def slist(lst, idx, default):
    """ Safely extract list element or give default """
    try: 
        return lst[idx]
    except (IndexError, TypeError, ValueError, KeyError) as e: 
        return default


def scast(value, target_type, default_value):
    """ Safely cast into a given type or give default value """
    try:
        if value is None:
            return default_value
        return target_type(value)
    except (ValueError, TypeError):
        return default_value

def sround(value, rnd, default):
    """ Safely round a variable """
    try: return round(value, rnd)
    except (ValueError, TypeError): return default

def nullif(val, nullifier):
    """ SQL's nullif counterpart for Python, returning None if val is in nullifier (list of str/int/float)"""
    if isinstance(nullifier, (list, tuple)):
        if val in nullifier: return None
    elif isinstance(nullifier, (str, int, float)):
        if val == nullifier: return None
    return val

def coalesce(*args, **kargs):
    nulls = kargs.get('nulls',(None,))
    for a in args:
        if a not in nulls: return a


def dezeroe(num, default):
    """ Overwrite zero with default """
    if num == 0: return default
    else: return num


def ellipsize(string, length):
    """ Ellipsize a string for display """
    if len(string) > length: return f"{string[:length]}..."
    else: return string








def convert_timestamp(datestring:str, **kargs):
    """ This is needed to handle timestamps from updates, as it can be tricky at times and will derail the whole thing"""
    if isinstance(datestring, str):
        
        if datestring.isdigit():
            if len(datestring) >= 10:
                datestring = datestring[:10]
                return int(datestring)
            else: 
                msg(FX_ERROR_VAL, _('Timestamp convertion: %a'), _('Invalid epoch'))
                return None

        try:
            date_obj = dateutil.parser.parse(datestring, fuzzy_with_tokens=True)
            return int(date_obj[0].timestamp())
        except (dateutil.parser.ParserError, ValueError) as e:
            msg(FX_ERROR_VAL, _('Timestamp convertion: %a'), e )
            return None

    elif isinstance(datestring, int): return datestring
    else: return None


def humanize_date(string, today, yesterday, year):
    """ Format date to be more human readable and context dependent """
    date_short = string
    date_short = date_short.replace(today, _("Today") )
    date_short = date_short.replace(yesterday, _("Yesterday") )
    date_short = date_short.replace(year,'')
    return date_short



def sanitize_file_size(size:int, **kargs):
    """ Convert bytes to a nice string """
    str_dict = {1: 'KB', 2:' MB', 3:'GB', 4:'TB', 5:'PB', 6:'EB' } # This is clearly an overkill :)
    unit = ''

    r = scast(size, float, None)
    rs = float(0)
    if r is None: return _('<???>')
    for i in range(1,6):
        r = r / 1024
        if r < 1: break
        rs = r
        unit = str_dict[i]

    return f"""{rs:.4f} {unit}"""



def get_dir_size(start_path = '.'):
    """ Calculates size recursively for everything under "start_path" directory """
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size




def random_str(**kargs):
    """ Generates a random string with length=length for string=string 
        Assures that random sequence is not in original text
        Useful for escape sequences """
    l = kargs.get('length',15)
    string = kargs.get('string','')
    rand_str = ''
 
    while rand_str in string:
        for _ in range(l):
            rand_int = randint(97, 97 + 26 - 1)
            flip = randint(0, 1)
            rand_int = rand_int - 32 if flip == 1 else rand_int
            rand_str += (chr(rand_int))
    
    return rand_str




def cli_mu(string:str, **kargs):
    string = string.replace('<b>',f'{TERM_BOLD}')
    string = string.replace('</b>',f'{TERM_NORMAL}')
    string = string.replace('<i>',f'{TERM_FLAG}')
    string = string.replace('</i>',f'{TERM_NORMAL}')
    string = string.replace('&lt;','<')
    string = string.replace('&gt;','>')
    return string

def clr_mu(string:str, **kargs):
    string = string.replace('<b>','')
    string = string.replace('</b>','')
    string = string.replace('<i>','')
    string = string.replace('</i>','')
    string = string.replace('&lt;','<')
    string = string.replace('&gt;','>')
    return string


def mu_print(string:str, **kargs):
    """ Nice print for marked up messages - with bold etc. """
    print(cli_mu(string))



def check_paths(paths:list):
    """ Check if paths in a list exist and create them if not """
    for p in paths:
        if not os.path.isdir(p): os.makedirs(p)


def check_if_regex(string:str):
    """ Check if string is a valid REGEX """
    try:
        re.compile(string)
        is_valid = True
    except re.error:
        is_valid = False
    return is_valid





def check_url(string:str):
    """ Check if a string is a valid URL or IP """
    if type(string) is not str:
        return False
    matches = re.findall(URL_VALIDATE_RE, string)
    if matches not in (None, (), []): return True
    matches = re.findall(URL_VALIDATE_RE, f'http://{string}')
    if matches not in (None, (), []):
        return True
    matches = re.findall(URL_VALIDATE_RE, f'https://{string}')
    if matches not in (None, (), []):
        return True
    matches = re.findall(IP4_VALIDATE_RE, string)
    if matches not in (None, (), []):
        return True
    matches = re.findall(IP6_VALIDATE_RE, string)
    if matches not in (None, (), []):
        return True

    return False







def load_json(infile, default, **kargs):
    """ Loads JSON file and returns default if failed  """
    if not os.path.isfile(infile):
        msg(FX_ERROR_IO, _('JSON file %a does not exist!'), infile)
        if kargs.get('create_file',False) and not os.path.exists(infile): save_json(infile, default)         
        return default
    out = default
    try:
        with open(infile, 'r') as f:
            out = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        msg(FX_ERROR_IO, _('Error reading from %a: %b'), infile, e )
        return default
    return out


def save_json(ofile:str, data, **kargs):
    """ Saves GUI attrs into text file """
    if kargs.get('check',False):
        if os.path.exists(ofile):
            msg(FX_ERROR_IO, _('File %a already exists!'), ofile)
            return -1
    try:
        with open(ofile, 'w') as f:
            json.dump(data, f)
        msg(_('Data saved to %a'), ofile)
    except (OSError, json.JSONDecodeError) as e:
        msg(FX_ERROR_IO, _('Error writing to %a: %b'), ofile, e)
        return -1
    return 0



def print_json(data):
    """ Prints data in JSON format """
    try:
        json_string = json.dumps(data)
    except (OSError, json.JSONDecodeError, TypeError) as e:
        msg(FX_ERROR_IO, _('Error converting to JSON: %a'), e)
        return -1
    print(json_string)
    return 0
