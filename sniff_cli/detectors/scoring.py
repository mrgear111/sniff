class ScoreAggregator:
    def __init__(self, text_weight=0.4, code_weight=0.4, velocity_weight=0.2):
        self.text_weight = text_weight
        self.code_weight = code_weight
        self.velocity_weight = velocity_weight

    def compute(self, text_res: dict, code_res: dict, velocity_lpm: float = 0.0) -> dict:
        t_score = text_res.get("score", 0.0)
        c_score = code_res.get("score", 0.0)
        
        # Velocity scoring: anything above 20 LPM is highly suspicious
        v_score = 0.0
        v_reason = None
        if velocity_lpm > 50:
            v_score = 1.0
            v_reason = f"Impossible human typing velocity ({velocity_lpm:.0f} Lines/Minute)"
        elif velocity_lpm > 20:
            v_score = 0.6
            v_reason = f"Abnormally high commit velocity ({velocity_lpm:.0f} Lines/Minute)"

        # Base average
        final_score = (t_score * self.text_weight) + (c_score * self.code_weight) + (v_score * self.velocity_weight)

        # Amplification (Make it extremely sensitive for demo purposes)
        if t_score >= 0.4 or c_score >= 0.4:
            final_score += 0.3
        if v_score >= 0.5:
            # If they type impossibly fast, it's almost certainly AI
            final_score += 0.4

        final_score = min(final_score, 1.0)

        reasons = []
        if text_res.get("score", 0.0) > 0.0 and text_res.get("reason"):
            reasons.extend(text_res["reason"].split("; "))
        if code_res.get("score", 0.0) > 0.0 and code_res.get("reason"):
            reasons.extend(code_res["reason"].split("; "))
        if v_reason:
            reasons.append(v_reason)

        if final_score < 0.3:
            band = "Likely Human"
        elif final_score < 0.7:
            band = "Mixed / Uncertain"
        else:
            band = "Likely AI-assisted"

        return {
            "score": final_score,
            "band": band,
            "reasons": reasons if reasons else ["Organic changes"]
        }
