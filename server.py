"""
Web Dashboard Server for AI Accessibility (WCAG) & UI Regression Auditor.
Serves interactive audit interface, dynamic re-audit API, test pack pages,
and graceful link simulation fallbacks.
"""

import sys
import json
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse
from datetime import datetime, timezone

from auditor.rules import audit_page_file
from auditor.models import AuditSummaryReport, Severity

BASE_DIR = Path(__file__).resolve().parent
PORT = 8000


class AuditorRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # Flush stdout immediately
        sys.stdout.write(f"[{datetime.now().strftime('%H:%M:%S')}] {format % args}\n")
        sys.stdout.flush()

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
            if target.exists() and target.is_file():
                self.serve_file(target, "text/html")
            else:
                self.serve_simulated_destination(path)
        elif path.startswith("/output/"):
            filename = path.replace("/output/", "")
            target = BASE_DIR / "output" / filename
            if target.exists() and target.is_file():
                self.serve_file(target, "application/json")
            else:
                self.send_error(404, "Report not found")
        else:
            # Fallback for relative links clicked inside preview iframe (e.g. /research/...)
            self.serve_simulated_destination(path)

    def serve_file(self, file_path: Path, content_type: str):
        if not file_path.exists():
            self.send_error(404, f"File {file_path.name} not found")
            return
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(data)

    def serve_simulated_destination(self, requested_path: str):
        """Friendly destination page when links are clicked inside preview iframes."""
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Simulated Navigation Target</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #f8fafc;
      color: #334155;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
      padding: 1rem;
    }}
    .card {{
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 2rem;
      max-width: 480px;
      text-align: center;
      box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    }}
    .badge {{
      background: #e0e7ff;
      color: #4338ca;
      font-size: 0.75rem;
      font-weight: 600;
      padding: 0.25rem 0.6rem;
      border-radius: 9999px;
      display: inline-block;
      margin-bottom: 1rem;
    }}
    code {{
      background: #f1f5f9;
      color: #0f172a;
      padding: 0.2rem 0.4rem;
      border-radius: 4px;
      font-size: 0.85rem;
    }}
    button {{
      background: #4f46e5;
      color: white;
      border: none;
      padding: 0.65rem 1.25rem;
      border-radius: 6px;
      font-weight: 600;
      cursor: pointer;
      margin-top: 1.5rem;
    }}
    button:hover {{ background: #4338ca; }}
  </style>
</head>
<body>
  <div class="card">
    <span class="badge">Simulated Link Target</span>
    <h3 style="margin: 0 0 0.5rem 0; color: #0f172a;">Sample Link Navigation</h3>
    <p style="font-size: 0.9rem; line-height: 1.5; color: #64748b;">
      You clicked a test link pointing to: <br><code>{requested_path}</code>
    </p>
    <p style="font-size: 0.825rem; color: #94a3b8;">
      This link is part of the bounded accessibility test pack to audit link ambiguity (WCAG 2.4.4).
    </p>
    <button onclick="history.back()">← Return to Page</button>
  </div>
</body>
</html>"""
        data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
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
    sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server stopped.")


if __name__ == "__main__":
    run_server()
