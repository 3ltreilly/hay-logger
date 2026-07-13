import csv
import datetime
import json

import pytz
from django.db.models import Sum
from django.http import HttpResponse
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from .models import BailCount, Log


# useful functions
def burn_rate(hay_type, days):
    last_log = (
        Log.objects.filter(hay_type__exact=hay_type)
        .filter(direction__exact="WITHDRAW")
        .latest("date")
    )
    start_date = last_log.date - datetime.timedelta(days)
    end_date = last_log.date
    bail_type = Log.objects.filter(hay_type__exact=hay_type).filter(direction__exact="WITHDRAW")
    bail_date = bail_type.filter(date__range=(start_date, end_date))
    bail_count = bail_date.aggregate(Sum("amount"))["amount__sum"]

    return round(bail_count / days, 2)


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
            # get date of last log for empty date math
            try:
                last_log = (
                    Log.objects.filter(hay_type__exact=hay_type["id"])
                    .filter(direction__exact="WITHDRAW")
                    .latest("date")
                )
            except Log.DoesNotExist:
                pass
            hay_type["sixty"] = burn_rate(hay_type["id"], 60)
            hay_type["one_eight"] = burn_rate(hay_type["id"], 180)
            hay_type["one_year"] = burn_rate(hay_type["id"], 365)
            hay_type["empty_date"] = (
                datetime.timedelta(hay_type["total"] / hay_type["one_year"]) + last_log.date
            ).date()
            hay_type["throw_down"] = round(
                (datetime.datetime.now(pytz.utc) - last_log.date).days * hay_type["one_year"]
            )
        return context


class UsageOverTimeView(TemplateView):
    template_name = "log_app/usage_over_time.html"

    def _parse_date(self, raw_value):
        if not raw_value:
            return None

        try:
            return datetime.datetime.strptime(raw_value, "%Y-%m-%d").date()
        except ValueError:
            return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        start_date = self._parse_date(self.request.GET.get("start_date"))
        end_date = self._parse_date(self.request.GET.get("end_date"))

        context["start_date"] = self.request.GET.get("start_date", "")
        context["end_date"] = self.request.GET.get("end_date", "")

        logs = Log.objects.order_by("date")
        if start_date:
            logs = logs.filter(date__date__gte=start_date)
        if end_date:
            logs = logs.filter(date__date__lte=end_date)

        logs = logs.values("date", "hay_type__name", "direction", "amount")

        daily_changes = {}
        hay_types = []
        for entry in logs:
            day = entry["date"].date().isoformat()
            hay_type_name = entry["hay_type__name"]
            change = entry["amount"] if entry["direction"] == "DEPOSIT" else -entry["amount"]

            if day not in daily_changes:
                daily_changes[day] = {}
            daily_changes[day][hay_type_name] = daily_changes[day].get(hay_type_name, 0) + change
            if hay_type_name not in hay_types:
                hay_types.append(hay_type_name)

        labels = sorted(daily_changes.keys())
        running_totals = {hay_type: 0 for hay_type in hay_types}
        data_by_type = {hay_type: [] for hay_type in hay_types}

        for day in labels:
            for hay_type in hay_types:
                running_totals[hay_type] += daily_changes[day].get(hay_type, 0)
                data_by_type[hay_type].append(running_totals[hay_type])

        # find offset to get running total to match current bail count
        bail_counts = {
            bail_count["name"]: bail_count["total"]
            for bail_count in BailCount.objects.all().values("name", "total")
        }
        offset = {
            hay_type: bail_counts.get(hay_type, 0) - running_totals.get(hay_type, 0)
            for hay_type in hay_types
        }

        color_palette = [
            ("rgba(75, 192, 192, 1)", "rgba(75, 192, 192, 0.2)"),
            ("rgba(255, 99, 132, 1)", "rgba(255, 99, 132, 0.2)"),
            ("rgba(54, 162, 235, 1)", "rgba(54, 162, 235, 0.2)"),
        ]
        datasets = []
        for index, hay_type in enumerate(hay_types):
            border_color, background_color = color_palette[index % len(color_palette)]
            # apply offset to running totals
            plot_data = [num + offset[hay_type] for num in data_by_type[hay_type]]
            datasets.append(
                {
                    "label": hay_type.capitalize(),
                    "data": plot_data,
                    "borderColor": border_color,
                    "backgroundColor": background_color,
                    "fill": False,
                    "tension": 0.2,
                }
            )

        context["usage_labels"] = json.dumps(labels)
        context["usage_datasets"] = json.dumps(datasets)
        return context


class LogCreate(CreateView):
    """Make view for entering in a hay log

    Args:
        CreateView (obj): Django class for data entry

    Returns:
        form: cleaned form
    """

    # This make a form to enter in data
    model = Log
    fields = ["date", "hay_type", "direction", "amount", "horse_count", "notes"]

    def get_initial(self):
        # pre-populate the number of horse with the value from the latest log
        initial_data = super(LogCreate, self).get_initial()
        initial_data["horse_count"] = Log.objects.latest("date").horse_count
        return initial_data

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
    fields = ["date", "hay_type", "direction", "amount", "horse_count", "notes"]

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


def download_csv(request):
    """Return all Log entries as a CSV download (one row per log)."""
    # Query all logs ordered by date
    logs = Log.objects.all().order_by("date")

    # Create the HttpResponse with CSV header
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="hay_logs.csv"'

    writer = csv.writer(response)

    # Header row
    writer.writerow(
        [
            "id",
            "date",
            "amount",
            "hay_type",
            "direction",
            "horse_count",
            "balance_after_transaction",
            "notes",
        ]
    )

    # Data rows
    for log in logs:
        writer.writerow(
            [
                log.id,
                log.date.isoformat() if log.date else "",
                log.amount,
                log.hay_type.name if log.hay_type else "",
                log.direction,
                log.horse_count if log.horse_count is not None else "",
                log.balance_after_transaction if log.balance_after_transaction is not None else "",
                log.notes if log.notes else "",
            ]
        )

    return response
