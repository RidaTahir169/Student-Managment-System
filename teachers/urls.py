from django.urls import path
from . import views

app_name = 'teachers'

urlpatterns = [
    path('', views.teacher_list_view, name='teacher_list'),
    path('add/', views.teacher_create_view, name='teacher_create'),
    path('<int:pk>/', views.teacher_detail_view, name='teacher_detail'),
    path('<int:pk>/edit/', views.teacher_update_view, name='teacher_update'),
    path('<int:pk>/delete/', views.teacher_delete_view, name='teacher_delete'),
    path('<int:pk>/assign-courses/', views.teacher_assign_courses_view, name='teacher_assign_courses'),
    path('<int:teacher_pk>/unassign-course/<int:course_pk>/', views.teacher_unassign_course_view, name='teacher_unassign_course'),
]
