"""Behaviour tests: what the pages show, not how the totals are stored.

These should pass unchanged before and after moving from the stored `BaleCount.total` to
totals calculated from the logs. To keep them that way:
- every setup keeps the stored total and the logs in agreement, and
- totals are read from the index page (see `index_row`), not from the database column.
"""

import csv
import datetime
import io
import json

import pytest
from django.urls import reverse
from django.utils import timezone

from .models import BaleCount, Log


@pytest.fixture
def barn(db):
    """First cutting with 100 bales: stored total and logs agree."""
    first_cutting = BaleCount.objects.create(name="first", total=100)
    make_log(first_cutting, "DEPOSIT", 100, days_ago=400)
    return first_cutting


def make_log(hay_type, direction, amount, days_ago=0):
    return Log.objects.create(
        date=timezone.now() - datetime.timedelta(days=days_ago),
        hay_type=hay_type,
        direction=direction,
        amount=amount,
        horse_count=3,
    )


def add_log(client, hay_type, direction, amount):
    """Add a log through the Add page, the way the phone form does."""
    client.post(
        reverse("log-add"),
        {
            "date": "2024-01-01 08:00",
            "hay_type": hay_type.pk,
            "direction": direction,
            "amount": amount,
            "horse_count": 3,
        },
    )
    return Log.objects.latest("id")


def index_row(client, name):
    """The dashboard row for one hay type. If the index context changes shape, fix it here."""
    response = client.get(reverse("index"))
    return next(row for row in response.context["bale_count"] if row["name"] == name)


def index_total(client, name):
    return index_row(client, name)["total"]


# ---------------------------------------------------------------- totals


@pytest.mark.requirement("LOG001", "DASH001")
def test_adding_a_deposit_raises_total(client, barn):
    add_log(client, barn, "DEPOSIT", 20)

    assert index_total(client, "first") == 120


@pytest.mark.requirement("LOG002")
def test_editing_a_withdrawal_into_a_deposit(client, barn):
    log = add_log(client, barn, "WITHDRAW", 5)
    assert index_total(client, "first") == 95

    client.post(
        reverse("log-edit", args=[log.pk]),
        {
            "date": "2024-01-01 08:00",
            "hay_type": barn.pk,
            "direction": "DEPOSIT",
            "amount": 5,
            "horse_count": 3,
            "notes": "",
        },
    )

    assert index_total(client, "first") == 105


@pytest.mark.requirement("LOG002")
def test_deleting_a_deposit_lowers_total(client, barn):
    log = add_log(client, barn, "DEPOSIT", 20)

    client.post(reverse("item-delete", args=[log.pk]))

    assert index_total(client, "first") == 100


# ---------------------------------------------------------------- dashboard numbers


@pytest.mark.requirement("DASH001", "DASH002", "DASH003", "DASH004")
def test_dashboard_burn_rates_and_empty_date(client, db):
    # 1000 delivered, 365 used in the last year (120 of them in the last 60 days): 635 left
    first_cutting = BaleCount.objects.create(name="first", total=635)
    make_log(first_cutting, "DEPOSIT", 1000, days_ago=400)
    make_log(first_cutting, "WITHDRAW", 245, days_ago=200)
    last_withdrawal = make_log(first_cutting, "WITHDRAW", 120, days_ago=1)

    row = index_row(client, "first")

    assert row["total"] == 635
    assert row["sixty"] == 2.0  # 120 bales / 60 days
    assert row["one_year"] == 1.0  # 365 bales / 365 days
    # 635 bales at 1 bale a day, counted from the last withdrawal
    assert row["empty_date"] == (last_withdrawal.date + datetime.timedelta(days=635)).date()
    assert row["throw_down"] == 1  # 1 day since the last withdrawal at 1 bale a day


# ---------------------------------------------------------------- chart


@pytest.mark.requirement("HIST001")
def test_chart_ends_at_the_dashboard_total(client, barn):
    second_cutting = BaleCount.objects.create(name="second", total=50)
    make_log(second_cutting, "DEPOSIT", 80, days_ago=300)
    make_log(second_cutting, "WITHDRAW", 30, days_ago=10)
    add_log(client, barn, "WITHDRAW", 7)

    response = client.get(reverse("usage-over-time"))
    datasets = json.loads(response.context["usage_datasets"])
    last_points = {dataset["label"]: dataset["data"][-1] for dataset in datasets}

    assert last_points == {
        "First": index_total(client, "first"),
        "Second": index_total(client, "second"),
    }
    assert last_points == {"First": 93, "Second": 50}


# ---------------------------------------------------------------- smoke


@pytest.mark.parametrize(
    "url_name, needs_pk",
    [
        ("log-view", False),
        ("log-edit", True),
        ("item-delete", True),
        ("usage-over-time", False),
    ],
)
def test_pages_load(client, barn, url_name, needs_pk):
    args = [Log.objects.first().pk] if needs_pk else []

    response = client.get(reverse(url_name, args=args))

    assert response.status_code == 200


@pytest.mark.requirement("HIST003")
def test_csv_download_has_one_row_per_log(client, barn):
    make_log(barn, "WITHDRAW", 5)

    response = client.get(reverse("download-csv"))
    rows = list(csv.reader(io.StringIO(response.content.decode())))

    assert rows[0][:3] == ["id", "date", "amount"]
    assert len(rows) == 1 + Log.objects.count()
