# -*- coding: utf-8 -*-

""" Loads dependencies and all Feedex modules
    Declares constants: field lists, SQL queries, prefixes etc."""



# Standard
import sys
import os
from datetime import datetime, timedelta, date
import re
from math import log10
import subprocess
import time
import pickle
from shutil import copyfile
from random import randint
import json
import threading


# Downloaded
import feedparser
import urllib.request
import hashlib

import sqlite3
import xapian

from dateutil.relativedelta import relativedelta
import dateutil.parser
import snowballstemmer
import pyphen
import gettext





# Constants
FEEDEX_VERSION = "1.0.0"
FEEDEX_DB_VERSION_COMPAT = "1.0.0"
FEEDEX_RELEASE="2023"
FEEDEX_AUTHOR ="""Karol Pałac"""
FEEDEX_CONTACT="""palac.karol@gmail.com"""
FEEDEX_WEBSITE="""https://github.com/kpalac/feedex2""" 

PLATFORM = sys.platform
if PLATFORM == 'linux':
    FEEDEX_CONFIG = os.environ['HOME'] + '/.config/feedex.conf'
    FEEDEX_SYS_CONFIG = '/etc/feedex.conf'

    FEEDEX_SYS_SHARED_PATH = '/usr/share/feedex'
    FEEDEX_SHARED_PATH = os.environ['HOME'] + '/.local/share/feedex'

    # Paths
    APP_PATH = '/usr/bin'
    FEEDEX_DEFAULT_BROWSER = 'xdg-open %u'

FEEDEX_SYS_ICON_PATH = os.path.join(FEEDEX_SYS_SHARED_PATH,'data','pixmaps')
FEEDEX_MODELS_PATH = os.path.join(FEEDEX_SYS_SHARED_PATH,'data','models')
FEEDEX_LOCALE_PATH = os.path.join(FEEDEX_SYS_SHARED_PATH,'data','locales')


gettext.install('feedex', FEEDEX_LOCALE_PATH)

FEEDEX_DESC=_("Personal News and Notes organizer")

FEEDEX_HELP_ABOUT=f"""
<b>Feedex v. {FEEDEX_VERSION}</b>
{FEEDEX_DESC}

{_("Release")}: {FEEDEX_RELEASE}

{_("Author")}: {FEEDEX_AUTHOR}
{_("Contact")}: {FEEDEX_CONTACT}
{_("Website")}: {FEEDEX_WEBSITE}

"""


# Hardcoded params
MAX_SNIPPET_COUNT = 50
MAX_RANKING_DEPTH = 70
LOCAL_DB_TIMEOUT = 180 
MAX_LAST_UPDATES = 25
MAX_FEATURES_PER_ENTRY = 30
TERM_NET_DEPTH = 30
SOURCE_URL_WEIGHT = 0.1



# Image elements extraction
IM_URL_RE=re.compile('src=\"(.*?)\"', re.IGNORECASE)
IM_ALT_RE=re.compile('alt=\"(.*?)\"', re.IGNORECASE)
IM_TITLE_RE=re.compile('title=\"(.*?)\"', re.IGNORECASE)

# RSS Handling and parsing
FEEDEX_USER_AGENT = 'UniversalFeedParser/5.0.1 +http://feedparser.org/'
RSS_HANDLER_TEST_RE = re.compile('<p.*?>.*?<.*?/p>|<div.*?>.*?<.*?/div>|<br.*?/>|<br/>|<img.*?/>|<span.*?>.*?<.*?/span>')
RSS_HANDLER_IMAGES_RE = re.compile('<img.*?src=\".*?\".*?/>', re.IGNORECASE)
RSS_HANDLER_IMAGES_RE2 = re.compile('<div style=".*?image:url\("(.*?)"\)">', re.IGNORECASE)

RSS_HANDLER_STRIP_HTML_RE = re.compile('<.*?>')

# Mimetypes
FEEDEX_IMAGE_MIMES = ('image/jpeg','image/gif','image/png','image/tiff','image/x-icon','image/svg+xml','image/vnd.microsoft.icon','image/webp')
FEEDEX_AUDIO_MIMES = ()
FEEDEX_VIDEO_MIMES = ()
FEEDEX_TEXT_MIMES = ('text/html','text/plain',)


#Downloads...
FEEDEX_MB = 1024 * 1024
MAX_DOWNLOAD_SIZE = 50 * FEEDEX_MB

# Checks
FLOAT_VALIDATE_RE = re.compile(r'[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?')
URL_VALIDATE_RE = re.compile('http[s]?://?(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', re.IGNORECASE)
IP4_VALIDATE_RE = re.compile('^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$', re.IGNORECASE)
IP6_VALIDATE_RE = re.compile("""^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|
^::(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}$|
^[0-9a-fA-F]{1,4}::(?:[0-9a-fA-F]{1,4}:){0,5}[0-9a-fA-F]{1,4}$|
^[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}::(?:[0-9a-fA-F]{1,4}:){0,4}[0-9a-fA-F]{1,4}$|
^(?:[0-9a-fA-F]{1,4}:){0,2}[0-9a-fA-F]{1,4}::(?:[0-9a-fA-F]{1,4}:){0,3}[0-9a-fA-F]{1,4}$|
^(?:[0-9a-fA-F]{1,4}:){0,3}[0-9a-fA-F]{1,4}::(?:[0-9a-fA-F]{1,4}:){0,2}[0-9a-fA-F]{1,4}$|
^(?:[0-9a-fA-F]{1,4}:){0,4}[0-9a-fA-F]{1,4}::(?:[0-9a-fA-F]{1,4}:)?[0-9a-fA-F]{1,4}$|
^(?:[0-9a-fA-F]{1,4}:){0,5}[0-9a-fA-F]{1,4}::[0-9a-fA-F]{1,4}$|
^(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}::$""", re.IGNORECASE)

# Helper REGEXes
SPLIT_RE = re.compile("""\s|/|\\|\.|;|:|@|#|_|-""")



# SQL...
DOC_COUNT_SQL="""
select count(e.id)
from entries e 
join feeds f on f.id = e.feed_id and coalesce(f.deleted, 0) = 0
where coalesce(e.deleted,0) = 0
"""



GET_RULES_SQL="""
SELECT
null as n, r.name, r.type, r.feed_id, r.field_id, r.string, r.case_insensitive, r.lang,
sum(r.weight * coalesce(e.read, 
    case 
        when r.learned = 1 then 0
        else 1
    end
    ) * coalesce(e.weight,
	case 
		when r.learned = 1 then 0
		else 1
	end
	) ) as main_weight,
r.additive, r.learned, r.flag, coalesce(r.context_id, 0) as context_id

from rules r
left join entries e on e.id = r.context_id
left join feeds f on f.id = e.feed_id
where coalesce(e.deleted,0) <> 1 and coalesce(f.deleted,0) <> 1

group by n, r.name, r.type, r.feed_id, r.field_id, r.case_insensitive, r.lang, r.additive, r.string, r.learned, r.flag, r.context_id

having sum(r.weight * coalesce(e.read, 
    case 
        when r.learned = 1 then 0
        else 1
    end
    ) * coalesce(e.weight,
	case 
		when r.learned = 1 then 0
		else 1
	end
	) ) <> 0
order by r.type asc, abs(main_weight) desc
"""


GET_RULES_NL_SQL="""
SELECT
null as n, r.name, r.type, r.feed_id, r.field_id, r.string, r.case_insensitive, r.lang, r.weight, r.additive, r.learned, r.flag, 0 as context_id
from rules r
where coalesce(r.learned,0) = 0 and r.context_id is NULL
order by r.weight desc
"""





GET_FEEDS_SQL="""select * from feeds order by display_order asc"""



RESULTS_COLUMNS_SQL="""e.*, f.name || ' (' || f.id || ')' as feed_name_id, 
f.name as feed_name, datetime(e.pubdate,'unixepoch', 'localtime') as pubdate_r, strftime('%Y.%m.%d', date(e.pubdate,'unixepoch', 'localtime')) as pudbate_short, 
coalesce( nullif(fl.name,''), fl.id) as flag_name, f.user_agent as user_agent,
c.id as parent_id, coalesce(c.name, c.title, c.id) as parent_name
from entries e 
left join feeds f on f.id = e.feed_id
left join feeds c on c.id = f.parent_id
left join flags fl on fl.id = e.flag"""




EMPTY_TRASH_RULES_SQL = """delete from rules where context_id in
( select e.id from entries e where e.deleted = 1 or e.feed_id in 
( select f.id from feeds f where f.deleted = 1)  )"""

EMPTY_TRASH_ENTRIES_SQL = """delete from entries where deleted = 1 or feed_id in ( select f.id from feeds f where f.deleted = 1)"""

EMPTY_TRASH_FEEDS_SQL1 = """update feeds set parent_id = NULL where parent_id in ( select f1.id from feeds f1 where f1.deleted = 1)"""
EMPTY_TRASH_FEEDS_SQL2 = """delete from feeds where deleted = 1"""




SEARCH_HISTORY_SQL = """
select string,
max(datetime(date,'unixepoch', 'localtime')) as added_date,
max(date) as added_date_raw
from search_history where 
coalesce(string, '') <> '' 
group by string
order by date
"""

RECALC_MULTI_SQL = """select 
e.* 
from entries e 
join feeds f on f.id = e.feed_id 
left join feeds ff on ff.id = f.parent_id
where coalesce(e.deleted,0) <> 1 
and coalesce(f.deleted,0) <> 1 
and coalesce(ff.deleted,0) <> 1
and e.id >= :start_id
and e.id <= :end_id
order by e.id ASC
"""



def n_(arg): return arg # ... to facilitate localization


ENTRIES_SQL_TABLE =      ('id','feed_id','charset','lang','title','author','author_contact','contributors','publisher','publisher_contact',
                                'link','pubdate','pubdate_str','guid','desc','category','tags','comments','text','source','adddate','adddate_str','links','read',
                                'importance','sent_count','word_count','char_count','polysyl_count','com_word_count','numerals_count','caps_count','readability',
                                'weight','flag','images','enclosures','deleted','note','node_id','node_order', 'ix_id')

ENTRIES_SQL_TYPES = (int, int,  str, str, str, str, str, str, str, str, str,  int, str,   str, str, str, str, str, str, str,   int, str,
                     str, int, float,      int, int, int, int, int, int, int,    float, float,   int,   str, str,  int, int,    int, int,   int)

ENTRIES_SQL_TABLE_PRINT = (n_("ID"), n_("Source/Category"), n_("Character encoding"), n_("Language"), n_("Title"), n_("Author"), n_("Author - contact"), n_("Contributors"), n_("Publisher"), n_("Publisher - contact"),
                                  n_("Link"), n_("Date published (Epoch)"), n_("Date published (saved)"), n_("GUID"), n_("Description"), n_("Category"), n_("Tags"), n_("Comments link"), n_("Text"), n_("Source link"), n_("Date added (Epoch)"),
                                  n_("Date added"), n_("Internal links"), n_("Read"), n_("Importance"), n_("Sentence count"), n_("Word count"), n_("Character count"), n_("Polysylable count"), n_("Common words count"),
                                  n_("Numerals count"), n_("Capitalized words count"), n_("Readability"), n_("Weight"), n_("Flag"), n_("Images"), n_("Enclosures"), n_("Deleted?"), n_("Note?"),
                                  n_("Parent Node ID"), n_("Order within a Node"), n_("Index ID"))


RESULTS_SQL_TABLE                = ENTRIES_SQL_TABLE + ("feed_name_id", "feed_name", "pubdate_r", "pubdate_short", "flag_name", "user_agent", "parent_id", "parent_name", "snippets", "rank", "count")
RESULTS_SQL_TYPES                = ENTRIES_SQL_TYPES + (str, str, str, str, str, str, str, int, str, float, int)

RESULTS_SQL_TABLE_PRINT          = ENTRIES_SQL_TABLE_PRINT + (n_("Source (ID)"), n_("Source"), n_("Published - Timestamp"), n_("Date"), n_("Flag name"), n_("User Agent"), n_("Parent Category ID"), n_("Parent Category"), n_("Snippets"), n_("Rank"), n_("Count"))
RESULTS_SHORT_PRINT1             = ("ID", "Source (ID)", "Date", "Title", "Description", "Text", "Author", "Link","Published - Timestamp", "Read", "Flag name", "Parent Category","Parent Category ID", "Importance", "Word count", "Weight", "Snippets", "Rank", "Count")
RESULTS_SHORT_PRINT2             = ("ID", "Source (ID)", "Date", "Title", "Description", "Text", "Author", "Link","Published - Timestamp", "Read", "Flag name","Parent Category","Parent Category ID", "Importance", "Word count", "Weight")

NOTES_PRINT                      = ("ID", "Date", "Title", "Description", "Importance", "Weight", "Deleted?", "Published - Timestamp", "Source (ID)")
HEADLINES_PRINT                  = ("Date", "Title","Source (ID)", "ID")
HEADLINES_PRINT_TITLE             = ("Date", "Description","Source (ID)", "ID")

RESULTS_TOKENIZE_TABLE           = ("title","desc","text")



FEEDS_SQL_TABLE       =  ('id','charset','lang','generator','url','login','domain','passwd','auth','author','author_contact','publisher','publisher_contact',
                                'contributors','copyright','link','title','subtitle','category','tags','name','lastread','lastchecked','interval','error',
                                'autoupdate','http_status','etag','modified','version','is_category','parent_id', 'handler','deleted', 'user_agent', 'fetch',
                                'rx_entries','rx_title', 'rx_link', 'rx_desc', 'rx_author', 'rx_category', 'rx_text', 'rx_images', 'rx_pubdate', 
                                'rx_pubdate_feed', 'rx_image_feed', 'rx_title_feed', 'rx_charset_feed', 'rx_lang_feed',
                                'script_file', 'icon_name', 'display_order')
FEEDS_SQL_TYPES = (int,  str, str, str, str, str,str, str, str, str, str,str, str, str, str, str,str, str, str, str, str, str, str,
                  int, int, int,   str, str, str, str,   int, int,    str, int,     str, int,
                  str, str, str, str, str, str, str, str, str, str, str, str, str, str,
                  str, str, int)

FEEDS_REGEX_HTML_PARSERS = ('rx_entries','rx_title', 'rx_link', 'rx_desc', 'rx_author', 'rx_category', 'rx_text', 'rx_images', 'rx_pubdate', 'rx_pubdate_feed', 'rx_image_feed','rx_title_feed', 'rx_charset_feed', 'rx_lang_feed')


FEEDS_SQL_TABLE_PRINT = (n_("ID"), n_("Character encoding"), n_("Language"), n_("Feed generator"), n_("URL"), n_("Login"), n_("Domain"), n_("Password"), n_("Authentication method"), n_("Author"), n_("Author - contact"),
                                n_("Publisher"), n_("Publisher - contact"), n_("Contributors"), n_("Copyright"), n_("Home link"), n_("Title"), n_("Subtitle"), n_("Category"), n_("Tags"), n_("Name"), n_("Last read date (Epoch)"),
                                n_("Last check date (Epoch)"), n_("Update interval"), n_("Errors"), n_("Autoupdate?"), n_("Last connection HTTP status"), n_("ETag"), n_("Modified tag"), n_("Protocol version"), n_("Is category?"), 
                                n_("Category ID"), n_("Handler"), n_("Deleted?"), n_("User Agent"), n_("Fetch?"),
                                n_("Entries REGEX (HTML)"), n_("Title REGEX (HTML)"), n_("Link REGEX (HTML)"), n_("Description REGEX (HTML)"), n_("Author REGEX (HTML)"), n_("Category REGEX (HTML)"), 
                                n_("Additional Text REGEX (HTML)"), n_("Image extraction REGEX (HTML)"), n_("Published date REGEX (HTML)"),
                                n_("Published date - Feed REGEX (HTML)"), n_("Image/Icon - Feed REGEX (HTML)"), n_("Title REGEX - Feed (HTML)"), n_("Charset REGEX - Feed (HTML)"), 
                                n_("Lang REGEX - Feed (HTML)"), n_("Script file"), n_("Icon name"), n_("Display Order"))


FEEDS_SHORT_PRINT      = ("ID", "Name", "Title", "Subtitle", "Category", "Tags", "Publisher", "Author", "Home link", "URL", "Feedex Category", "Deleted?", "User Agent", "Fetch?", "Display Order")
CATEGORIES_PRINT       = ("ID", "Name", "Subtitle","Deleted?","No of Children", "Icon name")





RULES_SQL_TABLE =        ('id','name','type','feed_id','field_id','string','case_insensitive','lang','weight','additive','learned','context_id','flag')
RULES_SQL_TYPES = (int, str, int, int, str,   str, int, str,    float,   int, int, int, int)

RULES_SQL_TABLE_RES = RULES_SQL_TABLE + ('flag_name', 'feed_name', 'field_name', 'query_type', 'matched')


RULES_SQL_TABLE_PRINT =  (n_('ID'), n_('Name'), n_('Type'),n_('Feed ID'), n_('Field ID'), n_('Search string'), n_('Case insensitive?'), n_('Language'), n_('Weight'), 
                            n_('Additive?'), n_('Learned?'), n_('Context Entry ID'), n_('Flag') )

RULES_SQL_TABLE_RES_PRINT = RULES_SQL_TABLE_PRINT + (n_('Flag name'), n_('Feed/Category name'), n_('Field name'), n_('Query Type'), n_('No. of matches'))

PRINT_RULES_SHORT = (n_("ID"), n_("Name"), n_("Search string"), n_("Weight"), n_("Case insensitive?"), n_("Query Type"), n_("Learned?"), n_("Flag name"), n_("Flag"), n_("Field name"), n_("Feed/Category name"),)
PRINT_RULES_FOR_ENTRY = (n_("Name"), n_("Search string"), n_("No. of matches"), n_("Weight"), n_("Case insensitive?"), n_("Query Type"), n_("Learned?"), n_("Flag name"), n_("Flag"), n_("Field name"), n_("Feed/Category name"), n_('Context Entry ID'),)

RULES_TECH_LIST = ('learned','context_id',)



LING_TEXT_LIST = ('title','desc','tags','category','text', 'author', 'publisher', 'contributors')
REINDEX_LIST = LING_TEXT_LIST + ('adddate','pubdate','feed_id','flag','read','note','deleted','handler')
ENTRIES_TECH_LIST = ('sent_count','word_count','char_count','polysyl_count','com_word_count','numerals_count','caps_count','readability','weight','importance','adddate','adddate_str','ix_id')


HISTORY_SQL_TABLE = ('id', 'string', 'feed_id', 'date')
HISTORY_SQL_TYPES = (int, str, int, int)

FLAGS_SQL_TABLE = ('id', 'name', 'desc', 'color', 'color_cli')
FLAGS_SQL_TABLE_PRINT = (n_('ID'), n_('Name'), n_('Description'), n_('GUI display color'), n_('CLI display color'))
FLAGS_SQL_TYPES = (int, str, str, str, str)









#Prefix, sql field name, Field name, 
PREFIXES={
'feed_id' :     {'prefix':'',   'sql':'f.id',               'name':_('Feed ID'),        'meta':True,     'weight':1},
'lang' :        {'prefix':'',   'sql':'e.lang',             'name':_('Language'),       'meta':True,     'weight':1},
'author' :      {'prefix':'A',  'sql':'e.author',           'name':_('Author'),         'meta':True,     'weight':2},
'publisher':    {'prefix':'P',  'sql':'e.publisher',        'name':_('Publisher'),      'meta':True,     'weight':1},
'contributors': {'prefix':'B',  'sql':'e.contributors',     'name':_('Contributors'),   'meta':True,     'weight':1},

'title':        {'prefix':'T',  'sql':'e.title',            'name':_('Title'),          'meta':False,     'weight':3},
'desc':         {'prefix':'',   'sql':'e.desc',             'name':_('Description'),    'meta':False,     'weight':1},
'tags':         {'prefix':'G',  'sql':'e.tags',             'name':_('Tags'),           'meta':True,     'weight':2},
'category':     {'prefix':'C',  'sql':'e.category',         'name':_('Category'),       'meta':True,     'weight':2},
'text':         {'prefix':'',   'sql':'e.text',             'name':_('Text'),           'meta':False,     'weight':1},

'div' : 'DIV',   # Divider (perion, parentheses etc.)
'num' : 'NUM',   # Numerals
'cap' : 'CAP',   # Capitalized
'allcap' : 'ALLCAP', # All capitalized
'uncomm' : 'UNCOMM',  # Uncommon word
'polysyl' : 'POLYSYL',  # More than 3 syllables
'curr' : 'CURR', # Currency marker
'math' : 'MATH', #Math symbols
'rnum' : 'RNUM', # Roman numeral
'greek' : 'GREEK', # Greek letter
'unit' : 'UNIT', # Unit symbols

'exact' : 'Z', # Prefix for exact tokens (no stemming)
'sem' : 'XS' # Semantic tokens

}
# Prefixes of meta fields
META_PREFIXES = ('A','P','B','T','G','C')
META_PREFIXES_EXACT = ('AZ','PZ','BZ','TZ','GZ','CZ')
SEM_PREFIXES = ('XS',)
SEM_TERMS = ('DIV','NUM','CAP','ALLCAP','UNCOMM','POLYSYL','CURR','MATH','RNUM','GREEK','UNIT')
BOOLEAN_PREFIXES = ('FEED_ID ', 'UUID ','NOTE ','HANDLER ','READ ')

# Choice of fields for queries and rules
FIELD_CHOICE = {
None:_('All Fields'),
'title'         :PREFIXES['title']['name'], 
'category'      :PREFIXES['category']['name'], 
'tags'          :PREFIXES['tags']['name'], 
'author'        :PREFIXES['author']['name'], 
'publisher'     :PREFIXES['publisher']['name'], 
'contributors'  :PREFIXES['contributors']['name']
}


# Terminal display
if PLATFORM == 'linux':
    TCOLS = {
    'DEFAULT'    : '\033[0m',
    'WHITE'      : '\033[0;37m',
    'WHITE_BOLD' : '\033[1;37m',
    'YELLOW'     : '\033[0;33m',
    'YELLOW_BOLD': '\033[1;33m',
    'CYAN'       : '\033[0;36m',
    'CYAN_BOLD'  : '\033[1;36m',
    'BLUE'       : '\033[0;34m',
    'BLUE_BOLD'  : '\033[1;34m',
    'RED'        : '\033[0;31m',
    'RED_BOLD'   : '\033[1;31m',
    'GREEN'      : '\033[0;32m',
    'GREEN_BOLD' : '\033[1;32m',
    'PURPLE'     : '\033[0;35m',
    'PURPLE_BOLD': '\033[1;35m',
    'LIGHT_RED'  : '\033[0;91m',
    'LIGHT_RED_BOLD' : '\033[1;91m'
    }



TERM_NORMAL = TCOLS['DEFAULT']
TERM_BOLD   = TCOLS['WHITE_BOLD']
TERM_ERR = TCOLS['LIGHT_RED']
TERM_ERR_BOLD = TCOLS['LIGHT_RED_BOLD']

TERM_FLAG = TCOLS['YELLOW_BOLD']
TERM_READ = TCOLS['WHITE_BOLD']
TERM_DELETED = TCOLS['RED']
TERM_SNIPPET_HIGHLIGHT = TCOLS['CYAN_BOLD']

BOLD_MARKUP_BEG = '<b>'
BOLD_MARKUP_END = '</b>'


DEFAULT_CONFIG = {
            'log' : os.path.join(FEEDEX_SHARED_PATH, 'feedex.log'), 
            'db_path' : os.path.join(FEEDEX_SHARED_PATH, 'feedex.db'),
            'browser' : FEEDEX_DEFAULT_BROWSER,
            'lang' : 'en',
            'user_agent' : FEEDEX_USER_AGENT,
            'fallback_user_agent' : None, 
            'timeout' : 15,
            'default_interval': 45,
            'error_threshold': 5,
            'max_items_per_transaction': 300,
            'ignore_images' : False,
            'ignore_media' : False,
            'rule_limit' : 50000,
            'use_keyword_learning' : True,
            'use_search_habits' : True,
            'learn_from_added_entries': True,
            'no_history': False,
            'default_entry_weight' : 2,
            'default_rule_weight' : 2,
            'query_rule_weight' : 10,
            'default_similarity_limit' : 20,
            'default_depth' : 5,
            'do_redirects' : True,
            'save_perm_redirects': False,
            'mark_deleted' : False,
            'ignore_modified': True,
            
            'gui_desktop_notify' : True, 
            'gui_fetch_periodically' : False,
            'gui_notify_group': 'feed',
            'gui_notify_depth': 5,

            'gui_new_color' : '#0FDACA',
            'gui_deleted_color': 'grey',
            'gui_hilight_color' : 'blue',
            'gui_default_flag_color' : 'blue',

            'gui_layout' : 0,
            'gui_orientation' : 0,

            'window_name_exclude' : 'Firefox,firefox,chrome,Chrome,Mozilla,mozilla,Thunderbird,thunderbird',

            'imave_viewer': '',
            'text_viewer' : '',
            'search_engine': 'https://duckduckgo.com/?t=ffab&q=%Q&ia=web',
            'gui_clear_cache' : 30,
            'gui_key_search': 's',
            'gui_key_new_entry': 'n',
            'gui_key_new_rule': 'r',

            'normal_color' : 'DEFAULT',
            'flag_color': 'YELLOW_BOLD',
            'read_color': 'WHITE_BOLD',
            'bold_color': 'WHITE_BOLD',
            'bold_markup_beg': '<b>',
            'bold_markup_end': '</b>'


}

CONFIG_NAMES = {
            'log' : _('Log file'),
            'db_path' : _('Feedex database'),
            'browser' : _('Browser command'),
            'lang' : _('Language'),
            'user_agent': _('User Agent String'),
            'fallback_user_agent': _('Fallback User Agt.'),
            'timeout' : _('Database timeout'),
            'default_interval': _('Default Channel check interval'),
            'error_threshold': _('Channel error threshold'),
            'max_items_per_transaction': _('Max items for a single transaction'),
            'ignore_images' : _('Ignore image processing'),
            'ignore_media' : _('Ignore handling media'),
            'rule_limit' : _('Limit for rules'),
            'use_keyword_learning' : _('Use keyword learning'),
            'use_search_habits' : _('Use search habits'),
            'no_history' : _('Do not save queries in History'),
            'learn_from_added_entries': _('Learn from added Entries'),
            'default_entry_weight' : _('Default Entry weight'),
            'default_rule_weight' : _('Default Rule weight'),
            'query_rule_weight' : _('Default Rule wieght (query)'),
            'default_similarity_limit' : _('Max similar items'),
            'default_depth' : _('Default grouping depth'),
            'do_redirects' : _('Do HTTP redirects'),
            'save_perm_redirects' : _('Save permanent HTTP redirects'),
            'mark_deleted' : _('Mark deleted RSS channels as unhealthy'),
            'do_redirects' : _('Do HTTP redirects'),

            'ignore_modified': _('Ignore MODIFIED and ETag tags'),
            
            'gui_desktop_notify' : _('Push desktop notifications for new items'), 
            'gui_fetch_periodically' : _('Fetch news periodically'),
            'gui_notify_group': _('Notification grouping'),
            'gui_notify_depth': _('Notification depth'),

            'gui_new_color' : _('New item color'),
            'gui_deleted_color': _('Deleted item color'),
            'gui_hilight_color' : _('Search hilight color'),
            'gui_default_flag_color' : _('Default Color for Flags'),

            'gui_layout' : _('GUI pane layout'),
            'gui_orientation' : _('GUI pane orientation'),

            'window_name_exclude' : _('Phrases to exclude from window name'),

            'imave_viewer': _('Image viewer command'),
            'text_viewer': _('Text File viewer command'),
            'search_engine': _('Search Engine to use in GUI'),
            'gui_clear_cache' : _('Clear image cache after n days'),
            'gui_key_search': _('New Search shortkut key'),
            'gui_key_new_entry': _('New Entry shortcut key'),
            'gui_key_new_rule': _('New Rule shortcut key'),

            'normal_color' : _('CLI normal color'),
            'flag_color': _('CLI default flagged color'),
            'read_color': _('CLI read color'),
            'bold_color': _('CLI bold style'),
            'bold_markup_beg': _('Bold section beginning markup'),
            'bold_markup_end': _('Bold section end markup')
}


CONFIG_INTS_NZ=('timeout','notify_level','default_interval','error_threshold','max_items_per_transaction', 'default_similarity_limit')
CONFIG_INTS_Z=('rule_limit','gui_clear_cache','default_depth','gui_layout','gui_orientation','gui_notify_depth')

CONFIG_FLOATS=('default_entry_weight', 'default_rule_weight', 'query_rule_weight' )

CONFIG_STRINGS=('log','db_path','browser','lang','user_agent', 'fallback_user_agent', 'gui_notify_group', 'window_name_exclude', \
    'gui_new_color','gui_deleted_color', 'gui_hilight_color', 'gui_default_flag_color' ,'imave_viewer','text_viewer','search_engine','bold_markup_beg','bold_markup_end')
CONFIG_KEYS=('gui_key_search','gui_key_new_entry', 'gui_key_new_rule')

CONFIG_BOOLS=('notify','ignore_images', 'ignore_media', 'use_keyword_learning', 'learn_from_added_entries','do_redirects','ignore_modified','gui_desktop_notify',
'gui_fetch_periodically', 'use_search_habits', 'save_perm_redirects', 'mark_deleted', 'no_history')

CONFIG_COLS=('normal_color','flag_color','read_color','bold_color')




# Exceptions
class FeedexTypeError(Exception):
    def __init__(self, *args):
        if args: self.message = args[0]
        else: self.message = None

    def __str__(self):
        print(f'Type invalid! {self.message}')









class FeedexMainDataContainer:
    """ Main Container class for Feedex """    
    def __init__(self, **kargs):

        # Data edit lock
        self.__dict__['lock'] = threading.Lock()

        # Global configuration
        self.__dict__['config'] = kargs.get('config', DEFAULT_CONFIG)

        # Language models
        self.__dict__['lings'] = None
        
        # DB stuff
        self.__dict__['feeds'] = []
        self.__dict__['rules'] = []
        self.__dict__['search_history'] = []
        self.__dict__['flags'] = {}

        self.__dict__['doc_count'] = None
        self.__dict__['avg_weight'] = None
        self.__dict__['fetches'] = None


        # GUI stuff
        self.__dict__['icons'] = {}

        # Local DB lock
        self.__dict__['db_lock'] = False

        # Connection counter
        self.__dict__['conns'] = 0

        # Main return status
        self.__dict__['ret_status'] = 0

        # Flags
        self.__dict__['rules_validated'] = False



    def __setattr__(self, __name: str, __value) -> None:
        """ Setter with lock """
        self.lock.acquire()
        self.__dict__[__name] = __value
        self.lock.release()






# Our modules
from feedex_nlp_data import *
from feedex_utils import *
from feedex_feed import SQLContainer, SQLContainerEditable, FeedContainerBasic, FeedContainer
from smallsem import SmallSem
from feedex_nlp import FeedexLP
from feedex_entry import EntryContainer, ResultContainer
from feedex_rule import RuleContainerBasic, RuleContainer, FlagContainerBasic, FlagContainer, HistoryItem
from feedex_handlers import FeedexRSSHandler, FeedexHTMLHandler, FeedexScriptHandler
from feeder_query_parser import FeederQueryParser
from feeder import Feeder

