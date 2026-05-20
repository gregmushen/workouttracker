import { fetchAPI } from '../api.js';
import { toast } from '../toast.js';
import { esc, setSummary, renderEmpty } from './utils.js';

export function renderExerciseDetail(container, { exerciseId }) {
    container.innerHTML = `
        <div class="page-header">
            <div>
                <h1 class="page-title" id="exercise-title">Exercise</h1>
                <div class="page-subtitle" id="exercise-subtitle">Loading...</div>
            </div>
        </div>
        <div class="grid grid-2">
            <section class="card">
                <div class="card-header"><div class="card-title">Details</div></div>
                <div class="card-body" id="exercise-details"></div>
            </section>
            <section class="card">
                <div class="card-header"><div class="card-title">Recent Sets</div></div>
                <div id="recent-body"></div>
            </section>
        </div>
        <section class="card" style="margin-top:16px">
            <div class="card-header"><div class="card-title">Progress</div></div>
            <div id="progress-body"></div>
        </section>
    `;

    async function load() {
        const exercise = await fetchAPI(`/exercises/${exerciseId}`);
        container.querySelector('#exercise-title').textContent = exercise.name;
        container.querySelector('#exercise-subtitle').textContent = [exercise.category, exercise.equipment, exercise.level].filter(Boolean).join(' - ');
        container.querySelector('#exercise-details').innerHTML = `
            <div class="grid">
                ${renderImageGallery(exercise.image_urls || [])}
                <div><span class="pill">${esc(exercise.category || 'uncategorized')}</span> <span class="pill">${esc(exercise.equipment || 'equipment unknown')}</span></div>
                <div><strong>Primary:</strong> ${esc((exercise.primary_muscles || []).join(', ') || '-')}</div>
                <div><strong>Secondary:</strong> ${esc((exercise.secondary_muscles || []).join(', ') || '-')}</div>
                ${(exercise.instructions || []).length ? `<ol style="padding-left:20px">${exercise.instructions.map(i => `<li>${esc(i)}</li>`).join('')}</ol>` : ''}
            </div>
        `;
        loadRecent();
        loadProgress();
    }

    function renderImageGallery(imageUrls) {
        if (!imageUrls.length) return '';
        return `
            <div class="exercise-gallery">
                ${imageUrls.map((url, index) => `
                    <figure class="exercise-gallery-item">
                        <img src="${esc(url)}" alt="">
                        <figcaption>${index + 1}</figcaption>
                    </figure>
                `).join('')}
            </div>
        `;
    }

    async function loadRecent() {
        try {
            renderRecent(await fetchAPI(`/workouts/recent?exercise_id=${exerciseId}&limit=8`));
        } catch (err) {
            container.querySelector('#recent-body').innerHTML = renderEmpty('error', 'Could not load recent sets', err.message);
        }
    }

    async function loadProgress() {
        try {
            renderProgress(await fetchAPI(`/workouts/progress?exercise_id=${exerciseId}`));
        } catch (err) {
            container.querySelector('#progress-body').innerHTML = renderEmpty('error', 'Could not load progress', err.message);
        }
    }

    function renderRecent(recent) {
        const rows = recent.sessions || [];
        const body = container.querySelector('#recent-body');
        if (!rows.length) {
            body.innerHTML = renderEmpty('history', 'No recent sets');
            return;
        }
        body.innerHTML = `
            <table class="table">
                <thead><tr><th>Date</th><th>Top Set</th><th>Volume</th></tr></thead>
                <tbody>${rows.map(session => `<tr><td class="mono-sm">${esc(session.date || '')}</td><td class="mono-sm">${esc(session.top_set ? setSummary(session.top_set) : '-')}</td><td class="mono-sm">${esc(session.volume ?? '-')}</td></tr>`).join('')}</tbody>
            </table>
        `;
    }

    function renderProgress(progress) {
        const points = progress.sessions || [];
        const body = container.querySelector('#progress-body');
        if (!points.length) {
            body.innerHTML = renderEmpty('monitoring', 'No progress data');
            return;
        }
        body.innerHTML = `
            <table class="table">
                <thead><tr><th>Date</th><th>Best Weight</th><th>Volume</th><th>Estimated 1RM</th></tr></thead>
                <tbody>${points.slice(-20).reverse().map(row => `
                    <tr>
                        <td class="mono-sm">${esc(row.date || '')}</td>
                        <td class="mono-sm">${esc(row.top_set ? setSummary(row.top_set) : '-')}</td>
                        <td class="mono-sm">${esc(row.volume ?? '-')}</td>
                        <td class="mono-sm">${esc(row.estimated_1rm ?? '-')}</td>
                    </tr>
                `).join('')}</tbody>
            </table>
        `;
    }

    load().catch(err => {
        container.querySelector('#exercise-subtitle').textContent = 'Could not load exercise';
        container.querySelector('#exercise-details').innerHTML = renderEmpty('error', 'Exercise unavailable', err.message);
        toast.error(err.message);
    });
}
