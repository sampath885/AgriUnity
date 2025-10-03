from django.urls import path
from . import views

app_name = 'locations'

urlpatterns = [
    path('pincode/<str:pincode>/', views.PincodeDetailView.as_view(), name='pincode-detail'),
]
