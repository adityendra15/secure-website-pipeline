import os

from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

POD_NAME = os.environ.get("POD_NAME", "local-machine")

# Readiness is held in memory so we can flip it during a demo and watch
# Kubernetes pull this pod out of the Service endpoints.
_ready = True

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Secure Website Deployment Pipeline</title>
<style>
  :root { color-scheme: light dark; }
  body {
    margin: 0; min-height: 100vh;
    display: flex; align-items: center; justify-content: center;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: #f6f5f2; color: #2c2c2a;
  }
  .card {
    background: #fff; border: 1px solid #ddd; border-radius: 12px;
    padding: 40px 48px; max-width: 520px; width: 100%; margin: 24px;
  }
  h1 { font-size: 22px; font-weight: 500; margin: 0 0 8px; }
  p  { font-size: 15px; line-height: 1.6; color: #5f5e5a; margin: 0 0 24px; }
  dl { display: grid; grid-template-columns: auto 1fr; gap: 8px 16px;
       font-size: 14px; margin: 0; }
  dt { color: #5f5e5a; }
  dd { margin: 0; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
  .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%;
         background: #1d9e75; margin-right: 6px; }
  @media (prefers-color-scheme: dark) {
    body { background: #1a1a18; color: #e8e6e0; }
    .card { background: #232320; border-color: #3a3a36; }
    p, dt { color: #a3a19a; }
  }
</style>
</head>
<body>
  <div class="card">
    <h1><span class="dot"></span>Deployed and healthy</h1>
    <p>This page was built into a container image, scanned for vulnerabilities,
       inventoried into an SBOM, pushed to a registry and rolled out to
       Kubernetes &mdash; with no manual steps.</p>
    <dl>
      <dt>Serving pod</dt><dd>{{ pod }}</dd>
      <dt>Liveness</dt><dd>/healthz</dd>
      <dt>Readiness</dt><dd>/readyz</dd>
    </dl>
  </div>
</body>
</html>"""


@app.get("/")
def index():
    return render_template_string(PAGE, pod=POD_NAME)


@app.get("/healthz")
def healthz():
    """Liveness probe. If this fails, Kubernetes restarts the container."""
    return jsonify(status="alive", pod=POD_NAME), 200


@app.get("/readyz")
def readyz():
    """Readiness probe. If this fails, Kubernetes stops sending traffic here
    but leaves the container running."""
    if _ready:
        return jsonify(status="ready", pod=POD_NAME), 200
    return jsonify(status="not-ready", pod=POD_NAME), 503


@app.post("/demo/toggle-ready")
def toggle_ready():
    """Demo-only endpoint used to force a readiness failure on one pod."""
    global _ready
    _ready = not _ready
    return jsonify(ready=_ready, pod=POD_NAME), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
