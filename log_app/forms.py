from django import forms

from .models import Log


class LogForm(forms.ModelForm):
    class Meta:
        model = Log
        fields = ["date", "hay_type", "direction", "amount", "horse_count", "notes"]
        widgets = {
            # type="datetime-local" makes phones open their own date and time picker; the
            # browser only accepts a value in this ISO format (no seconds shown)
            "date": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }
