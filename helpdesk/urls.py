from django.urls import path
from helpdesk import views

urlpatterns = [
    path('', views.index, name='helpdesk_index'),
]
