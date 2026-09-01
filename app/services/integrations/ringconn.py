from typing import Dict, Any, Tuple

class RingConnService:
    """
    Parses sleep, readiness, and HRV metrics from RingConn Gen 2 Air
    and computes dynamic workload fatigue scaling factors.
    """
    @staticmethod
    def parse_biometrics(payload: Dict[str, Any]) -> Dict[str, Any]:
        sleep_score = float(payload.get("sleep_score") or 75.0)
        readiness_score = float(payload.get("readiness_score") or 80.0)
        hrv = float(payload.get("hrv") or 50.0)

        # Composite score
        composite_recovery = (sleep_score * 0.5) + (readiness_score * 0.5)

        if composite_recovery >= 85:
            recovery_status = "optimal"
            fatigue_scaling_factor = 1.15 # Boost capacity for peak performance
            recommendation = "Peak physical readiness. Ideal for high-cognitive deep work and complex problem solving."
        elif composite_recovery >= 70:
            recovery_status = "moderate"
            fatigue_scaling_factor = 1.0 # Normal standard baseline capacity
            recommendation = "Good baseline recovery. Standard schedule recommended."
        elif composite_recovery >= 50:
            recovery_status = "suboptimal"
            fatigue_scaling_factor = 0.8 # Scale down 20%
            recommendation = "Mild recovery deficit. Schedule lighter focus blocks and ensure regular breaks."
        else:
            recovery_status = "fatigued"
            fatigue_scaling_factor = 0.6 # Scale down 40%
            recommendation = "High fatigue detected. Defending rest blocks and deferring non-essential P3/P4 tasks."

        return {
            "sleep_score": sleep_score,
            "readiness_score": readiness_score,
            "hrv": hrv,
            "recovery_status": recovery_status,
            "fatigue_scaling_factor": fatigue_scaling_factor,
            "recommendation": recommendation
        }
