from pydantic import BaseModel


class DashboardSummary(BaseModel):
    fulfilled_sales_total: float
    open_orders_total: float
    invoices_outstanding_total: float
    stock_units_total: float
    stock_cost_value: float
    overdue_invoices_count: int
