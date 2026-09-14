from django.urls import path

from . import views

app_name = "invitation_themes"

urlpatterns = [
    path("", views.design_studio, name="studio"),
    path("theme/<slug:theme_key>/use/", views.use_theme, name="use_theme"),
    path("customize/", views.customize_theme, name="customize"),
    path("sections/", views.save_sections, name="save_sections"),
    path("publish/", views.publish_design, name="publish"),
    path("preview/<slug:theme_key>/", views.preview_theme, name="preview"),
]
