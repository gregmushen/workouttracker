import { fetchAPI, postAPI, deleteAPI } from '../api.js';
import { toast } from '../toast.js';
import { esc, todayISO, fmtDate, setSummary, renderEmpty, parseQuickLog } from './utils.js';

export function renderToday(container, { navigate }) {
    const today = todayISO();
    container.innerHTML = `
        <div class="page-header">
            <div>
                <h1 class="page-title">Today</h1>
                <div class="page-subtitle">${fmtDate(today)}</div>
            </div>
            <button class="btn btn-primary" id="new-session">
                <span class="material-symbols-outlined">add</span>
                Session
            </button>
        </div>
        <div class="grid grid-3" id="stats"></div>
        <div class="grid grid-2" style="margin-top:16px">
            <section class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">Quick Log</div>
                        <div class="page-subtitle">Example: bench 135x8, 155x5 @8</div>
                    </div>
                </div>
                <div class="card-body">
                    <textarea class="textarea quick-log" id="quick-log" placeholder="squat 225x5, 245x3 @8"></textarea>
                    <div style="display:flex;gap:8px;margin-top:12px">
                        <button class="btn btn-primary" id="log-sets">Log sets</button>
                        <button class="btn" id="open-session">Open session</button>
                    </div>
                    <div id="resolve-choices" class="choice-list" style="margin-top:12px"></div>
                </div>
            </section>
            <section class="card">
                <div class="card-header">
                    <div class="card-title">Today's Session</div>
                    <span id="session-label" class="pill">loading</span>
                </div>
                <div id="session-body" class="card-body"></div>
            </section>
        </div>
    `;

    let session = null;
    let sets = [];

    async function ensureSession() {
        const sessions = await fetchAPI(`/workouts/sessions?start=${today}&end=${today}`);
        session = sessions[0] || await postAPI('/workouts/sessions', {
            date: today,
            title: 'Lift',
            started_at: new Date().toISOString(),
        });
        return session;
    }

    async function load() {
        const summary = await fetchAPI(`/workouts/summary?start=${today}&end=${today}`);
        const sessions = await fetchAPI(`/workouts/sessions?start=${today}&end=${today}`);
        session = sessions[0] || null;
        sets = session ? await loadSetsForSession(session.id) : [];
        renderStats(summary);
        renderSession();
    }

    async function loadSetsForSession(sessionId) {
        return fetchAPI(`/workouts/sessions/${sessionId}/sets`);
    }

    function renderStats(summary) {
        container.querySelector('#stats').innerHTML = `
            <div class="card stat"><div class="stat-label">Sessions</div><div class="stat-value">${summary.sessions || 0}</div></div>
            <div class="card stat"><div class="stat-label">Sets</div><div class="stat-value">${summary.total_sets || 0}</div></div>
            <div class="card stat"><div class="stat-label">Volume</div><div class="stat-value">${Math.round(summary.total_volume || 0)}</div></div>
        `;
    }

    function renderSession() {
        container.querySelector('#session-label').textContent = session ? `#${session.id}` : 'none';
        const body = container.querySelector('#session-body');
        if (!session) {
            body.innerHTML = renderEmpty('fitness_center', 'No session yet', 'Create one or log a quick set.');
            return;
        }
        if (!sets.length) {
            body.innerHTML = renderEmpty('list_alt', 'No sets logged', 'Use Quick Log to add your first set.');
            return;
        }
        body.innerHTML = `
            <table class="table">
                <thead><tr><th>Exercise</th><th>Set</th><th></th></tr></thead>
                <tbody>
                    ${sets.map(set => `
                        <tr>
                            <td class="bold">${esc(set.exercise_name || `Exercise ${set.exercise_template_id}`)}</td>
                            <td class="mono-sm">${esc(setSummary(set))}</td>
                            <td class="text-right"><button class="btn btn-text btn-danger" data-delete="${set.id}">Delete</button></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        body.querySelectorAll('[data-delete]').forEach(btn => {
            btn.addEventListener('click', async () => {
                await deleteAPI(`/workouts/sets/${btn.dataset.delete}`);
                toast.success('Set deleted');
                await load();
            });
        });
    }

    async function logSets(exerciseQuery) {
        const parsed = parseQuickLog(container.querySelector('#quick-log').value);
        if (!parsed) {
            toast.error('Use a pattern like bench 135x8, 155x5 @8');
            return;
        }
        await ensureSession();
        await postAPI(`/workouts/sessions/${session.id}/sets/bulk`, {
            exercise_query: exerciseQuery || parsed.exercise,
            sets: parsed.sets,
        });
        container.querySelector('#quick-log').value = '';
        container.querySelector('#resolve-choices').innerHTML = '';
        toast.success('Sets logged');
        await load();
    }

    container.querySelector('#new-session').addEventListener('click', async () => {
        session = await postAPI('/workouts/sessions', {
            date: today,
            title: 'Lift',
            started_at: new Date().toISOString(),
        });
        navigate(`/sessions/${session.id}`);
    });
    container.querySelector('#open-session').addEventListener('click', async () => {
        await ensureSession();
        navigate(`/sessions/${session.id}`);
    });
    container.querySelector('#log-sets').addEventListener('click', async () => {
        const parsed = parseQuickLog(container.querySelector('#quick-log').value);
        if (!parsed) {
            toast.error('Use a pattern like bench 135x8, 155x5 @8');
            return;
        }
        const resolved = await postAPI('/exercises/resolve', { query: parsed.exercise });
        if (resolved.needs_confirmation && resolved.alternatives.length) {
            container.querySelector('#resolve-choices').innerHTML = resolved.alternatives.map(match => `
                <button class="btn choice-btn" data-name="${esc(match.name)}">
                    <span>${esc(match.name)}</span>
                    <span class="mono-sm">${Math.round(match.confidence * 100)}%</span>
                </button>
            `).join('');
            container.querySelectorAll('[data-name]').forEach(btn => {
                btn.addEventListener('click', () => logSets(btn.dataset.name));
            });
            return;
        }
        await logSets(resolved.best_match?.name || parsed.exercise);
    });

    load().catch(err => toast.error(err.message));
}
