import { fetchAPI, postAPI } from '../api.js';
import { toast } from '../toast.js';
import { esc, renderEmpty } from './utils.js';

export function renderExercises(container, { navigate }) {
    container.innerHTML = `
        <div class="page-header">
            <div>
                <h1 class="page-title">Exercises</h1>
                <div class="page-subtitle">Search the exercise library and save preferred mappings.</div>
            </div>
        </div>
        <section class="card">
            <div class="card-body">
                <div class="field">
                    <label>Search</label>
                    <input class="input" id="exercise-search" placeholder="bench, row, squat">
                </div>
            </div>
            <div id="exercise-results"></div>
        </section>
    `;

    const input = container.querySelector('#exercise-search');
    let timer = null;

    async function search() {
        const q = input.value.trim();
        const results = await fetchAPI(`/exercises/search?q=${encodeURIComponent(q)}&limit=25`);
        const body = container.querySelector('#exercise-results');
        if (!results.length) {
            body.innerHTML = renderEmpty('search_off', 'No exercises found');
            return;
        }
        body.innerHTML = `
            <table class="table">
                <thead><tr><th>Name</th><th>Equipment</th><th>Muscles</th><th></th></tr></thead>
                <tbody>
                    ${results.map(ex => `
                        <tr class="table-row-link" data-id="${ex.id}">
                            <td>
                                <div class="exercise-row">
                                    ${ex.image_urls?.[0] ? `<img class="exercise-thumb" src="${esc(ex.image_urls[0])}" alt="">` : ''}
                                    <div>
                                        <div class="bold">${esc(ex.name)}</div>
                                        <div class="mono-sm muted">#${ex.id}</div>
                                    </div>
                                </div>
                            </td>
                            <td>${esc(ex.equipment || '-')}</td>
                            <td>${esc((ex.primary_muscles || []).join(', ') || '-')}</td>
                            <td class="text-right"><button class="btn btn-text" data-prefer="${ex.id}" data-name="${esc(ex.name)}">Prefer</button></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        body.querySelectorAll('tr[data-id]').forEach(row => {
            row.addEventListener('click', event => {
                if (event.target.closest('[data-prefer]')) return;
                navigate(`/exercise/${row.dataset.id}`);
            });
        });
        body.querySelectorAll('[data-prefer]').forEach(btn => {
            btn.addEventListener('click', async event => {
                event.stopPropagation();
                await postAPI('/exercises/preferences', {
                    phrase: input.value.trim() || btn.dataset.name,
                    preferred_exercise_id: Number(btn.dataset.prefer),
                    context: {},
                });
                toast.success('Preference saved');
            });
        });
    }

    input.addEventListener('input', () => {
        clearTimeout(timer);
        timer = setTimeout(() => search().catch(err => toast.error(err.message)), 180);
    });
    search().catch(err => toast.error(err.message));
}
