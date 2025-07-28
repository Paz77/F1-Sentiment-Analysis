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
let selectedSessions: Set<string> = new Set();

const roundSelect = document.getElementById('round') as HTMLScriptElement;
const sessionGrid = document.getElementById('session-grid') as HTMLDivElement;
const analyzeButton = document.querySelector('button[type="submit]') as HTMLButtonElement;
const sentimentImage = document.getElementById('sentiment-image') as HTMLImageElement;

const API_BASE = 'http://localhost:5000/api';

document.addEventListener('DOMContentLoaded', (): void=>{
    console.log('Page loaded, initialzing F1 Sentiment Analysis app..');
    loadRaces();
    setupEventListeners();
});

async function loadRaces(): Promise<void>{
    try{
        console.log('loading races from API..')
        
        const response = await fetch(`${API_BASE}/races`);
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

async function loadSessions(roundNum: string) {
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

async function  analyzeSentiment(): Promise<void> {
    if(selectedSessions.size == 0) return;

    analyzeButton.disabled = true;
    analyzeButton.textContent = 'analyzing..'

    try{
        console.log('starting sentiment analysis..');

        const session = Array.from(selectedSessions)[0];
        console.log(`Analyzing session: ${session} for round: ${currentRound}`);

        const response = await fetch(`${API_BASE}/visualizations/${currentRound}/${session}`);
        const data: ApiResponse<Visualization[]> = await response.json();

        if (data.success && data.visualizations && data.visualizations.length > 0) {
            console.log('Visualization received:', data.visualizations[0].type);
            displayVisualization(data.visualizations[0]);
        } else {
            showError('No visualizations available for this session. Try running your data processing scripts first.');
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