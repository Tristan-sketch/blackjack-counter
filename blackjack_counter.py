"""Blackjack basic strategy with a Wong Halves card counter.

Rebuilt from a spreadsheet (Blackjack.xlsx, sheet 1) with an added count panel:
- Wong Halves card values and the legend as in the spreadsheet
- Basic-strategy chart (spreadsheet base, A,A / 8,8 / 11 vs 10 / A,2 vs 5
  corrected to standard multi-deck strategy)
- One count button per card, running count, true count = points / remaining decks
- The chart adapts to the true count through index plays (Illustrious 18)
- Next-card probabilities, estimated player edge, bet and Kelly fraction

Run: python blackjack_counter.py   (standard library only, tkinter)
"""

import math
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import font as tkfont

# --------------------------------------------------------------------------- #
# Data from the spreadsheet
# --------------------------------------------------------------------------- #

RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "A"]

# Wong Halves (spreadsheet B4:C13). "10" stands for ten, jack, queen and king.
HALVES = {"2": 0.5, "3": 1, "4": 1, "5": 1.5, "6": 1, "7": 0.5,
          "8": 0, "9": -0.5, "10": -1, "A": -1}

CARDS_PER_DECK = {r: 4 for r in RANKS}
CARDS_PER_DECK["10"] = 16

# Actions with the spreadsheet colours (legend B24:C28)
ACTIONS = {
    "H": ("Hit", "#4EA72E", "white"),
    "S": ("Stand", "#FF0000", "white"),
    "D": ("Double", "#0F9ED5", "white"),
    "P": ("Split", "#FFFF00", "black"),
}
CELL_TEXT = {"H": "H", "S": "S", "D": "D", "P": "SP"}

# Basic strategy (spreadsheet E4:O32), columns = dealer upcard 2..A.
# Differences from the spreadsheet (corrected to standard basic strategy):
#   11 vs 10 = Double (spreadsheet: Hit), 8,8 always Split (spreadsheet: Stand vs 10/A),
#   A,A always Split (spreadsheet: always Hit), A,2 vs 5 = Double (spreadsheet: Hit).
STRATEGY = [
    ("4-8",   "HHHHHHHHHH"),
    ("9",     "HDDDDHHHHH"),
    ("10",    "DDDDDDDDHH"),
    ("11",    "DDDDDDDDDH"),
    ("12",    "HHSSSHHHHH"),
    ("13",    "SSSSSHHHHH"),
    ("14",    "SSSSSHHHHH"),
    ("15",    "SSSSSHHHHH"),
    ("16",    "SSSSSHHHHH"),
    ("17-21", "SSSSSSSSSS"),
    ("A,2",   "HHHDDHHHHH"),
    ("A,3",   "HHHDDHHHHH"),
    ("A,4",   "HHHDDHHHHH"),
    ("A,5",   "HHDDDHHHHH"),
    ("A,6",   "HDDDDHHHHH"),
    ("A,7",   "SDDDDSSHHH"),
    ("A,8",   "SSSSSSSSSS"),
    ("A,9",   "SSSSSSSSSS"),
    ("2,2",   "PPPPPPHHHH"),
    ("3,3",   "PPPPPPHHHH"),
    ("4,4",   "HHHPPPHHHH"),
    ("5,5",   "DDDDDDDDHH"),
    ("6,6",   "PPPPPHHHHH"),
    ("7,7",   "PPPPPPHHHH"),
    ("8,8",   "PPPPPPPPPP"),
    ("9,9",   "PPPPPSPPSS"),
    ("10,10", "SSSSSSSSSS"),
    ("A,A",   "PPPPPPPPPP"),
]
BASE = {hand: dict(zip(RANKS, row)) for hand, row in STRATEGY}

# Index plays ("Illustrious 18", Hi-Lo indices, as an approximation for Wong Halves):
# (hand, dealer) -> (index, action at TC >= index, action at TC < index)
INDEX_PLAYS = {
    ("16", "10"):    (0, "S", "H"),
    ("15", "10"):    (4, "S", "H"),
    ("10,10", "5"):  (5, "P", "S"),
    ("10,10", "6"):  (4, "P", "S"),
    ("10", "10"):    (4, "D", "H"),
    ("12", "3"):     (2, "S", "H"),
    ("12", "2"):     (3, "S", "H"),
    ("11", "A"):     (1, "D", "H"),
    ("9", "2"):      (1, "D", "H"),
    ("10", "A"):     (4, "D", "H"),
    ("9", "7"):      (3, "D", "H"),
    ("16", "9"):     (5, "S", "H"),
    ("13", "2"):     (-1, "S", "H"),
    ("12", "4"):     (0, "S", "H"),
    ("12", "5"):     (-2, "S", "H"),
    ("12", "6"):     (-1, "S", "H"),
    ("13", "3"):     (-2, "S", "H"),
}
INSURANCE_INDEX = 3

# Rough rules of thumb for edge and bet
BASE_EDGE = -0.5      # % player edge at TC 0 (basic strategy, multi-deck)
EDGE_PER_TC = 0.5     # % additional edge per true-count point
MAX_UNITS = 8
# Variance of one hand of blackjack in squared units (standard multi-deck value)
HAND_VARIANCE = 1.32

# Keyboard: key -> card
KEYS = {str(n): str(n) for n in range(2, 10)}
KEYS.update({"0": "10", "t": "10", "a": "A"})

FONT = ("Segoe UI", 9)
BOLD = ("Segoe UI", 9, "bold")


def fmt(x, digits=1, sign=True):
    """Number with a fixed number of decimals and, by default, a sign."""
    return f"{x:+.{digits}f}" if sign else f"{x:.{digits}f}"


def points(x, sign=True):
    """Count value without a needless decimal (1 instead of 1.0)."""
    return fmt(x, 0 if x == int(x) else 1, sign=sign and x != 0)


# --------------------------------------------------------------------------- #
# Logic (kept apart from the interface so it can be tested)
# --------------------------------------------------------------------------- #

class Shoe:
    """The shoe: which cards have been seen so far."""

    def __init__(self, decks=6):
        self.decks = decks
        self.reset()

    def reset(self, decks=None):
        if decks is not None:
            self.decks = decks
        self.seen = {r: 0 for r in RANKS}
        self.history = []

    def total_cards(self):
        return 52 * self.decks

    def remaining_cards(self):
        return self.total_cards() - len(self.history)

    def remaining(self, rank):
        return CARDS_PER_DECK[rank] * self.decks - self.seen[rank]

    def can_add(self, rank):
        return self.remaining(rank) > 0

    def add(self, rank):
        if not self.can_add(rank):
            return False
        self.seen[rank] += 1
        self.history.append(rank)
        return True

    def undo(self):
        if not self.history:
            return False
        self.seen[self.history.pop()] -= 1
        return True

    def running_count(self):
        return sum(HALVES[r] * n for r, n in self.seen.items())

    def true_count(self):
        """Running count per remaining deck, None once the shoe is empty."""
        remaining = self.remaining_cards()
        if remaining <= 0:
            return None
        return self.running_count() / (remaining / 52)

    def probability(self, ranks):
        """Probability in % that the next card is one of the ranks."""
        remaining = self.remaining_cards()
        if remaining <= 0:
            return 0.0
        return sum(self.remaining(r) for r in ranks) / remaining * 100

    def base_probability(self, ranks):
        """Probability in % for a fresh shoe."""
        return sum(CARDS_PER_DECK[r] for r in ranks) / 52 * 100


def strategy_action(hand, dealer, tc):
    """Action for a hand against a dealer upcard, with the index-play deviation for the true count."""
    base = BASE[hand][dealer]
    play = INDEX_PLAYS.get((hand, dealer))
    if play is None or tc is None:
        return base
    index, above, below = play
    return above if tc >= index else below


def player_edge(tc):
    """Estimated player edge in % (rule of thumb)."""
    return BASE_EDGE + EDGE_PER_TC * tc


def bet_units(tc):
    """Bet in units: 0 at TC <= 0 (leave), otherwise the true count rounded down, 1..MAX_UNITS."""
    if tc is None or tc <= 0:
        return 0
    return min(MAX_UNITS, max(1, math.floor(tc)))


def kelly_fraction(tc):
    """Share of the bankroll that maximises expected log growth: edge / variance, 0 without an edge."""
    if tc is None:
        return 0.0
    return max(0.0, player_edge(tc) / 100 / HAND_VARIANCE)


def take_insurance(tc):
    return tc is not None and tc >= INSURANCE_INDEX


# --------------------------------------------------------------------------- #
# Interface
# --------------------------------------------------------------------------- #

class Tooltip:
    """Small hint window while the mouse is over a widget."""

    def __init__(self, widget, text_fn):
        self.widget, self.text_fn, self.tip = widget, text_fn, None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _event=None):
        self.hide()
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(self.tip, text=self.text_fn(), font=FONT, justify="left",
                 bg="#FFFFE0", relief="solid", bd=1, padx=6, pady=3).pack()

    def hide(self, _event=None):
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None


class BlackjackApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Blackjack – Basic Strategy & Wong Halves")
        self.configure(bg="white", padx=12, pady=12)

        self.decks = tk.IntVar(value=6)
        self.unit = tk.StringVar(value="10")
        self.shoe = Shoe(self.decks.get())

        left = tk.Frame(self, bg="white")
        middle = tk.Frame(self, bg="white")
        right = tk.Frame(self, bg="white")
        left.grid(row=0, column=0, sticky="n", padx=(0, 18))
        middle.grid(row=0, column=1, sticky="n", padx=(0, 18))
        right.grid(row=0, column=2, sticky="n")

        self._build_halves(left)
        self._build_legend(left)
        self._build_formula(left)
        self._build_deviations(left)
        self._build_strategy(middle)
        self._build_count_panel(right)
        self._build_probabilities(right)

        self.unit.trace_add("write", lambda *_: self.refresh())
        self.bind_all("<Key>", self._on_key)
        self.refresh()

    # ------------------------------------------------------------------ #
    # Layout
    # ------------------------------------------------------------------ #

    def _cell(self, parent, text, row, col, bold=False, **kw):
        lbl = tk.Label(parent, text=text, font=BOLD if bold else FONT,
                       bg=kw.pop("bg", "white"), relief="solid", bd=1, **kw)
        lbl.grid(row=row, column=col, sticky="nsew")
        return lbl

    def _build_halves(self, parent):
        tk.Label(parent, text="Wong Halves", font=("Segoe UI", 12, "bold"),
                 bg="white").pack(anchor="w")
        table = tk.Frame(parent, bg="white")
        table.pack(anchor="w", pady=(4, 14))
        self._cell(table, "Card", 0, 0, bold=True, width=10)
        self._cell(table, "Points", 0, 1, bold=True, width=7)
        for i, r in enumerate(RANKS[:8], start=1):
            self._cell(table, r, i, 0, bold=True)
            self._cell(table, points(HALVES[r], sign=False), i, 1)
        self._cell(table, "10-A", 9, 0, bold=True)
        self._cell(table, points(HALVES["10"], sign=False), 9, 1)

    def _build_legend(self, parent):
        table = tk.Frame(parent, bg="white")
        table.pack(anchor="w", pady=(0, 14))
        self._cell(table, "Legend", 0, 0, bold=True, width=10)
        self._cell(table, "Colour", 0, 1, bold=True, width=7)
        for i, code in enumerate("HSDP", start=1):
            name, color, _ = ACTIONS[code]
            self._cell(table, name, i, 0, bold=True)
            self._cell(table, "", i, 1, bg=color)

    def _build_formula(self, parent):
        text = ("True count = points / remaining decks\n\n"
                "Positive = play\nNegative = leave\nZero = leave\n\n"
                "The higher the true count,\nthe larger the bet")
        tk.Label(parent, text=text, font=BOLD, bg="white",
                 justify="center").pack(anchor="w", pady=(0, 14))

    def _build_deviations(self, parent):
        tk.Label(parent, text="Active deviations (index plays)", font=BOLD,
                 bg="white").pack(anchor="w")
        self.dev_label = tk.Label(parent, text="", font=FONT, bg="white",
                                  justify="left", anchor="w", wraplength=230)
        self.dev_label.pack(anchor="w", fill="x")

    def _build_strategy(self, parent):
        tk.Label(parent, text="Basic strategy", font=("Segoe UI", 12, "bold"),
                 bg="white").pack(anchor="w")
        table = tk.Frame(parent, bg="white")
        table.pack(anchor="w", pady=(4, 0))
        self._cell(table, "Dealer:", 0, 0, bold=True, width=7)
        for c, r in enumerate(RANKS, start=1):
            self._cell(table, r, 0, c, bold=True, width=4)

        # Fixed cell size, so the thick border does not shift the rows
        font = tkfont.Font(font=BOLD)
        cell_w = font.measure("SP*") + 16
        cell_h = font.metrics("linespace") + 5

        self.cells = {}
        for row, (hand, _) in enumerate(STRATEGY, start=1):
            self._cell(table, hand, row, 0, bold=True)
            for c, dealer in enumerate(RANKS, start=1):
                frame = tk.Frame(table, width=cell_w, height=cell_h, bg="black")
                frame.grid(row=row, column=c)
                lbl = tk.Label(frame, text="", font=BOLD, bd=0)
                self.cells[(hand, dealer)] = lbl
                Tooltip(lbl, lambda h=hand, d=dealer: self._cell_tooltip(h, d))

        tk.Label(parent, text="Cells with a thick border and * differ from the base chart\n"
                              "because of the true count (hover for details).",
                 font=("Segoe UI", 9), fg="#555", bg="white",
                 justify="left").pack(anchor="w", pady=(6, 0))

    def _build_count_panel(self, parent):
        box = tk.LabelFrame(parent, text=" Card counter ", font=BOLD, bg="white",
                            padx=10, pady=8)
        box.pack(fill="x")

        top = tk.Frame(box, bg="white")
        top.pack(fill="x")
        tk.Label(top, text="Decks in the shoe:", font=FONT, bg="white").pack(side="left")
        self.deck_box = ttk.Combobox(top, values=list(range(1, 9)), width=3,
                                     state="readonly", textvariable=self.decks)
        self.deck_box.pack(side="left", padx=6)
        self.deck_box.bind("<<ComboboxSelected>>", self._on_decks_changed)

        counts = tk.Frame(box, bg="white")
        counts.pack(fill="x", pady=8)
        for col, title in enumerate(("Running count", "True count")):
            tk.Label(counts, text=title, font=FONT, bg="white").grid(row=0, column=col, padx=12)
        self.rc_label = tk.Label(counts, font=("Segoe UI", 22, "bold"), bg="white")
        self.tc_label = tk.Label(counts, font=("Segoe UI", 22, "bold"), bg="white")
        self.rc_label.grid(row=1, column=0, padx=12)
        self.tc_label.grid(row=1, column=1, padx=12)

        self.shoe_label = tk.Label(box, font=FONT, bg="white")
        self.shoe_label.pack(anchor="w")

        self.signal_label = tk.Label(box, font=("Segoe UI", 14, "bold"), fg="white",
                                     pady=4)
        self.signal_label.pack(fill="x", pady=(8, 4))

        self.edge_label = tk.Label(box, font=FONT, bg="white", anchor="w")
        self.edge_label.pack(fill="x")
        self.kelly_label = tk.Label(box, font=FONT, bg="white", anchor="w")
        self.kelly_label.pack(fill="x")

        bet = tk.Frame(box, bg="white")
        bet.pack(fill="x")
        tk.Label(bet, text="1 unit =", font=FONT, bg="white").pack(side="left")
        tk.Entry(bet, textvariable=self.unit, width=6, font=FONT).pack(side="left", padx=4)
        self.bet_label = tk.Label(box, font=BOLD, bg="white", anchor="w")
        self.bet_label.pack(fill="x")
        self.insurance_label = tk.Label(box, font=FONT, bg="white", anchor="w")
        self.insurance_label.pack(fill="x", pady=(0, 8))

        tk.Label(box, text="Click every card you see:", font=BOLD,
                 bg="white").pack(anchor="w")
        grid = tk.Frame(box, bg="white")
        grid.pack(pady=4)
        self.card_buttons = {}
        for i, r in enumerate(RANKS):
            text = f"{'10/J/Q/K' if r == '10' else r}\n{points(HALVES[r])}"
            btn = tk.Button(grid, text=text, font=BOLD, width=8,
                            command=lambda rank=r: self.add_card(rank))
            btn.grid(row=i // 5, column=i % 5, padx=2, pady=2)
            self.card_buttons[r] = btn

        actions = tk.Frame(box, bg="white")
        actions.pack(fill="x", pady=(4, 0))
        tk.Button(actions, text="↶ Undo", font=FONT,
                  command=self.undo).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(actions, text="New shoe", font=FONT,
                  command=self.new_shoe).pack(side="left", expand=True, fill="x", padx=2)
        tk.Label(box, text="Keyboard: 2–9, 0 = ten/face, A = ace, Backspace = undo",
                 font=("Segoe UI", 9), fg="#555", bg="white").pack(anchor="w", pady=(4, 0))

    def _build_probabilities(self, parent):
        box = tk.LabelFrame(parent, text=" Next-card probability ", font=BOLD,
                            bg="white", padx=10, pady=8)
        box.pack(fill="x", pady=(10, 0))
        for c, title in enumerate(("Card", "Left", "Now", "Fresh", "Δ")):
            tk.Label(box, text=title, font=BOLD, bg="white",
                     width=8).grid(row=0, column=c)
        self.prob_rows = {}
        groups = [(r, [r]) for r in RANKS] + [
            ("Low 2–6", ["2", "3", "4", "5", "6"]),
            ("Mid 7–9", ["7", "8", "9"]),
            ("High 10–A", ["10", "A"]),
        ]
        for i, (name, members) in enumerate(groups, start=1):
            label = "10/face" if name == "10" else name
            is_group = len(members) > 1
            pady = (6, 0) if name == "Low 2–6" else 0
            row = []
            for c in range(5):
                lbl = tk.Label(box, text=label if c == 0 else "", bg="white",
                               font=BOLD if is_group or c == 0 else FONT)
                lbl.grid(row=i, column=c, pady=pady)
                row.append(lbl)
            self.prob_rows[name] = (members, row)

    # ------------------------------------------------------------------ #
    # Controls
    # ------------------------------------------------------------------ #

    def add_card(self, rank):
        if self.shoe.add(rank):
            self.refresh()

    def undo(self):
        if self.shoe.undo():
            self.refresh()

    def new_shoe(self, ask=True):
        if ask and self.shoe.history and not messagebox.askyesno(
                "New shoe", "Reset the count and start a new shoe?"):
            return False
        self.shoe.reset()
        self.refresh()
        return True

    def _on_decks_changed(self, _event=None):
        if self.shoe.history and not messagebox.askyesno(
                "Change decks", "Changing the number of decks resets the count. "
                                "Continue?"):
            self.decks.set(self.shoe.decks)
            return
        self.shoe.reset(self.decks.get())
        self.refresh()

    def _on_key(self, event):
        if isinstance(event.widget, (tk.Entry, ttk.Entry)):
            return
        if event.keysym == "BackSpace":
            self.undo()
        elif event.char.lower() in KEYS:
            self.add_card(KEYS[event.char.lower()])

    def _cell_tooltip(self, hand, dealer):
        tc = self.shoe.true_count()
        base = BASE[hand][dealer]
        now = strategy_action(hand, dealer, tc)
        text = f"{hand} vs {dealer}\nBase: {ACTIONS[base][0]}"
        play = INDEX_PLAYS.get((hand, dealer))
        if play:
            index, above, below = play
            text += (f"\nIndex: {ACTIONS[above][0]} from TC ≥ {points(index)}, "
                     f"otherwise {ACTIONS[below][0]}")
        if now != base:
            text += f"\nNow: {ACTIONS[now][0]} (because of the true count)"
        return text

    # ------------------------------------------------------------------ #
    # Display
    # ------------------------------------------------------------------ #

    def refresh(self):
        shoe = self.shoe
        rc = shoe.running_count()
        tc = shoe.true_count()
        remaining = shoe.remaining_cards()

        self.rc_label.config(text=fmt(rc), fg=self._sign_color(rc))
        self.tc_label.config(text="–" if tc is None else fmt(tc),
                             fg=self._sign_color(tc or 0))
        self.shoe_label.config(
            text=f"Cards counted: {len(shoe.history)} / {shoe.total_cards()}   ·   "
                 f"Remaining: {remaining} cards = {fmt(remaining / 52, sign=False)} decks")

        if tc is not None and tc > 0:
            self.signal_label.config(text="PLAY", bg="#4EA72E")
        else:
            self.signal_label.config(text="LEAVE", bg="#FF0000")

        self._refresh_bet(tc)
        self._refresh_table(tc)
        self._refresh_probabilities()

        for r, btn in self.card_buttons.items():
            btn.config(state="normal" if shoe.can_add(r) else "disabled")

    @staticmethod
    def _sign_color(x):
        return "#2E7D1F" if x > 0 else "#C00000" if x < 0 else "black"

    def _refresh_bet(self, tc):
        if tc is None:
            self.edge_label.config(text="Shoe empty – please start a new shoe.")
            self.kelly_label.config(text="")
            self.bet_label.config(text="")
            self.insurance_label.config(text="")
            return
        edge = player_edge(tc)
        self.edge_label.config(text=f"Estimated player edge: {fmt(edge)} %",
                               fg=self._sign_color(edge))
        self.kelly_label.config(
            text=f"Kelly bet: {fmt(kelly_fraction(tc) * 100, 2, sign=False)} % of bankroll")
        units = bet_units(tc)
        try:
            unit_value = float(self.unit.get().replace(",", "."))
            money = f" = {fmt(units * unit_value, 2, sign=False)}"
        except ValueError:
            money = ""
        if units == 0:
            self.bet_label.config(text="Bet: sit out (or table minimum)")
        else:
            self.bet_label.config(text=f"Bet: {units} unit{'s' if units > 1 else ''}"
                                       f"{money}")
        if take_insurance(tc):
            self.insurance_label.config(text="Insurance: YES (TC ≥ +3)", fg="#2E7D1F")
        else:
            self.insurance_label.config(text="Insurance: no (only from TC ≥ +3)",
                                        fg="black")

    def _refresh_table(self, tc):
        active = []
        for (hand, dealer), lbl in self.cells.items():
            base = BASE[hand][dealer]
            now = strategy_action(hand, dealer, tc)
            _, bg, fg = ACTIONS[now]
            deviates = now != base
            lbl.config(text=CELL_TEXT[now] + ("*" if deviates else ""), bg=bg, fg=fg)
            border = 3 if deviates else 1
            lbl.place(x=border, y=border, relwidth=1, relheight=1,
                      width=-2 * border, height=-2 * border)
            if deviates:
                active.append(f"• {hand} vs {dealer}: {ACTIONS[now][0]} "
                              f"instead of {ACTIONS[base][0]}")
        if take_insurance(tc):
            active.append("• Take insurance")
        self.dev_label.config(text="\n".join(active) if active else "none")

    def _refresh_probabilities(self):
        for members, (_, left, now, normal, delta) in self.prob_rows.values():
            rest = sum(self.shoe.remaining(r) for r in members)
            p_now = self.shoe.probability(members)
            p_normal = self.shoe.base_probability(members)
            d = p_now - p_normal
            left.config(text=str(rest))
            now.config(text=f"{fmt(p_now, sign=False)} %")
            normal.config(text=f"{fmt(p_normal, sign=False)} %", fg="#777")
            delta.config(text=fmt(d), fg=self._sign_color(round(d, 1)))


def main():
    BlackjackApp().mainloop()


if __name__ == "__main__":
    main()
