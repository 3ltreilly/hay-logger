from django.conf import settings


def app_version(request):
    # makes {{ app_version }} available in every template
    return {"app_version": settings.APP_VERSION}
