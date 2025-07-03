from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [
    path('', views.service_list, name='service_list'),
    path('<int:service_id>/', views.service_detail, name='service_detail'),
    path('hairstyles/', views.list_hairstyles, name='list_hairstyles'),
    path('hairstyles/<int:hairstyle_id>/select/', views.select_hairstyle, name='select_hairstyle'),
]