from django.urls import path
from . import views
from .views import login_view
from django.contrib.auth import views as auth_views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('', views.home, name='home'),
    path('verify-email/', views.verify_email, name='verify_email'),
    
   

    path('login/', login_view, name='login'),
    

   
    
    path('dashboard/', views.dashboard_user, name='dashboard'),

    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('create-ingredient/', views.create_ingredient, name='create_ingredient'),
    path('create-table/', views.create_table, name='create_table'),
    path('edit-image/', views.edit_image, name='edit_image'),
    path('register/', views.register, name='register'),
    path('home/', views.home, name='home'),
    path('webhook/', views.mercado_pago_webhook, name='mercado_pago_webhook'),
    
    path('create-subscription/<str:plan_name>/', views.create_subscription, name='create_subscription'),
    
    
    path('pending-order/', views.pending_order, name='panding-order'),
    path('faturas/', views.invoices, name='invoices'),
    path('tutoriais/', views.tutoriais, name='tutoriais'),

    path('serve-pdf/<int:order_id>/<str:order_type>/', views.serve_pdf, name='serve_pdf'),

    
    

    
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

