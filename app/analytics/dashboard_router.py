from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.analytics.dashboard_schemas import DashboardSummary
from app.auth.dependencies import CurrentUser, require_roles
from app.core.database import get_db

router = APIRouter(prefix="/dashboard", tags=["analytics"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(
    current_user: CurrentUser = Depends(require_roles("owner", "admin", "accountant", "sales")),
    db: Session = Depends(get_db),
):
    """Current, tenant-scoped operational snapshot; amounts use company currency."""
    row = db.execute(text("""
        SELECT
          COALESCE((SELECT SUM(grand_total) FROM orders WHERE company_id=:company_id AND status='fulfilled'), 0)::float AS fulfilled_sales_total,
          COALESCE((SELECT SUM(grand_total) FROM orders WHERE company_id=:company_id AND status IN ('draft','confirmed','processing')), 0)::float AS open_orders_total,
          COALESCE((SELECT SUM(i.grand_total - COALESCE(p.completed_total, 0))
            FROM invoices i
            LEFT JOIN (
              SELECT invoice_id, SUM(amount) AS completed_total FROM payments
              WHERE company_id=:company_id AND status='completed' GROUP BY invoice_id
            ) p ON p.invoice_id=i.id
            WHERE i.company_id=:company_id AND i.status IN ('issued','partially_paid')), 0)::float AS invoices_outstanding_total,
          COALESCE((SELECT SUM(quantity) FROM stocks WHERE company_id=:company_id), 0)::float AS stock_units_total,
          COALESCE((SELECT SUM(s.quantity * p.cost_price) FROM stocks s
            JOIN products p ON p.id=s.product_id AND p.company_id=s.company_id
            WHERE s.company_id=:company_id), 0)::float AS stock_cost_value,
          COALESCE((SELECT COUNT(*) FROM invoices WHERE company_id=:company_id AND status IN ('issued','partially_paid') AND due_date < CURRENT_DATE), 0)::integer AS overdue_invoices_count
    """), {"company_id": current_user.company_id}).mappings().one()
    return row
