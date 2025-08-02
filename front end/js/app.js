"use strict";
let currentRound = null;
let selectedSession = null;
let selectedVisualizationType = 'timeline';
const roundSelect = document.getElementById('round');
const sessionGrid = document.getElementById('session-grid');
const analyzeButton = document.querySelector('button[type="submit"]');
const sentimentImage = document.getElementById('sentiment-image');
const gettingStartedCard = document.getElementById('getting-started');
const roundSelectionCard = document.getElementById('round-selection');
const sessionSelectionCard = document.getElementById('session-selection');
const visualizationSelectionCard = document.getElementById('visualization-selection');
const resultsCard = document.getElementById('results-card');
let currStep = 1;
const API_BASE = 'http://127.0.0.1:5000/api';
document.addEventListener('DOMContentLoaded', () => {
    console.log('Page loaded, initializing F1 Sentiment Analysis app..');
    loadRaces();
    setupEventListeners();
    testRadioButtons();
});
async function loadRaces() {
    try {
        console.log('loading races from API..');
        const response = await fetch(`${API_BASE}/races`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const data = await response.json();
        if (data.success && data.races) {
            console.log('races loaded successfully: ', data.races);
            populateRaceDropdown(data.races);
        }
        else {
            showError('Failed to load races: ' + (data.error || 'Unknown error'));
        }
    }
    catch (error) {
        console.error('Error loading races:', error);
        showError('Error connecting to server. Make sure your Flask server is running on port 5000!');
    }
}
async function loadSessions(roundNum) {
    try {
        console.log(`loading sessions for round ${roundNum}..`);
        const response = await fetch(`${API_BASE}/sessions/${roundNum}`);
        const data = await response.json();
        if (data.success && data.sessions) {
            console.log('Sessions loaded:', data.sessions);
            populateSessionGrid(data.sessions);
        }
        else {
            showError('Failed to load sessions: ' + (data.error || 'Unknown error'));
        }
    }
    catch (error) {
        console.error('Error loading sessions:', error);
        showError('Error loading sessions');
    }
}
function getSelectedVisualizationType() {
    const selectedRadio = document.querySelector('input[name="viz-type"]:checked');
    return selectedRadio ? selectedRadio.value : 'timeline';
}
async function analyzeSentiment() {
    if (!selectedSession)
        return;
    console.log('=== DEBUG INFO ===');
    console.log('selectedSession:', selectedSession);
    console.log('currentRound:', currentRound);
    console.log('selectedVisualizationType (global):', selectedVisualizationType);
    console.log('getSelectedVisualizationType():', getSelectedVisualizationType());
    console.log('==================');
    analyzeButton.disabled = true;
    analyzeButton.textContent = 'analyzing..';
    try {
        const visType = getSelectedVisualizationType();
        console.log('starting sentiment analysis..');
        console.log(`analyzing ${selectedSession} for round ${currentRound} with ${visType} visualization`);
        const response = await fetch(`${API_BASE}/visualizations/${currentRound}/${selectedSession}?type=${visType}`);
        const data = await response.json();
        if (data.success && data.visualizations && data.visualizations.length > 0) {
            console.log('Visualization received:', data.visualizations[0].type);
            displayVisualization(data.visualizations[0]);
        }
        else {
            showError('No visualizations available for this session. Either nothing was found for this round & session or it hasn\'t happened yet.');
        }
    }
    catch (error) {
        console.error('Error analyzing sentiment:', error);
        showError('Error analyzing sentiment. Check console for details.');
    }
    finally {
        analyzeButton.disabled = false;
        updateAnalyzeButton();
    }
}
function populateRaceDropdown(races) {
    roundSelect.innerHTML = '<option value="">select a race..</option>';
    races.forEach((race) => {
        const option = document.createElement('option');
        option.value = race.round;
        option.textContent = `Round ${race.round}: ${race.name}`;
        roundSelect.appendChild(option);
    });
    console.log(`Added ${races.length} races to dropdown`);
}
function populateSessionGrid(sessions) {
    sessionGrid.innerHTML = '';
    selectedSession = null;
    sessions.forEach((session) => {
        const sessionDiv = document.createElement('div');
        sessionDiv.className = 'session-item bg-white p-3 rounded border cursor-pointer hover:bg-gray-50 transition';
        sessionDiv.innerHTML = `<input type="radio" name="session" id="session-${session}" class="mr-2">
                                <label for="session-${session}" class="cursor-pointer">${session}</label>`;
        const radiobutton = sessionDiv.querySelector('input[type="radio"]');
        radiobutton.addEventListener('change', (e) => {
            const target = e.target;
            if (target.checked) {
                selectedSession = session;
                resetToStep(2);
            }
            updateAnalyzeButton();
        });
        sessionGrid.appendChild(sessionDiv);
    });
    console.log(`Created ${sessions.length} radio buttons`);
}
function updateAnalyzeButton() {
    const hasSelections = selectedSession !== null;
    analyzeButton.disabled = !hasSelections;
    if (hasSelections) {
        analyzeButton.textContent = `Analyze ${selectedSession}`;
        analyzeButton.className = 'btn-primary w-full';
    }
    else {
        analyzeButton.textContent = 'Select session to analyze';
        analyzeButton.className = 'bg-gray-400 text-white px-6 py-3 rounded-lg w-full font-medium cursor-not-allowed';
    }
}
function displayVisualization(visualization) {
    const imgSrc = `data:image/png;base64,${visualization.data}`;
    sentimentImage.src = imgSrc;
    sentimentImage.alt = `${visualization.type} visualization`;
    console.log(`Displayed ${visualization.type} visualization`);
}
function testRadioButtons() {
    console.log('=== TESTING RADIO BUTTONS ===');
    const radioButtons = document.querySelectorAll('input[name="viz-type"]');
    console.log('Found radio buttons:', radioButtons.length);
    radioButtons.forEach((radio, index) => {
        const input = radio;
        console.log(`Radio ${index}: value="${input.value}", checked=${input.checked}`);
    });
    const checkedRadio = document.querySelector('input[name="viz-type"]:checked');
    console.log('Currently checked:', checkedRadio ? checkedRadio.value : 'none');
    console.log('============================');
}
function setupEventListeners() {
    roundSelect.addEventListener('change', (e) => {
        const target = e.target;
        currentRound = target.value;
        console.log(`race round selected ${currentRound}`);
        if (currentRound) {
            resetToStep(2);
            loadSessions(currentRound);
        }
        else {
            resetToStep(1);
            sessionGrid.innerHTML = '';
            selectedSession = null;
            updateAnalyzeButton();
        }
    });
    analyzeButton.addEventListener('click', () => {
        if (!selectedSession || !currentRound) {
            showToast('Please select a session first!', 'error');
            return;
        }
        analyzeSentiment();
        resetToStep(4);
    });
    console.log('Setting up radio button event listeners...');
    const radioButtons = document.querySelectorAll('input[name="viz-type"]');
    console.log('Found radio buttons:', radioButtons.length);
    radioButtons.forEach((radio, index) => {
        const input = radio;
        console.log(`Setting up listener for radio ${index}: value="${input.value}", checked=${input.checked}`);
        radio.addEventListener('change', (e) => {
            const target = e.target;
            console.log('Radio button clicked!');
            console.log('Previous value:', selectedVisualizationType);
            console.log('New value:', target.value);
            selectedVisualizationType = target.value;
            console.log(`Visualization type changed to: ${selectedVisualizationType}`);
            if (selectedSession && currentRound) {
                console.log('Auto-refreshing visualization with new type...');
                analyzeSentiment();
            }
        });
    });
    console.log('Event listeners set up successfully');
}
function showError(message) {
    showToast(message, 'error');
    console.error('User error:', message);
}
function logCurrentState() {
    console.log('Current state:', {
        currentRound,
        selectedSession,
        hasAnalyzeButton: !!analyzeButton,
        hasRoundSelect: !!roundSelect
    });
}
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    const container = document.getElementById('toast-container');
    container?.appendChild(toast);
    setTimeout(() => {
        toast.remove();
    }, 5000);
}
function setupProgressIndicator() {
    const progressContainer = document.createElement('div');
    progressContainer.className = 'progress-indicator';
    progressContainer.innerHTML = `
        <div class="progress-step active" data-step="1">1</div>
        <div class="progress-line" data-line="1"></div>
        <div class="progress-step" data-step="2">2</div>
        <div class="progress-line" data-line="2"></div>
        <div class="progress-step" data-step="3">3</div>
        <div class="progress-line" data-line="3"></div>
        <div class="progress-step" data-step="4">4</div>
        `;
    const header = document.querySelector('h1');
    header?.parentNode?.insertBefore(progressContainer, header.nextSibling);
}
function showCard(cardId) {
    const card = document.getElementById(cardId);
    if (card) {
        card.classList.remove('hidden');
        card.classList.add('card-visible');
        setTimeout(() => {
            card.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    }
}
function hideCard(cardId) {
    const card = document.getElementById(cardId);
    if (card) {
        card.classList.add('hidden');
        card.classList.remove('card-visible');
    }
}
function updateProgress(step) {
    currStep = step;
    for (let i = 1; i <= 4; i++) {
        const stepElement = document.querySelector(`[data-step="${i}"]`);
        const lineElement = document.querySelector(`[data-line="${i}"]`);
        if (stepElement && lineElement) {
            if (i < step) {
                // Completed steps
                stepElement.classList.remove('active');
                stepElement.classList.add('completed');
                lineElement.classList.remove('active');
                lineElement.classList.add('completed');
            }
            else if (i === step) {
                // Current step
                stepElement.classList.add('active');
                stepElement.classList.remove('completed');
                lineElement.classList.add('active');
                lineElement.classList.remove('completed');
            }
            else {
                // Future steps
                stepElement.classList.remove('active', 'completed');
                lineElement.classList.remove('active', 'completed');
            }
        }
    }
}
function resetToStep(step) {
    // Hide all cards first
    hideCard('session-selection');
    hideCard('visualization-selection');
    hideCard('results-card');
    // Show cards based on step
    switch (step) {
        case 1:
            // Only round selection visible
            break;
        case 2:
            showCard('session-selection');
            break;
        case 3:
            showCard('session-selection');
            showCard('visualization-selection');
            break;
        case 4:
            showCard('session-selection');
            showCard('visualization-selection');
            showCard('results-card');
            break;
    }
    updateProgress(step);
}
window.logCurrentState = logCurrentState;
