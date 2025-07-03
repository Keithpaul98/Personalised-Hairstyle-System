from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Thread(models.Model):
    customer = models.ForeignKey(User, related_name='customer_threads', on_delete=models.CASCADE)
    manager = models.ForeignKey(User, related_name='manager_threads', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Thread between {self.customer} and {self.manager}"

class Message(models.Model):
    thread = models.ForeignKey(Thread, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message in thread {self.thread.id} by {self.sender}"