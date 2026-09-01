from django.urls import path
from . import views

app_name = 'academics'

urlpatterns = [
    path('', views.record_list_view, name='record_list'),
    path('records/create/', views.record_create_view, name='record_create'),
    path('records/<int:pk>/edit/', views.record_update_view, name='record_update'),
    path('records/<int:pk>/delete/', views.record_delete_view, name='record_delete'),
    path('course/<int:course_pk>/', views.course_gradebook_view, name='course_gradebook'),
    path('student/<int:student_pk>/', views.student_report_card_view, name='student_report_card'),
    path('reports/', views.academic_reports_view, name='academic_reports'),
]
