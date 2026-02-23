"""Website customers registry: prospects who want to see the art of the possible (rebuilt site with SEO)."""
from clawbot.integrations.website_customers.sheets import (
    register_customer,
    list_customers,
    update_customer,
    ensure_sheet,
    get_customer_by_slug,
)

__all__ = ["register_customer", "list_customers", "update_customer", "ensure_sheet", "get_customer_by_slug"]
