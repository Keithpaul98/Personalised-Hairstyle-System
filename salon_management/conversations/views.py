from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, ListView
from django.views.generic.edit import FormMixin, FormView
from .forms import MessageForm, StartConversationForm
from .models import Thread, Message
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy 
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.contrib import messages


from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DeleteView
from .models import Thread

class ThreadListView(LoginRequiredMixin, ListView):
    model = Thread
    template_name = 'conversations/thread_list.html'
    context_object_name = 'thread_list'  # <-- matches your template

    def get_queryset(self):
        user = self.request.user
        # Get threads where the user is either the customer or the manager
        qs = Thread.objects.filter(customer=user) | Thread.objects.filter(manager=user)
        # Annotate each thread with latest_message and unread_count
        for thread in qs:
            # Get the latest message in the thread
            thread.latest_message = thread.messages.order_by('-created_at').first()
            # Count unread messages not sent by the current user
            thread.unread_count = thread.messages.filter(is_read=False).exclude(sender=user).count()
        return qs


class ThreadDetailView(LoginRequiredMixin, FormMixin, DetailView):
    model = Thread
    template_name = 'conversations/thread_detail.html'
    context_object_name = 'thread'
    form_class = MessageForm

    def get_success_url(self):
        return reverse('conversations:thread_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['thread_messages'] = self.object.messages.order_by('created_at')
        context['form'] = self.get_form()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            message = form.save(commit=False)
            message.thread = self.object
            message.sender = request.user
            message.save()
        # Mark as read for the recipient
            self.object.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
           
            if request.headers.get('Hx-Request') == 'true':
            # Render only the message list
                html = render_to_string(
                'conversations/conversation_container.html',
                {
                'thread_messages': self.object.messages.order_by('created_at'),
                'form': MessageForm(),
                'thread':self.object,
                'user': request.user
                },
                request=request
                )
                return HttpResponse(html)
            return super().form_valid(form)
        return self.form_invalid(form)




    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Mark all unread messages not sent by the current user as read
        unread_messages = self.object.messages.filter(is_read=False).exclude(sender=request.user)
        unread_messages.update(is_read=True)
        return super().get(request, *args, **kwargs)
# Create your views here.


class StartConversationView(LoginRequiredMixin, FormView):
    template_name = 'conversations/start_conversation.html'
    form_class = StartConversationForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = self.request.user
        recipient = form.cleaned_data['recipient']
        content = form.cleaned_data['content']

        if user.is_staff:
            customer = recipient
            manager = user
        else:
            customer = user
            manager = recipient

        thread, created = Thread.objects.get_or_create(customer=customer, manager=manager)
        if created or not thread.messages.exists():
            Message.objects.create(thread=thread, sender=user, content=content)
        else:
            messages.info(self.request, "A conversation already exists.")
        return redirect('conversations:thread_detail', pk=thread.pk)


class ThreadDeleteView(LoginRequiredMixin, DeleteView):
    model = Thread
    template_name = 'conversations/thread_confirm_delete.html'
    success_url = reverse_lazy('conversations:thread_list')  # adjust if your list view has a different name