from django.urls import path
from . import views

app_name = 'virtual_tryon'

urlpatterns = [
    path('', views.upload_photo, name='home'),  # Add home URL
    path('upload/', views.upload_photo, name='upload_photo'),
    path('recommend/', views.recommend_hairstyles, name='recommend_hairstyles'),
    path('try-on/<int:hairstyle_id>/', views.try_on_hairstyle, name='try_on_hairstyle'),
    path('history/', views.view_tryon_history, name='view_tryon_history'),
    path('book/<int:tryon_id>/', views.book_appointment, name='book_appointment'),
    path('guide/', views.face_shape_guide, name='face_shape_guide'),
    path('delete/<int:tryon_id>/', views.delete_tryon, name='delete_tryon'),
]