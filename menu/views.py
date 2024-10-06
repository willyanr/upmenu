from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from core.views import subscription_required, exclude_garcon
from menu.models import Menu, Ingredient
from django.core.paginator import Paginator
from django.db.models import Q
from core.forms import MenuForm, IngredientForm, TableForm, RestaurantImageForm, UserForm, RestaurantForm
from django.shortcuts import render, get_object_or_404, redirect
from restaurant.models import Restaurant
import logging
from django.http import JsonResponse
from django.urls import reverse


@subscription_required
@exclude_garcon
@login_required
def menu_list(request):
    
    menu_list = Menu.objects.filter(user=request.user)
    ingredient_count = Ingredient.objects.filter(user=request.user).count()
    menu_item_count = menu_list.count()
    paginator = Paginator(menu_list, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)


    return render(request, 'tabela-menu.html', {
        'page_obj': page_obj,
        'ingredient_count': ingredient_count,
        'menu_item_count': menu_item_count
    })
    
    

@login_required
def search_menu(request):
    query = request.GET.get('q')
    results = []
    if query:
        results = Menu.objects.filter(
            Q(name__icontains=query) | 
            Q(ingredients__name__icontains=query)
        ).distinct().order_by('name')

    return render(request, 'pages/menu-user.html', {'results': results, 'query': query})




@exclude_garcon
@login_required
def add_menu_item(request):
    if request.method == "POST":
        form = MenuForm(request.POST, request.FILES, user=request.user)

        if form.is_valid():
            menu_item = form.save(commit=False)

            # Supondo que o restaurante esteja relacionado ao usuário
            # Obtenha o restaurante associado ao usuário atual
            try:
                restaurant = request.user.restaurant  # Certifique-se de como o relacionamento com o restaurante está definido
                menu_item.restaurant = restaurant  # Atribua o restaurante ao menu_item
            except Restaurant.DoesNotExist:
                print("Erro: Usuário não está associado a um restaurante")
                return redirect('error_page')

            menu_item.user = request.user  # Relacionar ao usuário que criou o item de menu
            menu_item.save()

            # Definir os ingredientes do item de menu
            menu_item.ingredients.set(form.cleaned_data['ingredients'])

            return redirect('menu')
        else:
            print(form.errors)
    else:
        form = MenuForm(user=request.user)

    return render(request, 'add_menu_item.html', {'form': form})



@exclude_garcon
@login_required
def update_menu_item(request, pk):
    item = get_object_or_404(Menu, pk=pk)
    
    if request.method == "POST":
        form = MenuForm(request.POST, request.FILES, instance=item, user=request.user)
        if form.is_valid():
            menu_item = form.save(commit=False)
            menu_item.user = request.user 
            menu_item.save()

            menu_item.ingredients.set(form.cleaned_data['ingredients'])
            
            print("Menu Item Saved:", menu_item)
            return redirect('menu')
        else:
            print("Form Errors:", form.errors)
    else:
        form = MenuForm(instance=item, user=request.user)
    
    return render(request, 'update_menu_item.html', {'form': form, 'item': item})

@exclude_garcon
@login_required
def delete_menu_item(request, pk):
    item = get_object_or_404(Menu, pk=pk)
    if request.method == "POST":
        item.delete()
        return redirect('menu')
    return render(request, 'confirm_delete.html', {'item': item})





logger = logging.getLogger(__name__)
@login_required
def get_ingredients(request, item_id):
    from restaurant.models import Waiter
    
    logger.debug(f"Received request for item_id: {item_id} from user: {request.user}")

    user = request.user
    waiter = None
    waiter_restaurant = None

    # Tenta recuperar o garçom associado ao usuário
    try:
        waiter = Waiter.objects.get(user=user) 
        waiter_restaurant = waiter.restaurant
        print(f'Garçom encontrado: {waiter.name}, ID: {waiter.id}')
        print(f'Restaurante encontrado: {waiter_restaurant.id}')
    except Waiter.DoesNotExist:
        # O usuário não é um garçom, mas pode ser o dono do restaurante
        # Tenta encontrar o restaurante associado ao usuário
        try:
            # Supondo que o modelo Restaurant tenha um campo user para o dono
            waiter_restaurant = Restaurant.objects.get(user=user)
            print(f'Dono do restaurante encontrado: {waiter_restaurant.name}, ID: {waiter_restaurant.id}')
        except Restaurant.DoesNotExist:
            logger.error(f"O usuário {user} não é garçom nem dono de um restaurante.")
            return JsonResponse({'error': 'Acesso negado, usuário não tem permissão'}, status=403)

    # Recupera o menu item associado ao ID fornecido e ao restaurante do garçom ou do dono
    try:
        item = Menu.objects.get(id=item_id, restaurant=waiter_restaurant)
        logger.debug(f"Found menu item: {item.name}")
    except Menu.DoesNotExist:
        logger.error(f"Menu item with id {item_id} not found or access denied for user: {request.user}")
        return JsonResponse({'error': 'Menu item not found or access denied'}, status=404)
    
    # Recupera os ingredientes associados ao menu item
    ingredients = item.ingredients.all()
    if not ingredients:
        logger.debug("No ingredients found for the menu item.")
    
    logger.debug(f"Ingredients found: {[ingredient.name for ingredient in ingredients]}")

    # Cria a lista de dados dos ingredientes
    ingredient_data = [{'id': ingredient.id, 'name': ingredient.name} for ingredient in ingredients]
    
    logger.debug(f"Returning ingredient data: {ingredient_data}")

    return JsonResponse({'ingredients': ingredient_data})

@login_required
def delete_ingredients(request, pk):
    item = get_object_or_404(Ingredient, pk=pk)
    if request.method == 'POST':
        item.delete()
        return redirect(reverse('menu'))
        
    return render(request, 'pages/delete_ingredients.html')
    
    
@login_required
def ingredients(request):
    
    ingredients = Ingredient.objects.filter(user=request.user)
    
    return render(request, 'pages/ingredients.html', { 'ingredients': ingredients})
    
    