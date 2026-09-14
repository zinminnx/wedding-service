from django.test import TestCase

from .models import FeatureModule


class FeatureModuleModelTests(TestCase):
    def test_core_module_forces_system_enabled(self):
        module = FeatureModule.objects.create(
            key="test-core",
            name="Test Core",
            module_type=FeatureModule.ModuleType.CORE,
            system_enabled=False,
        )
        self.assertTrue(module.system_enabled)
