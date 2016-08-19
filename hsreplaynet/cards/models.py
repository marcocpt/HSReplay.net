import hashlib
import random
from enum import IntEnum
from django.db import models
from hearthstone import enums
from hsreplaynet.utils.fields import IntEnumField
from hsreplaynet.accounts.models import User
from hsreplaynet.api.models import APIKey

### WORK-IN-PROGRESS - START ###

# The following 3 models ArchType, RaceAffiliation, CanonicalList are a work in progress.
# They should not be merged into the master branch until they are finalized.


class ArchTypeManager(models.Manager):
	"""A Manager for ArchTypes.

	This manager provides methods for classifying decks into ArchTypes. It optionally may encapsulate
	call outs to external resources so that a single classifier may be shared across Lambdas.
	"""

	def classify_archtype_for_deck(self, card_list, player_class = None, as_of = None):
		"""Use our classifier to determine an ArchType for the provided deck

		:param card_list: A CardList which can contain between 0 and N cards.
		:param player_class: An optional enums.CardClass to help classify a deck of all neutral cards
		:param as_of: An optional datetime.Datetime so that historical replays can be classified based on the ArchTypes
		in play at the time of the as_of date.
		:return: An ArchType instance or None if one cannot be determined
		"""
		pass


class ArchType(models.Model):
	"""ArchTypes identify decks with minor card variations that all share the same strategy
	as members of a single category.

	E.g. 'Freeze Mage', 'Miracle Rogue', 'Pirate Warrior', 'Zoolock', 'Control Priest'
	"""
	id = models.BigAutoField(primary_key=True)
	objects = ArchTypeManager()
	name = models.CharField(max_length=250)
	player_class = IntEnumField(enum=enums.CardClass, default=enums.CardClass.INVALID)

	# Categories - an ArchType may fall into multiple categories
	aggro = models.BooleanField()
	combo = models.BooleanField()
	control = models.BooleanField()
	fatigue = models.BooleanField()
	midrange = models.BooleanField()
	ramp = models.BooleanField()
	tempo = models.BooleanField()
	token = models.BooleanField()

	def canonical_deck(self, as_of = None):
		if as_of is None:
			canonical = CanonicalList.objects.filter(archtype=self, current=True).first()
			if canonical:
				return canonical.deck
		else:
			canonical = CanonicalList.objects.filter(archtype=self, as_of__lte=as_of).order_by('-as_of').first()
			if canonical:
				return canonical.deck
		return None


class RaceAffiliation(models.Model):
	"""An ArchType may have between 0 and N race affiliations, e.g. A Dragon Murloc Paladin"""
	id = models.BigAutoField(primary_key=True)
	archtype = models.ForeignKey(ArchType, related_name="race_affiliations")
	race = IntEnumField(enum=enums.Race, default=enums.Race.INVALID)


class CanonicalList(models.Model):
	"""Each ArchType must have 1 and only 1 "current" CanonicalList

	The canonical list for an ArchType tends to evolve incrementally over time and can evolve
	dramatically when new card sets are released.
	"""
	id = models.BigAutoField(primary_key=True)
	archtype = models.ForeignKey(ArchType, related_name="canonical_deck_lists")
	card_list = models.ForeignKey(CardList)
	as_of = models.DateTimeField()
	current = models.BooleanField()

### WORK-IN-PROGRESS - END ###


class CardManager(models.Manager):
	def random(self, cost=None, collectible=True, card_class=None):
		"""
		Return a random Card.

		Keyword arguments:
		cost: Restrict the set of candidate cards to cards of this mana cost.
		By default will be in the range 1 through 8 inclusive.
		collectible: Restrict the set of candidate cards to the set of collectible cards.
		card_class: Restrict the set of candidate cards to this class.
		"""
		cost = random.randint(1, 8) if cost is None else cost
		cards = super(CardManager, self).filter(collectible=collectible)
		cards = cards.exclude(type=enums.CardType.HERO).filter(cost=cost)

		if card_class is not None:
			cards = [c for c in cards if c.card_class in (0, card_class)]

		if cards:
			return random.choice(cards)

	def get_valid_deck_list_card_set(self):
		if not hasattr(self, "_usable_cards"):
			card_list = Card.objects.filter(collectible=True).exclude(type=enums.CardType.HERO)
			self._usable_cards = set(c[0] for c in card_list.values_list("id"))

		return self._usable_cards


class Card(models.Model):
	id = models.CharField(primary_key=True, max_length=50)
	objects = CardManager()

	name = models.CharField(max_length=50)
	description = models.TextField(blank=True)
	flavortext = models.TextField(blank=True)
	how_to_earn = models.TextField(blank=True)
	how_to_earn_golden = models.TextField(blank=True)
	artist = models.CharField(max_length=255, blank=True)

	card_class = IntEnumField(enum=enums.CardClass, default=enums.CardClass.INVALID)
	card_set = IntEnumField(enum=enums.CardSet, default=enums.CardSet.INVALID)
	faction = IntEnumField(enum=enums.Faction, default=enums.Faction.INVALID)
	race = IntEnumField(enum=enums.Race, default=enums.Race.INVALID)
	rarity = IntEnumField(enum=enums.Rarity, default=enums.Rarity.INVALID)
	type = IntEnumField(enum=enums.CardType, default=enums.CardType.INVALID)

	collectible = models.BooleanField(default=False)
	battlecry = models.BooleanField(default=False)
	divine_shield = models.BooleanField(default=False)
	deathrattle = models.BooleanField(default=False)
	elite = models.BooleanField(default=False)
	evil_glow = models.BooleanField(default=False)
	inspire = models.BooleanField(default=False)
	forgetful = models.BooleanField(default=False)
	one_turn_effect = models.BooleanField(default=False)
	poisonous = models.BooleanField(default=False)
	ritual = models.BooleanField(default=False)
	secret = models.BooleanField(default=False)
	taunt = models.BooleanField(default=False)
	topdeck = models.BooleanField(default=False)

	atk = models.IntegerField(default=0)
	health = models.IntegerField(default=0)
	durability = models.IntegerField(default=0)
	cost = models.IntegerField(default=0)
	windfury = models.IntegerField(default=0)

	spare_part = models.BooleanField(default=False)
	overload = models.IntegerField(default=0)
	spell_damage = models.IntegerField(default=0)

	craftable = models.BooleanField(default=False)

	class Meta:
		db_table = "card"

	@classmethod
	def from_cardxml(cls, card, save=False):
		obj = cls(id=card.id)
		for k in dir(card):
			if k.startswith("_"):
				continue
			# Transfer all existing CardXML attributes to our model
			if hasattr(obj, k):
				setattr(obj, k, getattr(card, k))

		if save:
			obj.save()

		return obj

	def __str__(self):
		return self.name


class CardListManager(models.Manager):
	def get_or_create_from_id_list(self, id_list):
		digest = generate_digest_from_deck_list(id_list)
		existing_deck = CardList.objects.filter(digest=digest).first()
		if existing_deck:
			return existing_deck, False

		deck = CardList.objects.create(digest=digest)

		for card_id in id_list:
			include, created = deck.include_set.get_or_create(
				deck=deck,
				card_id=card_id,
				defaults={"count": 1}
			)

			if not created:
				# This must be an additional copy of a card we've
				# seen previously so we increment the count
				include.count += 1
				include.save()

		deck.save()
		return deck, True


def generate_digest_from_deck_list(id_list):
	sorted_cards = sorted(id_list)
	m = hashlib.md5()
	m.update(",".join(sorted_cards).encode("utf-8"))
	return m.hexdigest()


class DeckSource(IntEnum):
	UNKNOWN = 0
	HSREPLAYNET = 1
	API = 2


class Deck(models.Model):
	"""
	Represents an instance of a CardList owned by a player.
	"""
	id = models.BigAutoField(primary_key=True)
	owner = models.ForeignKey(User, null=True)
	# We use 0 to represent the UNKNOWN DeckType
	type = IntEnumField(enums.DeckType, default=0)
	player_class = IntEnumField(enums.CardClass)
	region = IntEnumField(enums.BnetRegion)
	hearthstone_id = models.BigIntegerField(
		null=True,
		help_text="The deck's ID in Hearthstone's collection manager."
	)
	source = IntEnumField(DeckSource, help_text="The source of the initial version")
	source_url = models.URLField(blank=True)
	source_api_key = models.ForeignKey(APIKey)


class DeckVersion(models.Model):
	"""
	Represents an instance of a CardList owned by a player.
	"""
	id = models.BigAutoField(primary_key=True)
	created = models.DateTimeField(auto_now_add=True)
	version_id = models.IntegerField()
	name = models.CharField(max_length=255)
	deck = models.ForeignKey(Deck, related_name="versions")
	card_list = models.ForeignKey(CardList)
	cardback_id = models.IntegerField()
	hero = models.ForeignKey(Card)
	format = IntEnumField(enums.FormatType)


class CardList(models.Model):
	"""
	Represents an abstract collection of cards.

	The default sorting for cards when iterating over a deck is by
	mana cost and then alphabetical within cards of equal cost.
	"""
	id = models.BigAutoField(primary_key=True)
	objects = CardListManager()
	cards = models.ManyToManyField(Card, through="Include")
	digest = models.CharField(max_length=32, unique=True)
	created = models.DateTimeField(auto_now_add=True, null=True, blank=True)

	def __repr__(self):
		return "[" + ",".join(map(str, self.include_set.all())) + "]"

	def __iter__(self):
		# sorted() is stable, so sort alphabetically first and then by mana cost
		alpha_sorted = sorted(self.cards.all(), key=lambda c: c.name)
		mana_sorted = sorted(alpha_sorted, key=lambda c: c.cost)
		return mana_sorted.__iter__()

	def save(self, *args, **kwargs):
		EMPTY_DECK_DIGEST = "d41d8cd98f00b204e9800998ecf8427e"
		if self.digest != EMPTY_DECK_DIGEST and self.include_set.count() == 0:
			# A client has set a digest by hand, so don't recalculate it.
			return super(CardList, self).save(*args, **kwargs)
		else:
			self.digest = generate_digest_from_deck_list(self.card_id_list())
			return super(CardList, self).save(*args, **kwargs)

	def card_id_list(self):
		result = []

		includes = self.include_set.all().values_list("card__id", "count")
		for id, count in includes:
			for i in range(count):
				result.append(id)

		return result

	def size(self):
		"""
		The number of cards in the deck.
		"""
		return sum(i.count for i in self.include_set.all())


class Include(models.Model):
	id = models.BigAutoField(primary_key=True)
	deck = models.ForeignKey(CardList, on_delete=models.CASCADE)
	card = models.ForeignKey(Card, on_delete=models.PROTECT)
	count = models.IntegerField(default=1)

	def __str__(self):
		return "%s x %s" % (self.card.name, self.count)

	class Meta:
		unique_together = ("deck", "card")
