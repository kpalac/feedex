BEGIN TRANSACTION;


CREATE TABLE IF NOT EXISTS "params" (
	"name"	TEXT,
	"val"	TEXT
);

CREATE TABLE IF NOT EXISTS "actions" (
	"name"	TEXT,
	"time"	INTEGER
);


CREATE TABLE IF NOT EXISTS "search_history" (
	"id"	INTEGER NOT NULL UNIQUE,
	"string"	TEXT,
	"feed_id"	INTEGER,
	"date"	INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT)
);


CREATE TABLE IF NOT EXISTS "rules" (
	"id"	INTEGER NOT NULL UNIQUE,
	"name"	TEXT,
	"type"	INTEGER,
	"feed_id"	INTEGER,
	"field_id"	TEXT,
	"string"	TEXT,
	"case_insensitive"	INTEGER,
	"lang"	TEXT,
	"weight"	NUMERIC,
	"additive"	INTEGER,
	"flag"	INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT)
);


CREATE TABLE IF NOT EXISTS "feeds" (
	"id"	INTEGER NOT NULL UNIQUE,
	"charset"	TEXT,
	"lang"	TEXT,
	"generator"	TEXT,
	"url"	TEXT,
	"login"	TEXT,
	"domain"	TEXT,
	"passwd"	TEXT,
	"auth"	TEXT,
	"author"	TEXT,
	"author_contact"	TEXT,
	"publisher"	TEXT,
	"publisher_contact"	TEXT,
	"contributors"	TEXT,
	"copyright"	TEXT,
	"link"	TEXT,
	"title"	TEXT,
	"subtitle"	TEXT,
	"category"	TEXT,
	"tags"	TEXT,
	"name"	TEXT,
	"lastread"	TEXT,
	"lastchecked"	TEXT,
	"interval"	INTEGER,
	"error"	INTEGER,
	"autoupdate"	INTEGER,
	"http_status"	TEXT,
	"etag"	TEXT,
	"modified"	TEXT,
	"version"	TEXT,
	"is_category"	INTEGER,
	"parent_id"	INTEGER,
	"handler"	TEXT,
	"deleted"	INTEGER,
	"user_agent"	TEXT,
	"fetch"	INTEGER,
	"rx_entries"	TEXT,
	"rx_title"	TEXT,
	"rx_link"	TEXT,
	"rx_desc"	TEXT,
	"rx_author"	TEXT,
	"rx_category"	TEXT,
	"rx_text"	TEXT,
	"rx_images"	TEXT,
	"rx_pubdate"	TEXT,
	"rx_pubdate_feed"	TEXT,
	"rx_image_feed"	TEXT,
	"rx_title_feed"	TEXT,
	"rx_charset_feed"	TEXT,
	"rx_lang_feed"	TEXT,
	"script_file"	TEXT,
	"icon_name"	TEXT,
	"display_order"	INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT)
);


CREATE TABLE IF NOT EXISTS "entries" (
	"id"	INTEGER NOT NULL,
	"feed_id"	INTEGER,
	"charset"	TEXT,
	"lang"	TEXT,
	"title"	TEXT,
	"author"	TEXT,
	"author_contact"	TEXT,
	"contributors"	TEXT,
	"publisher"	TEXT,
	"publisher_contact"	TEXT,
	"link"	TEXT,
	"pubdate"	INTEGER,
	"pubdate_str"	TEXT,
	"guid"	TEXT,
	"desc"	TEXT,
	"category"	TEXT,
	"tags"	TEXT,
	"comments"	TEXT,
	"text"	TEXT,
	"source"	TEXT,
	"adddate"	INTEGER,
	"adddate_str"	TEXT,
	"links"	TEXT,
	"read"	INTEGER,
	"importance"	NUMERIC,
	"sent_count"	INTEGER,
	"word_count"	INTEGER,
	"char_count"	INTEGER,
	"polysyl_count"	INTEGER,
	"com_word_count"	INTEGER,
	"numerals_count"	INTEGER,
	"caps_count"	INTEGER,
	"readability"	NUMERIC,
	"weight"	NUMERIC,
	"flag"	INTEGER,
	"images"	TEXT,
	"enclosures"	TEXT,
	"deleted"	INTEGER,
	"note" INTEGER,
	"node_id" INTEGER,
	"node_order" INTEGER,
	"ix_id" INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT)
);


CREATE TABLE IF NOT EXISTS "flags" (
	"id"	INTEGER NOT NULL,
	"name"	TEXT,
	"desc"	TEXT,
	"color"	TEXT,
	"color_cli"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT)
);

CREATE TABLE IF NOT EXISTS "terms" (
	"id"	INTEGER NOT NULL,
	"term"	TEXT,
	"weight"	NUMERIC,
	"model"	TEXT,
	"form"	TEXT,
	"context_id" INTEGER, 
	PRIMARY KEY("id" AUTOINCREMENT)
);




CREATE INDEX IF NOT EXISTS "idx_rules_id" ON "rules" ( "id"	ASC );
CREATE INDEX IF NOT EXISTS "idx_rules_context_id" ON "rules" ( "context_id"	DESC );
CREATE INDEX IF NOT EXISTS "idx_rules_name" ON "rules" ( "name" );
CREATE INDEX IF NOT EXISTS "idx_rules_string" ON "rules" ( "string" );


CREATE INDEX IF NOT EXISTS "idx_entries_id" ON "entries" ( "id" );
CREATE INDEX IF NOT EXISTS "idx_entries_id_desc" ON "entries" ( "id" DESC);
CREATE INDEX IF NOT EXISTS "idx_entires_title" ON "entries" ( "title" );
CREATE INDEX IF NOT EXISTS "idx_entries_author" ON "entries" ( "author" );
CREATE INDEX IF NOT EXISTS "idx_entries_pubdate" ON "entries" ( "pubdate"	DESC );
CREATE INDEX IF NOT EXISTS "idx_entries_adddate" ON "entries" ( "adddate" DESC);
CREATE INDEX IF NOT EXISTS "idx_entries_pubdate_asc" ON "entries" ( "pubdate"   ASC );
CREATE INDEX IF NOT EXISTS "idx_entries_adddate_asc" ON "entries" ( "adddate"   ASC );
CREATE INDEX IF NOT EXISTS "idx_entries_link" ON "entries" ( "link"	DESC );
CREATE INDEX IF NOT EXISTS "idx_entries_weight" ON "entries" ( "weight"    ASC );
CREATE INDEX IF NOT EXISTS "idx_entries_importance" ON "entries" ( "importance"    ASC );
CREATE INDEX IF NOT EXISTS "idx_entries_readability" ON "entries" ( "readability"    ASC );
CREATE INDEX IF NOT EXISTS "idx_entries_feed_id" ON "entries" ( "feed_id" );
CREATE INDEX IF NOT EXISTS "idx_entries_tags" ON "entries" ("tags" ASC);
CREATE INDEX IF NOT EXISTS "idx_entries_category" ON "entries" ("category" ASC);
CREATE INDEX IF NOT EXISTS "idx_entries_text" ON "entries" ("text" ASC);
CREATE INDEX IF NOT EXISTS "idx_entries_desc" ON "entries" ("desc" ASC);
CREATE INDEX IF NOT EXISTS "idx_entries_flag" ON "entries" ("flag" ASC);
CREATE INDEX IF NOT EXISTS "idx_entries_deleted" ON "entries" ("deleted" ASC);
CREATE INDEX IF NOT EXISTS "idx_entries_read" ON "entries" ("read" ASC);
CREATE INDEX IF NOT EXISTS "idx_entries_note" ON "entries" ("note" ASC);
CREATE INDEX IF NOT EXISTS "idx_entries_ix_id" ON "entries" ("ix_id" ASC);
CREATE INDEX IF NOT EXISTS "idx_entries_ix_id_desc" ON "entries" ("ix_id" DESC);



CREATE INDEX IF NOT EXISTS "idx_search_history_date" ON "search_history" ( "date" );
CREATE INDEX IF NOT EXISTS "idx_search_history_feed_id" ON "search_history" ( "feed_id" );
CREATE INDEX IF NOT EXISTS "idx_search_history_id" ON "search_history" ( "id"	DESC );

CREATE INDEX IF NOT EXISTS "idx_feeds_id" ON "feeds" ( "id" );
CREATE INDEX IF NOT EXISTS "idx_feeds_id_desc" ON "feeds" ( "id" DESC);
CREATE INDEX IF NOT EXISTS "idx_feeds_name" ON "feeds" ( "name" );
CREATE INDEX IF NOT EXISTS "idx_feeds_parent_id" ON "feeds" ( "parent_id" );
CREATE INDEX IF NOT EXISTS "idx_feeds_parent_id_desc" ON "feeds" ( "parent_id" DESC);
CREATE INDEX IF NOT EXISTS "idx_feeds_title" ON "feeds" ( "link" );



CREATE INDEX IF NOT EXISTS "idx_params_name" ON "params" ( "name" );

CREATE INDEX IF NOT EXISTS "idx_actions_name" ON "actions" ( "name" );
CREATE INDEX IF NOT EXISTS "idx_actions_time" ON "actions" ( "time" );
CREATE INDEX IF NOT EXISTS "idx_actions_time_desc" ON "actions" ( "time"	DESC );

CREATE INDEX IF NOT EXISTS "idx_flags_id" ON "flags" ( "id"	ASC );
CREATE INDEX IF NOT EXISTS "idx_flags_name" ON "flags" ( "name" );

CREATE INDEX IF NOT EXISTS "idx_terms_id" ON "terms" ( "id"	ASC );
CREATE INDEX IF NOT EXISTS "idx_terms_term" ON "terms" ( "term" ASC);
CREATE INDEX IF NOT EXISTS "idx_terms_term_desc" ON "terms" ( "term" DESC);
CREATE INDEX IF NOT EXISTS "idx_terms_context_id" ON "terms" ( "context_id"	ASC );
CREATE INDEX IF NOT EXISTS "idx_terms_context_id_desc" ON "terms" ( "context_id"	DESC );



COMMIT;
