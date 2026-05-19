from dataclasses import dataclass
from typing import Any

import chess
import chess.engine


@dataclass(frozen=True)
class PositionAnalysis:
    evaluation: dict[str, Any] | None
    side_score_cp: int | None
    best_move_uci: str | None
    best_move_san: str | None
    principal_variation: list[str]


def format_cp_evaluation(value: int) -> dict[str, Any]:
    return {
        "type": "cp",
        "value": value,
        "display": f"{value / 100:+.2f}",
    }


def format_mate_evaluation(value: int) -> dict[str, Any]:
    prefix = "" if value >= 0 else "-"
    return {
        "type": "mate",
        "value": value,
        "display": f"{prefix}M{abs(value)}",
    }


def format_score(score: chess.engine.PovScore) -> dict[str, Any] | None:
    mate = score.mate()
    if mate is not None:
        return format_mate_evaluation(mate)
    cp = score.score()
    if cp is None:
        return None
    return format_cp_evaluation(cp)


def score_to_cp(score: chess.engine.PovScore) -> int | None:
    return score.score(mate_score=100_000)


def classify_centipawn_loss(centipawn_loss: int | None) -> str:
    if centipawn_loss is None:
        return "unknown"
    if centipawn_loss <= 15:
        return "best"
    if centipawn_loss <= 35:
        return "excellent"
    if centipawn_loss <= 75:
        return "good"
    if centipawn_loss <= 150:
        return "inaccuracy"
    if centipawn_loss <= 300:
        return "mistake"
    return "blunder"


class StockfishEngine:
    def __init__(
        self,
        path: str,
        time_limit_ms: int | None = None,
        pv_limit: int = 5,
    ) -> None:
        self.path = path
        self.time_limit_ms = time_limit_ms
        self.pv_limit = pv_limit
        self._engine: chess.engine.SimpleEngine | None = None

    def __enter__(self) -> "StockfishEngine":
        self._engine = chess.engine.SimpleEngine.popen_uci(self.path)
        return self

    def __exit__(self, *_: object) -> None:
        if self._engine is not None:
            self._engine.quit()
            self._engine = None

    @property
    def version(self) -> str | None:
        if self._engine is None:
            return None
        return str(self._engine.id.get("name") or "stockfish")

    def analyze(
        self,
        board: chess.Board,
        depth: int,
        pov_color: chess.Color,
    ) -> PositionAnalysis:
        if self._engine is None:
            raise RuntimeError("Stockfish engine is not running")

        limit_kwargs: dict[str, int | float] = {"depth": depth}
        if self.time_limit_ms is not None:
            limit_kwargs["time"] = self.time_limit_ms / 1000
        info = self._engine.analyse(board, chess.engine.Limit(**limit_kwargs))
        score = info.get("score")
        evaluation = format_score(score.pov(chess.WHITE)) if score is not None else None
        side_score_cp = score_to_cp(score.pov(pov_color)) if score is not None else None
        principal_variation = [
            move.uci() for move in list(info.get("pv") or [])[: self.pv_limit]
        ]
        best_move = info.get("pv", [None])[0] if info.get("pv") else None
        best_move_uci = best_move.uci() if best_move is not None else None
        best_move_san = None
        if best_move is not None and best_move in board.legal_moves:
            best_move_san = board.san(best_move)

        return PositionAnalysis(
            evaluation=evaluation,
            side_score_cp=side_score_cp,
            best_move_uci=best_move_uci,
            best_move_san=best_move_san,
            principal_variation=principal_variation,
        )
