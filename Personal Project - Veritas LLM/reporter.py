# Import standard library modules for JSON serialization, file path manipulation, timestamps, and type hinting
import json
import os
from datetime import datetime
from typing import List, Dict, Any

# Generates structured security audit reports from evaluation runs
class SecurityReporter:
    
    # Initializes the security reporter and ensures the target output directory exists
    def __init__(self, output_dir: str = "reports"):

        # Set output directory and create it if it doesn't already exist
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    # Exports evaluation results, latency metrics, and summary metadata into a timestamped JSON file
    def export_json(self, results: List[Dict[str, Any]], score: float, model_name: str) -> str:
        
        # Generate a timestamp string and construct the output filename and path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"veritas_audit_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)

        # Calculate average probe latency in seconds, defaulting to 0.0 if empty
        latencies = [r["latency"] for r in results if "latency" in r]
        avg_latency = round(sum(latencies) / len(latencies), 3) if latencies else 0.0

        # Construct structured summary metadata alongside evaluation details
        report_data = {
            "metadata": {
                "framework": "Veritas-LLM v1.0",
                "target_model": model_name,
                "timestamp": datetime.now().isoformat(),
                "robustness_score": round(score, 2),
                "average_latency_sec": avg_latency,
                "total_probes": len(results),
                "passed": sum(1 for r in results if r["passed"]),
                "failed": sum(1 for r in results if not r["passed"])
            },
            "evaluations": results
        }

        # Write the formatted report data to the JSON file
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, default=str)

        # Return file path where the report was saved
        return filepath
