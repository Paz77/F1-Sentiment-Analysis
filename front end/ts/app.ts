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
}

interface Visualization{
    type: string;
    data: string;
}

let currentRound: string | null = null;
let selectedSession: string | null = null;
let selectedVisualizationType: string = 'timeline';

const roundSelect = document.getElementById('round') as HTMLSelectElement;
const sessionGrid = document.getElementById('session-grid') as HTMLDivElement;
const analyzeButton = document.querySelector('button[type="submit"]') as HTMLButtonElement;
const sentimentImage = document.getElementById('sentiment-image') as HTMLImageElement;

const API_BASE = 'http://127.0.0.1:5000/api';

document.addEventListener('DOMContentLoaded', (): void => {
    console.log('Page loaded, initializing F1 Sentiment Analysis app..');
    loadRaces();
    setupEventListeners();
    testRadioButtons(); // Add this line
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
        analyzeButton.textContent = `Analyze ${selectedSession}`;
        analyzeButton.className = 'bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition w-full font-medium';
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
            loadSessions(currentRound);
        } else {
            sessionGrid.innerHTML = '';
            selectedSession = null;
            updateAnalyzeButton();
        }
    });

    analyzeButton.addEventListener('click', analyzeSentiment);

    console.log('Setting up radio button event listeners...');
    const radioButtons = document.querySelectorAll('input[name="viz-type"]');
    console.log('Found radio buttons:', radioButtons.length);

    radioButtons.forEach((radio, index) => {
        const input = radio as HTMLInputElement;
        console.log(`Setting up listener for radio ${index}: value="${input.value}", checked=${input.checked}`);
        
        radio.addEventListener('change', (e: Event) => {
            const target = e.target as HTMLInputElement;
            console.log('Radio button clicked!');
            console.log('Previous value:', selectedVisualizationType);
            console.log('New value:', target.value);
            
            selectedVisualizationType = target.value;
            console.log(`Visualization type changed to: ${selectedVisualizationType}`);
            
            if(selectedSession) {
                console.log('Auto-refreshing visualization with new type...');
                analyzeSentiment();
            }
        });
    });
    
    console.log('Event listeners set up successfully');
}

function showError(message: string): void {
    alert('Error: ' + message);
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

(window as any).logCurrentState = logCurrentState;