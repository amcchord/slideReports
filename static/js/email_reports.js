/**
 * Email Reports Management JavaScript
 */

let schedules = [];
let currentScheduleId = null;
let deleteScheduleId = null;

// Load schedules on page load
document.addEventListener('DOMContentLoaded', function() {
    loadSchedules();
});

/**
 * Load all email schedules
 */
async function loadSchedules() {
    try {
        const response = await fetch('/api/email-schedules');
        if (!response.ok) {
            throw new Error('Failed to load schedules');
        }
        
        schedules = await response.json();
        renderSchedules();
    } catch (error) {
        console.error('Error loading schedules:', error);
        showError('Failed to load email schedules');
    }
}

/**
 * Render schedules to the page
 */
function renderSchedules() {
    const container = document.getElementById('schedules-container');
    
    if (schedules.length === 0) {
        container.innerHTML = `
            <div class="text-center py-5">
                <i class="bi bi-envelope" style="font-size: 3rem; color: #ccc;"></i>
                <h3 class="mt-3">No Email Schedules Yet</h3>
                <p class="text-muted">Create your first email schedule to start sending automated reports.</p>
                <a href="/email-reports/create" class="btn btn-primary">
                    <i class="bi bi-plus-circle"></i> Create Schedule
                </a>
            </div>
        `;
        return;
    }
    
    const dateRangeLabels = {
        'last_day': 'Last Day',
        '7_days': '7 Days',
        '30_days': '30 Days',
        '90_days': '90 Days'
    };
    
    const formatLabels = {
        'html': 'HTML',
        'pdf': 'PDF',
        'both': 'HTML & PDF'
    };
    
    let html = '';
    schedules.forEach(schedule => {
        const enabled = schedule.enabled === 1;
        const statusBadge = enabled 
            ? '<span class="badge badge-enabled">Enabled</span>'
            : '<span class="badge badge-disabled">Disabled</span>';
        
        const attachmentFormat = schedule.attachment_format || 'html';
        const subjectPreview = schedule.email_subject 
            ? (schedule.email_subject.length > 50 ? schedule.email_subject.substring(0, 50) + '...' : schedule.email_subject)
            : 'Slide Backup Report - {{ date_range }}';
        
        html += `
            <div class="schedule-card">
                <div class="row align-items-center">
                    <div class="col-md-8">
                        <h5>${escapeHtml(schedule.name)} ${statusBadge}</h5>
                        <p class="mb-1">
                            <i class="bi bi-envelope-fill"></i> 
                            <strong>To:</strong> ${escapeHtml(schedule.email_address)}
                        </p>
                        <p class="mb-1">
                            <i class="bi bi-file-earmark-text"></i> 
                            <strong>Template:</strong> ${escapeHtml(schedule.template_name)}
                        </p>
                        <p class="mb-1">
                            <i class="bi bi-calendar-range"></i> 
                            <strong>Date Range:</strong> 
                            <span class="date-range-badge">${dateRangeLabels[schedule.date_range_type] || schedule.date_range_type}</span>
                        </p>
                        <p class="mb-1">
                            <i class="bi bi-building"></i> 
                            <strong>Client:</strong> ${escapeHtml(schedule.client_name)}
                        </p>
                        <p class="mb-1">
                            <i class="bi bi-paperclip"></i> 
                            <strong>Format:</strong> ${formatLabels[attachmentFormat]}
                        </p>
                        <p class="mb-0 text-muted small">
                            <i class="bi bi-chat-text"></i> 
                            <strong>Subject:</strong> <em>${escapeHtml(subjectPreview)}</em>
                        </p>
                    </div>
                    <div class="col-md-4 text-md-end mt-3 mt-md-0">
                        <button class="btn btn-success btn-sm mb-1" onclick="testSendSchedule(${schedule.schedule_id})" id="testBtn${schedule.schedule_id}">
                            <span class="loading-spinner"></span>
                            <i class="bi bi-send-fill"></i> Test Send
                        </button>
                        <a href="/email-reports/edit/${schedule.schedule_id}" class="btn btn-primary btn-sm mb-1">
                            <i class="bi bi-pencil"></i> Edit
                        </a>
                        <button class="btn btn-danger btn-sm mb-1" onclick="confirmDelete(${schedule.schedule_id})">
                            <i class="bi bi-trash"></i> Delete
                        </button>
                    </div>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// Modal functions removed - now using dedicated pages for create/edit

/**
 * Confirm delete schedule
 */
function confirmDelete(scheduleId) {
    deleteScheduleId = scheduleId;
    const modal = new bootstrap.Modal(document.getElementById('deleteModal'));
    modal.show();
    
    document.getElementById('confirmDeleteBtn').onclick = async function() {
        await deleteSchedule(scheduleId);
        modal.hide();
    };
}

/**
 * Delete schedule
 */
async function deleteSchedule(scheduleId) {
    try {
        const response = await fetch(`/api/email-schedules/${scheduleId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error('Failed to delete schedule');
        }
        
        await loadSchedules();
        showSuccess('Schedule deleted successfully');
    } catch (error) {
        console.error('Error deleting schedule:', error);
        showError('Failed to delete schedule');
    }
}

/**
 * Test send email for a schedule
 */
async function testSendSchedule(scheduleId) {
    const button = document.getElementById(`testBtn${scheduleId}`);
    button.classList.add('sending');
    button.disabled = true;
    
    try {
        const response = await fetch(`/api/email-schedules/${scheduleId}/test`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'Failed to send test email');
        }
        
        showSuccess('Test email sent successfully! Check your inbox.');
    } catch (error) {
        console.error('Error sending test email:', error);
        showError(error.message);
    } finally {
        button.classList.remove('sending');
        button.disabled = false;
    }
}

/**
 * Show success message
 */
function showSuccess(message) {
    // Create temporary alert
    const alert = document.createElement('div');
    alert.className = 'alert alert-success alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3';
    alert.style.zIndex = '9999';
    alert.innerHTML = `
        <i class="bi bi-check-circle-fill"></i> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alert);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        alert.remove();
    }, 5000);
}

/**
 * Show error message
 */
function showError(message) {
    // Create temporary alert
    const alert = document.createElement('div');
    alert.className = 'alert alert-danger alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3';
    alert.style.zIndex = '9999';
    alert.innerHTML = `
        <i class="bi bi-exclamation-triangle-fill"></i> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alert);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        alert.remove();
    }, 5000);
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

