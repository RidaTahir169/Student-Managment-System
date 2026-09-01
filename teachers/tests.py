from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import CustomUser
from courses.models import Department, Course, ClassRoom, AcademicSession
from teachers.models import Teacher


class TeacherManagementTests(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Create Admin User
        self.admin_user = CustomUser.objects.create_superuser(
            username='admin_test',
            email='admin@test.com',
            password='AdminPassword123!',
            role=CustomUser.Role.ADMIN
        )

        # 2. Create Academic Entities
        self.department = Department.objects.create(
            name='Computer Science',
            code='CS'
        )
        self.classroom = ClassRoom.objects.create(
            name='BSCS-4',
            section='A',
            department=self.department
        )
        self.session = AcademicSession.objects.create(
            name='2025-2026',
            start_date='2025-09-01',
            end_date='2026-06-30',
            is_current=True
        )

        # 3. Create Teacher User and Profile
        self.teacher_user = CustomUser.objects.create_user(
            username='prof_smith',
            email='smith@test.com',
            password='TeacherPassword123!',
            first_name='Alan',
            last_name='Smith',
            role=CustomUser.Role.TEACHER
        )
        self.teacher = Teacher.objects.create(
            user=self.teacher_user,
            employee_id='EMP-TEST-001',
            department=self.department,
            designation='Associate Professor',
            qualification='Ph.D. in AI'
        )

        # 4. Create Courses
        self.course1 = Course.objects.create(
            course_code='CS101',
            title='Intro to Programming',
            credit_hours=3,
            department=self.department,
            teacher=self.teacher,
            classroom=self.classroom,
            session=self.session
        )
        self.course2 = Course.objects.create(
            course_code='CS201',
            title='Data Structures',
            credit_hours=4,
            department=self.department,
            classroom=self.classroom,
            session=self.session
        )

    def test_teacher_list_view_as_admin(self):
        self.client.login(username='admin_test', password='AdminPassword123!')
        response = self.client.get(reverse('teachers:teacher_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EMP-TEST-001')
        self.assertContains(response, 'Alan Smith')

    def test_teacher_list_search_and_filter(self):
        self.client.login(username='admin_test', password='AdminPassword123!')
        # Search match
        response = self.client.get(reverse('teachers:teacher_list'), {'q': 'Smith'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EMP-TEST-001')

        # Filter by department
        response = self.client.get(reverse('teachers:teacher_list'), {'department': self.department.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EMP-TEST-001')

    def test_teacher_detail_view(self):
        self.client.login(username='admin_test', password='AdminPassword123!')
        response = self.client.get(reverse('teachers:teacher_detail', kwargs={'pk': self.teacher.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EMP-TEST-001')
        self.assertContains(response, 'Associate Professor')
        self.assertContains(response, 'CS101')

    def test_teacher_create_view(self):
        self.client.login(username='admin_test', password='AdminPassword123!')
        create_data = {
            'username': 'prof_clark',
            'email': 'clark@test.com',
            'first_name': 'Sarah',
            'last_name': 'Clark',
            'password': 'TeacherSecret123',
            'phone_number': '+1234567890',
            'employee_id': 'EMP-TEST-002',
            'department': self.department.id,
            'designation': 'Assistant Professor',
            'qualification': 'M.Sc. Computer Engineering',
        }
        response = self.client.post(reverse('teachers:teacher_create'), create_data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Verify CustomUser and Teacher created
        new_user = CustomUser.objects.filter(username='prof_clark').first()
        self.assertIsNotNone(new_user)
        self.assertEqual(new_user.role, CustomUser.Role.TEACHER)
        self.assertEqual(new_user.first_name, 'Sarah')

        new_teacher = Teacher.objects.filter(employee_id='EMP-TEST-002').first()
        self.assertIsNotNone(new_teacher)
        self.assertEqual(new_teacher.user, new_user)
        self.assertEqual(new_teacher.department, self.department)

    def test_teacher_update_view(self):
        self.client.login(username='admin_test', password='AdminPassword123!')
        update_data = {
            'first_name': 'Alan Updated',
            'last_name': 'Smith',
            'email': 'smith_updated@test.com',
            'phone_number': '+9876543210',
            'employee_id': 'EMP-TEST-001-MOD',
            'department': self.department.id,
            'designation': 'Full Professor',
            'qualification': 'Ph.D. in Computer Science',
            'joining_date': '2020-01-15',
            'bio': 'Senior AI researcher with 15 publications.'
        }
        response = self.client.post(
            reverse('teachers:teacher_update', kwargs={'pk': self.teacher.pk}),
            update_data,
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        self.teacher_user.refresh_from_db()
        self.teacher.refresh_from_db()
        self.assertEqual(self.teacher_user.first_name, 'Alan Updated')
        self.assertEqual(self.teacher_user.email, 'smith_updated@test.com')
        self.assertEqual(self.teacher.employee_id, 'EMP-TEST-001-MOD')
        self.assertEqual(self.teacher.designation, 'Full Professor')

    def test_teacher_assign_courses_view(self):
        self.client.login(username='admin_test', password='AdminPassword123!')
        # Assign both course1 and course2 to teacher
        response = self.client.post(
            reverse('teachers:teacher_assign_courses', kwargs={'pk': self.teacher.pk}),
            {'courses': [self.course1.id, self.course2.id]},
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        self.course1.refresh_from_db()
        self.course2.refresh_from_db()
        self.assertEqual(self.course1.teacher, self.teacher)
        self.assertEqual(self.course2.teacher, self.teacher)

    def test_teacher_unassign_single_course_view(self):
        self.client.login(username='admin_test', password='AdminPassword123!')
        self.assertEqual(self.course1.teacher, self.teacher)

        response = self.client.post(
            reverse('teachers:teacher_unassign_course', kwargs={
                'teacher_pk': self.teacher.pk,
                'course_pk': self.course1.pk
            }),
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        self.course1.refresh_from_db()
        self.assertIsNone(self.course1.teacher)

    def test_teacher_delete_view(self):
        self.client.login(username='admin_test', password='AdminPassword123!')
        teacher_pk = self.teacher.pk
        user_pk = self.teacher_user.pk

        response = self.client.post(
            reverse('teachers:teacher_delete', kwargs={'pk': teacher_pk}),
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        # Verify teacher and user deleted
        self.assertFalse(Teacher.objects.filter(pk=teacher_pk).exists())
        self.assertFalse(CustomUser.objects.filter(pk=user_pk).exists())

        # Verify course was safely unassigned rather than deleted
        self.course1.refresh_from_db()
        self.assertIsNone(self.course1.teacher)
