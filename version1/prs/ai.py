"""AI-assisted categorization of visit notes.

AIModel is the common interface. KeywordFallbackClassifier is NOT an AI model;
it is a temporary rule-based fallback / test substitute. OllamaClassifier calls
a locally running LLM (optional).
"""
import json
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from .models import CATEGORIES


@dataclass
class Suggestion:
    category: str
    confidence: float
    source: str


class AIModel(ABC):
    name = "model"

    @abstractmethod
    def classify(self, text, patient_context=""):
        """Return Suggestion, or None if uncertain. May raise on failure."""


class KeywordFallbackClassifier(AIModel):
    name = "keyword-fallback (NOT AI)"
    KEYWORDS = {
        "Respiratory": ["cough", "breath", "wheez", "asthma", "lung", "congestion", "pneumonia"],
        "Digestive": ["stomach", "nausea", "vomit", "diarrhea", "abdominal", "bowel", "digest"],
        "Musculoskeletal": ["back pain", "joint", "fracture", "muscle", "sprain", "knee", "shoulder"],
    }

    def classify(self, text, patient_context=""):
        lowered = text.lower()
        scores = {c: sum(k in lowered for k in kws) for c, kws in self.KEYWORDS.items()}
        best = max(scores, key=scores.get)
        if scores[best] == 0 or list(scores.values()).count(scores[best]) > 1:
            return None
        return Suggestion(best, min(1.0, 0.5 + 0.2 * scores[best]), self.name)


class OllamaClassifier(AIModel):
    """Local LLM via Ollama (http://localhost:11434)."""
    def __init__(self, model="llama3.2", url="http://localhost:11434/api/generate"):
        self.model = model
        self.url = url
        self.name = f"ollama:{model}"

    def classify(self, text, patient_context=""):
        prompt = (f"Classify this clinical visit note into exactly one of: {', '.join(CATEGORIES)}.\n"
                  f"Patient context: {patient_context}\nNote: {text}\n"
                  "Answer with only the category name, or UNSURE.")
        body = json.dumps({"model": self.model, "prompt": prompt, "stream": False}).encode()
        req = urllib.request.Request(self.url, body, {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            answer = json.load(resp)["response"].strip()
        for cat in CATEGORIES:
            if cat.lower() in answer.lower():
                return Suggestion(cat, 0.8, self.name)
        return None


class AIController:
    """Never raises: failures or uncertainty yield (None, message)."""
    def __init__(self, model: AIModel):
        self.model = model

    def suggest(self, text, patient_context="") -> tuple[Optional[Suggestion], str]:
        try:
            suggestion = self.model.classify(text, patient_context)
        except Exception as exc:
            return None, f"AI unavailable ({exc}). Note saved without category."
        if suggestion is None:
            return None, "AI is unsure; no recommendation."
        return suggestion, f"Suggested by {suggestion.source}"
