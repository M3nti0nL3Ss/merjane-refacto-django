from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .dto.product import ProcessOrderResponse
from .services.order_service import OrderService


@csrf_exempt
@require_POST
def process_order(request, order_id):
    order = OrderService().process_order(order_id)
    return JsonResponse({'id': ProcessOrderResponse(order.get_id()).get_id()}, status=200)
