![Blackjack Counter](docs/banner.png)

# Blackjack Counter

[![Tests](https://github.com/Tristan-sketch/blackjack-counter/actions/workflows/tests.yml/badge.svg)](https://github.com/Tristan-sketch/blackjack-counter/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![tkinter](https://img.shields.io/badge/GUI-tkinter-555)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A desktop app that turns a blackjack spreadsheet into a live model of a finite shoe: the
basic-strategy chart, a Wong Halves card counter, and a chart that changes with the true count.
You click every card you see, and the app keeps the running count, the true count, the
conditional odds for the next card, the estimated edge and a Kelly bet size up to date.

Blackjack is one of the few casino games without independent rounds: every card removed changes
the distribution of the next one. That makes it a small, fully observable laboratory for
conditional probability, expected value and bet sizing under an uncertain edge.

![Screenshot of the app](docs/screenshot.png)

## Features

| Part | What it does |
|---|---|
| Strategy chart | Hard totals, soft hands and pairs against every dealer upcard, coloured like the original spreadsheet (Hit, Stay, Double, Split) |
| Card counter | One button per card (2–9, 10/face, ace) with its Wong Halves value, plus keyboard shortcuts, undo and a new-shoe button; 1–8 decks |
| True count | Running count divided by the remaining decks, which the app works out from the cards already counted |
| Index plays | The "Illustrious 18" deviations: cells whose best play changes at the current true count get a thick border and a `*`, and hovering a cell shows its index |
| Next-card odds | Cards left per rank and the chance that the next card is a 2, 3, …, 10 or ace, compared with a fresh shoe |
| Edge and bet | Estimated player edge, the Kelly fraction of the bankroll, a bet in units, a play/leave signal and an insurance hint |

## How it works

**Wong Halves.** Every card adds a fixed value to the running count:

| Card | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10–A |
|---|---|---|---|---|---|---|---|---|---|
| Points | +0.5 | +1 | +1 | +1.5 | +1 | +0.5 | 0 | −0.5 | −1 |

**True count** = running count / remaining decks. A positive true count means the shoe is rich in
tens and aces, which favours the player: the app says "Play" and raises the bet. At zero or below
it says "Leave".

**Index plays.** The basic-strategy chart assumes a neutral shoe. Seventeen hands, plus insurance (together the "Illustrious 18"),
are played differently once the true count passes a threshold, for example standing on 16 against a
10 from a true count of 0, or taking insurance from +3.

**Rules of thumb.** Edge ≈ −0.5 % + 0.5 % per true-count point. Bet = true count rounded down,
between 1 and 8 units, and nothing at a true count of 0 or below.

## The mathematics

**Next-card odds.** With $n_r$ cards of rank $r$ left among $N$ cards, the next card is a draw
without replacement: $P(r) = n_r / N$. The app shows this next to the fresh-shoe value
$4/52$ (or $16/52$ for tens) and the difference, so you can see how far the shoe has drifted.

**Why the count works.** The Halves values are chosen so that a full deck sums to zero (a
*balanced* count, checked in the tests). The running count therefore estimates how many more
small cards than large ones have left the shoe. Dividing by the remaining decks turns it into a
density, the true count, which is roughly linear in the player's expected value per hand.

**Kelly bet.** For a bet with edge $\mu$ (expected win per unit staked) and variance $\sigma^2$
per unit, maximising the expected logarithm of wealth gives, for small edges,

$$f^{\star} \approx \frac{\mu}{\sigma^2},$$

the share of the bankroll to stake. One blackjack hand has $\sigma^2 \approx 1.32$ because of
doubles, splits and the 3:2 blackjack payout, so at a true count of +3 (edge ≈ 1 %) the Kelly
bet is about 0.76 % of the bankroll. Betting more than $2f^{\star}$ makes long-run growth negative
even though every single bet has a positive expectation.

**Risk of ruin.** With a bankroll of $B$ units and a per-hand edge $\mu$, the diffusion
approximation gives a ruin probability of about $\exp(-2\mu B / \sigma^2)$. The edge estimate
itself is uncertain, which is why practitioners bet a *fraction* of Kelly. How much that
estimation risk should shrink the bet is the subject of
[kelly-under-uncertainty](https://github.com/Tristan-sketch/kelly-under-uncertainty).

## Notes on the chart

The chart follows the original spreadsheet, with four cells changed to standard multi-deck basic
strategy: always split aces, always split eights, double 11 against a 10, and double soft 13 (A,2)
against a 5.

The index thresholds are the published Hi-Lo values. Wong Halves runs on a very similar scale, so
they are a close approximation rather than exact Halves indices. The edge, bet and Kelly formulas are
approximations too: a linear edge model and a single variance for all true counts.

## Run it

Needs Python 3.10 or newer; the app uses only the standard library.

```bash
python blackjack_counter.py
```

On Windows you can double-click `start_blackjack.bat`. It uses [uv](https://docs.astral.sh/uv/)
to set up the environment and starts the app without a console window.

Keyboard: `2`–`9` for those cards, `0` or `T` for a ten or face card, `A` for an ace, Backspace to undo.

## Tests

```bash
uv run pytest
```

The tests cover the counting values (including that the count is balanced), the strategy chart
(with spot checks against the spreadsheet), the index plays, the shoe bookkeeping, the
probabilities, the bet rules and the Kelly fraction. GitHub
Actions runs them on every push.

## Project layout

```
blackjack_counter.py   app: data, counting logic and tkinter interface
tests/                 pytest suite for the logic
start_blackjack.bat    Windows launcher
docs/screenshot.png    screenshot for this README
```

## Disclaimer

This is a study and practice tool. Card counting is legal in most places, but casinos may refuse
to deal to counters, and using any device at the table is usually against the rules. No strategy
removes the risk of losing money.

## License

[MIT](LICENSE)
