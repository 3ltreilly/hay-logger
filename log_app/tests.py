import datetime
import json

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import BaleCount, Log


class UsageOverTimeViewTests(TestCase):
    def test_usage_over_time_can_be_filtered_by_date_range(self):
        first_bale = BaleCount.objects.create(name="first", total=100)
        BaleCount.objects.create(name="second", total=200)

        Log.objects.create(
            date=datetime.datetime(2024, 1, 1, 8, 0, 0),
            hay_type=first_bale,
            direction="DEPOSIT",
            amount=10,
        )
        Log.objects.create(
            date=datetime.datetime(2024, 1, 15, 8, 0, 0),
            hay_type=first_bale,
            direction="WITHDRAW",
            amount=5,
        )
        Log.objects.create(
            date=datetime.datetime(2024, 2, 1, 8, 0, 0),
            hay_type=first_bale,
            direction="WITHDRAW",
            amount=3,
        )
        Log.objects.create(
            date=datetime.datetime(2024, 2, 15, 8, 0, 0),
            hay_type=first_bale,
            direction="WITHDRAW",
            amount=2,
        )

        response = self.client.get(
            reverse("usage-over-time"),
            {"start_date": "2024-01-15", "end_date": "2024-02-01"},
        )

        self.assertEqual(response.status_code, 200)
        labels = json.loads(response.context["usage_labels"])
        self.assertEqual(labels, ["2024-01-15", "2024-02-01"])
        self.assertEqual(response.context["start_date"], "2024-01-15")
        self.assertEqual(response.context["end_date"], "2024-02-01")

    def test_end_date_shows_balance_on_that_date_not_today(self):
        # 100 delivered, 10 used, then 50 used after the end date: the barn now holds 40
        first_bale = BaleCount.objects.create(name="first", total=40)
        for day, direction, amount in [
            (1, "DEPOSIT", 100),
            (10, "WITHDRAW", 10),
            (20, "WITHDRAW", 50),
        ]:
            Log.objects.create(
                date=timezone.make_aware(datetime.datetime(2024, 1, day, 8, 0, 0)),
                hay_type=first_bale,
                direction=direction,
                amount=amount,
            )

        response = self.client.get(reverse("usage-over-time"), {"end_date": "2024-01-15"})

        datasets = json.loads(response.context["usage_datasets"])
        self.assertEqual(json.loads(response.context["usage_labels"]), ["2024-01-01", "2024-01-10"])
        self.assertEqual(datasets[0]["data"], [100, 90])


class AppVersionTests(TestCase):
    def test_version_is_shown_in_footer(self):
        response = self.client.get(reverse("index"))

        self.assertContains(response, f"v{settings.APP_VERSION}")
