import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class PairingPlayer:
    user_id: uuid.UUID
    username: str
    points: float = 0.0
    wins: int = 0
    draws: int = 0
    games_played: int = 0
    white_games: int = 0
    black_games: int = 0
    had_bye: bool = False
    seed_order: int = 0


@dataclass(frozen=True)
class GeneratedPairing:
    white_user_id: uuid.UUID | None
    black_user_id: uuid.UUID | None
    result: str = "pending"


PreviousPairSet = set[frozenset[uuid.UUID]]


def _pair_key(first: uuid.UUID, second: uuid.UUID) -> frozenset[uuid.UUID]:
    return frozenset((first, second))


def _has_previous_pairing(
    first: PairingPlayer,
    second: PairingPlayer,
    previous_pairs: PreviousPairSet,
) -> bool:
    return _pair_key(first.user_id, second.user_id) in previous_pairs


def _choose_bye_player(players: list[PairingPlayer]) -> PairingPlayer:
    for player in reversed(players):
        if not player.had_bye:
            return player
    return players[-1]


def _assign_colors(
    first: PairingPlayer,
    second: PairingPlayer,
    board_number: int,
    round_number: int,
) -> GeneratedPairing:
    first_balance = first.white_games - first.black_games
    second_balance = second.white_games - second.black_games
    if first_balance > second_balance:
        return GeneratedPairing(white_user_id=second.user_id, black_user_id=first.user_id)
    if second_balance > first_balance:
        return GeneratedPairing(white_user_id=first.user_id, black_user_id=second.user_id)
    if (round_number + board_number) % 2 == 0:
        return GeneratedPairing(white_user_id=first.user_id, black_user_id=second.user_id)
    return GeneratedPairing(white_user_id=second.user_id, black_user_id=first.user_id)


def _pair_greedily(
    players: list[PairingPlayer],
    previous_pairs: PreviousPairSet,
    round_number: int,
) -> list[GeneratedPairing]:
    available = players.copy()
    pairings: list[GeneratedPairing] = []
    while len(available) >= 2:
        player = available.pop(0)
        opponent_index = next(
            (
                index
                for index, opponent in enumerate(available)
                if not _has_previous_pairing(player, opponent, previous_pairs)
            ),
            0,
        )
        opponent = available.pop(opponent_index)
        pairings.append(
            _assign_colors(
                player,
                opponent,
                board_number=len(pairings) + 1,
                round_number=round_number,
            )
        )
    return pairings


def generate_swiss_pairings(
    players: list[PairingPlayer],
    previous_pairs: PreviousPairSet,
    round_number: int,
) -> list[GeneratedPairing]:
    ordered_players = sorted(
        players,
        key=lambda player: (
            -player.points,
            -player.wins,
            -player.draws,
            -player.games_played,
            player.username.lower(),
        ),
    )
    generated: list[GeneratedPairing] = []
    if len(ordered_players) % 2 == 1:
        bye_player = _choose_bye_player(ordered_players)
        ordered_players = [
            player for player in ordered_players if player.user_id != bye_player.user_id
        ]
        generated.append(
            GeneratedPairing(
                white_user_id=bye_player.user_id,
                black_user_id=None,
                result="bye",
            )
        )
    generated.extend(_pair_greedily(ordered_players, previous_pairs, round_number))
    return _renumber_bye_last(generated)


def _round_robin_slots(
    players: list[PairingPlayer],
    rotation_offset: int,
) -> list[PairingPlayer | None]:
    slots: list[PairingPlayer | None] = players.copy()
    if len(slots) % 2 == 1:
        slots.append(None)
    fixed = slots[0]
    rotating = slots[1:]
    offset = rotation_offset % len(rotating)
    return [fixed, *rotating[offset:], *rotating[:offset]]


def _round_robin_conflicts(
    slots: list[PairingPlayer | None],
    previous_pairs: PreviousPairSet,
) -> int:
    conflicts = 0
    for left, right in _slot_pairs(slots):
        if (
            left is not None
            and right is not None
            and _has_previous_pairing(left, right, previous_pairs)
        ):
            conflicts += 1
    return conflicts


def _slot_pairs(
    slots: list[PairingPlayer | None],
) -> list[tuple[PairingPlayer | None, PairingPlayer | None]]:
    return [(slots[index], slots[-index - 1]) for index in range(len(slots) // 2)]


def generate_round_robin_pairings(
    players: list[PairingPlayer],
    previous_pairs: PreviousPairSet,
    round_number: int,
) -> list[GeneratedPairing]:
    ordered_players = sorted(
        players,
        key=lambda player: (player.username.lower(), player.seed_order),
    )
    if len(ordered_players) < 2:
        return []
    slots_count = (
        len(ordered_players) if len(ordered_players) % 2 == 0 else len(ordered_players) + 1
    )
    candidate_offsets = list(range(slots_count - 1))
    preferred_offset = (round_number - 1) % len(candidate_offsets)
    candidate_offsets.remove(preferred_offset)
    candidate_offsets.insert(0, preferred_offset)
    best_slots = min(
        (_round_robin_slots(ordered_players, offset) for offset in candidate_offsets),
        key=lambda slots: _round_robin_conflicts(slots, previous_pairs),
    )
    pairings: list[GeneratedPairing] = []
    fallback_players: list[PairingPlayer] = []
    for left, right in _slot_pairs(best_slots):
        if left is None and right is None:
            continue
        if left is None or right is None:
            bye_player = left or right
            if bye_player is not None:
                pairings.append(
                    GeneratedPairing(
                        white_user_id=bye_player.user_id,
                        black_user_id=None,
                        result="bye",
                    )
                )
            continue
        if _has_previous_pairing(left, right, previous_pairs):
            fallback_players.extend([left, right])
            continue
        pairings.append(
            _assign_colors(
                left,
                right,
                board_number=len(pairings) + 1,
                round_number=round_number,
            )
        )
    if fallback_players:
        pairings.extend(_pair_greedily(fallback_players, previous_pairs, round_number))
    return _renumber_bye_last(pairings)


def _renumber_bye_last(pairings: list[GeneratedPairing]) -> list[GeneratedPairing]:
    normal_pairings = [pairing for pairing in pairings if pairing.result != "bye"]
    bye_pairings = [pairing for pairing in pairings if pairing.result == "bye"]
    return [*normal_pairings, *bye_pairings]
