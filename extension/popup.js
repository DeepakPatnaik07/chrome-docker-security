document.addEventListener('DOMContentLoaded', () => {
    console.log("Popup DOM loaded."); // Log 1: Popup loaded

    const statusContainerEl = document.getElementById('status-container'); // Updated ID
    const statusIconEl = document.getElementById('status-icon'); // New icon element
    const statusTextEl = document.getElementById('status-text'); // New text element
    const urlValueEl = document.getElementById('url-value'); // Get value span
    const titleValueEl = document.getElementById('title-value'); // Get value span
    const reasonsContainerEl = document.getElementById('reasons-container');
    const reasonsListEl = document.getElementById('reasons-list');
    const aiContainerEl = document.getElementById('ai-container'); // Get AI container
    const aiAnalysisEl = document.getElementById('ai-analysis');
    const toggleAnalysisBtn = document.getElementById('toggle-analysis-details'); // Correct ID from HTML update needed
    const toggleTechnicalBtn = document.getElementById('toggle-technical-details'); // Correct ID from HTML update needed
    const detailsContainerEl = document.getElementById('details-container');
    const detailsEl = document.getElementById('details');

    // --- Revised Helper Function for Overall Status ---
    function determineOverallStatus(data) {
        let icon = '?';
        let tooltip = '';
        let status = { text: 'Error', class: 'status-error' }; 

        if (!data || data.status === 'error') {
            icon = '❌'; 
            status = { text: 'Error', class: 'status-error' };
        } else {
            const localSuspicious = data.analysis?.suspicious || false;
            const aiSkipped = data.analysis?.ai_skipped === true;
            const aiAssessment = (data.analysis?.ai_assessment || '').toLowerCase();
            const suspiciousKeywords = ['high', 'suspicious', 'malicious', 'risky', 'phishing', 'dangerous'];
            const safeKeywords = ['very low', 'low risk', 'safe', 'clean', 'benign'];
            let isAiSuspicious = false;
            let isAiSafe = false;
            if (!aiSkipped) {
                isAiSuspicious = suspiciousKeywords.some(keyword => aiAssessment.includes(keyword));
                isAiSafe = safeKeywords.some(keyword => aiAssessment.includes(keyword));
            }

            if (localSuspicious || isAiSuspicious) {
                icon = '⚠️'; 
                status = { text: 'Suspicious', class: 'status-suspicious' };
            } else if (isAiSafe) { 
                icon = '✅'; 
                status = { text: 'Safe', class: 'status-safe' };
            } else if (aiSkipped) { 
                icon = '✅'; 
                status = { text: 'Safe*', class: 'status-safe' };
                tooltip = "Based on local checks only. AI analysis was skipped.";
            } else { 
                icon = '❓'; 
                status = { text: 'Caution Advised', class: 'status-suspicious' }; 
            }
        }
        return { ...status, icon, tooltip }; 
    }
    // --- End Helper Function ---

    chrome.storage.local.get(['lastScanResult'], (result) => {
        const data = result.lastScanResult;

        // --- Update Main Status --- 
        const overallStatus = determineOverallStatus(data);
        statusTextEl.textContent = `Status: ${overallStatus.text}`;
        statusIconEl.textContent = overallStatus.icon;
        // Apply class to container for color, and set tooltip
        statusContainerEl.className = `info-section status ${overallStatus.class}`;
        statusContainerEl.title = overallStatus.tooltip;
        // --- End Main Status Update ---
        
        // URL & Title
        urlValueEl.textContent = data.url || 'N/A';
        titleValueEl.textContent = data.title || 'N/A';

        // Display Local Analysis Reasons & Errors
        reasonsListEl.innerHTML = ''; 
        let hasReasons = false;
        if (data.analysis?.reasons?.length > 0) {
            hasReasons = true;
            data.analysis.reasons.forEach(reason => {
                const li = document.createElement('li');
                li.textContent = reason;
                reasonsListEl.appendChild(li);
            });
        }
        if(data.status === 'error' && data.error && !data.analysis?.reasons?.length) { // Avoid duplicating error message if already in reasons
             hasReasons = true;
             const li = document.createElement('li');
             li.textContent = `Error: ${data.error}`;
             reasonsListEl.appendChild(li);
        }
        reasonsContainerEl.style.display = 'none'; // Hide initially

        // Display AI Analysis Results
        let hasAiAssessment = false;
        if (data.analysis && data.analysis.ai_assessment && !data.analysis.ai_skipped) {
            hasAiAssessment = true;
            aiAnalysisEl.textContent = data.analysis.ai_assessment;
        } else if (data.analysis && data.analysis.ai_skipped) {
            hasAiAssessment = true; 
            aiAnalysisEl.textContent = `Skipped: ${data.analysis.ai_reason}`;
        }
        aiContainerEl.style.display = 'none'; // Hide initially

        // Full Technical Data
        detailsEl.textContent = JSON.stringify(data, null, 2); 
        detailsContainerEl.style.display = 'none'; // Hide initially

        // --- Setup Buttons --- 
        // Button 1: Show/Hide Analysis (Local Flags + AI Assessment)
        let analysisVisible = false;
        if(hasReasons || hasAiAssessment){ 
             toggleAnalysisBtn.style.display = 'inline-block'; // Use inline-block for buttons
             toggleAnalysisBtn.textContent = 'Show Analysis Details';
             toggleAnalysisBtn.onclick = () => {
                analysisVisible = !analysisVisible;
                reasonsContainerEl.style.display = analysisVisible && hasReasons ? 'block' : 'none'; 
                aiContainerEl.style.display = analysisVisible && hasAiAssessment ? 'block' : 'none'; 
                toggleAnalysisBtn.textContent = analysisVisible ? 'Hide Analysis Details' : 'Show Analysis Details';
             };
        } else {
             toggleAnalysisBtn.style.display = 'none'; // Hide button if no content
        }

        // Button 2: Show/Hide Technical Data (Full JSON)
        let technicalVisible = false;
        toggleTechnicalBtn.style.display = 'inline-block'; // Use inline-block for buttons
        toggleTechnicalBtn.textContent = 'Show Technical Data';
        toggleTechnicalBtn.onclick = () => {
            technicalVisible = !technicalVisible;
            detailsContainerEl.style.display = technicalVisible ? 'block' : 'none';
            toggleTechnicalBtn.textContent = technicalVisible ? 'Hide Technical Data' : 'Show Technical Data';
        };
        // --- End Setup Buttons --- 
        
        console.log("Popup updated with data.");

    });
});
