import pandas as pd
from datetime import datetime
from pathlib import Path
import json
from typing import Dict, List


class ResponseLogger:
    def __init__(self):
        self.eval_dir = Path(__file__).parent
        self.json_path = self.eval_dir / "response_metrics.json"

        # Create or load existing metrics
        if self.json_path.exists():
            with open(self.json_path, "r", encoding="utf-8") as f:
                self.metrics = json.load(f)
        else:
            self.metrics = {"responses": []}

    def log_response(
        self,
        user_query: str,
        bot_response: str,
        latency: float,
        function_called: str = None,
    ):
        """Log response with metrics in JSON format"""
        response_data = {
            "timestamp": datetime.now().isoformat(),
            "response": {"user_query": user_query, "bot_response": bot_response},
            "latency": latency,
            "function_called": function_called,
        }

        self.metrics["responses"].append(response_data)

        # Save to JSON file with proper formatting
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(self.metrics, f, ensure_ascii=False, indent=2)

    def get_metrics_summary(self) -> Dict:
        """Get summary statistics"""
        if not self.metrics["responses"]:
            return {}

        latencies = [r["latency"] for r in self.metrics["responses"]]
        return {
            "total_responses": len(self.metrics["responses"]),
            "avg_latency": sum(latencies) / len(latencies),
            "max_latency": max(latencies),
            "min_latency": min(latencies),
        }
