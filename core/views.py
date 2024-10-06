from django.shortcuts import render
from .models import Subscription
from restaurant.models import Restaurant
from menu.models import Menu

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
import logging



from .forms import MenuForm, IngredientForm, TableForm, RestaurantImageForm, UserForm, RestaurantForm
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login as auth_login
from django.contrib import messages

from django.contrib.auth.decorators import login_required
import os 

from delivery.views import create_pdf_delivery

import mercadopago
from django.conf import settings
from functools import wraps

from django.core.mail import send_mail
from django.utils.crypto import get_random_string


from django.http import FileResponse

import os
import json
import logging
from django.http import JsonResponse
from restaurant.models import Order

from reportlab.pdfgen import canvas


from reportlab.lib.units import mm








def create_pdf(file_path, order):
    # Definir a largura do papel como 80mm (recibo padrão)
    width_mm = 80
    width = width_mm * mm
    height = 200 * mm  # Altura reduzida para economizar papel

    # Configurações de margens e layout
    margin_top = 2 * mm
    margin_bottom = 20 * mm  # Aumentado para adicionar espaço
    margin_left = 5 * mm
    margin_right = 5 * mm
    line_height = 20  # Espaçamento entre as linhas
    font_size = 12  # Tamanho da fonte ajustado para caber mais informações

    # Criar o PDF
    c = canvas.Canvas(file_path, pagesize=(width, height))
    c.setFont("Helvetica", font_size)

    # Adicionar a logo no meio do PDF
    logo_path = 'static/images/logoimpressao.png'  # Substitua pelo caminho da sua logo
    logo_width = 40 * mm  # Largura da logo ajustada
    logo_height = 40 * mm  # Altura da logo ajustada
    c.drawImage(logo_path, (width - logo_width) / 2, height - margin_top - logo_height, width=logo_width, height=logo_height, mask='auto')

    # Posição inicial abaixo da logo
    y_position = height - margin_top - logo_height - 5 * mm
    x_position = margin_left

    # Cabeçalho do pedido
    c.drawString(x_position, y_position, f"Pedido #{order.id}")
    y_position -= line_height
    c.drawString(x_position, y_position, f"Mesa: {order.table.table_number}")
    y_position -= line_height
    c.drawString(x_position, y_position, f"Garçon: {order.waiter.name if order.waiter else 'N/A'}")
    y_position -= line_height

    order_date_time = order.order_date.strftime("%d/%m/%Y %H:%M")
    c.drawString(x_position, y_position, f"Data: {order_date_time}")
    y_position -= line_height
    c.drawString(x_position, y_position, "-" * 40)  # Separador
    y_position -= line_height

    # Itens do pedido
    for item in order.order_items.all():
        if y_position < margin_bottom + line_height * 3:
            # Começa uma nova página se necessário
            c.showPage()
            c.setFont("Helvetica", font_size)
            y_position = height - margin_top

        # Descrição do item
        item_str = f"{item.menu_item.name[:15].ljust(15)} x{item.quantity} R$ {item.get_total_value():.2f}"
        c.drawString(x_position, y_position, item_str)
        y_position -= line_height

        # Observações
        if item.special_instructions:
            c.drawString(x_position, y_position, f"Obs: {item.special_instructions}")
            y_position -= line_height

        # Ingredientes removidos
        removed_ingredients = item.removed_ingredients.all()
        if removed_ingredients.exists():
            c.drawString(x_position + 10, y_position, "Removidos:")
            y_position -= line_height
            for ingredient in removed_ingredients:
                c.drawString(x_position + 20, y_position, f"- {ingredient.name}")
                y_position -= line_height

    c.drawString(x_position, y_position, "-" * 40)
    y_position -= line_height

    # Total do pedido
    c.drawString(x_position, y_position, f"Total: R$ {order.get_total_value():.2f}")
    y_position -= 10 * mm  # Adiciona uma margem abaixo do total

    # Finalizar o PDF
    c.save()

def serve_pdf(request, order_id, order_type):
    from delivery.models import DeliveryOrder

    import os
    from django.http import FileResponse, HttpResponseNotFound, HttpResponseServerError
    
    try:
        if order_type == 'delivery':
            # Busca o pedido na tabela de Delivery
            order_delivery = DeliveryOrder.objects.get(id=order_id)
            print('PEDIDO DELIVERY NOVO')

            file_path = os.path.join('static', 'pdf', 'print_order_delivery.pdf')
            create_pdf_delivery(file_path, order_delivery)
        
        elif order_type == 'table':
            # Busca o pedido na tabela de Mesas
            order_table = Order.objects.get(id=order_id)
            print('PEDIDO MESA')

            file_path = os.path.join('static', 'pdf', 'print_order_table.pdf')
            create_pdf(file_path, order_table)
            
            # Marca o pedido como impresso
            order_table.order_print = True
            order_table.save()
        
        else:
            print("Tipo de pedido inválido.")
            return HttpResponseNotFound("Tipo de pedido inválido.")

        # Retorna o arquivo PDF gerado
        response = FileResponse(open(file_path, 'rb'), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(file_path)}"'  
        return response
    
    except DeliveryOrder.DoesNotExist:
        print(f"Pedido de Delivery com ID {order_id} não foi encontrado.")
        return HttpResponseNotFound(f"Pedido de Delivery com ID {order_id} não foi encontrado.")
    
    except Order.DoesNotExist:
        print(f"Pedido de Mesa com ID {order_id} não foi encontrado.")
        return HttpResponseNotFound(f"Pedido de Mesa com ID {order_id} não foi encontrado.")
    
    except Exception as e:
        print(f"Erro ao gerar o PDF: {e}")
        return HttpResponseServerError("Erro ao gerar o PDF.")


    
def exclude_garcon(view_func):
    def _wrapped_view_func(request, *args, **kwargs):
        if request.user.groups.filter(name='Garçons').exists():
            return render(request, 'pages/garcon.html')
        else:
            return view_func(request, *args, **kwargs)
    return _wrapped_view_func


def subscription_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.groups.filter(name='Garçons').exists():
                return redirect('menu_user')

            try:
                subscription = request.user.subscription
                if subscription.status == 'active':
                    return view_func(request, *args, **kwargs)
                else:
  
                    messages.error(request, 'Sua assinatura não está ativa. Por favor, renove sua assinatura.')
                    return redirect('order_plan')
            except Subscription.DoesNotExist:
             
                messages.error(request, 'Você não tem uma assinatura. Por favor, faça a assinatura para acessar esta página.')
                return redirect('order_plan')
        else:

            return redirect('login')  
    return _wrapped_view



    



def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            print(f"Usuário autenticado: {user.username}")

            if user.groups.filter(name='garcon').exists():
                print("Redirecionando para o menu_user")
                return redirect('menu_user')
            else:
                print("Redirecionando para o menu")
                return redirect('dashboard')
        else:
            messages.error(request, 'Usuário ou senha incorretos.')
            print("Formulário inválido")
    else:
        form = AuthenticationForm()
    
    return render(request, 'pages/login.html', {'form': form})












@subscription_required
@login_required
def dashboard_user(request):
    from delivery.models import DeliveryOrder

    
    user = request.user  
    restaurant_user = Restaurant.objects.get(user=user)

    orders = Order.objects.filter(user=user)
    order_delivery = DeliveryOrder.objects.filter(restaurant=restaurant_user)
    menu = Menu.objects.filter(user=user)
    
    payment_method_counts = {'pix': 0, 'dinheiro': 0, 'cartao': 0}
    total_value = 0
    total_orders_delivery = 0

    for order in orders:
        total_value += sum(item.get_total_value() for item in order.order_items.all())
        if order.payment_method in payment_method_counts:
            payment_method_counts[order.payment_method] += 1

    for delivery_order in order_delivery:
        total_orders_delivery += delivery_order.total_payment

    total_orders_value = total_value + sum(order_delivery.values_list('total_payment', flat=True))
    total_orders_value_formatted = total_orders_value

    total_orders = orders.count()
    total_menu = menu.count()
    ticket_medio = 0
    if total_orders > 0:
        ticket_medio = total_value / total_orders

    total_value_formatted = total_value
    ticket_medio_formatted = "{:.2f}".format(ticket_medio).replace('.', ',')

    payment_method_percentages = {}
    for method, count in payment_method_counts.items():
        if total_orders > 0:
            percentage = (count / total_orders) * 100
            payment_method_percentages[method] = "{:.2f}".format(percentage).replace('.', ',')

    total_global = total_orders_value + total_value
    order_total_delivery = order_delivery.count()
    
    
    return render(request, 'pages/dashboard.html', {
        'total_value': total_value_formatted,
        'total_orders': total_orders,
        'total_menu': total_menu,
        'ticket_medio': ticket_medio_formatted,
        'payment_method_percentages': payment_method_percentages,
        'total_orders_delivery': total_orders_delivery,
        'total_orders_value': total_orders_value_formatted,
        'total_global': total_global,
        'order_total_delivery': order_total_delivery
    })



def profile(request):
    return render(request, 'pages/profile.html')


@login_required
def create_ingredient(request):
    if request.method == 'POST':
        form = IngredientForm(request.POST)
        if form.is_valid():
            ingredient = form.save(commit=False)
            ingredient.user = request.user
            ingredient.save()
            return redirect('menu')  # Redirecionar para a página inicial ou onde você desejar
    else:
        form = IngredientForm()

    return render(request, 'create-ingredient.html', {'form': form})



@login_required
def create_table(request):
    if request.method == 'POST':
        form = TableForm(request.POST)
        if form.is_valid():
            table = form.save(commit=False)
            table.user = request.user
            table.save()
            return redirect('menu')  # Redirecionar para a página inicial ou onde você desejar
    else:
        form = TableForm()

    return render(request, 'create-table.html', {'form': form})


  
@login_required
def edit_image(request):
    restaurant = request.user.restaurant
    if request.method == 'POST':
        form = RestaurantImageForm(request.POST, request.FILES, instance=restaurant)
        if form.is_valid():
            form.save()
            return redirect('config')  # Redirecionar para a página de configuração após o sucesso
    else:
        form = RestaurantImageForm(instance=restaurant)
    
    return render(request, 'edit_image.html', {
        'form': form,
        'restaurant': restaurant  # Passa o objeto do restaurante para o template
    })
    
    
def register(request):
    if request.method == 'POST':
        user_form = UserForm(request.POST)
        restaurant_form = RestaurantForm(request.POST, request.FILES)
        
        if user_form.is_valid() and restaurant_form.is_valid():
            user = user_form.save(commit=False)
            user.set_password(user_form.cleaned_data['password'])
            user.save()

            # Associa o usuário ao formulário do restaurante
            restaurant = restaurant_form.save(commit=False)
            restaurant.user = user
            restaurant.save()

            # Gerar e salvar o código de verificação
            verification_code = get_random_string(length=4, allowed_chars='1234567890')
            restaurant.verification_code = verification_code
            restaurant.save()

            # Enviar o código de verificação por e-mail
            send_mail(
                'Código de verificação',
                f'Seu código de verificação é {verification_code}.',
                'upMenu <noreply@upmenu.online>',
                [user.email],
                fail_silently=False,
            )

            auth_login(request, user)
            messages.success(request, 'Cadastro realizado com sucesso! Verifique seu e-mail para o código de verificação.')
            return redirect('verify_email')
        else:
            messages.error(request, 'Houve um problema com o cadastro. Por favor, verifique os dados.')

            if user_form.errors:
                for field, errors in user_form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field.capitalize()}: {error}')

            if restaurant_form.errors:
                for field, errors in restaurant_form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field.capitalize()}: {error}')
    else:
        user_form = UserForm()
        restaurant_form = RestaurantForm()

    return render(request, 'pages/register.html', {
        'user_form': user_form,
        'restaurant_form': restaurant_form,
    })


logger = logging.getLogger(__name__)

def create_subscription(request, plan_name):
    if plan_name not in ['basic', 'premium']:
        return JsonResponse({'error': 'Plano inválido'}, status=400)

    sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
    price = 49.90 if plan_name == 'basic' else 69.90

    preference_data = {
        "items": [
            {
                "title": "Assinatura " + plan_name.capitalize(),
                "quantity": 1,
                "currency_id": "BRL",
                "unit_price": price
            }
        ],
        "back_urls": {
            "success": "https://upmenu.online/success-order",
            "failure": "https://upmenu.online/failure",
            "pending": "https://upmenu.online/faturas/"
        },
        "auto_return": "approved",
    }

    preference_response = sdk.preference().create(preference_data)
    
    # Log a resposta completa para depuração
    logger.info("Preference Response: %s", preference_response)

    preference = preference_response.get("response", {})
    
    if not preference:
        return JsonResponse({'error': 'Erro ao criar a preferência'}, status=500)

    preference_id = preference.get('id')
    if not preference_id:
        return JsonResponse({'error': 'ID da preferência não encontrado na resposta'}, status=500)

    Subscription.objects.create(
        user=request.user,
        plan_name=plan_name,
        status='pending'
    )

    return JsonResponse({'redirectUrl': preference['init_point']})


@csrf_exempt
def mercado_pago_webhook(request):
    if request.method == 'POST':
        try:
            notification_data = json.loads(request.body)
            
            logger.info("Notificação recebida: %s", notification_data)
            
            if notification_data.get('type') == 'preapproval':
                data = notification_data.get('data', {})
                subscription_id = data.get('id')
                status = data.get('status')

                if subscription_id is None:
                    logger.error("ID da assinatura não encontrado na notificação.")
                    return JsonResponse({'error': 'ID da assinatura não encontrado'}, status=400)

                try:
                    subscription = Subscription.objects.get(subscription_id=subscription_id)
                    subscription.status = 'active'
                    subscription.save()
                    return JsonResponse({'status': 'recebido'}, status=200)
                except Subscription.DoesNotExist:
                    logger.error(f"Assinatura com ID {subscription_id} não encontrada.")
                    return JsonResponse({'error': 'Assinatura não encontrada'}, status=404)

            return JsonResponse({'error': 'Tipo de notificação inválido'}, status=400)
        except json.JSONDecodeError:
            logger.error("Erro ao decodificar JSON.")
            return JsonResponse({'error': 'Erro ao processar a notificação'}, status=400)
    else:
        return JsonResponse({'error': 'Método inválido'}, status=405)


def home(request):
    

    return render(request, 'pages/home.html')




def sucess_order(request):
    user = request.user
    
    return render(request, 'pages/sucess-order.html')



def pending_order(request):

    return render(request, 'pages/pending-order.html')

@login_required
@subscription_required
def invoices(request):
    user = request.user
    restaurant = Restaurant.objects.get(user=user)
    plan = Subscription.objects.get(user=user)
    

    return render(request, 'pages/invoices.html', {'restaurant':restaurant,
                                                     'user':user,
                                                     'plan': plan,
                                                    })



@login_required
@subscription_required
def tutoriais(request):


    return render(request, 'pages/tutoriais.html')


def verify_email(request):
    if request.method == 'POST':
        # Coletando o código do formulário
        code = ''.join(request.POST.getlist('otp'))

        try:
            # Buscar o perfil do restaurante associado ao usuário atual
            user_profile = Restaurant.objects.get(user=request.user)

            # Verificar se o usuário já foi verificado
            if user_profile.is_verified:
                messages.info(request, 'Este e-mail já foi verificado.')
                return redirect('order_plan')

            # Limitar a verificação a 3 tentativas
            if user_profile.verification_attempts >= 3:
                messages.error(request, 'Você atingiu o número máximo de tentativas. Entre em contato com o suporte.')
                return render(request, 'pages/verify_email.html')

            # Verificar se o código inserido está correto
            if user_profile.verification_code == code:
                user_profile.is_verified = True
                user_profile.save()
                messages.success(request, 'E-mail verificado com sucesso!')
                return redirect('order_plan') 
            else:
                # Incrementar o número de tentativas e salvar
                user_profile.verification_attempts += 1
                user_profile.save()

                if user_profile.verification_attempts >= 3:
                    messages.error(request, 'Você atingiu o número máximo de tentativas. Entre em contato com o suporte.')
                else:
                    messages.error(request, f'Código de verificação incorreto. Tentativas restantes: {3 - user_profile.verification_attempts}.')

        except Restaurant.DoesNotExist:
            messages.error(request, 'Perfil de usuário não encontrado.')
    
    return render(request, 'pages/verify_email.html')


