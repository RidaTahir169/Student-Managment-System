from django.urls import path
from . import views

app_name = 'students'

urlpatterns = [
    path('', views.student_list_view, name='student_list'),
    path('add/', views.student_create_view, name='student_create'),
    path('<int:pk>/', views.student_detail_view, name='student_detail'),
    path('<int:pk>/edit/', views.student_update_view, name='student_update'),
    path('<int:pk>/delete/', views.student_delete_view, name='student_delete'),
    path('<int:pk>/enroll/', views.student_enroll_courses_view, name='student_enroll_courses'),
]
