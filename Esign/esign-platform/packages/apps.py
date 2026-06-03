from django.apps import AppConfig


class PackagesConfig(AppConfig):
    name = 'packages'

    def ready(self):
        import packages.signals  # noqa: F401