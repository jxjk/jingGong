from django.contrib import admin
from .models import Order, OrderStatusHistory, ProductionProgress, Notification


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'customer_name', 'product_name', 'status', 'quantity', 'total_price', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order_number', 'customer_name', 'customer_email', 'product_name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['order', 'status', 'timestamp', 'operator']
    list_filter = ['status', 'timestamp']
    search_fields = ['order__order_number', 'operator']
    ordering = ['-timestamp']


@admin.register(ProductionProgress)
class ProductionProgressAdmin(admin.ModelAdmin):
    list_display = ['order', 'stage', 'is_completed', 'started_at', 'completed_at']
    list_filter = ['is_completed', 'started_at', 'completed_at']
    search_fields = ['order__order_number', 'stage']
    ordering = ['order', 'id']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['order', 'title', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['order__order_number', 'title']
    ordering = ['-created_at']