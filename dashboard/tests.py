from datetime import date
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import CustomUser
from students.models import Student
from teachers.models import Teacher
from courses.models import Department, AcademicSession, ClassRoom, Course, Enrollment
from attendance.models import Attendance
from academics.models import AcademicRecord


class AdminDashboardTests(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Create Administrator User
        self.admin_user = CustomUser.objects.create_user(
            username='admin_boss',
            email='boss@sms.local',
            password='AdminPassword123!',
            role=CustomUser.Role.ADMIN
        )

        # 2. Create Departments, Sessions, Classes
        self.dept = Department.objects.create(name='Computer Science', code='CS')
        self.session = AcademicSession.objects.create(
            name='2025-2026',
            start_date='2025-09-01',
            end_date='2026-06-30',
            is_current=True
        )
        self.classroom = ClassRoom.objects.create(name='Grade 10', section='A', department=self.dept)

        # 3. Create Teacher & Student
        self.t_user = CustomUser.objects.create_user('prof_doe', 'doe@sms.local', 'Pass123!', role='TEACHER')
        self.teacher = Teacher.objects.create(user=self.t_user, employee_id='FAC-100', department=self.dept)

        self.s_user = CustomUser.objects.create_user('alice_smith', 'alice@sms.local', 'Pass123!', role='STUDENT')
        self.student = Student.objects.create(user=self.s_user, admission_number='ADM-100', classroom=self.classroom)

        # 4. Create Course & Enrollment
        self.course = Course.objects.create(
            course_code='CS101',
            title='Intro to CS',
            credit_hours=3,
            department=self.dept,
            teacher=self.teacher,
            classroom=self.classroom,
            session=self.session
        )
        self.enrollment = Enrollment.objects.create(student=self.student, course=self.course)

        # 5. Create Attendance Records with distinct dates (1 Present, 1 Absent = 50% rate)
        Attendance.objects.create(
            student=self.student,
            course=self.course,
            date=date(2026, 1, 10),
            status=Attendance.Status.PRESENT
        )
        Attendance.objects.create(
            student=self.student,
            course=self.course,
            date=date(2026, 1, 11),
            status=Attendance.Status.ABSENT
        )

        # 6. Create Academic Record (85% -> Grade A, 3.75 GPA)
        self.record = AcademicRecord.objects.create(
            student=self.student,
            course=self.course,
            exam_name='Midterm',
            marks_obtained=Decimal('85.00'),
            total_marks=Decimal('100.00')
        )

    def test_admin_dashboard_requires_authentication(self):
        """Unauthenticated user is redirected to login."""
        response = self.client.get(reverse('dashboard:admin_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_admin_dashboard_dynamic_metrics_computation(self):
        """Admin dashboard computes counts, attendance rate, and GPA dynamically."""
        self.client.login(username='admin_boss', password='AdminPassword123!')
        response = self.client.get(reverse('dashboard:admin_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/admin_dashboard.html')

        # Check Context Variables
        self.assertEqual(response.context['total_students'], 1)
        self.assertEqual(response.context['total_teachers'], 1)
        self.assertEqual(response.context['total_courses'], 1)
        self.assertEqual(response.context['total_classes'], 1)
        self.assertEqual(response.context['total_departments'], 1)
        self.assertEqual(response.context['active_session'].name, '2025-2026')

        # Attendance verification (1 present / 2 total = 50.0%)
        self.assertEqual(response.context['total_attendance'], 2)
        self.assertEqual(response.context['present_count'], 1)
        self.assertEqual(response.context['absent_count'], 1)
        self.assertEqual(response.context['attendance_rate'], 50.0)

        # Academic summary verification (85.00% avg, 3.75 GPA, 1 Grade A)
        self.assertEqual(response.context['avg_percentage'], 85.00)
        self.assertEqual(response.context['avg_gpa'], 3.75)
        self.assertEqual(response.context['grade_distribution']['A'], 1)


class TeacherDashboardTests(TestCase):
    """
    Comprehensive test suite for Phase 13: Teacher Dashboard.
    Tests teacher data scoping, assigned courses, student counts,
    pending attendance calculation, recent marks, and access control.
    """

    def setUp(self):
        self.client = Client()

        self.dept = Department.objects.create(name='Computer Science', code='CS')
        self.classroom = ClassRoom.objects.create(name='CS-101', section='A', department=self.dept)

        # Teacher 1
        self.t1_user = CustomUser.objects.create_user(
            username='prof_smith',
            email='smith@sms.local',
            password='Password123!',
            role=CustomUser.Role.TEACHER,
            first_name='John',
            last_name='Smith'
        )
        self.teacher_1 = Teacher.objects.create(
            user=self.t1_user,
            employee_id='FAC-101',
            department=self.dept,
            designation='Associate Professor'
        )

        # Teacher 2 (Other teacher)
        self.t2_user = CustomUser.objects.create_user(
            username='prof_jones',
            email='jones@sms.local',
            password='Password123!',
            role=CustomUser.Role.TEACHER,
            first_name='David',
            last_name='Jones'
        )
        self.teacher_2 = Teacher.objects.create(
            user=self.t2_user,
            employee_id='FAC-102',
            department=self.dept,
            designation='Lecturer'
        )

        # Students
        self.s1_user = CustomUser.objects.create_user('alice_w', 'alice@sms.local', 'Pass123!', role='STUDENT', first_name='Alice', last_name='Walker')
        self.student_1 = Student.objects.create(user=self.s1_user, admission_number='ADM-201', classroom=self.classroom)

        self.s2_user = CustomUser.objects.create_user('bob_t', 'bob@sms.local', 'Pass123!', role='STUDENT', first_name='Bob', last_name='Taylor')
        self.student_2 = Student.objects.create(user=self.s2_user, admission_number='ADM-202', classroom=self.classroom)

        # Courses
        # Course 1 taught by Teacher 1
        self.course_1 = Course.objects.create(
            course_code='CS201',
            title='Data Structures',
            credit_hours=3,
            department=self.dept,
            teacher=self.teacher_1,
            classroom=self.classroom
        )
        # Course 2 taught by Teacher 2
        self.course_2 = Course.objects.create(
            course_code='CS202',
            title='Database Systems',
            credit_hours=3,
            department=self.dept,
            teacher=self.teacher_2,
            classroom=self.classroom
        )

        # Enrollments
        Enrollment.objects.create(student=self.student_1, course=self.course_1, status=Enrollment.EnrollmentStatus.ACTIVE)
        Enrollment.objects.create(student=self.student_2, course=self.course_1, status=Enrollment.EnrollmentStatus.ACTIVE)
        Enrollment.objects.create(student=self.student_1, course=self.course_2, status=Enrollment.EnrollmentStatus.ACTIVE)

        # Academic marks
        self.mark_1 = AcademicRecord.objects.create(
            student=self.student_1,
            course=self.course_1,
            exam_name='Quiz 1',
            marks_obtained=Decimal('90.00'),
            total_marks=Decimal('100.00')
        )
        self.mark_2 = AcademicRecord.objects.create(
            student=self.student_1,
            course=self.course_2,
            exam_name='Quiz 1',
            marks_obtained=Decimal('70.00'),
            total_marks=Decimal('100.00')
        )

    def test_teacher_dashboard_access_control(self):
        """Unauthenticated user is redirected; student is redirected; teacher gains access."""
        # Unauthenticated
        response = self.client.get(reverse('dashboard:teacher_dashboard'))
        self.assertEqual(response.status_code, 302)

        # Student user -> Redirected (role protection)
        self.client.login(username='alice_w', password='Password123!')
        response = self.client.get(reverse('dashboard:teacher_dashboard'))
        self.assertEqual(response.status_code, 302)

        # Teacher user -> 200 OK
        self.client.login(username='prof_smith', password='Password123!')
        response = self.client.get(reverse('dashboard:teacher_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/teacher_dashboard.html')

    def test_teacher_dashboard_scoped_to_assigned_courses(self):
        """Teacher only sees courses assigned to them, not other teachers' courses."""
        self.client.login(username='prof_smith', password='Password123!')
        response = self.client.get(reverse('dashboard:teacher_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_courses'], 1)
        self.assertEqual(response.context['total_students_enrolled'], 2)

        # Contains CS201, does not contain CS202
        self.assertContains(response, 'CS201')
        self.assertContains(response, 'Data Structures')
        self.assertNotContains(response, 'CS202')
        self.assertNotContains(response, 'Database Systems')

    def test_teacher_dashboard_pending_attendance_tracking(self):
        """
        Before marking attendance for today, pending_attendance_count is 1.
        After marking attendance for today, pending_attendance_count becomes 0.
        """
        self.client.login(username='prof_smith', password='Password123!')
        today = timezone.now().date()

        # 1. Before marking today's attendance
        response = self.client.get(reverse('dashboard:teacher_dashboard'))
        self.assertEqual(response.context['pending_attendance_count'], 1)
        self.assertContains(response, 'Attendance Pending for Today')

        # 2. Mark today's attendance for Course 1
        Attendance.objects.create(
            student=self.student_1,
            course=self.course_1,
            date=today,
            status=Attendance.Status.PRESENT
        )

        # 3. Re-check dashboard
        response = self.client.get(reverse('dashboard:teacher_dashboard'))
        self.assertEqual(response.context['pending_attendance_count'], 0)
        self.assertContains(response, 'All Attendance Up to Date!')

    def test_teacher_dashboard_recent_marks_display_isolated(self):
        """Recent marks table only shows marks entered for Teacher 1's courses."""
        self.client.login(username='prof_smith', password='Password123!')
        response = self.client.get(reverse('dashboard:teacher_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['recent_marks']), 1)
        self.assertEqual(response.context['recent_marks'][0].course, self.course_1)
        self.assertEqual(response.context['total_marks_count'], 1)


class StudentDashboardTests(TestCase):
    """
    Comprehensive test suite for Phase 14: Student Dashboard.
    Tests student data scoping, profile summary, enrolled courses,
    attendance percentage, attendance history, marks/grades, and access control.
    """

    def setUp(self):
        self.client = Client()

        # 1. Academic Structure
        self.dept = Department.objects.create(name='Computer Science', code='CS')
        self.classroom = ClassRoom.objects.create(name='Grade 11', section='B', department=self.dept)

        # 2. Teacher
        self.t_user = CustomUser.objects.create_user(
            username='dr_watson',
            email='watson@sms.local',
            password='Password123!',
            role=CustomUser.Role.TEACHER,
            first_name='John',
            last_name='Watson'
        )
        self.teacher = Teacher.objects.create(
            user=self.t_user,
            employee_id='FAC-301',
            department=self.dept,
            designation='Professor'
        )

        # 3. Student 1 (Target Student)
        self.s1_user = CustomUser.objects.create_user(
            username='sherlock_h',
            email='sherlock@sms.local',
            password='Password123!',
            role=CustomUser.Role.STUDENT,
            first_name='Sherlock',
            last_name='Holmes'
        )
        self.student_1 = Student.objects.create(
            user=self.s1_user,
            admission_number='ADM-301',
            classroom=self.classroom,
            roll_number='CS-01',
            parent_name='Violet Holmes',
            parent_phone='+1-555-0199',
            emergency_contact='+1-555-0100',
            blood_group='O+'
        )

        # 4. Student 2 (Other Student)
        self.s2_user = CustomUser.objects.create_user(
            username='mycroft_h',
            email='mycroft@sms.local',
            password='Password123!',
            role=CustomUser.Role.STUDENT,
            first_name='Mycroft',
            last_name='Holmes'
        )
        self.student_2 = Student.objects.create(
            user=self.s2_user,
            admission_number='ADM-302',
            classroom=self.classroom,
            roll_number='CS-02'
        )

        # 5. Courses
        self.course_algorithms = Course.objects.create(
            course_code='CS301',
            title='Design and Analysis of Algorithms',
            credit_hours=4,
            department=self.dept,
            teacher=self.teacher,
            classroom=self.classroom
        )
        self.course_os = Course.objects.create(
            course_code='CS302',
            title='Operating Systems',
            credit_hours=3,
            department=self.dept,
            teacher=self.teacher,
            classroom=self.classroom
        )

        # 6. Enrollments: Student 1 in Algorithms & OS; Student 2 in OS only
        Enrollment.objects.create(student=self.student_1, course=self.course_algorithms, status=Enrollment.EnrollmentStatus.ACTIVE)
        Enrollment.objects.create(student=self.student_1, course=self.course_os, status=Enrollment.EnrollmentStatus.ACTIVE)
        Enrollment.objects.create(student=self.student_2, course=self.course_os, status=Enrollment.EnrollmentStatus.ACTIVE)

        # 7. Attendance Records for Student 1: 3 Present, 1 Absent = 75.0%
        Attendance.objects.create(student=self.student_1, course=self.course_algorithms, date=date(2026, 2, 1), status=Attendance.Status.PRESENT)
        Attendance.objects.create(student=self.student_1, course=self.course_algorithms, date=date(2026, 2, 2), status=Attendance.Status.PRESENT)
        Attendance.objects.create(student=self.student_1, course=self.course_os, date=date(2026, 2, 3), status=Attendance.Status.PRESENT)
        Attendance.objects.create(student=self.student_1, course=self.course_os, date=date(2026, 2, 4), status=Attendance.Status.ABSENT)

        # Attendance Record for Student 2
        Attendance.objects.create(student=self.student_2, course=self.course_os, date=date(2026, 2, 1), status=Attendance.Status.LATE, remarks='Student 2 specific note')

        # 8. Academic Records
        # Student 1: Midterm (90/100 -> A+, 4.00), Quiz 1 (80/100 -> A, 3.75) -> Avg % = 85.0%, GPA = 3.88
        self.record_1 = AcademicRecord.objects.create(
            student=self.student_1,
            course=self.course_algorithms,
            exam_name='Midterm Exam',
            marks_obtained=Decimal('90.00'),
            total_marks=Decimal('100.00')
        )
        self.record_2 = AcademicRecord.objects.create(
            student=self.student_1,
            course=self.course_os,
            exam_name='Quiz 1',
            marks_obtained=Decimal('80.00'),
            total_marks=Decimal('100.00')
        )

        # Student 2 Academic Record
        self.record_other = AcademicRecord.objects.create(
            student=self.student_2,
            course=self.course_os,
            exam_name='Final Project',
            marks_obtained=Decimal('50.00'),
            total_marks=Decimal('100.00')
        )

    def test_student_dashboard_access_control(self):
        """Unauthenticated is redirected; teacher is redirected; student gains access."""
        # Unauthenticated
        response = self.client.get(reverse('dashboard:student_dashboard'))
        self.assertEqual(response.status_code, 302)

        # Teacher user is redirected
        self.client.login(username='dr_watson', password='Password123!')
        response = self.client.get(reverse('dashboard:student_dashboard'))
        self.assertEqual(response.status_code, 302)

        # Student user has full access
        self.client.login(username='sherlock_h', password='Password123!')
        response = self.client.get(reverse('dashboard:student_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/student_dashboard.html')

    def test_student_dashboard_data_scoping_isolation(self):
        """Student only sees their own courses, attendance logs, and exam marks."""
        self.client.login(username='sherlock_h', password='Password123!')
        response = self.client.get(reverse('dashboard:student_dashboard'))

        self.assertEqual(response.status_code, 200)

        # Scoped Counts
        self.assertEqual(response.context['total_courses'], 2)
        self.assertEqual(response.context['total_academic_records'], 2)
        self.assertEqual(response.context['total_attendance'], 4)
        self.assertEqual(response.context['present_count'], 3)
        self.assertEqual(response.context['absent_count'], 1)

        # Contains Student 1's profile and records
        self.assertContains(response, 'ADM-301')
        self.assertContains(response, 'Sherlock')
        self.assertContains(response, 'CS301')
        self.assertContains(response, 'Design and Analysis of Algorithms')
        self.assertContains(response, 'Midterm Exam')

        # Does NOT contain Student 2's specific records
        self.assertNotContains(response, 'ADM-302')
        self.assertNotContains(response, 'Final Project')
        self.assertNotContains(response, 'Student 2 specific note')

    def test_student_dashboard_attendance_and_shortage_handling(self):
        """Calculates attendance percentage accurately and triggers alerts when < 75%."""
        self.client.login(username='sherlock_h', password='Password123!')

        # 1. 3 present out of 4 total = 75.0% (Good Standing)
        response = self.client.get(reverse('dashboard:student_dashboard'))
        self.assertEqual(response.context['attendance_pct'], 75.0)
        self.assertFalse(response.context['is_shortage'])
        self.assertContains(response, 'Good Attendance Standing!')

        # 2. Add an absence -> 3 present out of 5 total = 60.0% (Shortage)
        Attendance.objects.create(
            student=self.student_1,
            course=self.course_algorithms,
            date=date(2026, 2, 5),
            status=Attendance.Status.ABSENT
        )

        response = self.client.get(reverse('dashboard:student_dashboard'))
        self.assertEqual(response.context['attendance_pct'], 60.0)
        self.assertTrue(response.context['is_shortage'])
        self.assertContains(response, 'Attendance Shortage Warning')

    def test_student_dashboard_academic_metrics_calculation(self):
        """Calculates cumulative GPA and percentage accurately."""
        self.client.login(username='sherlock_h', password='Password123!')
        response = self.client.get(reverse('dashboard:student_dashboard'))

        # Midterm = 90% (GPA 4.00, A+), Quiz 1 = 80% (GPA 3.75, A)
        # Avg percentage = 85.0%, GPA = 3.88
        self.assertEqual(response.context['avg_percentage'], 85.0)
        self.assertEqual(response.context['cumulative_gpa'], 3.88)
        self.assertEqual(response.context['grade_counts']['A_plus'], 1)
        self.assertEqual(response.context['grade_counts']['A'], 1)

