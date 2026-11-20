# Import standard modules for filesystem management, timestamps, and typing support
import os
from datetime import datetime
from typing import List, Dict, Any

# Generates an executive visual HTML report with Tier-2 Judge metadata & Latency metrics
class HTMLReporter:

    # Initializes the reporter with an output directory and ensures the directory exists
    def __init__(self, output_dir: str = "reports"):

        # Store output directory path and create folder structure if missing
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    # Generates a stylized HTML dashboard report containing metrics, probe results, and judge metadata
    def export_html(self, results: List[Dict[str, Any]], score: float, model_name: str) -> str:
        
        # Create formatted timestamps and construct unique report filename/filepath
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        filename = f"audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = os.path.join(self.output_dir, filename)

        # Count total passes/failures and assign overall score badge color (green/red)
        passed_count = sum(1 for r in results if r["passed"])
        failed_count = len(results) - passed_count
        badge_color = "#10b981" if score >= 75 else "#ef4444"

        # Calculate average response latency across all finished probes
        latencies = [r["latency"] for r in results if "latency" in r]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

        # Build dynamic HTML table rows for each attack probe
        rows_html = ""
        for r in results:
            # Generate color-coded status badge for test outcomes
            status_badge = (
                '<span style="background: #10b98122; color: #10b981; border: 1px solid #10b981; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 0.85rem;">PASSED (Refused)</span>'
                if r["passed"] else
                '<span style="background: #ef444422; color: #ef4444; border: 1px solid #ef4444; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 0.85rem;">FAILED (Jailbreak)</span>'
            )
            
            # Escape HTML special characters in the response text to prevent layout breaking or XSS
            clean_response = r.get("model_response", "No response captured.").replace("<", "&lt;").replace(">", "&gt;")
            
            # Extract evaluation metadata from the judge dictionary
            judge = r.get("judge", {})
            reason = judge.get("reason", "Evaluated via Hybrid Engine")
            confidence = judge.get("confidence", 0.0) * 100
            severity = judge.get("severity", "LOW")
            latency = r.get("latency", 0.0)

            # Assign color dynamically based on evaluation severity level
            severity_color = "#ef4444" if severity in ["HIGH", "CRITICAL"] else "#f59e0b" if severity == "MEDIUM" else "#10b981"

            # Append current probe details into table row template
            rows_html += f"""
            <tr style="border-bottom: 1px solid #1e293b;">
                <td style="padding: 14px; font-family: monospace; color: #94a3b8; vertical-align: top;">{r['probe_id']}</td>
                <td style="padding: 14px; color: #38bdf8; font-weight: 500; vertical-align: top;">{r['category']}</td>
                <td style="padding: 14px; color: #e2e8f0; vertical-align: top;">
                    <div style="font-weight: 600; margin-bottom: 6px;">{r['prompt']}</div>
                    <div style="font-size: 0.75rem; color: #64748b; margin-top: 2px;"> Response Latency: {latency:.2f}s</div>
                    <details style="margin-top: 8px;">
                        <summary style="cursor: pointer; color: #a78bfa; font-size: 0.85rem; font-weight: 500; user-select: none;">
                            View Judge Audit & Raw Response
                        </summary>
                        <div style="margin-top: 8px; background: #090d16; padding: 12px; border-radius: 6px; border: 1px solid #334155;">
                            <div style="display: flex; gap: 12px; align-items: center; margin-bottom: 8px;">
                                <span style="font-size: 0.75rem; font-weight: 700; color: #38bdf8; text-transform: uppercase;"> AI Judge Verdict:</span>
                                <span style="font-size: 0.75rem; background: #334155; padding: 2px 6px; border-radius: 4px; color: #f8fafc;">Confidence: {confidence:.0f}%</span>
                                <span style="font-size: 0.75rem; background: {severity_color}22; color: {severity_color}; border: 1px solid {severity_color}; padding: 2px 6px; border-radius: 4px; font-weight: bold;">Severity: {severity}</span>
                            </div>
                            <div style="font-size: 0.85rem; color: #f1f5f9; margin-bottom: 12px; font-style: italic;">
                                "{reason}"
                            </div>
                            <div style="font-size: 0.75rem; font-weight: 700; color: #94a3b8; margin-bottom: 6px; text-transform: uppercase;">
                                Raw Model Response:
                            </div>
                            <div style="font-family: monospace; font-size: 0.85rem; color: #cbd5e1; white-space: pre-wrap; word-break: break-word;">
{clean_response}
                            </div>
                        </div>
                    </details>
                </td>
                <td style="padding: 14px; text-align: center; vertical-align: top;">{status_badge}</td>
            </tr>
            """
        # Construct full HTML document combining CSS styles, executive summary, and table rows
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Veritas-LLM Security Audit Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 40px; }}
        .container {{ max-width: 1100px; margin: 0 auto; }}
        .header {{ background: #1e293b; padding: 30px; border-radius: 12px; border: 1px solid #334155; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: center; }}
        .title {{ font-size: 1.6rem; font-weight: 700; color: #f8fafc; margin: 0; }}
        .subtitle {{ font-size: 0.9rem; color: #94a3b8; margin-top: 5px; }}
        .score-card {{ text-align: right; }}
        .score-num {{ font-size: 2.4rem; font-weight: 800; color: {badge_color}; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px; }}
        .stat-card {{ background: #1e293b; padding: 18px; border-radius: 10px; border: 1px solid #334155; text-align: center; }}
        .stat-val {{ font-size: 1.6rem; font-weight: 700; margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 12px; overflow: hidden; border: 1px solid #334155; }}
        th {{ background: #0f172a; color: #94a3b8; text-align: left; padding: 14px; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1 class="title"> Veritas-LLM Security Audit</h1>
                <div class="subtitle">Target Model: <strong>{model_name}</strong> | Executed: {timestamp}</div>
            </div>
            <div class="score-card">
                <div style="font-size: 0.8rem; text-transform: uppercase; color: #94a3b8;">Robustness Score</div>
                <div class="score-num">{score:.1f}%</div>
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div style="color: #94a3b8; font-size: 0.8rem;">Total Probes</div>
                <div class="stat-val" style="color: #38bdf8;">{len(results)}</div>
            </div>
            <div class="stat-card">
                <div style="color: #94a3b8; font-size: 0.8rem;">Refused (Safe)</div>
                <div class="stat-val" style="color: #10b981;">{passed_count}</div>
            </div>
            <div class="stat-card">
                <div style="color: #94a3b8; font-size: 0.8rem;">Jailbroken (Unsafe)</div>
                <div class="stat-val" style="color: #ef4444;">{failed_count}</div>
            </div>
            <div class="stat-card">
                <div style="color: #94a3b8; font-size: 0.8rem;">Avg Latency</div>
                <div class="stat-val" style="color: #a78bfa;">{avg_latency:.2f}s</div>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th style="width: 110px;">ID</th>
                    <th style="width: 170px;">Category</th>
                    <th>Adversarial Prompt & Model Audit</th>
                    <th style="width: 160px; text-align: center;">Audit Verdict</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
</body>
</html>
"""
        # Save complete HTML document string to report file path
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)

        # Return file path of saved HTML report
        return filepath
