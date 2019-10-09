from django.conf.urls import url
from .views import InitialInfo


urlpatterns = [
        url(r'^init_info/', InitialInfo.as_view()),
        ]
