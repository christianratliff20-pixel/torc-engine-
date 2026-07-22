from dataclasses import dataclass
from typing import Optional


@dataclass
class PlanOption:
    plan: str
    cycle: str
    price_usd: float
    minutes_included: int
    stripe_price_id_env: str


PLAN_OPTIONS: list[PlanOption] = [
    PlanOption("free", "monthly", 0.0, 90, ""),
    PlanOption("starter", "weekly", 4.25, 200, "STRIPE_PRICE_STARTER_WEEKLY"),
    PlanOption("starter", "monthly", 12.0, 400, "STRIPE_PRICE_STARTER_MONTHLY"),
    PlanOption("starter", "annual", 9.0, 400, "STRIPE_PRICE_STARTER_ANNUAL"),
    PlanOption("pro", "weekly", 9.0, 450, "STRIPE_PRICE_PRO_WEEKLY"),
    PlanOption("pro", "monthly", 27.0, 1000, "STRIPE_PRICE_PRO_MONTHLY"),
    PlanOption("pro", "annual", 22.0, 1000, "STRIPE_PRICE_PRO_ANNUAL"),
    PlanOption("studio", "monthly", 59.0, 2500, "STRIPE_PRICE_STUDIO_MONTHLY"),
    PlanOption("studio", "annual", 49.0, 2500, "STRIPE_PRICE_STUDIO_ANNUAL"),
]

ROLLOVER_MULTIPLIER = 1.5
PAYG_RATE_USD_PER_MINUTE = 0.05
PAYG_MINIMUM_USD = 5.0

TRIAL_LENGTH_DAYS = 14
TRIAL_PLAN = "pro"
TRIAL_MINUTES = 300


def find_plan_option(plan: str, cycle: str) -> Optional[PlanOption]:
    return next((p for p in PLAN_OPTIONS if p.plan == plan and p.cycle == cycle), None)


def minutes_for_plan(plan: str, cycle: str = "monthly") -> int:
    opt = find_plan_option(plan, cycle)
    return opt.minutes_included if opt else 0


def payg_minutes_for_amount(amount_usd: float) -> int:
    import math
    return math.ceil(amount_usd / PAYG_RATE_USD_PER_MINUTE)


def start_trial(user) -> None:
    from datetime import datetime, timedelta

    if user.has_used_trial:
        return

    now = datetime.utcnow()
    user.plan = TRIAL_PLAN
    user.trial_started_at = now
    user.trial_ends_at = now + timedelta(days=TRIAL_LENGTH_DAYS)
    user.has_used_trial = True
    user.period_started_at = now
    user.minutes_used_this_period = 0.0


def is_trial_active(user) -> bool:
    from datetime import datetime
    return bool(user.trial_ends_at) and datetime.utcnow() < user.trial_ends_at


def trial_days_remaining(user) -> int:
    from datetime import datetime
    if not is_trial_active(user):
        return 0
    return max(0, (user.trial_ends_at - datetime.utcnow()).days)


def expire_trial_if_needed(user) -> bool:
    from datetime import datetime

    if user.trial_ends_at and datetime.utcnow() >= user.trial_ends_at and not user.stripe_subscription_id:
        user.plan = "free"
        user.billing_cycle = None
        user.period_started_at = datetime.utcnow()
        user.minutes_used_this_period = 0.0
        return True
    return False


def minutes_included_for_user(user) -> int:
    if is_trial_active(user):
        return TRIAL_MINUTES
    return minutes_for_plan(user.plan, user.billing_cycle or "monthly")


def minutes_remaining_for_user(user) -> float:
    included = minutes_included_for_user(user)
    return max(0.0, included + user.minutes_rollover_balance - user.minutes_used_this_period)


def record_usage(user, minutes: float) -> None:
    user.minutes_used_this_period += minutes


def roll_over_period(user) -> None:
    from datetime import datetime

    included = minutes_included_for_user(user)
    unused = max(0.0, included - user.minutes_used_this_period)
    cap = included * ROLLOVER_MULTIPLIER
    user.minutes_rollover_balance = min(cap, user.minutes_rollover_balance + unused)
    user.minutes_used_this_period = 0.0
    user.period_started_at = datetime.utcnow()
