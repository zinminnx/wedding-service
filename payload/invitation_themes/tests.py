from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import InvitationTheme, REQUIRED_THEME_SECTIONS


class InvitationThemeModelTests(TestCase):
    def test_published_theme_requires_core_section_compatibility(self):
        theme = InvitationTheme(
            name="Incomplete",
            key="incomplete-theme",
            status=InvitationTheme.Status.PUBLISHED,
            visible=True,
            supported_sections=["hero", "event"],
            config={"accent": "#B98A45"},
        )
        with self.assertRaises(ValidationError):
            theme.full_clean()

    def test_complete_published_theme_is_valid(self):
        theme = InvitationTheme(
            name="Complete",
            key="complete-theme",
            status=InvitationTheme.Status.PUBLISHED,
            visible=True,
            supported_sections=sorted(REQUIRED_THEME_SECTIONS),
            config={"accent": "#B98A45"},
        )
        theme.full_clean()
