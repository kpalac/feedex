# -*- coding: utf-8 -*-
""" GUI classes for FEEDEX """

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GObject, Gdk, Pango, GLib

from PIL import Image, UnidentifiedImageError
from io import BytesIO

from feedex_headers import *






if PLATFORM == 'linux':
    FEEDEX_GUI_ATTR_CACHE = os.path.join(FEEDEX_SHARED_PATH, 'feedex_gui_cache.json')


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

# This is needed to ignore downloading useless icons etc.
FEEDEX_GUI_IGNORE_THUMBNAILS=(
'http://feeds.feedburner.com',
)

FEEDEX_GUI_ICONS=('rss','www','script','mail','twitter','calendar','document','ok','edit')






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
FX_TAB_RESULTS = 7
FX_TAB_FEEDS = 8
FX_TAB_REL_TIME = 9
FX_TAB_PREVIEW = 10
FX_TAB_FLAGS = 11
FX_TAB_TREE = 12
FX_TAB_NOTES = 13
FX_TAB_MAP = 14
FX_TAB_TRENDS = 15
FX_TAB_TRENDING = 16

# Tab type compatibility sets
FX_TT_ENTRY = (FX_TAB_PLACES, FX_TAB_SEARCH, FX_TAB_NOTES, FX_TAB_RESULTS, FX_TAB_SIMILAR, FX_TAB_TREE,)


# Places IDs
FX_PLACE_STARTUP = 0
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
FX_ACTION_RELOAD_FEEDS_DB = 6
FX_ACTION_BLOCK_DB = 7
FX_ACTION_UNBLOCK_DB = 8
FX_ACTION_DELETE = 9
FX_ACTION_HANDLE_IMAGES = 10
FX_ACTION_FINISHED_SEARCH = 11
FX_ACTION_FINISHED_FILTERING = 12



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

'rules_rank' : ( ('name',150), ('string',150), ('matched',30), ('slearned',20), ('scase_insensitive',20), ('query_type',100), ('field_name',100),
                 ('feed_name',100), ('lang',50), ('weight',50), ('flag',20), ('flag_name',100), ('sadditive',30), ('context_id',50)  ),

'rules_learned' : (('name',150), ('string',150), ('lang',50), ('weight',50), ('context_id',50)),

'keywords' : (('term',200), ('weight',100), ('search_form',100)),


}





#####################################################################################
# GUI objects factories



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
    label.xalign = kargs.get('xalign', 0)    
    
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


def f_feed_icon_combo(**kargs):
    """ Construct combo with standard display icons for feeds"""
    tooltip = kargs.get('tooltip', _("""Choose icon for this Channel. Leave empty to diplay downloaded logo, if present""") )

    search_engine_store = Gtk.ListStore(str)
    for se in FEEDEX_GUI_ICONS: search_engine_store.append((se,))

    combo = Gtk.ComboBox.new_with_entry()
    combo.set_entry_text_column(0)
    combo.set_model(search_engine_store)

    entry = combo.get_child()
    if tooltip is not None: combo.set_tooltip_markup(tooltip)

    return combo, entry    


def f_layout_combo(**kargs):
    """ Construct combo for GUI pane layout options """
    store = (
    (0,_('Standard') ),
    (1,_('Standard, preview on top') ),
    (2,_('Vertical panes') ),
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


def f_startup_page_combo(**kargs):
    """ Construct combo for GUI startup summary page"""
    store = (
    (0,_('No startup page') ),
    (1,_('Summary by Category') ),
    (2,_('Summary by Channel') ),
    (3,_('Summary by Flag') ),
    (4,_('Restore previous session') ),
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
    (9999,_('All') )
    )
    return f_dual_combo(store, **kargs)

def f_sort_combo(**kargs):
    """ Sorting for tree grouping """
    store = (
    ('+importance',_('Rank by Importance') ),
    ('trends',_('Rank by Trends') ),
    ('+pubdate',_('Sort by Date') ),
    ('-importance',_('"Debubble"') ),
    )
    return f_dual_combo(store, **kargs)



def f_read_combo(**kargs):
    """ Constr. combo for read/unread search filters """
    store = (
    ('__dummy', _('Read and Unread') ),
    ('read', _('Read') ),
    ('unread', _('Unread') )
    )
    return f_dual_combo(store, **kargs)



def f_flag_combo(**kargs):
    """ Constr. combo for flag choosers and search filters """
    if kargs.get('filters',True):
        store = [
        (None, _("Flagged and Unflagged"), None),
        ('no', _("Unflagged"), None),
        ('all_flags', _("All Flags"), None)]
        for fl in fdx.flags_cache.keys(): store.append( (scast(fl,str,'-1'), fdx.get_flag_name(fl), fdx.get_flag_color(fl) ) )

    else:
        store = [(-1, _("No Flag"), None)]
        for fl in fdx.flags_cache.keys(): store.append( (fl, fdx.get_flag_name(fl), fdx.get_flag_color(fl) ) )

    kargs['color'] = True
    return f_dual_combo(store, **kargs)


def f_cli_color_combo(**kargs):
    """ Constr. combo for CLI text attributes """
    tooltip = kargs.get('tooltip',_("""Choose color for command line interface """))
    store = []
    for a in TCOLS.keys(): store.append( (a,a.replace('_',' ')) )
    return f_dual_combo(store, tooltip=tooltip, **kargs)


def f_feed_combo(**kargs):
    """ Builds Feed/Category store for combos. This action is often repeated """
    store = []
    feed = ResultFeed()
    empty_label = kargs.get('empty_label' , _('-- No Category --'))
    exclude_id = kargs.get('exclude_id')

    if not kargs.get('no_empty',False):
        store.append((-1, empty_label, 400))

    if kargs.get('with_templates',False):
        for k,v in FEEDEX_REGEX_HTML_TEMPLATES.items():
            store.append( (-k, f"""{v.get('name',f'{_("Template")} {k}')}""", 700) )
    elif kargs.get('with_short_templates',False):
        for k,v in FEEDEX_REGEX_HTML_TEMPLATES_SHORT.items():
            store.append( (-k, f"""{v.get('name',f'{_("Template")} {k}')}""", 700) )

    if kargs.get('with_categories',True):
        for c in fdx.feeds_cache:
            feed.populate(c)
            if feed['is_category'] == 1 and feed['deleted'] != 1 and feed['id'] != exclude_id:
                store.append((feed['id'], feed.name(), 700,))

    if kargs.get('with_feeds',False):
        for f in fdx.feeds_cache:
            feed.populate(f)
            if feed['is_category'] != 1 and feed['deleted'] != 1 and feed['id'] != exclude_id:
                store.append(  (feed['id'], feed.name(), 400,)  )

    kargs['icons'] = True
    kargs['style'] = True
    return f_dual_combo(store, **kargs)





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


def f_ranking_scheme_combo(**kargs):
    """ Construct combo for query page length """
    store = (
    ('simple',_('Simple')), 
    ('similarity',_('Similarity')) 
    )
    tooltip = """Which ranking algorithm should be used to rank incomming items?
        <b>Simple:</b>  a basic summation on matched rules' weights (may overrank long articles)
        <b>Similarity:</b>  importance by only top matched most similar important entries
    """
    kargs['tooltip'] = tooltip
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
        else: return model[active][1]
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
    if kargs.get('connect') is not None: button.connect('clicked', kargs.get('connect'))

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


    else:
        renderer = Gtk.CellRendererPixbuf()
        if yalign is not None: renderer.props.yalign = yalign
        col = Gtk.TreeViewColumn( title, renderer, pixbuf=model_col)

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






####################################################################################################
# General GUI Utilities


def process_res_links(string:str, cache_path:str):
    """ Extracts elements and generates resource filename for cache """
    if string.strip() == '': return 0
    if string.startswith('http://') or string.startswith('https://'): url = string
    else: url = slist(re.findall(IM_URL_RE, string), 0, None)
    
    # This is to avoid showing icons from feedburner etc.
    if url is None: return 0
    for i in FEEDEX_GUI_IGNORE_THUMBNAILS:
        if url.startswith(i): return 0

    alt = slist(re.findall(IM_ALT_RE, string), 0, '')
    title = slist(re.findall(IM_TITLE_RE, string), 0, '')
    alt = slist( fdx.strip_markup(scast(alt, str, ''), html=True), 0, '')
    title = slist( fdx.strip_markup(scast(title, str,''), html=True), 0, '')
 
    hash_obj = hashlib.sha1(url.encode())
    filename = os.path.join(cache_path, f"""{hash_obj.hexdigest()}.img""")

    tooltip=''
    if title.strip() not in ('',None): tooltip=f"""<b><i>{esc_mu(title)}</i></b>
"""
    if alt.strip() not in ('',None): tooltip=f"""{tooltip}<b>{esc_mu(alt)}</b>"""

    return {'url':url, 'tooltip':tooltip, 'filename':filename, 'title':title, 'alt':alt}



def create_thumbnail(url:str, ofile:str, **kargs):
    """ Save remote resource to a thumbnail file """
    kargs['verbose'] = False
    response, res_data = fdx.download_res(url, mimetypes=FEEDEX_IMAGE_MIMES, output_pipe=BytesIO(), **kargs)
    if response == -3: return -3
    try:
        img = Image.open(res_data)
        img.thumbnail((150, 150))
        img.save(ofile, format="PNG")
        return 0
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError, FileNotFoundError, AttributeError) as e:
        return msg(FX_ERROR_HANDLER, f"""{_('Error saving thumbnail from %a: ')}{e}""")






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




def get_icons(feeds, ficons):
    """ Sets up a dictionary with feed icon pixbufs for use in lists """
    icons = {}
    for f,ic in ficons.items():
        try: icons[f] = GdkPixbuf.Pixbuf.new_from_file_at_size(ic, 16, 16)
        except Exception as e: 
            try: os.remove(ic)
            except OSError as ee: msg(FX_ERROR_IO, f"""_('Error removing %a:'){ee}""", ic)
            msg(FX_ERROR_IO, _('Image error: %a'), e)

    icons['default']  = GdkPixbuf.Pixbuf.new_from_file_at_size(     os.path.join(FEEDEX_SYS_ICON_PATH, 'news-feed.svg'), 16, 16)
    icons['main']  = GdkPixbuf.Pixbuf.new_from_file_at_size(        os.path.join(FEEDEX_SYS_ICON_PATH, 'feedex.png'), 64, 64)
    icons['tray_new']  = GdkPixbuf.Pixbuf.new_from_file_at_size(    os.path.join(FEEDEX_SYS_ICON_PATH, 'tray_new.png'), 64, 64)
    icons['doc'] = GdkPixbuf.Pixbuf.new_from_file_at_size(          os.path.join(FEEDEX_SYS_ICON_PATH, 'document.svg'), 16, 16)
    icons['ok'] = GdkPixbuf.Pixbuf.new_from_file_at_size(           os.path.join(FEEDEX_SYS_ICON_PATH, 'ok.svg'), 16, 16)
    icons['error'] = GdkPixbuf.Pixbuf.new_from_file_at_size(        os.path.join(FEEDEX_SYS_ICON_PATH, 'error.svg'), 16, 16)
    icons['trash'] = GdkPixbuf.Pixbuf.new_from_file_at_size(        os.path.join(FEEDEX_SYS_ICON_PATH, 'trash.svg'), 16, 16)
    icons['calendar'] = GdkPixbuf.Pixbuf.new_from_file_at_size(     os.path.join(FEEDEX_SYS_ICON_PATH, 'calendar.svg'), 16, 16)
    icons['new'] = GdkPixbuf.Pixbuf.new_from_file_at_size(          os.path.join(FEEDEX_SYS_ICON_PATH, 'new.svg'), 16, 16)
    icons['db'] = GdkPixbuf.Pixbuf.new_from_file_at_size(           os.path.join(FEEDEX_SYS_ICON_PATH, 'db.svg'), 64, 64)
    icons['rss'] = GdkPixbuf.Pixbuf.new_from_file_at_size(          os.path.join(FEEDEX_SYS_ICON_PATH, 'news-feed.svg'), 16, 16)
    icons['www'] = GdkPixbuf.Pixbuf.new_from_file_at_size(          os.path.join(FEEDEX_SYS_ICON_PATH, 'www.svg'), 16, 16)
    icons['script'] = GdkPixbuf.Pixbuf.new_from_file_at_size(       os.path.join(FEEDEX_SYS_ICON_PATH, 'script.svg'), 16, 16)
    icons['twitter'] = GdkPixbuf.Pixbuf.new_from_file_at_size(      os.path.join(FEEDEX_SYS_ICON_PATH, 'twitter.svg'), 16, 16)
    icons['disk'] = GdkPixbuf.Pixbuf.new_from_file_at_size(         os.path.join(FEEDEX_SYS_ICON_PATH, 'disk.svg'), 16, 16)
    icons['local'] = GdkPixbuf.Pixbuf.new_from_file_at_size(        os.path.join(FEEDEX_SYS_ICON_PATH, 'local.svg'), 16, 16)
    icons['table'] = GdkPixbuf.Pixbuf.new_from_file_at_size(        os.path.join(FEEDEX_SYS_ICON_PATH, 'table.svg'), 16, 16)
    icons['edit'] = GdkPixbuf.Pixbuf.new_from_file_at_size(         os.path.join(FEEDEX_SYS_ICON_PATH, 'edit.svg'), 16, 16)

    return icons




def gui_msg(*args, **kargs):
    """ Converts message tuple into a markup """
    code = args[0]
    text = args[1]
    arg = slist(args, 2, '')

    text = text.replace('\n',' ')
    text = text.replace('\r',' ')
    text = text.strip()
    text = esc_mu(text)

    if arg is not None:
        arg = arg.replace('\n',' ')
        arg = arg.replace('\r',' ')
        arg =  esc_mu(arg)

    if code < 0: text = f'<span foreground="red">{text}</span>'
    if arg is not None:
        arg = f'<b>{arg}</b>'
        if '%a' in text: text = text.replace('%a',arg)
        else: text = f'{text} <b>{arg}</b>'

    return text





def esc_mu(string, **kargs):
    """ Convenience wrapper for escaping markup in gui """
    string = scast(string, str, '')
    if kargs.get('ell') is not None: return GObject.markup_escape_text(ellipsize(string, kargs.get('ell'))) 
    else: return GObject.markup_escape_text(string)












def validate_gui_cache(gui_attrs):
    """ Validate GUI attributes in case the config file is not right ( to prevent crashing )"""
    
    
    new_gui_attrs = {}
    
    new_gui_attrs['win_width'] = scast(gui_attrs.get('win_width'), int, 1500)
    new_gui_attrs['win_height'] = scast(gui_attrs.get('win_height'), int, 800)
    new_gui_attrs['win_maximized'] = scast(gui_attrs.get('win_maximized'), bool, False)

    new_gui_attrs['div_horiz'] = scast(gui_attrs.get('div_horiz'), int, 400)
    new_gui_attrs['div_vert2'] = scast(gui_attrs.get('div_vert2'), int, 600)
    new_gui_attrs['div_vert'] = scast(gui_attrs.get('div_vert'), int, 350)

    new_gui_attrs['feeds_expanded'] = scast(gui_attrs.get('feeds_expanded',{}).copy(), dict, {})
    for v in new_gui_attrs['feeds_expanded'].values():
        if type(v) is not bool: 
            new_gui_attrs['feeds_expanded'] = {}
            msg(FX_ERROR_VAL, _('Expanded feeds invalid. Defaulting...') )
            break

    new_gui_attrs['layouts'] = scast(gui_attrs.get('layouts'), dict, {})
    if new_gui_attrs['layouts'] == {}:
        msg(FX_ERROR_VAL, _('No valid layouts found. Defaulting...'))
        new_gui_attrs['layouts'] = FX_DEF_LAYOUTS.copy()

    if new_gui_attrs['layouts'].keys() != FX_DEF_LAYOUTS.keys(): 
        msg(FX_ERROR_VAL, _('Invalid layout list. Defaulting...'))
        new_gui_attrs['layouts'] = FX_DEF_LAYOUTS.copy()
    
    for k,v in new_gui_attrs['layouts'].items():
        if type(v) not in (tuple, list) or len(v) == 0:
            msg(FX_ERROR_VAL, _('Invald %a layout. Defaulting...'), k)
            new_gui_attrs['layouts'][k] = FX_DEF_LAYOUTS[k]
            continue

        for i,c in enumerate(v):
            if type(c) not in (tuple, list): 
                msg(FX_ERROR_VAL, _('Invald %a layout. Defaulting...'), k)
                new_gui_attrs['layouts'][k] = FX_DEF_LAYOUTS[k]
                break
            if type(slist(c,0,None)) is not str or type(slist(c,1,None)) is not int or slist(c,1,0) <= 0:
                msg(FX_ERROR_VAL, _('Invald %a layout. Defaulting...'), k)
                new_gui_attrs['layouts'][k] = FX_DEF_LAYOUTS[k]
                break


    
    new_gui_attrs['default_search_filters'] = scast(gui_attrs.get('default_search_filters',FEEDEX_GUI_DEFAULT_SEARCH_FIELDS).copy(), dict, {})
    gui_attrs['default_search_filters'] = scast(gui_attrs.get('default_search_filters',FEEDEX_GUI_DEFAULT_SEARCH_FIELDS).copy(), dict, {})


    if new_gui_attrs['default_search_filters'] != {}:

        new_gui_attrs['default_search_filters']['qtype'] = scast(gui_attrs['default_search_filters'].get('qtype'), int, 0)

        new_gui_attrs['default_search_filters']['field'] = scast(gui_attrs['default_search_filters'].get('field'), int, None)
    
        new_gui_attrs['default_search_filters']['feed_or_cat'] = scast(gui_attrs['default_search_filters'].get('feed_or_cat'), int, None)
    
        new_gui_attrs['default_search_filters']['exact'] = scast(gui_attrs['default_search_filters'].get('exact'), bool, False)
        new_gui_attrs['default_search_filters']['last'] = scast(gui_attrs['default_search_filters'].get('last'), bool, None)
        new_gui_attrs['default_search_filters']['last_hour'] = scast(gui_attrs['default_search_filters'].get('last_hour'), bool, None)
        new_gui_attrs['default_search_filters']['today'] = scast(gui_attrs['default_search_filters'].get('today'), bool, None)
        new_gui_attrs['default_search_filters']['last_week'] = scast(gui_attrs['default_search_filters'].get('last_week'), bool, None)
        new_gui_attrs['default_search_filters']['last_month'] = scast(gui_attrs['default_search_filters'].get('last_month'), bool, None)
        new_gui_attrs['default_search_filters']['last_quarter'] = scast(gui_attrs['default_search_filters'].get('last_quarter'), bool, None)
        new_gui_attrs['default_search_filters']['last_year'] = scast(gui_attrs['default_search_filters'].get('last_year'), bool, None)

        new_gui_attrs['default_search_filters']['group'] = scast(gui_attrs['default_search_filters'].get('group'), str, 'daily')

        new_gui_attrs['default_search_filters']['lang'] = scast(gui_attrs['default_search_filters'].get('lang'), str, None)
        new_gui_attrs['default_search_filters']['handler'] = scast(gui_attrs['default_search_filters'].get('handler'), str, None)

        new_gui_attrs['default_search_filters']['case_ins'] = scast(gui_attrs['default_search_filters'].get('case_ins'), bool, None)
        new_gui_attrs['default_search_filters']['case_sens'] = scast(gui_attrs['default_search_filters'].get('case_sens'), bool, None)

        new_gui_attrs['default_search_filters']['read'] = scast(gui_attrs['default_search_filters'].get('read'), bool, None)
        new_gui_attrs['default_search_filters']['unread'] = scast(gui_attrs['default_search_filters'].get('unread'), bool, None)

        new_gui_attrs['default_search_filters']['flag'] = scast(gui_attrs['default_search_filters'].get('flag'), str, None)

    new_gui_attrs['tabs'] = gui_attrs.get('tabs',[]).copy()

    return new_gui_attrs








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







from feedex_desktop_notifier import DesktopNotifier
from feedex_gui_tabs import FeedexTab, FeedexGUITable, ResultGUI, ResultGUIEntry, ResultGUINote, ResultGUIContext, ResultGUIRule, ResultGUIFlag, ResultGUITerm, ResultGUITimeSeries, CalendarDialog
from feedex_gui_feeds import FeedexFeedTab
from feedex_gui_dialogs_entts import NewFromURL, EditCategory, EditEntry, EditFlag, EditRule, EditFeedRegex, EditFeed
from feedex_gui_dialogs_utils import InfoDialog, YesNoDialog, DisplayRules, DisplayWindow, AboutDialog, PreferencesDialog, DisplayKeywords, DisplayMatchedRules






