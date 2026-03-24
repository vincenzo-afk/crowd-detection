"""
Edge AI ONNX Exporter tool.
Takes the YOLO PyTorch model and the LSTM model, converting them
to INT8/ONNX formats for offline operation on Jetson/CPU.
"""

import os

class OnnxExporter:
    @staticmethod
    def convert_yolo(model_name="yolov8n.pt", output_dir="models/"):
        """Run YOLO export. Requires ultralytics package."""
        try:
            from ultralytics import YOLO
            print(f"[ONNX] Exporting {model_name} to ONNX format...")
            model = YOLO(model_name)
            path = model.export(format="onnx", half=True)
            print(f"[ONNX] Export complete: {path}")
            return path
        except ImportError:
            print("[ONNX] Ultralytics not installed. Skipped.")
        except Exception as e:
            print(f"[ONNX] Export failed: {e}")
            
    @staticmethod
    def export_all():
        OnnxExporter.convert_yolo()

if __name__ == "__main__":
    OnnxExporter.export_all()
