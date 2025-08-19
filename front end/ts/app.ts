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
    visualizations?: { [key: string]: Visualization }; 
    stats?: {
        post_limit: number;
        comment_limit: number;
        visualizations_generated: number;
    };
}

let currentRound: string | null = null;
let selectedSession: string | null = null;
let selectedVisualizationType: string = 'timeline';
let isRealtimeMode: boolean = true; 
let analyzeButton = document.getElementById('analyze-btn') as HTMLButtonElement;
let lastRealtimeVisualizations: {[key: string]: Visualization} | null = null;

const roundSelect = document.getElementById('round') as HTMLSelectElement;
const sessionGrid = document.getElementById('session-grid') as HTMLDivElement;
const sentimentImage = document.getElementById('sentiment-image') as HTMLImageElement;

const gettingStartedCard = document.getElementById('getting-started') as HTMLDivElement;
const roundSelectionCard = document.getElementById('round-selection') as HTMLDivElement;
const sessionSelectionCard = document.getElementById('session-selection') as HTMLDivElement;
const visualizationSelectionCard = document.getElementById('visualization-selection') as HTMLDivElement;
const resultsCard = document.getElementById('results-card') as HTMLDivElement;
let currStep = 1;

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000/api';

document.addEventListener('DOMContentLoaded', () => {
    console.log('Page loaded, initializing F1 Sentiment Analysis app..');
    
    const allForms = document.querySelectorAll('form');
    console.log('Forms found on page:', allForms.length);
    if (allForms.length > 0) {
        allForms.forEach((form, index) => {
            console.log(`Form ${index}:`, form);
            form.addEventListener('submit', (e) => {
                console.error('FORM SUBMIT DETECTED! This is causing the refresh!');
                e.preventDefault();
            });
        });
    }
    
    document.addEventListener('click', (e) => {
        const target = e.target as HTMLElement;
        if (target.tagName === 'BUTTON' || target.closest('button')) {
            const button = target.tagName === 'BUTTON' ? target : target.closest('button');
            console.log('=== BUTTON CLICK DETECTED ===');
            console.log('Button ID:', button?.id);
            console.log('Button type:', (button as HTMLButtonElement)?.type);
            console.log('Is default prevented?', e.defaultPrevented);
            console.log('Event phase:', e.eventPhase);
            console.log('=============================');
        }
    }, true); 
    
    window.addEventListener('beforeunload', (e) => {
        console.error('PAGE IS ABOUT TO REFRESH/RELOAD!');
        console.trace('Stack trace:');
    });
    
    const btn = document.getElementById('analyze-btn') as HTMLButtonElement;
    if (btn) {
        console.log('Analyze button found:');
        console.log('- Type attribute:', btn.type);
        console.log('- Parent element:', btn.parentElement?.tagName);
        console.log('- Is inside form?', btn.closest('form') !== null);
    }
    
    loadRaces();
    setupEventListeners();
    testRadioButtons();
    
    setTimeout(debugButtonBehavior, 1000);
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
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data: ApiResponse<Visualization[]> = await response.json();

        if (data.success && data.visualizations && data.visualizations.length > 0) {
            console.log('Visualization received:', data.visualizations[0].type);
            displayVisualization(data.visualizations[0]);
        } else {
            throw new Error('No visualizations available for this session. Either nothing was found for this round & session or it hasn\'t happened yet.');
        }
    }
    catch(error){
        console.error('Error analyzing sentiment:', error);
        if (error instanceof Error) {
            showError(`Analysis failed: ${error.message}`);
        } else {
            showError('An unexpected error occurred during analysis');
        }
    } finally {
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
        console.log('Starting real-time sentiment analysis...');
        console.log(`Real-time analyzing ${selectedSession} for round ${currentRound}`);
        
        const response = await fetch(`${API_BASE}/realtime-analysis/${currentRound}/${selectedSession}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data: RealtimeAnalysisResponse = await response.json();

        console.log('Backend response:', data);
        console.log('Response structure:', {
            success: data.success,
            hasVisualizations: !!data.visualizations,
            vizCount: data.visualizations ? Object.keys(data.visualizations).length : 0,
            message: data.message
        });

        if (data.success && data.visualizations) {
            const vizTypes = Object.keys(data.visualizations);
            lastRealtimeVisualizations = data.visualizations;
            const selectedVizType = getSelectedVisualizationType();
            
            if (data.visualizations[selectedVizType]) {
                displayVisualization(data.visualizations[selectedVizType]);
                console.log(`Displayed selected visualization: ${selectedVizType}`);
            } else {
                const firstVizType = vizTypes[0];
                displayVisualization(data.visualizations[firstVizType]);
                console.log(`Selected type ${selectedVizType} not available, showing ${firstVizType}`);
                showToast(`Note: ${selectedVizType} visualization not available, showing ${firstVizType} instead.`, 'info');
            }

            const stats = data.stats;
            if(stats){
                showToast(`Analysis completed! Generated ${stats.visualizations_generated} visualizations from ${stats.post_limit} posts.`, 'success');
            } else {
                showToast('Real-time analysis completed successfully!', 'success');
            }

            console.log('Available visualizations:', vizTypes)
            
        } else {
            const errorMsg = data.error || 'Unknown error occurred';
            console.error('API returned error:', errorMsg);
            showError('Real-time analysis failed: ' + errorMsg);
        }
    }
    catch(error){
        console.error('Error in real-time analysis:', error);
        if (error instanceof TypeError && error.message.includes('fetch')) {
            showError('Cannot connect to server. Make sure your Flask server is running!');
        } else if (error instanceof Error) {
            showError(`Real-time analysis failed: ${error.message}`);
        } else {
            showError('An unexpected error occurred during real-time analysis');
        }
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
        analyzeButton.removeEventListener('click', handleAnalyzeClick);
        analyzeButton.addEventListener('click', handleAnalyzeClick);
        
        console.log('Analyze button event listener attached successfully');
    } else {
        console.error('Analyze button not found!');
    }

    const vizTypeRadios = document.querySelectorAll('input[name="viz-type"]');
    vizTypeRadios.forEach(r => {
        r.addEventListener('change', () => {
            void handleVizTypeChange();
        });
    });
    
    console.log('Event listeners set up successfully');
}

async function handleAnalyzeClick(e: MouseEvent): Promise<void> {
    console.log('=== handleAnalyzeClick CALLED ===');
    console.log('Event type:', e.type);
    console.log('Event target:', e.target);
    console.log('Event currentTarget:', e.currentTarget);
    console.log('Before preventDefault - defaultPrevented:', e.defaultPrevented);
    
    // Prevent any default behavior and stop propagation
    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation(); // Add this too
    
    console.log('After preventDefault - defaultPrevented:', e.defaultPrevented);
    console.log('=================================');
    
    // Get the button from the event target to ensure we have the right reference
    const button = e.currentTarget as HTMLButtonElement;
    
    if (button.disabled) {
        console.log('Button already disabled, ignoring click');
        return;
    }
    
    button.disabled = true;
    
    // Validation check
    if (!selectedSession || !currentRound) {
        showToast('Please select a session first!', 'error');
        button.disabled = false;
        return;
    }
    
    try {
        console.log('About to call analyzeSentiment...');
        await analyzeSentiment();
        console.log('analyzeSentiment completed successfully');
        resetToStep(4);
    } catch (error) {
        console.error('Error during analysis (caught in handleAnalyzeClick):', error);
        
        if (error instanceof Error) {
            showError(`Analysis failed: ${error.message}`);
        } else {
            showError('An unexpected error occurred during analysis');
        }
        
        return; 
    } finally {
        console.log('handleAnalyzeClick finally block');
        button.disabled = false;
        updateAnalyzeButton();
    }
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

function debugButtonBehavior() {
    const button = document.getElementById('analyze-btn') as HTMLButtonElement;
    if (button) {
        console.log('Button element:', button);
        console.log('Button type:', button.type);
        console.log('Button onclick:', button.onclick);
        console.log('Button form:', button.form);
        console.log('Button parent form:', button.closest('form'));
        
        console.log('Button event listeners cannot be inspected in regular JavaScript');
    }
}

async function  pollForVisualization(round: string, session: string, visType: string, {
    intervalMs = 2000,
    maxAttempts = 10
} = {}): Promise<boolean> {
    for(let attempt = 0; attempt < maxAttempts; attempt++){
        try {
            const resp = await fetch(`${API_BASE}/visualizations/${round}/${session}?type=${visType}`);
            if (!resp.ok) {
                console.warn(`Poll attempt ${attempt + 1} failed: HTTP ${resp.status}`);
                await new Promise(r => setTimeout(r, intervalMs));
                continue;
            }
            
            const data: ApiResponse<Visualization[]> = await resp.json();

            if (data.success && data.visualizations && data.visualizations.length > 0) {
                displayVisualization(data.visualizations[0]);
                return true;
            }
        } catch (error) {
            console.warn(`Poll attempt ${attempt + 1} failed:`, error);
        }
        
        await new Promise(r => setTimeout(r, intervalMs));
    }
    return false;
}

async function  handleVizTypeChange(): Promise<void> {
    const selected = getSelectedVisualizationType();
    
    if(lastRealtimeVisualizations && lastRealtimeVisualizations[selected]){
        displayVisualization(lastRealtimeVisualizations[selected]);
        console.log(`Switched to ${selected} from cache`);
        return;
    }

    if(!currentRound || !selectedSession) return;

    try {
        const resp = await fetch(`${API_BASE}/visualizations/${currentRound}/${selectedSession}?type=${selected}`);
        if (!resp.ok) {
            showToast(`Failed to fetch ${selected} visualization`, 'error');
            return;
        }
        const data: ApiResponse<Visualization[]> = await resp.json();
        if (data.success && data.visualizations && data.visualizations.length > 0) {
            displayVisualization(data.visualizations[0]);
            console.log(`Switched to ${selected} via DB fetch`);
        } else {
            showToast(`No ${selected} visualization available for this session`, 'info');
        }
    } 
    catch(error) {
        console.error('Error fetching visualization:', error);
        showToast(`Error fetching ${selected} visualization`, 'error');
    }
}

(window as any).logCurrentState = logCurrentState;