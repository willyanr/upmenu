from django.db import models
from restaurant.models import Restaurant


class DeliveryOrder(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('accepted', 'Aceito'),
        ('canceled', 'Cancelado'),
    ]
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='delivery_orders')
    items = models.ManyToManyField('menu.Menu', related_name='delivery_orders')
    total_order = models.DecimalField(max_digits=10, decimal_places=2)
    total_payment = models.DecimalField(max_digits=10, decimal_places=2)
    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField(blank=True, null=True)
    customer_phone = models.CharField(max_length=20)
    address = models.CharField(max_length=255, blank=True, null=True)
    house_number = models.CharField(max_length=10, blank=True, null=True)
    complement = models.CharField(max_length=50, blank=True, null=True)
    payment_method = models.CharField(max_length=20)
    terms_accepted = models.BooleanField(default=False)
    order_date = models.DateTimeField(auto_now_add=True)  # Adicionando esta linha
    cep = models.CharField(max_length=10, blank=True, null=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    frete = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    observation = models.CharField(max_length=60, blank=True, null=True)
    is_local = models.BooleanField(default=False)

    def __str__(self):
        return f"Delivery Order for {self.customer_name}"

class Notification(models.Model):
    from django.contrib.auth.models import User
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, null=True, blank=True)  # Adicione este campo
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.CharField(max_length=255)
    order = models.ForeignKey(DeliveryOrder, on_delete=models.CASCADE, null=True, blank=True)
    seen = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.message