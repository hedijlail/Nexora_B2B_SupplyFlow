"""Tenant-aware query helpers."""
from uuid import UUID
from sqlalchemy import Select


def for_company(statement: Select, model: type, company_id: UUID) -> Select:
    """Scope a query using the company id derived from the JWT, never user input."""
    return statement.where(model.company_id == company_id)
