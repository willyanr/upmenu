from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('mesas/', views.tables, name='tables'),  
    path('menu-user/', views.menu_user, name='menu_user'),  
    path('submit-order/', views.submit_order, name='submit_order'),

    path('close-order/<int:order_id>/', views.close_order, name='close_order'),
    path('configuracao/', views.manage_restaurant, name='config'),
    path('escolher-plano/', views.order_plan, name='order_plan'),

 
    
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

