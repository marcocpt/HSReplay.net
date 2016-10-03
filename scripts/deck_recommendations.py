""" A basic demonstration of the math for calculating an expected winrate for decks."""

# Assume 4 unique decks to simplify the example
DECKS = [
	"Aggro Shaman",
	"Murloc Paladin",
	"Control Warrior",
	"Resurrect Priest",
]

# These must always sum to 1.0
# Represents the % probability of encountering each deck in the next match
DECK_FREQUENCY = {
	"Aggro Shaman": .31,
	"Murloc Paladin": .27,
	"Control Warrior": .23,
	"Resurrect Priest": .19
}

# These represent the head-to-head win rates between each deck
# The mirror match must always be .5
# The two reciprocal matchups between two decks must always add up to 1.0
WIN_RATES = {
	"Aggro Shaman": {
		"Aggro Shaman": .5,
		"Murloc Paladin": .7,
		"Control Warrior": .45,
		"Resurrect Priest": .2,
	},
	"Murloc Paladin": {
		"Murloc Paladin": .5,
		"Aggro Shaman": .3,
		"Control Warrior": .7,
		"Resurrect Priest": .5,
	},
	"Control Warrior": {
		"Control Warrior": .5,
		"Aggro Shaman": .55,
		"Murloc Paladin": .3,
		"Resurrect Priest": .7,
	},
	"Resurrect Priest": {
		"Aggro Shaman": .8,
		"Murloc Paladin": .5,
		"Control Warrior": .3,
		"Resurrect Priest": .5,
	}
}

for candidate_deck in DECKS:
	win_rate = 0.0
	candidate_win_rates = WIN_RATES[candidate_deck]
	for opponent_deck in DECKS:
		win_rate += (DECK_FREQUENCY[opponent_deck] * candidate_win_rates[opponent_deck])

	print("The expected win rate of %s is %s" % (candidate_deck, round(win_rate, 3)))
