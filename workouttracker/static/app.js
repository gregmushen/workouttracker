import { fetchAPI, onAuthRequired, setAuthToken, getAuthToken } from './api.js';
import { renderToday } from './views/today.js';
import { renderSessions } from './views/sessions.js';
import { renderSessionDetail } from './views/session-detail.js';
import { renderExercises } from './views/exercises.js';
import { renderExerciseDetail } from './views/exercise-detail.js';
import { renderProgress } from './views/progress.js';
import { renderRecords } from './views/records.js';
import { renderSettings } from './views/settings.js';

const app = document.getElementById('app');
let authenticated = Boolean(getAuthToken());

const routes = [
    { pattern: /^\/$/, view: 'today' },
    { pattern: /^\/today$/, view: 'today' },
    { pattern: /^\/sessions$/, view: 'sessions' },
    { pattern: /^\/sessions\/(\d+)$/, view: 'session-detail' },
    { pattern: /^\/exercises$/, view: 'exercises' },
    { pattern: /^\/exercise\/(\d+)$/, view: 'exercise-detail' },
    { pattern: /^\/progress$/, view: 'progress' },
    { pattern: /^\/records$/, view: 'records' },
    { pattern: /^\/settings$/, view: 'settings' },
];

function navigate(path) {
    history.pushState(null, '', path);
    window.scrollTo(0, 0);
    render();
}

window.addEventListener('popstate', render);
document.addEventListener('click', (event) => {
    const link = event.target.closest('[data-link]');
    if (!link) return;
    event.preventDefault();
    navigate(link.getAttribute('href'));
});

onAuthRequired(() => {
    authenticated = false;
    renderAuth();
});

async function checkAuth() {
    try {
        await fetchAPI('/workouts/summary');
        return true;
    } catch {
        return false;
    }
}

function renderSidebar(path) {
    const items = [
        ['/', 'today', 'Today', /^\/$|^\/today/],
        ['/sessions', 'calendar_month', 'Sessions', /^\/sessions/],
        ['/exercises', 'fitness_center', 'Exercises', /^\/exercises/],
        ['/progress', 'monitoring', 'Progress', /^\/progress/],
        ['/records', 'emoji_events', 'PRs', /^\/records/],
        ['/settings', 'settings', 'Settings', /^\/settings/],
    ];
    return `
        <aside class="sidebar">
            <div class="sidebar-brand">
                <a href="/" data-link class="brand">Workout Tracker</a>
            </div>
            <nav class="sidebar-nav">
                ${items.map(([href, icon, label, regex]) => `
                    <a href="${href}" data-link class="sidebar-link ${regex.test(path) ? 'active' : ''}">
                        <span class="material-symbols-outlined">${icon}</span>
                        <span>${label}</span>
                    </a>
                `).join('')}
            </nav>
            <div class="sidebar-footer">
                <a href="/openapi.json" target="_blank" class="sidebar-link">
                    <span class="material-symbols-outlined">schema</span>
                    <span>OpenAPI</span>
                </a>
            </div>
        </aside>
    `;
}

function renderAuth() {
    app.innerHTML = `
        <div class="auth-shell">
            <div class="card auth-card">
                <div class="card-header">
                    <div>
                        <div class="card-title">Workout Tracker</div>
                        <div class="page-subtitle">Enter your API bearer token.</div>
                    </div>
                </div>
                <form class="card-body" id="auth-form">
                    <div class="field">
                        <label for="auth-token">Bearer token</label>
                        <input class="input" id="auth-token" type="password" autocomplete="current-password" autofocus>
                    </div>
                    <button class="btn btn-primary" type="submit">Continue</button>
                </form>
            </div>
        </div>
    `;
    app.querySelector('#auth-form').addEventListener('submit', async (event) => {
        event.preventDefault();
        const token = app.querySelector('#auth-token').value.trim();
        setAuthToken(token);
        authenticated = await checkAuth();
        if (authenticated) render();
        else app.querySelector('#auth-token').value = '';
    });
}

async function render() {
    const path = location.pathname;

    if (!authenticated) {
        authenticated = await checkAuth();
    }
    if (!authenticated) {
        renderAuth();
        return;
    }

    let matched = null;
    let params = [];
    for (const route of routes) {
        const match = path.match(route.pattern);
        if (match) {
            matched = route.view;
            params = match.slice(1);
            break;
        }
    }
    if (!matched) matched = 'not-found';

    app.innerHTML = `
        <div class="sidebar-overlay" id="sidebar-overlay"></div>
        ${renderSidebar(path)}
        <div class="mobile-header">
            <a href="/" data-link class="brand">Workout Tracker</a>
            <button class="hamburger" id="hamburger-btn" aria-label="Open menu">
                <span class="material-symbols-outlined">menu</span>
            </button>
        </div>
        <main class="content" id="view"></main>
    `;

    const sidebar = app.querySelector('.sidebar');
    const overlay = app.querySelector('#sidebar-overlay');
    app.querySelector('#hamburger-btn')?.addEventListener('click', () => {
        sidebar.classList.add('open');
        overlay.classList.add('open');
    });
    overlay.addEventListener('click', () => {
        sidebar.classList.remove('open');
        overlay.classList.remove('open');
    });

    const view = app.querySelector('#view');
    switch (matched) {
        case 'today':
            document.title = 'Today - Workout Tracker';
            renderToday(view, { navigate });
            break;
        case 'sessions':
            document.title = 'Sessions - Workout Tracker';
            renderSessions(view, { navigate });
            break;
        case 'session-detail':
            document.title = `Session ${params[0]} - Workout Tracker`;
            renderSessionDetail(view, { sessionId: Number(params[0]), navigate });
            break;
        case 'exercises':
            document.title = 'Exercises - Workout Tracker';
            renderExercises(view, { navigate });
            break;
        case 'exercise-detail':
            document.title = `Exercise ${params[0]} - Workout Tracker`;
            renderExerciseDetail(view, { exerciseId: Number(params[0]), navigate });
            break;
        case 'progress':
            document.title = 'Progress - Workout Tracker';
            renderProgress(view, { navigate });
            break;
        case 'records':
            document.title = 'PRs - Workout Tracker';
            renderRecords(view, { navigate });
            break;
        default:
            view.innerHTML = `
                <div class="empty-state">
                    <span class="material-symbols-outlined">wrong_location</span>
                    <div class="bold">Route not found</div>
                    <a href="/" data-link class="btn btn-primary">Back to Today</a>
                </div>
            `;
    }
}

render();
