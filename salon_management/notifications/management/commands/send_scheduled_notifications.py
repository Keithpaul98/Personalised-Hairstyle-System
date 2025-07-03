from django.core.management.base import BaseCommand
from notifications.scheduled_notifications import run_all_scheduled_notifications

class Command(BaseCommand):
    help = 'Sends scheduled notifications like appointment reminders and loyalty points expiration alerts'

    def handle(self, *args, **options):
        results = run_all_scheduled_notifications()
        
        # Customer notification summary
        customer_notifications = (
            f"{results.get('appointment_reminders', 0)} appointment reminders, "
            f"{results.get('loyalty_reminders', 0)} loyalty points expiration reminders, "
            f"{results.get('new_product_notifications', 0)} new product notifications, "
            f"{results.get('service_discount_notifications', 0)} service discount notifications, "
            f"{results.get('birthday_special_notifications', 0)} birthday special offers, "
            f"{results.get('inactive_customer_notifications', 0)} re-engagement notifications"
        )
        
        # Stylist notification summary
        stylist_notifications = (
            f"{results.get('busy_day_notifications', 0)} busy day alerts, "
            f"{results.get('schedule_gap_notifications', 0)} schedule gap alerts, "
            f"{results.get('customer_anniversary_notifications', 0)} customer anniversary reminders"
        )
        
        # Admin notification summary
        admin_notifications = (
            f"{results.get('product_restock_notifications', 0)} product restock alerts, "
            f"{results.get('daily_revenue_notifications', 0)} daily revenue summaries, "
            f"{results.get('staff_performance_notifications', 0)} staff performance reports, "
            f"{results.get('cancellation_trend_notifications', 0)} cancellation trend analyses"
        )
        
        self.stdout.write(self.style.SUCCESS(f"Successfully sent customer notifications: {customer_notifications}"))
        self.stdout.write(self.style.SUCCESS(f"Successfully sent stylist notifications: {stylist_notifications}"))
        self.stdout.write(self.style.SUCCESS(f"Successfully sent admin notifications: {admin_notifications}"))