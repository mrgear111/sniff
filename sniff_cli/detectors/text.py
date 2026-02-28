import torch
import warnings
from transformers import GPT2LMHeadModel, GPT2Tokenizer

# Suppress warnings from huggingface about unused tensors
warnings.filterwarnings('ignore')

class TextDetector:
    def __init__(self):
        self.tokenizer = None
        self.model = None

    def _load_model(self):
        if self.model is None:
            # Lazy load GPT-2 so it doesn't block startup
            self.tokenizer = GPT2Tokenizer.from_pretrained('gpt2')
            self.model = GPT2LMHeadModel.from_pretrained('gpt2')
            self.model.eval()
            if torch.backends.mps.is_available():
                self.model = self.model.to('mps')
            elif torch.cuda.is_available():
                self.model = self.model.to('cuda')

    def analyze(self, text: str) -> dict:
        words = text.split()
        if not text or len(words) < 2:
            return {"score": 0.0, "reason": "Message too short for analysis"}
        
        # Catch common LLM auto-generated commit patterns
        if text.strip().lower() in ["initial commit", "update readme", "fix bug", "updates"]:
             return {"score": 0.2, "reason": "Generic boilerplate commit message"}
        
        # Load heavy model only on first text analysis
        self._load_model()
        
        encodings = self.tokenizer(text, return_tensors='pt')
        input_ids = encodings.input_ids
        
        if torch.backends.mps.is_available():
            input_ids = input_ids.to('mps')
        elif torch.cuda.is_available():
            input_ids = input_ids.to('cuda')

        seq_len = input_ids.size(1)
        if seq_len < 4:
             return {"score": 0.1, "reason": "Message too short for reliable mathematical perplexity"}

        with torch.no_grad():
            outputs = self.model(input_ids, labels=input_ids)
            loss = outputs.loss
            perplexity = torch.exp(loss).item()

        score = 0.0
        reasons = []

        # GPT-2 perplexity ranges roughly 10-50 for AI text (highly probable tokens), 100+ for human text (bursty)
        if perplexity < 30:
             score = 0.9
             reasons.append(f"Extremely low token perplexity ({perplexity:.1f}), characteristic of LLM generation")
        elif perplexity < 80:
             score = 0.6
             reasons.append(f"Low semantic entropy ({perplexity:.1f})")
        else:
             score = 0.1
             reasons.append(f"High text entropy ({perplexity:.1f}), likely human-written")

        return {
            "score": score,
            "reason": "; ".join(reasons)
        }
