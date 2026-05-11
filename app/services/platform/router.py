from fastapi import APIRouter

from app.services.platform.endpoints import auth
from app.services.platform.endpoints import credits
from app.services.platform.endpoints import design
from app.services.platform.endpoints import health
from app.services.platform.endpoints import revenuecat
from app.services.platform.endpoints import subscriptions

router = APIRouter()

router.include_router(auth.router, tags=["Auth"])
router.include_router(credits.router, tags=["Credits"])
router.include_router(design.router, tags=["Design"])
router.include_router(health.router, tags=["Platform"])
router.include_router(revenuecat.router, tags=["RevenueCat"])
router.include_router(subscriptions.router, tags=["Subscriptions"])
