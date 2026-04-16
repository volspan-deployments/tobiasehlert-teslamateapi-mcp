from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse
import uvicorn
import threading
from fastmcp import FastMCP
import httpx
import os
from typing import Optional, List, Dict, Any

mcp = FastMCP("TeslaMateApi")

BASE_URL = os.environ.get("TESLAMATE_API_URL", "http://localhost:8080")
API_TOKEN = os.environ.get("API_TOKEN", "")


def get_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if API_TOKEN:
        headers["Authorization"] = f"Bearer {API_TOKEN}"
    return headers


@mcp.tool()
async def get_cars() -> dict:
    """Retrieve a list of all cars registered in TeslaMate. Use this as the starting point to discover available car IDs before querying car-specific data."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/cars",
            headers=get_headers(),
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_car_status(car_id: int) -> dict:
    """Get the current real-time status of a specific car from MQTT data, including location, speed, battery level, charging state, doors, climate, and other live telemetry. Use this when the user wants to know what their car is doing right now."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/cars/{car_id}/status",
            headers=get_headers(),
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_car_drives(
    car_id: int,
    page: Optional[int] = 1,
    per_page: Optional[int] = 100
) -> dict:
    """Retrieve historical drive sessions for a specific car. Returns a list of trips with distance, duration, start/end locations, and efficiency. Use this to analyze driving history or find a specific trip."""
    params = {}
    if page is not None:
        params["page"] = page
    if per_page is not None:
        params["per_page"] = per_page

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/cars/{car_id}/drives",
            headers=get_headers(),
            params=params,
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_drive_details(car_id: int, drive_id: int) -> dict:
    """Get detailed information about a specific drive session including full route data, speed, power usage, and timestamps. Use this when the user wants to inspect a particular trip in depth."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/cars/{car_id}/drives/{drive_id}",
            headers=get_headers(),
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_car_charges(
    car_id: int,
    page: Optional[int] = 1,
    per_page: Optional[int] = 100
) -> dict:
    """Retrieve historical charging sessions for a specific car. Returns a list of charges with energy added, cost, duration, start/end battery levels, and location. Use this to review charging history or costs."""
    params = {}
    if page is not None:
        params["page"] = page
    if per_page is not None:
        params["per_page"] = per_page

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/cars/{car_id}/charges",
            headers=get_headers(),
            params=params,
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_current_charge(car_id: int) -> dict:
    """Get the details of the currently active or most recent charging session for a car. Use this when the user wants to know the live charging status, current charge rate, or estimated time to full."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/cars/{car_id}/charges/current",
            headers=get_headers(),
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_battery_health(car_id: int) -> dict:
    """Retrieve battery health metrics and degradation data for a specific car over time. Use this when the user wants to understand how their battery capacity has changed or assess long-term battery degradation."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/cars/{car_id}/battery_health",
            headers=get_headers(),
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def send_car_command(
    car_id: int,
    command: str,
    parameters: Optional[List[Dict[str, Any]]] = None
) -> dict:
    """Send a command to a Tesla vehicle via TeslaMate. Supports commands such as wake_up, door_lock, door_unlock, honk_horn, flash_lights, set_sentry_mode, climate control, charging control, trunk actuation, and logging suspend/resume. Use this when the user wants to remotely control their vehicle. Requires commands to be enabled via environment variables on the server.

    The command parameter should be the command path, e.g.:
    - 'wake_up'
    - 'command/door_lock'
    - 'command/door_unlock'
    - 'command/honk_horn'
    - 'command/flash_lights'
    - 'command/set_sentry_mode'
    - 'command/charge_start'
    - 'command/charge_stop'
    - 'command/set_charge_limit'
    - 'command/set_temps'
    - 'command/auto_conditioning_start'
    - 'command/auto_conditioning_stop'
    - 'command/actuate_trunk'
    - 'logging/resume'
    - 'logging/suspend'
    """
    # Normalize the command path
    command = command.strip("/")
    url = f"{BASE_URL}/api/v1/cars/{car_id}/{command}"

    # Build request body from parameters
    body = {}
    if parameters:
        for param in parameters:
            if "name" in param and "value" in param:
                body[param["name"]] = param["value"]

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers=get_headers(),
            json=body if body else None,
            timeout=60.0
        )
        response.raise_for_status()
        # Handle empty responses
        if response.content:
            try:
                return response.json()
            except Exception:
                return {"status": response.status_code, "message": response.text}
        return {"status": response.status_code, "message": "Command sent successfully"}




_SERVER_SLUG = "tobiasehlert-teslamateapi"

def _track(tool_name: str, ua: str = ""):
    try:
        import urllib.request, json as _json
        data = _json.dumps({"slug": _SERVER_SLUG, "event": "tool_call", "tool": tool_name, "user_agent": ua}).encode()
        req = urllib.request.Request("https://www.volspan.dev/api/analytics/event", data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=1)
    except Exception:
        pass

async def health(request):
    return JSONResponse({"status": "ok", "server": mcp.name})

async def tools(request):
    registered = await mcp.list_tools()
    tool_list = [{"name": t.name, "description": t.description or ""} for t in registered]
    return JSONResponse({"tools": tool_list, "count": len(tool_list)})

mcp_app = mcp.http_app(transport="streamable-http", stateless_http=True)

class _FixAcceptHeader:
    """Ensure Accept header includes both types FastMCP requires."""
    def __init__(self, app):
        self.app = app
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            accept = headers.get(b"accept", b"").decode()
            if "text/event-stream" not in accept:
                new_headers = [(k, v) for k, v in scope["headers"] if k != b"accept"]
                new_headers.append((b"accept", b"application/json, text/event-stream"))
                scope = dict(scope, headers=new_headers)
        await self.app(scope, receive, send)

app = _FixAcceptHeader(Starlette(
    routes=[
        Route("/health", health),
        Route("/tools", tools),
        Mount("/", mcp_app),
    ],
    lifespan=mcp_app.lifespan,
))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
