from fastapi import APIRouter

from app.services.platform.endpoints import (
    auth,
    design,
    discover,
    generations,
    health,
    revenuecat,
    subscriptions,
)

router = APIRouter()

router.include_router(auth.router, tags=["Auth"])
router.include_router(discover.router, tags=["Discover"])
router.include_router(design.router, tags=["Design"])
router.include_router(generations.router, tags=["Generations"])
router.include_router(health.router, tags=["Platform"])
router.include_router(revenuecat.router, tags=["RevenueCat"])
router.include_router(subscriptions.router, tags=["Subscriptions"])
