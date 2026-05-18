"""Minimal headless Blackjack. Pure stdlib, deterministic given seed.

Rules (v2, with double + split):
  - Heads-up: one player vs the dealer.
  - Infinite shoe: each card is an independent draw from the standard
    13-card distribution (so card counting is out of scope by design).
  - Dealer stands on all 17 (S17).
  - Blackjack pays 3:2 (return = +1.5 per unit bet).
  - Actions:
      0 = stand
      1 = hit
      2 = double  — only on initial 2-card hand. Doubles bet, takes
                    exactly one more card, then stands. Bust = -2.
      3 = split   — only when initial 2 cards have the same value
                    (10 = J = Q = K all count as 10). Player puts a
                    second equal bet up; the two cards become two
                    separate hands, each dealt one new card. Each
                    hand then plays hit/stand independently. House
                    rule simplifications:
                      - No re-split (max 2 hands).
                      - No double after split (DAS off).
                      - Split aces get exactly one card each, then
                        auto-stand. A 10 on a split ace is 21 but
                        NOT blackjack (pays 1:1).

Per-hand return is in units of the initial bet, so:
  - stand / hit: ±1 (or ±1.5 for natural BJ, 0 for push)
  - double: ±2 (or 0 for push)
  - split: each sub-hand contributes ±1; total in [-2, +2]

obs dict keys:
  player           list of card values (2-10 or 11 for ace)
  dealer_upcard    int 2-10 or 11
  can_double       bool — True only on initial 2 cards
  can_split        bool — True only when initial 2 cards are a pair

Card values:
  2-10 = face value; J/Q/K = 10; A = 1 or 11 (handled in hand_value)
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field


CARD_DISTRIBUTION = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11]

STAND, HIT, DOUBLE, SPLIT = 0, 1, 2, 3


def draw(rng: random.Random) -> int:
    return rng.choice(CARD_DISTRIBUTION)


def hand_value(cards: list[int]) -> tuple[int, bool]:
    """Return (best_total <= 21 when possible, is_soft)."""
    total = sum(cards)
    aces_high = cards.count(11)
    while total > 21 and aces_high > 0:
        total -= 10
        aces_high -= 1
    return total, aces_high > 0


def _make_obs(player: list[int], dealer_upcard: int,
              can_double: bool, can_split: bool) -> dict:
    return {
        "player": list(player),
        "dealer_upcard": dealer_upcard,
        "can_double": can_double,
        "can_split": can_split,
    }


def _dealer_play(dealer: list[int], rng: random.Random) -> int:
    """Dealer hits to 17+ (S17). Returns final total."""
    while True:
        total, _ = hand_value(dealer)
        if total >= 17:
            return total
        dealer.append(draw(rng))


def _settle(player_total: int, dealer_total: int, bet_mult: float) -> float:
    """Return signed bet outcome. Assumes player did not bust."""
    if dealer_total > 21:
        return bet_mult
    if player_total > dealer_total:
        return bet_mult
    if player_total < dealer_total:
        return -bet_mult
    return 0.0


def _play_split_hand(policy_fn, cards: list[int], dealer_upcard: int,
                     rng: random.Random) -> int:
    """Play one half of a non-aces split. Hit/stand only (no DAS, no resplit)."""
    while True:
        total, _ = hand_value(cards)
        if total >= 21:
            return total
        obs = _make_obs(cards, dealer_upcard, can_double=False, can_split=False)
        action = policy_fn(obs)
        if action == HIT:
            cards.append(draw(rng))
            continue
        return total  # stand (or unrecognized action → treat as stand)


def _play_split(policy_fn, card: int, dealer: list[int],
                rng: random.Random) -> float:
    """Resolve a split. Returns total return from both sub-hands (in [-2, +2])."""
    is_aces = card == 11
    hand_a = [card, draw(rng)]
    hand_b = [card, draw(rng)]

    if is_aces:
        a_total, _ = hand_value(hand_a)
        b_total, _ = hand_value(hand_b)
    else:
        a_total = _play_split_hand(policy_fn, hand_a, dealer[0], rng)
        b_total = _play_split_hand(policy_fn, hand_b, dealer[0], rng)

    d_total = _dealer_play(dealer, rng)

    a_result = -1.0 if a_total > 21 else _settle(a_total, d_total, 1.0)
    b_result = -1.0 if b_total > 21 else _settle(b_total, d_total, 1.0)
    return a_result + b_result


def _play_after_first_action(policy_fn, player: list[int], dealer: list[int],
                             rng: random.Random) -> float:
    """Play hit/stand loop after the first action was a hit. No double/split now."""
    while True:
        total, _ = hand_value(player)
        if total > 21:
            return -1.0
        obs = _make_obs(player, dealer[0], can_double=False, can_split=False)
        action = policy_fn(obs)
        if action == HIT:
            player.append(draw(rng))
            continue
        # Stand (or unrecognized action → treat as stand)
        d_total = _dealer_play(dealer, rng)
        p_total, _ = hand_value(player)
        return _settle(p_total, d_total, 1.0)


def _play_one_hand(policy_fn, rng: random.Random) -> float:
    """Play one full hand (incl. possible split/double). Returns net unit return."""
    player = [draw(rng), draw(rng)]
    dealer = [draw(rng), draw(rng)]

    p_total, _ = hand_value(player)
    d_total_initial, _ = hand_value(dealer)
    player_bj = p_total == 21
    dealer_bj = d_total_initial == 21
    if player_bj or dealer_bj:
        if player_bj and dealer_bj:
            return 0.0
        if player_bj:
            return 1.5
        return -1.0

    can_split = player[0] == player[1]
    obs = _make_obs(player, dealer[0], can_double=True, can_split=can_split)
    action = policy_fn(obs)

    if action == SPLIT and can_split:
        return _play_split(policy_fn, player[0], dealer, rng)

    if action == DOUBLE:
        player.append(draw(rng))
        p_total, _ = hand_value(player)
        if p_total > 21:
            return -2.0
        d_total = _dealer_play(dealer, rng)
        return _settle(p_total, d_total, 2.0)

    if action == HIT:
        player.append(draw(rng))
        return _play_after_first_action(policy_fn, player, dealer, rng)

    # action == STAND (or unrecognized first action → treat as stand)
    d_total = _dealer_play(dealer, rng)
    return _settle(p_total, d_total, 1.0)


def play_session(policy_fn, seed: int, n_hands: int) -> dict:
    """Play n_hands hands sharing one RNG stream. Returns aggregate stats."""
    rng = random.Random(seed)
    returns: list[float] = []
    decisions = [0]  # mutable counter closed over by the wrapper

    def counted(obs):
        decisions[0] += 1
        return policy_fn(obs)

    for _ in range(n_hands):
        returns.append(_play_one_hand(counted, rng))

    n = len(returns)
    mean = sum(returns) / n
    var = sum((r - mean) ** 2 for r in returns) / max(1, n - 1)
    stddev = var ** 0.5
    se = stddev / (n ** 0.5)
    return {
        "n_hands": n,
        "ev": mean,
        "stddev": stddev,
        "se": se,
        "ci95_low": mean - 1.96 * se,
        "ci95_high": mean + 1.96 * se,
        "n_decisions": decisions[0],
        # legacy: n_hits is now the same as n_decisions for driver compatibility
        "n_hits": decisions[0],
        "wins": sum(1 for r in returns if r > 0),
        "losses": sum(1 for r in returns if r < 0),
        "pushes": sum(1 for r in returns if r == 0),
        "player_bj": sum(1 for r in returns if r == 1.5),
        "dealer_bj": 0,  # legacy field; not tracked in v2 env
    }
