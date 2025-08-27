class ChartManager {
    constructor() {
        this.charts = new Map();
    }
    
    createChart(id, options) {
        this.destroyChart(id); // Clean up existing chart
        const chart = new ApexCharts(document.querySelector(id), options);
        chart.render();
        this.charts.set(id, chart);
        return chart;
    }
    
    destroyChart(id) {
        const chart = this.charts.get(id);
        if (chart) {
            chart.destroy();
            this.charts.delete(id);
        }
    }
    
    destroyAll() {
        for (const [id, chart] of this.charts) {
            chart.destroy();
        }
        this.charts.clear();
    }
}

window.addEventListener('beforeunload', () => {
    if (window.chartManager) {
        window.chartManager.destroyAll();
    }
});

class ErrorBoundary {
    static initialize() {
        window.addEventListener('error', this.handleError);
        window.addEventListener('unhandledrejection', this.handlePromiseRejection);
    }
    
    static handleError(event) {
        console.error('Global error:', event.error);
        this.showRecoveryOptions('An unexpected error occurred.');
    }
    
    static handlePromiseRejection(event) {
        console.error('Unhandled promise rejection:', event.reason);
        this.showRecoveryOptions('A network or processing error occurred.');
    }
    
    static showRecoveryOptions(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'position-fixed top-0 start-50 translate-middle-x mt-3 alert alert-danger alert-dismissible fade show';
        errorDiv.style.zIndex = '9999';
        errorDiv.innerHTML = `
            <i class="fas fa-exclamation-triangle"></i> 
            <strong>Error:</strong> ${message}
            <div class="mt-2">
                <button class="btn btn-sm btn-outline-light me-2" onclick="location.reload()">
                    <i class="fas fa-refresh"></i> Refresh Page
                </button>
                <button class="btn btn-sm btn-outline-light" onclick="this.closest('.alert').remove()">
                    <i class="fas fa-times"></i> Dismiss
                </button>
            </div>
        `;
        document.body.appendChild(errorDiv);
    }
}

ErrorBoundary.initialize();

class PerformanceMonitor {
    static trackOperation(name, operation) {
        const start = performance.now();
        
        return Promise.resolve(operation()).finally(() => {
            const duration = performance.now() - start;
            console.log(`Operation ${name} took ${duration.toFixed(2)}ms`);
            
            if (duration > 5000) {
                console.warn(`Slow operation detected: ${name} (${duration.toFixed(2)}ms)`);
            }
        });
    }
}

function initializeApp() {
    const socket = io();
    const connectionManager = new ConnectionManager(socket);
    const chartManager = new ChartManager();
    const uploadManager = new UploadManager();

    // Debug: Check if elements exist
    console.log('Search button found:', searchBtn);
    console.log('Email entry found:', userEmailEntry);
    console.log('Deep dive results found:', deepDiveResults);
    console.log('Chart container found:', deepDiveChartContainer);
    
    // Manual tab handling as fallback
    const analysisTab = document.getElementById('analysis-tab');
    const deepdiveTab = document.getElementById('deepdive-tab');
    const analysisPane = document.getElementById('analysis-pane');
    const deepdivePane = document.getElementById('deepdive-pane');
    
    if (deepdiveTab && analysisTab && analysisPane && deepdivePane) {
        deepdiveTab.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('Deep dive tab clicked');
            
            // Remove active classes
            analysisTab.classList.remove('active');
            analysisPane.classList.remove('show', 'active');
            
            // Add active classes
            deepdiveTab.classList.add('active');
            deepdivePane.classList.add('show', 'active');
        });
        
        analysisTab.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('Analysis tab clicked');
            
            // Remove active classes
            deepdiveTab.classList.remove('active');
            deepdivePane.classList.remove('show', 'active');
            
            // Add active classes
            analysisTab.classList.add('active');
            analysisPane.classList.add('show', 'active');
        });
    }

    // Charting Setup with modern styling
    function createDistributionChart(elementId) {
        const options = {
            chart: { 
                type: 'donut', 
                height: 280, 
                background: 'transparent',
                foreColor: '#888',
                toolbar: { show: false },
                animations: {
                    enabled: true,
                    easing: 'easeinout',
                    speed: 800,
                    animateGradually: {
                        enabled: true,
                        delay: 150
                    },
                    dynamicAnimation: {
                        enabled: true,
                        speed: 350
                    }
                }
            },
            series: [],
            labels: [],
            // Meaningful colors that work well on dark backgrounds
            // Power Users: Bright green (high performance)
            // Consistent Users: Teal (steady, reliable)
            // Coaching Needed: Amber (warning, needs attention)
            // New Users: Blue (fresh, learning)
            // License Recapture: Muted red (inactive, remove)
            colors: ["#39FF14", "#14b8a6", "#f59e0b", "#60a5fa", "#dc2626"],
            plotOptions: { 
                pie: { 
                    donut: { 
                        size: '65%',
                        labels: { 
                            show: true, 
                            total: { 
                                show: true, 
                                label: 'Total',
                                fontSize: '16px',
                                fontWeight: 600,
                                color: '#fff',
                                formatter: function (w) {
                                    return w.globals.seriesTotals.reduce((a, b) => a + b, 0)
                                }
                            } 
                        } 
                    },
                    expandOnClick: true,
                    dataLabels: {
                        offset: 0,
                        minAngleToShowLabel: 10
                    }
                } 
            },
            legend: { 
                position: 'bottom', 
                labels: { colors: ['#888'] },
                fontSize: '12px'
            },
            stroke: {
                show: true,
                width: 2,
                colors: ['#1a1a1a']  // Dark stroke to separate segments
            },
            dataLabels: {
                enabled: true,
                style: {
                    fontSize: '12px',
                    fontWeight: '600',
                    colors: ['#000', '#fff', '#000', '#000', '#fff']  // Black text on bright colors, white on dark
                },
                dropShadow: {
                    enabled: true,
                    top: 1,
                    left: 1,
                    blur: 1,
                    opacity: 0.5
                }
            },
            theme: { mode: 'dark' }
        };
        const chart = new ApexCharts(document.querySelector(elementId), options);
        chart.render();
        return chart;
    }
    const distributionChart = chartManager.createChart("#distribution-chart", options);

    // File Handling with modern UI feedback
    const handleFileUpload = (file, type, statusElement) => {
        return uploadManager.queueUpload(file, type, statusElement)
        .then(data => {
             if (data.status === 'success') {
                 if (data.type === 'target') {
                     // For target file, show individual file status
                     const statusDiv = document.createElement('div');
                     statusDiv.className = 'status-message status-success';
                     statusDiv.innerHTML = `<i class="fas fa-check-circle"></i> ${file.name} loaded successfully`;
                     statusElement.appendChild(statusDiv);
                     
                     populateSelect('company-filter', data.filters.companies);
                     populateSelect('department-filter', data.filters.departments);
                     populateSelect('location-filter', data.filters.locations);
                     populateSelect('manager-filter', data.filters.managers, window.preSelectedManagers);

                     if (window.preSelectedManagers && window.preSelectedManagers.length > 0) {
                         const statusDiv = document.createElement('div');
                         statusDiv.className = 'status-message status-success mt-2';
                         statusDiv.innerHTML = `<i class="fas fa-check-circle"></i> Preset managers selected`;
                         statusElement.appendChild(statusDiv);
                         setTimeout(() => statusDiv.remove(), 3000);
                     }
                 } else if (data.type === 'usage') {
                     uploadedUsageFiles.push(data.filename);
                 }                return data; // Resolve promise
            } else { throw new Error(data.message || 'File upload failed.'); }
        })
        .catch(error => {
            console.error('Upload Error:', error);
            if (type === 'target') {
                const statusDiv = document.createElement('div');
                statusDiv.className = 'status-message status-error';
                statusDiv.innerHTML = `<i class="fas fa-exclamation-circle"></i> Failed to upload ${file.name}`;
                statusElement.appendChild(statusDiv);
            }
            throw error; // Reject promise
        });
    };

    targetUsersFile.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            targetFileStatus.innerHTML = '';
            const filterSelects = ['company-filter', 'department-filter', 'location-filter', 'manager-filter'];
            filterSelects.forEach(id => {
                const select = document.getElementById(id);
                select.innerHTML = '<option>Loading...</option>';
                select.disabled = true;
            });
            handleFileUpload(e.target.files[0], 'target', targetFileStatus).finally(() => {
                filterSelects.forEach(id => {
                    document.getElementById(id).disabled = false;
                });
            });
        }
    });
    usageReports.addEventListener('change', (e) => {
        if (e.target.files.length === 0) return;
        usageFilesStatus.innerHTML = '';
        uploadedUsageFiles = []; 
        runAnalysisBtn.disabled = true;
        runAnalysisBtn.innerHTML = `<span class="loading-spinner"></span> Uploading Files...`;

        const totalFiles = e.target.files.length;
        let successCount = 0;
        let failCount = 0;

        const uploadPromises = [...e.target.files].map(file => 
            handleFileUpload(file, 'usage', usageFilesStatus)
                .then(() => { successCount++; })
                .catch(() => { failCount++; })
        );
        
        Promise.allSettled(uploadPromises)
            .then(() => {
                runAnalysisBtn.disabled = false;
                runAnalysisBtn.innerHTML = '<i class="fas fa-play"></i> Run Analysis';
                
                // Show single summary bubble
                usageFilesStatus.innerHTML = '';
                if (successCount > 0) {
                    const statusDiv = document.createElement('div');
                    statusDiv.className = 'status-message status-success';
                    statusDiv.innerHTML = `<i class="fas fa-check-circle"></i> ${successCount} usage report${successCount > 1 ? 's' : ''} loaded successfully`;
                    usageFilesStatus.appendChild(statusDiv);
                }
                
                if (failCount > 0) {
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'status-message status-error';
                    errorDiv.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${failCount} file${failCount > 1 ? 's' : ''} failed to upload`;
                    usageFilesStatus.appendChild(errorDiv);
                }
                
                console.log(`Upload complete: ${successCount} succeeded, ${failCount} failed out of ${totalFiles} total.`);
            });
    });

    // Socket.IO Handlers
    socket.on('connect', () => console.log('Socket.IO connection established!'));
    socket.on('status_update', (data) => {
        statusLabel.innerHTML = `<i class="fas fa-cog fa-spin"></i> ${data.message}`;
        statusLabel.style.color = '#888';
    });
    
    socket.on('analysis_complete', (data) => {
        runAnalysisBtn.disabled = false;
        runAnalysisBtn.innerHTML = '<i class="fas fa-play"></i> Run Analysis';
        statusLabel.innerHTML = '<i class="fas fa-check-circle"></i> Analysis complete!';
        statusLabel.style.color = '#39FF14';
        
        const { total, categories } = data.dashboard;
        
        // Animate the total users counter
        const totalElement = document.getElementById('total-users');
        let currentValue = 0;
        const targetValue = total;
        const increment = Math.ceil(targetValue / 30);
        const timer = setInterval(() => {
            currentValue += increment;
            if (currentValue >= targetValue) {
                currentValue = targetValue;
                clearInterval(timer);
            }
            totalElement.textContent = currentValue;
        }, 30);
        
        distributionChart.updateSeries([
            categories.power_user || 0,
            categories.consistent_user || 0,
            categories.coaching || 0,
            categories.new_user || 0,
            categories.recapture || 0
        ]);
        distributionChart.updateOptions({
            labels: ['Power Users', 'Consistent Users', 'Coaching Needed', 'New Users', 'License Recapture']
        });
        
        reportDataForDownload = data.reports;
        reportDataForDownload.excel_bytes = undefined;
        reportsContainer.style.display = 'block';
        
        // Add a subtle animation to the reports container
        reportsContainer.style.opacity = '0';
        setTimeout(() => {
            reportsContainer.style.transition = 'opacity 0.5s ease';
            reportsContainer.style.opacity = '1';
        }, 100);
    });

    socket.on('analysis_error', (data) => {
        runAnalysisBtn.disabled = false;
        runAnalysisBtn.innerHTML = '<i class="fas fa-play"></i> Run Analysis';
        statusLabel.innerHTML = `<i class="fas fa-exclamation-triangle"></i> Error: ${data.message}`;
        statusLabel.style.color = '#ef4444';
        
        // Show a more modern error notification instead of alert
        showErrorNotification(`Analysis Error: ${data.message}`);
    });

    socket.on('deep_dive_result', (data) => {
        deepDiveResults.textContent = data.text;
        if (deepDiveChart) {
            chartManager.destroyChart("deep-dive-chart-container");
        }
        const chartOptions = {
            chart: { 
                type: 'line', 
                height: 380, 
                background: 'transparent', 
                foreColor: '#888',
                toolbar: { show: false },
                animations: {
                    enabled: true,
                    easing: 'easeinout',
                    speed: 800
                }
            },
            series: data.chart_data.series,
            xaxis: { 
                categories: data.chart_data.categories, 
                labels: { 
                    style: { colors: '#888' },
                    rotate: -45
                },
                axisBorder: { color: '#333' },
                axisTicks: { color: '#333' }
            },
            yaxis: { 
                title: { 
                    text: 'Average Tools Used', 
                    style: { color: '#888', fontSize: '14px' } 
                }, 
                labels: { style: { colors: '#888' } },
                axisBorder: { color: '#333' },
                axisTicks: { color: '#333' }
            },
            colors: ['#39FF14', '#60a5fa', '#ef4444'],
            stroke: {
                curve: 'smooth',
                width: 3
            },
            markers: {
                size: 0,  // Hide markers by default
                hover: { size: 5 } // Show markers on hover
            },
            legend: { 
                labels: { colors: '#888' },
                position: 'top',
                horizontalAlign: 'right'
            },
            grid: { 
                borderColor: '#333',
                strokeDashArray: 4
            },
            tooltip: { 
                theme: 'dark',
                x: { format: 'dd MMM yyyy' }
            }
        };
        deepDiveChart = chartManager.createChart("deep-dive-chart-container", chartOptions);
    });
    socket.on('deep_dive_error', (data) => {
        deepDiveResults.textContent = `Error: ${data.message}`;
        deepDiveResults.style.color = '#ef4444';
        
        // Clear the chart container
        if (deepDiveChartContainer) {
            deepDiveChartContainer.innerHTML = '';
        }
        
        // Show error notification
        showErrorNotification(`Deep Dive Error: ${data.message}`);
    });

    // Action Button Listeners
    runAnalysisBtn.addEventListener('click', async () => {
        runAnalysisBtn.disabled = true;
        runAnalysisBtn.innerHTML = `<span class="loading-spinner"></span> Analyzing...`;
        reportsContainer.style.display = 'none';
        statusLabel.innerHTML = '<i class="fas fa-cog fa-spin"></i> Starting analysis...';
        statusLabel.style.color = 'var(--neon-green)';
        const filters = {
            companies: getSelectedOptions('company-filter'),
            departments: getSelectedOptions('department-filter'),
            locations: getSelectedOptions('location-filter'),
            managers: getSelectedOptions('manager-filter'),
        };
        try {
            await PerformanceMonitor.trackOperation('start_analysis', async () => {
                await RetryManager.withRetry(async () => {
                    socket.emit('start_analysis', { 
                        filters: filters,
                        usage_filenames: uploadedUsageFiles 
                    });
                });
            });
        } catch (error) {
            // This error will be caught by the socket.on('analysis_error') handler
            // or the global error boundary if it's a critical failure before emit
            console.error('Analysis initiation failed:', error);
            showErrorNotification('Analysis failed after multiple attempts. Please refresh and try again.');
        }
    });
    
    downloadBtn.addEventListener('click', () => {
        // --- THIS IS THE FIX ---
        // Use the report data that was saved in the browser
        if (reportDataForDownload) {
            triggerDownload(reportDataForDownload.excel_b64, `Copilot Analysis Report.xlsx`, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
            setTimeout(() => triggerDownload(reportDataForDownload.html_b64, 'leaderboard.html', 'text/html'), 500);
        } else {
            alert('No report data available to download.');
        }
    });

    // Add click handler with error catching
    if (searchBtn) {
        console.log('Adding click handler to search button');
        searchBtn.onclick = function(e) {
            e.preventDefault();
            console.log('Search button clicked!');
            
            try {
                const email = userEmailEntry.value.trim();
                console.log('Email value:', email);
                
                if (email) {
                    deepDiveResults.textContent = "Searching...";
                    deepDiveResults.style.color = '#888';
                    
                    if (deepDiveChart) {
                        chartManager.destroyChart("deep-dive-chart-container");
                        deepDiveChartContainer.innerHTML = '<div class="d-flex justify-content-center align-items-center h-100"><span class="loading-spinner"></span></div>';
                    }
                    
                    console.log('Emitting deep dive request for:', email);
                    PerformanceMonitor.trackOperation('perform_deep_dive', async () => {
                        socket.emit('perform_deep_dive', { email: email });
                    });
                } else {
                    console.log('No email entered');
                    showWarningNotification('Please enter an email address to search.');
                }
            } catch (error) {
                console.error('Error in search button handler:', error);
            }
        };
    } else {
        console.error('Search button not found!');
    }
    
    function showErrorNotification(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'position-fixed top-0 start-50 translate-middle-x mt-3 alert alert-danger alert-dismissible fade show';
        errorDiv.style.zIndex = '9999';
        errorDiv.innerHTML = `
            <i class="fas fa-exclamation-circle"></i> <strong>Error:</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(errorDiv);
        setTimeout(() => errorDiv.remove(), 5000);
    }

    function showWarningNotification(message) {
        const warningDiv = document.createElement('div');
        warningDiv.className = 'position-fixed top-0 start-50 translate-middle-x mt-3 alert alert-warning alert-dismissible fade show';
        warningDiv.style.zIndex = '9999';
        warningDiv.innerHTML = `
            <i class="fas fa-exclamation-triangle"></i> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(warningDiv);
        setTimeout(() => warningDiv.remove(), 3000);
    }

    // Also add Enter key support for the email input
    if (userEmailEntry) {
        userEmailEntry.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                searchBtn.click();
            }
        });
    }

    // Helper Functions
    function populateSelect(selectId, options, preSelected = []) {
        const select = document.getElementById(selectId);
        select.innerHTML = '';
        if (options) {
            options.forEach(optionText => {
                const option = document.createElement('option');
                option.value = optionText;
                option.textContent = optionText;
                if (preSelected.includes(optionText)) {
                    option.selected = true;
                }
                select.appendChild(option);
            });
        }
    }
    function getSelectedOptions(selectId) {
        const select = document.getElementById(selectId);
        return [...select.selectedOptions].map(option => option.value);
    }
    function triggerDownload(base64Data, fileName, mimeType) {
        const byteCharacters = atob(base64Data);
        const byteNumbers = new Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i++) {
            byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);
        const blob = new Blob([byteArray], { type: mimeType });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = fileName;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(link.href);
    }


class ConnectionManager {
    constructor(socket) {
        this.socket = socket;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.setupConnectionHandlers();
    }
    
    setupConnectionHandlers() {
        this.socket.on('connect', () => {
            console.log('Connected to server');
            this.reconnectAttempts = 0;
            this.showConnectionStatus('connected');
        });
        
        this.socket.on('disconnect', () => {
            console.log('Disconnected from server');
            this.showConnectionStatus('disconnected');
            this.attemptReconnect();
        });
        
        this.socket.on('connect_error', (error) => {
            console.error('Connection error:', error);
            this.showConnectionStatus('error');
        });
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => {
                console.log(`Reconnection attempt ${this.reconnectAttempts}`);
                this.socket.connect();
            }, Math.pow(2, this.reconnectAttempts) * 1000);
        }
    }
    
    showConnectionStatus(status) {
        // Update UI to show connection status
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            statusElement.className = `connection-status ${status}`;
            statusElement.textContent = status === 'connected' ? 'Connected' : 
                                      status === 'disconnected' ? 'Reconnecting...' : 'Connection Error';
        }
    }
}

class UploadManager {
    constructor() {
        this.uploadQueue = [];
        this.isUploading = false;
        this.uploadedFiles = new Map();
    }
    
    async queueUpload(file, type, statusElement) {
        return new Promise((resolve, reject) => {
            this.uploadQueue.push({ file, type, statusElement, resolve, reject });
            this.processQueue();
        });
    }
    
    async processQueue() {
        if (this.isUploading || this.uploadQueue.length === 0) return;
        
        this.isUploading = true;
        const upload = this.uploadQueue.shift();
        
        try {
            const result = await this.performUpload(upload);
            upload.resolve(result);
        } catch (error) {
            upload.reject(error);
        } finally {
            this.isUploading = false;
            this.processQueue();
        }
    }
    
    async performUpload(upload) {
        const { file, type, statusElement } = upload;
        const formData = new FormData();
        formData.append('file', file);
        formData.append('file_type', type);
        
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || 'Upload failed');
        }
        
        return await response.json();
    }
}
});
