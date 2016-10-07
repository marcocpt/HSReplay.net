from enum import IntEnum
from django.db import models
from hsreplaynet.accounts.models import User
from hsreplaynet.cards.models import Card
from hsreplaynet.utils.fields import IntEnumField


class BoosterType(IntEnum):
	"DBF/BOOSTER.xml"
	# INVALID = 0
	CLASSIC = 1
	GOBLINS_VS_GNOMES = 9
	THE_GRAND_TOURNAMENT = 10
	OLD_GODS = 11
	FIRST_PURCHASE = 17


class Pack(models.Model):
	id = models.BigAutoField(primary_key=True)
	booster_type = IntEnumField(enum=BoosterType)
	date = models.DateTimeField()
	cards = models.ManyToManyField(Card, through="packs.PackCard")
	user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
	account_hi = models.BigIntegerField()
	account_lo = models.BigIntegerField()

	def __str__(self):
		cards = self.cards.all()
		if not cards:
			return "(Empty pack)"
		return ", ".join(str(card) for card in cards)


class PackCard(models.Model):
	id = models.BigAutoField(primary_key=True)
	pack = models.ForeignKey(Pack)
	card = models.ForeignKey(Card)
	premium = models.BooleanField()
