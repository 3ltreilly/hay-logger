from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from .models import Log, BailCount
import datetime
from django.db.models import Sum


# useful functions
def burn_rate(hay_type, days):

    # id = get_object_or_404(Pile, pk=pk)
    start_date = datetime.datetime.now() - datetime.timedelta(days)
    end_date = datetime.datetime.now()
    bail_type = Log.objects.filter(hay_type__exact=hay_type).filter(direction__exact="WITHDRAW")
    bail_date = bail_type.filter(date__range=(start_date, end_date))
    bail_count = bail_date.aggregate(Sum('amount'))["amount__sum"]

    return round(bail_count / days,2)

class ListListView(ListView):
    model = Log
    template_name = "log_app/index.html"

    # redefine this method to add in the BailCount object
    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        context["bail_count"] = BailCount.objects.all().values()
        for hay_type in context["bail_count"]:
            hay_type["sixty"] = burn_rate(hay_type["id"], 60)
            hay_type["one_eight"] = burn_rate(hay_type["id"], 180)
            hay_type["one_year"] = burn_rate(hay_type["id"], 365)
            hay_type["empty_date"] = (
                datetime.timedelta(hay_type["total"] / hay_type["one_year"])
                + datetime.datetime.now()
            ).date()
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


class LogEdit(UpdateView):
    model = Log
    fields = ["date", "hay_type", "direction", "amount", "notes"]

    def get_context_data(self):
        context = super(LogEdit, self).get_context_data()
        context["amount_init"] = self.object.amount
        return context

    def get_initial(self):
        self.initial = super().get_initial()
        self.initial["hay_type"] = self.object.hay_type
        self.initial["direction"] = self.object.direction
        self.initial["amount"] = self.object.amount
        # return self.initial

    def form_valid(self, form):
        amount = form.cleaned_data.get("amount")
        direction = form.cleaned_data.get("direction")
        bail_type = form.cleaned_data.get("hay_type")
        # set number signs to make math easier
        if self.initial["direction"] == "WITHDRAW":
            self.initial["amount"] = -self.initial["amount"]
        if direction == "WITHDRAW":
            amount = -amount

        # check for changing hay type
        if self.initial["hay_type"] == bail_type:
            bail_type.total += amount - self.initial["amount"]
            bail_type.save(
                update_fields=[
                    "total",
                ]
            )
        else:
            bail_type.total += amount
            self.initial["hay_type"].total -= self.initial["amount"]

            bail_type.save(
                update_fields=[
                    "total",
                ]
            )
            self.initial["hay_type"].save(
                update_fields=[
                    "total",
                ]
            )

        # would like to add edit time stamp, this don't work yet
        # notes = f"{notes} edited {datetime.datetime.now()}"
        # form.save(
        #     update_fields=[
        #         "notes"
        #     ]
        # )

        return super().form_valid(form)

    def get_success_url(self):
        return reverse("index")


class LogView(ListView):
    model = Log


class LogDelete(DeleteView):
    model = Log
    success_url = reverse_lazy("index")

    def form_valid(self, form):
        amount = self.object.amount
        direction = self.object.direction
        bail_type = self.object.hay_type
        # set number signs to make math easier
        if direction == "WITHDRAW":
            amount = -amount

        bail_type.total -= amount

        bail_type.save(
            update_fields=[
                "total",
            ]
        )
        return super().form_valid(form)
