from django.contrib import admin

from log_app.models import BaleCount, Log

# Register your models here.
admin.site.register(Log)
admin.site.register(BaleCount)
