# -*- coding: utf-8 -*-
""" Constants with help strings for Feedex  """








FEEDEX_SHORT_HELP=_("""
Usage: <b>feedex [parameters|filters] [actions]</b>

    <b>Actions</b>:
        -h, --help                              Show this help
        -hh, --help-long                        Show full manual (use with ' | less -R' because it is long :))
        -v, --version                           Version info
        --about                                 About Feedex...

        -g, --get-news [ID]                     Get news without checking intervals (force download)
                                                Providing ID will limit download to specified channel ID

        -a, --add-feed [URL]                    Add news channel by providing a URL pointing to RSS
        -D, --delete-feed [ID] [option]         Delete news channel specified by ID (first - move to Trash, second - delete permanently with all entries)

        -u, --update-feeds [ID]                 Update news channel data like title, subtitle, tags etc.. Limit by ID
    	-L, --list-feeds                        List all registerred channels
        -c, --check [ID]                        Check for news (applying intervals and no force download with etag/modified). 
                                                Limit by channel ID

        -r, --read-entry [ID]                   Read entry/news article contents by ID
        -o, --open-in-browser [ID|URL]          Open link of an entry by ID or URL. Register openning and learn keywords/rules for later ranking
        -F, --read-feed [ID]                    Get all entries from a Channel specified by ID
        -C, --read-category [ID|NAME]           Get all entries for a specified Category
        -q, --query [Phrase]                    Query entries with search phrase (see -hh option for details)

        --csv                                   Output in CSV format (no beautifiers)
        --short                                 Show short output for queries
        --headlines                             Output only date, title and channel


    <b>!!! See feedex -hh for full manual !!!</b>
        --help-feeds                            Manual on Feeds and Ctegories 
        --help-entries                          Manual on Entries (articles, notes, hilights etc.)
        --help-rules                            Manual on rules, ranking and flags
        --help-scripting                        Manual for scripting
        --help-examples                         Command line examples

""")




FEEDEX_LONG_HELP=_("""
Usage: <b>feedex [parameters|filters] [actions] [arguments]</b>

    Feedex lets you organize your news and notes. It classifies incoming news according to your previous choices and manually created rules. 
    But Feedex can also handle other types of data - you can save categorized notes and analyze them for interesting features
    to apply to rank and highlight news, to help you get important information quickly and efficiently. 
    It is meant to be used as a scheduled job (with desktop notifications) or hotkey script for quickly saving highlighted text or keyword,
    adding a news channel with URL or simply as a tool to read, query and analyse news/notes.

    Technical notes:
    Feedex uses <b>SQLite</b> database to store data and Xapian for indexing. DB and index by default can be found in <b>~/.local/share/feedex/feedex.db/</b>
    Language Models, used to rank and extract keywords, can be found in <b>/use/share/feedex/models</b> in pickle format. 
    You can add new language model with examples in <b>/usr/share/feedex/data/model_generators</b> directory.
    Icons and thumbnails are saved separately in <b>~/.local/share/feedex/icons</b> and <b>~/.local/share/feedex/cache</b> respectively.

    <b>General:</b>
        -h, --help                              Show short help
        -hh, --help-long                        Show this help
        -v, --version                           Version info
        --about                                 About Feedex...

    <b>Display parameters:</b>
        --csv                                   Output in CSV format (no interlines and colours/beautifiers)
        --json                                  Output as standard JSON string
        --short                                 Output shortened version
        --headlines                             Output only date, title and channel

        --html-template=[FILE]                  Output results as HTML using a template from text file
                                                See --help-html for more information abot displaying results in HTML format

        --silent                                Do not print output

        --trunc=INT                             Truncate output of fields to INT chars (0 for no truncation)
        --delimiter=STR                         Change field separator (cli/csv), delault |
        --delimiter2=STR                        Change item separator inside field, e.g. for snippets and contexts (cli/csv), delault ;
        --escape=STR                            Escape sequence for delimiters (useful for CSV)

        --bold_beg=STR, --bold_end=STR          Strings to be inserted as bold markup beginning/end. Used for displaying snippets, to hilight
                                                the search phrase. Defaults are <b>,</b>

        --desktop-notify                        Show desktop notifications instead CLI output (-g, -c, and --query)
                                                and inform about adding new entries, rules and feeds from URL
                                                Useful for scheduled tasks and keyboard shortcuts (e.g. adding a hilighted note with --clipboard)

        --clipboard                             Enable destkop clipboard/selection support. Selection and window title can be used in arguments
                                                for actions: add-entry, add-feed, add-keyword, add-regex, add-full-text, add-full-text-exact
                                                Substitutions:  
                                                    %%  -   % character
                                                    %s  -   current text selection
                                                    %w  -   curent window name 


    <b>Fetching:</b>
        -g, --get-news [ID]                     Get news without checking intervals, ETags or Modified tags (force download). Limit by feed ID
        -c, --check [ID]                        Check for news (applying intervals and no force download with etag/modified). Limit by feed ID
        -o, --open-in-browser [ID|URL]          Open entry by ID or URL in browser. Register openning for later ranking and
                                                learn rules.

    <b>Feeds:</b>
        Every news channel is saved as feed. Feeds can be downloaded, edited, deleted, added by providing URL etc. Downloaded news 
        are saved as entries. See <b>--help-feeds</b> option for more detailed information.

    	-L, --list-feeds                        List all registerred feeds
        -a, --add-feed [URL]                    Add feed providing a URL pointing to RSS. 
                                                Possible parameters: --handler=[rss|html|script|local], --category=[ID/Name]
                                                --no_fetch - do not fetch anything to allow further editting (the same as with 'local/html/script' handlers)
        -u, --update-feeds [ID]                 Update feed data like title, subtitle, tags etc.. Limit by ID
                                                Providing ID will limit download to specified feed ID
        -D, --delete-feed [ID]                  Delete feed specified by ID. Deleted feed is moved to Trash. 
                                                Deleting Feed in Trash will remove it permanently with all associated Entries
        -F, --read-feed [ID]                    Get all entries from a feed specified by ID (filters like in --query)
        -C, --read-category [ID|NAME]           Get all entries from a category specified by ID or NAME (filters like in --query)
        --examine-feed [ID]                     Check feed configuration
        --edit-feed [ID] [FIELD] [VALUE]        Change feed's (by ID) PARAMETER 
                                                (for param. names check --examine-feed) to VALUE
                                                NULL or NONE means NULL value

        --insert-feed-before [ID] [TARGET ID]   Change display order of Channel/Category so it is displayed before TARGET IDd Channel/Category
                                                If IDd is a Channel and TARGET is a Category, then Channel will be assigned to the Category
                                                This command changes display_order field in feeds table

        --test-regexes [ID]                     Download URL and perform sample parsing with saved REGEXes for a specified Feed.
                                                DB will not be updated. For testing.

    <b>Categories:</b>
        Every Feed or Entry can be assigned to a Category

        --list-categories                       List all available categories
        --show-categories-tree                  List Category/Channel tree
        --add-category [Title] [Subtitle]       Add new category with given title and subtitle
        --delete-category [ID]                  Remove category with given ID. If category is already in Trash, it will be removed permanently
        --edit-category [ID] [FIELD] [VALUE]    Edit ID'd category - change field's value to [VALUE].
                                                NULL or NONE means NULL value


    <b>Entries:</b>
        Every news article, note, highlight etc. is saved as an Entry. Entries are available for queries and linguistic analysis.
        You can add entries of any category/feed as well as delete any entry. Entries are linguistically analysed and ranked by importance
        according to learned and manual rules and keywords.
        Every entry has a unique ID. See <b>--help-entries</b> for more detailed information

        -r, --read-entry [ID]                   Read entry contents by ID (does not cause learning)
        -S, --find-similar [ID]                 Find similar entries to ID'd (filters like in --query)
                                                --limit=INT        Limit results to INT-best (inproves performance)
        --rel-in-time [ID]                      Entry's relevance as a time series - like --term-in -time for entry's keywords (filters like in --query)
                                                --limit=INT        Limit results to INT-best (inproves performance)
        --mark [ID] [N]                         Mark entry as read N times (increases weight in later ranking) and learn features
                                                options:
                                                --learn,--no-learn         Extract patterns from Entry?
        --mark-unimportant [ID]                 Mark entry as unimportant and learn negative features
                                                options:
                                                --learn,--no-learn         Extract patterns from Entry?
        --flag [ID] [N]                         Flag entry to be highlighted in queries (0 - no flag)
                                                Flags are also added if entry contains a keyword specified by --add-keyword
                                                This helps to highlight items important to user
        -N, --add-entry [TITLE] [TEXT]          Add an entry providing title and text. Useful for saving highlights or notes.
                                                NULL or NONE means NULL value
                                                Parameters:
                                                --category=[INT|NAME]   Specifiy Entry's Category
                                                --feed=[INT]            Specify Entry's Feed
                                                --learn, --no-learn     Do you want to learn features from this entry for ranking news?
                                                                        Default is: learn
                                                                        Learning is useful to find topics that will interest you most based on your notes
                                                --note, --news          Is it a user's Note (default) or News item?


	    --delete-entry [ID]                     Delete entry/news article/note by its ID. If the Entry is already in Trash it will
                                                be removed permanently with all keywords/rules
        --edit-entry [ID] [FIELD] [VALUE]       Edit ID'd Entry. Change [FIELD] to specified [VALUE]. 
                                                NULL or NONE means NULL value
                                                See --help-entries for field names

        --add-entries-from-file [FILE]          
        --add-entries-from-pipe                 You can add Entries wholesale from a JSON file or pipe input compatibile with JSON format.
                                                For input format see <b>--help-entries</b> option
                                                --learn     Do you want to learn features from added entries if 'read' param is > 0?
                                                    
                                    

    <b>Queries:</b>
        --list-history                          Show search history
        
        -q, --query [Phrase]                    Query entries with a search phrase:
                                                operators:
                                                
                                                escape - \\
                                                
                                                Full Text Search:
                                                    
                                                    Capitalized tokens are treated as unstemmed/exact
                                                    
                                                    logical: OR, AND, NOT, (, )
                                                    proximity: NEAR, ~[NUM_OF_WORDS], ~
                                                    wildcards: 
                                                        *          - any character string
                                                        <DIV>      - divider (period, punctation etc.)
                                                        <NUM>      - number
                                                        <CAP>      - capitalized word
                                                        <ALLCAP>   - word with all capitals
                                                        <UNCOMM>   - uncommon word
                                                        <POLYSYL>  - long word (3+ syllables)
                                                        <CURR>     - currency symbol
                                                        <MATH>     - math symbol
                                                        <RNUM>     - Roman numeral
                                                        <GREEK>    - Greek symbol
                                                        <UNIT>     - unit marker/symbol
                                                        


                                                String Matching:
                                                    wildcard: *
                                                    field beginning/end: ^,$
                                                        

                                                    
                                                parameters:
                                                --lang=         language used in query for tokenizing and stemming
                                                --case_ins      query is case insensitive
                                                --case_sens     query is case sensitive
                                                --field=        field to search. 0 or None for all.
                                                                Available fields:
                                                                author, publisher, contributors, title, tags, category, comments
                                                --type=         type of qery
                                                                'fts' - full text (default)
                                                                'string' - simple string matching

                                                --logic=        How should fts terms be connected by default?
                                                                    'any' - any term matches (OR)
                                                                    'all' - all terms must match (AND)
                                                                    'near' - evaluate terms' proximity
                                                                    'phrase' - treat terms as a phrase
                                                

                                                --sort=/--rsort=   sort/reverse sort by field (see --read-entry for field names)
                                                --rev            display in reverse order
                                                --group=         Display as a tree grouped by this parameter 
                                                                (category, feed, flag, hourly, daily, monthly, similar)
                                                --depth=         Integer telling the depth of each node for grouping. If 0, every result is shown
                                                                 If no grouping was selected, simply first N results will be shown


                                                filters: 
                                                --from=,to=     filter by published dates
                                                --added_from=, 
                                                --added_to=     filter by dates when entry was added to database
                                                --last          limit to only recently added (on last update)
                                                --last_n=       limit to only last N updates
                                                --feed=         limit to feed specified by ID
                                                --category=     limit to category and feeds in category specified by ID
                                                --today         limit to last 24h
                                                --last_hour     limit to last 1h
                                                --last_week, --last_month, --last_quarter, --last_six_months, --last_year   limit to 7, 31, 93 or 365 days ago
                                                --read/--unread     limit to read/unread only (see --mark)
                                                --flag=             limit by flag. Possible values:
                                                                        all - flagged and unflagged entries
                                                                        no  - only unflagged entries
                                                                        all_flags - include all flags
                                                                        [INT] - choose a flag to filter by (by ID)
                                                --note, --news   limit to only user's Notes/News items 
                                                --handler=       limit to feed handler (rss, html, script, local)
                                                --deleted        indlude deleted feeds, categories and entries

                                                
                                                paging of results:
                                                --page=INT           page number (default is 1)
                                                --page_len=INT       page length (default is 3000)
                                                

                                                misc:
                                                --json_query            parse query argument as JSON and extract filters/phrase from it. Useful for scripts.
                                                                        see <b>--help-scripting</b> for details
    
                                                --export-to-file=FILE   export query results to JSON file that can be used with --add-entries-from-file option
                                                                        to move entries between databases (e.g. for archiving)
                                                                        This option works only with normal queries, so time series, groupings, contexts are excluded   

                                                                
        --term-context [TEXT]                   Show contexts for given terms (parameters as in query, contexts taken from results)

        --trends [TEXT]                         Show trends (frequent keywords) for filterred entries (filters as for query)
        --trending [TEXT]                       Show trending entries for given filters (filters as for query)
            
        --term-net [TERM]                       Show terms connected to a given term by context (parameters:lang)
        --term-in-time [TERM]                   Show time distribution of a term (filters like in --query) 
                                                parameters:
                                                --lang=          language used for query
                                                --group=         grouping (hourly, daily, monthly)
                                                --plot           plot data points in CLI
                                                --term-width=    width of terminal window (for aestetics)

                                                
    <b>Handlers:</b>
        Every Feed has a protocol handler specified:
        <b>rss</b>      RSS protocol (needs a valid URL)
        <b>html</b>     Fetch a HTML page and parse it with REGEXes from rx_... fields
        <b>script</b>   Run a script to fetch for this channel specified in <b>script_file</b> field
        <b>local</b>    No internet protocol. Feeds are not fetched from the Internet, but can be populated by scripts (see --add-entries-from-file/pipe)

    <b>Rules (Keywords and Terms):</b>
        Rules are learned when article is opened in browser (-o option) or added manually (--add-entry with --learn). 
        They can also be added manually as keywords, phrases, REGEXes etc.
        Learned rules are used to rank incoming news by importance (you can sort by importance in queries with --sort=importance)
        and get most important news on top. 
        Manual rules are used for flagging/highlighting articles so they are more visible. 
        Feedex learns rules by extracting important phrases from opened entries using language models.
        See <b>--help-rules</b> for more info

        --list-rules                            Show all non-learned rules (Keywords, REGEX and strings)       
        -K, --add-keyword [TEXT]                Add keyword(s) to rules applied on every news check (simple string matching)
                                                If a keyword is matched in an incoming news or note, it will be highlighted
                                                in notifications and queries (see --flag)
                                                parameters:
                                                --case_ins, --case_sens     for c. ins. matching
                                                --feed=[ID]                 feed ID to be matched exclusively
                                                --field=[NAME]              field name to be exclusively matched (
                                                                                Available fields:
                                                                                (author, publisher, contributors,
                                                                                title, tags, category, comments)
                                                --weight                    weight ascribed to this rule
                                                --lang                      language to be matched and used for stemming and tokenizing
                                                --flag                      choose a flag to use if matched. Possible values: 1-5 or no
                                                
        --add-regex [TEXT]                      Add REGEX to rules applied on every news check
                                                (parameters: as in previous option)
        --add-full-text [TEXT]                  Add stemmed and tokenized query to rules applied on every news check.
                                                Wildcards and logical operators are not supported
                                                (parameters: as in previous option)

        --edit-rule [ID] [FIELD] [VALUE]        Edit ID'd Rule. Change [FIELD] to specified [VALUE]. 
                                                \\NULL or \\NONE means NULL value
                                                See --help-rules for field names

        --delete-rule [ID]                      Delete rule by its ID (see: --show-rules)

        --keywords [ID]                         Show/generate features/keywords for a specified entry/article.
                                                Those same keywords from read entries are used for ranking new documents.
        --rules-for-entry [ID]                  Show rules that matched and added to importance of ID'd entry


    <b>Flags:</b>
        --list-flags                            Display all Flags
        --add-flag [NAME] [DESC]                Add new flag with given NAME and optional DESCription
        --edit-flag [ID] [FIELD] [VALUE]        Edit flag by ID
        --delete-flag [ID]                      Delete flag by ID


    <b>Misc:</b>
        --clear-history                         Clear search history
        --delete-query-rules                    Deletes all rules learned from query search phrases
        --delete-learned-rules                  Deletes all learned keywords/rules (<i>use cautiously</i>)
        --empty-trash                           Permanently removes all Entries, Feeds and Categories marked as deleted


    <b>Data and Dev:</b>
        
        --export-rules [FILENAME]               Export added rules to json file
        --import-rules [FILENAME]               Import added rules from json file to current DB

        --export-feeds [FILENAME]               Export saved news channels to json file
        --import-feeds [FILENAME]               Import saved news channels from json file to current DB

        --export-flags [FILENAME]               Export saved flags to json file
        --import-flags [FILENAME]               Import saved flags from json file to current DB

        Exports/imports can be used to move data between DBs. In addition you can export query results with --export-to-file option
        and then import it to new DB with --add-entries-from-file. This way you can archive or trim big databases.


        --reindex [ID]                          Index and relculate linguistic stats and tokens for all/IDd entry
        --rerank [ID]                           Recalculate importance and flag stats for all/IDd entry
        --relearn [ID]                          (Re)learn features from all read entries/IDd entry

        --batch_size=INT                        The size of processed entries before committing


                                                    
    <b>Database:</b>

        --lock-db, --unlock-db                  Force-lock/unlock database (use with caution)
        --lock-fetching,
        --unlock-fetching                       Force-lock/unlock database for fetching. Useful for scripts and error recovery
        --ignore-lock                           Ignore DB locking mechanism
        --db-stats                              Database statistics
        --timeout=INT                           (param) Timeout to try connect on case database is locked

        --db-maintenance                        Perform maintenance on the database (VACUUM, ANALYZE and REINDEX)
                                                to reduce DB size

                                                

    <b>Configuration parameters:</b>

        --config=                               Specify different configuration file. Useful for implementing different profiles.
        --log=                                  Specify different log file
        --database=                             Specify different SQLite database
        --debug                                 Set verbose debug mode to 1 - more inforation on what is done
        --debug=INT                             Set debug mode (see below)

    <b>Possible ENVIRONMENT variables to set:</b>

        FEEDEX_DB_PATH                          Path to SQLite database
        FEEDEX_LOG                              Path to log file
        FEEDEX_CONFIG                           Path to config file


    <b>Return codes:</b>
        0       No error occurred
        1       Generic error
        2       Database error (SQL, Operational or Xapian)
        3       Handler error (e.g. invalid HTTP status)
        4       Lock error (DB is locked for requested action)
        5       Invalid query options (e.g. requested search field is invalid)
        6       Input/Output data error (e.g. invalid pipe data or json data, invalid input file etc.)
        7       Validation error (e.g. invalid data type while editing entry)
        8       Referenced data not found (e.g. entry with a given ID does not exists)
        9       Invalid command line arguments
        

    <b>Debug levels:</b>
        1       All messages
        2       Database messages
        3       Handler messages
        4       Linguistic processing messages
        5       Query messages
        6       I/O messages
        7       GUI messages
        8       Show all fields/columns in CLI queries



""")



FEEDEX_HELP_EXAMPLES=_("""

<b>Feedex: Command examples</b>
        
        <b>feedex --rsort=adddate --category=Hilights -q</b>
            Show all documents in "Hilights" category and reverse-sort them by date added
        
        <b>feedex --sort=pubdate -F=1 -q</b>
            Show all news for feed 1 and sort them by publication date

        <b>feedex --sort=pubdate -f=2 --unread -q</b>
            Show all unread news for feed 2 and sort them by publication date

        <b>feedex --type=string -q "example"</b>
            Search for phrase "example" by simple string matching, case sensitive

        <b>feedex --field=title --case_ins -q "example"</b>
            Search for "example" in titles, case insensitive

        <b>feedex --headlines --group=category --depth=10 --last_month -q 'example'</b>
            Show entries containing 'example' grouped by category with headlines only

        <b>feedex --headlines --group=category --depth=10 --last -q</b>
            Show nicely grouped headlines from last fetch

        <b>feedex --desktop-notify --group=category --depth=10 --last -c</b>
            Fetch news and show grouped headlines from fetch as desktop notifications. Good for scheduled task

        <b>feedex --desktop-notify --group=flag --depth=0 --last -c</b>
            Fetch news and show flagged entries only from last fetch as desktop notifications

        <b>feedex --desktop-notify --clipboard --weight=10 --parent_category=Notes --add-entry 'Title:%w' '%s'</b>
            Add new entry to 'Notes' category with title and description suplied from desktop clipboard.
            Convenient to use as a hotkey command
            NOTE! Some desktops (e.g. GNOME) substitute % character, so you will have to escape it, so this command would look like:
            <b>feedex --desktop-notify --clipboard --weight=10 --parent_category=Notes --add-entry 'Title:%%w' '%%s'</b>

        <b>feedex --clipboard --weight=10 --parent_category=Notes --add-entry 'Title:%w' '%s'</b>
            The same as above, but silent

        <b>feedex --desktop-notify --weight=10 --parent_category=Notes --add-entry 'Title example' 'Description example'</b>
            Add new entry and throw desktop notification about it ( useful e.g. for Cron jobs and background script )

        <b>feedex --desktop-notify --clipboard --weight=10 --add-keyword '%s'</b>
            Add new keyword from selected text and notify about it to desktop

        <b>feedex --json_query -q '{"phrase":"test", "last_week":true, "case_sens":true, "read":true}'</b>
            An example usage of JSON query

""")


FEEDEX_HELP_FEEDS=_("""

<b>Feedex: Feeds</b>

Feeds (news Channels) are downloaded and parsed using handlers (rss, html) or populated by scripts (script, local - ignored during fetching).
Unless used with -g option, Feedex will respect etags and 'modified' tags if provided by publisher. 
It will also check for news duplicates before saving. 
HTTP return codes are analysed after download. If channel gave too many HTTP errors in consecutive tries, it will be
ignored. To try again one needs to change error parameter using <b>--edit-feed [ID] error 0 </b>

A feed/channel can be updated periodically (autoupdate field) to check for changes. If channel is moved permanently, 
new URL will be checked and saved. If channel moved temporarily, it will download from new location but keep old URL

If needed, authentication method ('auth' field) along with login ('login') and password ('password') can be specified
and Feedex will try to use those to download a feed. IMPORTANT: passwords are stored in PLAINTEXT!

News channels are stored in DB in <b>feeds</b> table. Value of each of those fields can be changed via <b>--edit-feed</b> 
Below are field descriptions:

    <b>id</b>                                  unique identifier (integer)
    <b>charset</b>                             character encoding stated in header.
    <b>lang</b>                                language stated in header
    <b>generator</b>                           RSS/Atom generator software used to generate the feed
    <b>url</b>                                 resource location used during download

    <b>login, domain, passwd</b>               data used if authentication is required (auth field is not NONE)
    <b>auth</b>                                authentication method: (If changed to not NONE, user will be prompted for auth. data)
                                               <b>NONE</b> - no auth., <b>detect</b> - detect required method,
                                               <b>digest</b>, <b>basic</b> - use these methods
    <b>author, author_contact,
    publisher, publisher_contact,
    contributors, copyright</b>                author, publisher, contributors and copyright from feed header

    <b>link</b>                                link to Homepage
    
    <b>title, subtitle, category, tags</b>     self-explanatory RSS fields
    
    <b>name</b>                                feed name displayed in Feedex's output.
    <b>lastread</b>                            Epoch-encoded date of last download
    <b>lastchecked</b>                         Epoch-encoded date of last check on this feed
    
    <b>interval</b>                            how often shoul this feed be checked for news (-c option)? in minutes
    <b>error</b>                               how many times download or parsing failed. Used to skip broken feeds after
                                               certain amount (error_threshold configuration option)
    <b>autoupdate</b>                          should Feedex automatically update feed data when -c or -g option is used?
    
    <b>http_status</b>                         last HTTP response. 200 means everything went well
    
    <b>etag, modified</b>                      etag and modified tags provided last time by the publisher
    
    <b>version</b>                             protocol version used

    <b>is_category</b>                         is this feed a category? This is because categories are stored in the same table. 
                                                <i>It is not recommended to change this manually</b>
    <b>parent_id</b>                           ID of category this feed belongs to 
                                               to change use: <b>parent_category</b> or <b>parent_id</b> (using 'category' will change other field)
    
    <b>handler</b>                             protocol handler:
                                               <b>rss</b>, 
                                               <b>html</b>  fetching a www page and parsing it by REGEX rules (see below)
                                               <b>script</b>  fetching with a script specified by path in <b>script_file</b> field 
                                               <b>local</b> (no fetching, populated manually or by scripts)
    <b>deleted</b>                             Is feed in trash?

    <b>user_agent</b>                          Custom User Agent tag to use with this feed only. If empty - default will be used.
                                               <i>To be used only for debug purposes!</i>

    <b>fetch</b>                               Should Channel be fetched automatically (-c or -g option with no specified ID)

    <b>rx_entries</b>                          REGEX for extracting main entries table (e.g. <article>.*</article>)

    <b>rx_title, rx_link, rx_desc,</b> 
    <b>rx_author, rx_category,</b>
    <b>rx_text, rx_images, rx_pubdate          REGEX lines for parsing entry strings list extracted by <b>rx_entries</b>.
                                               Non-empty <b>Title</b> and <b>Link</b> is required
                                               Only the first match for each is processed

        Fields <b>rx_images</b> and <b>rx_link</b> can be also used to extract image hrefs or resource links respectively from description and text fields
        after fetching with rss handler (in case those entities have non-standardd markup for a particular feed)


    <b>rx_pubdate_feed, rx_image_feed</b>
    <b>rx_title_feed, rx_charset_feed</b>      
    <b>rx_lang_feed</b>                        REGEXes for extracting head/meta information for whole channel.
                                               Only the first match for each is processed

    <b>script_file</b>                         Script used for fetching for this Channel
                                               Script should return a JSON string with entries (see <b>--help-scripting</b> for specification)


    <b>icon_name</b>                           Stock icon name for display for this Channel (it overwrites downloaded image)

    <b>display_order</b>                       Order in which a Channel/Category should be displayed in CLI and GUI



Every field can be changed with --edit-feed [ID] [FIELD] [VALUE] command, where [FIELD] is a name from above


""")






FEEDEX_HELP_ENTRIES=_("""

<b>Feedex: Entries</b>

Entries are downloaded news articles (see -c and -g options) and notes added by users (see --add-entry).
Text fields are stripped of html using re. Images and links are extracted and saved.  
Entries are stored in DB in 'entries' table. Below, are field descriptions:

    <b>id</b>           unique identifier (integer)
    <b>feed_id</b>      ID of Feed or Category this Entry belongs to (feed and category IDs do not overlap)
                        to change use: <b>parent_category</b>, <b>feed</b>, <b>parent_id</b> or <b>feed_id</b>
    
    <b>charset</b>      character encoding used in this entry ('utf-8' by default)
    <b>lang</b>         language used in this entry. If not provided in RSS/Atom, it will be heuristically detected
    
    <b>title, author, author_contact, contributors, publisher, publisher_contact, category, tags</b> - data from RSS headers
    <b>desc</b>                Description section (manually added entries fill up title and desc fields)
    
    <b>link</b>                Link to article
    <b>pubdate</b>             Epoch-encoded publication date
    <b>pubdate_str</b>         Publication date - human readable
    
    <b>guid</b>                Global identifier for entry provided by publisher (these, and links, are checked at parsing
                                to avoid duplicates)
    
    <b>comments, source, links</b>    Data extracted from respective feed sections

    <b>text</b>                This field contains all text found in 'contents' section of an RSS/Atom. HTML is stripped,
                                links to images are extracted and saved at 'images' field
    
    <b>addate</b>              Epoch-encoded date when entry was added to DB/modified
    <b>addate_str</b>          Added date - human readable

    <b>read</b>                 How many times was an entry opened (-o section) or marked. User-added, not downloaded entries
                                are assigned status equal to default_entry_weight configuration parameter (2 if not given). 
                                Feedex extract learning features from entries with read > 0 to use them for ranking of
                                incoming news (see --mark option). Status also influences the weight of features learned
                                from an entry.
    <b>importance</b>          This is a rank assigned by matching learned rules. New entries are sorted by this field
        
    <b>sent_count</b>          Sentence count
    <b>word_count</b>          Word count (non-punctation tokens)
    <b>char_count</b>          Character count
    <b>polysyl_count</b>       Count of polysyllables (words with >3 syllables)
    <b>com_word_count</b>      Commond word count. Common words are checked against lists predefined in language model
    <b>numerals_count</b>      Count of numerals
    <b>caps_count</b>          Count of capitalized words (for bicameral languages)
    
    <b>readability</b>         Purely heurstic readability measure added as a token prefixed with MX. Found in ling_processor module
    <b>weight</b>              A number to compensate for document length and information content, so that very long articles are not 
                               ranked at the top by virtue of length alone. Calculations found in ling_processor module

    <b>flag</b>                Increased whenever flagging rule is matched. It causes entry to be highlighted on output.
                               Useful for catching important keywords or phrases regardless of learned ranking (see --flag option)

    <b>images</b>              Links to images extracted from HTML
    <b>enclosures</b>          Links to other data/media

    <b>deleted</b>             Was Entry moved to Trash?
    <b>note</b>                Is entry a News item or user's note?

    <b>node_id</b>             Parent node entry ID 
    <b>node_order</b>          Entry's order within parent node 

    <b>ix_id</b>               Entry ID in Xapian index 
    

Each of those fields can be sorted by using --sort,--rsort query parameter.
Fields: 'author','publisher','contributors','title','tags','category' can be specifically searched
in query. If no field is given, every each text field will be searched

For <b>--add-entry-from-file</b> and <b>--add-entry-from-pipe</b> or <b>script</b> handler, input can be given to mass-insert entries.
Input needs to be in JSON format or list of dicts, as in:

[  
{'feed_id' : <int>, (must be provided and > 0)
... other fields from above ... 

},
... other entries ...
]

Fields other than:
'feed_id','read','flag','charset','lang','title', 'desc', 'text', 'author', 'publisher', 'contributors',
'author_contact', 'publisher_contact', 'link', 'pubdate_str', 'guid', 'category'
'tags','comments','source','links','images','enclosures', 'deleted', 'note', 'node_id', 'node_order'

... will be overwritten or ommitted on processing linguistic data, text statistics and database compatibility

""")




FEEDEX_HELP_RULES=_("""

<b>Feedex: Rules</b>

Each downloaded entry in checked against saved rules. For each entry importance is calculated and it is used to rank news against 
your intersts and preferences. Rules can be learned or added manually. Both contribute to importance, but if manually added rule
is matched an entry if flagged for highlighting at output (see --flag option) (this can be overriden by rule data). 
Each rule is ascribed to its entry (context), and entry's read status or amount of times opened (see --mark option) multiplies importance 
given from this particular rule. 
Each entry has 'weight' field, that is also multiplied when matching to offset advantage given to long news articles.

Each rule's weight is also multiplied by weight of a field it was extracted from, e.g. you will want title to bear more weight
than text. Field weight is implemented during feature learning

Learned rules are simply features extracted by ling_processor according to tagging and rules whenever entry is opened in browser
or marked. Example language model is described in comments in <b>sample_model_generator.py</b> in 'utils' folder along with mechanism
used for analysis, extraction, tagging and tokenizing.

Rules are stored in DB in rules table. Below are field descriptions:

    <b>id</b>                   unique identifier for a rule (integer)
    <b>name</b>                 name of rule used for display (<i>not matching!</i> Display only)
    <b>type</b>                 matching type of a rule:
                                values:
                                    string, 0   - simple string matching
                                    full, 1     - simple stemmed matching
                                    regex, 2    - REGEX search

    <b>feed_id</b>              ID of a feed or category whose entries are exclusively matched against this rule
                                to change use: <b>category</b>, <b>feed</b> or <b>feed_id</b>
    <b>field_id</b>             ID of a field to be matched by a rule, also: <b>field</b>
                                values: 'author','publisher','contributors','link','title','tags','category' 

    <b>string</b>               string to be matched according to rule type
    <b>case_insensitive</b>     is match case insensitive? 1 or 0
    <b>lang</b>                 what language (of an entry) rule applies to
    <b>weight</b>               increase in importance from this rule (later multiplied by context status and entry weight)
    <b>additive</b>             if rule importance additive or one-time
    <b>learned</b>              is rule learned?
                                values 1-learned, 0-manually added
    <b>flag</b>                 Is rule flagging matched entry? Default is YES
    <b>context_id</b>           ID of an entry that this rule comes from

    
Manual and search phrase rules can be deleted and edited by ID
(see --list-rules)
Fresh databases have no rules. As said before, they are learned by opening articles and adding notes.
Rules can be relearned using --relearn option.




<b>Feedex: Flags</b>

Flags are manual markers for Entries that can be searched for. Entry can be flagged if matched by a Rule (id specified - see above).
If more than one differently-flagged Rules are matched, frequency distribution is constructed with Rules' weights and maximum is selected.
Flags were added to allow more detailed classification of Entries and News.
They are stored in flags SQL table. Field description:

    <id>                        Unique identifier (integer)
    <name>                      Flag's name for display
    <desc>                      Flag's description
    <color>                     Color used to mark flagged entry in GUI. <i>Must be in #FFFFFF format</i> 
    <color_cli>                 Color used to mark flagged entry in CLI
                                Possible values:
                                    WHITE, WHITE_BOLD, YELLOW, YELLOW_BOLD, CYAN, CYAN_BOLD, BLUE, 
                                    BLUE_BOLD, RED, RED_BOLD, GREEN, GREEN_BOLD, PURPLE, PURPLE_BOLD, 
                                    LIGHT_RED, LIGHT_RED_BOLD

""")




FEEDEX_HELP_SCRIPTING=_("""
<b>Feedex: Scripting</b>

If Feed's handler is specified as <b>script</b> a user-specified command from <b>script_file</b> field (<b>feeds</b> table) is ran on fetching.
Its output, assumed to be a <b>JSON string</b> (see below), is then parsed and loaded for processing just like RSS. Errors should be handled within
the script, as STDERR is not analysed. User should take special care for the script not to cause unacceptable lattency or infinite loop, as fetching
process waits for output and blocks while waiting.

Several parameters can be passed in the command and be replaced by variables:

    <b>%A</b>   User Agent (feed-specific or global)
    <b>%E</b>   Last saved ETag
    <b>%M</b>   Last saved 'Modified' tag
    <b>%L</b>   Feed's login
    <b>%P</b>   Feed's password
    <b>%D</b>   Feed's auth domain
    <b>%U</b>   Feed's URL
    <b>%F</b>   Feed's ID
    <b>%%</b>   % character

<b>Output JSON string should have specific format:</b>

{
<i>#HTTP return headers...</i>
'status': <i>#HTTP return status, must be 200, 201, 202, 203, 204, 205 or 206 for Feedex to save results to DB</i>
'etag': ...
'modified': ...

<i>#Feed data...</i>
<b>feed</b>:  {
                    'title': ...
                    'pubdate': <i>#Updated date string</b>
                    'image': <i>#link to feed's icon/emblem</i>
                    'charset': ...
                    'lang': <i>#Language code, e.g. 'en'</i>

                    <i>#List of entries/articles to process</i>
                    entries : [ 
                                {
                                    <i>#Mandatory fields:</i>
                                    'title': ...
                                    'link': ...

                                    <i>#... and other optional fields - see --help-entries for details</i>

                                },
                                ...
                                ]

                }

}



<b>Feedex: JSON queries</b>

You can query Feedex by using JSON string as a phrase and --json_query parameter. All filters will be overwritten by fields from JSON string.
Fields are:
{ 
    <i>phrase</i>: search phrase
    
    <i>lang:</i> query language (for stemming)
    <i>handler:</i> filter by handler (rss, html, script, local)

    <i>field:</i> which field to search (title, desc, author etc.)
    <i>qtype:</i> query type (FTS, string matching)

    <i>date_from, date_to:</i> filter by published dates
    <i>date_add_from, date_add_to:</i> filter by added/modified date

    <i>feed, category, parent_category, feed_id, parent_id </i>: filter by channel/category
    <i>importance:</i> importance greater than FLOAT

    <i>note:</i> is a note? (True/False)
    <i>news:</i> is a news item? (True/False)

    <i>case_ins, case_sens:</i> case sensitivity (True/False)
    <i>logic:</i> FTS query logic (any, all, etc.)
    
    <i>last:</i> filter by last update (True/False)
    <i>last_n:</i> filter by last N updates (INT)

    <i>today:</i> filter for today (True/False)
    <i>last_hour:</i> filter for last hour (True/False)
    <i>last_week:</i> filter for last week (True/False)
    <i>last_month:</i> filter for last month (True/False)
    <i>last_quarter:</i> filter for last 3 months (True/False)
    <i>last_six_months:</i> filter for last 6 months (True/False)
    <i>last_year:</i> filter for last year (True/False)

    <i>read, unread:</i> filter by read/unread status (True/False)

    <i>deleted:</i> show deleted entries (True/False)

    <i>sort:</i> sort by field value (precede field name qith + or - for asc/desc, e.g. +author, -pubdate)
    <i>rev:</i> reverse sort order (True/False)

    <i>group:</i> group results by field (channel, category, flag, day, week, month)
    <i>depth:</i> grouping depth (first n results for each node according to sort order)

}


""")






FEEDEX_HELP_HTML=_("""
<b>Feedex: HTML Output</b>

Using the --html-template= option user can output results in a predefined HTML format. Every result is processed and marked field names
in the template are replaced with relevant fields. HTML special characters are escaped. Nearly every query can be processed in this way.

Field names must be contained within <%,%> strings, e.g. '<%title%>' will be replaced with the field 'title' from result. 

If field by a given name is not found, no changes will be made.

<b>Additional options:</b>

    --to-files-at-dir=[TARGET_DIR]      Save as separate files at TARGET_DIR - for mass-generated content
    --to-files-names=[STR]              Naming pattern for created files. STR is parsed the same as template (<%field%> is valid)
                                        Field valus will be truncated. Spaces and special characters will be escaped with _ character.
                                        User must take care of uniqueness. Good practice would be including <%id%> field in name string.
                                        Example:
                                            --to-files-names='<%id%>_<%pubdate_str%>_<%title%>.html'


<b>Field names:</b>

    Field names are the same as SQL fields described in <b>--help-entries</b>, <b>--help-feeds</b>, and <b>--help-rules</b> sections.

Some queries have additional fields:

    Query with phrase:

        rank                Result ranking (tf-idf or Xapian)
        count               Count of phrase occurrences
        snippets            A list of snippets 


    All querries for entries:

        feed_name           Name of Channel/Category
        parent_name         Name of Feedex Category 
        feed_name_id        Name of Channel/Category with ID
        flag_name           Name of Flag
        pubdate_short       Short version of Published Date

    Entries grouped in a summary have additonal 'is_node' field (1 means this row is a node)


    Time series queries have only two fields:

        time                The time slice (depends on grouping)
        frequency           Term/Document frequency

    Contexts have additional 'context' field

    Related terms:
        term, weight, count

    Keywords for etry: 
        term, weight

    

<b>EXAMPLE:</b>

<!DOCTYPE html>
<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html;charset=UTF-8"/>
        <meta name="date" content="<%pubdate_str%>"/>
        <meta name="title" content="<%title%>"/>
        <meta name="url" content="<%link%>"/>
    </head>

    <body>
        <a class="ulink" href="<%link%>"><%title%></a> (<%feed_name%>, <%author%>)
        <p>
        <%pubdate_str%>
        </p>

        <p>
        <%category%>
        </p>

        <p>
        <%desc%>
        </p>
        <p>
        <%title%>
        </p>

    </body>
</html>
<!!!--------------------------------------------- doc section for splitting

""")