from django.urls import path
from . import views

# use the 'name' as a way of referencing these paths.  for example
# reverse("log-add") will return the full url for adding a log

urlpatterns = [
    path("", views.ListListView.as_view(), name="index"),
    path("add/", views.LogCreate.as_view(), name="log-add"),
    path("log/", views.LogView.as_view(), name="log-view"),
    path("log/<int:pk>/", views.LogEdit.as_view(), name="log-edit"),
    path(
        "log/<int:pk>/delete/",
        views.LogDelete.as_view(),
        name="item-delete",
    ),
]
