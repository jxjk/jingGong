from django.urls import path
from . import views
from . import admin_views

urlpatterns = [
    # 用户端路由
    path('', views.home, name='quotation_home'),
    path('request/', views.quotation_request, name='quotation_request'),
    path('result/<int:request_id>/', views.quotation_result, name='quotation_result'),
    
    # 管理员路由
    path('admin/dashboard/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin/quotes/', admin_views.quote_list, name='admin_quote_list'),
    path('admin/quotes/<int:quote_id>/', admin_views.quote_detail, name='admin_quote_detail'),
    path('admin/export/csv/', admin_views.export_quotes_csv, name='admin_export_csv'),
]