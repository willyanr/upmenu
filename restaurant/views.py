
from .models import Table
from restaurant.models import Order, OrderItem
from delivery.models import DeliveryOrder
from menu.models import Menu, Ingredient
from core.models import Subscription
from restaurant.models import Table, Restaurant, Waiter
from menu.models import Ingredient, Menu
from delivery.models import DeliveryOrder
from django.contrib import messages

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login as auth_login
from django.db import transaction
from django.contrib.auth.decorators import login_required
from delivery.views import get_cep
import requests
from django.contrib.auth.models import User, Group

from django.db import IntegrityError
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from core.views import subscription_required, exclude_garcon
from django.http import JsonResponse
import json
import logging
from django.contrib.auth.decorators import login_required
import threading

import logging

@subscription_required
@exclude_garcon
@login_required

def tables(request):
    user = request.user  # Obtenha o usuário atualmente autenticado
    user_restaurant = Restaurant.objects.get(user=user)
    user_table = Table.objects.filter(user=user)
    user_orders = Order.objects.filter(user=user)
    
    tables = Table.objects.filter(restaurant=user_restaurant).prefetch_related('orders__order_items').filter(orders__is_closed=False).distinct()
    orders = Order.objects.filter(table__restaurant=user_restaurant, is_closed=False)
    orders_delivery = DeliveryOrder.objects.filter(restaurant=user_restaurant)

    total_value = sum(order.get_total_value() for order in orders)

    total_orders = orders.count()
    total_tables = user_table.count()
    table_data = []
    
    order_canceled = orders_delivery.filter(status='canceled').count()


    for table in tables:
        orders_data = []
        total_table_value = 0
        
        for order in table.orders.filter(is_closed=False):
            order_items_data = []
            for item in order.order_items.all():  # Use o related_name correto
                order_items_data.append({
                    'menu_item': item.menu_item.name,
                    'quantity': item.quantity,
                    'final_ingredients': ', '.join(item.get_final_ingredients()),
                    'special_instructions': item.special_instructions,
                    'total_value': item.get_total_value(),
                })
            order_total_value = order.get_total_value()
            total_table_value += order_total_value
            
            orders_data.append({
                'order_id': order.id,
                'order_date': order.order_date,
                'waiter': order.waiter.name if order.waiter else 'Unknown Waiter',
                'order_items': order_items_data,
                'total_order_value': order_total_value,
            })

        table_data.append({
            'table_number': table.table_number,
            'orders': orders_data,
            'total_table_value': total_table_value,
            'is_delivery': False,
        })

    context = {
        'tables': table_data,
        'total_orders': total_orders,
        'total_tables': total_tables,
        'orders': orders,
        'orders_delivery': orders_delivery.count(),
        'total_value': total_value,  
        'order_canceled': order_canceled,
    }

    return render(request, 'pages/tables.html', context)



@login_required
def menu_user(request):
    user = request.user  
    print(f'Usuário autenticado: {user.username}')  

    try:
        # Busca o garçom usando o usuário autenticado
        waiter = Waiter.objects.get(user=user) 
        waiter_id = waiter.id  
        print(f'Garçom encontrado: {waiter.name}, ID: {waiter_id}')

        # Obtém o restaurante associado ao garçom
        waiter_restaurant = waiter.restaurant 
        print(f'Restaurante encontrado: {waiter_restaurant.id}')
        
        # Busca os itens do menu e mesas do restaurante
        menu_items = Menu.objects.filter(restaurant=waiter_restaurant)
        tables = Table.objects.filter(restaurant=waiter_restaurant,is_active=True)
        orders = Order.objects.filter(waiter_id=waiter.id)
        order_count = orders.count()
        
        # Coleta ingredientes, removendo duplicatas
        ingredients = list(set(ingredient for item in menu_items for ingredient in item.ingredients.all()))
        
        print(f'Itens do menu: {menu_items}')
        print(f'Ingredientes: {ingredients}')

    except Waiter.DoesNotExist:
        # Se o usuário não for um garçom, obtém o menu e as mesas do usuário
        menu_items = Menu.objects.filter(user=user)
        tables = Table.objects.filter(user=user, is_active=True)
        ingredients = list(set(ingredient for item in menu_items for ingredient in item.ingredients.all()))
        
        print('Usuário não é um garçom. Obtendo menu e mesas do usuário principal.')

    return render(request, 'pages/menu-user.html', {
        'waiter': waiter if 'waiter' in locals() else None,  # Passa o objeto waiter ou None
        'menu': menu_items,  
        'tables': tables,
        'ingredients': ingredients,
        'orders': order_count if 'waiter' in locals() else None, 
    })




from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json




logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
@login_required


@login_required
def submit_order(request):
    from core.views import create_pdf

    if request.method == 'POST':
        try:
            logging.debug("Recebendo o pedido do cliente.")
            data = json.loads(request.body.decode('utf-8'))
            item_ids = data.get('items', [])
            table_id = data.get('tableId')

            if table_id is None:
                logging.error("ID da mesa não fornecido.")
                return JsonResponse({'error': 'Table ID is missing'}, status=400)

            # Verificar se a mesa existe
            try:
                table = Table.objects.get(id=table_id)
                logging.debug(f"Mesa encontrada: {table.table_number}")
            except Table.DoesNotExist:
                logging.error("Mesa inválida selecionada.")
                return JsonResponse({'error': 'Invalid table selected'}, status=400)

            # Obter os itens do menu
            item_ids_list = [item['id'] for item in item_ids]
            menu_items = Menu.objects.filter(id__in=item_ids_list)

            if not menu_items.exists():
                logging.error("Nenhum item encontrado para o pedido.")
                return JsonResponse({'error': 'Items not found'}, status=400)

            # Identificar o garçom e o restaurante
            try:
                waiter = Waiter.objects.get(user=request.user)
                restaurant = waiter.restaurant
                restaurant_user = restaurant.user  # Aqui pegamos o usuário do restaurante
                logging.debug(f"Garçom encontrado: {waiter.name}, Restaurante: {restaurant.name}, Dono: {restaurant_user.username}")
            except Waiter.DoesNotExist:
                logging.error("Usuário não associado a um garçom.")
                return JsonResponse({'error': 'User is not a waiter'}, status=403)

            # Criar o pedido associado ao dono do restaurante (restaurant_user)
            order = Order.objects.create(
                table=table, 
                is_closed=False, 
                payment_method='pix',  # Supondo que o método seja 'pix'
                user=restaurant_user,  # Dono ou responsável pelo restaurante
                waiter=waiter,  # Garçom que atendeu
                order_print=False,
                restaurant=restaurant  # Restaurante associado ao garçom
            )
            logging.debug(f"Pedido criado com sucesso: {order.id}")
            
            # Adicionar os itens ao pedido
            for item_data in item_ids:
                item_id = item_data.get('id')
                quantity = item_data.get('quantity', 1)  # Quantidade padrão é 1
                removed_ingredients = item_data.get('removed_ingredients', [])
                observation = item_data.get('observation', '')

                try:
                    item = Menu.objects.get(id=item_id)
                except Menu.DoesNotExist:
                    logging.error(f"Item do menu com id {item_id} não encontrado.")
                    continue  # Ignorar este item e continuar

                order_item = OrderItem.objects.create(
                    order=order,
                    menu_item=item,
                    quantity=quantity,
                    special_instructions=observation,
                )

                # Remover ingredientes se necessário
                for ingredient_id in removed_ingredients:
                    try:
                        ingredient = Ingredient.objects.get(id=ingredient_id)
                        order_item.removed_ingredients.add(ingredient)
                    except Ingredient.DoesNotExist:
                        logging.error(f"Ingrediente com id {ingredient_id} não encontrado.")

            total_value = order.get_total_value()
            logging.debug(f"Total do pedido calculado: {total_value}")

            # Gerar o PDF do pedido
            file_path = 'print_order.pdf'
            create_pdf(file_path, order)  
            
            return JsonResponse({'success': True, 'total_value': total_value, 'pdf_path': file_path, 'order_id': order.id})

        except json.JSONDecodeError:
            logging.error("Erro ao decodificar o JSON do pedido.")
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logging.error(f"Erro inesperado: {str(e)}")
            return JsonResponse({'error': 'An unexpected error occurred'}, status=500)


@login_required
def close_order(request, order_id):
    if request.method == 'POST':
        try:
            order = Order.objects.get(id=order_id)
            print(f"Pedido encontrado: {order}")

            data = json.loads(request.body)
            payment_method = data.get('payment_method', 'pix')
            print(f"Método de pagamento recebido: {payment_method}")

            order.payment_method = payment_method
            order.is_closed = True
            print(f"Status antes de salvar: is_closed={order.is_closed}")
            order.save()
            print(f"Pedido {order_id} atualizado e fechado com sucesso")

            return JsonResponse({'success': True})
        except Order.DoesNotExist:
            print(f"Pedido com ID {order_id} não encontrado")
            return JsonResponse({'error': 'Order not found'}, status=404)
        except json.JSONDecodeError:
            print("Erro ao decodificar JSON da requisição")
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)
        except Exception as e:
            print(f"Erro ao fechar o pedido: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    
    print(f"Método de requisição inválido: {request.method}")
    return JsonResponse({'error': 'Invalid request method'}, status=400)

@exclude_garcon  
@login_required
def manage_restaurant(request):
    user = request.user
    restaurant = Restaurant.objects.get(user=user)
    tables = Table.objects.filter(user=user)
    waiters = Waiter.objects.filter(restaurant_id=restaurant)
    
    plan = None
    has_plan = True
    
    try:
        plan = Subscription.objects.get(user=user)
    except Subscription.DoesNotExist:
        has_plan = False  
        
        
    tables_total = tables.count()

    if request.method == 'POST':
        if 'update_restaurant' in request.POST:
            restaurant.name = request.POST.get('name')
            restaurant.address = request.POST.get('address')
            restaurant.cep = request.POST.get('cep')
            restaurant.phone_number = request.POST.get('phone_number')
            restaurant.delivery_is_active = 'delivery_is_active' in request.POST
            restaurant.description = request.POST.get('description')
            restaurant.save()
            messages.success(request, 'Restaurante atualizado com sucesso.')  # Mensagem de sucesso
            return redirect('config')  # Redireciona após atualização

        elif 'update_tax' in request.POST:
            delivery_rate_per_km = request.POST.get('delivery_rate_per_km')
            if delivery_rate_per_km:
                try:
                    restaurant.delivery_rate_per_km = float(delivery_rate_per_km)
                    restaurant.save()
                    messages.success(request, 'Taxa de entrega atualizada com sucesso.')  # Mensagem de sucesso
                    return redirect('config')  # Redireciona após atualização
                except ValueError:
                    messages.error(request, 'Taxa de entrega inválida.')  # Mensagem de erro
            
        elif 'add_table' in request.POST:
            table_number = request.POST.get('table_number')  # Retorna como string
            if table_number:  # Verifica se o número da mesa foi enviado
                try:
                    table_number = int(table_number)
                    print('Número da mesa:', table_number)
                    
                    # Tenta criar a mesa
                    Table.objects.create(user=user, table_number=table_number, restaurant=restaurant)

                    print('Mesa foi adicionada com sucesso')
                    
                    messages.success(request, 'Mesa adicionada com sucesso.')  # Mensagem de sucesso
                    return redirect('config')  # Redireciona após adicionar mesa
                except ValueError:
                    # Captura erro de conversão para número
                    messages.error(request, 'Número da mesa inválido.')  # Mensagem de erro
                except IntegrityError:
                    # Captura erro de chave duplicada
                    messages.error(request, 'Número de mesa já existente.')  # Mensagem de erro
            else:
                messages.error(request, 'Por favor, insira um número de mesa.')  # Mensagem de erro se o número for vazio


        elif 'create_waiter' in request.POST:
            waiter_name = request.POST.get('waiter_name')
            waiter_username = request.POST.get('waiter_username')
            waiter_password = request.POST.get('waiter_password')

            if Waiter.objects.filter(name=waiter_name).exists():
                messages.error(request, 'Já existe um garçom com este nome.')  # Mensagem de erro
            else:
                try:
                    with transaction.atomic():
                        # Cria o usuário
                        waiter_user = User.objects.create_user(username=waiter_username, password=waiter_password)
                        waiter = Waiter.objects.create(user=waiter_user, name=waiter_name, restaurant=restaurant)

                        # (Opcional) Adiciona o garçom a um grupo, se necessário
                        group, created = Group.objects.get_or_create(name='Garçons')
                        waiter_user.groups.add(group)

                        messages.success(request, 'Garçom criado com sucesso.')  # Mensagem de sucesso
                        return redirect('config')  # Redireciona após criar garçom
                except IntegrityError:
                    messages.error(request, 'Erro ao criar o garçom. Tente novamente.')  # Mensagem de erro

    return render(request, 'pages/manage_restaurant.html', {
        'restaurant': restaurant,
        'tables': tables,
        'waiters': waiters,
        'has_plan': has_plan,
        'plan': plan,
        'tables_total': tables_total,
    })
  
def get_address_restaurant(cep):
    cep_restaurant = cep
    
    if not cep_restaurant:
        return JsonResponse({'success': False, 'error': 'CEP não fornecido'}, status=400)

    url = f'https://cep.awesomeapi.com.br/json/{cep}'
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        address_data = response.json()
        address = address_data.get('address')
        if not address:
            return JsonResponse({'success': False, 'error': 'Latitude ou longitude não encontradas para o CEP fornecido'}, status=400)
        
        return JsonResponse({
            'success': True,
            'cep': cep,
            'address_type': address_data.get('address_type'),
            'address_name': address_data.get('address_name'),
            'address': address_data.get('address'),
            'state': address_data.get('state'),
            'district': address_data.get('district'),
            'city': address_data.get('city'),
            'city_ibge': address_data.get('city_ibge'),
            'ddd': address_data.get('ddd'),

        })

    except requests.exceptions.HTTPError as http_err:
        return JsonResponse({'success': False, 'error': f'Erro HTTP: {http_err}'}, status=500)
    except requests.exceptions.RequestException as req_err:
        return JsonResponse({'success': False, 'error': f'Erro de requisição: {req_err}'}, status=500)
   
@exclude_garcon   
@login_required
def order_plan(request):
    user = request.user
    restaurant = Restaurant.objects.get(user=user)
    clean_cep = restaurant.cep.replace('-', '')
    print(clean_cep)
    
    # Chama a função get_address_restaurant e obtém o JsonResponse
    json_response = get_address_restaurant(clean_cep)
    
    # Acessa o conteúdo da resposta como um dicionário
    address_info = json_response.content.decode('utf-8')
    address_info = json.loads(address_info)  # Converte a string JSON em um dicionário
    
    print(address_info)  # Verifique o conteúdo da resposta

    if not address_info.get('success', False):
        return render(request, 'pages/order_plan.html', {
            'restaurant': restaurant,
            'user': user,
            'error': address_info.get('error', 'Unknown error')
        })

    restaurant.city = address_info['city']
    restaurant.address = address_info['address']
    restaurant.save()

    return render(request, 'pages/order_plan.html', {
        'restaurant': restaurant,
        'user': user,
        'address': address_info['address'],
        'state': address_info['state'],
        'district': address_info['district'],
        'city': address_info['city'],
        'distance_km': address_info.get('distance_km', 'N/A'),
        'cost': address_info.get('cost', 'N/A')
    })


