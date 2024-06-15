from django.shortcuts import render

# Create your views here.
from django.urls import reverse
from django.views.generic import ListView, CreateView
from .models import Log, BailCount


class ListListView(ListView):
    model = Log
    template_name = "log_app/index.html"

    # redefine this method to add in the BailCount object
    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        context["bail_count"] = BailCount.objects.all()
        return context


class LogCreate(CreateView):
    # This make a form to enter in data
    model = Log
    fields = ["date", "hay_type", "direction", "amount", "notes"]

    def form_valid(self, form):
        amount = form.cleaned_data.get("amount")
        direction = form.cleaned_data.get("direction")

        bail_type = form.cleaned_data.get("hay_type")
        if direction == "WITHDRAW":
            bail_type.total -= amount
        elif direction == "DEPOSIT":
            bail_type.total += amount

        bail_type.save(
            update_fields=[
                "total",
            ]
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("index")
