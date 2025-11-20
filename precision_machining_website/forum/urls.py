from django.urls import path
from . import views

app_name = 'forum'

urlpatterns = [
    path('', views.category_list, name='category_list'),
    path('category/<int:category_id>/', views.post_list, name='post_list'),
    path('post/<int:pk>/', views.post_detail, name='post_detail'),
    path('post/create/', views.post_create, name='post_create'),
    path('post/<int:pk>/edit/', views.post_edit, name='post_edit'),
]
