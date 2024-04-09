from django.apps import AppConfig

class JobManagerSignalConfig(AppConfig):
    name = 'hydra.jobmanager.signals_app'

    def ready(self):
        from . import signals
        