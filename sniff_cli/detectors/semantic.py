"""
Semantic Embedding Similarity Engine
──────────────────────────────────────
Uses sentence-transformers (MiniLM, runs fully offline, ~80MB) to embed
the commit message and the first 512 chars of the code diff, then measures
their cosine similarity.

The Core Insight:
  When a developer writes a commit message, they write from *intent* — what 
  they were *trying* to do. The code might look very different.
  
  When an AI writes a commit message, it summarizes the code it just produced — 
  resulting in an abnormally tight semantic match between message and diff.
  
  High cosine similarity (message ↔ diff) = AI-made the commit message by 
  reading its own output.
"""

import math
import re

_model = None
_model_name = "all-MiniLM-L6-v2"  # ~80MB, runs offline, excellent performance


def _load_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(_model_name)
        except ImportError:
            _model = None  # Graceful fallback if not installed
    return _model


def _cosine_similarity(a: list, b: list) -> float:
    """Pure Python cosine similarity between two embedding vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _clean_diff_for_embedding(diff: str) -> str:
    """Extract meaningful code tokens, stripping punctuation noise."""
    # Remove comments
    diff = re.sub(r'//.*?\n', '\n', diff)
    diff = re.sub(r'#.*?\n', '\n', diff)
    # Get identifiers and keywords
    tokens = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]{1,}\b', diff)
    return ' '.join(tokens[:200])  # Cap at 200 tokens to keep it fast


class SemanticDetector:
    """
    Measures semantic coherence between commit message and code diff.
    High coherence = AI wrote the message by summarizing its code output.
    """
    
    def __init__(self):
        self._available = None  # Will be set on first call

    def _check_available(self) -> bool:
        if self._available is None:
            self._available = _load_model() is not None
        return self._available

    def analyze(self, message: str, diff: str) -> dict:
        if not message or not diff:
            return {"score": 0.0, "reason": "Missing message or diff"}
        
        # Need reasonable content on both sides
        msg_words = message.strip().split()
        diff_tokens = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]{1,}\b', diff)
        
        if len(msg_words) < 4 or len(diff_tokens) < 8:
            return {"score": 0.0, "reason": "Too short for semantic analysis"}
        
        if not self._check_available():
            return {"score": 0.0, "reason": "Semantic model not installed (pip install sentence-transformers)"}

        try:
            model = _load_model()
            clean_diff = _clean_diff_for_embedding(diff)
            
            # Get embeddings
            embeddings = model.encode([message.strip(), clean_diff])
            similarity = _cosine_similarity(embeddings[0].tolist(), embeddings[1].tolist())

            score = 0.0
            reasons = []

            # Lowered thresholds: AI often achieves ~0.5-0.7
            if similarity > 0.60:
                score = 0.8
                reasons.append(f"Very high semantic coherence (message ↔ code: {similarity:.2f}) — AI self-summarization pattern")
            elif similarity > 0.45:
                score = 0.50
                reasons.append(f"High message-code semantic alignment ({similarity:.2f}) — possible AI narration")
            elif similarity > 0.35:
                score = 0.25
                reasons.append(f"Moderate semantic alignment ({similarity:.2f})")
            # Low similarity = human pattern (commits from intent, not from code)

            return {
                "score": min(score, 1.0),
                "reason": "; ".join(reasons) if reasons else "Natural human-style message-code divergence"
            }
        except Exception as e:
            return {"score": 0.0, "reason": f"Semantic analysis failed: {str(e)[:50]}"}
