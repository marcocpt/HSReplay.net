from enum import IntEnum
from django.db import models
from hearthstone.enums import DeckType
from hsreplaynet.accounts.models import User
from hsreplaynet.cards.models import Deck as CardList
from hsreplaynet.utils.fields import IntEnumField


class DeckSourceType(IntEnum):
	UNKNOWN = 0
	NORMAL = 1
	TEMPLATE = 2
	DECK = 3


class Deck(models.Model):
	id = models.BigAutoField(primary_key=True)
	hearthstone_id = models.BigIntegerField(null=True)
	type = IntEnumField(DeckType)
	name = models.CharField(max_length=64, blank=True)
	hero_overridden = models.BooleanField(default=False)
	cardback_id = models.IntegerField(null=True)
	cardback_overridden = models.BooleanField(default=False)
	create_date = models.DateTimeField(null=True)
	season_id = models.PositiveSmallIntegerField()
	wild = models.BooleanField()
	sort_order = models.PositiveSmallIntegerField(default=0)
	source_type = IntEnumField(enum=DeckSourceType, default=DeckSourceType.UNKNOWN)

	user = models.ForeignKey(User, null=True)

	created = models.DateTimeField(auto_now_add=True)
	updated = models.DateTimeField(auto_now=True)

	cards = models.ForeignKey(CardList)

	def __str__(self):
		return self.name
