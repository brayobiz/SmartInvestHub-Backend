from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, include

def home(request):
    return HttpResponse("SmartInvestHub Backend is running!")
    
urlpatterns = [
  path('', home, name= 'home'),
    path('admin/', admin.site.urls),
    path('', include('core.urls')), 
]