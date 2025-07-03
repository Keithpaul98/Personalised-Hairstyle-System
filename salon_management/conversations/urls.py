from django.urls import path
from . import views
from .views import ThreadDeleteView

app_name = 'conversations'

urlpatterns = [
    path('', views.ThreadListView.as_view(), name='thread_list'),
    path('thread/<int:pk>/', views.ThreadDetailView.as_view(), name='thread_detail'),
    path('start/', views.StartConversationView.as_view(), name='start_conversation'),
     path('thread/<int:pk>/delete/', ThreadDeleteView.as_view(), name='thread_delete'), 
]