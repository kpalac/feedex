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

        -r, --read-entry [ID]                   Read entry/news article contents by ID (--summarize=1..100 for text summary, --details for keywords and rules)
        -o, --open-in-browser [ID|URL]          Open link of an entry by ID or URL. Register openning and learn keywords/rules for later ranking

        -F, --read-feed [ID]                    Get all entries from a Channel specified by ID
        -C, --read-category [ID|NAME]           Get all entries for a specified Category

        -q, --query [Phrase]                    Query entries with search phrase (see --help-query option for details)
        -R, -recommend                          Show recommended articles
                    
        -qc, --query-catalog [PHRASE]           Query Feed Catalog for Channels to import
        
        --long                                  Show long output for queries
        --headlines                             Output only date, title and channel

        --create-db                             Create database in default location or specified by <b>--database=PATH</b>
                                                Additional options:
                                                    --defaults      Import default Flags, Rules etc.
                                                    --default-feeds Import default Feeds 

    <b>!!! See feedex -hh for full manual !!!</b>
        --help-query                            Manual for Queries
        --help-feeds                            Manual on Feeds and Ctegories 
        --help-entries                          Manual on Entries (articles, notes, hilights etc.)
        --help-rules                            Manual on rules, ranking and flags
        --help-scripting                        Manual for scripting
        --help-examples                         Command line examples

""")




FEEDEX_HELP_DESC=_("""
                   
""")



FEEDEX_LONG_HELP=_("""
Usage: <b>feedex [parameters|filters] [actions] [arguments]</b>

    Feedex lets you organize your news and notes. It features recommendations, trend analysis, context search, time series,
    term relatedness, similarity search and more. It can parse RSS/Atom feeds, HTML pages as well as JSON input from custom scripts.
    User can define rules for flagging incomming articles or simply boosting them to the top. 
    Keywords learning from opened or marked entries is used for recommendation system. 
    Feedex also supports text summarization, desktop notification and adding item from desktop's selected text buffer (e.g. from a hotkey)
    for adding notes and hilights that can be used to learn topics interesting to user.

    Technical notes:
    Feedex uses <b>SQLite</b> database to store data and <b>Xapian</b> for indexing. Ranking, indexing, feature learning and text summary
    are performed by heuristic language models in <b>smallsem</b> module with "good enough" precision-performance balance. 
    RSS is handled by <b>UniversalFeedParser</b> library. Resources like images and HTML documents are handled with <b>URLLib</b>.
              

    <b>General:</b>
        -h, --help                              Show short help
        -hh, --help-long                        Show this help
        -v, --version                           Version info
        --about                                 About Feedex...

    <b>Display parameters:</b>
        --csv                                   Output in CSV format (no interlines and colours/beautifiers)
        --json                                  Output as standard JSON string
        --long                                  Output long version
        --headlines                             Output only date, title and channel

        --display-cols=STR                      Which columns should be displayed in results? A comma separated list consisting of valid field names (entries, feeds, rules etc.)
                                                You can also add snippets, rank, counk etc. 
                                                e.g. --display-cols=title,date,rank,snippets
        
        --export, --export=FILE                 Export results as JSON string compatibile for later import (query results-entries, feeds, rules, flags)
        --ofile=FILE                            Output file for export

        --silent                                Do not print output

        --trunc=INT                             Truncate output of fields to INT chars (0 for no truncation)
        --delimiter=STR                         Change field separator (cli/csv), delault |
        --delimiter2=STR                        Change item separator inside field, e.g. for snippets and contexts (cli/csv), delault ;
        --escape=STR                            Escape sequence for delimiters (useful for CSV)

        --note_marker=STR, --read_marker=STR    Strings to mark read items and notes in CLI output

        --bold_beg=STR, --bold_end=STR          Strings to be inserted as bold markup beginning/end. Used for displaying snippets, to hilight
                                                the search phrase. Defaults are <b>,</b>

        --desktop-notify                        Show desktop notifications instead CLI output (-g, -c, and --query)
                                                and inform about adding new entries, rules and feeds from URL
                                                Useful for scheduled tasks and keyboard shortcuts (e.g. adding a hilighted note with --clipboard)

        --clipboard                             Enable destkop clipboard/selection support. Selection and window title can be used in arguments
                                                for actions: add-entry, add-feed, add-rule, add-regex, add-full-text, add-full-text-exact
                                                Substitutions:  
                                                    %%  -   % character
                                                    %s  -   current text selection
                                                    %w  -   curent window name 


    <b>Fetching:</b>
        -g, --get-news [ID]                     Get news without checking intervals, ETags or Modified tags (force download). Limit by feed ID
        -c, --check [ID]                        Check for news (applying intervals and no force download with etag/modified). Limit by feed ID

        -o, --open-in-browser [ID|URL]          Open entry by ID or URL in browser. Openned items are marked as important.
                                                Features are extracted from it for future recommendations
                   
        --list-fetches                          Display fetching history. Ordinals can be used in query with last_n filter

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
        --list-feeds-cats                       List Category/Channel tree
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
                                                --summarize=INT    Give summarization level for this entry for display (1..100)
                                                --details          Show keywords and rules matched for this entry

        --mark [ID] [N]                         Mark entry as read N times (important for future recommendation)
                                                options:
                                                --learn,--no-learn         Extract patterns from Entry?
        --unmark [ID]                           Unmark entry

        --flag [ID] [N]                         Set entry's flag

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
        
        -q, --query [PHRASE]                    Query entries with a search phrase. See --help-query option for detailed manual
                                                
        -R, --recommend                         Show entries recommended for user (filters as for query)
        --trending [PHRASE]                     Show trending entries for given filters (filters as for query)
                                                                
        --context [PHRASE]                      Show contexts for given terms (parameters as in query, contexts taken from results)

        --trends [PHRASE]                       Show trends (frequent keywords) for filterred entries (filters as for query)
            
        --term-net [PHRASE]                     Show terms connected to a given term by context (parameters:lang)
        --time-series [PHRASE]                  Show time distribution of a term (filters like in --query) 
                                                parameters:
                                                --lang=          language used for query
                                                --group=         grouping (hourly, daily, monthly)
                                                --plot           plot data points in CLI
                                                --term-width=    width of terminal window (for aestetics)

        -S, --similar [ID]                      Find similar entries to ID'd (filters like in --query)
                                                --limit=INT        Limit results to INT-best (inproves performance)
        --rel-in-time [ID]                      Entry's relevance as a time series - like --time-series for entry's keywords (filters like in --query)
                                                --limit=INT        Limit results to INT-best (inproves performance)

        -qc [PHRASE], --query-catalog [PHRASE]  Query Feed Catalog for Channels to import 
                                                They can then be imported by using <b>--import-from-catalog [COMMA_SEPARATED_ID_LIST]</b> option
                                                --category=[ID|NAME]    filter results by categories. Enter empty query to list all categories
                                                --field=[NAME]          query only certain fields:
                                                                            name, desc, location, tags  
                   
                                                
                   
    <b>Handlers:</b>
        Every Feed has a protocol handler specified:
        <b>rss</b>      RSS protocol (needs a valid URL)
        <b>html</b>     Fetch a HTML page and parse it with REGEXes from rx_... fields
        <b>script</b>   Run a script to fetch for this channel specified in <b>script_file</b> field
        <b>local</b>    No internet protocol. Feeds are not fetched from the Internet, but can be populated by scripts (see --add-entries-from-file/pipe)

    <b>Rules:</b>
        User can define rules to flag or boost incomming articles/notes. Flags are defined by user.
        See <b>--help-rules</b> for more info

        --list-rules                            Show all rules

        -K, --add-rule [TEXT]                   Add simple string matching rule ($,^,*) wildcards are allowed
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
                                                
        --add-regex [TEXT]                      Add REGEX rule
                                                (parameters: as in previous option)
        --add-full-text [TEXT]                  Add stemmed and tokenized query rule. Wildcards and logical operators are not supported
                                                (parameters: as in previous option)

        --edit-rule [ID] [FIELD] [VALUE]        Edit ID'd Rule. Change [FIELD] to specified [VALUE]. 
                                                \\NULL or \\NONE means NULL value
                                                See --help-rules for field names

        --delete-rule [ID]                      Delete rule by its ID (see: --list-rules)



    <b>Flags:</b>
        --list-flags                            Display all Flags
        --add-flag [NAME] [DESC]                Add new flag with given NAME and optional DESCription
        --edit-flag [ID] [FIELD] [VALUE]        Edit flag by ID
        --delete-flag [ID]                      Delete flag by ID


    <b>Misc:</b>
        --clear-history                         Clear search history
        --delete-learned-keywords               Deletes all learned keywords (<i>use cautiously</i>)
        --empty-trash                           Permanently removes all Entries, Feeds and Categories marked as deleted


    <b>Data and Dev:</b>
        
        --export-rules [FILENAME]               Export added rules to JSON file
        --import-rules [FILENAME]               Import added rules from JSON file to current DB

        --export-feeds [FILENAME]               Export saved news channels to JSON file
        --import-feeds [FILENAME]               Import saved news channels from JSON file to current DB

        --export-flags [FILENAME]               Export saved flags to JSON file
        --import-flags [FILENAME]               Import saved flags from JSON file to current DB

        --export, --export=FILE                 Export results as JSON string compatibile for later import (query results-entries, feeds, rules, flags)

        Exports/imports can be used to move data between DBs. In addition you can export query results with --ofile option
        and then import it to new DB with --add-entries-from-file. This way you can archive or trim big databases.


        --reindex [ID]                          Index and relculate linguistic stats and tokens for all/IDd entry
        --rerank [ID]                           Recalculate importance and flag stats for all/IDd entry
        --relearn [ID]                          (Re)learn features from all read entries/IDd entry

        --batch_size=INT                        The size of processed entries before committing

        
        --download-catalog [OUTPUT DIR]         Download feed catalog from blog.feedspot.com. For development and testing

                                                    
    <b>Database:</b>
                   
        --create-db                             Create database in default location or specified by <b>--database=PATH</b>
                                                Additional options:
                                                    --defaults      Import default Flags, Rules etc.
                                                    --default-feeds Import default Feeds 
        
        --lock-db, --unlock-db                  Force-lock/unlock database (use with caution)

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
        10      Language processing error
        11      Index error
        12      Configuration error

    <b>Debug levels:</b>
        1       All
        2       Database messages
        3       Handler messages
        4       Locks
        5       Query messages
        6       I/O messages
        7       Data validation
        10      Language processing        


""")



FEEDEX_HELP_EXAMPLES=_("""

<b>Feedex: Command examples</b>
        
        <b>feedex --sort=adddate --rev --category=Hilights -q</b>
            Show all documents in "Hilights" category and reverse-sort them by date added
        
        <b>feedex --sort=pubdate -F=1 -q</b>
            Show all news for feed 1 and sort them by publication date

        <b>feedex --sort=pubdate --feed=2 --unread -q</b>
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

        <b>feedex --desktop-notify --clipboard --weight=10 --add-rule '%s'</b>
            Add new keyword from selected text and notify about it to desktop

        <b>feedex --json_query -q '{"phrase":"test", "last_week":true, "case_sens":true, "read":true}'</b>
            An example usage of JSON query

        <b>feedex --export --ofile=feed_data.json --list-feeds && feedex --database=target.db --import-feeds feed_data.json
            Moving feed data from one database to the next


""")








FEEDEX_HELP_QUERY=_("""

<b>Feedex: Query </b>


<b>Query Phrase</b> is the text you are searching for. Depending on query type it has certain features:

    Full Text Search:
        Escape Character: \\
                                                
        Capitalized tokens are treated as unstemmed/exact
                                                    
        Special operators:
            logical: OR, AND, NOT, (, )
            proximity: NEAR, ~[NUM_OF_WORDS], ~
            
            wildcards: 
                *          - any character string
                <DIV>      - divider (period, punctation etc.)
                <NUM>      - numeral
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
                                                        

        
Query is defined by by <b>parameters</b>:
                                                    
    --type=         type of qery
                        'fts' - full text (default)
                        'string' - simple string matching    --lang=         language used in query for tokenizing and stemming
    
    --case_ins      query is case insensitive
    --case_sens     query is case sensitive
    --field=        field to search. 0 or None for all.
                    Available fields: <b>author, publisher, contributors, title, tags, category, comments</b>
    
    --logic=        How should fts terms be connected by default?
                        'any' - any term matches (OR)
                        'all' - all terms must match (AND)
                        'near' - evaluate terms' proximity
                        'phrase' - treat terms as a phrase
                                                
    --sort=          sort by comma-separated fields (see --read-entry for field names)
                        add '-' before field name for reverse sort on it
                        e.g.: --sort=flag,-importance,readability

    --rev            display in reverse order
    
    --group=         Display as a tree grouped by this parameter 
                     Available groupings: <b>category, feed, flag, hourly, daily, monthly, similar)</b>
    --depth=         Integer telling the depth of each node for grouping. If 0, every result is shown
                     If no grouping was selected, simply first N results will be shown


Query can also be <b>filtered</b> by parameters:
                                                 
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
                            'all' - flagged and unflagged entries (default)
                            'no'  - only unflagged entries
                            'all_flags' - include all flags
                            [INT] - choose a flag to filter by (by ID)
    --note, --news   limit to only user's Notes/News items 
    --handler=       limit to feed handler (rss, html, script, local)
    --deleted        indlude deleted feeds, categories and entries

    Paging of results:
        --page=INT           page number (default is 1)
        --page_len=INT       page length (default is 3000)
                                                

<b>Misc:</b>
    --json_query            parse query argument as JSON and extract filters/phrase from it. Useful for scripts.
                            see <b>--help-scripting</b> for details
 


<b>Fields available for --display_cols output option (apart from database fields):<b>

    <b>Entries/Contexts:</b>                            

        <b>feed_name</b>            Name of the parent feed
        <b>feed_name_id</b>         Name of the parent feed with ID
        <b>pubdate_r</b>            Human-friendly pubdate
        <b>pubdate_short</b>        Short vershion of humanized pubdate
        <b>flag_name</b>            Name of flag if present
        <b>user_agent</b>           User agent used to download this resource
        <b>parent_name</b>          Name of the top parent (feed or category, if present)
        <b>parent_id</b>            ID of the top parent
    
        <b>is_deleted<b>            Marked deletion of parent or present entry
    
        <b>sread</b>                Humanized "read" markes (Yes/No)
        <b>sdeleted</b>             Humanized "deleted"
        <b>snote</b>                Humanized "note"

        <b>snippets</b>             Snippet list
        <b>rank<b>,<b>count</b>     Rank/count from query if phrase was present

        <b>is_node</b>              Is this result a node (e.g. in grouped queries)
        <b>children_no</b>          How many children does this node have?

        <b>context</b>              This is available only for context query
    
    

    <b>Term Nets/Keywords/Trends:</b>
        
        <b>term</b>                 Basic term form
        <b>weight</b>               Term's weight
        <b>search_form</b>          Stemmed term form


    <b>Time series:</b> 
        <b>time</b>                 Time series item
        <b>from</b>                 Start of grouping interval
        <b>to</b>                   End of grouping interval
        <b>freq</b>                 Term/Entry frequency

""")





FEEDEX_HELP_FEEDS=_("""

<b>Feedex: Feeds</b>

Feeds (news Channels) are downloaded and parsed using handlers (rss, html) or populated by scripts ('script' handler).
Local handler marks feeds not updagted (storage only).
Unless used with -g option, Feedex will respect etags and 'modified' tags if provided by publisher. 
It will also check for news duplicates before saving. 
HTTP return codes are analysed after download. If channel gave too many HTTP errors in consecutive tries, it will be
ignored. To try again one needs to change error parameter using <b>--edit-feed [ID] error 0 </b>

A feed/channel's metadata can be updated periodically (autoupdate field) to check for changes. If channel is moved permanently, 
new URL will be checked and saved. If channel moved temporarily, it will download from new location but keep old URL.

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
    
    <b>recom_weight</b>                        Aggregate of marked entries for this feed, used in recommendation



Every field can be changed with --edit-feed [ID] [FIELD] [VALUE] command, where [FIELD] is a name from above

                       
<b>Categories</b> are used to group feeds or assign notes to. They are not fetched from, but are stored in the same table for convenience.

""")






FEEDEX_HELP_ENTRIES=_("""

<b>Feedex: Entries</b>

Entries are downloaded news articles (see -c and -g options) and notes added by users (see --add-entry).
Text fields are stripped of html using re. Images and links are extracted and saved.  
Entries are stored in DB in <b>entries</b> table. Below, are field descriptions:

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

    <b>read</b>                How many times was an entry opened (-o section) or marked. User-added, not downloaded entries
                               are assigned status equal to default_entry_weight configuration parameter (2 if not given). 
                               Feedex extract learning features from entries with read > 0 to use them for ranking of
                               incoming news (see --mark option). Status also influences the weight of features learned
                               from an entry.
    <b>importance</b>          This is a rank assigned by matching rules. 
        
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

    <b>flag</b>                User-defined flag assigned to entry by rules or manually
                      
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

Rules are used to boost and flag incomming news/notes.                    
Rules are stored in DB in <b>rules</b> table. Below are field descriptions:

                    
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
    <b>lang</b>                 what language (of an entry) is used for stemming and tokenizing?
    <b>weight</b>               importance boost from this rule
    <b>additive</b>             if rule importance additive or one-time
    <b>flag</b>                 Should rule flag matched entry? If multiple flags match, the most common is chosen

    
Rules can be deleted and edited by ID
(see --list-rules)




<b>Feedex: Flags</b>

Flags are user-defined entities with name, description and color. They can be assigned by rule or manually.
They are stored in <b>flags</b> table. 
Fields:
                    
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

If Feed's handler is specified as <b>script</b> a user-specified command from <b>script_file</b> field (<b>feeds</b> table) is executed on fetching.
Feedex then reads contents of <b>temp file</b> (expected to be in JSON format) and treats it as incomming feed data.
Temp file path is passed as <b>%T</b> parameter to command or <b>FEEDEX_TEMP_FILE</b> env variable. 
Script must populate it with a valid JSON structure (see below)
It is also up to the script to prevent hanging, infinite loops and errors as Feedex will wait for the script to finish.
                        
Feed data can be read from another temp file (<b>FEEDEX_TEMP_FILE_FEED</b> env variable or <b>%I</b> argument).
It is encoded in JSON format. 

Following arguments can be passed in the command and be replaced by variables:

    <b>%T</b>   Transfer temp file path (raw feed data in JSON)
    <b>%I</b>   Input temp file path (feed data in JSON)
    <b>%A</b>   User Agent (feed-specific or global)
    <b>%E</b>   Last saved ETag
    <b>%M</b>   Last saved 'Modified' tag
    <b>%U</b>   Feed's URL
    <b>%F</b>   Feed's ID
    <b>%%</b>   % character

                        
<b>JSON structure in transfer file should have specific format:</b>

{
<i>#HTTP return headers...</i>
'status': <i>#HTTP return status, must be 200, 201, 202, 203, 204, 205 or 206 for Feedex to save results to DB</i>
'etag': ...
'modified': ...

<i>#Feed data...</i>
<b>feed</b>:  {
                    'title': ...
                    'pubdate': <i>#Updated date string</i>
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
""")



FEEDEX_HELP_JSON_QUERY = _("""
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








FEEDEX_HELP_PLUGINS = _("""
<b>Feedex: Plugins</b>

Plugins allow user to run scripts/commands on various Feedex items:

    -   Selected text (useful e.g. for custom browser searches)
    -   Query results  (useful for exporting results to other formats)
    -   Feedex entities (e.g. selected entry, feed, or category) 

                        
Data in JSON format is transferred using temp file whose path is transferred to script by:

    <b>%T</b>                       parameter in command line argument
    <b>FEEDEX_TMP_FILE</b>          environment variable

                        
If plugin processes text selection, data is transferred to script by:

    <b>%S</b>                       parameter in command line argument
    <b>FEEDEX_SELECTED_TEXT</b>     environment variable
                        

When executing a plugin command substitutions will be made:
                        
    <b>%%</b>                       Percent (%) character
                        
    <b>%t</b>                       Table type for result list               

    <b>%choose_file_save%</b>       File chooser dialog for a new file will be displayed 
                                    and chosen filename will be substituted for this string        
    <b>%choose_file_open%</b>       File chooser dialog for an existing file will be displayed 
                                    and chosen file will be substituted for this string        
    <b>%choose_dir_open%</b>        Folder chooser dialog will be displayed 
                                    and chosen folder will be substituted for this string        

                        
Following environment variables are available:

    <b>FEEDEX_TABLE</b>             Result table type (e.g. entries, feeds, rules, terms, time_series, keywords)
    <b>FEEDEX_FIELDS</b>            Semicolon-separated list of result fields
                                 

Output from executed command will be send to status bar. 
Pipes and redirecting are not allowed.
                        
Plugin examples can be found in data-examples-plugins folder.

""")