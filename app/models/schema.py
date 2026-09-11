"""Shared SQLAlchemy types and incremental ORM mappings.

The initial hand-written Alembic migration is authoritative for the complete
production schema. Add domain ORM mappings here alongside their services as
the API endpoints are implemented.
"""
import enum

from app.core.database import Base


class UserRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    SALES = "sales"
    WAREHOUSE = "warehouse"
    ACCOUNTANT = "accountant"
    VIEWER = "viewer"


class OrderStatus(str, enum.Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    VOID = "void"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class StockMovementType(str, enum.Enum):
    OPENING = "opening"
    RECEIPT = "receipt"
    SALE = "sale"
    ADJUSTMENT = "adjustment"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    RETURN = "return"
