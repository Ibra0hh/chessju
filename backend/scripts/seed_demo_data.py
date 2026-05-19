from __future__ import annotations

import argparse
import asyncio
import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.constants import DEFAULT_ROLE_NAMES
from app.auth.models import Role, UserRole
from app.auth.security import hash_password
from app.common.time import utc_now
from app.config import get_settings
from app.games.models import Game
from app.leaderboard.services import recompute_leaderboard
from app.news.models import Announcement, Article
from app.notifications.models import NotificationPreference
from app.pgn.services import create_game_from_parsed_pgn, parse_pgn_text
from app.social.models import Conversation, ConversationMember, Friendship, Message
from app.tournaments.models import Pairing, Round, TimeControl, Tournament, TournamentRegistration
from app.tournaments.services import _upsert_game_for_pairing
from app.users.models import Profile, User, UserPreferences

DEMO_PASSWORD = "ChangeMe123!"
DEMO_ENVIRONMENTS = {"development", "local", "test"}
DEMO_PGN = """[Event "ChessJU Demo Game"]
[Site "University of Jordan"]
[Date "2026.05.19"]
[Round "1"]
[White "ChessJU Demo Member 1"]
[Black "ChessJU Demo Member 2"]
[Result "1-0"]
[ECO "C20"]
[Opening "King's Pawn Game"]
[TimeControl "600+5"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6
8. c3 O-O 9. h3 Nb8 10. d4 Nbd7 1-0
"""


@dataclass(frozen=True)
class DemoUserSpec:
    email: str
    username: str
    full_name: str
    roles: tuple[str, ...] = ("member",)
    university_id: str | None = None
    chesscom_username: str | None = None


@dataclass(frozen=True)
class DemoSeedResult:
    admin_email: str
    member_emails: list[str]
    tournament_slug: str
    pgn_game_created: bool


DEMO_USERS = (
    DemoUserSpec(
        email="admin@example.com",
        username="demo_admin",
        full_name="ChessJU Demo Admin",
        roles=("member", "admin", "super_admin"),
        university_id="DEMO-ADMIN",
        chesscom_username="demo_admin",
    ),
    DemoUserSpec(
        email="member1@example.com",
        username="demo_member_1",
        full_name="ChessJU Demo Member 1",
        university_id="DEMO-001",
        chesscom_username="demo_member_1",
    ),
    DemoUserSpec(
        email="member2@example.com",
        username="demo_member_2",
        full_name="ChessJU Demo Member 2",
        university_id="DEMO-002",
        chesscom_username="demo_member_2",
    ),
    DemoUserSpec(
        email="member3@example.com",
        username="demo_member_3",
        full_name="ChessJU Demo Member 3",
        university_id="DEMO-003",
    ),
    DemoUserSpec(
        email="member4@example.com",
        username="demo_member_4",
        full_name="ChessJU Demo Member 4",
        university_id="DEMO-004",
    ),
    DemoUserSpec(
        email="member5@example.com",
        username="demo_member_5",
        full_name="ChessJU Demo Member 5",
        university_id="DEMO-005",
    ),
)


def ensure_demo_seed_allowed(environment: str) -> None:
    if environment.lower() not in DEMO_ENVIRONMENTS:
        raise RuntimeError(
            "Demo seeding is allowed only in development, local, or test environments."
        )


async def _role_by_name(session: AsyncSession, name: str) -> Role:
    result = await session.execute(select(Role).where(Role.name == name))
    role = result.scalar_one_or_none()
    if role is None:
        role = Role(name=name)
        session.add(role)
        await session.flush()
    return role


async def _ensure_roles(session: AsyncSession) -> dict[str, Role]:
    return {name: await _role_by_name(session, name) for name in DEFAULT_ROLE_NAMES}


async def _ensure_user(
    session: AsyncSession,
    spec: DemoUserSpec,
    roles: dict[str, Role],
) -> User:
    result = await session.execute(select(User).where(User.email == spec.email.lower()))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(email=spec.email.lower(), password_hash=hash_password(DEMO_PASSWORD))
        session.add(user)
        await session.flush()
    else:
        user.password_hash = hash_password(DEMO_PASSWORD)
        user.status = "active"
        user.deleted_at = None

    result = await session.execute(select(Profile).where(Profile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = Profile(
            user_id=user.id,
            username=spec.username,
            full_name=spec.full_name,
            university_id=spec.university_id,
            chesscom_username=spec.chesscom_username,
        )
        session.add(profile)
    else:
        profile.username = spec.username
        profile.full_name = spec.full_name
        profile.university_id = spec.university_id
        profile.chesscom_username = spec.chesscom_username

    if await session.get(UserPreferences, user.id) is None:
        session.add(UserPreferences(user_id=user.id))
    if await session.get(NotificationPreference, user.id) is None:
        session.add(NotificationPreference(user_id=user.id))

    for role_name in spec.roles:
        role = roles[role_name]
        user_role = await session.get(UserRole, {"user_id": user.id, "role_id": role.id})
        if user_role is None:
            session.add(UserRole(user_id=user.id, role_id=role.id, assigned_by=user.id))
    await session.flush()
    return user


async def _ensure_article(session: AsyncSession, admin: User) -> None:
    slug = "demo-welcome-to-chessju"
    result = await session.execute(select(Article).where(Article.slug == slug))
    article = result.scalar_one_or_none()
    if article is None:
        article = Article(
            author_id=admin.id,
            title="Welcome to ChessJU",
            slug=slug,
            summary="A local demo article for the release-candidate MVP.",
            body_markdown=(
                "ChessJU is a custom chess club platform for University of Jordan members."
            ),
            status="published",
            published_at=utc_now(),
        )
        session.add(article)
    else:
        article.status = "published"
        article.published_at = article.published_at or utc_now()
        article.deleted_at = None
    await session.flush()


async def _ensure_announcement(session: AsyncSession, admin: User) -> None:
    result = await session.execute(
        select(Announcement).where(Announcement.title == "Demo tournament night")
    )
    announcement = result.scalar_one_or_none()
    if announcement is None:
        session.add(
            Announcement(
                created_by=admin.id,
                title="Demo tournament night",
                message="Use the demo data to try registrations, pairings, results, and chat.",
                target="all",
                priority="important",
                status="published",
                published_at=utc_now(),
                expires_at=utc_now() + timedelta(days=30),
            )
        )
    else:
        announcement.status = "published"
        announcement.deleted_at = None
        announcement.expires_at = utc_now() + timedelta(days=30)
    await session.flush()


async def _ensure_time_control(session: AsyncSession) -> TimeControl:
    result = await session.execute(select(TimeControl).where(TimeControl.name == "Demo Rapid 10+5"))
    time_control = result.scalar_one_or_none()
    if time_control is None:
        time_control = TimeControl(
            name="Demo Rapid 10+5",
            base_seconds=600,
            increment_seconds=5,
            delay_seconds=0,
            type="rapid",
        )
        session.add(time_control)
        await session.flush()
    return time_control


async def _ensure_tournament(
    session: AsyncSession,
    admin: User,
    members: list[User],
    time_control: TimeControl,
) -> Tournament:
    slug = "demo-rapid-release-candidate"
    result = await session.execute(select(Tournament).where(Tournament.slug == slug))
    tournament = result.scalar_one_or_none()
    starts_at = utc_now() + timedelta(days=2)
    if tournament is None:
        tournament = Tournament(
            title="Demo Rapid Release Candidate",
            slug=slug,
            description="Seeded tournament for local QA and Flutter demos.",
            status="registration_closed",
            format="swiss",
            time_control_id=time_control.id,
            max_players=16,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=3),
            registration_open_at=utc_now() - timedelta(days=3),
            registration_close_at=utc_now() - timedelta(hours=1),
            location="University of Jordan Chess Club",
            created_by=admin.id,
        )
        session.add(tournament)
        await session.flush()
    else:
        tournament.status = "registration_closed"
        tournament.deleted_at = None
        tournament.time_control_id = time_control.id

    for index, member in enumerate(members, start=1):
        result = await session.execute(
            select(TournamentRegistration).where(
                TournamentRegistration.tournament_id == tournament.id,
                TournamentRegistration.user_id == member.id,
            )
        )
        registration = result.scalar_one_or_none()
        if registration is None:
            session.add(
                TournamentRegistration(
                    tournament_id=tournament.id,
                    user_id=member.id,
                    status="approved",
                    seed_rating=1400 - index * 20,
                )
            )
        else:
            registration.status = "approved"
            registration.seed_rating = 1400 - index * 20
            registration.cancelled_at = None
    await session.flush()
    return tournament


async def _ensure_round(session: AsyncSession, tournament: Tournament, round_number: int) -> Round:
    result = await session.execute(
        select(Round).where(
            Round.tournament_id == tournament.id,
            Round.round_number == round_number,
        )
    )
    round_record = result.scalar_one_or_none()
    if round_record is None:
        round_record = Round(
            tournament_id=tournament.id,
            round_number=round_number,
            title=f"Demo Round {round_number}",
            status="completed" if round_number == 1 else "published",
        )
        session.add(round_record)
        await session.flush()
    return round_record


async def _ensure_pairing(
    session: AsyncSession,
    round_record: Round,
    tournament: Tournament,
    admin: User,
    board_number: int,
    white_user_id: uuid.UUID | None,
    black_user_id: uuid.UUID | None,
    result: str,
) -> None:
    existing = await session.scalar(
        select(Pairing).where(
            Pairing.round_id == round_record.id,
            Pairing.board_number == board_number,
        )
    )
    if existing is None:
        existing = Pairing(
            round_id=round_record.id,
            tournament_id=tournament.id,
            board_number=board_number,
            white_user_id=white_user_id,
            black_user_id=black_user_id,
        )
        session.add(existing)
    existing.white_user_id = white_user_id
    existing.black_user_id = black_user_id
    existing.status = "completed"
    existing.result = result
    existing.result_reported_by = admin.id
    existing.result_reported_at = existing.result_reported_at or utc_now()
    await session.flush()
    await _upsert_game_for_pairing(session, existing)


async def _ensure_tournament_flow(
    session: AsyncSession,
    admin: User,
    members: list[User],
    tournament: Tournament,
) -> None:
    round_one = await _ensure_round(session, tournament, 1)
    await _ensure_pairing(
        session, round_one, tournament, admin, 1, members[0].id, members[1].id, "white_win"
    )
    await _ensure_pairing(
        session, round_one, tournament, admin, 2, members[2].id, members[3].id, "draw"
    )
    await _ensure_pairing(session, round_one, tournament, admin, 3, members[4].id, None, "bye")
    await _ensure_round(session, tournament, 2)


async def _ensure_pgn_game(session: AsyncSession, owner: User) -> bool:
    existing = await session.scalar(
        select(Game).where(
            Game.owner_id == owner.id,
            Game.source == "pgn_upload",
            Game.white_name == "ChessJU Demo Member 1",
            Game.black_name == "ChessJU Demo Member 2",
        )
    )
    if existing is not None:
        return False
    parsed = parse_pgn_text(DEMO_PGN)
    await create_game_from_parsed_pgn(
        session=session,
        user_id=owner.id,
        pgn_text=DEMO_PGN,
        parsed=parsed,
        import_source="paste",
        game_source="pgn_upload",
    )
    return True


def _ordered_pair(first: uuid.UUID, second: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    return (first, second) if first < second else (second, first)


async def _ensure_social_demo(session: AsyncSession, first: User, second: User) -> None:
    user_a_id, user_b_id = _ordered_pair(first.id, second.id)
    friendship = await session.scalar(
        select(Friendship).where(
            Friendship.user_a_id == user_a_id,
            Friendship.user_b_id == user_b_id,
        )
    )
    if friendship is None:
        session.add(Friendship(user_a_id=user_a_id, user_b_id=user_b_id))
        await session.flush()

    conversation_id = await session.scalar(
        select(ConversationMember.conversation_id)
        .where(ConversationMember.user_id.in_([first.id, second.id]))
        .group_by(ConversationMember.conversation_id)
        .having(func.count(ConversationMember.user_id) == 2)
    )
    conversation = await session.get(Conversation, conversation_id) if conversation_id else None
    if conversation is None:
        conversation = Conversation(type="direct")
        session.add(conversation)
        await session.flush()
        session.add_all(
            [
                ConversationMember(conversation_id=conversation.id, user_id=first.id),
                ConversationMember(conversation_id=conversation.id, user_id=second.id),
            ]
        )
        await session.flush()
    message_count = await session.scalar(
        select(func.count()).select_from(Message).where(Message.conversation_id == conversation.id)
    )
    if not message_count:
        session.add_all(
            [
                Message(
                    conversation_id=conversation.id,
                    sender_id=first.id,
                    body="Ready for the demo rapid game?",
                ),
                Message(
                    conversation_id=conversation.id,
                    sender_id=second.id,
                    body="Ready. Good luck!",
                ),
            ]
        )
    await session.flush()


async def seed_demo_data(session: AsyncSession) -> DemoSeedResult:
    roles = await _ensure_roles(session)
    users = [await _ensure_user(session, spec, roles) for spec in DEMO_USERS]
    admin = users[0]
    members = users[1:]
    await _ensure_article(session, admin)
    await _ensure_announcement(session, admin)
    time_control = await _ensure_time_control(session)
    tournament = await _ensure_tournament(session, admin, members, time_control)
    await _ensure_tournament_flow(session, admin, members, tournament)
    pgn_game_created = await _ensure_pgn_game(session, members[0])
    await _ensure_social_demo(session, members[0], members[1])
    await session.commit()
    await recompute_leaderboard(session, admin_id=admin.id)
    return DemoSeedResult(
        admin_email=DEMO_USERS[0].email,
        member_emails=[spec.email for spec in DEMO_USERS[1:]],
        tournament_slug=tournament.slug,
        pgn_game_created=pgn_game_created,
    )


async def _run_seed(database_url: str | None = None) -> DemoSeedResult:
    settings = get_settings()
    ensure_demo_seed_allowed(settings.environment)
    engine = create_async_engine(database_url or settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            return await seed_demo_data(session)
    finally:
        await engine.dispose()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Seed local ChessJU demo data.")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm this is a local development database.",
    )
    parser.add_argument(
        "--database-url",
        help="Override CHESSJU_DATABASE_URL before connecting.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    if not args.yes:
        parser.error("Refusing to seed without --yes confirmation.")
    result = asyncio.run(_run_seed(args.database_url))
    print("Demo data seeded for local development.")
    print(f"Admin: {result.admin_email} / {DEMO_PASSWORD}")
    print(f"Members: {', '.join(result.member_emails)} / {DEMO_PASSWORD}")
    print(f"Tournament slug: {result.tournament_slug}")
    print(f"PGN game created this run: {result.pgn_game_created}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
