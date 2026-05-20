from workouttracker.repositories.exercises import ExerciseRepository


class ExerciseSearchService:
    def __init__(self, repo: ExerciseRepository):
        self.repo = repo

    def search(self, query: str, limit: int = 20, **filters) -> list[dict]:
        alias_match = self.repo.get_by_alias(query.strip())
        if alias_match and self._matches_filters(alias_match, filters):
            return [alias_match]
        if query.strip():
            return self.repo.search_fts(query, limit=limit, **filters)
        return self.repo.list_filtered(limit=limit, **filters)

    def resolve(self, query: str) -> dict | None:
        """Return single best match for a query (for bulk set logging)."""
        results = self.search(query, limit=1)
        return results[0] if results else None

    def resolve_detailed(self, query: str, *, user_id: int, context: dict | None = None) -> dict:
        context = context or {}
        preference = self.repo.get_preference(user_id=user_id, phrase=query)
        if preference:
            preferred = self.repo.get(preference["preferred_exercise_id"])
            if preferred:
                match = self._match(preferred, 0.98, "user preference")
                self.repo.log_search(
                    user_id=user_id,
                    query=query,
                    matched_exercise_id=preferred["id"],
                    confidence=match["confidence"],
                    required_confirmation=False,
                )
                return {
                    "query": query,
                    "best_match": match,
                    "alternatives": [],
                    "needs_confirmation": False,
                    "confirmation_prompt": None,
                }

        alias_match = self.repo.get_by_alias(query)
        if alias_match:
            match = self._match(alias_match, 0.94, "exact alias")
            self.repo.log_search(
                user_id=user_id,
                query=query,
                matched_exercise_id=alias_match["id"],
                confidence=match["confidence"],
                required_confirmation=False,
            )
            return {
                "query": query,
                "best_match": match,
                "alternatives": [],
                "needs_confirmation": False,
                "confirmation_prompt": None,
            }

        exact_name = self.repo.get_by_normalized_name(query)
        if exact_name:
            match = self._match(exact_name, 0.92, "exact name")
            self.repo.log_search(
                user_id=user_id,
                query=query,
                matched_exercise_id=exact_name["id"],
                confidence=match["confidence"],
                required_confirmation=False,
            )
            return {
                "query": query,
                "best_match": match,
                "alternatives": [],
                "needs_confirmation": False,
                "confirmation_prompt": None,
            }

        results = self.search(query, limit=5)
        matches = [self._match(r, self._confidence(query, r, i, context), "full-text match")
                   for i, r in enumerate(results)]
        needs_confirmation = True
        best_match = None

        if matches:
            top = matches[0]
            second = matches[1] if len(matches) > 1 else None
            close_second = second and top["confidence"] - second["confidence"] < 0.08
            recent_ids = set(context.get("recent_exercise_ids", []))
            recently_used = top["id"] in recent_ids
            if top["confidence"] >= 0.90 or (top["confidence"] >= 0.75 and recently_used and not close_second):
                needs_confirmation = False
                best_match = top

        prompt = None
        if needs_confirmation:
            names = [m["name"] for m in matches[:3]]
            prompt = f"Which exercise do you mean: {', '.join(names)}?" if names else None

        self.repo.log_search(
            user_id=user_id,
            query=query,
            matched_exercise_id=best_match["id"] if best_match else None,
            confidence=best_match["confidence"] if best_match else (matches[0]["confidence"] if matches else None),
            required_confirmation=needs_confirmation,
        )
        return {
            "query": query,
            "best_match": best_match,
            "alternatives": matches if needs_confirmation else matches[1:],
            "needs_confirmation": needs_confirmation,
            "confirmation_prompt": prompt,
        }

    def _matches_filters(self, exercise: dict, filters: dict) -> bool:
        for field in ("equipment", "category", "level", "mechanic", "force"):
            if filters.get(field) and (exercise.get(field) or "").lower() != filters[field].lower():
                return False
        if filters.get("muscle"):
            muscle = filters["muscle"].lower()
            muscles = exercise.get("primary_muscles", []) + exercise.get("secondary_muscles", [])
            if not any(muscle in m.lower() for m in muscles):
                return False
        return True

    def _match(self, exercise: dict, confidence: float, reason: str) -> dict:
        return {
            "id": exercise["id"],
            "name": exercise["name"],
            "confidence": round(confidence, 2),
            "match_reason": reason,
        }

    def _confidence(self, query: str, exercise: dict, index: int, context: dict) -> float:
        confidence = max(0.55, 0.82 - (index * 0.04))
        equipment = context.get("equipment_available", [])
        if equipment and exercise.get("equipment") in equipment:
            confidence += 0.04
        if exercise["id"] in set(context.get("recent_exercise_ids", [])):
            confidence += 0.05
        if exercise.get("normalized_name", "").startswith(query.lower().strip()):
            confidence += 0.05
        return min(confidence, 0.89)
