from django.urls import path
from . import views, admin_views

app_name = 'orders'

urlpatterns = [
    # 用户端URL
    path('', views.order_list, name='order_list'),
    path('<int:order_id>/', views.order_detail, name='order_detail'),
    path('create/<int:quotation_id>/', views.create_order_from_quotation, name='create_order'),
    path('api/status/<int:order_id>/', views.order_status_api, name='order_status_api'),
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('monitoring/<int:order_id>/', views.production_monitoring, name='production_monitoring'),
    
    # 管理端URL
    path('admin/', admin_views.admin_order_list, name='admin_order_list'),
    path('admin/<int:order_id>/', admin_views.admin_order_detail, name='admin_order_detail'),
    path('admin/<int:order_id>/status/', admin_views.admin_update_order_status, name='admin_update_order_status'),
    path('admin/<int:order_id>/progress/', admin_views.admin_add_production_progress, name='admin_add_production_progress'),
    path('admin/progress/<int:progress_id>/', admin_views.admin_update_production_progress, name='admin_update_production_progress'),
    path('admin/<int:order_id>/notify/', admin_views.admin_send_notification, name='admin_send_notification'),
]