import { fetchAPI, postAPI } from '../api.js';
import { toast } from '../toast.js';
import { esc, setSummary, renderEmpty } from './utils.js';

export function renderProgress(container, { navigate }) {
    container.innerHTML = `
        <div class="page-header">
            <div>
                <h1 class="page-title">Progress</h1>
                <div class="page-subtitle">Resolve an exercise and review recent performance.</div>
            </div>
        </div>
        <section class="card">
            <div class="card-body">
                <form id="progress-form" style="display:flex;gap:10px">
                    <input class="input" name="exercise" placeholder="bench press" required>
                    <button class="btn btn-primary" type="submit">Review</button>
                </form>
            </div>
        </section>
        <div id="progress-result" style="margin-top:16px"></div>
    `;

    container.querySelector('#progress-form').addEventListener('submit', async event => {
        event.preventDefault();
        const query = new FormData(event.currentTarget).get('exercise');
        const resolved = await postAPI('/exercises/resolve', { query });
        if (!resolved.best_match) {
            toast.error('Exercise not found');
            return;
        }
        const exerciseId = resolved.best_match.id;
        const [recent, progress, prs] = await Promise.all([
            fetchAPI(`/workouts/recent?exercise_id=${exerciseId}&limit=6`),
            fetchAPI(`/workouts/progress?exercise_id=${exerciseId}`),
            fetchAPI('/workouts/personal-records'),
        ]);
        const pr = prs.find(item => item.exercise_template_id === exerciseId);
        renderResult(resolved.best_match, recent, progress, pr);
    });

    function renderResult(exercise, recent, progress, pr) {
        const sessions = progress.sessions || [];
        const recentSessions = recent.sessions || [];
        container.querySelector('#progress-result').innerHTML = `
            <div class="grid grid-3">
                <div class="card stat"><div class="stat-label">Exercise</div><div class="stat-value" style="font-size:18px">${esc(exercise.name)}</div></div>
                <div class="card stat"><div class="stat-label">Best e1RM</div><div class="stat-value">${esc(progress.best_e1rm || pr?.estimated_1rm || 0)}</div></div>
                <div class="card stat"><div class="stat-label">Sessions</div><div class="stat-value">${esc(progress.session_count || 0)}</div></div>
            </div>
            <section class="card" style="margin-top:16px">
                <div class="card-header">
                    <div class="card-title">Recent Sessions</div>
                    <button class="btn btn-text" id="open-exercise">Open exercise</button>
                </div>
                ${recentSessions.length ? `
                    <table class="table">
                        <thead><tr><th>Date</th><th>Top Set</th><th>Volume</th></tr></thead>
                        <tbody>${recentSessions.map(session => `
                            <tr>
                                <td class="mono-sm">${esc(session.date)}</td>
                                <td class="mono-sm">${esc(session.top_set ? setSummary(session.top_set) : '-')}</td>
                                <td class="mono-sm">${esc(session.volume)}</td>
                            </tr>
                        `).join('')}</tbody>
                    </table>
                ` : renderEmpty('monitoring', 'No progress data')}
            </section>
            <section class="card" style="margin-top:16px">
                <div class="card-header"><div class="card-title">Trend</div></div>
                ${sessions.length ? `
                    <table class="table">
                        <thead><tr><th>Date</th><th>Top Set</th><th>Estimated 1RM</th><th>Volume</th></tr></thead>
                        <tbody>${sessions.slice(-20).reverse().map(session => `
                            <tr>
                                <td class="mono-sm">${esc(session.date)}</td>
                                <td class="mono-sm">${esc(session.top_set ? setSummary(session.top_set) : '-')}</td>
                                <td class="mono-sm">${esc(session.estimated_1rm)}</td>
                                <td class="mono-sm">${esc(session.volume)}</td>
                            </tr>
                        `).join('')}</tbody>
                    </table>
                ` : renderEmpty('timeline', 'No trend yet')}
            </section>
        `;
        container.querySelector('#open-exercise')?.addEventListener('click', () => navigate(`/exercise/${exercise.id}`));
    }
}
