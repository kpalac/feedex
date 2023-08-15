#!/usr/bin/python3
# -*- coding: utf-8 -*-

""" Feedex plugin skeleton """

import sys
import os
import json


PIPE_ENV = os.getenv('FEEDEX_PIPE')
TABLE_ENV = os.getenv('FEEDEX_TABLE')
FIELDS_ENV = os.getenv('FEEDEX_FIELDS')

if len(sys.argv) > 2:
    OFILE = sys.argv[1]
    PIPE = sys.argv[2]
else: sys.exit(1)

INPUT = json.load(PIPE)

print(f'Plugin executed: {PIPE};{TABLE_ENV};{FIELDS_ENV}; {type(INPUT)}')


