"""AI Categorizer component: AIModel interface, classifiers and AIController (AIR-01, AIR-02)."""
from __future__ import annotations

import json
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass

from django.conf import settings

from .models import CATEGORIES


@dataclass(frozen=True)
class Suggestion:
    """A category recommendation and the model that produced it."""

    category: str
    source: str


class AIModel(ABC):
    """Common interface for all categorizers."""

    name: str = "model"

    @abstractmethod
    def classify(self, text: str, patient_context: str = "") -> Suggestion | None:
        """Return a Suggestion, or None when uncertain. May raise on failure."""


class KeywordFallbackClassifier(AIModel):
    """Rule-based fallback / test substitute. This is NOT an AI model."""

    name = "keyword-fallback (NOT AI)"
    KEYWORDS: dict[str, tuple[str, ...]] = {
        "Respiratory": ("cough", "breath", "wheez", "asthma", "lung", "congestion", "pneumonia"),
        "Digestive": ("stomach", "nausea", "vomit", "diarrhea", "abdominal", "bowel", "digest"),
        "Musculoskeletal": ("back pain", "joint", "fracture", "muscle", "sprain", "knee", "shoulder"),
    }

    def classify(self, text: str, patient_context: str = "") -> Suggestion | None:
        """Pick the category with the most keyword hits; None on zero hits or a tie."""
        lowered = text.lower()
        scores = {c: sum(k in lowered for k in kws) for c, kws in self.KEYWORDS.items()}
        best = max(scores, key=lambda c: scores[c])
        if scores[best] == 0 or list(scores.values()).count(scores[best]) > 1:
            return None
        return Suggestion(best, self.name)


class OllamaClassifier(AIModel):
    """LLM categorizer using an Ollama server."""

    def __init__(self, model: str, url: str, timeout: int = 60) -> None:
        """Store the model name, endpoint URL and request timeout (seconds)."""
        self.model = model
        self.url = url
        self.timeout = timeout
        self.name = f"ollama:{model}"

    def classify(self, text: str, patient_context: str = "") -> Suggestion | None:
        """Ask the model for one of the four categories; None if it answers UNSURE."""
        prompt = (f"Classify this clinical visit note into exactly one of: {', '.join(CATEGORIES)}.\n"
                  f"Patient context: {patient_context}\nNote: {text}\n"
                  "Answer with only the category name, or UNSURE.")
        body = json.dumps({"model": self.model, "prompt": prompt, "stream": False,
                           "think": False}).encode()
        request = urllib.request.Request(self.url, body, {"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            answer = json.load(response)["response"].strip().lower()
        for category in CATEGORIES:
            if category.lower() in answer:
                return Suggestion(category, self.name)
        return None


class AIController:
    """Wraps a model so that failures never propagate (AIR-02)."""

    def __init__(self, model: AIModel) -> None:
        """Use ``model`` for all suggestions."""
        self.model = model

    def suggest(self, text: str, patient_context: str = "") -> tuple[Suggestion | None, str]:
        """Return (suggestion or None, human-readable message). Never raises."""
        try:
            suggestion = self.model.classify(text, patient_context)
        except Exception as exc:  # noqa: BLE001 - AI faults must never block note saving
            return None, f"AI unavailable ({type(exc).__name__}). Note saved without category."
        if suggestion is None:
            return None, "AI is unsure; no recommendation."
        return suggestion, f"Suggested by {suggestion.source}"


def build_controller() -> AIController:
    """Create the AIController configured in Django settings."""
    if settings.AI_BACKEND == "keyword":
        return AIController(KeywordFallbackClassifier())
    return AIController(OllamaClassifier(settings.AI_MODEL, settings.AI_SERVER_URL))
