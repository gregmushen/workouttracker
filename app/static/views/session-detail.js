import { fetchAPI, postAPI, deleteAPI } from '../api.js';
import { toast } from '../toast.js';
import { esc, fmtDate, setSummary, renderEmpty } from './utils.js';

export function renderSessionDetail(container, { sessionId, navigate }) {
    container.innerHTML = `
        <div class="page-header">
            <div>
                <h1 class="page-title">Session</h1>
                <div class="page-subtitle" id="session-subtitle">Loading...</div>
            </div>
            <button class="btn" id="close-session">Close session</button>
        </div>
        <div class="grid grid-2">
            <section class="card">
                <div class="card-header"><div class="card-title">Sets</div></div>
                <div id="sets-body"></div>
            </section>
            <section class="card">
                <div class="card-header"><div class="card-title">Add Set</div></div>
                <form class="card-body" id="set-form">
                    <div class="field">
                        <label>Exercise</label>
                        <input class="input" name="exercise" placeholder="bench press" required>
                    </div>
                    <div class="form-row">
                        <div class="field"><label>Weight</label><input class="input" name="weight" type="number" step="0.5"></div>
                        <div class="field"><label>Reps</label><input class="input" name="reps" type="number" step="1" required></div>
                        <div class="field"><label>RPE</label><input class="input" name="rpe" type="number" step="0.5"></div>
                        <div class="field"><label>RIR</label><input class="input" name="rir" type="number" step="0.5"></div>
                    </div>
                    <div class="field">
                        <label>Type</label>
                        <select class="select" name="set_type">
                            <option value="working">working</option>
                            <option value="warmup">warmup</option>
                            <option value="amrap">amrap</option>
                            <option value="failure">failure</option>
                            <option value="drop">drop</option>
                        </select>
                    </div>
                    <button class="btn btn-primary" type="submit">Add set</button>
                </form>
            </section>
        </div>
    `;

    let session = null;

    async function load() {
        session = await fetchAPI(`/workouts/sessions/${sessionId}`);
        const sets = await fetchAPI(`/workouts/sessions/${sessionId}/sets`);
        container.querySelector('#session-subtitle').textContent = `${fmtDate(session.date)} - ${session.title || 'Lift'}`;
        container.querySelector('#close-session').disabled = Boolean(session.ended_at);
        const body = container.querySelector('#sets-body');
        if (!sets.length) {
            body.innerHTML = renderEmpty('list_alt', 'No sets yet', 'Add a set from the form.');
            return;
        }
        body.innerHTML = `
            <table class="table">
                <thead><tr><th>Exercise</th><th>Set</th><th></th></tr></thead>
                <tbody>
                    ${sets.map(set => `
                        <tr>
                            <td><a href="/exercise/${set.exercise_template_id}" data-link class="bold">${esc(set.exercise_name || `Exercise ${set.exercise_template_id}`)}</a></td>
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

    container.querySelector('#set-form').addEventListener('submit', async event => {
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        const resolved = await postAPI('/exercises/resolve', { query: data.get('exercise') });
        if (!resolved.best_match) {
            toast.error('Exercise not found');
            return;
        }
        const body = {
            exercise_template_id: resolved.best_match.id,
            weight: data.get('weight') ? Number(data.get('weight')) : undefined,
            weight_unit: data.get('weight') ? 'lb' : undefined,
            reps: Number(data.get('reps')),
            rpe: data.get('rpe') ? Number(data.get('rpe')) : undefined,
            rir: data.get('rir') ? Number(data.get('rir')) : undefined,
            set_type: data.get('set_type'),
        };
        await postAPI(`/workouts/sessions/${sessionId}/sets`, body);
        event.currentTarget.reset();
        toast.success('Set added');
        await load();
    });

    container.querySelector('#close-session').addEventListener('click', async () => {
        await postAPI(`/workouts/sessions/${sessionId}/close`, {});
        toast.success('Session closed');
        await load();
    });

    load().catch(err => {
        toast.error(err.message);
        navigate('/sessions');
    });
}
