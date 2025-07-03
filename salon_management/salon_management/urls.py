"""
URL configuration for salon_management project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
import os

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('User_Management.urls')),
    path('appointments/', include('appointments.urls')),
    path('services/', include('services.urls')),
    path('payments/', include('payments.urls')),
    path('stock/', include('Stock_Management.urls', namespace='Stock_Management')),
    path('reporting/', include('reporting.urls', namespace='reporting')),
    path('notifications/', include('notifications.urls', namespace='notifications')),
    path('conversations/', include('conversations.urls', namespace='conversations')),
    path('virtual-tryon/', include('virtual_tryon.urls', namespace='virtual_tryon')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# We no longer need this since virtual_tryon_results is now inside MEDIA_ROOT
# and will be served by the main media URL configuration above
# if settings.DEBUG:
#     urlpatterns += static('/virtual_tryon_results/', document_root=os.path.join(settings.BASE_DIR, 'virtual_tryon_results'))
