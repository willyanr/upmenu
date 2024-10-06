from restaurant.models import Restaurant

def restaurant_code(request):

    if request.user.is_authenticated and hasattr(request.user, 'restaurant'):
        restaurant_code = str(request.user.restaurant.restaurant_code)
    else:
        restaurant_code = None
    
    return {'restaurant_code': restaurant_code}
