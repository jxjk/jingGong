from django.urls import path
from . import views
from . import admin_views

app_name = 'quotation'

urlpatterns = [
    # 用户报价请求
    path('', views.quotation_home, name='quotation_home'),
    path('request/', views.quotation_request, name='quotation_request'),
    path('result/<int:quotation_id>/', views.quotation_result, name='quotation_result'),
    
    # DFM分析功能
    path('dfm/', views.dfm_analysis_home, name='dfm_analysis_home'),
    path('dfm/request/', views.dfm_analysis_request, name='dfm_analysis_request'),
    path('dfm/result/<int:analysis_id>/', views.dfm_analysis_result, name='dfm_analysis_result'),
    path('dfm/user/analyses/', views.user_dfm_analysis_list, name='user_dfm_analysis_list'),
    
    # 用户报价管理
    path('user/quotations/', views.user_quotation_list, name='user_quotation_list'),
    path('delete/<int:quotation_id>/', views.delete_quotation, name='delete_quotation'),
    
    # 管理员功能
    path('admin/dashboard/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin/quotations/', admin_views.quote_list, name='admin_quotation_list'),
    path('admin/quotations/<int:quote_id>/', admin_views.quotation_detail, name='admin_quotation_detail'),
    path('admin/factors/', admin_views.adjustment_factors, name='admin_factors'),
    path('admin/factors/create/', admin_views.create_adjustment_factor, name='create_factor'),
    path('admin/factors/<int:factor_id>/edit/', admin_views.edit_adjustment_factor, name='edit_factor'),
    path('admin/dfm-analyses/', admin_views.dfm_analysis_list, name='admin_dfm_analysis_list'),
    path('admin/dfm-analyses/<int:analysis_id>/', admin_views.dfm_analysis_detail, name='admin_dfm_analysis_detail'),
    path('admin/export-quotes-csv/', admin_views.export_quotes_csv, name='export_quotes_csv'),
    path('admin/quotations/<int:pk>/update-profit/', admin_views.update_profit_margin, name='update_profit_margin'),
]