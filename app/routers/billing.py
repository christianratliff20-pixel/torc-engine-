import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app import models, schemas, auth as auth_utils, billing

router = APIRouter()


def _stripe():
    if not settings.stripe_secret_key:
        raise HTTPException(501, "Stripe is not configured yet — set STRIPE_SECRET_KEY in .env")
    import stripe
    stripe.api_key = settings.stripe_secret_key
    return stripe


@router.get("/plans", response_model=list[schemas.PlanOptionOut])
def list_plans():
    return [
        schemas.PlanOptionOut(plan=p.plan, cycle=p.cycle, price_usd=p.price_usd, minutes_included=p.minutes_included)
        for p in billing.PLAN_OPTIONS
    ]


@router.get("/me", response_model=schemas.BillingStatusOut)
def get_my_billing(
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    downgraded = billing.expire_trial_if_needed(current_user)
    if downgraded:
        db.commit()

    return schemas.BillingStatusOut(
        plan=current_user.plan,
        billing_cycle=current_user.billing_cycle,
        is_trial=billing.is_trial_active(current_user),
        trial_days_remaining=billing.trial_days_remaining(current_user),
        minutes_included=billing.minutes_included_for_user(current_user),
        minutes_used_this_period=current_user.minutes_used_this_period,
        minutes_rollover_balance=current_user.minutes_rollover_balance,
        minutes_remaining=billing.minutes_remaining_for_user(current_user),
        has_payment_method=bool(current_user.stripe_subscription_id),
    )


@router.post("/checkout", response_model=schemas.CheckoutSessionOut)
def create_checkout(
    payload: schemas.CheckoutRequest,
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    stripe = _stripe()

    option = billing.find_plan_option(payload.plan, payload.cycle)
    if not option:
        raise HTTPException(400, f"No such plan/cycle combination: {payload.plan}/{payload.cycle}")

    price_id = getattr(settings, option.stripe_price_id_env.lower(), None)
    if not price_id:
        raise HTTPException(501, f"Stripe price ID not configured for {payload.plan}/{payload.cycle} — set {option.stripe_price_id_env} in .env")

    if not current_user.stripe_customer_id:
        customer = stripe.Customer.create(email=current_user.email, metadata={"user_id": str(current_user.id)})
        current_user.stripe_customer_id = customer.id
        db.commit()

    session = stripe.checkout.Session.create(
        customer=current_user.stripe_customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{settings.frontend_url}/billing?checkout=success",
        cancel_url=f"{settings.frontend_url}/billing?checkout=cancelled",
        metadata={"user_id": str(current_user.id), "plan": payload.plan, "cycle": payload.cycle},
    )
    return schemas.CheckoutSessionOut(checkout_url=session.url)


@router.post("/payg-checkout", response_model=schemas.CheckoutSessionOut)
def create_payg_checkout(
    payload: schemas.PaygCheckoutRequest,
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    stripe = _stripe()

    if payload.amount_usd < billing.PAYG_MINIMUM_USD:
        raise HTTPException(400, f"Minimum PAYG purchase is ${billing.PAYG_MINIMUM_USD}")

    minutes = billing.payg_minutes_for_amount(payload.amount_usd)

    if not current_user.stripe_customer_id:
        customer = stripe.Customer.create(email=current_user.email, metadata={"user_id": str(current_user.id)})
        current_user.stripe_customer_id = customer.id
        db.commit()

    session = stripe.checkout.Session.create(
        customer=current_user.stripe_customer_id,
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": f"{minutes} processing minutes (pay-as-you-go)"},
                "unit_amount": int(round(payload.amount_usd * 100)),
            },
            "quantity": 1,
        }],
        success_url=f"{settings.frontend_url}/billing?payg=success",
        cancel_url=f"{settings.frontend_url}/billing?payg=cancelled",
        metadata={"user_id": str(current_user.id), "payg_minutes": str(minutes)},
    )
    return schemas.CheckoutSessionOut(checkout_url=session.url)


@router.post("/portal", response_model=schemas.PortalSessionOut)
def create_portal_session(
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    stripe = _stripe()

    if not current_user.stripe_customer_id:
        raise HTTPException(400, "No billing account yet — subscribe to a plan first")

    session = stripe.billing_portal.Session.create(
        customer=current_user.stripe_customer_id,
        return_url=f"{settings.frontend_url}/settings",
    )
    return schemas.PortalSessionOut(portal_url=session.url)


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    stripe = _stripe()

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
    except (ValueError, Exception) as e:
        raise HTTPException(400, f"Invalid webhook signature: {e}")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        user_id = data.get("metadata", {}).get("user_id")
        if not user_id:
            return {"ok": True}
        user = db.query(models.User).filter(models.User.id == uuid.UUID(user_id)).first()
        if not user:
            return {"ok": True}

        if data.get("mode") == "subscription":
            plan = data["metadata"].get("plan")
            cycle = data["metadata"].get("cycle")
            user.plan = plan
            user.billing_cycle = cycle
            user.stripe_subscription_id = data.get("subscription")
            user.period_started_at = datetime.utcnow()
            user.minutes_used_this_period = 0.0
        elif data.get("mode") == "payment":
            minutes = float(data["metadata"].get("payg_minutes", 0))
            user.minutes_rollover_balance += minutes

        db.commit()

    elif event_type == "invoice.paid":
        customer_id = data.get("customer")
        user = db.query(models.User).filter(models.User.stripe_customer_id == customer_id).first()
        if user:
            billing.roll_over_period(user)
            db.commit()

    elif event_type == "customer.subscription.deleted":
        customer_id = data.get("customer")
        user = db.query(models.User).filter(models.User.stripe_customer_id == customer_id).first()
        if user:
            user.plan = "free"
            user.billing_cycle = None
            user.stripe_subscription_id = None
            db.commit()

    return {"ok": True}
