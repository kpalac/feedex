BEGIN TRANSACTION;

--DROP TABLE rules_tmp;

CREATE TABLE IF NOT EXISTS "rules_tmp" (
	"id"	INTEGER NOT NULL UNIQUE,
	"name"	TEXT,
	"type"	INTEGER,
	"feed_id"	INTEGER,
	"field"	TEXT,
	"string"	TEXT,
	"case_insensitive"	INTEGER,
	"lang"	TEXT,
	"weight"	NUMERIC,
	"additive"	INTEGER,
	"flag"	INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT)
);

INSERT INTO rules_tmp
select * from rules;


DROP TABLE rules;


CREATE TABLE IF NOT EXISTS "rules" (
	"id"	INTEGER NOT NULL UNIQUE,
	"name"	TEXT,
	"type"	INTEGER,
	"feed_id"	INTEGER,
	"field"	TEXT,
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
select * from rules_tmp;;

DROP TABLE rules_tmp;


update params set val = '1.2.1' where name = 'version';

commit;