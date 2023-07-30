#!/usr/bin/python3
# -*- coding: utf-8 -*-

""" Feedex plugin skeleton """

import sys
import os
import json


TMP_FILE_ENV = os.getenv('FEEDEX_TMP_FILE')
TABLE_ENV = os.getenv('FEEDEX_TABLE')
FIELDS_ENV = os.getenv('FEEDEX_FIELDS')

if len(sys.argv) > 2:
    OFILE = sys.argv[1]
    TMP_FILE = sys.argv[2]
else: sys.exit(1)


print(f'Plugin executed: {TMP_FILE};{TMP_FILE_ENV};{TABLE_ENV};{FIELDS_ENV}')


