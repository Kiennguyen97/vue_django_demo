from datetime import datetime

import django_rq
from rq_scheduler import Scheduler

from django.apps import AppConfig
from django.conf import settings

from . import odoo_client


def load_schedules(scheduler):
    # Delete any existing jobs in the scheduler when the app starts up
    for job in scheduler.get_jobs():
        job.delete()

    scheduler.schedule(
        datetime.utcnow(),
        "odoo.tasks.sync_order_to_odoo",
        interval=60 * 1,
        repeat=None,
        queue_name="default",
    )

    scheduler.schedule(
        datetime.utcnow(),
        "odoo.products.migrate_product.execute",
        interval=60 * 5,
        repeat=None,
        queue_name="low",
    )

    scheduler.schedule(
        datetime.utcnow(),
        "odoo.categories.migrate_category.execute",
        interval=60 * 5,
        repeat=None,
        queue_name="low",
    )

    scheduler.schedule(
        datetime.utcnow(),
        "odoo.tasks.update_product_order",
        interval=60 * 60 * 12,
        repeat=None,
        queue_name="low",
    )

    scheduler.schedule(
        datetime.utcnow(),
        "odoo.customers.migrate_company.execute",
        interval=60 * 15,
        repeat=None,
        queue_name="low",
    )

    scheduler.schedule(
        datetime.utcnow(),
        "odoo.customers.migrate_pricelist_cpg.execute",
        interval=60 * 25,
        repeat=None,
        queue_name="low",
    )

    scheduler.schedule(
        datetime.utcnow(),
        "odoo.customers.migrate_users.execute",
        interval=60 * 5,
        repeat=None,
        queue_name="low",
    )

    scheduler.schedule(
        datetime.utcnow(),
        "odoo.customers.transfer_user.execute",
        interval=60 * 1,
        repeat=None,
        queue_name="default",
    )

    scheduler.schedule(
        datetime.utcnow(),
        "odoo.products.update_brand.execute",
        interval=60 * 5,
        repeat=None,
        queue_name="low",
    )

    """
    scheduler.schedule(
        datetime.utcnow(),
        "odoo.tasks.sentry_with_failed_job",
        interval=60 * 60,
        repeat=None,
        queue_name="low",
    )
    """

    scheduler.schedule(
        datetime.utcnow(),
        "odoo.products.indexer_products.execute",
        interval=60 * 60,
        repeat=None,
        queue_name="low",
    )

    scheduler.schedule(
        datetime.utcnow(),
        "odoo.products.generate_google_merchant_feed_xml.execute",
        interval=24 * 60 * 60,
        repeat=None,
        queue_name="low",
    )

    scheduler.schedule(
        datetime.utcnow(),
        "odoo.products.migrate_order_all_invoice.execute",
        interval=60 * 60 * 24,
        repeat=None,
        queue_name="low",
    )


class OdooConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "odoo"

    def ready(self):
        from odoo.tasks import sync_order_to_odoo

        try:
            scheduler = django_rq.get_scheduler("default")
            load_schedules(scheduler)
        except Exception as e:
            if settings.CONFIG_ENV == "dev":
                print(e)
            else:
                raise e
