from datetime import date, timedelta
from unittest.mock import Mock

from django.test import SimpleTestCase

from orders.entities.product import Product, ProductType
from orders.services.implementations.product_service import ProductService

TODAY = date.today()


def in_days(days):
    return TODAY + timedelta(days=days)


class ProductServiceTestCase(SimpleTestCase):

    def setUp(self):
        self.products = Mock()
        self.notifications = Mock()
        self.service = ProductService(self.products, self.notifications)

    def process(self, **fields):
        product = Product(name="Tested product", **fields)
        self.service.process_ordered_product(product)
        return product

    def assert_nothing_notified(self):
        self.notifications.send_delay_notification.assert_not_called()
        self.notifications.send_out_of_stock_notification.assert_not_called()
        self.notifications.send_expiry_notification.assert_not_called()


class NormalProductTests(ProductServiceTestCase):

    def test_sells_one_unit_when_in_stock(self):
        product = self.process(type=ProductType.NORMAL, available=15, lead_time=30)

        self.assertEqual(14, product.available)
        self.products.save.assert_called_once_with(product)
        self.assert_nothing_notified()

    def test_announces_the_lead_time_when_out_of_stock(self):
        product = self.process(type=ProductType.NORMAL, available=0, lead_time=30)

        self.assertEqual(0, product.available)
        self.products.save.assert_not_called()
        self.notifications.send_delay_notification.assert_called_once_with(30, product.name)

    def test_stays_silent_when_out_of_stock_without_lead_time(self):
        product = self.process(type=ProductType.NORMAL, available=0, lead_time=0)

        self.assertEqual(0, product.available)
        self.products.save.assert_not_called()
        self.assert_nothing_notified()


class SeasonalProductTests(ProductServiceTestCase):

    def in_season(self, **fields):
        return self.process(
            type=ProductType.SEASONAL,
            season_start_date=in_days(-2),
            season_end_date=in_days(58),
            **fields,
        )

    def test_sells_one_unit_during_the_season(self):
        product = self.in_season(available=15, lead_time=30)

        self.assertEqual(14, product.available)
        self.products.save.assert_called_once_with(product)
        self.assert_nothing_notified()

    def test_announces_the_lead_time_when_restocking_happens_before_the_season_ends(self):
        product = self.in_season(available=0, lead_time=30)

        self.assertEqual(0, product.available)
        self.products.save.assert_not_called()
        self.notifications.send_delay_notification.assert_called_once_with(30, product.name)

    def test_declares_unavailable_when_restocking_happens_after_the_season_ends(self):
        product = self.in_season(available=0, lead_time=90)

        self.assertEqual(0, product.available)
        self.products.save.assert_called_once_with(product)
        self.notifications.send_out_of_stock_notification.assert_called_once_with(product.name)

    def test_declares_unavailable_before_the_season_starts(self):
        product = self.process(
            type=ProductType.SEASONAL,
            available=15,
            lead_time=30,
            season_start_date=in_days(180),
            season_end_date=in_days(240),
        )

        self.assertEqual(15, product.available, "stock is kept for the coming season")
        self.products.save.assert_not_called()
        self.notifications.send_out_of_stock_notification.assert_called_once_with(product.name)

    def test_declares_unavailable_once_the_season_is_over(self):
        product = self.process(
            type=ProductType.SEASONAL,
            available=15,
            lead_time=30,
            season_start_date=in_days(-240),
            season_end_date=in_days(-2),
        )

        self.assertEqual(0, product.available)
        self.products.save.assert_called_once_with(product)
        self.notifications.send_out_of_stock_notification.assert_called_once_with(product.name)


class ExpirableProductTests(ProductServiceTestCase):

    def test_sells_one_unit_before_the_expiry_date(self):
        product = self.process(type=ProductType.EXPIRABLE, available=15, expiry_date=in_days(26))

        self.assertEqual(14, product.available)
        self.products.save.assert_called_once_with(product)
        self.assert_nothing_notified()

    def test_empties_the_stock_and_notifies_once_expired(self):
        product = self.process(type=ProductType.EXPIRABLE, available=90, expiry_date=in_days(-2))

        self.assertEqual(0, product.available)
        self.products.save.assert_called_once_with(product)
        self.notifications.send_expiry_notification.assert_called_once_with(product.name)

    def test_expires_on_the_expiry_date_itself(self):
        product = self.process(type=ProductType.EXPIRABLE, available=5, expiry_date=TODAY)

        self.assertEqual(0, product.available)
        self.notifications.send_expiry_notification.assert_called_once_with(product.name)

    def test_notifies_expiry_when_out_of_stock(self):
        product = self.process(type=ProductType.EXPIRABLE, available=0, expiry_date=in_days(26))

        self.assertEqual(0, product.available)
        self.notifications.send_expiry_notification.assert_called_once_with(product.name)


class UnknownProductTypeTests(ProductServiceTestCase):

    def test_leaves_the_product_untouched(self):
        product = self.process(type="FLASH_SALE", available=15)

        self.assertEqual(15, product.available)
        self.products.save.assert_not_called()
        self.assert_nothing_notified()
