"""Local web app: one Python process, no build step, no account or database."""
import argparse
import json
import logging
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from urllib.request import urlopen
from plotly.offline import get_plotlyjs
from market_data import search_stocks
from service import analyze

ROOT = Path(__file__).resolve().parent
PLOTLY = get_plotlyjs().encode("utf-8")
FILES = {"/":("index.html","text/html"),"/styles.css":("styles.css","text/css"),
         "/main.js":("main.js","text/javascript")}

class Handler(BaseHTTPRequestHandler):
    def send(self, status, data, content_type="application/json"):
        if isinstance(data, (dict,list)):
            data = json.dumps(data, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type+"; charset=utf-8")
        self.send_header("Content-Length",str(len(data)))
        self.send_header("Cache-Control","private, max-age=3600" if urlsplit(self.path).path=="/plotly.js" else "no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):
            pass

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path in FILES:
            filename, mime = FILES[url.path]
            return self.send(200,(ROOT/"web"/filename).read_bytes(),mime)
        if url.path == "/plotly.js":
            return self.send(200,PLOTLY,"text/javascript")
        if url.path == "/health":
            return self.send(200,{"ok":True,"application":"portfolio-thesis-analyzer"})
        if url.path == "/api/search":
            try:
                return self.send(200,{"results":search_stocks(parse_qs(url.query).get("q",[""])[0])})
            except ValueError as exc:
                return self.send(400,{"error":str(exc)})
            except Exception:
                logging.exception("Search failed")
                return self.send(503,{"error":"Stock search is temporarily unavailable. Try again shortly."})
        return self.send(404,{"error":"Not found"})

    def do_POST(self):
        if urlsplit(self.path).path != "/api/analyze":
            return self.send(404,{"error":"Not found"})
        # Browser actions must originate from this app; no cross-origin API use.
        origin = self.headers.get("Origin")
        if origin and urlsplit(origin).netloc != self.headers.get("Host"):
            return self.send(403,{"error":"Cross-origin requests are not accepted."})
        try:
            size = int(self.headers.get("Content-Length","0"))
            if not 0 < size <= 16000:
                raise ValueError("Invalid request size.")
            payload = json.loads(self.rfile.read(size))
            return self.send(200,analyze(payload))
        except (ValueError,TypeError,KeyError) as exc:
            return self.send(400,{"error":str(exc) if isinstance(exc,ValueError) else "Invalid portfolio request."})
        except Exception:
            logging.exception("Portfolio request failed")
            return self.send(503,{"error":"Analysis is temporarily unavailable. Your last portfolio is unchanged. Please retry."})

    def log_message(self, format, *args):
        # Do not log company search queries or user inputs.
        if args and str(args[1]) not in {"200","304"}:
            logging.info("HTTP response %s",args[1])

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--port",type=int,default=8501)
    parser.add_argument("--host",default="127.0.0.1")
    parser.add_argument("--open-browser",action="store_true")
    args=parser.parse_args()
    url=f"http://{args.host}:{args.port}"
    try:
        server=ThreadingHTTPServer((args.host,args.port),Handler)
    except OSError as exc:
        if args.open_browser:
            try:
                with urlopen(url+"/health",timeout=2) as response:
                    existing=json.load(response)
                if existing.get("application")=="portfolio-thesis-analyzer":
                    webbrowser.open(url)
                    print(f"Your portfolio app is already running: {url}")
                    raise SystemExit(0)
            except (OSError,ValueError):
                pass
        raise SystemExit(f"Could not start on {url}: {exc}. Try --port 8502.")
    print(f"Portfolio Thesis Analyzer: {url}",flush=True)
    if args.open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
