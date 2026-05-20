from pathlib import Path

from workouttracker import cli


def test_cli_help():
    parser = cli.build_parser()
    help_text = parser.format_help()
    assert "serve" in help_text
    assert "import-exercises" in help_text


def test_cli_version(capsys):
    assert cli.main(["version"]) == 0
    out = capsys.readouterr().out
    assert "0.1.0" in out


def test_cli_migrate_creates_database(tmp_path):
    db_path = tmp_path / "workout.db"
    assert cli.main(["migrate", "--db", str(db_path)]) == 0
    assert db_path.exists()


def test_cli_serve_uses_defaults(monkeypatch, tmp_path):
    called = {}

    def fake_run(app_path, **kwargs):
        called["app_path"] = app_path
        called["kwargs"] = kwargs

    monkeypatch.setattr("uvicorn.run", fake_run)
    monkeypatch.setattr(cli, "DEFAULT_DB_PATH", tmp_path / "serve.db")

    assert cli.main(["serve"]) == 0
    assert Path(tmp_path / "serve.db").exists()
    assert called["app_path"] == "workouttracker.main:app"
    assert called["kwargs"]["host"] == "127.0.0.1"
    assert called["kwargs"]["port"] == 8000


def test_cli_serve_allows_overrides(monkeypatch, tmp_path):
    called = {}

    def fake_run(app_path, **kwargs):
        called["app_path"] = app_path
        called["kwargs"] = kwargs

    monkeypatch.setattr("uvicorn.run", fake_run)
    db_path = tmp_path / "override.db"

    assert cli.main(["serve", "--db", str(db_path), "--host", "0.0.0.0", "--port", "9000"]) == 0
    assert Path(db_path).exists()
    assert called["kwargs"]["host"] == "0.0.0.0"
    assert called["kwargs"]["port"] == 9000
