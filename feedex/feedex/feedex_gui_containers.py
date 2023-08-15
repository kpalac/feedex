# -*- coding: utf-8 -*-
""" GUI container classes for FEEDEX """

from feedex_gui_utils import *





class ResultGUI:
    """ Template for GUI result"""
    def __init__(self, **kargs) -> None:
        self.MW = kargs.get('main_win', None)
        self.config = kargs.get('config')
        if self.config is None:
            if self.MW is None: self.config = fdx.config
            else: self.config = self.MW.config
        self.gui_fields = ()
        self.gui_types = ()
        self.gui_vals = {}
        self.gui_markup_fields = ()
        self.search_col = None
        self.toggled_ids = []
        self.toggled_gui_ixs = []

    def gindex(self, field):
        """ Returns a GUI field index """
        return self.gui_fields.index(field)

    def gget(self, field, *args):
        """ Get GUI value """
        if len(args) > 1: default = args[0]
        else: default = None
        return self.gui_vals.get(field, default)

    def gadd(self, field, type):
        """ Add typed field to store template """
        self.gui_fields, self.gui_types = list(self.gui_fields), list(self.gui_types)
        self.gui_fields.append(field)
        self.gui_types.append(type)
        self.gui_fields, self.gui_types = tuple(self.gui_fields), tuple(self.gui_types)

    def gpopulate(self, ilist):
        for i,f in enumerate(self.gui_fields): self.gui_vals[f] = ilist[i]

    def gclear(self): self.gui_vals.clear()

    def glistify(self):
        """ Return GUI fields as ordered list"""
        out_list = []
        for f in self.gui_fields: out_list.append(self.gui_vals.get(f))
        return out_list

    def gtuplify(self): return tuple(self.glistify())











class ResultGUIEntry(ResultGUI, ResultEntry):
    """ GUI Result for generating and storing table items """
    def __init__(self, **kargs):
        ResultEntry.__init__(self, replace_nones=True, **kargs)
        ResultGUI.__init__(self, **kargs)
        self.gui_fields = ('gui_ix', 'gui_icon', 'gui_toggle', 'id', 'pubdate_short', 'pubdate', 'title', 'feed_name', 'feed_id', 'desc', 'author', 'flag_name',
             'category', 'tags', 'read', 'importance', 'readability', 'weight', 'word_count', 'rank',
             'count', 'adddate_str', 'pubdate_str', 'publisher', 'link', 'is_node', 'gui_color', 'gui_bold')
        self.gui_types = (int, GdkPixbuf.Pixbuf, bool, int,   str, int,   str, str, int, str, str, str, 
                          str, str, int, float, float, float, int, float, 
                          int, str, str, str, str, int,  str, int)
        self.search_col = self.gindex('title')


    def pre_prep_gui_vals(self, ix, **kargs):
        self.gui_vals.clear()
        self.gui_vals['gui_ix'] = ix
        self.gui_vals['id'] = self.vals['id']
        if self.vals['pubdate_short'] not in (None, ''):
            self.gui_vals['pubdate_short'] = humanize_date(self.vals['pubdate_short'], self.MW.today, self.MW.yesterday, self.MW.year)
        self.gui_vals['pubdate'] = self.vals['pubdate']
        self.gui_vals['title'] = self.vals['title']
        self.gui_vals['feed_name'] = self.vals['feed_name']
        self.gui_vals['feed_id'] = self.vals['feed_id']
        self.gui_vals['author'] = self.vals['author']
        self.gui_vals['flag_name'] = self.vals['flag_name']
        self.gui_vals['category'] = self.vals['category']
        self.gui_vals['tags'] = self.vals['tags']
        self.gui_vals['read'] = self.vals['read']
        self.gui_vals['importance'] = self.vals['importance']
        self.gui_vals['readability'] = self.vals['readability']
        self.gui_vals['weight'] = self.vals['weight']
        self.gui_vals['word_count'] = self.vals['word_count']
        self.gui_vals['rank'] = self.vals['rank']
        self.gui_vals['count'] = self.vals['count']
        self.gui_vals['adddate_str'] = self.vals['adddate_str']
        self.gui_vals['pubdate_str'] = self.vals['pubdate_str']
        self.gui_vals['publisher'] = self.vals['publisher']
        self.gui_vals['link'] = self.vals['link']
        self.gui_vals['is_node'] = self.vals['is_node']
        if self.vals['id'] in self.toggled_ids: self.gui_vals['gui_toggle'] = True
        else: self.gui_vals['gui_toggle'] = False

    def prep_gui_vals(self, ix, **kargs):        
        """ Prepares values for display and generates icon and style fields """
        self.pre_prep_gui_vals(ix, **kargs)
        self.gui_vals['gui_icon'] = self.MW.icons.get(self.vals["feed_id"], self.MW.icons['default'])
        self.gui_vals['desc'] = ellipsize(scast(self.vals['desc'], str, ''), 150).replace('\n',' ').replace('\r',' ').replace('\t', ' ')

        if coalesce(self.vals['read'],0) > 0: self.gui_vals['gui_bold'] = 700
        else: self.gui_vals['gui_bold'] = 400

        if kargs.get('new_col',False): self.gui_vals['gui_color'] = self.config.get('gui_new_color','#0FDACA')
        elif coalesce(self.vals['deleted'],0) > 0 or coalesce(self.vals['is_deleted'],0) > 0: 
            self.gui_vals['gui_color'] = self.config.get('gui_deleted_color','grey')
        elif coalesce(self.vals['flag'],0) > 0: self.gui_vals['gui_color'] = fdx.get_flag_color(self.vals['flag'])




class ResultGUITree(ResultGUIEntry):
    """ GUI result for tree view """
    def __init__(self, **kargs):
        super().__init__(**kargs)
        self.table = 'tree'
        self.gui_markup_fields = ('title',)


    def prep_gui_vals(self, ix, **kargs):

        if self.vals['is_node'] == 1 and self.vals['id'] is None:

            self.gui_vals.clear()
            self.gui_vals['gui_ix'] = ix
            self.gui_vals['id'] = self.vals['id']  
            self.gui_vals['title'] = esc_mu(self.vals['title'])
            self.gui_vals['desc'] = ellipsize(scast(self.vals['desc'], str, ''), 150).replace('\n',' ').replace('\r',' ').replace('\t', ' ')
            self.gui_vals['is_node'] = 1

            if self.vals['feed_id'] is not None: self.gui_vals['gui_icon'] = self.MW.icons.get(self.vals["feed_id"], self.MW.icons['default'])
            elif self.vals['flag'] is not None: self.gui_vals['gui_icon'] = self.MW.icons['flag']
            elif self.vals['pubdate_str'] is not None: self.gui_vals['gui_icon'] = self.MW.icons['calendar']

            self.gui_vals['gui_bold'] = 800
            self.gui_vals['title'] = f"""<u>{self.gui_vals['title']} ({esc_mu(self.vals['children_no'])})</u>"""
            if self.gui_vals['gui_ix'] in self.toggled_gui_ixs: self.gui_vals['gui_toggle'] = True
            elif self.gui_vals['id'] is not None and self.gui_vals['id'] in self.toggled_ids: self.gui_vals['gui_toggle'] = True
            else: self.gui_vals['gui_toggle'] = False

        else:
            self.pre_prep_gui_vals(ix, **kargs)
            self.gui_vals['gui_icon'] = self.MW.icons.get(self.vals["feed_id"], self.MW.icons['default'])
            self.gui_vals['desc'] = ellipsize(scast(self.vals['desc'], str, ''), 150).replace('\n',' ').replace('\r',' ').replace('\t', ' ')
            self.gui_vals['title'] = esc_mu(self.gui_vals['title'])

            if self.vals['is_node'] == 1:
                self.gui_vals['gui_bold'] = 800
                self.gui_vals['title'] = f"""<u>{self.gui_vals['title']} ({esc_mu(self.vals['children_no'])})</u>"""
            else:
                if coalesce(self.vals['read'],0) > 0: self.gui_vals['gui_bold'] = 700
                else: self.gui_vals['gui_bold'] = 400

                if kargs.get('new_col',False): self.gui_vals['gui_color'] = self.config.get('gui_new_color','#0FDACA')
                elif coalesce(self.vals['deleted'],0) > 0 or coalesce(self.vals['is_deleted'],0) > 0: 
                    self.gui_vals['gui_color'] = self.config.get('gui_deleted_color','grey')
                elif coalesce(self.vals['flag'],0) > 0: self.gui_vals['gui_color'] = fdx.get_flag_color(self.vals['flag'])








class ResultGUINote(ResultGUIEntry):
    """ GUI result for note """
    def __init__(self, **kargs):
        ResultEntry.__init__(self, replace_nones=True, **kargs)
        ResultGUI.__init__(self, **kargs)
        self.table = 'notes'
        self.gui_fields = ('gui_ix', 'gui_icon', 'gui_toggle', 'id', 'pubdate_short', 'pubdate', 'title', 'feed_name', 'feed_id', 'entry', 'author', 'flag_name',
             'category', 'tags', 'read', 'importance', 'readability', 'weight', 'word_count', 'rank',
             'count', 'adddate_str', 'pubdate_str', 'publisher', 'link', 'is_node', 'gui_color',)
        self.gui_types = (int, GdkPixbuf.Pixbuf, bool, int,   str, int,   str, str, int, str, str, str, 
                          str, str, int, float, float, float, int, float, 
                          int, str, str, str, str, int,  str,)
        self.gui_markup_fields = ('entry',)
        self.search_col = self.gindex('entry')


    def prep_gui_vals(self, ix, **kargs):        
        """ Prepares values for display and generates icon and style fields """
        self.pre_prep_gui_vals(ix, **kargs)

        self.gui_vals['gui_icon'] = self.MW.icons['large'].get(self.vals["feed_id"], self.MW.icons['large']['default'])
        
        if coalesce(self.vals.get('flag'),0) > 0:
            color = fdx.get_flag_color(self.vals.get('flag',0)) 
            flag_str = f"""<b><span foreground="{color}">{esc_mu(self.vals.get("flag_name",''))}</span></b>: """
        else: flag_str = ''    
            
        desc = ellipsize(scast(self.vals['desc'], str, ''), 250).replace('\n',' ').replace('\r',' ').replace('\t', ' ')
        title = scast(self.vals['title'], str, '').replace('\n',' ').replace('\r',' ').replace('\t', ' ')

        self.gui_vals['entry'] = f"""---------------------------------------------------------------------------------
{flag_str}<b>{esc_mu(title)}</b>
{esc_mu(desc)}"""

        if coalesce(self.vals['deleted'],0) > 0 or coalesce(self.vals['is_deleted'],0) > 0: 
            self.gui_vals['gui_color'] = self.config.get('gui_deleted_color','grey')






class ResultGUIContext(ResultGUI, ResultContext):
    """ GUI result for context """
    def __init__(self, **kargs):
        ResultContext.__init__(self, replace_nones=True, **kargs)
        ResultGUI.__init__(self, **kargs)

        self.gui_fields = ('gui_ix', 'gui_icon', 'id', 'pubdate_short', 'pubdate', 'context', 'title', 'feed_name', 'feed_id', 'author', 'flag_name',
             'category', 'tags', 'read', 'importance', 'readability', 'weight', 'word_count', 'rank',
             'count', 'adddate_str', 'pubdate_str', 'publisher', 'link', 'gui_color',)
        self.gui_types = (int, GdkPixbuf.Pixbuf, int,   str, int,   str, str, str, int, str, str, 
                          str, str, int, float, float, float, int, float, 
                          int, str, str, str, str,  str,)
        self.gui_markup_fields = ('context','flag_name')
        self.search_col = self.gindex('title')



    def prep_gui_vals(self, ix, **kargs):
        self.gui_vals.clear()
        self.gui_vals['gui_ix'] = ix
        self.gui_vals['gui_icon'] = self.MW.icons.get(self.vals["feed_id"], self.MW.icons['default'])
        self.gui_vals['id'] = self.vals['id']
        if self.vals['pubdate_short'] not in (None, ''):
            self.gui_vals['pubdate_short'] = humanize_date(self.vals['pubdate_short'], self.MW.today, self.MW.yesterday, self.MW.year)
        self.gui_vals['pubdate'] = self.vals['pubdate']
        self.gui_vals['context'] = f"""{esc_mu(self.vals['context'][0][0])}<b>{esc_mu(self.vals['context'][0][1])}</b>{esc_mu(self.vals['context'][0][2])}"""
        self.gui_vals['title'] = self.vals['title']
        self.gui_vals['feed_name'] = self.vals['feed_name']
        self.gui_vals['feed_id'] = self.vals['feed_id']
        self.gui_vals['author'] = self.vals['author']
        self.gui_vals['flag_name'] = self.vals['flag_name']
        self.gui_vals['category'] = self.vals['category']
        self.gui_vals['tags'] = self.vals['tags']
        self.gui_vals['read'] = self.vals['read']
        self.gui_vals['importance'] = self.vals['importance']
        self.gui_vals['readability'] = self.vals['readability']
        self.gui_vals['weight'] = self.vals['weight']
        self.gui_vals['word_count'] = self.vals['word_count']
        self.gui_vals['rank'] = self.vals['rank']
        self.gui_vals['count'] = self.vals['count']
        self.gui_vals['adddate_str'] = self.vals['adddate_str']
        self.gui_vals['pubdate_str'] = self.vals['pubdate_str']
        self.gui_vals['publisher'] = self.vals['publisher']
        self.gui_vals['link'] = self.vals['link']

        if coalesce(self.vals['deleted'],0) > 0 or coalesce(self.vals['is_deleted'],0) > 0: 
            self.gui_vals['gui_color'] = self.config.get('gui_deleted_color','grey')
        elif coalesce(self.vals['flag'],0) > 0: 
            flag_col = fdx.get_flag_color(self.vals['flag'])
            self.gui_vals['flag_name'] = f"""<span foreground="{flag_col}">{esc_mu(self.gui_vals['flag_name'])}</span>"""





class ResultGUIFeedTree(ResultGUI, ResultFeed):
    """ GUI result for tree view """
    def __init__(self, **kargs):
        ResultFeed.__init__(self, replace_nones=True, **kargs)
        ResultGUI.__init__(self, **kargs)
        self.table = 'feed_tree'
        self.gui_fields = ('gui_ix', 'gui_icon', 'gui_toggle', 'id', 'name', 'title', 'subtitle', 'url', 'link', 'location', 'handler', 'sfetch', 'sautoupdate', 'interval', 'is_category', 'display_order', 'parent_id', 
                           'gui_color', 'is_node',)
        self.gui_types = (int, GdkPixbuf.Pixbuf, bool,    int,    str, str, str,   str,str,  str, str,  str, str,  int, int,  int, int,
                          str,   int)
        
        self.search_col = self.gindex('name')
        self.gui_markup_fields = ('name',)


    def prep_gui_vals(self, ix, **kargs):
        self.gui_vals.clear()
        self.gui_vals['gui_ix'] = ix
        self.gui_vals['id'] = self.vals['id']
        self.gui_vals['gui_icon'] = self.MW.icons.get(self.vals["id"], self.MW.icons['default'])


        self.gui_vals['name'] = esc_mu(self.name())
        self.gui_vals['title'] = scast(self.vals['title'], str, '')
        self.gui_vals['subtitle'] = ellipsize(scast(self.vals['subtitle'], str, ''), 150).replace('\n',' ').replace('\r',' ').replace('\t', ' ')

        if self.gui_vals['gui_ix'] in self.toggled_gui_ixs: self.gui_vals['gui_toggle'] = True
        elif self.gui_vals['id'] is not None and self.gui_vals['id'] in self.toggled_ids: self.gui_vals['gui_toggle'] = True
        else: self.gui_vals['gui_toggle'] = False

        if scast(self.vals['deleted'], int, 0) == 1: self.gui_vals['gui_color'] = self.config.get('gui_deleted_color','grey')

        self.gui_vals['is_category'] = self.vals['is_category']
        self.gui_vals['parent_id'] = self.vals['parent_id']
        
        self.gui_vals['display_order'] = self.vals['display_order']

        if self.vals['is_node'] == 1:
            self.gui_vals['is_node'] = 1
            self.gui_vals['name'] = f"""<u><b>{self.gui_vals['name']} ({esc_mu(self.vals['children_no'])})</b></u>"""

        else:
            self.gui_vals['url'] = self.vals['url']
            self.gui_vals['link'] = self.vals['link']
            self.gui_vals['location'] = self.vals['location']
            self.gui_vals['handler'] = self.vals['handler']
            self.gui_vals['sfetch'] = self.vals['sfetch']
            self.gui_vals['sautoupdate'] = self.vals['sautoupdate']
            self.gui_vals['interval'] = self.vals['interval']
            self.gui_vals['is_node'] = 0






class ResultGUIRule(ResultGUI, ResultRule):
    """ GUI result for rule """
    def __init__(self, **kargs) -> None:
        ResultRule.__init__(self, replace_nones=True, **kargs)
        ResultGUI.__init__(self, **kargs)

        self.gui_fields = ('gui_ix', 'gui_toggle', 'id', 'name', 'string', 'weight', 'scase_insensitive', 'query_type', 'flag_name', 'field_name', 'feed_name', 
                           'lang', 'matched', 'sadditive', 'flag', 'gui_color',)
        self.gui_types = (int, bool, int, str, str, float, str, str, str, str, str, str, int, str,  int, str,)
        self.search_col = self.gindex('string')


    def prep_gui_vals(self, ix, **kargs):
        self.gui_vals.clear()
        self.gui_vals['gui_ix'] = ix
        self.gui_vals['id'] = self.vals['id']
        self.gui_vals['name'] = self.name()
        self.gui_vals['string'] = self.vals['string']
        self.gui_vals['weight'] = self.vals['weight']
        self.gui_vals['scase_insensitive'] = self.vals['scase_insensitive']
        self.gui_vals['query_type'] = self.vals['query_type']
        self.gui_vals['flag_name'] = self.vals['flag_name']
        self.gui_vals['field_name'] = self.vals['field_name']
        self.gui_vals['feed_name'] = self.vals['feed_name']
        self.gui_vals['lang'] = self.vals['lang']
        self.gui_vals['matched'] = self.vals['matched']
        self.gui_vals['sadditive'] = self.vals['sadditive']        
        self.gui_vals['flag'] = self.vals['flag']        
        if coalesce(self.vals['flag'],0) > 0: self.gui_vals['gui_color'] = fdx.get_flag_color(self.vals['flag'])
        if self.vals['id'] in self.toggled_ids: self.gui_vals['gui_toggle'] = True
        else: self.gui_vals['gui_toggle'] = False



class ResultGUIFlag(ResultGUI, ResultFlag):
    """ GUI result for flag """
    def __init__(self, **kargs):
        ResultFlag.__init__(self, replace_nones=True, **kargs)
        ResultGUI.__init__(self, **kargs)
        self.gui_fields = ('gui_ix', 'gui_toggle', 'id', 'name', 'desc', 'color', 'color_cli', 'gui_color',)
        self.gui_types = (int, bool, int,  str, str, str, str, str,)
        self.search_col = self.gindex('name')

    def prep_gui_vals(self, ix, **kargs):
        self.gui_vals.clear()
        self.gui_vals['gui_ix'] = ix
        self.gui_vals['id'] = self.vals['id']
        self.gui_vals['name'] = self.vals['name']
        self.gui_vals['desc'] = self.vals['desc']
        self.gui_vals['color'] = self.vals['color']
        self.gui_vals['gui_color'] = self.vals['color']
        if self.vals['id'] in self.toggled_ids: self.gui_vals['gui_toggle'] = True
        else: self.gui_vals['gui_toggle'] = False


class ResultGUITerm(ResultGUI, ResultTerm):
    """ GUI result for term list """
    def __init__(self, **kargs):
        ResultTerm.__init__(self, replace_nones=True, **kargs)
        ResultGUI.__init__(self, **kargs)
        self.gui_fields = ('gui_ix', 'term', 'weight', 'search_form',)
        self.gui_types = (int, str, float, str,)
        self.search_col = self.gindex('term')


    def prep_gui_vals(self, ix, **kargs):
        self.gui_vals.clear()
        self.gui_vals['gui_ix'] = ix
        self.gui_vals['term'] = self.vals['term']
        self.gui_vals['weight'] = self.vals['weight']
        self.gui_vals['search_form'] = self.vals['search_form']


class ResultGUIKwTerm(ResultGUI, ResultKwTermShort):
    """ GUI result for term list """
    def __init__(self, **kargs):
        ResultKwTermShort.__init__(self, replace_nones=True, **kargs)
        ResultGUI.__init__(self, **kargs)
        self.gui_fields = ('gui_ix', 'term', 'weight', 'model', 'form', 'gui_bold',)
        self.gui_types = (int, str, float, str, str, int)
        self.search_col = self.gindex('term')


    def prep_gui_vals(self, ix, **kargs):
        self.gui_vals.clear()
        self.gui_vals['gui_ix'] = ix
        self.gui_vals['term'] = self.vals['term']
        self.gui_vals['weight'] = self.vals['weight']
        self.gui_vals['model'] = self.vals['model']
        self.gui_vals['form'] = self.vals['form']
        if ix <= self.config.get('recom_limit',0): self.gui_vals['gui_bold'] = 700
        else: self.gui_vals['gui_bold'] = 400



class ResultGUITimeSeries(ResultGUI, ResultTimeSeries):
    """ GUI result for time series """
    def __init__(self, **kargs):
        ResultTimeSeries.__init__(self, replace_nones=True, **kargs)
        ResultGUI.__init__(self, **kargs)
        self.gui_fields = ('gui_ix', 'time', 'from', 'to', 'freq', 'gui_plot',)
        self.gui_types = (int, str, str, str, float, str,)
        self.gui_markup_fields = ('gui_plot',)
        self.search_col = self.gindex('time')


    def prep_gui_vals(self, ix, **kargs):
        self.gui_vals.clear()
        self.gui_vals['gui_ix'] = ix
        self.gui_vals['time'] = self.vals['time']
        self.gui_vals['from'] = self.vals['from']
        self.gui_vals['to'] = self.vals['to']
        self.gui_vals['freq'] = self.vals['freq']
        
        color = self.config.get('gui_hilight_color','blue')
        unit = dezeroe(self.TB.result_max,1)/200
        length = int(self.vals.get('freq',0)/unit)
        magn = ""
        for l in range(length): magn = f'{magn} ' 
        magn = f'<span background="{color}">{magn}</span>'
        self.gui_vals['gui_plot'] = magn












class ResultPlugin(SQLContainer):
    def __init__(self, **kargs):
        SQLContainer.__init__(self, 'plugins', FX_PLUGIN_TABLE, **kargs)
        self.col_names = FX_PLUGIN_TABLE_PRINT
        self.types = FX_PLUGIN_TABLE_TYPES

    def humanize(self):
        if self.vals['type'] == FX_PLUGIN_RESULT: self.vals['stype'] = _('Search result')
        elif self.vals['type'] == FX_PLUGIN_RESULTS: self.vals['stype'] = _('All search results')
        elif self.vals['type'] == FX_PLUGIN_SELECTION: self.vals['stype'] = _('Selected text')
        elif self.vals['type'] == FX_PLUGIN_CATEGORY: self.vals['stype'] = _('Category')
        elif self.vals['type'] == FX_PLUGIN_FEED: self.vals['stype'] = _('Channel')
        elif self.vals['type'] == FX_PLUGIN_ENTRY: self.vals['stype'] = _('Article/Note')
    
    def fill(self): pass






class FeedexPlugin(ResultPlugin):
    """ GUI Plugin container class"""
    def __init__(self, **kargs) -> None:
        ResultPlugin.__init__(self, **kargs)

        self.MW = kargs.get('main_win')
        self.backup_vals = {}

        self.exists = False
        if kargs.get('id') is not None: self.get_by_id(kargs.get('id'))


    def get_by_id(self, id, **kargs):
        """ Populate this container with IDd plugin """
        for p in self.MW.gui_plugins:
            if p[self.get_index('id')] == id: 
                self.populate(p)
                self.exists = True
                return 0
        self.exists = False
        return msg(FX_ERROR_NOT_FOUND, _('Plugin %a not found!'), id)

    def populate(self, ilist: list, **kargs):
        super().populate(ilist, **kargs)
        self.backup_vals = self.vals.copy()



    

    def validate(self):
        """ Validate plugin's field valuse and types """
        for i,t in enumerate(self.types):
            field = self.fields[i]
            if field == 'id': continue 
            if self.vals[field] is not None and type(self.vals[field]) is not t: return FX_ERROR_VAL, _('Invalid type for %a field'), self.fields[i]
        
        if scast(self.vals['name'], str, '').strip() == '': return FX_ERROR_VAL, _('Name cannot be empty!')
        if self.vals['type'] not in (FX_PLUGIN_SELECTION, FX_PLUGIN_RESULTS, FX_PLUGIN_CATEGORY, FX_PLUGIN_FEED, FX_PLUGIN_ENTRY, FX_PLUGIN_RESULT, FX_PLUGIN_RESULTS,): 
            return FX_ERROR_VAL, _('Invalid plugin type!')
        if scast(self.vals['command'], str, '').strip() == '': return FX_ERROR_VAL, _('Command cannot be empty!')
        return 0



    def add(self, **kargs):
        """ Add plugin to main window and save to JSON """
        max_id = len(self.MW.gui_plugins) + 1

        self.vals['id'] = max_id
        if kargs.get('validate',True):
            err = self.validate()
            if err != 0: return msg(*err)

        if type(self.MW.gui_plugins) is not list: list(self.MW.gui_plugins)
        self.MW.gui_plugins.append(self.tuplify())
        err = save_json(self.MW.gui_plugins_path, self.MW.gui_plugins)

        if err == 0: return msg(_('Plugin %a added successfully'), self.vals['id'])
        else: return err





    def edit(self, **kargs):
        """ Edit existing plugin """
        if not self.exists: return FX_ERROR_NOT_FOUND

        if kargs.get('validate',True):
            err = self.validate()
            if err != 0: return msg(*err)

        for ix, p in enumerate(self.MW.gui_plugins):
            if p[self.get_index('id')] == self.vals['id']: 
                self.MW.gui_plugins[ix] = self.tuplify()
                break
        err = save_json(self.MW.gui_plugins_path, self.MW.gui_plugins)

        if err == 0: return msg(_('Plugin %a updated successfully'), self.vals['id'])
        else: return err
        




    def delete(self, **kargs):
        """ Delete existing plugin """
        if not self.exists: return FX_ERROR_NOT_FOUND

        ix = -1
        for i, p in enumerate(self.MW.gui_plugins):
            if p[self.get_index('id')] == self.vals['id']:
                ix = i
                break

        if ix != -1: del self.MW.gui_plugins[ix]
        err = save_json(self.MW.gui_plugins_path, self.MW.gui_plugins)

        if err == 0: return msg(_('Plugin %a deleted'), self.vals['id'])
        else: return err






    def run(self, item, **kargs): 
        """ Execute command, substitute fields and run additional dialogues if needed """
        command = scast( self.vals.get('command'), str, '')
        if command == '': return -1

        rstr = random_str(length=5, string=command)
        run_env = os.environ.copy()

        # Setup running environment and temp file
        if isinstance(item, SQLContainer):

            is_cont = True
            run_env['FEEDEX_TABLE'] = item.table
            run_env['FEEDEX_FIELDS'] = ';'.join(item.fields)

        elif type(item) is str:
            is_cont = False
            run_env['FEEDEX_SELECTED_TEXT'] = item


        # Substitute parametrized values
        command = command.split(' ')
        for i, arg in enumerate(command):
            
            # Handle escaping percent signs
            arg = arg.replace('%%',rstr)

            # File/Dir choosers
            if '%choose_file_save%' in arg:
                filename = f_chooser(self.MW, self.MW, action='save', header=_('Save to...'))
                if filename is not False: arg = arg.replace('%choose_file_save%', filename)
                else: return msg(_('No file chosen'))
            if '%choose_file_open%' in arg:
                filename = f_chooser(self.MW, self.MW, action='open_file', header=_('Choose File...'))
                if filename is not False: arg = arg.replace('%choose_file_open%', filename)
                else: return msg(_('No file chosen'))
            if '%choose_dir_open%' in arg:
                filename = f_chooser(self.MW, self.MW, action='open_dir', header=_('Choose Directory...'))
                if filename is not False: arg = arg.replace('%choose_dir_open%', filename)
                else: return msg(_('No directory chosen'))

            # Substitute fields
            if '%S' in arg and type(item) is str:
                arg = arg.replace('%S', item)

            # Restore escaped percent sign
            if not is_cont: arg = arg.replace(rstr, '%')

        command[i] = arg

        debug(6, f'Running: {" ".join(command)}')
        
        if is_cont:
            self.MW.DB.create_pipe(type=1)
            run_env['FEEDEX_PIPE'] = fdx.out_pipe
            if self.vals['type'] == FX_PLUGIN_RESULTS: err = save_json(fdx.out_pipe, self.MW.curr_upper.table.results)
            else: err = save_json(fdx.out_pipe, item)
 
            # substitute tmp file string
            for i, arg in enumerate(command):
            
                # Handle container-specific arguments
                arg = arg.replace('%p', fdx.out_pipe)
                arg = arg.replace('%t', item.table)
                arg = arg.replace(rstr, '%')

                command[i] = arg   

        err = 0
        # Run command
        try:
            comm_pipe = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=run_env)
            output = comm_pipe.stdout.read()
            msg(output.decode())
        except Exception as e:
            err = msg(FX_ERROR_HANDLER, _("Error executing script: %a"), e)
        finally:
            if is_cont:
                err = self.MW.DB.destroy_pipe(type=1)

        return err










class ResultGUIPlugin(ResultGUI, ResultPlugin):
    """ GUI representation for plugin """
    def __init__(self, **kargs) -> None:
        ResultPlugin.__init__(self, **kargs)
        ResultGUI.__init__(self, **kargs)
        self.gui_fields = self.fields + ('gui_ix',)
        self.gui_types = (int, str, str, str, str, int,)
        self.search_col = self.gindex('name')



    def prep_gui_vals(self, ix, **kargs):
        self.gui_vals.clear()
        self.gui_vals['gui_ix'] = ix
        self.gui_vals['id'] = self.vals['id']

        self.gui_vals['type'] = self.vals.get('stype','?')

        self.gui_vals['name'] = scast(self.vals['name'], str, '')
        self.gui_vals['command'] = scast(self.vals['command'], str, '')
        self.gui_vals['desc'] = ellipsize(scast(self.vals['desc'], str, '').replace('\n',' ').replace('\r',' ').replace('\t',' '), 200)

        #if self.vals['id'] in self.toggled_ids: self.gui_vals['gui_toggle'] = True
        #else: self.gui_vals['gui_toggle'] = False





class ResultGUICatItem(ResultGUI, ResultCatItem):
    """ GUI representation for plugin """
    def __init__(self, **kargs) -> None:
        ResultCatItem.__init__(self, **kargs)
        ResultGUI.__init__(self, **kargs)
        self.gui_fields = ('id', 'gui_icon', 'gui_toggle',  'name', 'desc', 'tags', 'location', 'rank', 'freq', 'link_res', 'link_home',  'gui_bold', 'gui_ix', 'is_node', 'parent_id')
        self.gui_types = (int,  GdkPixbuf.Pixbuf, bool,    str, str, str, str, int, str, str, str,   int,   int,   bool, int )
        self.gui_markup_fields = ('name',)
        self.toggled_ids = []


    def prep_gui_vals(self, ix, **kargs):
        self.gui_vals.clear()
        self.gui_vals['gui_ix'] = ix
        self.gui_vals['id'] = self.vals['id']
        self.gui_vals['desc'] = self.vals['desc']
        if self.vals['id'] in self.toggled_ids: self.gui_vals['gui_toggle'] = True
        else: self.gui_vals['gui_toggle'] = False
        self.gui_vals['name'] = esc_mu(self.vals['name'])
        self.gui_vals['is_node'] = self.vals['is_node']

        if self.vals['is_node']:
            self.gui_vals['name'] = f"""<u>{self.gui_vals['name']}</u>"""
            self.gui_vals['gui_bold'] = 800
            self.gui_vals['parent_id'] = -1

            thumbnail = os.path.join(FEEDEX_SYS_ICON_PATH, f"""{self.vals['thumbnail']}.svg""")
            if os.path.isfile(thumbnail):
                self.MW.cat_icons[self.vals['thumbnail']] = GdkPixbuf.Pixbuf.new_from_file_at_size(thumbnail , 16, 16)
            else:
                self.MW.cat_icons[self.vals['thumbnail']] = self.MW.icons['doc']
            self.gui_vals['gui_icon'] = self.MW.cat_icons.get(self.vals['thumbnail'])
        
        else:
            self.gui_vals['parent_id'] = self.vals['parent_id']
            self.gui_vals['gui_bold'] = 400
            if self.MW.cat_icons.get(self.vals['thumbnail']) is None: 
                thumbnail = os.path.join(FEEDEX_FEED_CATALOG_CACHE, 'thumbnails', self.vals['thumbnail'])
                if os.path.isfile(thumbnail):
                    self.MW.cat_icons[self.vals['thumbnail']] = GdkPixbuf.Pixbuf.new_from_file_at_size(thumbnail , 16, 16)
                else:
                    self.MW.cat_icons[self.vals['thumbnail']] = self.MW.icons['rss']
            self.gui_vals['gui_icon'] = self.MW.cat_icons.get(self.vals['thumbnail'])
            self.gui_vals['tags'] = self.vals['tags']
            self.gui_vals['location'] = self.vals['location']
            self.gui_vals['rank'] = self.vals['rank']
            self.gui_vals['freq'] = self.vals['freq']
            self.gui_vals['link_res'] = self.vals['link_res']
            self.gui_vals['link_home'] = self.vals['link_home']




