"""{{cookiecutter.project_name}} URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from rest_framework.documentation import include_docs_urls
from rest_framework.routers import DefaultRouter

# External application routers
# ie: from app.urls import router as app_router


from {{cookiecutter.project_slug}}.apps.user.urls import router as user_router
from {{cookiecutter.project_slug}}.apps.user.urls import urlpatterns as user_urls


class OptionalSlashDefaultRouter(DefaultRouter):
    """ Subclass of DefaultRouter to make the trailing slash optional """

    def __init__(self, *args, **kwargs):
        super(DefaultRouter, self).__init__(*args, **kwargs)
        self.trailing_slash = '/?'


# Create a router and register our viewsets with it.
router = OptionalSlashDefaultRouter()

# External workplace application
router.registry.extend(user_router.registry)

urlpatterns = [
    path('', include(user_urls)),
    path('', include(router.urls)),  # includes router generated URL
]
