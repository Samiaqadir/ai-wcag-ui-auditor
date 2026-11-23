"""
Web Dashboard Server for AI Accessibility (WCAG) & UI Regression Auditor.
Serves interactive audit interface, dynamic re-audit API, and test pack pages.
"""

import os
import sys
import json
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse

from auditor.rules import audit_page_file
from auditor.models import AuditSummaryReport, Severity
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent
PORT = 8000


class AuditorRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ["/", "/index.html"]:
            self.serve_file(BASE_DIR / "dashboard.html", "text/html")
        elif path == "/api/audit":
            self.handle_api_audit()
        elif path.startswith("/test_pages/"):
            filename = path.replace("/test_pages/", "")
            target = BASE_DIR / "test_pages" / filename
            self.serve_file(target, "text/html")
        elif path.startswith("/output/"):
            filename = path.replace("/output/", "")
            target = BASE_DIR / "output" / filename
            self.serve_file(target, "application/json")
        else:
            super().do_GET()

    def serve_file(self, file_path: Path, content_type: str):
        if not file_path.exists():
            self.send_error(404, f"File {file_path.name} not found")
            return
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def handle_api_audit(self):
        test_pages_dir = BASE_DIR / "test_pages"
        html_files = sorted(test_pages_dir.glob("*.html"))

        page_results = []
        total_violations = 0
        passed_count = 0
        failed_count = 0
        severity_totals = {
            Severity.CRITICAL.value: 0,
            Severity.SERIOUS.value: 0,
            Severity.MODERATE.value: 0,
            Severity.MINOR.value: 0,
        }

        for p in html_files:
            res = audit_page_file(p)
            page_results.append(res)
            if res.status == "PASSED":
                passed_count += 1
            else:
                failed_count += 1
            total_violations += res.total_violations
            for sev, count in res.violations_by_severity.items():
                severity_totals[sev] = severity_totals.get(sev, 0) + count

        summary_report = AuditSummaryReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            engine_version="1.0.0-day1",
            total_pages_scanned=len(html_files),
            passed_pages=passed_count,
            failed_pages=failed_count,
            total_violations=total_violations,
            violations_by_severity=severity_totals,
            results=page_results,
        )

        # Save to disk
        output_file = BASE_DIR / "output" / "initial_audit_report.json"
        output_file.write_text(json.dumps(summary_report.model_dump(), indent=2), encoding="utf-8")

        response_bytes = json.dumps(summary_report.model_dump()).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response_bytes)


def run_server():
    server = HTTPServer(("127.0.0.1", PORT), AuditorRequestHandler)
    print(f"[*] AI Accessibility Auditor Web Server listening on http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server stopped.")


if __name__ == "__main__":
    run_server()
