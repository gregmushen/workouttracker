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
                    <div class="field typeahead-field">
                        <label>Exercise</label>
                        <input class="input" name="exercise" id="exercise-input" placeholder="bench press" autocomplete="off" required>
                        <div class="typeahead-menu hidden" id="exercise-suggestions"></div>
                    </div>
                    <div class="form-row">
                        <div class="field"><label>Weight</label><input class="input" name="weight" type="text" inputmode="decimal" placeholder="135"></div>
                        <div class="field">
                            <label>Reps</label>
                            <input class="input" name="reps" type="text" inputmode="numeric" list="rep-options" placeholder="8" required>
                            <datalist id="rep-options">
                                <option value="1"><option value="3"><option value="5"><option value="6"><option value="8"><option value="10"><option value="12"><option value="15">
                            </datalist>
                        </div>
                        <div class="field">
                            <label>RPE</label>
                            <input class="input" name="rpe" type="text" inputmode="decimal" list="rpe-options" placeholder="8">
                            <datalist id="rpe-options">
                                <option value="6"><option value="6.5"><option value="7"><option value="7.5"><option value="8"><option value="8.5"><option value="9"><option value="9.5"><option value="10">
                            </datalist>
                        </div>
                        <div class="field">
                            <label>RIR</label>
                            <input class="input" name="rir" type="text" inputmode="decimal" list="rir-options" placeholder="2">
                            <datalist id="rir-options">
                                <option value="0"><option value="1"><option value="2"><option value="3"><option value="4"><option value="5">
                            </datalist>
                        </div>
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
    let exerciseTimer = null;
    let exerciseSuggestions = new Map();
    let exerciseSuggestionRows = [];
    let selectedExerciseId = null;

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

    async function resolveExercise(query) {
        if (selectedExerciseId && exerciseSuggestions.get(query) === selectedExerciseId) {
            return selectedExerciseId;
        }
        const selectedId = exerciseSuggestions.get(query);
        if (selectedId) {
            return selectedId;
        }
        const resolved = await postAPI('/exercises/resolve', { query });
        if (!resolved.best_match) {
            return null;
        }
        return resolved.best_match.id;
    }

    async function updateExerciseSuggestions(query) {
        const menu = container.querySelector('#exercise-suggestions');
        const trimmed = query.trim();
        selectedExerciseId = null;
        if (trimmed.length < 2) {
            exerciseSuggestions = new Map();
            exerciseSuggestionRows = [];
            menu.innerHTML = '';
            menu.classList.add('hidden');
            return;
        }
        const results = await fetchAPI(`/exercises/search?q=${encodeURIComponent(query)}&limit=8`);
        exerciseSuggestionRows = results;
        exerciseSuggestions = new Map(results.map(ex => [ex.name, ex.id]));
        const exactMatch = exerciseSuggestions.has(trimmed);
        menu.innerHTML = `
            ${results.map(ex => `
                <button class="typeahead-option" type="button" data-exercise-id="${ex.id}">
                    <span class="typeahead-main">${esc(ex.name)}</span>
                    <span class="typeahead-meta">${esc([ex.equipment, (ex.primary_muscles || [])[0]].filter(Boolean).join(' · ') || 'exercise')}</span>
                </button>
            `).join('')}
            ${exactMatch ? '' : `
                <button class="typeahead-option typeahead-create" type="button" data-create-exercise>
                    <span class="material-symbols-outlined">add</span>
                    <span>Create custom exercise: ${esc(trimmed)}</span>
                </button>
            `}
        `;
        menu.classList.remove('hidden');
    }

    container.querySelector('#exercise-input').addEventListener('input', event => {
        clearTimeout(exerciseTimer);
        const query = event.target.value;
        exerciseTimer = setTimeout(() => {
            updateExerciseSuggestions(query).catch(err => toast.error(err.message));
        }, 160);
    });

    container.querySelector('#exercise-suggestions').addEventListener('mousedown', event => {
        event.preventDefault();
    });

    container.querySelector('#exercise-suggestions').addEventListener('click', async event => {
        const option = event.target.closest('[data-exercise-id]');
        if (option) {
            const input = container.querySelector('#exercise-input');
            selectedExerciseId = Number(option.dataset.exerciseId);
            const match = exerciseSuggestionRows.find(ex => ex.id === selectedExerciseId);
            const name = match?.name || '';
            exerciseSuggestions = new Map([[name, selectedExerciseId]]);
            input.value = name;
            container.querySelector('#exercise-suggestions').classList.add('hidden');
            return;
        }
        const createOption = event.target.closest('[data-create-exercise]');
        if (createOption) {
            await createCustomExercise(container.querySelector('#exercise-input').value);
        }
    });

    container.querySelector('#exercise-input').addEventListener('blur', () => {
        setTimeout(() => container.querySelector('#exercise-suggestions').classList.add('hidden'), 120);
    });

    async function createCustomExercise(name) {
        const input = container.querySelector('#exercise-input');
        const trimmed = name.trim();
        if (!trimmed) return;
        const exercise = await postAPI('/exercises', {
            source: 'custom',
            name: trimmed,
            category: 'strength',
        });
        selectedExerciseId = exercise.id;
        exerciseSuggestions = new Map([[exercise.name, exercise.id]]);
        input.value = exercise.name;
        container.querySelector('#exercise-suggestions').classList.add('hidden');
        toast.success('Custom exercise created');
    }

    function parseOptionalNumber(value) {
        const text = String(value || '').trim();
        if (!text) return undefined;
        const parsed = Number(text);
        return Number.isFinite(parsed) ? parsed : NaN;
    }

    function parseRequiredNumber(value) {
        const parsed = parseOptionalNumber(value);
        return parsed === undefined ? NaN : parsed;
    }

    container.querySelector('#set-form').addEventListener('submit', async event => {
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        const exerciseId = await resolveExercise(String(data.get('exercise') || ''));
        if (!exerciseId) {
            toast.error('Exercise not found');
            return;
        }
        const weight = parseOptionalNumber(data.get('weight'));
        const reps = parseRequiredNumber(data.get('reps'));
        const rpe = parseOptionalNumber(data.get('rpe'));
        const rir = parseOptionalNumber(data.get('rir'));
        if ([weight, reps, rpe, rir].some(value => Number.isNaN(value))) {
            toast.error('Weight, reps, RPE, and RIR must be numbers');
            return;
        }
        const body = {
            exercise_template_id: exerciseId,
            weight,
            weight_unit: weight !== undefined ? 'lb' : undefined,
            reps,
            rpe,
            rir,
            set_type: data.get('set_type'),
        };
        await postAPI(`/workouts/sessions/${sessionId}/sets`, body);
        event.currentTarget.reset();
        exerciseSuggestions = new Map();
        exerciseSuggestionRows = [];
        selectedExerciseId = null;
        container.querySelector('#exercise-suggestions').innerHTML = '';
        container.querySelector('#exercise-suggestions').classList.add('hidden');
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
