"""
Explainability Engine.
Takes raw metrics and outputs a plain-English, human-readable
explanation of why the current risk score and alert level are what they are.
Also computes contribution percentages for the HUD.
"""

from typing import Dict, Any

class ExplainabilityEngine:
    def explain(self, metrics: Dict[str, Any], risk_score: float, alert_level: str) -> dict:
        """
        Returns a dictionary with an explanation string and contribution breakdown.
        """
        reasons = []
        contributions = {}
        total = 0.0

        density = metrics.get("density", 0.0)
        speed_mult = metrics.get("speed_multiplier", 1.0)
        compressed = metrics.get("compressed", False)
        entropy = metrics.get("direction_entropy", 1.0)
        lost_child = metrics.get("lost_child", False)

        # Baseline contribution
        c_base = 10.0
        contributions["baseline"] = c_base
        total += c_base

        if density > 0.3:
            reasons.append(f"Density elevated ({density*100:.0f}%)")
            c_dens = density * 40.0
            contributions["density"] = c_dens
            total += c_dens

        if speed_mult > 1.3:
            reasons.append(f"Speed surge ({speed_mult:.1f}x baseline)")
            c_spd = (speed_mult - 1.0) * 30.0
            contributions["speed"] = c_spd
            total += c_spd

        if compressed:
            dist = metrics.get("avg_dist", 0)
            reasons.append(f"Compression detected (avg dist {dist:.1f}px)")
            c_comp = 25.0
            contributions["compression"] = c_comp
            total += c_comp
            
        if metrics.get("pressure_wave", False):
            reasons.append("Pressure Wave detected in crowd density")
            c_wv = 40.0
            contributions["pressure_wave"] = c_wv
            total += c_wv
            
        if entropy < 0.6:
            reasons.append(f"Direction alignment ({(1-entropy)*100:.0f}%)")
            c_ent = (1 - entropy) * 20.0
            contributions["direction"] = c_ent
            total += c_ent

        if lost_child:
            reasons.append("Possible lost child")
            c_lc = 15.0
            contributions["lost_child"] = c_lc
            total += c_lc
            
        dense_clusters = metrics.get("dense_clusters", 0)
        if dense_clusters > 0:
            reasons.append(f"Tight merging clusters ({dense_clusters})")
            c_clust = dense_clusters * 25.0
            contributions["clusters"] = c_clust
            total += c_clust

        # Normalize contributions
        if total > 0:
            contributions = {k: (v / total) * 100 for k, v in contributions.items()}

        summary = "Normal monitoring state."
        if reasons:
            summary = "Alert driven by: " + " + ".join(reasons)

        if alert_level == "SAFE" and not reasons:
            summary = "All metrics within safe operational limits."

        return {
            "summary": summary,
            "reasons": reasons,
            "contributions": contributions,
            "risk_score": risk_score,
            "alert_level": alert_level
        }
