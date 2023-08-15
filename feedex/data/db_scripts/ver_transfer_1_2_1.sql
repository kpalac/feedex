BEGIN TRANSACTION;


alter table feeds add column recom_weight INTEGER;

alter table feeds add column location TEXT;
CREATE INDEX IF NOT EXISTS "idx_feeds_location" ON "feeds" ( "location" );

--update terms set context_id = (select e.ix_id from entries e where e.id = context_id);
--update terms set context_id = (select e.id from entries e where e.ix_id = context_id)

update params set val = '1.2.0' where name = 'version';

COMMIT;