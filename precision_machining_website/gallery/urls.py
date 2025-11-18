from django.urls import path
from . import views

app_name = 'gallery'

urlpatterns = [
    path('', views.work_list, name='work_list'),
    path('category/<slug:category_slug>/', views.work_list, name='work_list_by_category'),
    path('work/<int:id>/', views.work_detail, name='work_detail'),
]