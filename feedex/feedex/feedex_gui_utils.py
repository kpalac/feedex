# -*- coding: utf-8 -*-
""" GUI classes for FEEDEX """

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GObject, Gdk, Pango, GLib

from PIL import Image, UnidentifiedImageError
from io import BytesIO

from feedex_headers import *





# Constants for Feedex GUI



# Plugin consts
FX_PLUGIN_RESULT = 1
FX_PLUGIN_ENTRY = 2
FX_PLUGIN_SELECTION = 9
FX_PLUGIN_FEED = 11
FX_PLUGIN_CATEGORY = 12
FX_PLUGIN_RESULTS = 20

FX_PLUGIN_TABLE = ('id', 'type', 'name', 'command', 'desc',)
FX_PLUGIN_TABLE_PRINT = (_('ID'), _('Type'), _('Name'), _('Command'), _('Description'),)
FX_PLUGIN_TABLE_TYPES = (int, int, str, str, str,)

if PLATFORM == 'linux':
    FX_DEFAULT_PLUGINS = (
        (1, FX_PLUGIN_SELECTION, _("Search Wikipedia"), f"xdg-open https://en.wikipedia.org/w/index.php?search=%S&title=Special%3ASearch&ns0=1", _("Search Wikipedia for selected text")),
        (2, FX_PLUGIN_SELECTION, _("Search Google"), f"xdg-open https://www.google.com/search?q=%S", _("Search Google for selected text")),
    )





FEEDEX_GUI_VALID_KEYS='qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM1234567890'


FEEDEX_GUI_USER_AGENTS=(
"UniversalFeedParser/5.0.1 +http://feedparser.org/",
"Mozilla/5.0 (X11; Linux x86_64; rv:10.0) Gecko/20100101 Firefox/10.0",
"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36",
"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36 Edg/97.0.1072.62",
"curl/7.75.0",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15",
)

FEEDEX_GUI_SEARCH_ENGINES=(
"https://duckduckgo.com/?t=ffab&q=%Q&ia=web",
"https://www.google.com/search?q=%Q",
"https://www.bing.com/search?q=%Q",
"https://search.yahoo.com/search?p=%Q",
"https://yandex.com/search/?text=%Q",
)


FEEDEX_GUI_ICONS=('rss','www','script','mail','twitter','calendar','document','ok','edit','comment','warning','archive','bookmark','hand','heart','link',
                  'money', 'violence', 'no_violence', 'community', 'terminal', 'dev', 'education', 'electronics','game','image','health','media',
                  'science','utils','bug','toolkit','radio','google','player','audio','weather','notes','lightbulb', 'travel', 'sport','surprise',
                  'markup', 'law', 'python', 'database', 'card', 'avatar', 'cert', 'shield', 'sun', 'night', 'voltage', 'clouds', 'rain', 'disk',)






# Attribute mnemonics
FX_ATTR_ELL_NONE = Pango.EllipsizeMode.NONE
FX_ATTR_ELL_START = Pango.EllipsizeMode.START
FX_ATTR_ELL_MIDDLE = Pango.EllipsizeMode.MIDDLE
FX_ATTR_ELL_END = Pango.EllipsizeMode.END

FX_ATTR_JUS_LEFT = Gtk.Justification.LEFT
FX_ATTR_JUS_CENTER = Gtk.Justification.CENTER
FX_ATTR_JUS_RIGHT = Gtk.Justification.RIGHT
FX_ATTR_JUS_FILL = Gtk.Justification.FILL


# Tab IDs
FX_TAB_PLACES = 0
FX_TAB_SEARCH = 1
FX_TAB_CONTEXTS = 2
FX_TAB_TERM_NET = 3
FX_TAB_TIME_SERIES = 4
FX_TAB_RULES = 5
FX_TAB_SIMILAR = 6
FX_TAB_REL_TIME = 7
FX_TAB_FEEDS = 8
FX_TAB_PREVIEW = 9
FX_TAB_FLAGS = 10
FX_TAB_TREE = 11
FX_TAB_NOTES = 12
FX_TAB_MAP = 13
FX_TAB_TRENDS = 14
FX_TAB_PLUGINS = 15
FX_TAB_LEARNED = 16
FX_TAB_CATALOG = 17

# Tab type compatibility sets
FX_TT_ENTRY = (FX_TAB_PLACES, FX_TAB_SEARCH, FX_TAB_NOTES, FX_TAB_SIMILAR, FX_TAB_TREE,)


# Places IDs
FX_PLACE_LAST = 1
FX_PLACE_PREV_LAST = 2
FX_PLACE_TRASH_BIN = 3

FX_PLACE_LAST_HOUR = 11
FX_PLACE_TODAY = 12
FX_PLACE_LAST_WEEK = 13
FX_PLACE_LAST_MONTH = 14
FX_PLACE_LAST_QUARTER = 15
FX_PLACE_LAST_SIX_MONTHS = 16
FX_PLACE_LAST_YEAR = 17

FX_PLACE_ALL_CHANNELS = 18

# Action IDs
FX_ACTION_EDIT = 1
FX_ACTION_ADD = 2
FX_ACTION_BLOCK_FETCH = 3
FX_ACTION_UNBLOCK_FETCH = 4
FX_ACTION_RELOAD_FEEDS = 5
FX_ACTION_BLOCK_DB = 6
FX_ACTION_UNBLOCK_DB = 7
FX_ACTION_DELETE = 8
FX_ACTION_HANDLE_IMAGES = 9
FX_ACTION_FINISHED_SEARCH = 10
FX_ACTION_FINISHED_FILTERING = 11

# Preview IDs
FX_PREV_STARTUP = 0
FX_PREV_ENTRY = 1
FX_PREV_RULE = 2
FX_PREV_FLAG = 3
FX_PREV_PLUGIN = 4
FX_PREV_CATALOG = 5
FX_PREV_FEED = 6

# Default column layouts for tabs
FX_DEF_LAYOUTS = {
'entries' : (('pubdate_short',100),('title',650),('feed_name',200),('desc',650),('author',200),('flag_name',100),
             ('category',150),('tags',150),('read',50), ('importance',50),('readability',50),('weight',50),('word_count',50),
             ('adddate_str',70), ('pubdate_str',70), ('publisher',150),('link',150), ('rank',50),('count',50),),

'tree' : (('pubdate_short',100),('title',650),('feed_name',200),('desc',650),('author',200),('flag_name',100),
             ('category',150),('tags',150),('read',50), ('importance',50),('readability',50),('weight',50),('word_count',50),('rank',50),
             ('count',50),('adddate_str',70), ('pubdate_str',70), ('publisher',150),('link',150),),

'notes' : ( ('pubdate_short',100), ('entry',650), ('feed_name',200),  ('author',200), ('category',150),('tags',150),
                   ('read',50), ('importance',50),('readability',50),('weight',50),('word_count',50),('rank',50), ('count',50),
                   ('adddate_str',70), ('pubdate_str',70), ('publisher',150),('link',150),),

'contexts' : (('pubdate_short',100),('context',700),('feed_name',200),('title',650),('desc',650),('author',200),('flag_name',100),
             ('category',150),('tags',150),('sread',50), ('importance',50),('readability',50),('weight',50),('word_count',50),('rank',50),
             ('count',50),('adddate_str',70), ('pubdate_str',70), ('publisher',150),('link',150),),

'terms' : (('term',200), ('weight',100)),

'time_series' : (('time',200), ('gui_plot',650), ('freq',70) ),

'rules' : (('name',250), ('string',250), ('weight',70), ('scase_insensitive',50), ('query_type',70), ('flag_name',70),('field_name',100),('feed_name',400),  ),

'flags' : (('id',30), ('name',200), ('desc',700),),

'keywords_learned' : (('form',150), ('weight',150), ('term',150), ('model', 70),),

'plugins' : (('id',30), ('name',200), ('type',150), ('command',450), ('desc',300)),

'catalog' : (('name',200), ('desc',400), ('location',150), ('tags',150), ('freq',70), ('popularity',40),  ('link_res',200), ('link_home',200),),

}


# Search consts
FEEDEX_GUI_DEFAULT_SEARCH_FIELDS = {  
'field': None, 
'feed_or_cat' : None,
'last': True,
'qtype': 1,
'exact': False,
'group': 'daily', 
'lang': None,
'hadler': None,
'logic' : 'any',
'page' : 1,
'page_len' : 1000,
}


FEEDEX_FILTERS_PER_TABS = {

FX_TAB_PLACES : {},
FX_TAB_RULES : {},
FX_TAB_FLAGS : {},
FX_TAB_PLUGINS : {},
FX_TAB_LEARNED: {},

FX_TAB_SEARCH :         {'search':'combo',  'filters': ('time', 'rank', 'read', 'flag', 'notes', 'case', 'field', 'logic', 'type', 'lang', 'handler', 'cat', 'page',) },
FX_TAB_NOTES :          {'search':'combo',  'filters': ('time', 'rank', 'read', 'flag', 'notes', 'case', 'field', 'logic', 'type', 'lang', 'handler', 'cat', 'page',) },
FX_TAB_TREE :           {'search':'combo',  'filters': ('time', 'group', 'depth', 'rank', 'read', 'flag', 'notes', 'case', 'field', 'logic', 'type', 'lang', 'handler', 'cat',) },
FX_TAB_TIME_SERIES :    {'search':'combo',  'filters': ('time', 'time_series', 'read', 'flag', 'notes', 'case', 'field', 'logic', 'type', 'lang', 'handler', 'cat',) },
FX_TAB_TERM_NET :       {'search':'combo',  'filters': ('time', 'read', 'flag', 'notes', 'case', 'field', 'logic', 'type', 'lang', 'handler', 'cat',) },
FX_TAB_TRENDS :         {'search':'combo',  'filters': ('time', 'read', 'flag', 'notes', 'case', 'field', 'logic', 'type', 'lang', 'handler', 'cat',) },
FX_TAB_CONTEXTS :       {'search':'combo',  'filters': ('time', 'read', 'flag', 'notes', 'case', 'field', 'logic', 'type', 'lang', 'handler', 'cat', 'page',) },

FX_TAB_SIMILAR :        {'search':'button', 'filters': ('time', 'depth', 'read', 'flag', 'notes', 'handler', 'cat',) },
FX_TAB_REL_TIME :       {'search':'button', 'filters': ('time', 'group', 'read', 'flag', 'notes', 'handler', 'cat',) },

FX_TAB_CATALOG :        {'search':'catalog_combo',  'filters': ('catalog_field',) },

}






# HTML REGEX templates
FEEDEX_REGEX_HTML_TEMPLATES = {
1: {'name':f"""{_('Template')}: Soundcloud""",
    'rx_title_feed': """<title>(.*?)</title>""", 
    'rx_pubdate_feed': """<meta property="article:modified_time" content="(.*?)" />""",
    'rx_image_feed': """<meta name="msapplication-TileImage" content="(.*?)">""",
    'rx_charset_feed': """<meta charset="(.*?)">""",
    'rx_lang_feed': """<html lang="(.*?)\"""",
    'rx_entries': """<article class="audible"(.*?)</article>""",
    'rx_title': """<a itemprop=.*?>(.*?)</a>""",
    'rx_link': """href="(.*?)\"""",
    'rx_pubdate': """<time pubdate>(.*?)</time>"""
    },
2: {'name':f"""{_('Template')}: NY Review of Books""",
    'rx_title_feed': """<title>(.*?)</title>""", 
    'rx_pubdate_feed': """<meta property="article:modified_time" content="(.*?)" />""",
    'rx_image_feed': """<link rel="icon" href="(.*?)"/>""",
    'rx_charset_feed': """<meta.*charset=(.*?)" />""",
    'rx_lang_feed': """<html lang="(.*?)\"""",
    'rx_entries': """<article class=""(.*?)/article>""",
    'rx_title': """<p class=".*?block.*?">(.*?)</p>""",
    'rx_link': """<a href="(.*?)\"""",
    'rx_desc': """<p class="text.*?">(.*?)</p>""",
    'rx_images': """(<img src=".*?" class=".*?" alt=".*?">)""",
    'rx_author': """<span class="text-small.*?">(.*?)</span>"""
    },
3: {'name':f"""{_('Template')}: The Baffler""",
    'rx_title_feed': """<title>(.*?)</title>""", 
    'rx_pubdate_feed': """<meta property="article:modified_time" content="(.*?)" />""",
    'rx_image_feed': """<meta property="og:image" content="(.*?)" />""",
    'rx_charset_feed': """<meta charset="(.*?)">""",
    'rx_lang_feed': """<meta property="og:locale" content="(.*?)" />""",
    'rx_entries': """<article class="(.*?<article>.*?</article>.*?)/article>""",
    'rx_title': """<img class=".*?alt="(.*?)".*?/>""",
    'rx_link': """<a href="(.*?)\"""",
    'rx_desc': """</article></div>.*?<div class=".*?<a href=".*?">(.*?)</a>""",
    'rx_images': """(<img class=".*?/>)""",
    'rx_author': """<article>.*?<a href=".*?">(.*?)</a>.*?</article></div>"""
    },
4: {'name':f"""{_('Template')}: The Walrus Canada""",
    'rx_title_feed': """<title>(.*?)</title>""", 
    'rx_pubdate_feed': """<meta property="article:modified_time" content="(.*?)" />""",
    'rx_image_feed': """<meta property="og:image" content="(.*?)" />""",
    'rx_charset_feed': """<meta charset="(.*?)">""",
    'rx_lang_feed': """<html lang="(.*?)\"""",
    'rx_entries': """<div class="su-column(.*?)</ul></div></div>""",
    'rx_title': """<a class="title".*?>(.*?)</a>""",
    'rx_link': """<a class="title" href="(.*?)\"""",
    'rx_desc': """<span class="excerpt">(.*?)</span>""",
    'rx_images': """<a class="image".*?data-src="(.*?)".*?</a>""",
    'rx_author': """<span class="author">(.*?)</span>"""
    },
5: {'name':f"""{_('Template')}: China Gov News CGTN""",
    'rx_title_feed': """<title>(.*?)</title>""", 
    'rx_pubdate_feed': """""",
    'rx_image_feed': """<meta property="og:image" content="(.*?)" />""",
    'rx_charset_feed': """<meta charset="(.*?)">""",
    'rx_lang_feed': """<html lang="(.*?)\"""",
    'rx_entries': """(<a href=".*?/news/.*?data-action="News_Click".*?data-news-id="[a-zA-Z1-9].*?</a>)""",
    'rx_title': """(?:data-label="|target="_self">)(.*?)(?:"|</a>)""",
    'rx_link': """<a href="(.*?)\"""",
    'rx_desc': """""",
    'rx_images': """<img.*?data-src="(.*?)\"""",
    'rx_pubdate': """data-time="(.*?)\""""
    },
6: {'name':f"""{_('Template')}: Open AI Blog""",
    'rx_title_feed': """<title>(.*?)</title>""", 
    'rx_pubdate_feed': """<meta property="article:modified_time" content="(.*?)" />""",
    'rx_image_feed': """<meta property="og:image" content="(.*?)" />""",
    'rx_charset_feed': """<meta charset="(.*?)\"""",
    'rx_lang_feed': """<html lang="(.*?)\"""",
    'rx_entries': """<div class="row">(.*?)</ul>""",
    'rx_title': """<h5 class=".*?"><a href=".*?">(.*?)</a></h5>""",
    'rx_link': """<h5 class=".*?"><a href="(.*?)">.*?</a></h5>""",
    'rx_pubdate': """<time datetime="(.*?)">"""
    }

}


FEEDEX_REGEX_HTML_TEMPLATES_SHORT = {
1: {'name': f"""{_('Template')} 1""",
    'rx_images': """<img.*?src="(.*?)".*?>""",
    'rx_link': """<href.*?"(.*?)".*?>"""
    }

}







#####################################################################################
# GUI objects assembly methods



def f_pack_page(fields:list):
    """ Wrapper for building page of lower notebook widget (preview result) """
    page = Gtk.ScrolledWindow()
    page.set_placement(Gtk.CornerType.TOP_LEFT)
    vbox = Gtk.Box()
    vbox.set_border_width(8)
    vbox.set_orientation(Gtk.Orientation.VERTICAL)
    vbox.set_homogeneous(False) 
    for f in fields:
        vbox.pack_start(f, False, True, 5)
    page.add(vbox)
    return page




def f_label(text:str, **kargs):
    """ Build a label quickly """
    label = Gtk.Label()

    if kargs.get('markup',False): label.set_markup(coalesce(text,''))
    else: label.set_text(coalesce(text,''))

    label.set_justify( kargs.get('justify', FX_ATTR_JUS_LEFT) )  
    label.set_xalign(kargs.get('xalign', 0))   
    
    label.set_selectable(kargs.get('selectable',False))
    label.set_line_wrap(kargs.get('wrap',True))
    if kargs.get('char_wrap',False): label.set_line_wrap_mode(Gtk.WrapMode.CHAR)
    label.set_ellipsize( kargs.get('ellipsize', FX_ATTR_ELL_NONE) )

    return label








def f_list_store(store):
    """ Create list store from given list or tuple """
    sample = store[-1]
    types = []

    sample_type = type(sample)
    if sample_type in (list, tuple):
        for f in sample:
            types.append(type(f))

    else:
        types = []
        types.append(sample_type)

    list_store = Gtk.ListStore()
    list_store.set_column_types(types)

    for r in store: list_store.append(r)

    return list_store



def f_dual_combo(store, **kargs):
    """ Construct dual combo from store """
    start_at = kargs.get('start_at')
    color = kargs.get('color', False)
    icon = kargs.get('icon',False)
    style = kargs.get('style',False)
    tooltip = kargs.get('tooltip')
    connect = kargs.get('connect')

    list_store = f_list_store(store)
    combo = Gtk.ComboBox.new_with_model(list_store)
 
    rend = Gtk.CellRendererText()
    if kargs.get('ellipsize', True): rend.props.ellipsize = FX_ATTR_ELL_START
 
    combo.pack_start(rend, True)
    combo.add_attribute(rend, 'text', 1)
 
    if color: combo.add_attribute(rend, 'foreground', 2)
    elif style: combo.add_attribute(rend, 'weight', 2)

    if tooltip is not None: combo.set_tooltip_markup(tooltip)

    if start_at is not None:
        for ix, s in enumerate(store):
            if start_at == s[0]: 
                combo.set_active(ix)
                break
    else: combo.set_active(0)

    if connect is not None: combo.connect('changed', connect)

    return combo






def f_combo_with_icons(store, **kargs):
    """ Generic combo with icons """
    tooltip = kargs.get('tooltip')
    style = kargs.get('style',False)
    
    combo = Gtk.ComboBox()
    text_rend = Gtk.CellRendererText()
    icon_rend = Gtk.CellRendererPixbuf()
    combo.pack_start(icon_rend, False)
    combo.pack_start(text_rend, True)
    combo.add_attribute(text_rend, 'text', 2)
    combo.add_attribute(icon_rend, 'pixbuf', 1)
    if style: combo.add_attribute(text_rend, 'weight', 3)
    combo.set_model(store)

    if tooltip is not None: combo.set_tooltip_markup(tooltip)
    if kargs.get('ellipsize', True): text_rend.props.ellipsize = FX_ATTR_ELL_START
    if kargs.get('color', False): combo.add_attribute(text_rend, 'foreground', 3)

    return combo






def f_user_agent_combo(**kargs):
    """ Construct combo with entry for custom User Agents"""
    tooltip = kargs.get('tooltip',f"""{_('Sometimes it is needed to change user anger tag if the publisher does not allow download (e.g. 403 HTTP response)')}
<b>{_('Changing this tag is not recommended and for debugging purposes only')}</b>""")

    user_agent_store = Gtk.ListStore(str)
    for ua in FEEDEX_GUI_USER_AGENTS: user_agent_store.append((ua,))

    combo = Gtk.ComboBox.new_with_entry()
    combo.set_entry_text_column(0)
    combo.set_model(user_agent_store)

    entry = combo.get_child()
    if tooltip is not None: combo.set_tooltip_markup(tooltip)

    return combo, entry    


def f_search_engine_combo(**kargs):
    """ Construct combo with entry for most common search engines"""
    tooltip = kargs.get('tooltip',_("""Search engine to use for browser searches. Use <b>Q%</b> symbol to substitute for query""") )

    search_engine_store = Gtk.ListStore(str)
    for se in FEEDEX_GUI_SEARCH_ENGINES: search_engine_store.append((se,))

    combo = Gtk.ComboBox.new_with_entry()
    combo.set_entry_text_column(0)
    combo.set_model(search_engine_store)

    entry = combo.get_child()
    if tooltip is not None: combo.set_tooltip_markup(tooltip)

    return combo, entry    









def f_feed_icon_combo(main_win, **kargs):
    """ Construct combo with standard display icons for feeds"""
    tooltip = kargs.get('tooltip', _("""Choose icon for this Channel. Leave empty to diplay downloaded logo, if present""") )
    feed_id = kargs.get('id')
    is_category = kargs.get('is_category', True)

    store = Gtk.ListStore(str, GdkPixbuf.Pixbuf, str)
    
    if is_category: default = 'document'
    else: default = 'rss'

    if feed_id is not None:
        if is_category: pb = main_win.icons.get(feed_id, main_win.icons[default])
        else:
            ico_path = os.path.join(main_win.DB.icon_path, f'feed_{feed_id}.ico')
            if os.path.isfile(ico_path): pb = GdkPixbuf.Pixbuf.new_from_file_at_size( ico_path, 16, 16)
            else: pb = main_win.icons.get(feed_id, main_win.icons[default])
        store.append( ('', pb, f"""  {_('Default')}""") )
    else:
        pb = main_win.icons.get(default)
        store.append( ('', pb, f"""  {_('Default')}""") ) 

    for ico in FEEDEX_GUI_ICONS:
        pb = main_win.icons[ico]
        store.append( (ico, pb, f' {ico}') )
     
    return f_combo_with_icons(store, **kargs)






def f_layout_combo(**kargs):
    """ Construct combo for GUI pane layout options """
    store = (
    (0,_('Vertical panes') ),
    (1,_('Horizontal panes') ),
    (2,_('Horiz. panes, preview on top') ),
    )
    return f_dual_combo(store, **kargs)

def f_orientation_combo(**kargs):
    """ Construct combo for GUI pane orientation """
    store = (
    (0,_('Left to Right') ),
    (1,_('Right to Left') ),
    )
    return f_dual_combo(store, **kargs)


def f_loc_combo(**kargs):
    """ Construct combo for localisation """
    store = (
    (None,_('System default') ),
    ('en','English'),
    )
    return f_dual_combo(store, **kargs)







def f_time_combo(**kargs):
    """ Construct combo for time search filters """
    store = [
    ('last',_('Last Update') ),
    ('last_hour',_('Last Hour') ),
    ('today',_('Today') ),
    ('last_week',_('Week') ),
    ('last_month',_('Month') ),
    ('last_quarter',_('Quarter') ),
    ('last_six_months',_('Six Months') ),
    ('last_year',_('Year') ),
    ('...-...', _('All times')),
    ('choose_dates',_('Choose dates...') ),
    ]
    # Append additional times
    if kargs.get('add') is not None:
        for d in kargs.get('add'): store.append(d)

    return f_dual_combo(store, **kargs)


def f_time_series_combo(**kargs):
    """ Construct combo for time series grouping """
    store = (
    ('monthly',_('Group Monthly') ),
    ('daily',_('Group Daily') ),
    ('hourly',_('Group Hourly') ),
    )
    return f_dual_combo(store, **kargs)

def f_group_combo(**kargs):
    """ Construct combo for tree grouping """
    tmp_store1 = (
    ('category',_('Group by Category') ),
    ('feed',_('Group by Channel') ),
    ('flag',_('Group by Flag') ),
    )
    if kargs.get('with_times',False): 
        tmp_store = tmp_store1 + (
        ('similar',_('Group by Similarity') ),
        ('monthly',_('Group Monthly') ),
        ('daily',_('Group Daily') ),
        ('hourly',_('Group Hourly') ),
        )
    else: tmp_store = tmp_store1
    if kargs.get('with_empty',False): store = ((None, _('No Grouping') ),) + tmp_store
    else: store = tmp_store
    if kargs.get('with_number',False): 
        tmp_store = store
        store =  tmp_store + (('number', _('Just number') ),)

    return f_dual_combo(store, **kargs)

def f_depth_combo(**kargs):
    """ Construct combo for tree grouping depth """
    store = (
    (5,_('Top 5') ),
    (10,_('Top 10') ),
    (15,_('Top 15') ),
    (20,_('Top 20') ),
    (30,_('Top 30') ),
    (50,_('Top 50') ),
    (100,_('Top 100') ),
    (250,_('Top 250') ),
    (9999,_('All') )
    )
    return f_dual_combo(store, **kargs)

FX_RANK_RECOM = 1
FX_RANK_TREND = 2
FX_RANK_LATEST = 3
FX_RANK_DEBUBBLE = 4

def f_rank_combo(**kargs):
    """ Sorting for tree grouping """
    store = (
    (FX_RANK_RECOM,_('Recommended') ),
    (FX_RANK_TREND,_('Trending') ),
    (FX_RANK_LATEST,_('Most Recent') ),
    (FX_RANK_DEBUBBLE,_('"Debubble"') ),
    )
    kargs['tooltip'] = _("""Default ranking/sorting
Use <b>Recommended</b> to rank by most interesting entries for you based on previously read articles
Use <b>Trending</b> to rank by most talked about subjects (<i>time consming for large time ranges</i>)
Use <b>Most Recent</b> to simply sort by date
Use <b>Debubble</b> to show news with the least importance for each grouping""")
    return f_dual_combo(store, **kargs)



def f_read_combo(**kargs):
    """ Constr. combo for read/unread search filters """
    store = (
    ('__dummy', _('Read and Unread') ),
    ('read', _('Read') ),
    ('unread', _('Unread') )
    )
    return f_dual_combo(store, **kargs)



def f_flag_store(**kargs):
    if kargs.get('filters',True):
        store = [
        (None, _("Flagged and Unflagged"), None),
        ('no', _("Unflagged"), None),
        ('all_flags', _("All Flags"), None)]
        for fl in fdx.flags_cache.keys(): store.append( (scast(fl,str,'-1'), fdx.get_flag_name(fl), fdx.get_flag_color(fl) ) )

    else:
        store = [(-1, _("No Flag"), None)]
        for fl in fdx.flags_cache.keys(): store.append( (fl, fdx.get_flag_name(fl), fdx.get_flag_color(fl) ) )
    
    if kargs.get('list_store',False):
        lstore = Gtk.ListStore(str, str, str)
        for si in store: lstore.append(si)
        return lstore
    
    return store


def f_flag_combo(**kargs):
    """ Constr. combo for flag choosers and search filters """
    store = f_flag_store(**kargs)
    kargs['color'] = True
    return f_dual_combo(store, **kargs)





def f_cli_color_combo(**kargs):
    """ Constr. combo for CLI text attributes """
    tooltip = kargs.get('tooltip',_("""Choose color for command line interface """))
    store = []
    for a in TCOLS.keys(): store.append( (a,a.replace('_',' ')) )
    return f_dual_combo(store, tooltip=tooltip, **kargs)





def f_feed_store(main_win, **kargs):
    """ Build store for feeds and categories """
    store = Gtk.ListStore(int, GdkPixbuf.Pixbuf, str, int)

    feed = ResultFeed()
    empty_label = kargs.get('empty_label' , _('-- No Category --'))
    exclude_id = kargs.get('exclude_id')

    if not kargs.get('no_empty',False):
        store.append((-1, None, empty_label, 400))

    if kargs.get('with_templates',False):
        for k,v in FEEDEX_REGEX_HTML_TEMPLATES.items():
            store.append( (-k, main_win.icons.get('markup'), f"""{v.get('name',f'{_("Template")} {k}')}""", 700) )
    elif kargs.get('with_short_templates',False):
        for k,v in FEEDEX_REGEX_HTML_TEMPLATES_SHORT.items():
            store.append( (-k, main_win.icons.get('markup'), f"""{v.get('name',f'{_("Template")} {k}')}""", 700) )

    if kargs.get('with_categories',True):
        for c in fdx.feeds_cache:
            feed.populate(c)
            if feed['is_category'] == 1 and feed['deleted'] != 1 and feed['id'] != exclude_id:
                store.append((feed['id'], main_win.icons.get(feed['id']), feed.name(), 700,))

    if kargs.get('with_feeds',False):
        for f in fdx.feeds_cache:
            feed.populate(f)
            if feed['is_category'] != 1 and feed['deleted'] != 1 and feed['id'] != exclude_id:
                store.append(  (feed['id'], main_win.icons.get(feed['id']), feed.name(), 400,)  )
    return store


def f_feed_combo(main_win, **kargs):
    """ Builds Feed/Category store for combos. This action is often repeated """
    kargs['style'] = True
    store = f_feed_store(main_win, **kargs)
    return f_combo_with_icons(store, **kargs)





def f_handler_combo(**kargs):
    """ Build standard handler combo """
    kargs['tooltip'] = kargs.get('tooltip', _("""Choose Channel's protocol handler:
<b>RSS</b> - use RSS protocol
<b>HTML</b> - download webpage and parse it with defined REGEX rules for each field
<b>Script</b> - fetched by User's script 
<b>Local</b> - no downloads. Can be populated by scripts or command line
using <i>--add-entries</i>, <i>--add-entries-from-file</i>, <i>--add-entries-from-pipe</i> options
""") )
    store = [('rss', _('RSS')), ('html', _('HTML')), ('script', _('Script'))]

    if kargs.get('local',False):
        store.append( ('local', _('Local')) )
    if kargs.get('all', False):
        store.insert(0, (None, _('All handlers')) )

    return f_dual_combo(store, **kargs)







def f_note_combo(**kargs):
    """ Build combo for note/news choice """ 
    if kargs.get('search',True):
        store = (
        (-1, _("Notes and News")),
        (1, _("Notes")),
        (0, _("News"))
    )
    else:
        store = (
        (1, _("Note")),
        (0, _("News Item"))
    )

    return f_dual_combo(store, **kargs)



def f_auth_combo(**kargs):
    """ Build combo for auth methods """ 
    kargs['tooltip'] = kargs.get('tooltip',_("""Chose Channel's authentication method""") )
    store = (
    (None, _('No Authentication') ),
    ('detect', _('Detect Auth. Method') ),
    ('digest', _('Digest') ),
    ('basic', _('Basic') )
    )
    return f_dual_combo(store, **kargs)


def f_query_logic_combo(**kargs):
    """ Build combo for choosing default FTS logical operation """ 
    kargs['tooltip'] = kargs.get('tooltip',_("""Chose default logic operation i.e. how whitespace should work""") )
    store = (
    ('any', _('Any Term') ),
    ('all', _('All Terms') ),
    ('near', _('Terms near') ),
    ('phrase', _('Phrase') )
    )
    return f_dual_combo(store, **kargs)






def f_query_type_combo(**kargs):
    """ Construct combo for choice of query type for search or a rule"""

    if kargs.get('rule',False):
        store = ( (0,_('String matching')), (1,_('Full text matching')), (2,_('REGEX')) )
        kargs['tooltip'] = kargs.get('tooltip',_("""Set query type to match this rule:
<b>String matching</b>: simple string comparison
<b>Full text matching</b>: stemmed and tokenized (no subqueries, logical markers, wildcards or nearness operators)
<b>REGEX</b>: REGEX matching""") )
    else:
        store = ( (1,_('Full Text Search')), (0,_('String matching')) )
        kargs['tooltip'] = kargs.get('tooltip',_("""Set query type:
<b>Full Text Search:</b> stemmed and tokenized (use capitalized terms for exact/unstemmed match)
<b>String matching</b>: simple string comparison""") )

    return f_dual_combo(store, **kargs)





def f_lang_combo(**kargs):
    """ Build combo list of languages """

    kargs['tooltip'] = kargs.get('tooltip', _('Select language used fort query tokenizing and stemming') )

    if kargs.get('with_all',True): store = [(None, _("All Languages"),)]
    else: store = []

    for l in fdx.lings:
        if l['names'][0] != 'heuristic':
            store.append( (l['names'][0], l['names'][0].upper()) )

    return f_dual_combo(store, **kargs)



def f_field_combo(**kargs):
    """ Build field combo """
    all_label = kargs.get('all_label',_('-- All --') )
    store = []
    store.append((None, all_label,))
    for f,p in PREFIXES.items():
        if type(p) is dict:
            if p['prefix'] != '': store.append((f, p['name']))
    
    return f_dual_combo(store, **kargs)




def f_page_len_combo(**kargs):
    """ Construct combo for query page length """
    default = kargs.get('default',0)
    if default != 0 and default not in (500,1000,1500,2000,3000,5000): 
        store = ( (default, str(default))
    (500,_('500') ),
    (1000,_('1000') ),
    (1500,_('1500') ),
    (2000,_('2000') ),
    (3000,_('3000') ),
    (5000,_('5000') ),
    )
    else:
        store = (
    (500,_('500') ),
    (1000,_('1000') ),
    (1500,_('1500') ),
    (2000,_('2000') ),
    (3000,_('3000') ),
    (5000,_('5000') ),
    )

    return f_dual_combo(store, **kargs)





def f_recom_algo_combo(**kargs):
    """ Construct combo for choosing recommendation algo """
    store = (
    (1,_('Similarity')), 
    (2,_('Simil. offset by doc, weight')),
    (3,_('Simil. boosted by readability')),
    )
    tooltip = """Which algorithm should be used when recommending documents?"""
    kargs['tooltip'] = tooltip
    return f_dual_combo(store, **kargs)



def f_plugin_type_combo(**kargs):
    """ Construct combo for plugin context menu type  """
    store = (
    (FX_PLUGIN_RESULT, _('Query result') ),
    (FX_PLUGIN_RESULTS, _('All query results') ),
    (FX_PLUGIN_SELECTION, _('Selected text') ),
    (FX_PLUGIN_FEED, _('Channel') ),
    (FX_PLUGIN_CATEGORY, _('Category') ),
    (FX_PLUGIN_ENTRY, _('Article/Note') ),
    )
    return f_dual_combo(store, **kargs)




def f_catalog_field_combo(**kargs):
    """ Build combo for choosing search fields for feed catalog """ 
    kargs['tooltip'] = kargs.get('tooltip',_("""Chose field to search""") )
    store = (
    (None, _('-- All Fields --')),
    ('name', _('Name') ),
    ('desc', _('Description') ),
    ('location', _('Location') ),
    ('tags', _('Tags') ),
    )
    return f_dual_combo(store, **kargs)







def f_combo_entry(store, **kargs):
    """ Builds an entry with history/options """
    tooltip = kargs.get('tooltip')
    tooltip_button = kargs.get('tooltip_button')
    connect = kargs.get('connect')
    connect_button = kargs.get('connect_button')

    combo = Gtk.ComboBox.new_with_entry()
    combo.set_entry_text_column(0)
    combo.set_model(store)

    entry = combo.get_child()
    entry.set_text(kargs.get('text',''))
    if connect is not None: entry.connect('activate', connect)
    if tooltip is not None: combo.set_tooltip_markup(tooltip)

    entry.set_icon_from_icon_name(1,'edit-clear-symbolic')
    if tooltip_button is not None: entry.set_icon_tooltip_markup(1, tooltip_button)
    if connect_button is not None: entry.connect('icon-press', connect_button)

    return combo, entry









def f_get_combo(combo, **kargs):
    """ Get current combo's ID value (assumed to be the first on the store list) """
    model = combo.get_model()
    active = combo.get_active()
    val = model[active][0]
    if type(val) == int:
        if val == kargs.get('null_val',-1): val = None

    if kargs.get('name',False): 
        if val is None: return None
        else:
            if type(model[active][1]) is str: return model[active][1] 
            else: return model[active][2]
    else: return val



def f_set_combo(combo, val, **kargs):
    """ Set combo to a specified value """
    if val is None: val = kargs.get('null_val', -1)
    model = combo.get_model()
    for i,m in enumerate(model):
        if m[0] == val: 
            combo.set_active(i)
            return 0

    combo.set_active(0)
    return -1


def f_set_combo_from_bools(combo, dc, **kargs):
    """ Set combo given a dictionary (set if value is TRUE)"""
    for k,v in dc.items():
        if type(v) is bool and v is True:
            found = f_set_combo(combo, k, **kargs)
            if found == 0: return 0
    return -1



def f_get_combo_id(combo, id):
    """ Get the combo's element with a given ID (assumed to be the first on the store list)"""
    model = combo.get_model()
    for i,m in enumerate(model):
        if m[0] == id: return i
    return 0             







def f_button(label:str, icon:str, **kargs):
    """ Construct a button :)"""
    if icon is not None: 
        if label is None: button = Gtk.Button.new_from_icon_name( icon, kargs.get('size',Gtk.IconSize.BUTTON) )
        else:
            button = Gtk.Button()
            image = Gtk.Image.new_from_icon_name(icon, kargs.get('size', Gtk.IconSize.BUTTON) )
            image.show()
            text_label = Gtk.Label()
            text_label.set_text(label)
            box = Gtk.HBox()
            box.pack_start(image, False, False, 3)
            box.pack_start(text_label, False, False, 3)
            button.add(box)

    else: button = Gtk.Button.new_with_label(label)

    if kargs.get('tooltip') is not None: button.set_tooltip_markup(kargs.get('tooltip',''))
    if kargs.get('connect') is not None: 
        args = kargs.get('args',[])
        kwargs = kargs.get('kargs')
        if kwargs is not None:
            args = list(args)
            args.append(kwargs)
        button.connect('clicked', kargs.get('connect'), *args)

    return button




def f_set_button_image(button, image_path:str, **kargs):
    """ Set image for f_image_button"""
    if not os.path.isfile(image_path): 
        image = Gtk.Image.new_from_icon_name('image-x-generic-symbolic', Gtk.IconSize.DIALOG)
    else:
        try: pb = GdkPixbuf.Pixbuf.new_from_file_at_size( image_path, 64, 64)
        except Exception as e: return msg(FX_ERROR_IO, _('Error getting image from %a: %b'), image_path, e)
        image = Gtk.Image.new_from_pixbuf(pb)
    
    for c in button.get_children(): button.remove(c)
    button.add(image)
    image.show()
    return 0



def f_image_button(image_path:str, **kargs):
    """ Construct a button with image """
    tooltip = kargs.get('tooltip')
    button = Gtk.Button()
    f_set_button_image(button, image_path)
    if kargs.get('connect') is not None: 
        args = kargs.get('args',[])
        kwargs = kargs.get('kargs')
        if kwargs is not None:
            args = list(args)
            args.append(kwargs)
        button.connect('clicked', kargs.get('connect'), *args)

    return button






def f_col(title:str, ctype:int,  model_col:int, **kargs):
    """ Wrapper for building a TreeVeiw column """
    color_col = kargs.get('color_col')
    attr_col = kargs.get('attr_col')
    ellipsize = kargs.get('ellipsize', FX_ATTR_ELL_END)
    clickable = kargs.get('clickable', True)
    sort_col = kargs.get('sort_col')
    start_width = kargs.get('start_width')
    width = kargs.get('width',16)
    name = kargs.get('name')
    note = kargs.get('note',False)
    yalign = kargs.get('yalign')
    connect = kargs.get('connect')

    if ctype in (0,1):
        renderer = Gtk.CellRendererText()
        if ctype == 0: col = Gtk.TreeViewColumn( title, renderer, text=model_col)
        elif ctype == 1: col = Gtk.TreeViewColumn( title, renderer, markup=model_col)

        if note:
            renderer.props.wrap_width = 650
            renderer.props.wrap_mode = Gtk.WrapMode.WORD
            renderer.props.height = 150
            renderer.props.ellipsize = FX_ATTR_ELL_NONE
            renderer.props.single_paragraph_mode = False
            if yalign is not None: renderer.props.yalign = yalign

        else:
            if ellipsize is not None: renderer.props.ellipsize = ellipsize
        
        if attr_col is not None:  col.add_attribute(renderer, 'weight', attr_col)    
        if color_col is not None: col.add_attribute(renderer, 'foreground', color_col)    


    elif ctype == 3:
        renderer = Gtk.CellRendererPixbuf()
        if yalign is not None: renderer.props.yalign = yalign
        col = Gtk.TreeViewColumn( title, renderer, pixbuf=model_col)

    elif ctype == 4:
        renderer = Gtk.CellRendererToggle()
        if yalign is not None: renderer.props.yalign = yalign
        col = Gtk.TreeViewColumn( title, renderer, active=model_col)
        if connect is not None: renderer.connect('toggled', connect)

    if clickable:
        col.set_clickable(True)
        if sort_col is not None: col.set_sort_column_id(sort_col)    
        else: col.set_sort_column_id(model_col)
    else: col.set_clickable(False)

    col.set_resizable(kargs.get('resizeable',True))
    col.set_reorderable(kargs.get('reorderable',True))

    if width is not None: col.set_min_width(width)
    if start_width is not None: col.props.fixed_width = start_width
    if name is not None: col.set_name(name)
        
    return col







def f_menu_item(item_type:int, label:str, connect, **kargs):
    """ Factory for building menu item """
    icon = kargs.get('icon')
    color = kargs.get('color')
    tooltip = kargs.get('tooltip')
    args = kargs.get('args',[])
    kwargs = kargs.get('kargs')

    if item_type == 0:
        item = Gtk.SeparatorMenuItem()
        return item

    if icon in (None,'') and color in (None,''):
        item = Gtk.MenuItem(label)
    else:
        item = Gtk.MenuItem()

    if color is not None:
        lb = Gtk.Label()
        lb.set_markup(f'<span foreground="{color}">{label}</span>')
        vbox = Gtk.Box()
        vbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        vbox.set_homogeneous(False)
        vbox.pack_start(lb, False, False, 3)
        item.add(vbox)


    elif icon is not None:
        im = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU)     
        im.show()
        lb = Gtk.Label()
        lb.set_text(label)
        vbox = Gtk.Box()
        vbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        vbox.set_homogeneous(False)
        vbox.pack_start(im, False, False, 3)
        vbox.pack_start(lb, False, False, 3)
        item.add(vbox)

    if item_type == 3:
        if connect is not None: item.set_submenu(connect)
        
    elif connect is not None:
        if kwargs is not None: 
            args = list(args)
            args.append(kwargs)
        item.connect('activate', connect, *args)

    if tooltip is not None:
        item.set_tooltip_markup(tooltip)

    return item





def f_imagebox(res, **kargs):
    """ Build a box with image in it provided a dictionary with specs """
    eventbox = Gtk.EventBox()
    try:
        pixb = GdkPixbuf.Pixbuf.new_from_file(res['thumbnail'])
        image = Gtk.Image.new_from_pixbuf(pixb)
    except GLib.Error as e:
        fdx.add_error(res['url'])
        msg(FX_ERROR_HANDLER, _('Image error: %a'), e)
        return None

    build_res_tooltip(res)
    image.set_tooltip_markup(f"""{res.get('tooltip')}Click to open in image viewer""")

    eventbox.add(image)
    image.show()
    eventbox.show()
    return eventbox



def f_chooser(parent, main_win, *args, **kargs):
    """ File chooser for porting """
    action = kargs.get('action', 'open_file')
    start_dir = kargs.get('start_dir')

    if action == 'save':
        header = kargs.get('header',_('Save as...'))
        dialog = Gtk.FileChooserDialog(header, parent=parent, action=Gtk.FileChooserAction.SAVE)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        dialog.set_do_overwrite_confirmation(True)

    elif action == 'open_file':
        header = kargs.get('header',_('Open File'))
        dialog = Gtk.FileChooserDialog(header, parent=parent, action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
    
    elif action == 'open_dir':
        header = kargs.get('header',_('Open Folder'))
        dialog = Gtk.FileChooserDialog(header, parent=parent, action=Gtk.FileChooserAction.SELECT_FOLDER)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
    
    elif action == 'choose_image':
        header = kargs.get('header',_('Choose Image'))
        filter = Gtk.FileFilter()
        filter.set_name(_('Image files'))
        for e in ('png','jpg','jpeg','bmp','jpe','ico','tif','tiff','icon','bitmap','pcx',):
            filter.add_pattern(f'*.{e}')
            filter.add_pattern(f'*.{e.upper()}')

        all_filter = Gtk.FileFilter()
        all_filter.set_name(_('All files'))
        all_filter.add_pattern('*.*')

        dialog = Gtk.FileChooserDialog(header, parent=parent, action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, _('No Image'), Gtk.ResponseType.NO, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        dialog.add_filter(filter)
        dialog.add_filter(all_filter)



    if start_dir is not None: dialog.set_current_folder(start_dir)
    else: dialog.set_current_folder(main_win.gui_cache.get('last_dir', os.getcwd()))
    response = dialog.run()
    if response == Gtk.ResponseType.OK:
        filename = dialog.get_filename()
    elif response == Gtk.ResponseType.NO: filename = -1
    else: filename = False
    dialog.destroy()

    if action == 'save':
        if os.path.isdir(filename):
            msg(FX_ERROR_IO, _('Target %a is a directory!'), filename)
            filename = False

    if filename in ('',None,False,): filename = False
    elif filename != -1: main_win.gui_cache['last_dir'] = os.path.dirname(filename)

    return filename





####################################################################################################
# General GUI Utilities


def save_thumbnail(bin_data, ofile, **kargs):
    """ Saves binary data to thumbnail """
    try:
        img = Image.open(bin_data)
        img.thumbnail((150, 150))
        img.save(ofile, format="PNG")
        return 0
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError, FileNotFoundError, AttributeError) as e:
        return msg(FX_ERROR_HANDLER, _('Error saving thumbnail from %a: %b'), url, e)


def download_thumbnail(url, ofile, **kargs):
    """ Downloads an image from url and saves it to ofile """
    kargs['verbose'] = kargs.get('verbose', False)
    response, bin_data = fdx.download_res(url, mimetypes=FEEDEX_IMAGE_MIMES, output_pipe=BytesIO(), **kargs)
    if response == -3: return -3
    return save_thumbnail(bin_data, ofile, **kargs)


def local_thumbnail(ifile, ofile, **kargs):
    """ Creates thumbnail out of local image """
    bin_data = BytesIO()
    try:
        with open(ifile, 'rb') as f: bin_data.write(f.read())
    except (OSError, IOError,) as e: return msg(FX_ERROR_HANDLER, _('Error creating %a thumbnail for %b: %c'), ofile, ifile, e)
    return save_thumbnail(bin_data, ofile, **kargs)
    



def sanitize_snippet(snip:tuple):
    """ Sanitizes snippet string for output with Pango markup """
    if len(snip) == 3:
        beg = esc_mu(scast(snip[0], str, ''))
        phr = esc_mu(scast(snip[1], str, ''))
        end = esc_mu(scast(snip[2], str, ''))
        return f'{beg}<b>{phr}</b>{end}'
    else:
        return '<???>'    


def image2pixbuf(im):
    """Convert Pillow image to GdkPixbuf"""
    data = im.tobytes()
    w, h = im.size
    data = GLib.Bytes.new(data)
    pix = GdkPixbuf.Pixbuf.new_from_bytes(data, GdkPixbuf.Colorspace.RGB,
            False, 8, w, h, w * 3)
    return pix



def gui_msg(*args, **kargs):
    """ Converts message tuple into a markup """
    code = None
    text = None
    sargs = []
    for a in args:
        if code is None:
            code = a
            continue
        if text is None:
            text = a
            text = text.strip()
            text = esc_mu(text)
            continue
        
        sargs.append(a)
        
        
    for i,a in enumerate(sargs):
        if i == 0: chks = '%a'
        elif i == 1: chks = '%b'
        elif i == 2: chks = '%c'
        elif i == 3: chks = '%d'

        if chks in text: text = text.replace(chks, f'<b>{esc_mu(a)}</b>')
        else: text = f'{text} <b>{esc_mu(a)}</b>'

    text = text.replace('\n',' ')
    text = text.replace('\r',' ')
    
    if code < 0: text = f'<span foreground="red">{text}</span>'
    return text





def esc_mu(string, **kargs):
    """ Convenience wrapper for escaping markup in gui """
    string = scast(string, str, '')
    if kargs.get('ell') is not None: return GObject.markup_escape_text(ellipsize(string, kargs.get('ell'))) 
    else: return GObject.markup_escape_text(string)



def build_res_tooltip(res):
    """ Builds tooltip for res """
    tooltip=''
    if res['title'] != '': tooltip=f"""<b><i>{esc_mu(res['title'])}</i></b>
"""
    if res['alt'] != '': tooltip=f"""{tooltip}<b>{esc_mu(res['alt'])}</b>
"""

    res['tooltip'] = tooltip













#################################################
#       UTILITIES
#

def quick_find_case_ins(self, model, column, key, rowiter, *args):
    """ Guick find 'equals' fundction - case insensitive """
    column=args[-1]
    row = model[rowiter]
    if key.lower() in scast(list(row)[column], str, '').lower(): return False
    return True

def quick_find_case_ins_tree(self, model, column, key, rowiter, *args):
    """ Quick find 'equals' function - basically case insensitivity """
    column = args[-1]
    tree = args[-2]
    row = model[rowiter]
    if key.lower() in scast(list(row)[column], str, '').lower(): return False

    # Search in child rows.  If one of the rows matches, expand the row so that it will be open in later checks.
    for inner in row.iterchildren():
        if key.lower() in scast(list(inner)[column], str, '').lower():
            tree.expand_to_path(row.path)
            return False
    return True








from feedex_desktop_notifier import DesktopNotifier
from feedex_gui_containers import ResultGUI, ResultGUIEntry, ResultGUINote, ResultGUITree, ResultGUIContext, ResultGUIRule, ResultGUIFlag, ResultGUITerm, ResultGUITimeSeries, FeedexPlugin, FeedexCatalogQuery, ResultGUIPlugin, ResultGUICatItem, ResultPlugin, ResultCatItem, ResultGUIKwTerm
from feedex_gui_dialogs_utils import BasicDialog, YesNoDialog, PreferencesDialog, CalendarDialog
from feedex_gui_tabs import FeedexTab, FeedexGUITable
from feedex_gui_feeds import FeedexFeedTab
from feedex_gui_dialogs_entts import NewFromURL, EditCategory, EditEntry, EditFlag, EditPlugin, EditRule, EditFeedRegex, EditFeed
from feedex_gui_actions import FeedexGUIActions






