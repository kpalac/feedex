#!/usr/bin/python3
# -*- coding: utf-8 -*-

""" Feedex plugin skeleton """

import sys
import os
import json



RESULTS_JSON = os.getenv('FEEDEX_RESULTS_JSON','')
try: RESULTS = json.loads(RESULTS_JSON)
except (json.JSONDecodeError,): RESULTS = ''

FIELDS_JSON = os.getenv('FEEDEX_RESULT_FIELDS_JSON','')
try: FIELDS = json.loads(FIELDS_JSON)
except (json.JSONDecodeError,): FIELDS = ''

ITEM_JSON = os.getenv('FEEDEX_ITEM_JSON','')
try: ITEM = json.loads(ITEM_JSON)
except (json.JSONDecodeError,): ITEM = ''

RESULT_TYPE = os.getenv('FEEDEX_TABLE_TYPE','')

if len(sys.argv) > 1:
    OFILE = sys.argv[1]
else: OFILE = None



if OFILE is not None:
     with open(OFILE, 'w') as f: 
         f.write(f"""
Feedex Pugin Test

Table Type: {RESULT_TYPE}
Fields: {', '.join(FIELDS)}                                         

RESULTS: {RESULTS_JSON}

""")
         
print('Plugin executed...')


