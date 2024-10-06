from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('menu/', views.menu_list, name='menu'),
    path('search/', views.search_menu, name='search_menu'),
    path('add/', views.add_menu_item, name='add_menu_item'),
    path('update/<int:pk>/', views.update_menu_item, name='update_menu_item'),
    path('delete/<int:pk>/', views.delete_menu_item, name='delete_menu_item'),
    path('api/ingredients/<int:item_id>/', views.get_ingredients, name='get_ingredients'),
    path('api/delete_ingredients/<int:pk>/', views.delete_ingredients, name='delete_ingredients'),
    path('ingredients/', views.ingredients, name='ingredients'),
    
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

