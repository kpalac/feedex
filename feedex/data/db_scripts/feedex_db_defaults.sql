BEGIN TRANSACTION;

INSERT INTO "main"."flags" ("id", "name", "desc", "color", "color_cli") VALUES ('1', 'Technology', 'Technology and Engineering related', '#34346565a4a4', 'BLUE');
INSERT INTO "main"."flags" ("id", "name", "desc", "color", "color_cli") VALUES ('2', 'Entertainment', 'Popular culture, movies etc.', '#c887256ebea9', 'PURPLE');
INSERT INTO "main"."flags" ("id", "name", "desc", "color", "color_cli") VALUES ('3', 'Literature', 'Books, Novels, Beau-Lettre', '#a4a400000000', 'RED');
INSERT INTO "main"."flags" ("id", "name", "desc", "color", "color_cli") VALUES ('4', 'Environment', 'Ecology, sustainability, Cliament Change', '#4e4e9a9a0606', 'GREEN');
INSERT INTO "main"."flags" ("id", "name", "desc", "color", "color_cli") VALUES ('5', 'Finance', 'Everything relateg to Money', '#8a8ae2e23434', 'GREEN_BOLD');
INSERT INTO "main"."flags" ("id", "name", "desc", "color", "color_cli") VALUES ('6', 'Geopolitics', 'International affairs, power, world politics', '#c4c4a0a00000', 'YELLOW');
INSERT INTO "main"."flags" ("id", "name", "desc", "color", "color_cli") VALUES ('7', 'Gaming', 'Video games, mage-design etc.', '#757550507b7b', 'PURPLE');
INSERT INTO "main"."flags" ("id", "name", "desc", "color", "color_cli") VALUES ('8', 'Humour', 'Stand-up, mockumentaries, Onion etc.', '#dd0270b770b7', 'LIGHT_RED');
INSERT INTO "main"."flags" ("id", "name", "desc", "color", "color_cli") VALUES ('9', 'Future', 'New tech, social change, challenges', '#fcfce9e94f4f', 'YELLOW_BOLD');
INSERT INTO "main"."flags" ("id", "name", "desc", "color", "color_cli") VALUES ('10', 'History', 'Anything history-related...', '#555557575353', 'WHITE');
INSERT INTO "main"."flags" ("id", "name", "desc", "color", "color_cli") VALUES ('11', 'Important!', 'Breaking and important news', '#efef29292929', 'LIGHT_RED_BOLD');
INSERT INTO "main"."flags" ("id", "name", "desc", "color", "color_cli") VALUES ('12', 'Check later...', 'Something to check out later...', '#ededd4d40000', 'YELLOW');

INSERT INTO "main"."rules" ("id", "name", "type", "feed_id", "field", "string", "case_insensitive", "lang", "weight", "additive", "flag") VALUES ('1', 'BREAKING', '0', NULL, 'title', 'BREAKING', '1', NULL, '50', '1', '11');
INSERT INTO "main"."rules" ("id", "name", "type", "feed_id", "field", "string", "case_insensitive", "lang", "weight", "additive", "flag") VALUES ('2', 'ALERT', '0', NULL, 'title', 'ALERT', '0', NULL, '50', '0', '11');

COMMIT;



