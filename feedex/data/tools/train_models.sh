#!/bin/bash


export CORPUS_DIR="$HOME/__corpus"



# EN
python3 smallsem.py --lang=en --weight=2 --learn-from-dir "$CORPUS_DIR"/en/europarl
python3 smallsem.py --lang=en --weight=2 --learn-from-dir "$CORPUS_DIR"/en/gutenberg
python3 smallsem.py --lang=en --weight=2 --learn-from-dir "$CORPUS_DIR"/en/inaugural
python3 smallsem.py --lang=en --weight=2 --learn-from-dir "$CORPUS_DIR"/en/state_union
#python3 smallsem.py --lang=en --weight=1 --learn-from-dir "$CORPUS_DIR"/en/wiki
#python3 smallsem.py --lang=en --weight=1 --learn-from-dir "$CORPUS_DIR"/en/news
python3 smallsem.py --lang=en --weight=1 --learn-from-dir "$CORPUS_DIR"/en/misc
python3 smallsem.py --lang=en --weight=1 --learn-from-dir "$CORPUS_DIR"/en/reviews


# PL
python3 smallsem.py --lang=pl --weight=2 --learn-from-dir "$CORPUS_DIR"/pl/main_corpus
#python3 smallsem.py --lang=pl --weight=1 --learn-from-dir "$CORPUS_DIR"/pl/wiki
#python3 smallsem.py --lang=pl --weight=1 --learn-from-dir "$CORPUS_DIR"/pl/news

# DE
python3 smallsem.py --lang=de --weight=2 --learn-from-dir "$CORPUS_DIR"/de/europarl
python3 smallsem.py --lang=de --weight=1 --learn-from-dir "$CORPUS_DIR"/de/web
python3 smallsem.py --lang=de --weight=1 --learn-from-dir "$CORPUS_DIR"/de/mixed_typical
#python3 smallsem.py --lang=de --weight=1 --learn-from-dir "$CORPUS_DIR"/de/news

# RU
#python3 smallsem.py --lang=ru --weight=2 --learn-from-dir "$CORPUS_DIR"/ru/wiki
python3 smallsem.py --lang=ru --weight=1 --learn-from-dir "$CORPUS_DIR"/ru/web

# FR
python3 smallsem.py --lang=fr --weight=1 --learn-from-dir "$CORPUS_DIR"/fr/web
python3 smallsem.py --lang=fr --weight=1 --learn-from-dir "$CORPUS_DIR"/fr/mixed_typical

#ES
python3 smallsem.py --lang=es --weight=1 --learn-from-dir "$CORPUS_DIR"/es/web








