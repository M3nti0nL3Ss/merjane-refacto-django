"""Replays the original implementation against the refactored one.

Scaffolding for the refactoring, delete it once the refactor is accepted.
"""

import itertools
from datetime import date, timedelta
from unittest.mock import Mock

from django.test import SimpleTestCase

from orders.entities.product import Product
from orders.services.product_service import ProductService

TODAY = date.today()


def in_days(days):
    return TODAY + timedelta(days=days)


def legacy_process(p, pr, ns):

    def notify_delay(lead_time, p):
        p.lead_time = lead_time
        pr.save(p)
        ns.send_delay_notification(lead_time, p.name)

    def handle_seasonal_product(p):
        if date.today() + timedelta(days=p.lead_time) > p.season_end_date:
            ns.send_out_of_stock_notification(p.name)
            p.available = 0
            pr.save(p)
        elif p.season_start_date > date.today():
            ns.send_out_of_stock_notification(p.name)
            pr.save(p)
        else:
            notify_delay(p.lead_time, p)

    def handle_expired_product(p):
        if p.available > 0 and p.expiry_date > date.today():
            p.available -= 1
            pr.save(p)
        else:
            p.available = 0
            pr.save(p)
            ns.send_expiry_notification(p.name)

    if p.type == "NORMAL":
        if p.available > 0:
            p.available = p.available - 1
            pr.save(p)
        else:
            lead_time = p.lead_time
            if lead_time > 0:
                notify_delay(lead_time, p)
    elif p.type == "SEASONAL":
        if (date.today() > p.season_start_date and date.today() < p.season_end_date
                and p.available > 0):
            p.available = p.available - 1
            pr.save(p)
        else:
            handle_seasonal_product(p)
    elif p.type == "EXPIRABLE":
        if p.available > 0 and p.expiry_date > date.today():
            p.available = p.available - 1
            pr.save(p)
        else:
            handle_expired_product(p)


def every_product_situation():
    for available, lead_time in itertools.product([0, 1, 15], [0, 6, 30, 200]):
        common = {'available': available, 'lead_time': lead_time}
        yield {'type': "NORMAL", **common}
        for expiry in [-30, -1, 0, 1, 26]:
            yield {'type': "EXPIRABLE", 'expiry_date': in_days(expiry), **common}
        for start, end in [(-240, -2), (-2, 58), (-1, 0), (0, 1), (180, 240), (-2, 2)]:
            yield {'type': "SEASONAL", 'season_start_date': in_days(start),
                   'season_end_date': in_days(end), **common}


class LegacyParityTests(SimpleTestCase):

    def test_stock_and_notifications_match_the_legacy_behaviour(self):
        for fields in every_product_situation():
            with self.subTest(**fields):
                legacy, refactored = Product(name="Tofu", **fields), Product(name="Tofu", **fields)
                legacy_notifications, new_notifications = Mock(), Mock()

                legacy_process(legacy, Mock(), legacy_notifications)
                ProductService(Mock(), new_notifications).process_ordered_product(refactored)

                self.assertEqual(legacy.available, refactored.available, "stock left")
                self.assertEqual(legacy.lead_time, refactored.lead_time, "lead time")
                self.assertEqual(
                    sorted(str(call) for call in legacy_notifications.mock_calls),
                    sorted(str(call) for call in new_notifications.mock_calls),
                    "notifications sent",
                )
