from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import CustomUser
from courses.models import Department, ClassRoom
from students.models import Student


class StudentCRUDTests(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Create Admin & Teacher
        self.admin = CustomUser.objects.create_user(
            username='admin_user',
            email='admin@test.com',
            password='Password123!',
            role=CustomUser.Role.ADMIN
        )
        self.teacher = CustomUser.objects.create_user(
            username='teacher_user',
            email='teacher@test.com',
            password='Password123!',
            role=CustomUser.Role.TEACHER
        )

        # 2. Create Classrooms
        self.dept = Department.objects.create(name='Science', code='SCI')
        self.class1 = ClassRoom.objects.create(name='Grade 10', section='A', department=self.dept)
        self.class2 = ClassRoom.objects.create(name='Grade 11', section='B', department=self.dept)

        # 3. Create Sample Student
        self.student_user = CustomUser.objects.create_user(
            username='student_alice',
            email='alice@test.com',
            password='Password123!',
            first_name='Alice',
            last_name='Walker',
            role=CustomUser.Role.STUDENT
        )
        self.student = Student.objects.create(
            user=self.student_user,
            admission_number='ADM-101',
            classroom=self.class1,
            roll_number='12'
        )

    def test_student_list_search_and_filter(self):
        """Tests student search query and classroom filter."""
        self.client.login(username='admin_user', password='Password123!')
        
        # Search by name
        response = self.client.get(reverse('students:student_list'), {'q': 'Alice'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ADM-101')
        self.assertContains(response, 'Alice Walker')

        # Filter by matching classroom
        response = self.client.get(reverse('students:student_list'), {'classroom': self.class1.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ADM-101')

        # Filter by non-matching classroom
        response = self.client.get(reverse('students:student_list'), {'classroom': self.class2.id})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'ADM-101')

    def test_student_create_view(self):
        """Tests admitting a new student creates CustomUser and Student profile."""
        self.client.login(username='admin_user', password='Password123!')
        response = self.client.post(reverse('students:student_create'), {
            'username': 'bob_smith',
            'email': 'bob@test.com',
            'first_name': 'Bob',
            'last_name': 'Smith',
            'password': 'StrongPassword123!',
            'admission_number': 'ADM-102',
            'classroom': self.class2.id,
            'roll_number': '15',
            'parent_name': 'Robert Smith',
            'parent_phone': '555-0199',
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(CustomUser.objects.filter(username='bob_smith').exists())
        self.assertTrue(Student.objects.filter(admission_number='ADM-102').exists())
        student = Student.objects.get(admission_number='ADM-102')
        self.assertEqual(student.classroom, self.class2)

    def test_student_detail_view(self):
        """Tests student detail view renders profile details correctly."""
        self.client.login(username='admin_user', password='Password123!')
        response = self.client.get(reverse('students:student_detail', args=[self.student.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ADM-101')
        self.assertContains(response, 'Alice Walker')

    def test_student_update_view(self):
        """Tests updating student and user profile fields."""
        self.client.login(username='admin_user', password='Password123!')
        response = self.client.post(reverse('students:student_update', args=[self.student.pk]), {
            'first_name': 'Alicia',
            'last_name': 'Walker-Smith',
            'email': 'alicia@test.com',
            'admission_number': 'ADM-101-UPDATED',
            'classroom': self.class2.id,
            'roll_number': '99',
            'parent_name': 'Jane Walker',
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.student.refresh_from_db()
        self.student.user.refresh_from_db()

        self.assertEqual(self.student.admission_number, 'ADM-101-UPDATED')
        self.assertEqual(self.student.user.first_name, 'Alicia')
        self.assertEqual(self.student.classroom, self.class2)

    def test_student_delete_view(self):
        """Tests deleting a student removes both Student profile and CustomUser."""
        self.client.login(username='admin_user', password='Password123!')
        response = self.client.post(reverse('students:student_delete', args=[self.student.pk]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Student.objects.filter(admission_number='ADM-101').exists())
        self.assertFalse(CustomUser.objects.filter(username='student_alice').exists())
