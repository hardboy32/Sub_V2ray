import asyncio
import base64
import binascii
import json
import os
import re
import time
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, Response
from apscheduler.schedulers.asyncio import AsyncIOScheduler

SCHEMES = ("vless://", "vmess://", "trojan://", "ss://")


def load_sources():
    # Preferred Railway Variables: SOURCE_1=URL, SOURCE_2=URL, ... SOURCE_20=URL.
    # Numeric names are also checked for backward compatibility.
    numbered = []
    for index in range(1, 21):
        value = os.getenv(f"SOURCE_{index}") or os.getenv(str(index), "")
        value = value.strip()
        if value:
            numbered.append(value)
    # Keep SOURCES as a backwards-compatible alternative.
    legacy = [x.strip() for x in re.split(r"[,\\n]+", os.getenv("SOURCES", "")) if x.strip()]
    return list(dict.fromkeys(numbered + legacy))


SOURCES = load_sources()
REFRESH_MINUTES = max(5, int(os.getenv("REFRESH_MINUTES", "30")))
MAX_RESULTS = max(1, int(os.getenv("MAX_RESULTS", "200")))
CONCURRENCY = max(1, int(os.getenv("TEST_CONCURRENCY", "40")))
CONNECT_TIMEOUT = max(1, float(os.getenv("CONNECT_TIMEOUT", "4")))

state = {
    "items": [],
    "last_refresh": None,
    "last_error": None,
    "sources_ok": 0,
    "candidates": 0,
    "iran_test_available": False,
}
scheduler = AsyncIOScheduler()


def decode_subscription(body: str) -> str:
    text = body.strip().lstrip("\\ufeff")
    if not text:
        return ""
    if any(s in text.lower() for s in SCHEMES):
        return text
    compact = re.sub(r"\\s+", "", text)
    try:
        decoded = base64.b64decode(compact + "=" * (-len(compact) % 4)).decode("utf-8", "ignore")
        if any(s in decoded.lower() for s in SCHEMES):
            return decoded
    except (binascii.Error, ValueError):
        pass
    return text


def endpoint(link: str):
    raw = link.strip()
    try:
        if raw.lower().startswith("vmess://"):
            payload = raw[8:].split("#", 1)[0]
            data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
            return str(data.get("add", "")), int(data.get("port", 0))
        if raw.lower().startswith("ss://"):
            part = raw[5:].split("#", 1)[0].split("?", 1)[0]
            if "@" not in part:
                part = base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)).decode()
            parsed = urlsplit("ss://" + part if not part.startswith("ss://") else part)
            return parsed.hostname or "", parsed.port or 0
        parsed = urlsplit(raw)
        return parsed.hostname or "", parsed.port or (443 if parsed.scheme == "https" else 0)
    except Exception:
        return "", 0


async def fetch_source(client: httpx.AsyncClient, url: str):
    try:
        response = await client.get(url)
        response.raise_for_status()
        text = decode_subscription(response.text)
        return [line.strip() for line in text.splitlines() if line.strip().lower().startswith(SCHEMES)], None
    except Exception as exc:
        return [], f"{url}: {type(exc).__name__}"


async def probe(link: str, semaphore: asyncio.Semaphore):
    host, port = endpoint(link)
    if not host or not (1 <= port <= 65535):
        return None
    async with semaphore:
        started = time.perf_counter()
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=CONNECT_TIMEOUT
            )
            latency = (time.perf_counter() - started) * 1000
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            return {"link": link, "host": host, "port": port, "latency_ms": round(latency, 1)}
        except Exception:
            return None


async def refresh():
    global SOURCES
    SOURCES = load_sources()
    if not SOURCES:
        state["last_error"] = "No sources configured. Add SOURCE_1 through SOURCE_20 Railway Variables."
        return

    errors = []
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(12), follow_redirects=True,
        headers={"User-Agent": "Sub-V2ray-Aggregator/1.0"}
    ) as client:
        results = await asyncio.gather(*(fetch_source(client, u) for u in SOURCES))
    candidates = []
    for links, error in results:
        candidates.extend(links)
        if error:
            errors.append(error)
    unique = list(dict.fromkeys(x.strip() for x in candidates))
    state["candidates"] = len(unique)
    semaphore = asyncio.Semaphore(CONCURRENCY)
    tested = await asyncio.gather(*(probe(link, semaphore) for link in unique))
    alive = [x for x in tested if x]
    alive.sort(key=lambda x: x["latency_ms"])
    state["sources_ok"] = len(SOURCES) - len(errors)
    if alive:
        state["items"] = [x["link"] for x in alive[:MAX_RESULTS]]
        state["last_refresh"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        state["last_error"] = "; ".join(errors[:5]) if errors else None
    elif not state["items"]:
        state["last_error"] = "; ".join(errors[:5]) or "No reachable endpoints found"


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(refresh, "interval", minutes=REFRESH_MINUTES, id="refresh", max_instances=1)
    scheduler.start()
    await refresh()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Sub V2ray", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/status")
async def status():
    return {
        "last_refresh": state["last_refresh"],
        "last_error": state["last_error"],
        "sources_configured": len(SOURCES),
        "sources_ok": state["sources_ok"],
        "unique_candidates": state["candidates"],
        "published": len(state["items"]),
        "max_results": MAX_RESULTS,
        "iran_test_available": state["iran_test_available"],
        "server_side_check": "TCP reachability from Railway only",
        "client_side_ping": True,
        "client_side_selection": "The user's own V2Ray client tests imported nodes and chooses the preferred one",
        "test_location": "Railway deployment region; not Iran",
    }


@app.get("/sub", response_class=Response)
@app.get("/sub/all", response_class=Response)
async def subscription():
    if not state["items"]:
        return Response("Subscription is being prepared. Please retry later.\\n", status_code=503, media_type="text/plain")
    payload = "\\n".join(state["items"]) + "\\n"
    encoded = base64.b64encode(payload.encode()).decode()
    return Response(encoded, media_type="text/plain; charset=utf-8")
