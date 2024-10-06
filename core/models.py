from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
import uuid
from django.utils import timezone
from datetime import timedelta



class Subscription(models.Model):
    BASIC = 'basic'
    PREMIUM = 'premium'

    PIX = 'pix'
    CARD = 'card'

    PLAN_CHOICES = [
        (BASIC, 'Básico'),
        (PREMIUM, 'Premium'),
    ]

    PAYMENT_CHOICES = [
        (PIX, 'Pix'),
        (CARD, 'Cartão'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    subscription_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    plan_name = models.CharField(max_length=10, choices=PLAN_CHOICES)
    method_payment = models.CharField(max_length=10, choices=PAYMENT_CHOICES)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(blank=True, null=True)
    next_billing_date = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    subscription_price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Subscription of {self.user.username} - {self.plan_name}"

    def save(self, *args, **kwargs):
        if self.plan_name == self.BASIC:
            self.subscription_price = 49.90
        elif self.plan_name == self.PREMIUM:
            self.subscription_price = 69.90

        if not self.pk or not self.next_billing_date:
            self.next_billing_date = timezone.now() + timedelta(days=30)
        
        super(Subscription, self).save(*args, **kwargs)
        
        

        

@receiver(post_save, sender='restaurant.Order')  # Use o nome do app
def update_table_status_on_order_save(sender, instance, **kwargs):
    if not instance.is_delivery and instance.table is not None:
        instance.table.update_availability()

@receiver(post_delete, sender='restaurant.Order')  # Use o nome do app
def update_table_status_on_order_delete(sender, instance, **kwargs):
    if not instance.is_delivery and instance.table is not None:
        instance.table.update_availability()