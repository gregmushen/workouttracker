class TestUIRoutes:
    def test_root_serves_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "Workout Tracker" in resp.text

    def test_client_routes_serve_html(self, client):
        for path in ["/today", "/sessions", "/sessions/123", "/exercises", "/exercise/123", "/progress", "/settings"]:
            resp = client.get(path)
            assert resp.status_code == 200
            assert "text/html" in resp.headers["content-type"]

    def test_static_assets_served(self, client):
        css = client.get("/static/style.css")
        js = client.get("/static/app.js")
        assert css.status_code == 200
        assert "text/css" in css.headers["content-type"]
        assert js.status_code == 200
        assert "javascript" in js.headers["content-type"]

    def test_api_routes_not_shadowed(self, client):
        health = client.get("/health")
        openapi = client.get("/openapi.json")
        summary = client.get("/workouts/summary")

        assert health.status_code == 200
        assert health.json()["status"] == "ok"
        assert openapi.status_code == 200
        assert "x-agent-guidance" in openapi.json()
        assert summary.status_code == 200
        assert "sessions" in summary.json()

    def test_free_exercise_db_images_use_upstream_urls(self, client, db):
        from workouttracker.repositories.exercises import ExerciseRepository

        repo = ExerciseRepository(db)
        repo.ensure_fts()
        eid = repo.create(
            source="free_exercise_db",
            source_code="demo",
            name="Demo Exercise",
            image_paths='["Demo/0.jpg"]',
        )

        resp = client.get(f"/exercises/{eid}")

        assert resp.status_code == 200
        assert resp.json()["image_urls"] == [
            "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises/Demo/0.jpg"
        ]
