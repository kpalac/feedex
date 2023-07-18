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
import socket

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






# Our modules
from feedex_data import *
from feedex_utils import *
from feedex_containers import SQLContainer, SQLContainerEditable, ResultEntry, ResultContext, ResultFeed, ResultRule, ResultFlag, ResultTerm, ResultTimeSeries, ResultHistoryItem, FeedexHistoryItem, FeedexFlag

from smallsem import SmallSem
from feedex_nlp import FeedexLP

from feedex_feed import FeedexFeed, FeedexCatalog, ResultCatItem
from feedex_entry import FeedexEntry
from feedex_rule import FeedexRule

from feedex_handlers import FeedexRSSHandler, FeedexHTMLHandler, FeedexScriptHandler


from feeder_query import FeedexQuery, FeedexQueryInterface, FeedexCatalogQuery
from feeder import FeedexDatabase, FeedexDatabaseError, FeedexDataError

from feedex_cli import FeedexCLI

