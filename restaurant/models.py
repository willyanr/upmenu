from django.db import models
from django.contrib.auth.models import User
import uuid
from django.contrib.sites.models import Site
from django.conf import settings
from datetime import time
from django.utils import timezone

from menu.models import Menu, Ingredient
import logging

class Restaurant(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='restaurant')
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=255, default='Campo Grande')
    cep = models.CharField(max_length=9)
    cnpj = models.CharField(max_length=20)
    cpf = models.CharField(max_length=14)
    phone_number = models.CharField(max_length=15)
    restaurant_code = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    delivery_is_active = models.BooleanField(default=True)
    delivery_rate_per_km = models.DecimalField(max_digits=5, decimal_places=2, default=2.00, blank=True)
    description = models.CharField(max_length=300, blank=True, null=True)
    img = models.ImageField(upload_to='menu_images/', blank=True, default='menu_images/avatar_restaurant.webp')
    delivery_opening_time = models.TimeField(default=time(0, 0), blank=True)  
    delivery_closing_time = models.TimeField(default=time(23, 59), blank=True)  
    verification_code = models.CharField(max_length=4, blank=True, null=True)
    verification_attempts = models.IntegerField(default=0)
    is_verified = models.BooleanField(default=False)
    default_printer = models.CharField(max_length=255, blank=True, null=True)
    delivery_time_in_minutes = models.PositiveIntegerField(default=30, help_text="Tempo de entrega em minutos")

    def __str__(self):
        return self.name
    
    def get_restaurant_url(self):
        if settings.DEBUG:
            domain = 'upmenu.online'
        else:
            current_site = Site.objects.get_current()
            domain = current_site.domain

        return f"http://{domain}/delivery/restaurant/{self.restaurant_code}/"
        
    def update_delivery_status(self):
        now = timezone.localtime(timezone.now()).time()
        self.delivery_is_active = self.delivery_opening_time <= now <= self.delivery_closing_time
        self.save()


class Table(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tables')
    table_number = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.table_number}"

    def get_total_orders_value(self):
        """Returns the total value of all orders for the table."""
        orders = self.orders.filter(is_closed=False)
        return sum(order.get_total_value() for order in orders)

    def update_availability(self):
        """Updates the table's availability based on open orders."""
        self.is_active = not self.orders.filter(is_closed=False).exists()
        self.save()


class Waiter(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='waiters')
    name = models.CharField(max_length=50)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='waiters')
    

    def __str__(self):
        return self.name


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    PAYMENT_METHODS = [
        ('pix', 'PIX'),
        ('dinheiro', 'Dinheiro'),
        ('cartao', 'Cartão'),
    ]
    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='orders', null=True, blank=True)
    order_date = models.DateTimeField(auto_now_add=True)
    is_closed = models.BooleanField(default=False)
    waiter = models.ForeignKey(Waiter, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS, null=True, blank=True)
    is_delivery = models.BooleanField(default=False)  
    observation = models.CharField(max_length=60, blank=True, null=True)
    order_print = models.BooleanField(default=False)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='user_restaurant')
    
    def __str__(self):
        table_number = self.table.table_number if self.table else 'Unknown Table'
        waiter_name = self.waiter.name if self.waiter else 'Unknown Waiter'
        return f"Order #{self.id} for Table {table_number} by {waiter_name}"

    def get_total_value(self):
        total_value = sum(item.get_total_value() for item in self.order_items.all())
        logging.debug(f"Total value for Order #{self.id}: {total_value}")
        return total_value

class OrderItem(models.Model):

    order = models.ForeignKey(Order, related_name='order_items', on_delete=models.CASCADE, null=True, blank=True)
    delivery_order = models.ForeignKey('delivery.DeliveryOrder', related_name='order_items', on_delete=models.CASCADE, null=True, blank=True)
    menu_item = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name='order_items')
    quantity = models.PositiveIntegerField(default=1)
    special_instructions = models.TextField(blank=True)
    removed_ingredients = models.ManyToManyField(Ingredient, related_name='removed_from_order_items', blank=True)

    def __str__(self):
        return f"{self.quantity} x {self.menu_item.name}"

    def get_total_value(self):
        item_value = self.menu_item.value * self.quantity
        logging.debug(f"Total value for {self.quantity} x {self.menu_item.name}: {item_value}")
        return item_value
    
    
    def get_final_ingredients(self):
        all_ingredients = set(self.menu_item.ingredients.all())
        removed_ingredients = set(self.removed_ingredients.all())
        final_ingredients = all_ingredients - removed_ingredients
        return [ingredient.name for ingredient in final_ingredients]