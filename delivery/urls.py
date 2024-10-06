from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    
    path('checkout/<uuid:restaurant_code>/', views.checkout_orders, name='checkout'),
    path('capture-order-data/', views.capture_order_data, name='capture_order_data'),
    path('restaurant/<uuid:restaurant_code>/', views.menu_orders, name='a'),
    path('get-cep/', views.get_cep, name='get_cep'),
    path('delivery/', views.page_delivery, name='delivery'),
    path('approve-order/<int:order_id>/', views.approve_order, name='approve_order'),
    path('sucess-order/<int:order_id>/', views.sucess_page, name='sucess_order'),
    path('order-status/<int:order_id>/', views.order_status, name='order-status'),
    path('delivery_approved/<int:order_id>/', views.delivery_approved_view, name='delivery_approved'),
    path('delivery/delivery_canceled/<int:order_id>/', views.delivery_canceled_view, name='delivery_canceled'),
    path('cancel-order/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path('mark-notifications-as-seen/', views.mark_notifications_as_seen, name='mark_notifications_as_seen'),
    path('delivery/restaurant/<str:restaurant_code>/', views.menu_orders, name='menu_orders'),
    path('order/pickup/<str:restaurant_code>/', views.order_pickup, name='order_pickup'),
    
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

