from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    # Course URLs
    path('', views.course_list_view, name='course_list'),
    path('add/', views.course_create_view, name='course_create'),
    path('<int:pk>/', views.course_detail_view, name='course_detail'),
    path('<int:pk>/edit/', views.course_update_view, name='course_update'),
    path('<int:pk>/delete/', views.course_delete_view, name='course_delete'),
    path('<int:pk>/enroll-students/', views.course_enroll_students_view, name='course_enroll_students'),
    path('<int:course_pk>/unenroll/<int:student_pk>/', views.course_unenroll_student_view, name='course_unenroll_student'),

    # Class Room URLs
    path('classes/', views.classroom_list_view, name='classroom_list'),
    path('classes/add/', views.classroom_create_view, name='classroom_create'),
    path('classes/<int:pk>/', views.classroom_detail_view, name='classroom_detail'),
    path('classes/<int:pk>/edit/', views.classroom_update_view, name='classroom_update'),
    path('classes/<int:pk>/delete/', views.classroom_delete_view, name='classroom_delete'),
    path('classes/<int:pk>/assign-students/', views.classroom_assign_students_view, name='classroom_assign_students'),

    # Enrollment URLs (Phase 10)
    path('enrollments/', views.enrollment_list_view, name='enrollment_list'),
    path('enrollments/add/', views.enrollment_create_view, name='enrollment_create'),
    path('enrollments/<int:pk>/edit/', views.enrollment_update_view, name='enrollment_update'),
    path('enrollments/<int:pk>/delete/', views.enrollment_delete_view, name='enrollment_delete'),
]
