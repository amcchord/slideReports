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
        let lastCountUpdate = 0;
        
        while (this.isSyncing && pollCount < maxPolls) {
            try {
                const response = await fetch('/api/sync/status');
                const data = await response.json();
                
                if (progressContainer) {
                    this.updateProgressDisplay(data.sources, progressContainer, data.current_source);
                }
                
                // Update counts every 5 seconds
                if (pollCount === 0 || pollCount - lastCountUpdate >= 5) {
                    this.updateDataCounts(data.counts);
                    lastCountUpdate = pollCount;
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
    },
    
    /**
     * Update data counts in the dashboard table
     */
    updateDataCounts(counts) {
        if (!counts) return;
        
        const dataSources = [
            'devices',
            'agents', 
            'backups',
            'snapshots',
            'alerts',
            'virtual_machines',
            'clients'
        ];
        
        dataSources.forEach(source => {
            const countElement = document.getElementById(`count-${source}`);
            if (countElement && counts[source] !== undefined) {
                countElement.textContent = counts[source];
            }
        });
    }
};

// Template Manager
const templateManager = {
    /**
     * Generate template with AI using streaming
     */
    async generateTemplate(description, dataSources) {
        const button = document.getElementById('generate-button');
        const progressDiv = document.getElementById('generation-progress');
        
        if (button) {
            button.disabled = true;
            button.innerHTML = '<span class="spinner"></span> Generating...';
        }
        
        if (progressDiv) {
            progressDiv.style.display = 'block';
        }
        
        try {
            // Use EventSource for streaming
            const response = await fetch('/api/templates/generate-stream', {
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
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let accumulatedHtml = '';
            
            // Get editor reference
            const editor = window.monacoEditor || window.monacoEditorInstance;
            const htmlField = document.getElementById('template-html');
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.substring(6));
                            
                            if (data.error) {
                                throw new Error(data.error);
                            }
                            
                            if (data.chunk) {
                                accumulatedHtml += data.chunk;
                                
                                // Update editor in real-time
                                if (editor && editor.setValue) {
                                    editor.setValue(accumulatedHtml);
                                }
                                if (htmlField) {
                                    htmlField.value = accumulatedHtml;
                                }
                            }
                            
                            if (data.done && data.html) {
                                // Final complete HTML
                                if (editor && editor.setValue) {
                                    editor.setValue(data.html);
                                }
                                if (htmlField) {
                                    htmlField.value = data.html;
                                }
                                accumulatedHtml = data.html;
                            }
                        } catch (e) {
                            console.error('Failed to parse streaming data:', e);
                        }
                    }
                }
            }
            
            utils.showToast('Template generated successfully', 'success');
        } catch (error) {
            console.error('Generation error:', error);
            utils.showToast('Generation failed: ' + error.message, 'danger');
        } finally {
            if (button) {
                button.disabled = false;
                button.innerHTML = '<i class="bi bi-magic"></i> Generate Template with AI';
            }
            if (progressDiv) {
                progressDiv.style.display = 'none';
            }
        }
    },
    
    /**
     * Improve existing template with AI
     */
    async improveTemplate(improvementRequest, currentHtml) {
        const button = document.getElementById('improve-button');
        const previewFrame = document.getElementById('template-preview');
        
        if (button) {
            button.disabled = true;
            button.innerHTML = '<span class="spinner"></span> Improving (1-5 minutes)...';
        }
        
        try {
            const response = await fetch('/api/templates/improve', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    current_html: currentHtml,
                    improvement_request: improvementRequest
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Improvement failed');
            }
            
            const data = await response.json();
            
            // Update the hidden textarea
            const htmlField = document.getElementById('template-html');
            if (htmlField) {
                htmlField.value = data.improved_html;
            }
            
            // Update Monaco editor
            const editor = window.monacoEditor || window.monacoEditorInstance;
            if (editor && editor.setValue) {
                editor.setValue(data.improved_html);
            }
            
            // Clear the improvement prompt
            const improvePrompt = document.getElementById('improve-prompt');
            if (improvePrompt) {
                improvePrompt.value = '';
            }
            
            utils.showToast('Template improved successfully', 'success');
        } catch (error) {
            console.error('Improvement error:', error);
            utils.showToast('Improvement failed: ' + error.message, 'danger');
        } finally {
            if (button) {
                button.disabled = false;
                button.innerHTML = '<i class="bi bi-magic"></i> Improve Template with AI';
            }
        }
    },
    
    /**
     * Test template with real data
     */
    async testWithRealData(htmlContent, startDate, endDate, dataSources, clientId) {
        const button = document.getElementById('test-button');
        const previewFrame = document.getElementById('template-preview');
        const errorDisplay = document.getElementById('error-display');
        const previewModeBadge = document.getElementById('preview-mode-badge');
        const previewDescription = document.getElementById('preview-description');
        
        // Hide any previous errors
        if (errorDisplay) {
            errorDisplay.style.display = 'none';
        }
        
        if (button) {
            button.disabled = true;
            button.innerHTML = '<span class="spinner"></span> Testing...';
        }
        
        try {
            const response = await fetch('/api/templates/test', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    html_content: htmlContent,
                    start_date: startDate,
                    end_date: endDate,
                    data_sources: dataSources,
                    client_id: clientId
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Display test results
                if (previewFrame) {
                    const previewDoc = previewFrame.contentDocument || previewFrame.contentWindow.document;
                    previewDoc.open();
                    previewDoc.write(data.html);
                    previewDoc.close();
                }
                
                // Update badge
                if (previewModeBadge) {
                    previewModeBadge.className = 'badge bg-success';
                    previewModeBadge.textContent = 'Real Data Test';
                }
                
                if (previewDescription) {
                    previewDescription.textContent = `Test results with data from ${startDate} to ${endDate}.`;
                }
                
                utils.showToast('Template tested successfully with real data', 'success');
            } else {
                // Show error
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('Test error:', error);
            
            // Show error display with auto-fix option
            if (errorDisplay) {
                const errorMessage = document.getElementById('error-message');
                if (errorMessage) {
                    errorMessage.textContent = error.message;
                }
                errorDisplay.style.display = 'block';
                
                // Store error for auto-fix
                if (window.lastTestError !== undefined) {
                    window.lastTestError = error.message;
                }
            }
            
            utils.showToast('Template test failed: ' + error.message, 'danger');
        } finally {
            if (button) {
                button.disabled = false;
                button.innerHTML = '<i class="bi bi-play-circle"></i> Test with Real Data';
            }
        }
    },
    
    /**
     * Fix template error with AI
     */
    async fixTemplateError(htmlContent, errorMessage) {
        const button = document.getElementById('auto-fix-button');
        const errorDisplay = document.getElementById('error-display');
        
        if (button) {
            button.disabled = true;
            button.innerHTML = '<span class="spinner"></span> Fixing (1-5 minutes)...';
        }
        
        try {
            const response = await fetch('/api/templates/fix-error', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    html_content: htmlContent,
                    error_message: errorMessage
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Fix failed');
            }
            
            const data = await response.json();
            
            // Update the hidden textarea
            const htmlField = document.getElementById('template-html');
            if (htmlField) {
                htmlField.value = data.fixed_html;
            }
            
            // Update Monaco editor
            const editor = window.monacoEditor || window.monacoEditorInstance;
            if (editor && editor.setValue) {
                editor.setValue(data.fixed_html);
            }
            
            // Hide error display
            if (errorDisplay) {
                errorDisplay.style.display = 'none';
            }
            
            utils.showToast('Template fixed! ' + data.explanation, 'success');
            
            // Automatically re-test with the same parameters
            const startDate = document.getElementById('test-start-date').value;
            const endDate = document.getElementById('test-end-date').value;
            if (startDate && endDate) {
                const dataSources = [];
                document.querySelectorAll('input[type="checkbox"]:checked').forEach(cb => {
                    dataSources.push(cb.value);
                });
                
                utils.showToast('Re-testing with fixed template...', 'info');
                setTimeout(() => {
                    this.testWithRealData(data.fixed_html, startDate, endDate, dataSources, null);
                }, 1000);
            }
        } catch (error) {
            console.error('Fix error:', error);
            utils.showToast('Auto-fix failed: ' + error.message, 'danger');
        } finally {
            if (button) {
                button.disabled = false;
                button.innerHTML = '<i class="bi bi-magic"></i> Auto-fix with AI';
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
    async previewReport(templateId, startDate, endDate, dataSources, clientId = null) {
        const previewFrame = document.getElementById('report-preview');
        const button = document.getElementById('preview-button');
        
        if (button) {
            button.disabled = true;
            button.innerHTML = '<span class="spinner"></span> Generating...';
        }
        
        try {
            const requestBody = {
                template_id: templateId,
                start_date: startDate,
                end_date: endDate,
                data_sources: dataSources
            };
            
            if (clientId) {
                requestBody.client_id = clientId;
            }
            
            const response = await fetch('/api/reports/preview', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
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

// Info Banner Manager
const bannerManager = {
    /**
     * Initialize banner close functionality
     */
    init() {
        const banner = document.getElementById('infoBanner');
        const closeButton = document.getElementById('closeBanner');
        
        if (!banner || !closeButton) {
            return;
        }
        
        // Check if banner was previously closed in this session
        if (sessionStorage.getItem('infoBannerClosed') === 'true') {
            banner.classList.add('hidden');
            document.body.classList.add('banner-closed');
        }
        
        // Handle close button click
        closeButton.addEventListener('click', () => {
            banner.classList.add('hidden');
            document.body.classList.add('banner-closed');
            sessionStorage.setItem('infoBannerClosed', 'true');
        });
    }
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('Slide Reports System initialized');
    
    // Initialize banner close functionality
    bannerManager.init();
    
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
    reportManager,
    bannerManager
};

