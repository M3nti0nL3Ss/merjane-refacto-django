from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from orders.entities.order import Order
from orders.entities.product import Product

TODAY = date.today()


def in_days(days):
    return TODAY + timedelta(days=days)


class ProcessOrderViewTestCase(TestCase):

    def setUp(self):
        patcher = patch('orders.services.implementations.product_service.NotificationService')
        self.notifications = patcher.start().return_value
        self.addCleanup(patcher.stop)

    def post_order(self, products):
        order = Order.objects.create()
        order.products.set(Product.objects.bulk_create(products))
        return order, self.client.post(reverse('process_order', args=[order.id]))

    def test_processes_every_product_of_the_order(self):
        order, response = self.post_order([
            Product(available=15, lead_time=30, type="NORMAL", name="USB Cable"),
            Product(available=10, lead_time=0, type="NORMAL", name="USB Dongle"),
            Product(available=15, lead_time=30, type="EXPIRABLE", name="Butter",
                    expiry_date=in_days(26)),
            Product(available=90, lead_time=6, type="EXPIRABLE", name="Milk",
                    expiry_date=in_days(-2)),
            Product(available=15, lead_time=30, type="SEASONAL", name="Watermelon",
                    season_start_date=in_days(-2), season_end_date=in_days(58)),
            Product(available=15, lead_time=30, type="SEASONAL", name="Grapes",
                    season_start_date=in_days(180), season_end_date=in_days(240)),
        ])

        self.assertEqual(200, response.status_code)
        self.assertEqual({'id': order.id}, response.json())

        stock = {p.name: p.available for p in Product.objects.all()}
        self.assertEqual(
            {'USB Cable': 14, 'USB Dongle': 9, 'Butter': 14, 'Milk': 0,
             'Watermelon': 14, 'Grapes': 15},
            stock,
        )
        self.notifications.send_expiry_notification.assert_called_once_with("Milk")
        self.notifications.send_out_of_stock_notification.assert_called_once_with("Grapes")
        self.notifications.send_delay_notification.assert_not_called()

    def test_notifies_the_delay_of_an_out_of_stock_product(self):
        self.post_order([
            Product(available=0, lead_time=15, type="NORMAL", name="RJ45 Cable"),
        ])

        self.assertEqual(0, Product.objects.get(name="RJ45 Cable").available)
        self.notifications.send_delay_notification.assert_called_once_with(15, "RJ45 Cable")

    def test_rejects_anything_but_post(self):
        order, _ = self.post_order([])

        response = self.client.get(reverse('process_order', args=[order.id]))

        self.assertEqual(405, response.status_code)
