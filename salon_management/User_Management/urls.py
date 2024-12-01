from django.urls import path
from . import views

urlpatterns = [
    path('customer_registration/', views.customer_registration, name='customer_registration'),
    path('login/', views.custom_login, name='custom_login'),
    path('logout/', views.custom_logout, name='custom_logout'),
    path('admin_registration/', views.admin_registration, name='admin_registration'),
    path('customer_products/', views.customer_products, name='customer_products'),
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('profile/', views.profile, name='profile'),
    path('add_to_cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'), # URL for adding to cart 
    path('cart/', views.view_cart, name='view_cart'),
    path('remove_from_cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('receipts/', views.view_receipts, name='view_receipts'), path('receipts/<int:receipt_id>/download/', views.download_receipt, name='download_receipt'),
]
