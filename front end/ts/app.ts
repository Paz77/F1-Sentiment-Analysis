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

    }
    catch(error){
        
    }
}