import { fetchAPI } from '../api.js';
import { toast } from '../toast.js';
import { esc, renderEmpty } from './utils.js';

export function renderRecords(container, { navigate }) {
    container.innerHTML = `
        <div class="page-header">
            <div>
                <h1 class="page-title">PRs</h1>
                <div class="page-subtitle">Best estimated 1RM by exercise.</div>
            </div>
        </div>
        <section class="card">
            <div class="card-header">
                <div class="card-title">Personal Records</div>
            </div>
            <div id="records-body"></div>
        </section>
    `;

    async function load() {
        const records = await fetchAPI('/workouts/personal-records');
        const body = container.querySelector('#records-body');
        if (!records.length) {
            body.innerHTML = renderEmpty('emoji_events', 'No PRs yet', 'Log weighted sets to build your PR table.');
            return;
        }
        body.innerHTML = `
            <table class="table">
                <thead>
                    <tr>
                        <th>Exercise</th>
                        <th>Best Set</th>
                        <th>Estimated 1RM</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    ${records.map(record => `
                        <tr class="table-row-link" data-id="${record.exercise_template_id}">
                            <td>
                                <div class="bold">${esc(record.name)}</div>
                                <div class="mono-sm muted">#${record.exercise_template_id}</div>
                            </td>
                            <td class="mono-sm">${esc(record.best_weight)} ${esc(record.weight_unit || '')} x ${esc(record.best_reps)}</td>
                            <td class="mono-sm bold">${esc(record.estimated_1rm)}</td>
                            <td class="text-right"><button class="btn btn-text" data-open="${record.exercise_template_id}">Open</button></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        body.querySelectorAll('[data-id]').forEach(row => {
            row.addEventListener('click', event => {
                if (event.target.closest('[data-open]')) return;
                navigate(`/exercise/${row.dataset.id}`);
            });
        });
        body.querySelectorAll('[data-open]').forEach(btn => {
            btn.addEventListener('click', event => {
                event.stopPropagation();
                navigate(`/exercise/${btn.dataset.open}`);
            });
        });
    }

    load().catch(err => toast.error(err.message));
}
