from __future__ import unicode_literals

from django.db import migrations

CREATE_PRETTY_DECK_LIST_TABLE_FUNCTION = """
CREATE OR REPLACE FUNCTION pretty_deck_list_table(numeric)
RETURNS TABLE (card_name text, card_count integer) AS $$
    SELECT c.name, ci.count
    FROM cards_include ci
    JOIN card c ON c.id = ci.card_id
    WHERE ci.deck_id = $1
    ORDER BY c.cost;
$$ LANGUAGE SQL STABLE;
"""

DROP_PRETTY_DECK_LIST_TABLE_FUNCTION = """
DROP FUNCTION pretty_deck_list_table(int);
"""

CREATE_PRETTY_DECK_LIST_STRING = """
CREATE OR REPLACE FUNCTION pretty_deck_list_string(numeric)
RETURNS text AS $$
    SELECT string_agg(card_name || ' x ' || card_count, ', ')
    FROM pretty_deck_list_table($1);
$$ LANGUAGE SQL STABLE;
"""

DROP_PRETTY_DECK_LIST_STRING = """
DROP FUNCTION pretty_deck_list_string(int);
"""

CREATE_DECK_DIGEST = """
CREATE OR REPLACE FUNCTION deck_digest(text[]) RETURNS text AS $$
SELECT md5(convert_to(string_agg(c.id, ',' ORDER BY c.id), 'UTF8'))
FROM UNNEST($1) c(id);
$$ LANGUAGE SQL STABLE;
"""

DROP_DECK_DIGEST = """
DROP FUNCTION deck_digest(text[]);
"""



class Migration(migrations.Migration):
	dependencies = [
		('cards', '0002_auto_20160907_2216'),
	]

	operations = [
		migrations.RunSQL(
			CREATE_PRETTY_DECK_LIST_TABLE_FUNCTION,
			DROP_PRETTY_DECK_LIST_TABLE_FUNCTION
		),
		migrations.RunSQL(
			CREATE_PRETTY_DECK_LIST_STRING,
			DROP_PRETTY_DECK_LIST_STRING
		),
		migrations.RunSQL(
			CREATE_DECK_DIGEST,
			DROP_DECK_DIGEST
		),
	]
