document.addEventListener("DOMContentLoaded", function() {
    const socket = io();
    
    let uploadedUsageFiles = [];
    let reportDataForDownload = null;

    // UI Elements
    const runAnalysisBtn = document.getElementById('run-analysis-btn');
    const statusLabel = document.getElementById('status-label');
    const reportsContainer = document.getElementById('reports-container');
    const downloadBtn = document.getElementById('download-btn');
    const targetUsersFile = document.getElementById('targetUsersFile');
    const usageReports = document.getElementById('usageReports');
    const targetFileStatus = document.getElementById('target-file-status');
    const usageFilesStatus = document.getElementById('usage-files-status');
    const searchBtn = document.getElementById('search-btn');
    const userEmailEntry = document.getElementById('user-email-entry');
    const deepDiveResults = document.getElementById('deep-dive-results');
    const deepDiveChartContainer = document.getElementById('deep-dive-chart-container');
    let deepDiveChart = null;
    
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
    const distributionChart = createDistributionChart("#distribution-chart");

    // File Handling with modern UI feedback
    const handleFileUpload = (file, type, statusElement) => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('file_type', type);
        return fetch('/upload', { method: 'POST', body: formData })
        .then(response => {
            if (!response.ok) { return response.json().then(err => { throw new Error(err.message || 'Network response was not ok.') }); }
            return response.json();
        })
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
                     populateSelect('manager-filter', data.filters.managers, preSelectedManagers);
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
            handleFileUpload(e.target.files[0], 'target', targetFileStatus);
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
        const errorDiv = document.createElement('div');
        errorDiv.className = 'position-fixed top-0 start-50 translate-middle-x mt-3 alert alert-danger alert-dismissible fade show';
        errorDiv.style.zIndex = '9999';
        errorDiv.innerHTML = `
            <i class="fas fa-exclamation-circle"></i> <strong>Analysis Error:</strong> ${data.message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(errorDiv);
        setTimeout(() => errorDiv.remove(), 5000);
    });

    socket.on('deep_dive_result', (data) => {
        deepDiveResults.textContent = data.text;
        if (deepDiveChart) {
            deepDiveChart.destroy();
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
        deepDiveChart = new ApexCharts(deepDiveChartContainer, chartOptions);
        deepDiveChart.render();
    });
    socket.on('deep_dive_error', (data) => {
        deepDiveResults.textContent = `Error: ${data.message}`;
        deepDiveResults.style.color = '#ef4444';
        
        // Clear the chart container
        if (deepDiveChartContainer) {
            deepDiveChartContainer.innerHTML = '';
        }
        
        // Show error notification
        const errorDiv = document.createElement('div');
        errorDiv.className = 'position-fixed top-0 start-50 translate-middle-x mt-3 alert alert-danger alert-dismissible fade show';
        errorDiv.style.zIndex = '9999';
        errorDiv.innerHTML = `
            <i class="fas fa-exclamation-circle"></i> <strong>Deep Dive Error:</strong> ${data.message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(errorDiv);
        setTimeout(() => errorDiv.remove(), 5000);
    });

    // Action Button Listeners
    runAnalysisBtn.addEventListener('click', () => {
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
        socket.emit('start_analysis', { 
            filters: filters,
            usage_filenames: uploadedUsageFiles 
        });
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
                        deepDiveChart.destroy();
                        deepDiveChartContainer.innerHTML = '<div class="d-flex justify-content-center align-items-center h-100"><span class="loading-spinner"></span></div>';
                    }
                    
                    console.log('Emitting deep dive request for:', email);
                    socket.emit('perform_deep_dive', { email: email });
                } else {
                    console.log('No email entered');
                    // Show modern error notification
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'position-fixed top-0 start-50 translate-middle-x mt-3 alert alert-warning alert-dismissible fade show';
                    errorDiv.style.zIndex = '9999';
                    errorDiv.innerHTML = `
                        <i class="fas fa-exclamation-triangle"></i> Please enter an email address to search.
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    `;
                    document.body.appendChild(errorDiv);
                    setTimeout(() => errorDiv.remove(), 3000);
                }
            } catch (error) {
                console.error('Error in search button handler:', error);
            }
        };
    } else {
        console.error('Search button not found!');
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

    // Initial population of filters if data is available from the server
    if (window.initialFilters) {
        populateSelect('company-filter', window.initialFilters.companies);
        populateSelect('department-filter', window.initialFilters.departments);
        populateSelect('location-filter', window.initialFilters.locations);
        populateSelect('manager-filter', window.initialFilters.managers, window.preSelectedManagers);
    }
});