from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse
import uvicorn
import threading
from fastmcp import FastMCP
import httpx
import os
from typing import Optional, List, Any

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
    """Retrieve a list of all Tesla vehicles tracked by TeslaMate. Use this as the first step to discover available car IDs before querying any car-specific data."""
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
    """Get the current real-time status of a specific Tesla vehicle, including location, battery level, charging state, climate, and other live data pulled from MQTT. Use this when the user wants to know what their car is doing right now."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/cars/{car_id}/status",
            headers=get_headers(),
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_car_battery_health(car_id: int) -> dict:
    """Retrieve battery health history and degradation data for a specific Tesla vehicle. Use this when the user wants to understand how their battery capacity has changed over time."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/cars/{car_id}/battery_health",
            headers=get_headers(),
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_car_charges(car_id: int, page: int = 1, per_page: int = 100) -> dict:
    """Retrieve a paginated list of past charging sessions for a specific Tesla vehicle, including dates, energy added, and costs. Use this to review charging history or analyze charging patterns."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/cars/{car_id}/charges",
            headers=get_headers(),
            params={"page": page, "per_page": per_page},
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_charge_details(car_id: int, charge_id: int) -> dict:
    """Get detailed information about a specific charging session including energy data, start/end battery levels, duration, cost, and charging curve. Use this when the user wants to drill into a particular charge event."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/cars/{car_id}/charges/{charge_id}",
            headers=get_headers(),
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_car_drives(car_id: int, page: int = 1, per_page: int = 100) -> dict:
    """Retrieve a paginated list of past driving trips for a specific Tesla vehicle, including distance, duration, energy used, and start/end locations. Use this to review driving history or analyze trip patterns."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/cars/{car_id}/drives",
            headers=get_headers(),
            params={"page": page, "per_page": per_page},
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_drive_details(car_id: int, drive_id: int) -> dict:
    """Get detailed information about a specific driving trip including route data, speed, energy consumption, and efficiency metrics. Use this when the user wants to drill into a particular drive."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/cars/{car_id}/drives/{drive_id}",
            headers=get_headers(),
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def send_car_command(
    car_id: int,
    command: str,
    parameters: Optional[List[Any]] = None
) -> dict:
    """Send a command to a Tesla vehicle through TeslaMate. Available commands include: wake_up, honk_horn, flash_lights, door_lock, door_unlock, set_sentry_mode, charge_start, charge_stop, set_charge_limit, set_charging_amps, climate controls, window controls, trunk controls, and logging suspend/resume. Use this when the user wants to remotely control their vehicle. Requires commands to be enabled via environment variables."""
    # Normalize command path - strip leading slash if present
    command_path = command.lstrip("/")
    url = f"{BASE_URL}/api/v1/cars/{car_id}/{command_path}"

    async with httpx.AsyncClient() as client:
        if parameters:
            response = await client.post(
                url,
                headers=get_headers(),
                json=parameters,
                timeout=30.0
            )
        else:
            response = await client.post(
                url,
                headers=get_headers(),
                timeout=30.0
            )
        response.raise_for_status()
        try:
            return response.json()
        except Exception:
            return {"status": response.status_code, "message": response.text}




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

sse_app = mcp.http_app(transport="sse")

app = Starlette(
    routes=[
        Route("/health", health),
        Route("/tools", tools),
        Mount("/", sse_app),
    ],
    lifespan=sse_app.lifespan,
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
