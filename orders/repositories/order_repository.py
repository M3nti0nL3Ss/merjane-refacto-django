from ..entities.order import Order


class OrderRepository:
    def find_by_id(self, order_id):
        return Order.objects.prefetch_related('products').get(pk=order_id)
