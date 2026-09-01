from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_index, name='index'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('teacher-dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('student-dashboard/', views.student_dashboard, name='student_dashboard'),
    # URL aliases to support alternative path conventions
    path('admin/dashboard/', views.admin_dashboard),
    path('teacher/dashboard/', views.teacher_dashboard),
    path('student/dashboard/', views.student_dashboard),
    path('dashboard/admin/', views.admin_dashboard),
    path('dashboard/teacher/', views.teacher_dashboard),
    path('dashboard/student/', views.student_dashboard),
]
