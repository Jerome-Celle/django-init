from django.contrib import admin

from {{cookiecutter.project_slug}}.apps.user.models import User, ActionToken

admin.site.register(User)
admin.site.register(ActionToken)
