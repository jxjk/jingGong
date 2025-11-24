from django.urls import path
from . import views

app_name = 'roles'

urlpatterns = [
    # 角色管理
    path('', views.role_list, name='role_list'),
    path('create/', views.role_create, name='role_create'),
    path('<int:role_id>/edit/', views.role_edit, name='role_edit'),
    path('<int:role_id>/delete/', views.role_delete, name='role_delete'),
    
    # 用户角色管理
    path('users/', views.user_role_list, name='user_role_list'),
    path('users/<int:user_id>/assign/', views.user_role_assign, name='user_role_assign'),
]