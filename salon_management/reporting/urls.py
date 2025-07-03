from django.urls import path
from . import views

app_name = 'reporting'

urlpatterns = [
    path('dashboard/', views.report_dashboard, name='dashboard'),
    path('generate/', views.generate_report, name='generate_report'),
    path('view/<int:report_id>/', views.view_report, name='view_report'),
    path('export/pdf/<int:report_id>/', views.export_report_pdf, name='export_pdf'),
    path('export/csv/<int:report_id>/', views.export_report_csv, name='export_csv'),
    path('delete/<int:report_id>/', views.delete_report, name='delete_report'),
    path('sales-vs-salon/', views.sales_vs_salon_report, name='sales_vs_salon_report'),
]