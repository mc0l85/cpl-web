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

    // Charting Setup
    function createRadialChart(elementId, label, color) {
        const options = { 
            chart: { type: 'radialBar', height: 200, sparkline: { enabled: true } }, 
            series: [0], 
            plotOptions: { 
                radialBar: { 
                    hollow: { size: '60%' }, 
                    dataLabels: { 
                        name: { offsetY: -10, color: "#fff", fontSize: '1em' }, 
                        value: { offsetY: 5, color: "#fff", fontSize: '1.5em', formatter: (val) => val }, 
                    }, 
                    track: { background: '#3a3a3a' }
                } 
            }, 
            labels: [label], 
            colors: [color], 
            theme: { mode: 'dark' } 
        };
        const chart = new ApexCharts(document.querySelector(elementId), options);
        chart.render();
        return chart;
    }
    const powerUserChart = createRadialChart("#power-user-chart", "Power Users", "#00bc8c");
    const consistentUserChart = createRadialChart("#consistent-user-chart", "Consistent Users", "#0d6efd");
    const coachingChart = createRadialChart("#coaching-opportunity-chart", "Coaching", "#f0ad4e");
    const newUserChart = createRadialChart("#new-user-chart", "New Users", "#6f42c1");
    const recaptureChart = createRadialChart("#recapture-chart", "Recapture", "#d9534f");

    // File Handling
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
                const p = document.createElement('p');
                p.textContent = `${file.name} loaded.`;
                p.className = 'text-success small mb-0';
                statusElement.appendChild(p);
                if (data.type === 'target') {
                    populateSelect('company-filter', data.filters.companies);
                    populateSelect('department-filter', data.filters.departments);
                    populateSelect('location-filter', data.filters.locations);
                    populateSelect('manager-filter', data.filters.managers);
                } else if (data.type === 'usage') {
                    uploadedUsageFiles.push(data.filename);
                }
                return data; // Resolve promise
            } else { throw new Error(data.message || 'File upload failed.'); }
        })
        .catch(error => {
            console.error('Upload Error:', error);
            statusElement.innerHTML += `<p class="text-danger small mb-0">Upload failed for ${file.name}.</p>`;
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
        runAnalysisBtn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Uploading...`;

        const uploadPromises = [...e.target.files].map(file => handleFileUpload(file, 'usage', usageFilesStatus));
        
        Promise.all(uploadPromises)
            .then(() => {
                runAnalysisBtn.disabled = false;
                runAnalysisBtn.innerHTML = 'Run Analysis';
                console.log('All usage reports uploaded successfully.');
            })
            .catch(error => {
                runAnalysisBtn.disabled = false;
                runAnalysisBtn.innerHTML = 'Run Analysis';
                alert('One or more usage reports failed to upload. Please try again.');
                console.error('Error during batch upload of usage reports:', error);
            });
    });

    // Socket.IO Handlers
    socket.on('connect', () => console.log('Socket.IO connection established!'));
    socket.on('status_update', (data) => statusLabel.textContent = data.message);
    
    socket.on('analysis_complete', (data) => {
        runAnalysisBtn.disabled = false;
        runAnalysisBtn.innerHTML = 'Run Analysis';
        statusLabel.textContent = 'Analysis complete.';
        const { total, categories } = data.dashboard;
        document.getElementById('total-users').textContent = total;
        const updateChart = (chart, count, total) => {
            const percentage = total > 0 ? Math.round((count / total) * 100) : 0;
            chart.updateSeries([percentage]);
            chart.updateOptions({ plotOptions: { radialBar: { dataLabels: { value: { formatter: () => count } } } } });
        };
        updateChart(powerUserChart, categories.power_user || 0, total);
        updateChart(consistentUserChart, categories.consistent_user || 0, total);
        updateChart(coachingChart, categories.coaching || 0, total);
        updateChart(newUserChart, categories.new_user || 0, total);
        updateChart(recaptureChart, categories.recapture || 0, total);
        
        reportDataForDownload = data.reports;
        reportDataForDownload.excel_bytes = undefined;
        reportsContainer.style.display = 'block';
    });

    socket.on('analysis_error', (data) => {
        runAnalysisBtn.disabled = false;
        runAnalysisBtn.innerHTML = 'Run Analysis';
        statusLabel.textContent = `Error: ${data.message}`;
        alert(`Analysis Error: ${data.message}`);
    });

    socket.on('deep_dive_result', (data) => {
        deepDiveResults.textContent = data.text;
        if (deepDiveChart) {
            deepDiveChart.destroy();
        }
        const chartOptions = {
            chart: { type: 'line', height: 350, background: '#060606', foreColor: '#ccc' },
            series: data.chart_data.series,
            xaxis: { categories: data.chart_data.categories, labels: { style: { colors: '#ccc' } } },
            yaxis: { title: { text: 'Avg. Tools Used', style: { color: '#ccc' } }, labels: { style: { colors: '#ccc' } } },
            colors: ['#39FF14', '#00bc8c', '#ff4136'],
            legend: { labels: { colors: '#ccc' } },
            grid: { borderColor: '#444' },
            tooltip: { theme: 'dark' }
        };
        deepDiveChart = new ApexCharts(deepDiveChartContainer, chartOptions);
        deepDiveChart.render();
    });
    socket.on('deep_dive_error', (data) => alert(`Deep Dive Error: ${data.message}`));

    // Action Button Listeners
    runAnalysisBtn.addEventListener('click', () => {
        runAnalysisBtn.disabled = true;
        runAnalysisBtn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Running...`;
        reportsContainer.style.display = 'none';
        statusLabel.textContent = 'Starting analysis...';
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

    searchBtn.addEventListener('click', () => {
        const email = userEmailEntry.value;
        if (email) {
            deepDiveResults.textContent = "Searching...";
            if (deepDiveChart) {
                deepDiveChart.destroy(); // Clear previous chart if exists
            }
            socket.emit('perform_deep_dive', { email });
        } else {
            alert('Please enter an email to search.');
        }
    });

    // Helper Functions
    function populateSelect(selectId, options) {
        const select = document.getElementById(selectId);
        select.innerHTML = '';
        if (options) {
            options.forEach(optionText => {
                const option = document.createElement('option');
                option.value = optionText;
                option.textContent = optionText;
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
});
