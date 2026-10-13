"""A small, self-contained Texas hold'em tournament bot."""

import random

from poker.action import Action
from poker.card import Card, Rank, Suit
from poker.game_state import GameState
from poker.hand import evaluate


DECK = tuple(Card(rank, suit) for rank in Rank for suit in Suit)


def estimate_equity(state: GameState, opponents: int, trials: int = 96) -> float:
    """Estimate our share of the pot against unknown, random opponent cards."""
    hole = tuple(state.my_player.hole_cards)
    board = tuple(state.community_cards)
    known = set(hole) | set(board)
    available = [card for card in DECK if card not in known]
    missing_board = 5 - len(board)
    draw_count = missing_board + 2 * opponents
    share = 0.0

    for _ in range(trials):
        drawn = random.sample(available, draw_count)
        complete_board = board + tuple(drawn[:missing_board])
        my_score = evaluate(list(hole + complete_board))
        best_score = my_score
        winners = 1

        for seat in range(opponents):
            start = missing_board + 2 * seat
            score = evaluate(list(complete_board) + drawn[start:start + 2])
            if score > best_score:
                best_score = score
                winners = 1
            elif score == best_score:
                winners += 1

        if my_score == best_score:
            share += 1 / winners

    return share / trials


def myAI(state: GameState) -> Action:
    me = state.my_player
    to_call = max(player.chips_bet for player in state.players) - me.chips_bet
    opponents = sum(1 for player in state.players if player is not me and not player.has_folded)

    if opponents == 0:
        return Action.call() if to_call else Action.check()

    equity = estimate_equity(state, opponents)
    cost = min(to_call, me.chips_in_stack)
    pot_odds = cost / (state.chips_in_pot + cost) if cost else 0.0
    board_size = len(state.community_cards)

    # Early streets need a cushion because later bets can still be costly.
    caution = 0.07 if board_size == 0 else 0.04 if board_size < 5 else 0.02
    if to_call > state.chips_in_pot // 2:
        caution += 0.05

    if cost and equity < pot_odds + caution:
        return Action.fold()

    # A stronger hand can build the pot, while preserving chips with marginal hands.
    fair_share = 1 / (opponents + 1)
    strong = equity > fair_share + 0.15 and equity > pot_odds + 0.12
    if strong and me.chips_in_stack > to_call:
        bet = min(me.chips_in_stack - to_call, max(2, state.chips_in_pot // 2))
        if bet > 0:
            return Action.raise_by(bet)

    return Action.call() if to_call else Action.check()


def defaultAI(state: GameState) -> Action:
    """Safe fallback used by the competition engine if our bot fails."""
    to_call = max(player.chips_bet for player in state.players) - state.my_player.chips_bet
    return Action.fold() if to_call else Action.check()
