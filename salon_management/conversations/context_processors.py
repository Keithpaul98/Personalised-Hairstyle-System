from .models import Message

def unread_messages_count(request):
    if request.user.is_authenticated:
        # Unread messages for customer
        customer_unread = Message.objects.filter(
            thread__customer=request.user,
            is_read=False
        ).exclude(sender=request.user)
        # Unread messages for manager
        manager_unread = Message.objects.filter(
            thread__manager=request.user,
            is_read=False
        ).exclude(sender=request.user)
        count = customer_unread.count() + manager_unread.count()
        return {'unread_messages_count': count}
    return {'unread_messages_count': 0}