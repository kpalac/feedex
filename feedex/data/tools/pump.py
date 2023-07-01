#!/usr/bin/python3
# -*- coding: utf-8 -*-



#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.



import sqlite3


source = 'main.db_old'
target = 'main.db'



source_db = sqlite3.connect(source)
source_curs = source_db.cursor()
target_db = sqlite3.connect(target)
target_curs = target_db.cursor()


entries = []


beg = 0
end = 10000

while True:

    beg = end
    end += 10000

    print(f'Processing: {beg}-{end}')

    entries = source_curs.execute(f"""
SELECT
    "id",
    "feed_id",
    "charset",
    "lang",
    "title",
    "author",
    "author_contact",
    "contributors",
    "publisher",
    "publisher_contact",
    "link",
    "pubdate",
    "pubdate_str",
    "guid",
    "desc",
    "category",
    "tags",
    "comments",
    "text",
    "source",
    "adddate",
    "adddate_str",
    "links",
    "read",
    "importance",
    "sent_count",
    "word_count",
    "char_count",
    "polysyl_count",
    "com_word_count",
    "numerals_count",
    "caps_count",
    "readability",
    "weight",
    "flag",
    "images",
    "enclosures",
    "deleted",
    "note",
    "node_id" ,
    "node_order",
    Null

from entries e
where e.id >= {beg} and e.id < {end}
""").fetchall()

    if entries in ((), [], None, (None,), [None], [()]): break

    target_curs.executemany("""
insert into entries 
(id, feed_id, charset, lang, title, author, author_contact, contributors, publisher, publisher_contact, link, pubdate, pubdate_str, 
guid, desc, category, tags, comments, text, source, adddate, adddate_str, links, read, importance, sent_count, word_count, char_count, polysyl_count,
com_word_count, numerals_count, caps_count, readability, weight, flag, images, enclosures, deleted, note, node_id , node_order, ix_id)

VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ? , ?, ?)
""", entries)
    target_db.commit()
    

target_db.close()
source_db.close()

