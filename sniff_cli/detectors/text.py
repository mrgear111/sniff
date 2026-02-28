import re
import math

# AI-style conventional commit format
_CONVENTIONAL_PREFIX = re.compile(
    r"^(feat|fix|chore|refactor|style|docs|test|build|ci|perf|revert)(\([a-z\-]+\))?!?:\s",
    re.IGNORECASE
)

# AI-style template phrases (only suspicious in long messages)
_TEMPLATE_PHRASES = [
    "this commit introduces",
    "the following changes were made",
    "this pr adds",
    "this pull request",
    "as part of this change",
    "this change implements",
    "to ensure",
    "in order to",
    "the purpose of this",
]

# Known AI boilerplate variable/function name prefixes
_AI_IDENTIFIER_PREFIXES = ["handle", "on", "get", "set", "fetch", "update", "create", "delete", "parse", "format"]

class TextDetector:
    def __init__(self):
        self.tokenizer = None
        self.model = None

    def _load_model(self):
        import torch
        import warnings
        from transformers import GPT2LMHeadModel, GPT2Tokenizer
        warnings.filterwarnings('ignore')
        if self.model is None:
            self.tokenizer = GPT2Tokenizer.from_pretrained('gpt2')
            self.model = GPT2LMHeadModel.from_pretrained('gpt2')
            self.model.eval()
            if torch.backends.mps.is_available():
                self.model = self.model.to('mps')
            elif torch.cuda.is_available():
                self.model = self.model.to('cuda')

    def _perplexity(self, text: str) -> float:
        """Returns GPT-2 perplexity for longer messages only."""
        try:
            import torch
            self._load_model()
            enc = self.tokenizer(text, return_tensors='pt', max_length=512, truncation=True)
            ids = enc.input_ids
            if torch.backends.mps.is_available():
                ids = ids.to('mps')
            elif torch.cuda.is_available():
                ids = ids.to('cuda')
            with torch.no_grad():
                loss = self.model(ids, labels=ids).loss
                return torch.exp(loss).item()
        except Exception:
            return 999.0

    def _typo_index(self, text: str) -> float:
        """Rough measure of 'deliberate messiness' — human text has typos, contractions, slang."""
        informal_markers = ["dont", "cant", "wont", "gonna", "lol", "tbh", "imo", "nvm", "btw",
                            "!!!", "???", "hmm", "oops", "wtf", "asap"]
        words = text.lower().split()
        hits = sum(1 for w in words if w in informal_markers)
        # Also count lowercase sentence starts as human signal
        if text and text[0].islower():
            hits += 1
        return hits

    def analyze(self, text: str, diff_lines: int = 0) -> dict:
        """
        Analyze a commit message for AI-likeness.
        diff_lines: number of lines changed in the associated diff for cross-signal analysis.
        """
        if not text or len(text.strip()) < 2:
            return {"score": 0.0, "reason": "Empty commit message"}

        score = 0.0
        reasons = []
        words = text.strip().split()
        word_count = len(words)
        msg_lower = text.strip().lower()

        # ─── 1. Conventional commit format (strong AI signal) ───────────────
        if _CONVENTIONAL_PREFIX.match(text.strip()):
            score += 0.5
            reasons.append("Conventional commit format (CI tooling or AI assistant)")

        # ─── 2. Capitalization + period perfection ───────────────────────────
        # Only flag if title-cased AND ends with period AND no human traces
        title_line = text.strip().split('\n')[0]
        is_perfect = (title_line[0].isupper() and title_line.endswith('.') and
                      self._typo_index(text) == 0)
        if is_perfect and word_count > 4:
            score += 0.25
            reasons.append("Overly perfect grammar with zero informal markers")

        # ─── 3. Terse boilerplate (1-2 words) ────────────────────────────────
        if word_count <= 2:
            score += 0.3
            reasons.append(f"Extremely terse message ({word_count} word) — AI boilerplate style")

        # ─── 4. Template phrases (only suspicious with large diffs) ──────────
        if diff_lines > 50 or word_count > 20:
            for phrase in _TEMPLATE_PHRASES:
                if phrase in msg_lower:
                    score += 0.4
                    reasons.append(f"AI template phrasing detected: '{phrase}'")
                    break

        # ─── 5. Message-to-diff ratio (cross-signal) ─────────────────────────
        if diff_lines > 0:
            # Long message, tiny diff → suspicious (ChatGPT-style over-explanation)
            if word_count > 50 and diff_lines < 10:
                score += 0.35
                reasons.append(f"Long commit message ({word_count} words) for tiny diff ({diff_lines} lines)")
            # Tiny message, huge diff → "lazy captioning" AI pattern
            if word_count < 5 and diff_lines > 100:
                score += 0.3
                reasons.append(f"Tiny message ({word_count} words) for large diff ({diff_lines} lines) — AI lazy captioning")

        # ─── 6. Bulleted / markdown structure in messages ────────────────────
        if text.count('\n- ') >= 2 or text.count('\n* ') >= 2:
            score += 0.2
            reasons.append("Markdown-style bullet list in commit message (AI formatting)")

        # ─── 7. GPT-2 perplexity (only for long messages, 8+ words) ─────────
        if word_count >= 8:
            perp = self._perplexity(text)
            if perp < 50:
                score += 0.7
                reasons.append(f"Very low token perplexity ({perp:.1f}) — LLM-generated phrasing")
            elif perp < 120:
                score += 0.35
                reasons.append(f"Low-medium perplexity ({perp:.1f}) — possibly AI assisted")

        return {
            "score": min(score, 1.0),
            "reason": "; ".join(reasons) if reasons else "No strong text signals"
        }
