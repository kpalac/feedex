BEGIN TRANSACTION;



CREATE TABLE IF NOT EXISTS "terms" (
	"id"	INTEGER NOT NULL,
	"term"	TEXT,
	"weight"	NUMERIC,
	"model"	TEXT,
	"form"	TEXT,
	"context_id" INTEGER, 
	PRIMARY KEY("id" AUTOINCREMENT)
);

CREATE INDEX IF NOT EXISTS "idx_terms_id" ON "terms" ( "id"	ASC );
CREATE INDEX IF NOT EXISTS "idx_terms_term" ON "terms" ( "term" ASC);
CREATE INDEX IF NOT EXISTS "idx_terms_term_desc" ON "terms" ( "term" DESC);
CREATE INDEX IF NOT EXISTS "idx_terms_context_id" ON "terms" ( "context_id"	ASC );
CREATE INDEX IF NOT EXISTS "idx_terms_context_id_desc" ON "terms" ( "context_id"	DESC );



INSERT INTO terms
SELECT
null,
string, weight, lang, name, context_id
from rules
where learned = 1;

delete from rules where learned = 1;


CREATE TABLE IF NOT EXISTS "rules_tmp" (
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
	"learned" INTEGER,
	"context_id" INTEGER,
	"flag"	INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT)
);

INSERT INTO rules_tmp
select id, name, type, feed_id, field_id, string, case_insensitive, lang, weight, additive, learned, context_id, flag from rules;


DROP TABLE rules;


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

CREATE INDEX IF NOT EXISTS "idx_rules_id" ON "rules" ( "id"	ASC );
CREATE INDEX IF NOT EXISTS "idx_rules_context_id" ON "rules" ( "context_id"	DESC );
CREATE INDEX IF NOT EXISTS "idx_rules_name" ON "rules" ( "name" );
CREATE INDEX IF NOT EXISTS "idx_rules_string" ON "rules" ( "string" );



INSERT INTO rules
select id, name, type, feed_id, field_id, string, case_insensitive, lang, weight, additive, flag from rules_tmp;

DROP TABLE rules_tmp;

delete from terms where term like 'URL:%';
update terms set term = trim(term), form = trim(form);

update params set val = '1.2.0' where name = 'version';

commit;