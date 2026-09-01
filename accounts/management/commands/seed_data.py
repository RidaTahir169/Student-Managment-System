import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import CustomUser
from teachers.models import Teacher
from students.models import Student
from courses.models import Department, AcademicSession, ClassRoom, Course, Enrollment
from attendance.models import Attendance
from academics.models import AcademicRecord


class Command(BaseCommand):
    help = "Seeds the database with realistic sample/dummy data for testing and demo purposes."

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Optionally clear seeded dummy entities before re-populating.',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== Starting Student Management System Data Seeder ==="))

        stats = {
            'users': 0,
            'teachers': 0,
            'students': 0,
            'departments': 0,
            'sessions': 0,
            'classrooms': 0,
            'courses': 0,
            'enrollments': 0,
            'attendance': 0,
            'academics': 0,
        }

        with transaction.atomic():
            # 1. ACADEMIC SESSION
            session, created = AcademicSession.objects.get_or_create(
                name="2025-2026",
                defaults={
                    'start_date': datetime.date(2025, 9, 1),
                    'end_date': datetime.date(2026, 6, 30),
                    'is_current': True,
                }
            )
            if not session.is_current:
                session.is_current = True
                session.save()
            if created:
                stats['sessions'] += 1
                self.stdout.write(self.style.SUCCESS(f"  [+] Created Academic Session: {session.name}"))
            else:
                self.stdout.write(f"  [*] Academic Session already exists: {session.name}")

            # 2. DEPARTMENTS
            dept_data = [
                ("Computer Science", "CS", "Department of Computer Science and Computing Technologies"),
                ("Software Engineering", "SE", "Department of Software Engineering and Quality Assurance"),
                ("Information Technology", "IT", "Department of Information Technology and Network Systems"),
            ]
            departments = {}
            for name, code, desc in dept_data:
                dept, created = Department.objects.get_or_create(
                    code=code,
                    defaults={'name': name, 'description': desc}
                )
                departments[code] = dept
                if created:
                    stats['departments'] += 1
                    self.stdout.write(self.style.SUCCESS(f"  [+] Created Department: {name} ({code})"))
                else:
                    self.stdout.write(f"  [*] Department already exists: {name} ({code})")

            # 3. CLASS ROOMS
            classroom_data = [
                ("BSCS Sem 1", "A", departments["CS"]),
                ("BSCS Sem 3", "A", departments["CS"]),
                ("BSSE Sem 2", "A", departments["SE"]),
                ("BSIT Sem 4", "A", departments["IT"]),
            ]
            classrooms = {}
            for name, section, dept in classroom_data:
                key = f"{name}-{section}"
                classroom, created = ClassRoom.objects.get_or_create(
                    name=name,
                    section=section,
                    defaults={'department': dept}
                )
                classrooms[key] = classroom
                if created:
                    stats['classrooms'] += 1
                    self.stdout.write(self.style.SUCCESS(f"  [+] Created Class Room: {name} - Section {section}"))
                else:
                    self.stdout.write(f"  [*] Class Room already exists: {name} - Section {section}")

            # 4. ADMIN USER (admin@school.com / Admin123!)
            admin_user = CustomUser.objects.filter(email="admin@school.com").first()
            if not admin_user:
                admin_user = CustomUser.objects.filter(username="admin").first()
                if admin_user:
                    admin_user.email = "admin@school.com"
                else:
                    admin_user = CustomUser(username="admin", email="admin@school.com")
            
            admin_user.first_name = "System"
            admin_user.last_name = "Administrator"
            admin_user.role = CustomUser.Role.ADMIN
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.is_active = True
            admin_user.set_password("Admin123!")
            admin_user.save()
            stats['users'] += 1
            self.stdout.write(self.style.SUCCESS("  [+] Admin User configured: admin@school.com / Admin123!"))

            # 5. TEACHERS (5)
            teachers_data = [
                {
                    'username': 'teacher1',
                    'email': 'teacher1@sms.local',
                    'first_name': 'Sarah',
                    'last_name': 'Jenkins',
                    'gender': CustomUser.Gender.FEMALE,
                    'phone': '+1-555-0101',
                    'dob': datetime.date(1982, 4, 14),
                    'emp_id': 'FAC-1001',
                    'dept': departments['CS'],
                    'designation': 'Professor',
                    'qualification': 'Ph.D. in Computer Science (MIT)',
                    'bio': 'Specialist in Algorithms, Data Structures, and Machine Learning with 15+ years teaching experience.',
                },
                {
                    'username': 'teacher2',
                    'email': 'teacher2@sms.local',
                    'first_name': 'Michael',
                    'last_name': 'Chang',
                    'gender': CustomUser.Gender.MALE,
                    'phone': '+1-555-0102',
                    'dob': datetime.date(1986, 9, 21),
                    'emp_id': 'FAC-1002',
                    'dept': departments['CS'],
                    'designation': 'Associate Professor',
                    'qualification': 'Ph.D. in Object-Oriented Paradigms (Stanford)',
                    'bio': 'Passionate educator focusing on Clean Code, Design Patterns, and OOP Architecture.',
                },
                {
                    'username': 'teacher3',
                    'email': 'teacher3@sms.local',
                    'first_name': 'Emily',
                    'last_name': 'Watson',
                    'gender': CustomUser.Gender.FEMALE,
                    'phone': '+1-555-0103',
                    'dob': datetime.date(1990, 11, 5),
                    'emp_id': 'FAC-1003',
                    'dept': departments['CS'],
                    'designation': 'Assistant Professor',
                    'qualification': 'M.S. in Database Systems & Distributed Architectures (CMU)',
                    'bio': 'Experienced in SQL/NoSQL databases, big data warehousing, and query optimization.',
                },
                {
                    'username': 'teacher4',
                    'email': 'teacher4@sms.local',
                    'first_name': 'Robert',
                    'last_name': 'Davis',
                    'gender': CustomUser.Gender.MALE,
                    'phone': '+1-555-0104',
                    'dob': datetime.date(1984, 1, 19),
                    'emp_id': 'FAC-1004',
                    'dept': departments['SE'],
                    'designation': 'Associate Professor',
                    'qualification': 'Ph.D. in Software Engineering (UC Berkeley)',
                    'bio': 'Expert in Agile development, DevOps lifecycle, and enterprise software architecture.',
                },
                {
                    'username': 'teacher5',
                    'email': 'teacher5@sms.local',
                    'first_name': 'Aisha',
                    'last_name': 'Patel',
                    'gender': CustomUser.Gender.FEMALE,
                    'phone': '+1-555-0105',
                    'dob': datetime.date(1989, 7, 30),
                    'emp_id': 'FAC-1005',
                    'dept': departments['IT'],
                    'designation': 'Assistant Professor',
                    'qualification': 'Ph.D. in Cybersecurity & Web Engineering (Oxford)',
                    'bio': 'Specialist in full-stack web application development and information security.',
                },
            ]

            teachers_dict = {}
            for t_item in teachers_data:
                u, u_created = CustomUser.objects.get_or_create(
                    username=t_item['username'],
                    defaults={
                        'email': t_item['email'],
                        'first_name': t_item['first_name'],
                        'last_name': t_item['last_name'],
                        'role': CustomUser.Role.TEACHER,
                        'gender': t_item['gender'],
                        'phone_number': t_item['phone'],
                        'date_of_birth': t_item['dob'],
                        'address': f"Faculty Housing #{t_item['emp_id'][-3:]}, University Campus",
                        'is_active': True,
                    }
                )
                u.set_password("teacher123")
                u.role = CustomUser.Role.TEACHER
                u.save()
                if u_created:
                    stats['users'] += 1

                t_profile, t_created = Teacher.objects.get_or_create(
                    user=u,
                    defaults={
                        'employee_id': t_item['emp_id'],
                        'department': t_item['dept'],
                        'designation': t_item['designation'],
                        'qualification': t_item['qualification'],
                        'bio': t_item['bio'],
                        'joining_date': datetime.date(2021, 8, 15),
                    }
                )
                teachers_dict[t_item['username']] = t_profile
                if t_created:
                    stats['teachers'] += 1
                    self.stdout.write(self.style.SUCCESS(f"  [+] Created Teacher: {t_item['first_name']} {t_item['last_name']} ({t_item['emp_id']})"))
                else:
                    self.stdout.write(f"  [*] Teacher already exists: {t_item['first_name']} {t_item['last_name']} ({t_item['emp_id']})")

            # 6. COURSES (7)
            course_data = [
                {
                    'code': 'CS101',
                    'title': 'Programming Fundamentals',
                    'credits': 3,
                    'dept': departments['CS'],
                    'teacher': teachers_dict['teacher1'],
                    'classroom': classrooms['BSCS Sem 1-A'],
                    'desc': 'Core introductory course covering variables, control flow, functions, arrays, and basic problem solving in Python/C++.',
                },
                {
                    'code': 'CS201',
                    'title': 'Object-Oriented Programming',
                    'credits': 4,
                    'dept': departments['CS'],
                    'teacher': teachers_dict['teacher2'],
                    'classroom': classrooms['BSCS Sem 3-A'],
                    'desc': 'In-depth exploration of OOP paradigms including encapsulation, inheritance, polymorphism, abstract classes, and design patterns.',
                },
                {
                    'code': 'CS301',
                    'title': 'Database Systems',
                    'credits': 3,
                    'dept': departments['CS'],
                    'teacher': teachers_dict['teacher3'],
                    'classroom': classrooms['BSCS Sem 3-A'],
                    'desc': 'Relational data models, normalization (1NF-BCNF), SQL queries, indexing, transaction ACID properties, and relational algebra.',
                },
                {
                    'code': 'SE302',
                    'title': 'Software Engineering',
                    'credits': 3,
                    'dept': departments['SE'],
                    'teacher': teachers_dict['teacher4'],
                    'classroom': classrooms['BSSE Sem 2-A'],
                    'desc': 'Software life cycle models, Agile Scrum, requirements analysis, system architecture, testing strategies, and project management.',
                },
                {
                    'code': 'CS401',
                    'title': 'Machine Learning',
                    'credits': 3,
                    'dept': departments['CS'],
                    'teacher': teachers_dict['teacher1'],
                    'classroom': classrooms['BSCS Sem 3-A'],
                    'desc': 'Supervised and unsupervised learning, regression, classification, clustering, neural networks, and model evaluation techniques.',
                },
                {
                    'code': 'CS303',
                    'title': 'Web Engineering',
                    'credits': 3,
                    'dept': departments['IT'],
                    'teacher': teachers_dict['teacher5'],
                    'classroom': classrooms['BSIT Sem 4-A'],
                    'desc': 'Modern web development principles, client-server architectures, RESTful APIs, Django backend development, and responsive frontends.',
                },
                {
                    'code': 'CS402',
                    'title': 'Information Security',
                    'credits': 3,
                    'dept': departments['IT'],
                    'teacher': teachers_dict['teacher5'],
                    'classroom': classrooms['BSIT Sem 4-A'],
                    'desc': 'Principles of cryptography, symmetric/asymmetric encryption, network defense, threat modeling, and web security vulnerabilities.',
                },
            ]

            courses_dict = {}
            for c_item in course_data:
                course, created = Course.objects.get_or_create(
                    course_code=c_item['code'],
                    defaults={
                        'title': c_item['title'],
                        'credit_hours': c_item['credits'],
                        'department': c_item['dept'],
                        'teacher': c_item['teacher'],
                        'classroom': c_item['classroom'],
                        'session': session,
                        'description': c_item['desc'],
                    }
                )
                courses_dict[c_item['code']] = course
                if created:
                    stats['courses'] += 1
                    self.stdout.write(self.style.SUCCESS(f"  [+] Created Course: {c_item['code']} - {c_item['title']}"))
                else:
                    self.stdout.write(f"  [*] Course already exists: {c_item['code']} - {c_item['title']}")

            # 7. STUDENTS (18)
            students_data = [
                # BSCS Sem 1-A Students (5)
                {'num': 1, 'first': 'Alex', 'last': 'Rivera', 'gender': CustomUser.Gender.MALE, 'dob': datetime.date(2005, 3, 12), 'blood': 'O+', 'cls': classrooms['BSCS Sem 1-A'], 'roll': 'CS1-01', 'p_name': 'Carlos Rivera', 'p_phone': '+1-555-1101'},
                {'num': 2, 'first': 'Sophia', 'last': 'Martinez', 'gender': CustomUser.Gender.FEMALE, 'dob': datetime.date(2005, 7, 24), 'blood': 'A+', 'cls': classrooms['BSCS Sem 1-A'], 'roll': 'CS1-02', 'p_name': 'Elena Martinez', 'p_phone': '+1-555-1102'},
                {'num': 3, 'first': 'Daniel', 'last': 'Kim', 'gender': CustomUser.Gender.MALE, 'dob': datetime.date(2004, 11, 30), 'blood': 'B+', 'cls': classrooms['BSCS Sem 1-A'], 'roll': 'CS1-03', 'p_name': 'Min-jun Kim', 'p_phone': '+1-555-1103'},
                {'num': 4, 'first': 'Emma', 'last': 'Johnson', 'gender': CustomUser.Gender.FEMALE, 'dob': datetime.date(2005, 1, 15), 'blood': 'AB+', 'cls': classrooms['BSCS Sem 1-A'], 'roll': 'CS1-04', 'p_name': 'David Johnson', 'p_phone': '+1-555-1104'},
                {'num': 5, 'first': 'Lucas', 'last': 'Brown', 'gender': CustomUser.Gender.MALE, 'dob': datetime.date(2005, 5, 8), 'blood': 'O-', 'cls': classrooms['BSCS Sem 1-A'], 'roll': 'CS1-05', 'p_name': 'Thomas Brown', 'p_phone': '+1-555-1105'},

                # BSCS Sem 3-A Students (5)
                {'num': 6, 'first': 'Olivia', 'last': 'Taylor', 'gender': CustomUser.Gender.FEMALE, 'dob': datetime.date(2004, 8, 19), 'blood': 'A+', 'cls': classrooms['BSCS Sem 3-A'], 'roll': 'CS3-01', 'p_name': 'James Taylor', 'p_phone': '+1-555-1106'},
                {'num': 7, 'first': 'Ethan', 'last': 'Anderson', 'gender': CustomUser.Gender.MALE, 'dob': datetime.date(2004, 2, 14), 'blood': 'B+', 'cls': classrooms['BSCS Sem 3-A'], 'roll': 'CS3-02', 'p_name': 'Mark Anderson', 'p_phone': '+1-555-1107'},
                {'num': 8, 'first': 'Ava', 'last': 'Thomas', 'gender': CustomUser.Gender.FEMALE, 'dob': datetime.date(2004, 9, 27), 'blood': 'O+', 'cls': classrooms['BSCS Sem 3-A'], 'roll': 'CS3-03', 'p_name': 'Paul Thomas', 'p_phone': '+1-555-1108'},
                {'num': 9, 'first': 'Noah', 'last': 'Jackson', 'gender': CustomUser.Gender.MALE, 'dob': datetime.date(2003, 12, 10), 'blood': 'AB-', 'cls': classrooms['BSCS Sem 3-A'], 'roll': 'CS3-04', 'p_name': 'William Jackson', 'p_phone': '+1-555-1109'},
                {'num': 10, 'first': 'Mia', 'last': 'White', 'gender': CustomUser.Gender.FEMALE, 'dob': datetime.date(2004, 4, 3), 'blood': 'A-', 'cls': classrooms['BSCS Sem 3-A'], 'roll': 'CS3-05', 'p_name': 'Edward White', 'p_phone': '+1-555-1110'},

                # BSSE Sem 2-A Students (4)
                {'num': 11, 'first': 'Liam', 'last': 'Harris', 'gender': CustomUser.Gender.MALE, 'dob': datetime.date(2005, 2, 22), 'blood': 'O+', 'cls': classrooms['BSSE Sem 2-A'], 'roll': 'SE2-01', 'p_name': 'Arthur Harris', 'p_phone': '+1-555-1111'},
                {'num': 12, 'first': 'Isabella', 'last': 'Martin', 'gender': CustomUser.Gender.FEMALE, 'dob': datetime.date(2004, 10, 17), 'blood': 'B-', 'cls': classrooms['BSSE Sem 2-A'], 'roll': 'SE2-02', 'p_name': 'George Martin', 'p_phone': '+1-555-1112'},
                {'num': 13, 'first': 'Mason', 'last': 'Clark', 'gender': CustomUser.Gender.MALE, 'dob': datetime.date(2005, 6, 29), 'blood': 'A+', 'cls': classrooms['BSSE Sem 2-A'], 'roll': 'SE2-03', 'p_name': 'Henry Clark', 'p_phone': '+1-555-1113'},
                {'num': 14, 'first': 'Charlotte', 'last': 'Lewis', 'gender': CustomUser.Gender.FEMALE, 'dob': datetime.date(2004, 12, 5), 'blood': 'O+', 'cls': classrooms['BSSE Sem 2-A'], 'roll': 'SE2-04', 'p_name': 'Samuel Lewis', 'p_phone': '+1-555-1114'},

                # BSIT Sem 4-A Students (4)
                {'num': 15, 'first': 'Benjamin', 'last': 'Walker', 'gender': CustomUser.Gender.MALE, 'dob': datetime.date(2003, 10, 11), 'blood': 'B+', 'cls': classrooms['BSIT Sem 4-A'], 'roll': 'IT4-01', 'p_name': 'Richard Walker', 'p_phone': '+1-555-1115'},
                {'num': 16, 'first': 'Amelia', 'last': 'Hall', 'gender': CustomUser.Gender.FEMALE, 'dob': datetime.date(2004, 1, 23), 'blood': 'O+', 'cls': classrooms['BSIT Sem 4-A'], 'roll': 'IT4-02', 'p_name': 'Charles Hall', 'p_phone': '+1-555-1116'},
                {'num': 17, 'first': 'James', 'last': 'Allen', 'gender': CustomUser.Gender.MALE, 'dob': datetime.date(2003, 5, 18), 'blood': 'AB+', 'cls': classrooms['BSIT Sem 4-A'], 'roll': 'IT4-03', 'p_name': 'Joseph Allen', 'p_phone': '+1-555-1117'},
                {'num': 18, 'first': 'Harper', 'last': 'Young', 'gender': CustomUser.Gender.FEMALE, 'dob': datetime.date(2003, 9, 30), 'blood': 'A-', 'cls': classrooms['BSIT Sem 4-A'], 'roll': 'IT4-04', 'p_name': 'Walter Young', 'p_phone': '+1-555-1118'},
            ]

            students_list = []
            for s_item in students_data:
                uname = f"student{s_item['num']}"
                adm_no = f"STU-20{s_item['num']:02d}"
                email = f"{uname}@sms.local"

                stu_user, u_created = CustomUser.objects.get_or_create(
                    username=uname,
                    defaults={
                        'email': email,
                        'first_name': s_item['first'],
                        'last_name': s_item['last'],
                        'role': CustomUser.Role.STUDENT,
                        'gender': s_item['gender'],
                        'phone_number': f"+1-555-20{s_item['num']:02d}",
                        'date_of_birth': s_item['dob'],
                        'address': f"Student Residence Hall #{s_item['num']}, University Avenue",
                        'is_active': True,
                    }
                )
                stu_user.set_password("student123")
                stu_user.role = CustomUser.Role.STUDENT
                stu_user.save()
                if u_created:
                    stats['users'] += 1

                student_obj, s_created = Student.objects.get_or_create(
                    user=stu_user,
                    defaults={
                        'admission_number': adm_no,
                        'classroom': s_item['cls'],
                        'roll_number': s_item['roll'],
                        'parent_name': s_item['p_name'],
                        'parent_phone': s_item['p_phone'],
                        'admission_date': datetime.date(2025, 9, 1),
                        'emergency_contact': s_item['p_phone'],
                        'blood_group': s_item['blood'],
                    }
                )
                # Keep classroom assigned if existing
                if student_obj.classroom != s_item['cls']:
                    student_obj.classroom = s_item['cls']
                    student_obj.save()

                students_list.append((student_obj, s_item['cls']))
                if s_created:
                    stats['students'] += 1
                    self.stdout.write(self.style.SUCCESS(f"  [+] Created Student: {s_item['first']} {s_item['last']} ({adm_no})"))
                else:
                    self.stdout.write(f"  [*] Student already exists: {s_item['first']} {s_item['last']} ({adm_no})")

            # 8. ENROLLMENTS
            # Map classrooms to courses:
            classroom_courses_map = {
                classrooms['BSCS Sem 1-A']: [courses_dict['CS101']],
                classrooms['BSCS Sem 3-A']: [courses_dict['CS201'], courses_dict['CS301'], courses_dict['CS401']],
                classrooms['BSSE Sem 2-A']: [courses_dict['SE302']],
                classrooms['BSIT Sem 4-A']: [courses_dict['CS303'], courses_dict['CS402']],
            }

            active_enrollments = []
            for student_obj, cls_obj in students_list:
                courses_for_class = classroom_courses_map.get(cls_obj, [])
                for course_obj in courses_for_class:
                    enrollment, e_created = Enrollment.objects.get_or_create(
                        student=student_obj,
                        course=course_obj,
                        defaults={
                            'enrollment_date': datetime.date(2025, 9, 5),
                            'status': Enrollment.EnrollmentStatus.ACTIVE,
                        }
                    )
                    active_enrollments.append(enrollment)
                    if e_created:
                        stats['enrollments'] += 1

            self.stdout.write(self.style.SUCCESS(f"  [+] Verified {len(active_enrollments)} course enrollments ({stats['enrollments']} newly created)"))

            # 9. ATTENDANCE LOGS
            # Generate 10 past distinct school days (weekdays over past 3 weeks prior to today)
            today = timezone.now().date()
            past_dates = []
            cur_date = today - datetime.timedelta(days=1)
            while len(past_dates) < 10:
                # Monday=0 to Friday=4
                if cur_date.weekday() < 5:
                    past_dates.append(cur_date)
                cur_date -= datetime.timedelta(days=1)
            past_dates.reverse()

            attendance_remarks = {
                Attendance.Status.PRESENT: "",
                Attendance.Status.LATE: "Arrived 10 minutes late due to campus transit delay",
                Attendance.Status.ABSENT: "Unexcused absence",
                Attendance.Status.EXCUSED: "Medical excuse submitted to faculty",
            }

            for idx, enrollment in enumerate(active_enrollments):
                student_obj = enrollment.student
                course_obj = enrollment.course

                for d_idx, att_date in enumerate(past_dates):
                    # Deterministic status pattern based on student id and date index
                    # Ensures realistic attendance: ~80% present, ~10% late, ~5% absent, ~5% excused
                    hash_val = (student_obj.id * 17 + d_idx * 13 + course_obj.id * 7) % 100
                    if hash_val < 75:
                        status = Attendance.Status.PRESENT
                    elif hash_val < 88:
                        status = Attendance.Status.LATE
                    elif hash_val < 95:
                        status = Attendance.Status.EXCUSED
                    else:
                        status = Attendance.Status.ABSENT

                    remarks = attendance_remarks[status]

                    att_obj, a_created = Attendance.objects.get_or_create(
                        student=student_obj,
                        course=course_obj,
                        date=att_date,
                        defaults={
                            'status': status,
                            'remarks': remarks,
                        }
                    )
                    if a_created:
                        stats['attendance'] += 1

            self.stdout.write(self.style.SUCCESS(f"  [+] Generated attendance logs ({stats['attendance']} newly created across {len(past_dates)} dates)"))

            # 10. ACADEMIC RECORDS & GRADES
            # Assessments for each course: Quiz 1 (20), Midterm Exam (100), Assignment 1 (50)
            assessments = [
                ('Quiz 1', AcademicRecord.ExamType.QUIZ, Decimal('20.00'), datetime.date(2025, 10, 15), 0.70, 0.98),
                ('Assignment 1', AcademicRecord.ExamType.ASSIGNMENT, Decimal('50.00'), datetime.date(2025, 11, 10), 0.65, 0.96),
                ('Midterm Exam', AcademicRecord.ExamType.MIDTERM, Decimal('100.00'), datetime.date(2025, 12, 18), 0.55, 0.98),
            ]

            for enrollment in active_enrollments:
                student_obj = enrollment.student
                course_obj = enrollment.course

                for exam_name, exam_type, total_marks, exam_date, min_pct, max_pct in assessments:
                    # Deterministic score distribution across students
                    factor = ((student_obj.id * 23 + course_obj.id * 19 + int(total_marks)) % 100) / 100.0
                    score_pct = min_pct + factor * (max_pct - min_pct)
                    marks_obtained = round(Decimal(str(score_pct)) * total_marks, 2)

                    record, r_created = AcademicRecord.objects.get_or_create(
                        student=student_obj,
                        course=course_obj,
                        exam_name=exam_name,
                        defaults={
                            'exam_type': exam_type,
                            'total_marks': total_marks,
                            'marks_obtained': marks_obtained,
                            'date_recorded': exam_date,
                            'remarks': f"Evaluated and verified for {course_obj.course_code}",
                        }
                    )
                    if r_created:
                        stats['academics'] += 1
                        # save() auto-computes percentage, grade (A+ to F), and grade_point (4.00 to 0.00)

            self.stdout.write(self.style.SUCCESS(f"  [+] Generated academic marks & grade records ({stats['academics']} newly created)"))

        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Seeding Summary ==="))
        self.stdout.write(f"Users created/updated:       {stats['users']} created (Total: {CustomUser.objects.count()})")
        self.stdout.write(f"Teachers created:            {stats['teachers']} created (Total: {Teacher.objects.count()})")
        self.stdout.write(f"Students created:            {stats['students']} created (Total: {Student.objects.count()})")
        self.stdout.write(f"Departments created:         {stats['departments']} created (Total: {Department.objects.count()})")
        self.stdout.write(f"Class Rooms created:         {stats['classrooms']} created (Total: {ClassRoom.objects.count()})")
        self.stdout.write(f"Courses created:             {stats['courses']} created (Total: {Course.objects.count()})")
        self.stdout.write(f"Enrollments created:         {stats['enrollments']} created (Total: {Enrollment.objects.count()})")
        self.stdout.write(f"Attendance records created:  {stats['attendance']} created (Total: {Attendance.objects.count()})")
        self.stdout.write(f"Academic records created:    {stats['academics']} created (Total: {AcademicRecord.objects.count()})")
        self.stdout.write(self.style.SUCCESS("\n[SUCCESS] Realistic sample data seeded successfully!"))
