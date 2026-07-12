from django.contrib import admin

from log_app.models import BailCount, Log

# Register your models here.
admin.site.register(Log)
admin.site.register(BailCount)
