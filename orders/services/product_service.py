from datetime import date

from ..entities.product import ProductType
from ..repositories.product_repository import ProductRepository
from .notification_service import NotificationService


class ProductService:

    def __init__(self, product_repository=None, notification_service=None):
        self._products = product_repository or ProductRepository()
        self._notifications = notification_service or NotificationService()

    def process_ordered_product(self, product):
        handler = {
            ProductType.NORMAL: self._process_normal,
            ProductType.SEASONAL: self._process_seasonal,
            ProductType.EXPIRABLE: self._process_expirable,
        }.get(product.type)

        if handler:
            handler(product, date.today())

    def _process_normal(self, product, today):
        if product.is_in_stock():
            self._sell_one_unit(product)
        elif product.lead_time > 0:
            self._notifications.send_delay_notification(product.lead_time, product.name)

    def _process_seasonal(self, product, today):
        if product.is_in_season(today) and product.is_in_stock():
            self._sell_one_unit(product)
        elif product.restock_date(today) > product.season_end_date:
            self._mark_unavailable(product)
            self._notifications.send_out_of_stock_notification(product.name)
        elif today < product.season_start_date:
            self._notifications.send_out_of_stock_notification(product.name)
        else:
            self._notifications.send_delay_notification(product.lead_time, product.name)

    def _process_expirable(self, product, today):
        if product.is_in_stock() and not product.is_expired(today):
            self._sell_one_unit(product)
        else:
            self._mark_unavailable(product)
            self._notifications.send_expiry_notification(product.name)

    def _sell_one_unit(self, product):
        product.available -= 1
        self._products.save(product)

    def _mark_unavailable(self, product):
        product.available = 0
        self._products.save(product)
