from django.urls import path

from . import views

app_name = "modules"

urlpatterns = [
    path("", views.wedding_modules, name="wedding_modules"),
    path("<slug:module_key>/toggle/", views.toggle_wedding_module, name="toggle"),
]
