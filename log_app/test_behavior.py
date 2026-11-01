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
import zoneinfo

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


# ---------------------------------------------------------------- add form


@pytest.mark.requirement("LOG003")
def test_add_form_prefills_horse_count_from_latest_log(client, barn):
    # barn's delivery (400 days ago) had 3 horses; a newer log says there are 5 now
    Log.objects.create(
        date=timezone.now() - datetime.timedelta(days=1),
        hay_type=barn,
        direction="WITHDRAW",
        amount=10,
        horse_count=5,
    )

    response = client.get(reverse("log-add"))

    assert response.context["form"].initial["horse_count"] == 5


@pytest.mark.requirement("LOG003")
def test_add_form_horse_count_starts_empty_with_no_logs(client, db):
    response = client.get(reverse("log-add"))

    assert "horse_count" not in response.context["form"].initial


NEW_YORK = zoneinfo.ZoneInfo("America/New_York")


def date_input(response):
    """The date field's <input> HTML, as the phone's browser receives it."""
    return str(response.context["form"]["date"])


def edit_form_data(log, date):
    return {
        "date": date,
        "hay_type": log.hay_type.pk,
        "direction": log.direction,
        "amount": log.amount,
        "horse_count": log.horse_count,
        "notes": log.notes or "",
    }


@pytest.mark.requirement("LOG004")
def test_add_form_date_is_a_date_and_time_picker(client, barn):
    response = client.get(reverse("log-add"))

    assert 'type="datetime-local"' in date_input(response)


@pytest.mark.requirement("LOG004")
def test_add_form_date_starts_at_current_time(client, barn):
    # the minute may tick over during the request, so either side of it is fine
    before = timezone.localtime().strftime("%Y-%m-%dT%H:%M")
    response = client.get(reverse("log-add"))
    after = timezone.localtime().strftime("%Y-%m-%dT%H:%M")

    html = date_input(response)
    assert f'value="{before}"' in html or f'value="{after}"' in html


@pytest.mark.requirement("LOG004")
def test_edit_form_date_starts_at_saved_date(client, barn):
    log = make_log(barn, "WITHDRAW", 5)
    log.date = datetime.datetime(2024, 3, 10, 8, 30, tzinfo=NEW_YORK)
    log.save()

    html = date_input(client.get(reverse("log-edit", args=[log.pk])))

    assert 'type="datetime-local"' in html
    assert 'value="2024-03-10T08:30"' in html


@pytest.mark.requirement("LOG004")
def test_saving_edit_form_unchanged_keeps_date(client, barn):
    log = make_log(barn, "WITHDRAW", 5)
    log.date = datetime.datetime(2024, 3, 10, 8, 30, tzinfo=NEW_YORK)
    log.save()

    client.post(reverse("log-edit", args=[log.pk]), edit_form_data(log, "2024-03-10T08:30"))

    log.refresh_from_db()
    # 10 March 2024 is the first day of daylight saving time: 08:30 EDT is 12:30 UTC
    assert log.date == datetime.datetime(2024, 3, 10, 12, 30, tzinfo=datetime.UTC)


@pytest.mark.requirement("LOG004")
def test_add_form_rejects_empty_date(client, barn):
    logs_before = Log.objects.count()

    response = client.post(
        reverse("log-add"),
        {"date": "", "hay_type": barn.pk, "direction": "DEPOSIT", "amount": 5, "horse_count": 3},
    )

    assert Log.objects.count() == logs_before
    assert response.context["form"].errors["date"]


@pytest.mark.requirement("LOG004")
def test_edit_form_date_drops_seconds(client, barn):
    log = make_log(barn, "WITHDRAW", 5)
    log.date = datetime.datetime(2024, 3, 10, 8, 30, 45, tzinfo=NEW_YORK)
    log.save()

    html = date_input(client.get(reverse("log-edit", args=[log.pk])))
    assert 'value="2024-03-10T08:30"' in html

    client.post(reverse("log-edit", args=[log.pk]), edit_form_data(log, "2024-03-10T08:30"))
    log.refresh_from_db()
    assert log.date.astimezone(NEW_YORK).time() == datetime.time(8, 30, 0)


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
