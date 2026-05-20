import { fetchAPI, postAPI } from '../api.js';
import { toast } from '../toast.js';
import { esc, renderEmpty } from './utils.js';

export function renderExercises(container, { navigate }) {
    const pageSize = 25;
    let page = 0;

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
        const offset = page * pageSize;
        const results = await fetchAPI(`/exercises/search?q=${encodeURIComponent(q)}&limit=${pageSize}&offset=${offset}`);
        const body = container.querySelector('#exercise-results');
        if (!results.length) {
            body.innerHTML = `
                ${renderEmpty('search_off', page === 0 ? 'No exercises found' : 'No more exercises')}
                ${renderPager(results)}
            `;
            wirePager(results);
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
            ${renderPager(results)}
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
        wirePager(results);
    }

    function renderPager(results) {
        const start = page * pageSize + 1;
        const end = page * pageSize + results.length;
        return `
            <div class="pager">
                <span class="pager-label">${results.length ? `${start}-${end}` : `Page ${page + 1}`}</span>
                <button class="btn" id="prev-page" ${page === 0 ? 'disabled' : ''}>Previous</button>
                <button class="btn" id="next-page" ${results.length < pageSize ? 'disabled' : ''}>Next</button>
            </div>
        `;
    }

    function wirePager(results) {
        container.querySelector('#prev-page')?.addEventListener('click', () => {
            if (page === 0) return;
            page -= 1;
            search().catch(err => toast.error(err.message));
        });
        container.querySelector('#next-page')?.addEventListener('click', () => {
            if (results.length < pageSize) return;
            page += 1;
            search().catch(err => toast.error(err.message));
        });
    }

    input.addEventListener('input', () => {
        clearTimeout(timer);
        page = 0;
        timer = setTimeout(() => search().catch(err => toast.error(err.message)), 180);
    });
    search().catch(err => toast.error(err.message));
}
