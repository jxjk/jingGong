from django.urls import path
from . import views

app_name = 'quotation'

urlpatterns = [
    path('', views.quotation_home, name='home'),
    path('request/', views.quotation_request, name='request'),
    path('result/<int:quotation_id>/', views.quotation_result, name='result'),
]