"""Stub implementation of Translator."""


class Translator:
    """Identity translator: returns English text as both EN and ES.

    Real implementation in cooksense-core calls Claude for actual translation.
    """

    def __init__(self) -> None:
        pass

    def translate_batch(self, recipes: list[dict]) -> dict[str, dict]:
        return {
            r["id"]: {
                "title_es": r["title"],
                "ingredients_es": list(r["ingredients"]),
                "instructions_es": list(r["instructions"]),
            }
            for r in recipes
        }
