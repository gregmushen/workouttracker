from app.repositories.exercises import ExerciseRepository


class ExerciseSearchService:
    def __init__(self, repo: ExerciseRepository):
        self.repo = repo

    def search(self, query: str, limit: int = 20) -> list[dict]:
        alias_match = self.repo.get_by_alias(query.strip())
        if alias_match:
            return [alias_match]
        return self.repo.search_fts(query, limit=limit)

    def resolve(self, query: str) -> dict | None:
        """Return single best match for a query (for bulk set logging)."""
        results = self.search(query, limit=1)
        return results[0] if results else None
