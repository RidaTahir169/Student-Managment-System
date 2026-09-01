"""
URL configuration for Student Management System project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from accounts import views as account_views
from dashboard import views as dashboard_views

urlpatterns = [
    path('admin/dashboard/', dashboard_views.admin_dashboard),
    path('admin/', admin.site.urls),
    path('register/', account_views.register_view, name='root_register'),
    path('login/', account_views.login_view, name='root_login'),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('students/', include('students.urls', namespace='students')),
    path('teachers/', include('teachers.urls', namespace='teachers')),
    path('courses/', include('courses.urls', namespace='courses')),
    path('attendance/', include('attendance.urls', namespace='attendance')),
    path('academics/', include('academics.urls', namespace='academics')),
    path('', include('dashboard.urls', namespace='dashboard')),
]

# Custom HTTP Error Handlers for Role-Based Access Control & System Reliability
handler403 = 'accounts.views.permission_denied_view'
handler404 = 'accounts.views.page_not_found_view'
handler500 = 'accounts.views.server_error_view'

# Serve media and static files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

