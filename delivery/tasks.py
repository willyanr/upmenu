from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from delivery.models import DeliveryOrder



@shared_task
def check_pending_orders():
    # Verifica pedidos no banco de dados que não foram aceitos
    pending_orders = DeliveryOrder.objects.filter(status='pending')

    if pending_orders.exists():
        for order in pending_orders:
            restaurant_code = order.restaurant.restaurant_code

            # Se o pedido é local, cria order_data com campos específicos
            if order.is_local:
                order_data = {
                    'id': order.id,
                    'customer_name': order.customer_name,
                    'customer_phone': order.customer_phone,
                    'payment_method': order.payment_method,
                    'total_order': f'R$ {order.total_order:.2f}',  # Formatando como reais
                    'observation': order.observation,
                    'pickup': True

                }
                # Log para pedidos locais, se necessário
                print(f"Pedido local {order.id} processado com dados específicos.")
            else:
                # Para pedidos que não são locais
                order_data = {
                    'id': order.id,
                    'customer_name': order.customer_name,
                    'customer_phone': order.customer_phone,
                    'address': order.address,
                    'house_number': order.house_number,
                    'complement': order.complement,
                    'cep': order.cep,
                    'total_order': f'R$ {order.total_order:.2f}',  # Formatando como reais
                    'total_payment': f'R$ {order.total_payment:.2f}' if order.total_order is not None else 'R$ 0.00', 
                    'items': [
                        {
                            'name': item.menu_item.name,
                            'quantity': item.quantity
                        } for item in order.order_items.all()  # Obtendo itens e suas quantidades
                    ],
                    'payment_method': order.payment_method,
                    'order_date': order.order_date.isoformat(),  # Manter a string ISO para uso posterior
                }

            # Envia pedido para o canal WebSocket correspondente
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'orders_{restaurant_code}',
                {
                    'type': 'new_order',
                    'message': 'Novo pedido via',
                    'order': order_data  # Dados do pedido enviados ao WebSocket
                }
            )

           

@shared_task
def check_pending_orders_table():
    from restaurant.models import Order
    pending_print_orders = Order.objects.filter(order_print=False)
    
    
   
    if pending_print_orders.exists():
        for order in pending_print_orders:
            restaurant_code = order.restaurant.restaurant_code
            
            table_number = order.table.table_number
            waiter = order.waiter.name
            
            
            
            
            order_data = {
                'id': order.id,
                'table': table_number,
                'order_date': order.order_date.isoformat(),
                'waiter': waiter,
                'payment_method': order.payment_method,
                'observation': order.observation,
               
      
            }


            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'orders_{restaurant_code}',
                {
                    'type': 'new_order_table',
                    'message': f'Novo Pedido Mesa: {table_number}',
                    'order': order_data  
                }
                
        )