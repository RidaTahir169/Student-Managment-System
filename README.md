# EduManage - Django Student Management System (SMS)

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![Django Version](https://img.shields.io/badge/django-5.x-green.svg)](https://www.djangoproject.com/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple.svg)](https://getbootstrap.com/)
[![Tests](https://img.shields.io/badge/tests-75%20passing-brightgreen.svg)]()
[![License](https://img.shields.io/badge/license-MIT-orange.svg)]()

EduManage is a comprehensive, modular, and professional web-based Student Management System developed in Python & Django. It provides full lifecycle management for academic institutions, covering student admissions, faculty onboarding, course curriculum, cohort enrollment, daily attendance tracking, exam grading, transcripts, and role-specific dashboards.

---

## Key Features

- **Multi-Role Access Control (RBAC):** Custom portals and strict data isolation for **Administrators**, **Teachers**, and **Students**.
- **Student Profile Management:** Admissions, demographics, parent/guardian info, and course history.
- **Faculty Directory & Workload:** Faculty records, designations, qualifications, and course allocations.
- **Curriculum & Class Cohorts:** Department tracking, academic sessions, classrooms, and course modules.
- **Enrollment Engine:** Single-student enrollment, bulk enrollment, and one-click classroom cohort sync with duplicate prevention.
- **Attendance Tracker:** Daily roll-call, future-date prevention, idempotent updates, and $<75\%$ shortage alerts.
- **Academic Grading & GPA:** Percentage, letter grade (A+ to F), and 4.00 GPA calculation, gradebooks, and report cards.
- **Search & Reports:** Real-time search across all entities, multi-parameter filters, honor rolls, and at-risk student reports.
- **Validation & Security Layer:** Case-insensitive unique IDs, lowercase email uniqueness, CSRF protection, and custom 403/404/500 handlers.
- **Modern Responsive UI:** Mobile slide-out drawer, stat metric cards, soft badges, and clean Inter typography.

---

## Quickstart Guide

### 1. Prerequisites
- Python 3.10+ installed
- Git (optional)

### 2. Setup Virtual Environment & Dependencies

```powershell
# Navigate to project directory
cd "C:\Student Management System"

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install requirements
pip install --upgrade pip
pip install django Pillow
```

### 3. Database Initialization & Migrations

```powershell
# Run migrations
python manage.py makemigrations
python manage.py migrate
```

### 4. Run Automated Test Suite

```powershell
# Run all 75 automated unit and integration tests
python manage.py test
```

### 5. Create Administrator Superuser

```powershell
python manage.py createsuperuser
```

### 6. Start Development Server

```powershell
python manage.py runserver
```

Open your browser at `http://127.0.0.1:8000/`

---

## Full Documentation

For the complete technical report, system architecture diagrams, database data dictionary, user manual, testing reports, and screenshot placeholders, please refer to:
- **[PROJECT_DOCUMENTATION.md](file:///C:/Student%20Management%20System/PROJECT_DOCUMENTATION.md)**

---

## License
This project is open-source under the [MIT License](LICENSE).
