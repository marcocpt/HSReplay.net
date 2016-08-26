import hashlib
import random
from datetime import datetime
from enum import IntEnum
from django.db import models
from hearthstone import enums
from hsreplaynet.utils.fields import IntEnumField
from hsreplaynet.accounts.models import User
from hsreplaynet.api.models import APIKey

### WORK-IN-PROGRESS - START ###

class ClassifierManager(models.Manager):

	def train_classifier(self, deck_list_iter):
		"""Train a classifier based on the provided list of decks.

		This is the primary entry point for our management command.

		:param deck_list_iter: An iterable of tuples. The first element
		 is the enums.CardClass value to represent the player's class.
		 The second element is a list of card_id strings.
		"""
		# Get the current classifier, in case we are doing online training
		current = Classifier.objects.current()
		new_classifier = self._generate_new_classifier(current, deck_list_iter)

		if new_classifier.is_valid():
			new_classifier.validated = True
			new_classifier._generate_and_update_archetypes()

			if current:
				# May not exist if this is the initial run
				current.retired = datetime.now()
				current.save()
		else:
			new_classifier.regression = True

		new_classifier.save()

	def current(self):
		return Classifier.objects.filter(retired__isnull=True).order_by("-created").first()

	def _generate_new_classifier(self, current, deck_list_iter):
		"""
		An internal method for actually generating the newest classifier

		:param current: (Optional) the soon-to-be-replaced current classifier. Can be None.
		:param deck_list_iter: The iterable of tuples passed into train_classifier()
		"""
		result = Classifier()
		# TODO: Logic to generate the new classifier goes here.
		return result

	def classifier_for(self, as_of_date):
		"""
		Provides access to historical classifiers for tagging old replays

		Returns None if one can't be found.
		"""
		if not as_of_date:
			return self.current()
		else:
			return Classifier.objects.filter(
				created__lte=as_of_date,
				validated=True
			).order_by("-created").first()

	def elapsed_minutes_from_previous_training(self):
		current = self.current()
		if current:
			now = datetime.now()
			delta = now - current.created
			return delta.minutes


def _generate_classifier_cache_path(instance, filename):
	ts = instance.created
	timestamp = ts.strftime("%Y/%m/%d/%H/%M")
	return "classifiers/%s/classifier.pkl" % timestamp


class Classifier(models.Model):
	id = models.BigAutoField(primary_key=True)
	objects = ClassifierManager()
	created = models.DateTimeField(auto_now_add=True)
	retired = models.DateTimeField(null=True)
	parent = models.ForeignKey(
		"Classifier",
		null = True,
		related_name="descendants")
	validated = models.BooleanField(
		default=False,
		help_text="Only true if the parent's CanonicalList for each Archetypes was "
				  "classified into the same Archetype by this classifier."
	)
	regression = models.BooleanField(
		default=False,
		help_text="Only set True if validation was run and failed",
	)

	# Internal storage of classifier state
	classifier_cache = models.FileField(upload_to=_generate_classifier_cache_path)

	def is_valid(self):
		validation_set = Archetype.objects.filter(in_validation_set=True)
		if validation_set.count() == 0:
			return True

		for archetype in validation_set.all():
			card_id_list = archetype.canonical_deck().card_id_list()
			new_classification = self.classify_deck(card_id_list, archetype.player_class)

			# We anticipate training the classifier every few hours.
			# Each time we train it ~ 90% of the data will be data seen by the previous
			# classifier, and ~ 10% will be new data.

			# We intend the Archetypes we include in the validation set to be so core
			# that the CanonicalList for the previous classifier should not be a
			# discontinuous Archetype in the next classifier. Instead we expect to see
			# the incremental evolution of these core Archetypes captured by the
			# variations in the CanonicalList that each Classifier generates.
			if new_classification.id != archetype.id:
				return False

		return True

	def classify_deck(self, card_list, player_class = None):
		# TODO: This should return an instance of Archetype or None
		# Note, the classifier should select among the approved Archetypes
		candidates = Archetype.objects.filter(approved=True).all()
		# Determine here which candidate is correct, or None if one can't be found.
		return None

	def _generate_and_update_archetypes(self):
		# Calling this is only legal if this Classifier is being installed as the current
		assert self.validated

		# First we create an Archetype record for any new Archetypes we've discovered.
		# Each of these Archetypes will need to be reviewed in the Admin panel and labeled.
		for archetype in self._get_newly_discovered_archetypes():
			self._create_new_archetype(archetype)

		# Second we update the CanonicalList for each of the existing Archetypes
		for archetype in self._get_existing_archetypes():
			self._update_archetype(archetype)


	def _get_newly_discovered_archetypes(self):
		# Returns new Archetype models that haven't been saved to the DB yet.
		return []

	def _get_existing_archetypes(self):
		# Returns a list of models from existing Archetpyes that need to be updated.
		return []

	def _create_new_archetype(self, archetype):
		archetype.save()
		self._create_or_update_canonical_list_for_archetype()
		for race_affiliation in archetype.race_affiliations.all():
			race_affiliation.save()

	def _update_archetype(self, archetype):
		archetype.save()
		self._create_or_update_canonical_list_for_archetype()
		# Note: racial affiliations don't usually change over time unless
		# One archetype morphs into another. E.g. Handlock -> Deamonlock


	def _create_or_update_canonical_list_for_archetype(self, archetype):
		current_canonical_list = archetype.canonical_deck()
		# Creating a new CanonicalList each time we retrain the classifier is how
		# We capture the change overtime in the meta (might be interesting to visualize)

		if current_canonical_list:
			# First, we retire the old canonical list if one exists
			current_canonical_list.current = False
			current_canonical_list.save()

		new_canonical = self._generate_canonical_list(archetype)
		new_canonical.current = True
		new_canonical.save()

	def _generate_canonical_list(self, archetype):
		result = CanonicalList(archetype = archetype)
		# TODO: We need to pull the card list out of the clusters and set it
		return result


class ArchetypeManager(models.Manager):
	"""A Manager for Archetypes.

	This manager provides methods for classifying decks into Archetypes. It optionally
	may encapsulate call outs to external resources so that a single classifier may be
	shared across Lambdas.
	"""

	def classify_deck(self, card_list, player_class = None, as_of = None):
		"""Select an appropriate classifier and apply it to this card_list.

		:param card_list: A CardList which can contain between 0 and N cards.
		:param player_class: An optional enums.CardClass to help classify a deck of
		all neutral cards
		:param as_of: An optional datetime.Datetime so that historical replays can be
		classified based on the Archetypes in play at the time of the as_of date.
		:return: An Archetype instance or None if one cannot be determined
		"""
		if as_of:
			classifier = Classifier.objects.classifier_for(as_of)
		else:
			classifier = Classifier.objects.current()

		if classifier:
			return classifier.classify_deck(card_list, player_class)


class Archetype(models.Model):
	"""Archetypes identify decks with minor card variations that all share the same strategy
	as members of a single category.

	E.g. 'Freeze Mage', 'Miracle Rogue', 'Pirate Warrior', 'Zoolock', 'Control Priest'
	"""
	id = models.BigAutoField(primary_key=True)
	objects = ArchetypeManager()
	name = models.CharField(max_length=250, blank=True)
	player_class = IntEnumField(enum=enums.CardClass, default=enums.CardClass.INVALID)
	in_validation_set = models.BooleanField(
		default=False,
		help_text="Classifiers that don't classify this Archetype correctly are rejected"
	)
	approved = models.BooleanField(
		default=False,
		help_text="Decks will never be classified as this type until it is approved"
	)

	# Categories - an Archetype may fall into multiple categories
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
				return canonical.card_list
		else:
			canonical = CanonicalList.objects.filter(
				archtype=self,
				as_of__lte=as_of
			).order_by('-as_of').first()

			if canonical:
				return canonical.card_list
		return None


class RaceAffiliation(models.Model):
	"""An Archetype may have between 0 and N race affiliations, e.g. A Dragon Murloc
	Paladin"""
	id = models.BigAutoField(primary_key=True)
	archtype = models.ForeignKey(Archetype, related_name="race_affiliations")
	race = IntEnumField(enum=enums.Race, default=enums.Race.INVALID)


class CanonicalList(models.Model):
	"""Each Archetype must have 1 and only 1 "current" CanonicalList

	The canonical list for an Archetype tends to evolve incrementally over time and can
	evolve more dramatically when new card sets are first released.
	"""
	id = models.BigAutoField(primary_key=True)
	archetype = models.ForeignKey(Archetype, related_name="canonical_deck_lists")
	card_list = models.ForeignKey("CardList")
	as_of = models.DateTimeField(auto_now_add=True)
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

	def __str__(self):
		return repr(self)

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
