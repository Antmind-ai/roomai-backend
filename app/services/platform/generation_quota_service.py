from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.platform import revenuecat_service
from app.services.platform.models import DeviceUser, GenerationUsage
from app.services.platform.models.subscription import PurchaseRecord

COUNTED_USAGE_STATUSES = ("reserved", "completed")
SUBSCRIPTION_DAILY_WINDOW = timedelta(days=1)
SUBSCRIPTION_WEEKLY_WINDOW = timedelta(days=7)


@dataclass(frozen=True)
class GenerationQuotaSnapshot:
    user_id: uuid.UUID
    has_active_subscription: bool
    plan_type: str | None
    quota_scope: str
    free_lifetime_generation_limit: int
    free_lifetime_generations_used: int
    free_lifetime_generations_remaining: int
    daily_generation_limit: int | None
    daily_generations_used: int
    daily_generations_remaining: int | None
    weekly_generation_limit: int | None
    weekly_generations_used: int
    weekly_generations_remaining: int | None


@dataclass(frozen=True)
class GenerationReservationResult:
    usage_id: uuid.UUID
    snapshot: GenerationQuotaSnapshot


class GenerationQuotaExceededError(Exception):
    def __init__(self, *, reason: str, snapshot: GenerationQuotaSnapshot):
        super().__init__(reason)
        self.reason = reason
        self.snapshot = snapshot

    @property
    def message(self) -> str:
        if self.reason == "free_trial_exhausted":
            return "Free generation limit reached. Upgrade to continue."
        if self.reason == "daily_generation_limit_reached":
            return "Daily generation limit reached. Try again later."
        if self.reason == "weekly_generation_limit_reached":
            return "Weekly generation limit reached. Try again later."
        return "Generation limit reached."


async def get_generation_quota(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    now: datetime | None = None,
) -> GenerationQuotaSnapshot:
    await _load_active_user(db, user_id=user_id)
    active_subscription = await _get_active_subscription(db, user_id=user_id)
    return await _build_quota_snapshot(
        db,
        user_id=user_id,
        active_subscription=active_subscription,
        now=now or datetime.now(UTC),
    )


async def reserve_generation_quota(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    generation_type: str,
    reference_id: str | None,
    now: datetime | None = None,
) -> GenerationReservationResult:
    reservation_time = now or datetime.now(UTC)
    user = await _lock_active_user(db, user_id=user_id)
    active_subscription = await _get_active_subscription(db, user_id=user.id)
    snapshot = await _build_quota_snapshot(
        db,
        user_id=user.id,
        active_subscription=active_subscription,
        now=reservation_time,
    )

    _raise_if_quota_exceeded(snapshot)

    usage = GenerationUsage(
        user_id=user.id,
        generation_type=generation_type,
        reference_id=reference_id,
        status="reserved",
        reserved_at=reservation_time,
    )
    db.add(usage)
    await db.flush()

    return GenerationReservationResult(usage_id=usage.id, snapshot=snapshot)


async def complete_generation_quota(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    generation_type: str,
    reference_id: str,
    now: datetime | None = None,
) -> bool:
    usage = await _find_generation_usage(
        db,
        user_id=user_id,
        generation_type=generation_type,
        reference_id=reference_id,
    )
    if usage is None:
        return False
    if usage.status == "completed":
        return True
    if usage.status == "released":
        return False

    usage.status = "completed"
    usage.completed_at = now or datetime.now(UTC)
    return True


async def release_generation_quota(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    generation_type: str,
    reference_id: str,
    now: datetime | None = None,
) -> bool:
    usage = await _find_generation_usage(
        db,
        user_id=user_id,
        generation_type=generation_type,
        reference_id=reference_id,
    )
    if usage is None:
        return False
    if usage.status == "released":
        return True
    if usage.status == "completed":
        return False

    usage.status = "released"
    usage.released_at = now or datetime.now(UTC)
    return True


def quota_snapshot_payload(snapshot: GenerationQuotaSnapshot) -> dict[str, object]:
    return {
        "user_id": snapshot.user_id,
        "has_active_subscription": snapshot.has_active_subscription,
        "plan_type": snapshot.plan_type,
        "quota_scope": snapshot.quota_scope,
        "free_lifetime_generation_limit": snapshot.free_lifetime_generation_limit,
        "free_lifetime_generations_used": snapshot.free_lifetime_generations_used,
        "free_lifetime_generations_remaining": snapshot.free_lifetime_generations_remaining,
        "daily_generation_limit": snapshot.daily_generation_limit,
        "daily_generations_used": snapshot.daily_generations_used,
        "daily_generations_remaining": snapshot.daily_generations_remaining,
        "weekly_generation_limit": snapshot.weekly_generation_limit,
        "weekly_generations_used": snapshot.weekly_generations_used,
        "weekly_generations_remaining": snapshot.weekly_generations_remaining,
    }


def quota_exceeded_detail(exc: GenerationQuotaExceededError) -> dict[str, object]:
    payload = quota_snapshot_payload(exc.snapshot)
    payload["user_id"] = str(payload["user_id"])
    return {
        "error": exc.reason,
        "message": exc.message,
        "quota": payload,
    }


async def _load_active_user(db: AsyncSession, *, user_id: uuid.UUID) -> DeviceUser:
    result = await db.execute(
        select(DeviceUser).where(
            DeviceUser.id == user_id,
            DeviceUser.deleted_at.is_(None),
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise ValueError("User not found")
    return user


async def _lock_active_user(db: AsyncSession, *, user_id: uuid.UUID) -> DeviceUser:
    result = await db.execute(
        select(DeviceUser)
        .where(
            DeviceUser.id == user_id,
            DeviceUser.deleted_at.is_(None),
        )
        .with_for_update()
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise ValueError("User not found")
    return user


async def _get_active_subscription(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> PurchaseRecord | None:
    return await revenuecat_service.get_current_subscription_record(db, user_id=user_id)


async def _build_quota_snapshot(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    active_subscription: PurchaseRecord | None,
    now: datetime,
) -> GenerationQuotaSnapshot:
    daily_cutoff = now - SUBSCRIPTION_DAILY_WINDOW
    weekly_cutoff = now - SUBSCRIPTION_WEEKLY_WINDOW

    lifetime_used = await _count_limited_usage(db, user_id=user_id)
    daily_used = await _count_limited_usage(db, user_id=user_id, since=daily_cutoff)
    weekly_used = await _count_limited_usage(db, user_id=user_id, since=weekly_cutoff)

    has_active_subscription = active_subscription is not None
    plan_type = (
        revenuecat_service.get_plan_type_for_product(
            active_subscription.revenuecat_product_id
        )
        if active_subscription
        else None
    )

    free_limit = settings.free_lifetime_generation_limit
    if has_active_subscription:
        daily_limit: int | None = settings.subscription_daily_generation_limit
        weekly_limit: int | None = settings.subscription_weekly_generation_limit
        quota_scope = "subscription"
    else:
        daily_limit = None
        weekly_limit = None
        quota_scope = "free_trial"

    return GenerationQuotaSnapshot(
        user_id=user_id,
        has_active_subscription=has_active_subscription,
        plan_type=plan_type,
        quota_scope=quota_scope,
        free_lifetime_generation_limit=free_limit,
        free_lifetime_generations_used=lifetime_used,
        free_lifetime_generations_remaining=max(free_limit - lifetime_used, 0),
        daily_generation_limit=daily_limit,
        daily_generations_used=daily_used,
        daily_generations_remaining=(
            max(daily_limit - daily_used, 0) if daily_limit is not None else None
        ),
        weekly_generation_limit=weekly_limit,
        weekly_generations_used=weekly_used,
        weekly_generations_remaining=(
            max(weekly_limit - weekly_used, 0) if weekly_limit is not None else None
        ),
    )


async def _count_limited_usage(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    since: datetime | None = None,
) -> int:
    statement = (
        select(func.count(GenerationUsage.id))
        .where(GenerationUsage.user_id == user_id)
        .where(GenerationUsage.status.in_(COUNTED_USAGE_STATUSES))
    )
    if since is not None:
        statement = statement.where(GenerationUsage.reserved_at >= since)

    result = await db.execute(statement)
    count = result.scalar_one()
    return int(count or 0)


async def _find_generation_usage(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    generation_type: str,
    reference_id: str,
) -> GenerationUsage | None:
    result = await db.execute(
        select(GenerationUsage)
        .where(GenerationUsage.user_id == user_id)
        .where(GenerationUsage.generation_type == generation_type)
        .where(GenerationUsage.reference_id == reference_id)
        .order_by(GenerationUsage.reserved_at.desc())
        .limit(1)
        .with_for_update()
    )
    return result.scalar_one_or_none()


def _raise_if_quota_exceeded(snapshot: GenerationQuotaSnapshot) -> None:
    if not snapshot.has_active_subscription:
        if (
            snapshot.free_lifetime_generations_used
            >= snapshot.free_lifetime_generation_limit
        ):
            raise GenerationQuotaExceededError(
                reason="free_trial_exhausted",
                snapshot=snapshot,
            )
        return

    if (
        snapshot.daily_generation_limit is not None
        and snapshot.daily_generations_used >= snapshot.daily_generation_limit
    ):
        raise GenerationQuotaExceededError(
            reason="daily_generation_limit_reached",
            snapshot=snapshot,
        )

    if (
        snapshot.weekly_generation_limit is not None
        and snapshot.weekly_generations_used >= snapshot.weekly_generation_limit
    ):
        raise GenerationQuotaExceededError(
            reason="weekly_generation_limit_reached",
            snapshot=snapshot,
        )
