import { fetchAPI, postAPI } from '../api.js';
import { toast } from '../toast.js';
import { esc, todayISO, fmtDate, renderEmpty } from './utils.js';

export function renderSessions(container, { navigate }) {
    container.innerHTML = `
        <div class="page-header">
            <div>
                <h1 class="page-title">Sessions</h1>
                <div class="page-subtitle">Training history by date.</div>
            </div>
            <button class="btn btn-primary" id="new-session">
                <span class="material-symbols-outlined">add</span>
                Session
            </button>
        </div>
        <section class="card">
            <div class="card-header">
                <div class="card-title">Recent Sessions</div>
            </div>
            <div id="sessions-body"></div>
        </section>
    `;

    async function load() {
        const sessions = await fetchAPI('/workouts/sessions');
        const body = container.querySelector('#sessions-body');
        if (!sessions.length) {
            body.innerHTML = renderEmpty('calendar_month', 'No sessions yet', 'Create one to start logging.');
            return;
        }
        body.innerHTML = `
            <table class="table">
                <thead><tr><th>Date</th><th>Title</th><th>Status</th><th></th></tr></thead>
                <tbody>
                    ${sessions.map(session => `
                        <tr class="table-row-link" data-id="${session.id}">
                            <td class="mono-sm">${esc(fmtDate(session.date))}</td>
                            <td class="bold">${esc(session.title || 'Lift')}</td>
                            <td>${session.ended_at ? '<span class="badge badge-green">closed</span>' : '<span class="pill">open</span>'}</td>
                            <td class="text-right mono-sm">#${session.id}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        body.querySelectorAll('[data-id]').forEach(row => {
            row.addEventListener('click', () => navigate(`/sessions/${row.dataset.id}`));
        });
    }

    container.querySelector('#new-session').addEventListener('click', async () => {
        const session = await postAPI('/workouts/sessions', {
            date: todayISO(),
            title: 'Lift',
            started_at: new Date().toISOString(),
        });
        navigate(`/sessions/${session.id}`);
    });

    load().catch(err => toast.error(err.message));
}
