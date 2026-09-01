/**
 * Student Management System - Main UI Script (Phase 18 UI Polish)
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Mobile Sidebar Drawer Handler
    const sidebarToggleBtn = document.getElementById('sidebarToggleBtn');
    const appSidebar = document.getElementById('appSidebar');
    const sidebarBackdrop = document.getElementById('sidebarBackdrop');

    if (sidebarToggleBtn && appSidebar) {
        sidebarToggleBtn.addEventListener('click', function (e) {
            e.preventDefault();
            appSidebar.classList.toggle('show');
            if (sidebarBackdrop) {
                sidebarBackdrop.classList.toggle('show');
            }
        });
    }

    if (sidebarBackdrop) {
        sidebarBackdrop.addEventListener('click', function () {
            if (appSidebar) {
                appSidebar.classList.remove('show');
            }
            sidebarBackdrop.classList.remove('show');
        });
    }

    // 2. Auto-Dismiss Alert Messages after 5 seconds with smooth fade
    const autoDismissAlerts = document.querySelectorAll('.alert-dismissible');
    autoDismissAlerts.forEach(function (alertElement) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alertElement);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 5000);
    });

    // 3. Initialize Bootstrap Tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl, {
            boundary: document.body
        });
    });

    // 4. Initialize Bootstrap Popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // 5. Select All Checkbox Helper in Form Tables (e.g. Enrollments & Course Assignments)
    const selectAllCheckboxes = document.querySelectorAll('[data-select-all]');
    selectAllCheckboxes.forEach(function (masterCheckbox) {
        masterCheckbox.addEventListener('change', function () {
            const targetSelector = masterCheckbox.getAttribute('data-select-all');
            const targetCheckboxes = document.querySelectorAll(targetSelector);
            targetCheckboxes.forEach(function (cb) {
                cb.checked = masterCheckbox.checked;
            });
        });
    });
});
