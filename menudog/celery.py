from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Define o módulo de configurações do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'menudog.settings')

app = Celery('menudog')

# Carrega as configurações do Django para o Celery com prefixo 'CELERY_'
app.config_from_object('django.conf:settings', namespace='CELERY')

# Descobre e carrega tasks de todos os apps automaticamente
app.autodiscover_tasks()

