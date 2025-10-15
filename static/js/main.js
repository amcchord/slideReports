/**
 * Main JavaScript for Slide Reports System
 */

// Utility Functions
const utils = {
    /**
     * Show a toast notification
     */
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `alert alert-${type} position-fixed top-0 end-0 m-3`;
        toast.style.zIndex = '9999';
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 5000);
    },
    
    /**
     * Format bytes to human readable
     */
    formatBytes(bytes) {
        const units = ['B', 'KB', 'MB', 'GB', 'TB'];
        let value = bytes;
        let unitIndex = 0;
        
        while (value >= 1024 && unitIndex < units.length - 1) {
            value /= 1024;
            unitIndex++;
        }
        
        return `${value.toFixed(1)} ${units[unitIndex]}`;
    },
    
    /**
     * Format date/time
     */
    formatDateTime(dateString) {
        if (!dateString) return 'Never';
        const date = new Date(dateString);
        return date.toLocaleString();
    }
};

// Sync Manager
const syncManager = {
    issyncing: false,
    
    /**
     * Start data sync
     */
    async startSync(dataSources) {
        if (this.isSyncing) {
            utils.showToast('Sync already in progress', 'warning');
            return;
        }
        
        this.isSyncing = true;
        const progressContainer = document.getElementById('sync-progress');
        const syncButton = document.getElementById('sync-button');
        
        if (syncButton) {
            syncButton.disabled = true;
            syncButton.innerHTML = '<span class="spinner"></span> Syncing...';
        }
        
        if (progressContainer) {
            progressContainer.style.display = 'block';
        }
        
        try {
            // Start the sync (this will run in background on server)
            const response = await fetch('/api/sync', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ data_sources: dataSources })
            });
            
            if (!response.ok) {
                throw new Error('Sync failed');
            }
            
            // Note: Sync runs synchronously on server, so it's complete when response returns
            // The sync is now complete, show success and reload
            utils.showToast('Sync completed successfully', 'success');
            
            // Force reload to show updated data
            window.location.reload();
        } catch (error) {
            console.error('Sync error:', error);
            utils.showToast('Sync failed: ' + error.message, 'danger');
        } finally {
            this.isSyncing = false;
            if (syncButton) {
                syncButton.disabled = false;
                syncButton.innerHTML = '<i class="bi bi-arrow-repeat"></i> Sync Now';
            }
        }
    },
    
    /**
     * Poll sync status
     */
    async pollSyncStatus() {
        const progressContainer = document.getElementById('sync-progress-items');
        let pollCount = 0;
        const maxPolls = 300; // 5 minutes max (300 * 1000ms)
        
        while (this.isSyncing && pollCount < maxPolls) {
            try {
                const response = await fetch('/api/sync/status');
                const data = await response.json();
                
                if (progressContainer) {
                    this.updateProgressDisplay(data.sources, progressContainer, data.current_source);
                }
                
                // Check sync state
                if (data.sync_state === 'completed' || data.sync_state === 'error') {
                    this.isSyncing = false;
                    break;
                }
                
                await new Promise(resolve => setTimeout(resolve, 1000)); // Poll every second
                pollCount++;
            } catch (error) {
                console.error('Status poll error:', error);
                break;
            }
        }
    },
    
    /**
     * Update progress display
     */
    updateProgressDisplay(status, container, currentSource) {
        container.innerHTML = '';
        
        for (const [key, data] of Object.entries(status)) {
            const item = document.createElement('div');
            item.className = 'sync-item';
            
            let statusBadge = '';
            let progressInfo = '';
            
            if (data.status === 'syncing') {
                const current = data.current_items || 0;
                const total = data.total_items_fetching || '?';
                statusBadge = '<span class="status-badge status-info"><span class="spinner"></span> Syncing</span>';
                progressInfo = `<div class="small text-primary">${current} / ${total} items...</div>`;
            } else if (data.status === 'completed') {
                statusBadge = '<span class="status-badge status-success">✓ Complete</span>';
            } else if (data.status === 'error') {
                statusBadge = '<span class="status-badge status-danger">✗ Error</span>';
            } else {
                statusBadge = '<span class="status-badge">Pending</span>';
            }
            
            item.innerHTML = `
                <div class="sync-item-header">
                    <span class="sync-item-name">${data.name}</span>
                    ${statusBadge}
                </div>
                ${progressInfo}
                <div class="sync-item-status">
                    ${data.total_items || 0} items in database
                    ${data.last_sync ? '• Last: ' + utils.formatDateTime(data.last_sync) : ''}
                </div>
                ${data.error_message ? `<div class="text-danger small">${data.error_message}</div>` : ''}
            `;
            
            container.appendChild(item);
        }
        
        if (currentSource) {
            const msg = document.createElement('div');
            msg.className = 'alert alert-info mb-3';
            msg.innerHTML = `<strong>Currently syncing:</strong> ${status[currentSource]?.name || currentSource}`;
            container.prepend(msg);
        }
    }
};

// Template Manager
const templateManager = {
    /**
     * Generate template with AI
     */
    async generateTemplate(description, dataSources) {
        const button = document.getElementById('generate-button');
        const previewFrame = document.getElementById('template-preview');
        
        if (button) {
            button.disabled = true;
            button.innerHTML = '<span class="spinner"></span> Generating...';
        }
        
        try {
            const response = await fetch('/api/templates/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    description: description,
                    data_sources: dataSources
                })
            });
            
            if (!response.ok) {
                throw new Error('Generation failed');
            }
            
            const data = await response.json();
            
            // Update preview
            if (previewFrame) {
                const previewDoc = previewFrame.contentDocument || previewFrame.contentWindow.document;
                previewDoc.open();
                previewDoc.write(data.html);
                previewDoc.close();
            }
            
            // Update hidden field if exists
            const htmlField = document.getElementById('template-html');
            if (htmlField) {
                htmlField.value = data.html;
            }
            
            utils.showToast('Template generated successfully', 'success');
        } catch (error) {
            console.error('Generation error:', error);
            utils.showToast('Generation failed: ' + error.message, 'danger');
        } finally {
            if (button) {
                button.disabled = false;
                button.innerHTML = '<i class="bi bi-magic"></i> Generate Template';
            }
        }
    },
    
    /**
     * Save template
     */
    async saveTemplate(name, description, htmlContent) {
        try {
            const response = await fetch('/api/templates', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name: name,
                    description: description,
                    html_content: htmlContent
                })
            });
            
            if (!response.ok) {
                throw new Error('Save failed');
            }
            
            const data = await response.json();
            utils.showToast('Template saved successfully', 'success');
            
            // Redirect to templates list
            setTimeout(() => {
                window.location.href = '/templates';
            }, 1000);
        } catch (error) {
            console.error('Save error:', error);
            utils.showToast('Save failed: ' + error.message, 'danger');
        }
    }
};

// Report Manager
const reportManager = {
    /**
     * Preview report
     */
    async previewReport(templateId, startDate, endDate, dataSources) {
        const previewFrame = document.getElementById('report-preview');
        const button = document.getElementById('preview-button');
        
        if (button) {
            button.disabled = true;
            button.innerHTML = '<span class="spinner"></span> Generating...';
        }
        
        try {
            const response = await fetch('/api/reports/preview', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    template_id: templateId,
                    start_date: startDate,
                    end_date: endDate,
                    data_sources: dataSources
                })
            });
            
            if (!response.ok) {
                throw new Error('Preview generation failed');
            }
            
            const data = await response.json();
            
            // Display preview
            if (previewFrame) {
                const previewDoc = previewFrame.contentDocument || previewFrame.contentWindow.document;
                previewDoc.open();
                previewDoc.write(data.html);
                previewDoc.close();
            }
            
            utils.showToast('Preview generated successfully', 'success');
        } catch (error) {
            console.error('Preview error:', error);
            utils.showToast('Preview failed: ' + error.message, 'danger');
        } finally {
            if (button) {
                button.disabled = false;
                button.innerHTML = '<i class="bi bi-eye"></i> Preview Report';
            }
        }
    },
    
    /**
     * Print report
     */
    printReport() {
        const previewFrame = document.getElementById('report-preview');
        if (previewFrame && previewFrame.contentWindow) {
            previewFrame.contentWindow.print();
        }
    }
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('Slide Reports System initialized');
    
    // Auto-hide alerts after 5 seconds
    document.querySelectorAll('.alert:not(.alert-permanent)').forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });
});

// Export for global access
window.slideReports = {
    utils,
    syncManager,
    templateManager,
    reportManager
};

