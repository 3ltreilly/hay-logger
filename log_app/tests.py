import datetime
import importlib
import json

import pytest
from django.apps import apps
from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import BaleCount, Log


class UsageOverTimeViewTests(TestCase):
    @pytest.mark.requirement("HIST002")
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

    @pytest.mark.requirement("HIST001", "HIST002")
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


class BalanceCorrectionMigrationTests(TestCase):
    # remove this along with the BaleCount.total field: it runs the migration's function
    # against today's models, which only works while they still have `total`
    def test_correction_logs_make_totals_match_the_old_stored_totals(self):
        migration = importlib.import_module("log_app.migrations.0011_balance_corrections")
        first = BaleCount.objects.create(name="first", total=120)  # logs say 100
        second = BaleCount.objects.create(name="second", total=40)  # logs say 50
        third = BaleCount.objects.create(name="third", total=0)  # logs agree
        start = timezone.make_aware(datetime.datetime(2020, 1, 1, 8, 0, 0))
        for hay_type, direction, amount in [
            (first, "DEPOSIT", 100),
            (second, "DEPOSIT", 60),
            (second, "WITHDRAW", 10),
        ]:
            Log.objects.create(date=start, hay_type=hay_type, direction=direction, amount=amount)

        migration.add_corrections(apps, None)

        self.assertEqual(first.current_total(), 120)
        self.assertEqual(second.current_total(), 40)
        self.assertEqual(third.current_total(), 0)
        corrections = Log.objects.filter(notes=migration.NOTE)
        self.assertEqual(corrections.count(), 2)
        self.assertTrue(all(log.date == start for log in corrections))

        migration.remove_corrections(apps, None)

        self.assertEqual(first.current_total(), 100)
