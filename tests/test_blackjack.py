import pytest

import blackjack_counter as bj


# --- Wong Halves ------------------------------------------------------------

def test_halves_values_match_spreadsheet():
    assert bj.HALVES == {"2": 0.5, "3": 1, "4": 1, "5": 1.5, "6": 1, "7": 0.5,
                         "8": 0, "9": -0.5, "10": -1, "A": -1}


def test_full_deck_counts_to_zero():
    """A balanced count ends at 0 after a complete deck."""
    assert sum(bj.HALVES[r] * bj.CARDS_PER_DECK[r] for r in bj.RANKS) == 0
    assert sum(bj.CARDS_PER_DECK.values()) == 52


# --- Strategy table ---------------------------------------------------------

def test_table_shape_and_codes():
    assert len(bj.STRATEGY) == 28
    for hand, row in bj.STRATEGY:
        assert len(row) == 10, hand
        assert set(row) <= set(bj.ACTIONS), hand


@pytest.mark.parametrize("hand, dealer, action", [
    ("9", "2", "H"), ("9", "3", "D"), ("12", "3", "H"), ("12", "4", "S"),
    ("16", "7", "H"), ("A,7", "2", "S"), ("A,7", "3", "D"), ("A,7", "9", "H"),
    ("9,9", "7", "S"), ("9,9", "8", "P"), ("4,4", "5", "P"), ("5,5", "9", "D"),
])
def test_spot_checks_from_spreadsheet(hand, dealer, action):
    assert bj.BASE[hand][dealer] == action


def test_corrections_to_standard_basic_strategy():
    assert set(bj.BASE["A,A"].values()) == {"P"}
    assert set(bj.BASE["8,8"].values()) == {"P"}
    assert bj.BASE["11"]["10"] == "D"
    assert bj.BASE["A,2"]["5"] == "D"


def test_index_plays_switch_between_base_and_alternative():
    for (hand, dealer), (_, above, below) in bj.INDEX_PLAYS.items():
        assert bj.BASE[hand][dealer] in (above, below), (hand, dealer)


@pytest.mark.parametrize("hand, dealer, tc, action", [
    ("16", "10", -0.1, "H"), ("16", "10", 0, "S"),
    ("11", "A", 0.9, "H"), ("11", "A", 1, "D"),
    ("12", "4", -0.5, "H"), ("12", "4", 0, "S"),
    ("10,10", "6", 4, "P"), ("10,10", "6", 3.9, "S"),
    ("17-21", "A", 10, "S"),
])
def test_strategy_action_follows_true_count(hand, dealer, tc, action):
    assert bj.strategy_action(hand, dealer, tc) == action


def test_strategy_action_without_true_count_uses_base():
    assert bj.strategy_action("16", "10", None) == "H"


# --- Shoe -------------------------------------------------------------------

def test_running_and_true_count():
    shoe = bj.Shoe(decks=6)
    for _ in range(20):
        shoe.add("5")
    for _ in range(6):
        shoe.add("2")
    assert shoe.running_count() == 33
    assert shoe.remaining_cards() == 312 - 26
    assert shoe.true_count() == pytest.approx(33 / (286 / 52))


def test_undo_and_reset():
    shoe = bj.Shoe(decks=2)
    shoe.add("A")
    shoe.add("3")
    assert shoe.undo()
    assert shoe.history == ["A"]
    assert shoe.running_count() == -1
    shoe.reset(decks=8)
    assert shoe.decks == 8 and shoe.history == [] and shoe.running_count() == 0
    assert not shoe.undo()


def test_rank_limit_per_shoe():
    shoe = bj.Shoe(decks=1)
    assert all(shoe.add("A") for _ in range(4))
    assert not shoe.can_add("A")
    assert not shoe.add("A")
    assert shoe.seen["A"] == 4


def test_empty_shoe_has_no_true_count():
    shoe = bj.Shoe(decks=1)
    for rank in bj.RANKS:
        while shoe.add(rank):
            pass
    assert shoe.remaining_cards() == 0
    assert shoe.running_count() == 0
    assert shoe.true_count() is None


def test_probabilities():
    shoe = bj.Shoe(decks=6)
    assert shoe.probability(["10"]) == pytest.approx(16 / 52 * 100)
    assert shoe.probability(bj.RANKS) == pytest.approx(100)
    for _ in range(10):
        shoe.add("5")
    assert shoe.probability(["5"]) < shoe.base_probability(["5"])
    assert shoe.probability(bj.RANKS) == pytest.approx(100)


# --- Edge and bet -----------------------------------------------------------

@pytest.mark.parametrize("tc, units", [
    (None, 0), (-2, 0), (0, 0), (0.1, 1), (1.9, 1), (3.7, 3), (8, 8), (20, 8),
])
def test_bet_units(tc, units):
    assert bj.bet_units(tc) == units


def test_edge_and_insurance():
    assert bj.player_edge(0) == pytest.approx(-0.5)
    assert bj.player_edge(3) == pytest.approx(1.0)
    assert not bj.take_insurance(2.9)
    assert bj.take_insurance(3)
    assert not bj.take_insurance(None)


def test_kelly_fraction_is_edge_over_variance():
    assert bj.kelly_fraction(3) == pytest.approx(0.01 / bj.HAND_VARIANCE)
    assert bj.kelly_fraction(0) == 0
    assert bj.kelly_fraction(-4) == 0
    assert bj.kelly_fraction(None) == 0


# --- Formatting -------------------------------------------------------------

def test_number_format():
    assert bj.fmt(1.25, 2) == "+1.25"
    assert bj.points(1) == "+1"
    assert bj.points(1.5) == "+1.5"
    assert bj.points(0) == "0"
    assert bj.points(-1, sign=False) == "-1"
