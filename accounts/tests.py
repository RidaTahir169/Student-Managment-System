from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import CustomUser
from students.models import Student
from teachers.models import Teacher
from courses.models import Department, ClassRoom, Course, Enrollment
from attendance.models import Attendance
from academics.models import AcademicRecord



class AuthenticationAndRoleTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create users for all three roles
        self.admin_user = CustomUser.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='Password123!',
            role=CustomUser.Role.ADMIN
        )
        self.teacher_user = CustomUser.objects.create_user(
            username='teacher_test',
            email='teacher@test.com',
            password='Password123!',
            role=CustomUser.Role.TEACHER
        )
        self.teacher_profile = Teacher.objects.create(
            user=self.teacher_user,
            employee_id='FAC-9999'
        )
        self.student_user = CustomUser.objects.create_user(
            username='student_test',
            email='student@test.com',
            password='Password123!',
            role=CustomUser.Role.STUDENT
        )
        self.student_profile = Student.objects.create(
            user=self.student_user,
            admission_number='STU-9999'
        )

    def test_public_registration_is_disabled_for_unauthenticated_users(self):
        """Tests that public registration GET/POST redirects unauthenticated users to login."""
        # Unauthenticated GET
        get_response = self.client.get(reverse('accounts:register'))
        self.assertEqual(get_response.status_code, 302)
        self.assertRedirects(get_response, reverse('accounts:login'))

        # Unauthenticated POST attempt
        post_response = self.client.post(reverse('accounts:register'), {
            'username': 'unauthorized_student',
            'email': 'unauth@test.com',
            'role': CustomUser.Role.STUDENT,
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertEqual(post_response.status_code, 302)
        self.assertRedirects(post_response, reverse('accounts:login'))
        self.assertFalse(CustomUser.objects.filter(username='unauthorized_student').exists())

    def test_registration_forbidden_for_non_admin_users(self):
        """Tests that non-admin authenticated users receive 403 Forbidden on registration endpoint."""
        self.client.login(username='student_test', password='Password123!')
        student_resp = self.client.get(reverse('accounts:register'))
        self.assertEqual(student_resp.status_code, 403)

        self.client.login(username='teacher_test', password='Password123!')
        teacher_resp = self.client.get(reverse('accounts:register'))
        self.assertEqual(teacher_resp.status_code, 403)

    def test_admin_can_provision_new_users(self):
        """Tests that authenticated administrators can provision student/teacher accounts."""
        self.client.login(username='admin_test', password='Password123!')
        response = self.client.post(reverse('accounts:register'), {
            'username': 'new_student',
            'email': 'newstudent@test.com',
            'first_name': 'New',
            'last_name': 'Student',
            'role': CustomUser.Role.STUDENT,
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(CustomUser.objects.filter(username='new_student').exists())
        user = CustomUser.objects.get(username='new_student')
        self.assertTrue(Student.objects.filter(user=user).exists())

    def test_admin_login_redirects_to_admin_dashboard(self):
        """Tests admin login via username and email redirects to /admin-dashboard/."""
        # Login with username
        response = self.client.post(reverse('accounts:login'), {
            'username': 'admin_test',
            'password': 'Password123!',
        }, follow=True)
        self.assertRedirects(response, reverse('dashboard:admin_dashboard'))

        # Login with email
        self.client.logout()
        email_response = self.client.post(reverse('accounts:login'), {
            'username': 'admin@test.com',
            'password': 'Password123!',
        }, follow=True)
        self.assertRedirects(email_response, reverse('dashboard:admin_dashboard'))

    def test_teacher_login_redirects_to_teacher_dashboard(self):
        """Tests teacher login via username and email redirects to /teacher-dashboard/."""
        # Login with username
        response = self.client.post(reverse('accounts:login'), {
            'username': 'teacher_test',
            'password': 'Password123!',
        }, follow=True)
        self.assertRedirects(response, reverse('dashboard:teacher_dashboard'))

        # Login with email
        self.client.logout()
        email_response = self.client.post(reverse('accounts:login'), {
            'username': 'teacher@test.com',
            'password': 'Password123!',
        }, follow=True)
        self.assertRedirects(email_response, reverse('dashboard:teacher_dashboard'))

    def test_student_login_redirects_to_student_dashboard(self):
        """Tests student login via username and email redirects to /student-dashboard/."""
        # Login with username
        response = self.client.post(reverse('accounts:login'), {
            'username': 'student_test',
            'password': 'Password123!',
        }, follow=True)
        self.assertRedirects(response, reverse('dashboard:student_dashboard'))

        # Login with email
        self.client.logout()
        email_response = self.client.post(reverse('accounts:login'), {
            'username': 'student@test.com',
            'password': 'Password123!',
        }, follow=True)
        self.assertRedirects(email_response, reverse('dashboard:student_dashboard'))

    def test_invalid_credentials_returns_error_and_does_not_redirect_to_register(self):
        """Tests failed login renders error on login page and does NOT redirect to register."""
        response = self.client.post(reverse('accounts:login'), {
            'username': 'nonexistent_user',
            'password': 'WrongPassword123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')
        self.assertNotEqual(response.status_code, 302)

    def test_logout_view(self):
        """Tests user logout."""
        self.client.login(username='student_test', password='Password123!')
        response = self.client.get(reverse('accounts:logout'), follow=True)
        self.assertRedirects(response, reverse('accounts:login'))

    def test_student_cannot_access_admin_dashboard(self):
        """Tests student receives 403 Forbidden when accessing Admin Dashboard."""
        self.client.login(username='student_test', password='Password123!')
        response = self.client.get(reverse('dashboard:admin_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_student_cannot_access_teacher_dashboard(self):
        """Tests student receives 403 Forbidden when accessing Teacher Dashboard."""
        self.client.login(username='student_test', password='Password123!')
        response = self.client.get(reverse('dashboard:teacher_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_teacher_cannot_access_admin_dashboard(self):
        """Tests teacher receives 403 Forbidden when accessing Admin Dashboard."""
        self.client.login(username='teacher_test', password='Password123!')
        response = self.client.get(reverse('dashboard:admin_dashboard'))
        self.assertEqual(response.status_code, 403)


class Phase16ValidationAndSecurityTests(TestCase):
    """
    Dedicated comprehensive test suite for Phase 16: Validation & Security.
    """
    def setUp(self):
        self.client = Client()

        # Academic infrastructure
        self.dept = Department.objects.create(name='Computer Science', code='CS')
        self.classroom = ClassRoom.objects.create(name='Year 1', section='A', department=self.dept)

        # Users
        self.admin = CustomUser.objects.create_superuser(
            username='admin_phase16',
            email='admin_p16@sms.edu',
            password='Password123!',
            role=CustomUser.Role.ADMIN
        )

        self.teacher_user = CustomUser.objects.create_user(
            username='teacher_phase16',
            email='teacher_p16@sms.edu',
            password='Password123!',
            role=CustomUser.Role.TEACHER
        )
        self.teacher = Teacher.objects.create(
            user=self.teacher_user,
            employee_id='EMP-P16-01',
            department=self.dept
        )

        self.other_teacher_user = CustomUser.objects.create_user(
            username='other_teacher_p16',
            email='other_teacher_p16@sms.edu',
            password='Password123!',
            role=CustomUser.Role.TEACHER
        )
        self.other_teacher = Teacher.objects.create(
            user=self.other_teacher_user,
            employee_id='EMP-P16-02',
            department=self.dept
        )

        self.student_user_1 = CustomUser.objects.create_user(
            username='student1_p16',
            email='student1_p16@sms.edu',
            password='Password123!',
            role=CustomUser.Role.STUDENT
        )
        self.student_1 = Student.objects.create(
            user=self.student_user_1,
            admission_number='STU-P16-01',
            classroom=self.classroom
        )

        self.student_user_2 = CustomUser.objects.create_user(
            username='student2_p16',
            email='student2_p16@sms.edu',
            password='Password123!',
            role=CustomUser.Role.STUDENT
        )
        self.student_2 = Student.objects.create(
            user=self.student_user_2,
            admission_number='STU-P16-02',
            classroom=self.classroom
        )

        # Courses
        self.course_1 = Course.objects.create(
            course_code='CS101-P16',
            title='Intro to Programming',
            department=self.dept,
            teacher=self.teacher,
            classroom=self.classroom
        )
        self.course_2 = Course.objects.create(
            course_code='CS102-P16',
            title='Object Oriented Programming',
            department=self.dept,
            teacher=self.other_teacher,
            classroom=self.classroom
        )

        # Enrollments
        Enrollment.objects.create(student=self.student_1, course=self.course_1)

    # 1. Unique Student ID & Unique Teacher ID
    def test_unique_student_id_case_insensitive_model_validation(self):
        """Duplicate student admission number in different case must be rejected."""
        duplicate_student = Student(
            user=self.admin,
            admission_number='stu-p16-01'  # Lowercase version of existing STU-P16-01
        )
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            duplicate_student.clean()

    def test_unique_teacher_id_case_insensitive_model_validation(self):
        """Duplicate teacher employee ID in different case must be rejected."""
        duplicate_teacher = Teacher(
            user=self.admin,
            employee_id='emp-p16-01'  # Lowercase version of existing EMP-P16-01
        )
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            duplicate_teacher.clean()

    # 2. Email Validation
    def test_email_normalization_and_case_insensitive_uniqueness(self):
        """Email should be lowercased and duplicate case-insensitive email rejected."""
        user = CustomUser(username='unique_user_p16', email='TEACHER_P16@SMS.EDU')
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            user.clean()

    # 3. Marks Validation
    def test_marks_validation_cannot_exceed_total(self):
        """Marks obtained cannot exceed total marks."""
        from decimal import Decimal
        from django.core.exceptions import ValidationError
        record = AcademicRecord(
            student=self.student_1,
            course=self.course_1,
            exam_name='Quiz 1',
            marks_obtained=Decimal('105.00'),
            total_marks=Decimal('100.00')
        )
        with self.assertRaises(ValidationError):
            record.clean()

    def test_marks_validation_cannot_be_negative(self):
        """Marks obtained cannot be negative."""
        from decimal import Decimal
        from django.core.exceptions import ValidationError
        record = AcademicRecord(
            student=self.student_1,
            course=self.course_1,
            exam_name='Quiz Negative',
            marks_obtained=Decimal('-5.00'),
            total_marks=Decimal('100.00')
        )
        with self.assertRaises(ValidationError):
            record.clean()

    def test_marks_validation_total_must_be_positive(self):
        """Total marks must be greater than 0."""
        from decimal import Decimal
        from django.core.exceptions import ValidationError
        record = AcademicRecord(
            student=self.student_1,
            course=self.course_1,
            exam_name='Quiz Zero Total',
            marks_obtained=Decimal('0.00'),
            total_marks=Decimal('0.00')
        )
        with self.assertRaises(ValidationError):
            record.clean()

    def test_marks_validation_student_must_be_enrolled(self):
        """Cannot create academic record for unenrolled student."""
        from decimal import Decimal
        from django.core.exceptions import ValidationError
        # Student 2 is NOT enrolled in course_1
        record = AcademicRecord(
            student=self.student_2,
            course=self.course_1,
            exam_name='Midterm',
            marks_obtained=Decimal('80.00'),
            total_marks=Decimal('100.00')
        )
        with self.assertRaises(ValidationError):
            record.clean()

    # 4. Attendance Validation & Duplicate Prevention
    def test_attendance_cannot_be_future_date(self):
        """Attendance date cannot be in the future."""
        from django.utils import timezone
        from datetime import timedelta
        from django.core.exceptions import ValidationError
        future_date = timezone.now().date() + timedelta(days=5)
        att = Attendance(
            student=self.student_1,
            course=self.course_1,
            date=future_date,
            status=Attendance.Status.PRESENT
        )
        with self.assertRaises(ValidationError):
            att.clean()

    def test_attendance_student_must_be_enrolled(self):
        """Attendance cannot be logged for unenrolled student."""
        from django.utils import timezone
        from django.core.exceptions import ValidationError
        att = Attendance(
            student=self.student_2,  # Not enrolled in course_1
            course=self.course_1,
            date=timezone.now().date(),
            status=Attendance.Status.PRESENT
        )
        with self.assertRaises(ValidationError):
            att.clean()

    # 5. Role-Based Permissions
    def test_student_isolation_cannot_view_other_student_detail(self):
        """Student cannot view another student's detail profile."""
        self.client.login(username='student1_p16', password='Password123!')
        response = self.client.get(reverse('students:student_detail', args=[self.student_2.pk]))
        self.assertEqual(response.status_code, 403)

    def test_student_isolation_cannot_view_other_student_report_card(self):
        """Student cannot view another student's report card / transcript."""
        self.client.login(username='student1_p16', password='Password123!')
        response = self.client.get(reverse('academics:student_report_card', args=[self.student_2.pk]))
        self.assertEqual(response.status_code, 403)

    def test_teacher_scope_cannot_manage_unassigned_course_attendance(self):
        """Teacher cannot mark attendance for an unassigned course."""
        self.client.login(username='teacher_phase16', password='Password123!')
        # course_2 is assigned to other_teacher
        response = self.client.get(reverse('attendance:mark_course_attendance', args=[self.course_2.pk]))
        self.assertEqual(response.status_code, 404)

    def test_teacher_scope_cannot_enter_marks_for_unassigned_course(self):
        """Teacher cannot enter marks for unassigned course."""
        self.client.login(username='teacher_phase16', password='Password123!')
        response = self.client.post(reverse('academics:record_create'), {
            'course': self.course_2.id,
            'student': self.student_1.id,
            'exam_name': 'Hacked Exam',
            'exam_type': AcademicRecord.ExamType.QUIZ,
            'marks_obtained': '90.00',
            'total_marks': '100.00',
            'date_recorded': timezone.now().date().strftime('%Y-%m-%d'),
        })
        self.assertIn(response.status_code, [200, 403])
        self.assertFalse(AcademicRecord.objects.filter(exam_name='Hacked Exam').exists())

    def test_admin_has_full_access(self):
        """Admin has full access to dashboards and detail views."""
        self.client.login(username='admin_phase16', password='Password123!')
        resp1 = self.client.get(reverse('dashboard:admin_dashboard'))
        self.assertEqual(resp1.status_code, 200)
        resp2 = self.client.get(reverse('students:student_detail', args=[self.student_1.pk]))
        self.assertEqual(resp2.status_code, 200)
        resp3 = self.client.get(reverse('academics:student_report_card', args=[self.student_1.pk]))
        self.assertEqual(resp3.status_code, 200)

    # 6. Login Protection
    def test_unauthenticated_user_redirected_to_login(self):
        """Unauthenticated access to protected view is redirected to login page."""
        response = self.client.get(reverse('dashboard:admin_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

