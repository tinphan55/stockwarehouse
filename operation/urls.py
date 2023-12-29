from django.urls import path
from .views import *


urlpatterns = [
    path('warehouse', warehouse, name='warehouse'),
    path('customer/<int:pk>', customer_view, name='customerview'),
   
]