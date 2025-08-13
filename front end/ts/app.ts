interface Race{
    round: string;
    name: string;
}
interface ApiResponse<T>{
    success: boolean;
    error?: string,
    races?: Race[],
    sessions?: string[];
    visualizations?: Visualization[];
    message?: string;
    warning?: string; 
}

interface Visualization{
    type: string;
    data: string;
}

interface RealtimeAnalysisResponse {
    success: boolean;
    message?: string;
    warning?: string;
    error?: string;
    visualization?: Visualization;
}

let currentRound: string | null = null;
let selectedSession: string | null = null;
let selectedVisualizationType: string = 'timeline';
let isRealtimeMode: boolean = true; // Always use real-time mode

const roundSelect = document.getElementById('round') as HTMLSelectElement;
const sessionGrid = document.getElementById('session-grid') as HTMLDivElement;
const analyzeButton = document.getElementById('analyze-btn') as HTMLButtonElement;
const sentimentImage = document.getElementById('sentiment-image') as HTMLImageElement;

const gettingStartedCard = document.getElementById('getting-started') as HTMLDivElement;
const roundSelectionCard = document.getElementById('round-selection') as HTMLDivElement;
const sessionSelectionCard = document.getElementById('session-selection') as HTMLDivElement;
const visualizationSelectionCard = document.getElementById('visualization-selection') as HTMLDivElement;
const resultsCard = document.getElementById('results-card') as HTMLDivElement;
let currStep = 1;

const API_BASE = 'http://127.0.0.1:5000/api';

document.addEventListener('DOMContentLoaded', (): void => {
    console.log('Page loaded, initializing F1 Sentiment Analysis app..');
    loadRaces();
    setupEventListeners();
    testRadioButtons();
});

async function loadRaces(): Promise<void>{
    try{
        console.log('loading races from API..');
        
        const response = await fetch(`${API_BASE}/races`);
        if(!response.ok){
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data: ApiResponse<Race[]> = await response.json();

        if(data.success && data.races){
            console.log('races loaded successfully: ', data.races);
            populateRaceDropdown(data.races);
        } else {
            showError('Failed to load races: ' + (data.error || 'Unknown error'));
        }
    }
    catch(error){
        console.error('Error loading races:', error);
        showError('Error connecting to server. Make sure your Flask server is running on port 5000!');
    }
}

async function loadSessions(roundNum: string): Promise<void> {
    try{
        console.log(`loading sessions for round ${roundNum}..`)

        const response = await fetch(`${API_BASE}/sessions/${roundNum}`)
        const data: ApiResponse<string[]> = await response.json();

        if (data.success && data.sessions) {
            console.log('Sessions loaded:', data.sessions);
            populateSessionGrid(data.sessions);
        } else {
            showError('Failed to load sessions: ' + (data.error || 'Unknown error'));
        }
    }
    catch(error){
        console.error('Error loading sessions:', error);
        showError('Error loading sessions');
    }
}

function getSelectedVisualizationType(): string {
    const selectedRadio = document.querySelector('input[name="viz-type"]:checked') as HTMLInputElement;
    return selectedRadio ? selectedRadio.value : 'timeline';
}

async function analyzeSentiment(): Promise<void> {
    if(!selectedSession) return;

    if (isRealtimeMode) {
        await performRealtimeAnalysis();
        return;
    }

    console.log('=== DEBUG INFO ===');
    console.log('selectedSession:', selectedSession);
    console.log('currentRound:', currentRound);
    console.log('selectedVisualizationType (global):', selectedVisualizationType);
    console.log('getSelectedVisualizationType():', getSelectedVisualizationType());
    console.log('==================');

    analyzeButton.disabled = true;
    analyzeButton.textContent = 'analyzing..';

    try{
        const visType = getSelectedVisualizationType();

        console.log('starting sentiment analysis..');
        console.log(`analyzing ${selectedSession} for round ${currentRound} with ${visType} visualization`);

        const response = await fetch(`${API_BASE}/visualizations/${currentRound}/${selectedSession}?type=${visType}`);
        const data: ApiResponse<Visualization[]> = await response.json();

        if (data.success && data.visualizations && data.visualizations.length > 0) {
            console.log('Visualization received:', data.visualizations[0].type);
            displayVisualization(data.visualizations[0]);
        } else {
            showError('No visualizations available for this session. Either nothing was found for this round & session or it hasn\'t happened yet.');
        }
    }
    catch(error){
        console.error('Error analyzing sentiment:', error);
        showError('Error analyzing sentiment. Check console for details.');
    }
    finally{
        analyzeButton.disabled = false;
        updateAnalyzeButton();
    }
}

async function performRealtimeAnalysis(): Promise<void> {
    if(!selectedSession || !currentRound) return;

    console.log('=== REAL-TIME ANALYSIS DEBUG ===');
    console.log('selectedSession:', selectedSession);
    console.log('currentRound:', currentRound);
    console.log('selectedVisualizationType:', selectedVisualizationType);
    console.log('================================');

    analyzeButton.disabled = true;
    analyzeButton.textContent = 'Processing real-time data...';
    
    showRealtimeLoadingState();

    try{
        const visType = getSelectedVisualizationType();
        
        console.log('Starting real-time sentiment analysis...');
        console.log(`Real-time analyzing ${selectedSession} for round ${currentRound} with ${visType} visualization`);

        // Call the real-time analysis endpoint
        const response = await fetch(`${API_BASE}/realtime-analysis/${currentRound}/${selectedSession}?type=${visType}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data: RealtimeAnalysisResponse = await response.json();

        if (data.success) {
            console.log('Real-time analysis completed:', data.message);
            
            if (data.visualization) {
                displayVisualization(data.visualization);
                showToast('Real-time analysis completed successfully!', 'success');
            } else if (data.warning) {
                showToast(data.warning, 'info');
                setTimeout(() => {
                    console.log('Attempting to fetch visualization after processing...');
                    analyzeSentiment();
                }, 2000);
            }
        } else {
            showError('Real-time analysis failed: ' + (data.error || 'Unknown error'));
        }
    }
    catch(error){
        console.error('Error in real-time analysis:', error);
        showError('Error performing real-time analysis. Check console for details.');
    }
    finally{
        hideRealtimeLoadingState();
        analyzeButton.disabled = false;
        updateAnalyzeButton();
    }
}

function populateRaceDropdown(races: Race[]): void {
    roundSelect.innerHTML = '<option value="">select a race..</option>';

    races.forEach((race: Race) => {
        const option = document.createElement('option');
        option.value = race.round;
        option.textContent = `Round ${race.round}: ${race.name}`;
        roundSelect.appendChild(option);
    });

    console.log(`Added ${races.length} races to dropdown`);
}

function populateSessionGrid(sessions: string[]): void {
    sessionGrid.innerHTML = '';
    selectedSession = null;

    sessions.forEach((session: string) => {
        const sessionDiv = document.createElement('div');
        sessionDiv.className = 'session-item bg-white p-3 rounded border cursor-pointer hover:bg-gray-50 transition';

        sessionDiv.innerHTML = `<input type="radio" name="session" id="session-${session}" class="mr-2">
                                <label for="session-${session}" class="cursor-pointer">${session}</label>`;

        const radiobutton = sessionDiv.querySelector('input[type="radio"]') as HTMLInputElement;
        
        radiobutton.addEventListener('change', (e: Event) => {
            const target = e.target as HTMLInputElement;
            if(target.checked){
                selectedSession = session;
                resetToStep(2);
            }
            updateAnalyzeButton();
        });

        sessionGrid.appendChild(sessionDiv);
    });

    console.log(`Created ${sessions.length} radio buttons`);
}

function updateAnalyzeButton(): void {
    const hasSelections = selectedSession !== null;
    
    analyzeButton.disabled = !hasSelections;
    
    if(hasSelections){
        analyzeButton.textContent = `Real-time Analyze ${selectedSession}`;
        analyzeButton.className = 'btn-realtime w-full';
    } else {
        analyzeButton.textContent = 'Select session to analyze';
        analyzeButton.className = 'bg-gray-400 text-white px-6 py-3 rounded-lg w-full font-medium cursor-not-allowed';
    }
}

function displayVisualization(visualization: Visualization): void {
    const imgSrc = `data:image/png;base64,${visualization.data}`;

    sentimentImage.src = imgSrc;
    sentimentImage.alt = `${visualization.type} visualization`

    console.log(`Displayed ${visualization.type} visualization`);
}

function testRadioButtons(): void {
    console.log('=== TESTING RADIO BUTTONS ===');
    const radioButtons = document.querySelectorAll('input[name="viz-type"]');
    console.log('Found radio buttons:', radioButtons.length);
    
    radioButtons.forEach((radio, index) => {
        const input = radio as HTMLInputElement;
        console.log(`Radio ${index}: value="${input.value}", checked=${input.checked}`);
    });
    
    const checkedRadio = document.querySelector('input[name="viz-type"]:checked') as HTMLInputElement;
    console.log('Currently checked:', checkedRadio ? checkedRadio.value : 'none');
    console.log('============================');
}

function setupEventListeners(): void {
    roundSelect.addEventListener('change', (e: Event) => {
        const target = e.target as HTMLSelectElement;
        currentRound = target.value;
        console.log(`race round selected ${currentRound}`);

        if(currentRound){
            resetToStep(2);
            loadSessions(currentRound);
        } else {
            resetToStep(1);
            sessionGrid.innerHTML = '';
            selectedSession = null;
            updateAnalyzeButton();
        }
    });
    
    if (analyzeButton) {
        analyzeButton.addEventListener('click', (e: Event) => {
            e.preventDefault(); 
            e.stopPropagation(); 
            
            console.log('Analyze button clicked!');
            
            if (!selectedSession || !currentRound) {
                showToast('Please select a session first!', 'error');
                return;
            }
            
            try {
                analyzeSentiment();
                resetToStep(4);
            } catch (error) {
                console.error('Error during analysis:', error);
                showError('An error occurred during analysis');
            }
        });
    } else {
        console.error('Analyze button not found!');
    }
    
    console.log('Event listeners set up successfully');
}

function showError(message: string): void {
    showToast(message, 'error');
    console.error('User error:', message);
}

function logCurrentState(): void {
    console.log('Current state:', {
        currentRound,
        selectedSession,
        hasAnalyzeButton: !!analyzeButton,
        hasRoundSelect: !!roundSelect
    });
}

function showToast(message: string, type: 'success' | 'error' | 'info' = 'info'): void {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    const container = document.getElementById('toast-container');
    container?.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 5000)
}

function setupProgressIndicator(): void {
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

function showCard(cardId: string): void {
    const card = document.getElementById(cardId);
    if(card){
        card.classList.remove('hidden');
        card.classList.add('card-visible');

        setTimeout(() => {
            card.scrollIntoView({behavior: 'smooth', block: 'start'});
        });
    }
}

function hideCard(cardId: string): void {
    const card = document.getElementById(cardId);
    if (card) {
        card.classList.add('hidden');
        card.classList.remove('card-visible');
    }
}

function updateProgress(step: number): void {
    currStep = step;
    
    for (let i = 1; i <= 4; i++) {
        const stepElement = document.querySelector(`[data-step="${i}"]`) as HTMLElement;
        const lineElement = document.querySelector(`[data-line="${i}"]`) as HTMLElement;
        
        if (stepElement && lineElement) {
            if (i < step) {
                // Completed steps
                stepElement.classList.remove('active');
                stepElement.classList.add('completed');
                lineElement.classList.remove('active');
                lineElement.classList.add('completed');
            } else if (i === step) {
                // Current step
                stepElement.classList.add('active');
                stepElement.classList.remove('completed');
                lineElement.classList.add('active');
                lineElement.classList.remove('completed');
            } else {
                // Future steps
                stepElement.classList.remove('active', 'completed');
                lineElement.classList.remove('active', 'completed');
            }
        }
    }
}

function resetToStep(step: number): void {
    // Hide all cards first
    hideCard('session-selection');
    hideCard('visualization-selection');
    hideCard('results-card');
    
    // Show cards based on step
    switch(step) {
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

function showRealtimeLoadingState(): void {
    const resultsCard = document.getElementById('results-card');
    if (resultsCard) {
        let loadingDiv = document.getElementById('realtime-loading');
        if (!loadingDiv) {
            loadingDiv = document.createElement('div');
            loadingDiv.id = 'realtime-loading';
            loadingDiv.className = 'text-center py-8';
            loadingDiv.innerHTML = `
                <div class="spinner-large"></div>
                <p class="text-white mt-4 f1-subtitle">Scraping Reddit data...</p>
                <p class="text-gray-300 text-sm mt-2">This may take 1-2 minutes</p>
                <div class="progress-steps mt-4">
                    <div class="step active">🔍 Scraping posts</div>
                    <div class="step">🧠 Processing sentiment</div>
                    <div class="step">📊 Creating visualization</div>
                </div>
            `;
            resultsCard.appendChild(loadingDiv);
        }
        loadingDiv.classList.remove('hidden');
    }
}

function hideRealtimeLoadingState(): void {
    const loadingDiv = document.getElementById('realtime-loading');
    if (loadingDiv) {
        loadingDiv.classList.add('hidden');
    }
}

(window as any).logCurrentState = logCurrentState;