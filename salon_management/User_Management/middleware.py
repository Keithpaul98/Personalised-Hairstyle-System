from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

class RoleBasedAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Define path restrictions for each role
            admin_only_paths = ['/admin-dashboard/', '/add-service/', '/edit-service/']
            staff_only_paths = ['/staff-dashboard/']  
            customer_only_paths = ['/cart/', '/products/', '/book-appointment/']
            
            current_path = request.path
            
            # Restrict access based on role
            if request.user.role == 'admin':
                if current_path in customer_only_paths:
                    messages.error(request, 'Access denied. Admins cannot access customer pages.')
                    return redirect('User_Management:admin_dashboard')
                    
            elif request.user.role == 'staff':
                if current_path in customer_only_paths or current_path in admin_only_paths:
                    messages.error(request, 'Access denied. Staff cannot access these pages.')
                    return redirect('User_Management:staff_dashboard')
                    
            elif request.user.role == 'customer':
                if current_path in admin_only_paths or current_path in staff_only_paths:
                    messages.error(request, 'Access denied. Customers cannot access these pages.')
                    return redirect('User_Management:home')

        response = self.get_response(request)
        return response