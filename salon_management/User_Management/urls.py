from django.urls import path, include
from . import views

app_name = 'User_Management'

urlpatterns = [
    path('', views.home, name='home'),
    path('customer_registration/', views.customer_registration, name='customer_registration'),
    path('login/', views.custom_login, name='custom_login'),
    path('logout/', views.custom_logout, name='custom_logout'),
    path('admin_registration/', views.admin_registration, name='admin_registration'),
    path('products/', views.customer_products, name='customer_products'),
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('profile/', views.profile, name='profile'),
    path('add_to_cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'), # URL for adding to cart 
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('receipts/', views.view_receipts, name='view_receipts'),
    path('receipts/<int:receipt_id>/download/', views.download_receipt, name='download_receipt'),
    path('delete_profile/', views.delete_profile, name='delete_profile'),
    path ('add_stylist', views.add_stylist, name='add_stylist'),
    path ('add_product/', views.add_product, name='add_product'),
    path('add-service/', views.add_service, name='add_service'),
    path('edit-service/<int:service_id>/', views.edit_service, name='edit_service'),
    path('delete-service/<int:service_id>/', views.delete_service, name='delete_service'),
    path('add-staff/', views.add_staff, name='add_staff'),
    path('edit-staff/<int:staff_id>/', views.edit_staff, name='edit_staff'),
    path('delete-staff/<int:staff_id>/', views.delete_staff, name='delete_staff'),
    path('add-product/', views.add_product, name='add_product'),
    path('edit-product/<int:product_id>/', views.edit_product, name='edit_product'),
    path('delete-product/<int:product_id>/', views.delete_product, name='delete_product'),
    path('checkout/', views.checkout, name='checkout'),
    path('services/', include('services.urls')),  # This will include the services app URLs
    path('stylists/', views.stylist_directory, name='stylist_directory'),
    path('stylists/<int:stylist_id>/', views.stylist_profile, name='stylist_profile'),
    path('staff-dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('customer-list/', views.customer_list, name='customer_list'),
    path('update-total-earned-points/', views.update_total_earned_points, name='update_total_earned_points'),
    path('reset-total-earned-points/', views.reset_total_earned_points, name='reset_total_earned_points'),
]
