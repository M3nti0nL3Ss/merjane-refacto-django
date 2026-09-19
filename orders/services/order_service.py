from ..repositories.order_repository import OrderRepository
from .product_service import ProductService


class OrderService:

    def __init__(self, order_repository=None, product_service=None):
        self._orders = order_repository or OrderRepository()
        self._product_service = product_service or ProductService()

    def process_order(self, order_id):
        order = self._orders.find_by_id(order_id)
        for product in order.get_items():
            self._product_service.process_ordered_product(product)
        return order
