from django.urls import path

from . import views

app_name = "invitation_themes"

urlpatterns = [
    path("", views.design_studio, name="studio"),
    path("theme/<slug:theme_key>/use/", views.use_theme, name="use_theme"),
    path("customize/", views.customize_theme, name="customize"),
    path("hero/upload/", views.upload_hero_image, name="hero_upload"),
    path("hero/remove/", views.remove_hero_image, name="hero_remove"),
    path("hero/file/", views.draft_hero_image, name="hero_file"),
    path("sections/", views.save_sections, name="save_sections"),
    path("publish/", views.publish_design, name="publish"),
    path("preview/<slug:theme_key>/", views.preview_theme, name="preview"),
]
