"""
Main Pipeline Orchestrator.
Ties together: video capture → detection → tracking → density →
movement → alerts → prediction → HUD → web server.
"""

import cv2
import numpy as np
import threading
import time
import argparse
import os
import sys

# Check for required dependencies
def check_dependencies():
    missing = []
    try:
        import cv2
    except ImportError:
        missing.append('opencv-python')
    try:
        import numpy
    except ImportError:
        missing.append('numpy')
    try:
        import scipy
    except ImportError:
        missing.append('scipy')
    try:
        import fastapi
    except ImportError:
        missing.append('fastapi')
    
    if missing:
        print("\n" + "="*60)
        print("  ERROR: Missing Required Dependencies")
        print("="*60)
        print(f"\nThe following packages are not installed: {', '.join(missing)}")
        print("\nPlease run the setup script first:")
        print("  ./setup.sh")
        print("\nOr install manually:")
        print(f"  pip install {' '.join(missing)}")
        print("="*60 + "\n")
        sys.exit(1)

check_dependencies()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config.settings import (
    DEFAULT_SOURCE, FRAME_WIDTH, FRAME_HEIGHT, TARGET_FPS,
    SIMULATION_MODE, API_HOST, API_PORT
)
from src.detector import PersonDetector
from src.tracker import MultiTracker
from src.density import DensityAnalyzer
from src.movement import MovementAnalyzer
from src.alerts import AlertEngine
from src.predictor import LSTMRiskPredictor
from src.lost_child import LostChildDetector
from src.social_distance import SocialDistanceMonitor
from src.simulator import CrowdSimulator
from src.logger import EventLogger
from src.notifications import NotificationPipeline
from src.hud import HUDRenderer
from src.acoustic import AcousticDetector
from src.voice_alert import VoiceAlertSystem
from src.explainability import ExplainabilityEngine
from src.digital_twin import DigitalTwin
from src.weather import WeatherMonitor
from src.zone_manager import ZoneManager
from src.behavior_classifier import BehaviorClassifier
from src.recorder import IncidentRecorder
from src.restricted_zones import RestrictedZoneEnforcer
from src.cluster_analysis import ClusterAnalyzer
from web.server import update_state, get_state, start_server


class CrowdSafetyPipeline:
    def __init__(self, source=None, sim_mode: bool = False,
                 show_window: bool = True, headless: bool = False):
        self.source = source if source is not None else DEFAULT_SOURCE
        self.sim_mode = sim_mode or SIMULATION_MODE
        self.show_window = show_window and not headless
        self.headless = headless
        self.running = False
        self.paused = False

        # Core modules
        self.detector    = PersonDetector()
        self.tracker     = MultiTracker()
        self.density     = None      # init after frame size known
        self.movement    = MovementAnalyzer()
        self.alert_eng   = AlertEngine()
        self.predictor   = LSTMRiskPredictor()
        self.lost_child  = LostChildDetector()
        self.social_dist = SocialDistanceMonitor()
        self.logger      = EventLogger()
        self.notifier    = NotificationPipeline()
        self.simulator   = None
        self.hud         = None

        # Advanced Modules
        self.acoustic    = AcousticDetector()
        self.voice       = VoiceAlertSystem()
        self.explainer   = ExplainabilityEngine()
        self.digital_twin = DigitalTwin()
        self.weather     = WeatherMonitor()
        self.behavior_cls = BehaviorClassifier()
        self.recorder    = IncidentRecorder(fps=TARGET_FPS)
        self.cluster_analyzer = ClusterAnalyzer(cluster_radius=40)
        self.zone_mgr    = ZoneManager(FRAME_WIDTH, FRAME_HEIGHT)
        self.zone_enforcer = RestrictedZoneEnforcer(self.zone_mgr)
        
        # We start acoustic on run() starts

        # Register notification callback
        self.alert_eng.register_callback(self._on_alert)
        self.alert_eng.register_callback(self.notifier.send_all)
        self.alert_eng.register_callback(lambda e: self.voice.speak(e.level))
        self.alert_eng.register_callback(lambda e: self.recorder.trigger(e.level))

        # FPS tracking
        self._frame_count = 0
        self._fps = 0.0
        self._fps_ts = time.time()

        # Previous centers for motion heatmap
        self._prev_centers = {}

        print("=" * 60)
        print("  CrowdSafe AI — Intelligent Crowd Safety System")
        print(f"  Mode: {'SIMULATION' if self.sim_mode else 'LIVE'}")
        print(f"  Source: {self.source}")
        print(f"  Dashboard: http://{API_HOST}:{API_PORT}")
        print("=" * 60)

    # ──────────────────────────────────────────────────────────────────────
    # Alert callback
    # ──────────────────────────────────────────────────────────────────────

    def _on_alert(self, event):
        self.logger.log(
            event_type="ALERT",
            level=event.level,
            message=event.message,
            data=event.metrics
        )
        print(f"\n[ALERT] {event.level}: {event.message}\n")

    # ──────────────────────────────────────────────────────────────────────
    # Main loop
    # ──────────────────────────────────────────────────────────────────────

    def run(self):
        self.running = True
        self.acoustic.start()
        update_state(running=True)

        cap = None
        if not self.sim_mode:
            cap = cv2.VideoCapture(self.source)
            if not cap.isOpened():
                print(f"[Pipeline] Cannot open source: {self.source}. Switching to simulation.")
                self.sim_mode = True

        if self.sim_mode:
            self.simulator = CrowdSimulator(FRAME_WIDTH, FRAME_HEIGHT)

        # Determine frame size
        if cap and cap.isOpened():
            W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or FRAME_WIDTH
            H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or FRAME_HEIGHT
        else:
            W, H = FRAME_WIDTH, FRAME_HEIGHT

        self.density = DensityAnalyzer(W, H)
        self.hud = HUDRenderer(W, H)

        frame_interval = 1.0 / TARGET_FPS

        try:
            while self.running:
                t_start = time.time()

                # ── Get frame ──────────────────────────────────
                if self.sim_mode:
                    frame = self.simulator.render_blank_frame()
                    # Check for control commands from web
                    state = get_state()
                    sim_cmd = state.pop("sim_cmd", None)
                    if sim_cmd:
                        self.simulator.set_mode(sim_cmd)
                    raw_detections = self.simulator.step()
                else:
                    ret, frame = cap.read()
                    if not ret:
                        print("[Pipeline] End of video or stream lost.")
                        break
                    frame = cv2.resize(frame, (W, H))
                    raw_detections = self.detector.detect(frame)

                # ── Track ──────────────────────────────────────
                tracked = self.tracker.update(raw_detections)

                # ── Density ────────────────────────────────────
                density = self.density.compute_global_density(tracked)
                density_level = self.density.get_density_level(density)
                zone_grid = self.density.compute_zone_density(tracked)
                count = len(tracked)
                occupancy_pct = self.density.get_occupancy_pct(count)
                self.density.update_counts(count, density)

                # ── Heatmap ────────────────────────────────────
                heatmap = self.density.update_heatmap(tracked)
                curr_centers = {d.track_id: d.center for d in tracked}
                motion_hm = self.density.update_motion_heatmap(self._prev_centers, curr_centers)
                self._prev_centers = curr_centers

                # ── Movement ───────────────────────────────────
                speeds = self.movement.update(tracked)
                avg_speed = self.movement.get_avg_speed(speeds)
                self.movement.update_baseline(avg_speed)
                speed_mult = self.movement.get_speed_multiplier(avg_speed)
                speed_level = self.movement.detect_speed_spike(avg_speed)
                direction_entropy = self.movement.compute_direction_entropy(tracked)
                compressed, avg_dist, pressure_wave = self.movement.detect_compression(tracked)
                
                if pressure_wave:
                    self.logger.log("PRESSURE_WAVE", "CRITICAL", "A dangerous crowd compression wave was detected propagating through the tracked area.")
                    
                # Compute flow vectors once with scale=4 for both classifier and rendering
                flow_vectors = self.movement.compute_flow_vectors(tracked, scale=4)
                behaviors = self.movement.detect_behaviors(tracked, avg_speed)

                anomalies = self.behavior_cls.assess_anomalies(tracked, speeds, flow_vectors)
                dt_future = self.digital_twin.update(tracked, speeds, flow_vectors)

                # ── Social distance ────────────────────────────
                sd_violations = self.social_dist.compute_violations(tracked)

                # ── Lost child ─────────────────────────────────
                lost_children = self.lost_child.update(tracked)
                if lost_children:
                    self.logger.log("LOST_CHILD", "WARNING",
                                    f"Possible lost child(ren) detected: {len(lost_children)}",
                                    {"count": len(lost_children)})

                # ── Restricted Zones ───────────────────────────
                zone_intrusions = self.zone_enforcer.assess_intrusions(tracked)
                if zone_intrusions:
                    for z_name, ids in zone_intrusions.items():
                        self.logger.log("ZONE_VIOLATION", "WARNING", 
                                        f"Restricted zone intrusion in {z_name}", 
                                        {"zone": z_name, "count": len(ids)})

                # ── Group & Cluster Analysis ───────────────────
                cluster_stats = self.cluster_analyzer.analyze(tracked)
                if cluster_stats["dense_clusters"] > 0:
                    self.logger.log("DENSE_CLUSTER", "WARNING", f"Dangerous cluster compression developing: {cluster_stats['dense_clusters']} dense clusters detected")

                # ── Alert evaluation ───────────────────────────
                weather_data = self.weather.get_weather_data()
                ac_status = self.acoustic.get_status()
                
                metrics_dict = {
                    "count": count,
                    "density": density,
                    "density_level": density_level,
                    "speed_level": speed_level,
                    "speed_multiplier": speed_mult,
                    "avg_speed": avg_speed,
                    "compressed": compressed,
                    "pressure_wave": pressure_wave,
                    "avg_dist": avg_dist,
                    "direction_entropy": direction_entropy,
                    "occupancy_pct": occupancy_pct,
                    "lost_child": len(lost_children) > 0,
                    "social_violations": self.social_dist.current_violations,
                    "anomaly_score": anomalies["score"],
                    "acoustic_panic": ac_status["is_panic"],
                    "acoustic_db": ac_status["db_level"],
                    "weather_risk_mult": weather_data["risk_mult"],
                    "dense_clusters": cluster_stats["dense_clusters"],
                    "zone_grid": [[{"count":z["count"],"density":z["density"],"risk":z["risk"]}
                                   for z in row] for row in zone_grid],
                }
                alert_level = self.alert_eng.evaluate(metrics_dict)
                risk_score = min(self.alert_eng.risk_score * weather_data["risk_mult"], 100.0)
                
                explanation = self.explainer.explain(metrics_dict, risk_score, alert_level)
                metrics_dict["explanation"] = explanation

                # ── Prediction ─────────────────────────────────
                self.predictor.update(density, avg_speed, risk_score, count, direction_entropy)
                predictions = self.predictor.predict()
                trend = self.predictor.get_trend()
                metrics_dict["trend"] = trend

                # ── Logging ────────────────────────────────────
                self.logger.log_metric(count, density, avg_speed, risk_score, alert_level)

                # ── FPS ────────────────────────────────────────
                self._frame_count += 1
                now = time.time()
                if now - self._fps_ts >= 1.0:
                    self._fps = self._frame_count / (now - self._fps_ts)
                    self._frame_count = 0
                    self._fps_ts = now

                # ── Render ─────────────────────────────────────
                display = frame.copy()

                # Heatmap overlay
                display = self.density.render_heatmap_overlay(display, heatmap, alpha=0.35)

                # Zone grid
                display = self.density.draw_zone_grid(display, zone_grid)

                # Flow arrows (reuse computed flow_vectors)
                display = self.movement.draw_flow_arrows(display, flow_vectors)

                # Social distance lines
                display = self.social_dist.draw_violations(display, sd_violations)

                # Trajectories
                display = self.hud.draw_trajectories(display, self.tracker.get_trajectories())

                # Bounding boxes
                display = self.detector.draw_detections(display, tracked)

                # Behavior labels
                for det in tracked:
                    blist = behaviors.get(det.track_id, [])
                    if blist:
                        label = ",".join(blist[:2])
                        cv2.putText(display, label, (det.x1, det.y2 + 14),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 200, 0), 1)

                # Lost child overlay
                display = self.hud.draw_lost_child_alerts(display, lost_children)

                # HUD panels
                alert_msg = (self.alert_eng.alert_feed[0].message
                             if self.alert_eng.alert_feed else "")
                display = self.hud.draw_status_bar(
                    display, alert_level, count, density, risk_score, self._fps)
                display = self.hud.draw_side_panel(
                    display, metrics_dict, self.alert_eng.get_feed(), predictions)
                display = self.hud.draw_risk_gauge(display, risk_score)
                display = self.hud.draw_alert_banner(display, alert_level, alert_msg)
                display = self.hud.draw_system_health(display, self._fps)

                self.recorder.update(frame.copy())
                
                # ── Push to web server ──────────────────────────
                update_state(
                    frame=display,
                    metrics=metrics_dict,
                    alert_level=alert_level,
                    risk_score=risk_score,
                    predictions=predictions,
                    alert_feed=self.alert_eng.get_feed(),
                    timeline=self.logger.generate_incident_timeline(),
                    running=True,
                )

                # ── Show local window ───────────────────────────
                if self.show_window:
                    cv2.imshow("CrowdSafe AI", display)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        break
                    elif key == ord('h'):
                        self.show_window = False   # hide window
                    elif key == ord('s'):
                        self.sim_mode = not self.sim_mode
                    elif key == ord('1') and self.sim_mode:
                        self.simulator.set_mode("normal")
                    elif key == ord('2') and self.sim_mode:
                        self.simulator.set_mode("building")
                    elif key == ord('3') and self.sim_mode:
                        self.simulator.set_mode("dense")
                    elif key == ord('4') and self.sim_mode:
                        self.simulator.set_mode("panic")

                # ── Frame rate cap ──────────────────────────────
                elapsed = time.time() - t_start
                sleep_t = max(0, frame_interval - elapsed)
                if sleep_t > 0:
                    time.sleep(sleep_t)

        except KeyboardInterrupt:
            print("\n[Pipeline] Interrupted by user.")
        finally:
            self.running = False
            self.acoustic.stop()
            self.voice.stop()
            self.recorder.close()
            update_state(running=False)
            if cap:
                cap.release()
            if self.show_window:
                cv2.destroyAllWindows()
            # Generate final report
            timeline = self.logger.generate_incident_timeline()
            print("\n" + timeline)
            self.logger.close()
            print("[Pipeline] Shutdown complete.")


# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="CrowdSafe AI — Intelligent Crowd Safety & Stampede Prevention"
    )
    parser.add_argument("--source", default=None,
                        help="Camera index (0,1,...), video file path, or RTSP URL")
    parser.add_argument("--sim", action="store_true",
                        help="Run in simulation mode (no camera required)")
    parser.add_argument("--no-window", action="store_true",
                        help="Run headless (no OpenCV window — web dashboard only)")
    parser.add_argument("--port", type=int, default=API_PORT,
                        help=f"Web dashboard port (default {API_PORT})")
    args = parser.parse_args()

    source = args.source
    if source is not None:
        try:
            source = int(source)
        except ValueError:
            pass   # keep as string (file path or RTSP URL)

    pipeline = CrowdSafetyPipeline(
        source=source,
        sim_mode=args.sim,
        show_window=not args.no_window,
        headless=args.no_window
    )

    # Start web server in background thread
    server_thread = threading.Thread(
        target=start_server,
        kwargs={"host": API_HOST, "port": args.port},
        daemon=True
    )
    server_thread.start()
    print(f"[Server] Dashboard live at http://localhost:{args.port}")
    time.sleep(1.0)   # let server start

    # Run pipeline on main thread
    pipeline.run()


if __name__ == "__main__":
    main()
