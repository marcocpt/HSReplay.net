import django
django.setup()

from hsreplaynet.cards.models import Card # noqa

card_names = ['Gang Up', 'Vanish', 'Coldlight Oracle']
game_type = "bgt_ranked_standard"
player_class = "rogue"
max_rank = 20
min_games = 3

HOST = "https://hsreplay.net/"
PREFIX = "cards/winrates/?"

url = HOST + PREFIX

has_other_params = False

cards_filter = []

for name in card_names:
	cards_filter.append(Card.objects.get(name=name).id)

if cards_filter:
	url += "cards=%s" % ",".join(cards_filter)
	has_other_params = True

if game_type:
	url += "&" if has_other_params else ""
	url += "game_type=%s" % game_type
	has_other_params = True

if player_class:
	url += "&" if has_other_params else ""
	url += "class=%s" % player_class
	has_other_params = True

if max_rank:
	url += "&" if has_other_params else ""
	url += "player_rank=%s" % max_rank
	has_other_params = True

if min_games:
	url += "&" if has_other_params else ""
	url += "min_games=%s" % min_games
	has_other_params = True

print(url)
