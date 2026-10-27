"""Tests that expose known bugs.

The tests marked "BUG" fail with the current code; fix the code to make them pass.
The tests marked "SAFETY NET" pass now and should keep passing after your fixes.
"""

import datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from .models import BaleCount, Log


@pytest.fixture
def first_cutting(db):
    return BaleCount.objects.create(name="first", total=100)


def make_log(hay_type, direction, amount, days_ago=0):
    return Log.objects.create(
        date=timezone.now() - datetime.timedelta(days=days_ago),
        hay_type=hay_type,
        direction=direction,
        amount=amount,
        horse_count=3,
    )


# ---------------------------------------------------------------- BUG tests


@pytest.mark.django_db
def test_add_page_loads_with_empty_database(client):
    """BUG: LogCreate.get_initial assumes at least one Log exists."""
    response = client.get(reverse("log-add"))

    assert response.status_code == 200


def test_index_loads_when_hay_type_has_only_deposits(client, first_cutting):
    """BUG: a new hay type that has been delivered but not used yet crashes the index.

    burn_rate() and ListListView assume every hay type has at least one WITHDRAW log.
    """
    make_log(first_cutting, "DEPOSIT", 100, days_ago=1)

    response = client.get(reverse("index"))

    assert response.status_code == 200


def test_index_loads_with_very_low_usage(client, first_cutting):
    """BUG: one bale in a year rounds to a burn rate of 0.0, then the
    empty-barn-date math divides by it.
    """
    make_log(first_cutting, "DEPOSIT", 100, days_ago=30)
    make_log(first_cutting, "WITHDRAW", 1, days_ago=1)

    response = client.get(reverse("index"))

    assert response.status_code == 200


def test_new_log_default_date_is_timezone_aware():
    """BUG: USE_TZ is True, so the default date should be timezone aware.

    Hint: look at what `default=` is set to on Log.date.
    """
    log = Log()

    assert timezone.is_aware(log.date)


@pytest.mark.requirement("SRS001", "SRS002")
def test_invalid_edit_shows_form_errors(client, first_cutting):
    """BUG: submitting a bad value on the edit page should redisplay the form
    with an error message, not crash.

    Hint: compare the signature of LogEdit.get_context_data with the one in
    Django's UpdateView (https://ccbv.co.uk is handy for this).
    """
    log = make_log(first_cutting, "WITHDRAW", 5)

    response = client.post(
        reverse("log-edit", args=[log.pk]),
        {
            "date": "2024-01-01 08:00",
            "hay_type": first_cutting.pk,
            "direction": "WITHDRAW",
            "amount": 0,  # invalid: MinValueValidator(1)
        },
    )

    assert response.status_code == 200
    assert "amount" in response.context["form"].errors


# --------------------------------------------------------- SAFETY NET tests


def edit_log(client, log, **changes):
    data = {
        "date": "2024-01-01 08:00",
        "hay_type": log.hay_type.pk,
        "direction": log.direction,
        "amount": log.amount,
        "horse_count": log.horse_count,
        "notes": "",
    }
    data.update(changes)
    return client.post(reverse("log-edit", args=[log.pk]), data)


@pytest.mark.requirement("SRS001", "SRS004")
def test_adding_a_withdrawal_reduces_total(client, first_cutting):
    make_log(first_cutting, "DEPOSIT", 100, days_ago=10)
    client.post(
        reverse("log-add"),
        {
            "date": "2024-01-01 08:00",
            "hay_type": first_cutting.pk,
            "direction": "WITHDRAW",
            "amount": 7,
            "horse_count": 3,
        },
    )

    assert first_cutting.current_total() == 93


@pytest.mark.requirement("SRS002")
def test_editing_amount_adjusts_total(client, first_cutting):
    make_log(first_cutting, "DEPOSIT", 100, days_ago=10)
    log = make_log(first_cutting, "WITHDRAW", 5)

    edit_log(client, log, amount=8)

    assert first_cutting.current_total() == 92


@pytest.mark.requirement("SRS002")
def test_editing_hay_type_moves_amount_between_types(client, first_cutting):
    second_cutting = BaleCount.objects.create(name="second", total=200)
    make_log(first_cutting, "DEPOSIT", 100, days_ago=10)
    make_log(second_cutting, "DEPOSIT", 200, days_ago=10)
    log = make_log(first_cutting, "WITHDRAW", 5)

    edit_log(client, log, hay_type=second_cutting.pk)

    assert first_cutting.current_total() == 100
    assert second_cutting.current_total() == 195


@pytest.mark.requirement("SRS002")
def test_deleting_a_withdrawal_restores_total(client, first_cutting):
    make_log(first_cutting, "DEPOSIT", 100, days_ago=10)
    log = make_log(first_cutting, "WITHDRAW", 5)

    client.post(reverse("item-delete", args=[log.pk]))

    assert first_cutting.current_total() == 100
