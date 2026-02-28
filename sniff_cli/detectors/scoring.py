class ScoreAggregator:
    """
    5-Engine Score Aggregator
    ─────────────────────────
    Engines and weights:
      text       (0.10) — commit message heuristics + GPT-2 perplexity
      code       (0.50) — AST entropy, React/async patterns, comment density
      structural (0.15) — line length coefficient of variation, blank-line regularity
      similarity (0.15) — SimHash near-duplicate detection across commits
      semantic   (0.10) — sentence-transformer message ↔ code cosine similarity
      baseline   (0.15) — per-author style deviation (z-score from historical mean)
    
    Velocity and burst are additive bonuses applied after weighted sum.
    """

    def __init__(self):
        self.weights = {
            "text":       0.10,
            "code":       0.50,
            "structural": 0.15,
            "similarity": 0.15,
            "semantic":   0.10,
            "baseline":   0.15,
        }

    def compute(
        self,
        text_res: dict,
        code_res: dict,
        velocity_lpm: float = 0.0,
        burst_score: float = 0.0,
        structural_res: dict = None,
        similarity_res: dict = None,
        semantic_res: dict = None,
        baseline_res: dict = None,
    ) -> dict:
        structural_res = structural_res or {"score": 0.0, "reason": ""}
        similarity_res = similarity_res or {"score": 0.0, "reason": ""}
        semantic_res   = semantic_res   or {"score": 0.0, "reason": ""}
        baseline_res   = baseline_res   or {"score": 0.0, "reason": ""}

        # Weighted base score from all 6 signal engines
        final_score = (
            text_res.get("score", 0.0)       * self.weights["text"] +
            code_res.get("score", 0.0)       * self.weights["code"] +
            structural_res.get("score", 0.0) * self.weights["structural"] +
            similarity_res.get("score", 0.0) * self.weights["similarity"] +
            semantic_res.get("score", 0.0)   * self.weights["semantic"] +
            baseline_res.get("score", 0.0)   * self.weights["baseline"]
        )

        # Velocity bonus
        v_score = 0.0
        v_reason = None
        if velocity_lpm > 50:
            v_score = 1.0
            v_reason = f"Impossible human typing velocity ({velocity_lpm:.0f} Lines/Minute)"
        elif velocity_lpm > 20:
            v_score = 0.6
            v_reason = f"Abnormally high commit velocity ({velocity_lpm:.0f} Lines/Minute)"
        final_score += v_score * 0.15  # velocity is an additive bonus

        # Burst bonus
        if burst_score > 0:
            final_score += 0.1
        
        # Amplification: any single strong signal (>0.5) pushes score up
        all_scores = [
            text_res.get("score", 0.0),
            code_res.get("score", 0.0),
            structural_res.get("score", 0.0),
            similarity_res.get("score", 0.0),
            semantic_res.get("score", 0.0),
            baseline_res.get("score", 0.0),
        ]
        if any(s >= 0.5 for s in all_scores):
            final_score += 0.20  # boosted jump
        
        # If multiple engines suspect AI even slightly, drastically raise confidence
        suspect_engines = sum(1 for s in all_scores if s >= 0.3)
        if suspect_engines >= 2:
            final_score += 0.25
        elif suspect_engines == 1:
            final_score += 0.10

        final_score = min(final_score, 1.0)

        # Collect reasons from all engines (filter out noise/empty reasons)
        reasons = []
        _noise = {"", "No strong text signals", "Organic code complexity",
                  "Organic structural variation", "No near-duplicate commits found",
                  "Natural human-style message-code divergence",
                  "Style consistent with author baseline", "No baseline available",
                  "Insufficient baseline history", "No strong similarity signals",
                  "Too short for semantic analysis", "Missing message or diff",
                  "Diff too small for structural analysis", "No strong AI signals detected"}

        for res in [text_res, code_res, structural_res, similarity_res, semantic_res, baseline_res]:
            reason = res.get("reason", "")
            if reason and reason not in _noise and res.get("score", 0.0) > 0.0:
                for part in reason.split("; "):
                    if part.strip() and part.strip() not in _noise:
                        reasons.append(part.strip())
        if v_reason:
            reasons.append(v_reason)
        if burst_score > 0:
            reasons.append("Commit-burst: rapid large-diff sequence within 10 min window")

        if not reasons:
            reasons = ["No strong AI signals detected"]

        # Band classification (Lowered thresholds for AI verdict)
        if final_score < 0.20:
            band = "Likely Human"
        elif final_score < 0.50:
            band = "Mixed / Uncertain"
        else:
            band = "Likely AI-assisted"

        return {
            "score": round(final_score, 2),
            "band": band,
            "reasons": reasons,
        }
