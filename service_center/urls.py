from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.repairs.urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('analytics/', include('apps.analytics.urls')),
]
