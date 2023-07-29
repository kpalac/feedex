

ABOUT

FEEDEX is a modern news and notes aggregator to help you monitor, classify, group, rank and display your favourite news sources. 

Features:

  - RSS/Atom protocols (using Universal FeedParser)
  - HTML protocol. Downloaded resources can be parsed by predefined REGEX strings and saved as entries just like RSS items
    allowing you to monitor webpages that do not support RSS
  - External scripting support. News can be fetched by scripts (output should be JSON)
  
  - Support for rules and flags that can be manually added. This allows to automatically parse incomming entries for interesting information and flag/rank them accordingly. Flagging rules effectively act as alerts
  - Channels can be grouped into categories
  - Entries can be manually added to Channels and Categories as notes, hilights etc.
  - Entries that are read by you (openned in browser or added manually) are marked as interesting and keywords are automatically extracted from them to recommend interesting articles

  - Support for desktop notifications on incomming news or in scripting
  - Desktop clipboard integration with selected text and window names. They can be used for manually adding entries, e.g. by keyboard shortcut. This enables you to hilight some text and quickly add it to a database and contribute to ranking.
  - Feedex can be used solely as a CLI tool and in shell scripts

  - Support for queries:
      a) Full Text Search - with stemming or exact (using Xapian indexing library) and advanced wildcards such as Roman numerals, math symbors, currencies etc.
      b) String matching

      Queries support wildcards and also FTS allows proximity search. Searching by field is possible. Multiple filtering options.
      c) Recommendations based or previously read items
      d) Term contexts - display contexts in which a term appears
      e) Similarity search - find document similar to one selected
      f) Time series - generate time series for a term, choose grouping (can generate a plot)
      g) Document's relevance in time - generate time series of document's keywords (can generate a plot)
      h) Term relatedness - which terms go together
      i) Grouping by category, channel or flag with preferred depth, allowing for nice news summaries in a form of a tree
        i.1) Grouping by similarity, i.e. collapsing similar articles into a best choice to compact long lists
        i.2) Grouping by months, days or hours
      j) Extracting trending terms from a group of articles
      k) Ranking articles according to trends (i.e. "most talked about")
      l) Text summarization
      m) Extensive Feed catalogue based on https://blog.feedspot.com for subscribing and searching channels 

  - Exporting results to CSV or JSON

  - Keyword extractiom is based on language models - no fancy stuff here - just phrase lists and extraction rules. Currently english, polish, russian and german are supported. Model generators can be found in data directory to modify and generate new models based on word lists and dictionaries. See smallsem.py module for more information on how basic NLP is done by Feedex 

  - Full documentation can be viewed by feedex -hh option


INSTALLATION:

  LINUX:
    - Unpack ZIP and/or copy /feedex folder to temporary location
    - Change current directory to copied folder
    UBUNTU, DEBIAN:
    - Run install_apt.sh script in the base directory, to install all files to your system along with dependencies. (You need an active internet connection)

  
ACKNOWLEDGEMENTS:

    Kurt McKee (FeedParser)
    People to thank for Snowballstemmer: https://snowballstem.org/credits.html
    Kozea community (Pyphen)
    Fredrik Lundh (PIL author), Alex Clark (Pillow fork author) and GitHub Contributors
    daniruiz (Super Flat Remix icon theme)
    Qogir-ubuntu icon theme creator(s)
    Kim Saunders <kims@debian.org> Peter Ãstrand <astrand@lysator.liu.se> (XClip)
    https://blog.feedspot.com team for resources for feed catalogue

    If I failed to give credit to someone, please inform me and accept my apologies
    

CONTACT: Karol Pałac, palac.karol@gmail.com

Feel free to modify and play around :)





