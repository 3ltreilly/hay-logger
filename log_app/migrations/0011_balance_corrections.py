"""Data migration: add one "balance correction" log per hay type.

The historic stored totals (BaleCount.total) don't match the sum of the logs. After this
migration they do, so the total can be calculated from the logs alone. Each correction is
dated at that hay type's first log, so it shifts the whole history the same way the usage
chart's old offset did.
"""

from django.db import migrations
from django.db.models import Min, Q, Sum
from django.utils import timezone

NOTE = "Balance correction: matches the logs to the old stored total"


def add_corrections(apps, schema_editor):
    # historical models: the models as they were at this migration, not today's models.py
    BaleCount = apps.get_model("log_app", "BaleCount")
    Log = apps.get_model("log_app", "Log")

    for hay_type in BaleCount.objects.all():
        sums = Log.objects.filter(hay_type=hay_type).aggregate(
            deposits=Sum("amount", filter=Q(direction="DEPOSIT"), default=0),
            withdrawals=Sum("amount", filter=Q(direction="WITHDRAW"), default=0),
            first_date=Min("date"),
        )
        offset = hay_type.total - (sums["deposits"] - sums["withdrawals"])
        if offset == 0:
            continue

        Log.objects.create(
            date=sums["first_date"] or timezone.now(),
            hay_type=hay_type,
            direction="DEPOSIT" if offset > 0 else "WITHDRAW",
            amount=abs(offset),
            notes=NOTE,
        )


def remove_corrections(apps, schema_editor):
    Log = apps.get_model("log_app", "Log")
    Log.objects.filter(notes=NOTE).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("log_app", "0010_alter_log_date"),
    ]

    operations = [
        migrations.RunPython(add_corrections, remove_corrections),
    ]
