"""
LLM-Generated Incident Report Module.
Accepts an incident timeline and generates a plain-English, executive summary.
"""

from typing import Optional

class LLMReporter:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        # We can implement an actual API to OpenAI or Google Gemini here.
        # Fallback to local heuristic templates when no net connection or API key

    def generate_summary(self, timeline_text: str, metrics: dict) -> str:
        """Generate narrative from timeline events and peak metrics."""
        
        peak_dens = metrics.get('density', 0) * 100
        peak_speed = metrics.get('speed_multiplier', 1)
        
        # In a real deployed application, this would pass `timeline_text` 
        # as a prompt to a language model to return an executive summary.
        # Here we mock the LLM output if offline.
        
        if peak_dens > 75 or "CRITICAL" in timeline_text:
            return (
                f"INCIDENT SUMMARY:\n"
                f"The system detected a severe safety hazard driven by sudden compression and high density. "
                f"Peak crowd density reached {peak_dens:.1f}%, while crowd speed spiked {peak_speed:.1f}x above baseline. "
                f"The alert sequence escalated to CRITICAL as directional entropy collapsed, signaling a potential stampede. "
                f"Immediate security response procedures were engaged."
            )
        elif peak_dens > 50 or "DANGER" in timeline_text:
            return (
                f"INCIDENT SUMMARY:\n"
                f"A danger-level crowd density event was logged. Density climbed to {peak_dens:.1f}%, "
                f"reducing inter-person area and increasing systemic risk. "
                f"No stampede signature was finalized, but conditions were highly congested."
            )
        elif peak_dens > 30 or "WARNING" in timeline_text:
            return (
                f"INCIDENT SUMMARY:\n"
                f"Elevated traffic was observed, pushing density to {peak_dens:.1f}%. "
                f"Conditions returned to normal operational boundaries."
            )
        else:
             return "INCIDENT SUMMARY:\nSession remained within normal safe operating thresholds for the entirety of the timeline."
