from django.contrib import admin
from django.apps import apps

for model in apps.get_app_config('duties').get_models():
    admin.site.register(model)
