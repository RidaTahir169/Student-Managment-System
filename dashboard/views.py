from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.shortcuts import render, redirect
from django.utils import timezone
from accounts.decorators import admin_required, teacher_required, student_required
from accounts.models import CustomUser
from students.models import Student
from teachers.models import Teacher
from courses.models import Course, Department, ClassRoom, AcademicSession, Enrollment
from attendance.models import Attendance
from academics.models import AcademicRecord


@login_required
def dashboard_index(request):
    """
    Landing router directing users to their respective role dashboard.
    """
    return redirect('accounts:role_redirect')


@admin_required
def admin_dashboard(request):
    """
    Administrator dashboard aggregating real-time analytics, KPI cards,
    recent admissions, attendance overview, and academic performance distribution.
    """
    # 1. High-Level KPI Counters
    total_students = Student.objects.count()
    total_teachers = Teacher.objects.count()
    total_courses = Course.objects.count()
    total_classes = ClassRoom.objects.count()
    total_departments = Department.objects.count()
    active_session = AcademicSession.objects.filter(is_current=True).first()

    # 2. Recent Student Admissions (Latest 5)
    recent_students = Student.objects.select_related('user', 'classroom').order_by('-id')[:5]

    # 3. Attendance Overview Analytics
    total_attendance = Attendance.objects.count()
    present_count = Attendance.objects.filter(status=Attendance.Status.PRESENT).count()
    absent_count = Attendance.objects.filter(status=Attendance.Status.ABSENT).count()
    late_count = Attendance.objects.filter(status=Attendance.Status.LATE).count()
    excused_count = Attendance.objects.filter(status=Attendance.Status.EXCUSED).count()
    
    attendance_rate = 0.0
    if total_attendance > 0:
        attendance_rate = round((present_count / total_attendance) * 100, 1)

    # 4. Academic Performance Summary
    total_academic_records = AcademicRecord.objects.count()
    avg_performance = AcademicRecord.objects.aggregate(
        avg_pct=Avg('percentage'),
        avg_gpa=Avg('grade_point')
    )
    avg_percentage = round(avg_performance['avg_pct'], 2) if avg_performance['avg_pct'] is not None else 0.00
    avg_gpa = round(avg_performance['avg_gpa'], 2) if avg_performance['avg_gpa'] is not None else 0.00

    # Grade Distribution
    grade_distribution = {
        'A_plus': AcademicRecord.objects.filter(grade='A+').count(),
        'A': AcademicRecord.objects.filter(grade='A').count(),
        'B': AcademicRecord.objects.filter(grade='B').count(),
        'C': AcademicRecord.objects.filter(grade='C').count(),
        'D': AcademicRecord.objects.filter(grade='D').count(),
        'F': AcademicRecord.objects.filter(grade='F').count(),
    }

    # Recent Exam / Grade Postings
    recent_grades = AcademicRecord.objects.select_related(
        'student__user',
        'course'
    ).order_by('-id')[:5]

    context = {
        # Core Counters
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_courses': total_courses,
        'total_classes': total_classes,
        'total_departments': total_departments,
        'active_session': active_session,
        
        # Recent Admissions
        'recent_students': recent_students,
        
        # Attendance Data
        'total_attendance': total_attendance,
        'present_count': present_count,
        'absent_count': absent_count,
        'late_count': late_count,
        'excused_count': excused_count,
        'attendance_rate': attendance_rate,
        
        # Academic Summary Data
        'total_academic_records': total_academic_records,
        'avg_percentage': avg_percentage,
        'avg_gpa': avg_gpa,
        'grade_distribution': grade_distribution,
        'recent_grades': recent_grades,
    }
    return render(request, 'dashboard/admin_dashboard.html', context)


@teacher_required
def teacher_dashboard(request):
    """
    Teacher dashboard displaying assigned courses, total enrolled students,
    pending attendance for today, recent assessment marks, and quick academic actions.
    """
    user = request.user
    teacher_profile = getattr(user, 'teacher_profile', None)
    today = timezone.now().date()

    assigned_courses_data = []
    total_students_enrolled = 0
    pending_attendance_count = 0
    pending_attendance_courses = []
    recent_marks = []
    total_marks_count = 0
    total_attendance_logs = 0

    if teacher_profile:
        # 1. Fetch courses assigned specifically to this teacher
        assigned_courses = Course.objects.filter(
            teacher=teacher_profile
        ).select_related('department', 'classroom').order_by('course_code')

        course_ids = list(assigned_courses.values_list('id', flat=True))

        # 2. Total distinct active students across all courses taught by this teacher
        total_students_enrolled = Enrollment.objects.filter(
            course_id__in=course_ids,
            status=Enrollment.EnrollmentStatus.ACTIVE
        ).values('student_id').distinct().count()

        # 3. Check today's attendance status and metrics for each assigned course
        for course in assigned_courses:
            is_marked_today = Attendance.objects.filter(course=course, date=today).exists()
            student_count = Enrollment.objects.filter(
                course=course,
                status=Enrollment.EnrollmentStatus.ACTIVE
            ).count()

            # Calculate course attendance rate
            course_logs = Attendance.objects.filter(course=course)
            total_logs = course_logs.count()
            present_logs = course_logs.filter(status=Attendance.Status.PRESENT).count()
            rate = round((present_logs / total_logs) * 100, 1) if total_logs > 0 else 0.0

            assigned_courses_data.append({
                'course': course,
                'is_marked_today': is_marked_today,
                'student_count': student_count,
                'attendance_rate': rate,
            })

            # Flag as pending if there are active students and today's roll call is missing
            if not is_marked_today and student_count > 0:
                pending_attendance_count += 1
                pending_attendance_courses.append(course)

        # 4. Recent assessment marks entered for this teacher's courses
        recent_marks = AcademicRecord.objects.filter(
            course_id__in=course_ids
        ).select_related('student__user', 'course').order_by('-date_recorded', '-id')[:6]

        total_marks_count = AcademicRecord.objects.filter(course_id__in=course_ids).count()
        total_attendance_logs = Attendance.objects.filter(course_id__in=course_ids).count()
    else:
        assigned_courses = []

    context = {
        'teacher_profile': teacher_profile,
        'assigned_courses_data': assigned_courses_data,
        'total_courses': len(assigned_courses_data),
        'total_students_enrolled': total_students_enrolled,
        'pending_attendance_count': pending_attendance_count,
        'pending_attendance_courses': pending_attendance_courses,
        'recent_marks': recent_marks,
        'total_marks_count': total_marks_count,
        'total_attendance_logs': total_attendance_logs,
        'today': today,
    }
    return render(request, 'dashboard/teacher_dashboard.html', context)


@student_required
def student_dashboard(request):
    """
    Student dashboard displaying personal profile summary, enrolled courses with
    per-course attendance rates, overall attendance metrics, recent marks, cumulative GPA,
    and recent attendance ledger history.
    """
    user = request.user
    student_profile = getattr(user, 'student_profile', None)
    today = timezone.now().date()

    enrolled_courses_data = []
    total_courses = 0
    total_attendance = 0
    present_count = 0
    absent_count = 0
    late_count = 0
    excused_count = 0
    attendance_pct = 0.0
    is_shortage = False
    recent_attendance_logs = []
    
    recent_marks = []
    total_academic_records = 0
    avg_percentage = 0.00
    cumulative_gpa = 0.00
    grade_counts = {'A_plus': 0, 'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}

    if student_profile:
        # 1. Enrolled Courses with Per-Course Attendance Breakdown
        enrollments = Enrollment.objects.filter(
            student=student_profile,
            status=Enrollment.EnrollmentStatus.ACTIVE
        ).select_related(
            'course__department',
            'course__classroom',
            'course__teacher__user'
        ).order_by('course__course_code')

        total_courses = enrollments.count()

        for enrollment in enrollments:
            c = enrollment.course
            total_course_classes = Attendance.objects.filter(course=c).values('date').distinct().count()
            c_records = Attendance.objects.filter(student=student_profile, course=c)
            c_present = c_records.filter(status=Attendance.Status.PRESENT).count()
            c_rate = round((c_present / total_course_classes) * 100, 1) if total_course_classes > 0 else 0.0

            # Latest mark for this course if any
            latest_mark = AcademicRecord.objects.filter(
                student=student_profile,
                course=c
            ).order_by('-date_recorded', '-id').first()

            enrolled_courses_data.append({
                'enrollment': enrollment,
                'course': c,
                'total_classes': total_course_classes,
                'present_count': c_present,
                'attendance_rate': c_rate,
                'latest_mark': latest_mark,
            })

        # 2. Overall Attendance Analytics
        student_attendance_qs = Attendance.objects.filter(student=student_profile)
        total_attendance = student_attendance_qs.count()
        present_count = student_attendance_qs.filter(status=Attendance.Status.PRESENT).count()
        absent_count = student_attendance_qs.filter(status=Attendance.Status.ABSENT).count()
        late_count = student_attendance_qs.filter(status=Attendance.Status.LATE).count()
        excused_count = student_attendance_qs.filter(status=Attendance.Status.EXCUSED).count()

        if total_attendance > 0:
            attendance_pct = round((present_count / total_attendance) * 100, 1)
            is_shortage = attendance_pct < 75.0

        # Recent 6 attendance log entries
        recent_attendance_logs = student_attendance_qs.select_related('course').order_by('-date', '-id')[:6]

        # 3. Academic Assessment Records & Cumulative Metrics
        all_records_qs = AcademicRecord.objects.filter(student=student_profile)
        total_academic_records = all_records_qs.count()

        if total_academic_records > 0:
            avg_metrics = all_records_qs.aggregate(
                avg_pct=Avg('percentage'),
                avg_gpa=Avg('grade_point')
            )
            avg_percentage = round(avg_metrics['avg_pct'], 2) if avg_metrics['avg_pct'] is not None else 0.00
            cumulative_gpa = round(avg_metrics['avg_gpa'], 2) if avg_metrics['avg_gpa'] is not None else 0.00

            grade_counts = {
                'A_plus': all_records_qs.filter(grade='A+').count(),
                'A': all_records_qs.filter(grade='A').count(),
                'B': all_records_qs.filter(grade='B').count(),
                'C': all_records_qs.filter(grade='C').count(),
                'D': all_records_qs.filter(grade='D').count(),
                'F': all_records_qs.filter(grade='F').count(),
            }

        recent_marks = all_records_qs.select_related(
            'course__teacher__user'
        ).order_by('-date_recorded', '-id')[:6]

    context = {
        'student_profile': student_profile,
        'enrolled_courses_data': enrolled_courses_data,
        'total_courses': total_courses,
        'total_attendance': total_attendance,
        'present_count': present_count,
        'absent_count': absent_count,
        'late_count': late_count,
        'excused_count': excused_count,
        'attendance_pct': attendance_pct,
        'is_shortage': is_shortage,
        'recent_attendance_logs': recent_attendance_logs,
        'recent_marks': recent_marks,
        'total_academic_records': total_academic_records,
        'avg_percentage': avg_percentage,
        'cumulative_gpa': cumulative_gpa,
        'grade_counts': grade_counts,
        'today': today,
    }
    return render(request, 'dashboard/student_dashboard.html', context)
