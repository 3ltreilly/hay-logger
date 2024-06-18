from django.contrib import admin

from log_app.models import Log, BailCount

# Register your models here.
admin.site.register(Log)
admin.site.register(BailCount)
