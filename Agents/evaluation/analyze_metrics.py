import json
from pathlib import Path
from typing import Dict, List
import numpy as np
from datetime import datetime


class MetricsAnalyzer:
    def __init__(self):
        self.metrics_path = Path(__file__).parent / "response_metrics.json"
        # print(self.metrics_path)
        self.load_metrics()

    def load_metrics(self):
        """Load metrics from JSON file"""
        if not self.metrics_path.exists():
            raise FileNotFoundError("response_metrics.json not found")

        with open(self.metrics_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def calculate_latency_stats(self) -> Dict:
        """Calculate latency statistics"""
        latencies = [r["latency"] for r in self.data["responses"]]

        return {
            "average_latency": np.mean(latencies),
            "min_latency": np.min(latencies),
            "max_latency": np.max(latencies),
            "std_latency": np.std(latencies),
            "total_responses": len(latencies),
        }

    def print_analysis(self):
        """Print formatted analysis results"""
        stats = self.calculate_latency_stats()

        print("\n=== Chatbot Response Analysis ===")
        print(f"Total Responses: {stats['total_responses']}")
        print(f"Average Latency: {stats['average_latency']:.3f} seconds")
        print(f"Min Latency: {stats['min_latency']:.3f} seconds")
        print(f"Max Latency: {stats['max_latency']:.3f} seconds")
        print(f"Std Deviation: {stats['std_latency']:.3f} seconds")


# Run analysis if file is executed directly
if __name__ == "__main__":
    analyzer = MetricsAnalyzer()
    analyzer.print_analysis()
