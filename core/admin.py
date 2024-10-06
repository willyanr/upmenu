from django.contrib import admin
from .models import Subscription
from delivery.models import DeliveryOrder
from menu.models import Menu, Ingredient
from restaurant.models import Table, Restaurant, Waiter, OrderItem, Order


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'status', 'cost', 'get_description')
    search_fields = ('name',)
    list_filter = ('status',)
    filter_horizontal = ('ingredients',)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    fields = ('menu_item', 'quantity', 'special_instructions', 'get_final_ingredients', 'removed_ingredients')
    readonly_fields = ('get_final_ingredients',)
    filter_horizontal = ('removed_ingredients',)

    def get_final_ingredients(self, obj):
        if obj.pk:
            return ', '.join(obj.get_final_ingredients())
        return '-'
    get_final_ingredients.short_description = 'Final Ingredients'

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('table', 'order_date', 'is_closed', 'get_total_value', 'waiter')
    search_fields = ('table__table_number', 'waiter__name')
    list_filter = ('order_date', 'is_closed', 'waiter')
    inlines = [OrderItemInline]  # Adiciona inline para OrderItem

    def get_total_value(self, obj):
        return obj.get_total_value()
    get_total_value.short_description = 'Total Value'

@admin.register(DeliveryOrder)
class DeliveryOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_name', 'total_order', 'total_payment', 'payment_method', 'terms_accepted')
    inlines = [OrderItemInline]  # Adiciona inline para OrderItem

    
@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ('table_number', 'is_active')
    search_fields = ('table_number',)
    list_filter = ('is_active',)
    ordering = ('table_number',)



@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'address', 'cep', 'cnpj', 'cpf', 'phone_number',
        'delivery_opening_time', 'delivery_closing_time', 'delivery_is_active', 'user'
    )
    search_fields = ('name', 'cnpj', 'cpf')
    list_filter = ('address', 'delivery_is_active')
    fields = (
        'user', 'name', 'address', 'cep', 'cnpj', 'cpf', 'phone_number', 
        'delivery_rate_per_km', 'description', 'img', 
        'delivery_opening_time', 'delivery_closing_time', 'delivery_is_active'
    )
    readonly_fields = ('delivery_is_active',)

    def save_model(self, request, obj, form, change):
        obj.update_delivery_status()
        super().save_model(request, obj, form, change)


class WaiterAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_username')
    search_fields = ('name', 'user__username')

    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Username'


admin.site.register(Waiter, WaiterAdmin)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan_name', 'status', 'start_date', 'end_date')
    search_fields = ('user__username', 'plan_name')
    list_filter = ('plan_name', 'status', 'start_date')
    readonly_fields = ('subscription_id', 'start_date', 'created_at', 'updated_at')
