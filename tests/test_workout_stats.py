from workouttracker.services.workout_stats import WorkoutStats

stats = WorkoutStats()


def test_epley_1rm_single_rep():
    # 225 * (1 + 1/30) = 225 * 1.0333 ≈ 232.5
    result = stats.epley_1rm(225, 1)
    assert abs(result - 232.5) < 1.0


def test_epley_1rm_reps():
    # 225 * (1 + 5/30) = 225 * 1.1667 ≈ 262.5
    result = stats.epley_1rm(225, 5)
    assert abs(result - 262.5) < 1.0


def test_top_set_picks_highest_e1rm():
    sets = [
        {"weight": 225, "reps": 5, "weight_unit": "lb", "set_type": "working"},
        {"weight": 245, "reps": 2, "weight_unit": "lb", "set_type": "working"},
        {"weight": 135, "reps": 10, "weight_unit": "lb", "set_type": "warmup"},
    ]
    top = stats.top_set(sets)
    assert top["weight"] == 225  # higher e1RM: 262.5 vs 261.3


def test_top_set_ignores_warmup():
    sets = [
        {"weight": 300, "reps": 5, "set_type": "warmup"},
        {"weight": 225, "reps": 5, "set_type": "working"},
    ]
    top = stats.top_set(sets)
    assert top["weight"] == 225


def test_total_volume():
    sets = [
        {"weight": 135, "reps": 8},
        {"weight": 155, "reps": 5},
        {"weight": 165, "reps": 3},
    ]
    assert stats.total_volume(sets) == 135*8 + 155*5 + 165*3


def test_format_progress_groups_by_session():
    sets = [
        {"session_id": 1, "date": "2026-05-01", "weight": 135, "reps": 8, "set_type": "working", "weight_unit": "lb"},
        {"session_id": 1, "date": "2026-05-01", "weight": 155, "reps": 5, "set_type": "working", "weight_unit": "lb"},
        {"session_id": 2, "date": "2026-05-08", "weight": 140, "reps": 8, "set_type": "working", "weight_unit": "lb"},
    ]
    result = stats.format_progress(sets)
    assert len(result["sessions"]) == 2
    assert result["sessions"][0]["date"] == "2026-05-01"
    assert result["best_e1rm"] > 0
