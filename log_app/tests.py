import datetime
import json

from django.test import TestCase
from django.urls import reverse

from .models import BailCount, Log


class UsageOverTimeViewTests(TestCase):
    def test_usage_over_time_can_be_filtered_by_date_range(self):
        first_bail = BailCount.objects.create(name="first", total=100)
        BailCount.objects.create(name="second", total=200)

        Log.objects.create(
            date=datetime.datetime(2024, 1, 1, 8, 0, 0),
            hay_type=first_bail,
            direction="DEPOSIT",
            amount=10,
        )
        Log.objects.create(
            date=datetime.datetime(2024, 1, 15, 8, 0, 0),
            hay_type=first_bail,
            direction="WITHDRAW",
            amount=5,
        )
        Log.objects.create(
            date=datetime.datetime(2024, 2, 1, 8, 0, 0),
            hay_type=first_bail,
            direction="WITHDRAW",
            amount=3,
        )
        Log.objects.create(
            date=datetime.datetime(2024, 2, 15, 8, 0, 0),
            hay_type=first_bail,
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
