from datetime import datetime
from django.db import models
from django.urls import reverse
from django.core.validators import MinValueValidator


# Create your models here.
class BailCount(models.Model):
    name = models.CharField(max_length=20, help_text="Type of cutting", default="first")
    total = models.IntegerField()

    def __str__(self):
        """String for representing the Model object."""
        return str(self.name)


class Log(models.Model):
    date = models.DateTimeField(default=datetime.now)
    hay_type = models.ForeignKey(
        "BailCount",
        on_delete=models.RESTRICT,
        help_text="What type of cutting?",
        default=False,
    )
    direction = models.CharField(
        max_length=12,
        choices=(("WITHDRAW", "Withdraw"), ("DEPOSIT", "Deposit")),
        blank=False,
        default="WITHDRAW",
        help_text="Is hay coming or going?",
    )
    amount = models.IntegerField(default=20, validators=[MinValueValidator(1)])
    notes = models.CharField(
        max_length=200, help_text="general notes", null=True, blank=True
    )
    balance_after_transaction = models.IntegerField(blank=True, null=True)

    def get_absolute_url(self):
        return reverse("log-edit", args=[self.id])

    def __str__(self):
        """String for representing the Model object."""
        return "log_" + str(self.date)

    class Meta:
        ordering = ["date"]
