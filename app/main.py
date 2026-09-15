from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.auth.router import router as auth_router
from app.users.router import router as users_router
from app.customers.router import router as customers_router
from app.products.router import router as products_router
from app.inventory.router import router as inventory_router
from app.orders.router import router as orders_router
from app.invoices.router import router as invoices_router
from app.payments.router import router as payments_router
from app.analytics.router import router as audit_router
from app.settings.router import router as settings_router
from app.pricing.router import router as pricing_router
from app.analytics.dashboard_router import router as dashboard_router

settings = get_settings()
app = FastAPI(title=settings.app_name, debug=settings.debug)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(customers_router)
app.include_router(products_router)
app.include_router(inventory_router)
app.include_router(orders_router)
app.include_router(invoices_router)
app.include_router(payments_router)
app.include_router(audit_router)
app.include_router(settings_router)
app.include_router(pricing_router)
app.include_router(dashboard_router)
app.mount("/app", StaticFiles(directory="app/web", html=True), name="web")


@app.get("/health", tags=["system"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}
