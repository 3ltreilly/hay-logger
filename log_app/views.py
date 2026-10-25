import csv
import datetime
import json

import pytz
from django.db.models import Sum
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from .models import BaleCount, Log


# useful functions
def burn_rate(hay_type, days):
    # bales used per day over the `days` before the latest withdrawal; 0 if never used
    withdrawals = Log.objects.filter(hay_type__exact=hay_type, direction__exact="WITHDRAW")
    last_log = withdrawals.order_by("-date").first()
    if last_log is None:
        return 0

    start_date = last_log.date - datetime.timedelta(days)
    in_range = withdrawals.filter(date__range=(start_date, last_log.date))
    bale_count = in_range.aggregate(Sum("amount"))["amount__sum"] or 0

    return round(bale_count / days, 2)


class ListListView(ListView):
    model = Log
    template_name = "log_app/index.html"

    # redefine this method to add in the BaleCount object
    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        # one row per hay type for the summary table
        context["bale_count"] = [
            {"id": bale.id, "name": bale.name, "total": bale.current_total()}
            for bale in BaleCount.objects.all()
        ]
        for hay_type in context["bale_count"]:
            # get date of last log for empty date math
            try:
                last_log = (
                    Log.objects.filter(hay_type__exact=hay_type["id"])
                    .filter(direction__exact="WITHDRAW")
                    .latest("date")
                )
            except Log.DoesNotExist:
                continue
            hay_type["sixty"] = burn_rate(hay_type["id"], 60)
            hay_type["one_eight"] = burn_rate(hay_type["id"], 180)
            hay_type["one_year"] = burn_rate(hay_type["id"], 365)
            # too little usage to predict when the barn empties; the template shows a blank
            if hay_type["one_year"]:
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

        # use every log, not just the ones in the date range: the running total has to
        # start from the first log to be right on the first day shown
        logs = Log.objects.order_by("date").values("date", "hay_type__name", "direction", "amount")

        daily_changes = {}
        hay_types = []
        for entry in logs:
            # dates come back in UTC; group by the local day, like the date filter does
            day = timezone.localtime(entry["date"]).date().isoformat()
            hay_type_name = entry["hay_type__name"]
            change = entry["amount"] if entry["direction"] == "DEPOSIT" else -entry["amount"]

            if day not in daily_changes:
                daily_changes[day] = {}
            daily_changes[day][hay_type_name] = daily_changes[day].get(hay_type_name, 0) + change
            if hay_type_name not in hay_types:
                hay_types.append(hay_type_name)

        all_days = sorted(daily_changes.keys())
        running_totals = {hay_type: 0 for hay_type in hay_types}
        data_by_type = {hay_type: [] for hay_type in hay_types}

        for day in all_days:
            for hay_type in hay_types:
                running_totals[hay_type] += daily_changes[day].get(hay_type, 0)
                data_by_type[hay_type].append(running_totals[hay_type])

        # now trim to the requested range (ISO date strings sort the same as dates)
        in_range = [
            index
            for index, day in enumerate(all_days)
            if (not start_date or day >= start_date.isoformat())
            and (not end_date or day <= end_date.isoformat())
        ]
        labels = [all_days[index] for index in in_range]

        color_palette = [
            ("rgba(75, 192, 192, 1)", "rgba(75, 192, 192, 0.2)"),
            ("rgba(255, 99, 132, 1)", "rgba(255, 99, 132, 0.2)"),
            ("rgba(54, 162, 235, 1)", "rgba(54, 162, 235, 0.2)"),
        ]
        datasets = []
        for index, hay_type in enumerate(hay_types):
            border_color, background_color = color_palette[index % len(color_palette)]
            plot_data = [data_by_type[hay_type][index] for index in in_range]
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
    success_url = reverse_lazy("index")

    def get_initial(self):
        # pre-populate the number of horse with the value from the latest log
        initial_data = super(LogCreate, self).get_initial()
        try:
            initial_data["horse_count"] = Log.objects.latest("date").horse_count
        except Log.DoesNotExist:
            pass
        return initial_data


class LogEdit(UpdateView):
    model = Log
    fields = ["date", "hay_type", "direction", "amount", "horse_count", "notes"]
    success_url = reverse_lazy("index")


class LogView(ListView):
    model = Log


class LogDelete(DeleteView):
    model = Log
    success_url = reverse_lazy("index")


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
