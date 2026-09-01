from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    path('', views.attendance_dashboard_view, name='attendance_dashboard'),
    path('mark/', views.mark_attendance_view, name='mark_attendance'),
    path('mark/<int:course_pk>/', views.mark_course_attendance_view, name='mark_course_attendance'),
    path('history/', views.attendance_history_view, name='attendance_history'),
    path('reports/', views.attendance_report_view, name='attendance_report'),
    path('reports/course/<int:course_pk>/', views.course_attendance_report_view, name='course_attendance_report'),
    path('student/<int:student_pk>/', views.student_attendance_view, name='student_attendance'),
    path('edit/<int:pk>/', views.attendance_edit_view, name='attendance_edit'),
    path('delete/<int:pk>/', views.attendance_delete_view, name='attendance_delete'),
]
