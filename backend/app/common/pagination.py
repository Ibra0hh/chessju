from dataclasses import dataclass

from app.common.schemas import PaginationMetadata


@dataclass(frozen=True)
class PaginationParams:
    limit: int
    offset: int


def build_pagination(limit: int, offset: int, count: int) -> PaginationMetadata:
    return PaginationMetadata(limit=limit, offset=offset, count=count)
