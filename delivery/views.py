from django.shortcuts import render, get_object_or_404, reverse, redirect
from restaurant.models import Order
from restaurant.models import  Restaurant, OrderItem
from menu.models import Menu, Ingredient
from delivery.models import DeliveryOrder
from django.http import JsonResponse
import json
from django.contrib.auth import authenticate, login as auth_login
import re 
from geopy.distance import geodesic
import requests
import uuid


from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse 


from .models import Notification



from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

def exclude_garcon(view_func):
    def _wrapped_view_func(request, *args, **kwargs):
        if request.user.groups.filter(name='garcon').exists():
            return render(request, 'pages/garcon.html')
        else:
            return view_func(request, *args, **kwargs)
    return _wrapped_view_func



def checkout_orders(request, restaurant_code):
    
    if request.method == 'POST':
        try:
            body = request.body.decode('utf-8')
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)

            customer_name = data.get('name')
            customer_email = data.get('email')
            customer_phone = data.get('phone')
            cep = data.get('cep')
            address = data.get('street')
            house_number = data.get('houseNumber')
            complement = data.get('complement', '')
            payment_method = data.get('paymentMethod')
            terms_accepted = data.get('termsAccepted', False)
            items = data.get('items', [])
            total_order_str = data.get('totalOrder', '0.00')
            total_payment_str = data.get('totalPayment', '0.00')
            frete = data.get('frete', 5.00)
            is_local = data.get('isLocal', False)

            observation = data.get('observation', '')
            

            required_fields = ['name', 'email', 'phone', 'street', 'houseNumber', 'paymentMethod']
            missing_fields = [field for field in required_fields if not data.get(field)]

            if missing_fields:
                return JsonResponse({'success': False, 'message': f'Missing fields: {", ".join(missing_fields)}'}, status=400)

            def clean_currency(value):
                try:
                    value = re.sub(r'[^\d,]', '', value)
                    value = value.replace(',', '.')
                    return float(value)
                except ValueError:
                    return 0.0

            total_order = clean_currency(total_order_str)
            total_payment = clean_currency(total_payment_str)
            print('FRETE', frete)
            try:
                restaurant = Restaurant.objects.get(restaurant_code=restaurant_code)
                delivery_order = DeliveryOrder.objects.create(
                    restaurant=restaurant,
                    customer_name=customer_name,
                    customer_email=customer_email,
                    customer_phone=customer_phone,
                    address=address,
                    house_number=house_number,
                    complement=complement,
                    payment_method=payment_method,
                    terms_accepted=terms_accepted,
                    total_order=total_order,
                    total_payment=total_payment,
                    cep=cep,
                    frete=int(frete),
                    observation=observation
                )

                restaurant_menu = Menu.objects.filter(restaurant=restaurant)
                order_items = items
                for item_data in items:
                        try:
                            menu_item = restaurant_menu.get(name__iexact=item_data['name'])
                            quantity = int(item_data.get('qty', 1))

                            # Adiciona o item ao relacionamento ManyToMany
                            delivery_order.items.add(menu_item)

                            # Cria ou atualiza o OrderItem
                            order_item, created = OrderItem.objects.get_or_create(
                                delivery_order=delivery_order,
                                menu_item=menu_item,
                                defaults={'quantity': quantity}
                            )
                            if not created:
                                order_item.quantity += quantity
                                order_item.save()

                        except Menu.DoesNotExist:
                            print(f"Menu item '{item_data['name']}' not found in restaurant menu.")
                        except KeyError as ke:
                            print(f"KeyError: {ke}")
                        except ValueError as ve:
                            print(f"ValueError: {ve}")

                request.session['order_items'] = []
                request.session['total_order'] = '0.00'
                request.session['total_payment'] = '0.00'


        

                return JsonResponse({'success': True, 'id': delivery_order.id})

            except Restaurant.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Restaurant not found'}, status=404)
            except Exception as e:
                print(f"Error creating Order or DeliveryOrder: {e}")
                return JsonResponse({'success': False, 'message': 'Failed to create order or delivery order'}, status=500)

        except Exception as e:
            print(f"Unexpected error: {e}")
            return JsonResponse({'success': False, 'message': 'Internal Server Error'}, status=500)

    else:
        items = request.session.get('order_items', [])
        total_order = request.session.get('total_order', '0.00')
        total_payment = request.session.get('total_payment', '0.00')
        try:
            restaurant_user = Restaurant.objects.get(restaurant_code=restaurant_code)
        except Restaurant.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Restaurant not found'}, status=404)

        context = {
            'items': items,
            'total_order': total_order,
            'total_payment': total_payment,
            'restaurant_user': restaurant_user,
          
        }

        return render(request, 'pages/checkout.html', context)

def order_pickup(request, restaurant_code):
    if request.method == 'POST':
    
        body = request.body.decode('utf-8')
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)

        customer_name = data.get('name')
        customer_email = data.get('email')  
        customer_phone = data.get('phone')    
        payment_method = data.get('paymentMethod')
        terms_accepted = data.get('termsAccepted', False)
        items = data.get('items', [])
        total_order_str = data.get('totalOrder', '0.00')
        observation = data.get('observation', '')
        
        required_fields = ['name', 'email', 'phone', 'paymentMethod']
        missing_fields = [field for field in required_fields if not data.get(field)]

        if missing_fields:
            return JsonResponse({'success': False, 'message': f'Missing fields: {", ".join(missing_fields)}'}, status=400)

        def clean_currency(value):
            try:
                value = re.sub(r'[^\d,]', '', value)
                value = value.replace(',', '.')
                return float(value)
            except ValueError:
                return 0.0

        total_order = clean_currency(total_order_str)

        
        try:
            restaurant = Restaurant.objects.get(restaurant_code=restaurant_code)
            delivery_order = DeliveryOrder.objects.create(
                restaurant=restaurant,
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
                payment_method=payment_method,
                terms_accepted=terms_accepted,
                total_order=total_order,
                observation=observation,
                total_payment=total_order,
                is_local=True
            )

            restaurant_menu = Menu.objects.filter(restaurant=restaurant)
            for item_data in items:
                try:
                    menu_item = restaurant_menu.get(name__iexact=item_data['name'])
                    quantity = int(item_data.get('qty', 1))
                    delivery_order.items.add(menu_item)
                    order_item, created = OrderItem.objects.get_or_create(
                        delivery_order=delivery_order,
                        menu_item=menu_item,
                        defaults={'quantity': quantity}
                    )
                    if not created:
                        order_item.quantity += quantity
                        order_item.save()

                except Menu.DoesNotExist:
                    print(f"Menu item '{item_data['name']}' not found in restaurant menu.")
                except KeyError as ke:
                    print(f"KeyError: {ke}")
                except ValueError as ve:
                    print(f"ValueError: {ve}")

            request.session['order_items'] = []
            request.session['total_order'] = '0.00'
            request.session['total_payment'] = '0.00'
            
            return JsonResponse({'success': True, 'id': delivery_order.id})

        except Restaurant.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Restaurant not found'}, status=404)
        except Exception as e:
            print(f"Error creating Order or DeliveryOrder: {e}")
            return JsonResponse({'success': False, 'message': 'Failed to create order or delivery order'}, status=500)

        except Exception as e:
            print(f"Unexpected error: {e}")
            return JsonResponse({'success': False, 'message': 'Internal Server Error'}, status=500)


def capture_order_data(request):
    if request.method == 'POST':
        try:
            # Tenta carregar o corpo da solicitação como JSON
            data = json.loads(request.body)
            items = data.get('items', [])
            total_order = data.get('totalOrder', '0.00')
            total_payment = data.get('totalPayment', '0.00')
            restaurant_code_str = data.get('restaurant_code')

            # Verifica se todos os campos necessários foram fornecidos
            if not restaurant_code_str:
                return JsonResponse({'error': 'Restaurant code is required'}, status=400)
            if not isinstance(items, list):
                return JsonResponse({'error': 'Items must be a list'}, status=400)
            if not isinstance(total_order, str) or not isinstance(total_payment, str):
                return JsonResponse({'error': 'Total order and payment must be strings'}, status=400)

            # Converte o código do restaurante para UUID e valida
            try:
                restaurant_code = uuid.UUID(restaurant_code_str)
            except ValueError:
                return JsonResponse({'error': 'Invalid restaurant code format'}, status=400)

            # Obtém o restaurante com base no UUID
            restaurant = Restaurant.objects.filter(restaurant_code=restaurant_code).first()
            if not restaurant:
                return JsonResponse({'error': 'Restaurant not found'}, status=404)

            # Armazena os dados na sessão
            request.session['order_items'] = items
            request.session['total_order'] = total_order
            request.session['total_payment'] = total_payment
            request.session['restaurant_uuid'] = restaurant_code_str

            # Define a URL de redirecionamento
            redirect_url = f'/delivery/checkout/{restaurant_code_str}/'


            return JsonResponse({'redirect_url': redirect_url})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)



def get_cep(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Formato de JSON inválido'}, status=400)

    cep = data.get('cep')
    if not cep:
        return JsonResponse({'success': False, 'error': 'CEP não fornecido'}, status=400)

    
    fixed_lat = -20.52275  # Latitude fixa
    fixed_lng = -54.65077  # Longitude fixa
    cost_per_km = 2        # Custo por km

    url = f'https://cep.awesomeapi.com.br/json/{cep}'
    try:
        response = requests.get(url)
        response.raise_for_status()
        address_data = response.json()

        # Verifica se lat e lng estão presentes
        lat = address_data.get('lat')
        lng = address_data.get('lng')

        if not lat or not lng:
            return JsonResponse({'success': False, 'error': 'Latitude ou longitude não encontradas para o CEP fornecido'}, status=400)

        # Calcula a distância em quilômetros e o custo
        try:
            distance_km = geodesic((fixed_lat, fixed_lng), (float(lat), float(lng))).kilometers
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Erro ao converter latitude/longitude'}, status=500)

        cost = distance_km * cost_per_km
        
        if cost <= 0:
            cost = 2.00

        # Retorna os dados do endereço, junto com a distância e o custo
        return JsonResponse({
            'success': True,
            'cep': cep,
            'address_type': address_data.get('address_type'),
            'address_name': address_data.get('address_name'),
            'address': address_data.get('address'),
            'state': address_data.get('state'),
            'district': address_data.get('district'),
            'lat': lat,
            'lng': lng,
            'city': address_data.get('city'),
            'city_ibge': address_data.get('city_ibge'),
            'ddd': address_data.get('ddd'),
            'distance_km': distance_km,
            'cost': cost
        })

    except requests.exceptions.HTTPError as http_err:
        return JsonResponse({'success': False, 'error': f'Erro HTTP: {http_err}'}, status=500)
    except requests.exceptions.RequestException as req_err:
        return JsonResponse({'success': False, 'error': f'Erro de requisição: {req_err}'}, status=500)

def sucess_page(request, order_id):
    order_delivery = get_object_or_404(DeliveryOrder, id=order_id)
    
    return render(request, 'pages/sucess.html', {'order_delivery': order_delivery})


def get_restaurant_token(user):
    restaurant = Restaurant.objects.get(user=user)  
    return restaurant


def menu_orders(request, restaurant_code):
    from menu.models import Category
    restaurant = get_object_or_404(Restaurant, restaurant_code=restaurant_code)
    menu = Menu.objects.filter(restaurant=restaurant)
    categories = Category.objects.all()  # Obter todas as categorias para os botões
    return render(request, 'pages/restaurant-card.html', {'menu': menu, 'restaurant': restaurant, 'categories': categories})
  
import logging

@exclude_garcon
def page_delivery(request):
    restaurant = get_restaurant_token(user=request.user)
    order_delivery = DeliveryOrder.objects.filter(restaurant=restaurant, status='pending')
    
    latest_orders = DeliveryOrder.objects.order_by('-order_date')[:4]

    order_items = []
    for delivery_order in order_delivery:  
        items = delivery_order.order_items.all()  
        order_items.extend(items)  

    print(f"Pedidos de entrega: {list(order_delivery)}")  # Exibe os pedidos de entrega encontrados
    print(f"Itens de pedido encontrados: {order_items}")   # Exibe os itens de pedido encontrados

    return render(request, 'pages/delivery.html', {
        'order_items': order_items,  
        'latest_order_delivery': latest_orders,  
        'restaurant': restaurant,
        'order_delivery': order_delivery
    })


logger = logging.getLogger(__name__)

def approve_order(request, order_id):
    logger.debug(f'Requisição recebida: {request.method} {request.path}')

    if request.method == 'POST':
        order = get_object_or_404(DeliveryOrder, id=order_id)
        order.status = 'approved'
        order.restaurant_accepted = True
        order.save()

        return JsonResponse({'success': True, 'message': 'Order approved'}, status=200)

    return JsonResponse({'error': 'Invalid method'}, status=405)





def order_status(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(DeliveryOrder, id=order_id)
        
        # Verifica se o pedido está aprovado
        if order.status == 'approved':
            redirect_url = reverse('delivery_approved', args=[order.id])
            full_redirect_url = request.build_absolute_uri(redirect_url)
            
            return JsonResponse({
                'status': 'approved',
                'redirect_url': full_redirect_url
            }, status=200)
        
        # Verifica se o pedido está cancelado
        elif order.status == 'canceled':
            redirect_url = reverse('delivery_canceled', args=[order.id])
            full_redirect_url = request.build_absolute_uri(redirect_url)
            
            return JsonResponse({
                'status': 'canceled',
                'redirect_url': full_redirect_url
            }, status=200)

        # Se o pedido não estiver nem aprovado nem cancelado
        return JsonResponse({'status': 'pending'}, status=200)

    return JsonResponse({'error': 'Invalid method'}, status=405)


def delivery_approved_view(request, order_id):
    order = get_object_or_404(DeliveryOrder, id=order_id)  
    restaurant = order.restaurant
    
    return render(request, 'pages/delivery_approved.html', {'order': order, 'restaurant': restaurant})

def delivery_canceled_view(request, order_id):
    order = get_object_or_404(DeliveryOrder, id=order_id) 
    restaurant = order.restaurant
    
    return render(request, 'pages/delivery_canceled.html', {'order': order, 'restaurant': restaurant})

# Configure o logger
logger = logging.getLogger(__name__)

def cancel_order(request, order_id):
    logger.info(f"Tentando cancelar o pedido com ID: {order_id}")

    # Obtém o pedido ou retorna 404 se não encontrado
    order = get_object_or_404(DeliveryOrder, id=order_id)
    logger.info(f"Pedido encontrado: {order.id} com status {order.status}")

    if order.status != 'canceled':  # Verifique se o pedido já não foi cancelado
        order.status = 'canceled'
        order.save()
        logger.info(f"Pedido {order_id} cancelado com sucesso.")
        return JsonResponse({'success': True, 'message': 'Pedido cancelado com sucesso!'}, status=200)
    else:
        logger.warning(f"Tentativa de cancelar o pedido {order_id} falhou. O pedido já está cancelado.")
        return JsonResponse({'success': False, 'message': 'Este pedido já foi cancelado.'}, status=400)




def mark_notifications_as_seen(request):
    if request.method == 'POST' and request.user.is_authenticated:
        # Marcar todas as notificações como vistas para o usuário autenticado
        Notification.objects.filter(restaurant=request.user.restaurant, seen=False).update(seen=True)
        return JsonResponse({'success': True})

    return JsonResponse({'success': False}, status=400)

    
from reportlab.lib.pagesizes import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black, white
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import mm
from reportlab.pdfgen import canvas

from reportlab.lib.pagesizes import mm
from reportlab.pdfgen import canvas
from decimal import Decimal

def create_pdf_delivery(file_path, order):
    width_mm = 82
    width = width_mm * mm
    height = 200 * mm  # Altura ajustada para caber as informações do pedido

    # Configurações de margens e layout
    margin_top = 2 * mm
    margin_bottom = 20 * mm
    margin_left = 5 * mm
    margin_right = 5 * mm
    line_height = 20  # Espaçamento entre linhas
    font_size = 12  # Tamanho da fonte ajustado
    max_line_length = 30  # Definido para garantir que não haja quebras de linha

    # Criar o PDF
    c = canvas.Canvas(file_path, pagesize=(width, height))
    c.setFont("Helvetica", font_size)

    # Adicionar logo no topo centralizado
    logo_path = 'static/images/logoimpressao.png'  # Atualize para o caminho correto da logo
    logo_width = 40 * mm
    logo_height = 40 * mm
    c.drawImage(logo_path, 
                (width - logo_width) / 2, 
                height - margin_top - logo_height, 
                width=logo_width, 
                height=logo_height, 
                mask='auto')

    # Posição inicial para o texto
    y_position = height - margin_top - logo_height - 5 * mm
    x_position = margin_left

    # Função auxiliar para truncar texto que exceda o comprimento máximo
    def truncate_text(text, max_length):
        return text if len(text) <= max_length else text[:max_length - 3] + '...'

    # Informações do pedido
    c.drawString(x_position, y_position, f"{'Retirada' if order.is_local else 'Entrega'} - Pedido # {order.id}")
    y_position -= line_height
    c.drawString(x_position, y_position, f"Cliente: {truncate_text(order.customer_name, max_line_length)}")
    y_position -= line_height

    # Exibir informações dependendo do tipo de pedido
    if order.is_local:
        c.drawString(x_position, y_position, "PEDIDO RETIRADA")
        y_position -= line_height
        c.drawString(x_position, y_position, f"Contato: {order.customer_phone}")
        y_position -= line_height
    else:
        c.drawString(x_position, y_position, f"Endereço: {truncate_text(order.address, max_line_length)}")
        y_position -= line_height
        c.drawString(x_position, y_position, f"Nº {order.house_number}")
        y_position -= line_height
        c.drawString(x_position, y_position, f"CEP: {order.cep}")
        
        if order.complement:
            y_position -= line_height
            c.drawString(x_position, y_position, f"Complemento: {truncate_text(order.complement, max_line_length)}")
        
    # Continuação das informações do pedido
    y_position -= line_height
    order_date_time = order.order_date.strftime("%d/%m/%Y %H:%M")
    c.drawString(x_position, y_position, f"Data: {order_date_time}")
    y_position -= line_height
    c.drawString(x_position, y_position, f"Vai pagar com: {order.payment_method}")
    y_position -= line_height
    c.drawString(x_position, y_position, "-" * 40)  # Separador
    y_position -= line_height

    # Itens do pedido
    for item in order.order_items.all():  # Certifique-se de acessar os itens corretamente
        if y_position < margin_bottom + line_height * 3:
            # Iniciar nova página, se necessário
            c.showPage()
            c.setFont("Helvetica", font_size)
            y_position = height - margin_top

        # Descrição do item truncada se necessário
        item_str = f"{truncate_text(item.menu_item.name, 15).ljust(15)} x{item.quantity} R$ {item.get_total_value():.2f}"
        c.drawString(x_position, y_position, item_str)
        y_position -= line_height

        # Observações especiais truncadas
        if item.special_instructions:
            c.drawString(x_position, y_position, f"Obs: {truncate_text(item.special_instructions, max_line_length)}")
            y_position -= line_height

        # Ingredientes removidos truncados
        removed_ingredients = item.removed_ingredients.all()
        if removed_ingredients.exists():
            removed_str = ', '.join([truncate_text(ingredient.name, 15) for ingredient in removed_ingredients])
            c.drawString(x_position + 10, y_position, f"Removidos: {truncate_text(removed_str, max_line_length)}")
            y_position -= line_height
            
    total_order_delivery = order.total_order + order.frete

    # Exibir o total do pedido
    y_position -= line_height
    c.drawString(x_position, y_position, "-" * 40)  # Separador
    y_position -= line_height
    if order.is_local:
        c.drawString(x_position, y_position, f"Total: R$ {total_order_delivery:.2f}")
    else:
        y_position -= line_height
        c.drawString(x_position, y_position, f"Taxa de Entrega: R$ {order.frete:.2f}")
        y_position -= line_height
        c.drawString(x_position, y_position, f"Total: R$ {total_order_delivery:.2f}")
    

    # Finalizar e salvar o PDF
    c.save()