import asyncio
import json
import os
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from playwright.async_api import Browser, BrowserContext, Page, async_playwright



APP_URL = os.getenv(
    "WEBMCP_FLIGHTSEARCH_URL",
    "https://googlechromelabs.github.io/webmcp-tools/demos/react-flightsearch/",
)


HEADLESS = False
NAV_TIMEOUT_MS = int(os.getenv("PLAYWRIGHT_NAV_TIMEOUT_MS", "60000"))
ACTION_TIMEOUT_MS = int(os.getenv("PLAYWRIGHT_ACTION_TIMEOUT_MS", "6000"))


def _minutes_from_hhmm(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


class BrowserFlightBridge:
    def __init__(self) -> None:
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self.current_search: Dict[str, Any] = {
            "origin": "",
            "destination": "",
            "tripType": "one-way",
            "outboundDate": "",
            "inboundDate": "",
            "passengers": 1,
        }
        self.current_filters: Dict[str, Any] = self._default_filters()

    @staticmethod
    def _default_filters() -> Dict[str, Any]:
        return {
            "stops": [],
            "airlines": [],
            "origins": [],
            "destinations": [],
            "minPrice": 0,
            "maxPrice": 1000,
            "departureTime": [0, 1439],
            "arrivalTime": [0, 1439],
            "flightIds": [],
        }

    async def ensure_page(self) -> Page:
        if self._page:
            return self._page

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=HEADLESS)
        self._context = await self._browser.new_context()
        self._page = await self._context.new_page()
        self._page.set_default_navigation_timeout(NAV_TIMEOUT_MS)
        self._page.set_default_timeout(ACTION_TIMEOUT_MS)
        await self._page.goto(APP_URL, wait_until="domcontentloaded")
        await self._page.wait_for_timeout(1200)
        return self._page

    async def close(self) -> None:
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    async def open_demo(self) -> Dict[str, Any]:
        page = await self.ensure_page()
        await page.goto(APP_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(800)
        return {
            "url": page.url,
            "title": await page.title(),
            "native_modelcontext_detected": await self.has_native_modelcontext(),
        }

    async def has_native_modelcontext(self) -> bool:
        page = await self.ensure_page()
        return bool(
            await page.evaluate(
                "() => Boolean(window.navigator.modelContext)"
            )
        )

    async def _dispatch_custom_event(
        self,
        event_name: str,
        detail: Dict[str, Any],
        *,
        ensure_root: bool = False,
        ensure_results: bool = False,
    ) -> Dict[str, Any]:
        page = await self.ensure_page()

        if ensure_root:
            await page.goto(APP_URL, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

        if ensure_results and "/results" not in page.url:
            params = self.current_search.copy()
            if params.get("origin") and params.get("destination"):
                from urllib.parse import urlencode

                target = APP_URL.rstrip("/") + "/results?" + urlencode(
                    {
                        "origin": params["origin"],
                        "destination": params["destination"],
                        "tripType": params["tripType"],
                        "outboundDate": params["outboundDate"],
                        "inboundDate": params["inboundDate"],
                        "passengers": params["passengers"],
                    }
                )
                await page.goto(target, wait_until="domcontentloaded")
                await page.wait_for_timeout(500)

        # Dispatch the event without waiting for completion
        await page.evaluate(
            """
            ({ eventName, detail }) => {
              window.dispatchEvent(
                new CustomEvent(eventName, {
                  detail: detail,
                })
              );
            }
            """,
            {
                "eventName": event_name,
                "detail": detail,
            },
        )
        await page.wait_for_timeout(1000)  # Short wait for processing
        return {"ok": True}

    def _validate_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        origin = str(params.get("origin", "")).upper().strip()
        destination = str(params.get("destination", "")).upper().strip()
        trip_type = str(params.get("tripType", "one-way")).strip()
        outbound_date = str(params.get("outboundDate", "")).strip()
        inbound_date = str(params.get("inboundDate", "")).strip()
        passengers = int(params.get("passengers", 1))

        if len(origin) != 3 or not origin.isalpha():
            raise ValueError("origin debe ser un código IATA de 3 letras.")
        if len(destination) != 3 or not destination.isalpha():
            raise ValueError("destination debe ser un código IATA de 3 letras.")
        if trip_type not in {"one-way", "round-trip"}:
            raise ValueError('tripType debe ser "one-way" o "round-trip".')
        if not outbound_date:
            raise ValueError("outboundDate es obligatorio.")
        if trip_type == "round-trip" and not inbound_date:
            raise ValueError("inboundDate es obligatorio para round-trip.")
        if passengers < 1:
            raise ValueError("passengers debe ser >= 1.")

        return {
            "origin": origin,
            "destination": destination,
            "tripType": trip_type,
            "outboundDate": outbound_date,
            "inboundDate": inbound_date,
            "passengers": passengers,
        }

    def _demo_query_supported(self) -> bool:
        return (
            self.current_search.get("origin") == "LON"
            and self.current_search.get("destination") == "NYC"
            and self.current_search.get("tripType") == "round-trip"
        )

    def _apply_filters(self, flights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        f = self.current_filters
        filtered = list(flights)

        if f["stops"]:
            filtered = [x for x in filtered if x["stops"] in f["stops"]]
        if f["airlines"]:
            allowed = set(f["airlines"])
            filtered = [x for x in filtered if x["airlineCode"] in allowed]
        if f["origins"]:
            allowed = set(f["origins"])
            filtered = [x for x in filtered if x["origin"] in allowed]
        if f["destinations"]:
            allowed = set(f["destinations"])
            filtered = [x for x in filtered if x["destination"] in allowed]
        if f["flightIds"]:
            allowed = set(f["flightIds"])
            filtered = [x for x in filtered if x["id"] in allowed]

        filtered = [
            x for x in filtered
            if f["minPrice"] <= x["price"] <= f["maxPrice"]
        ]
        filtered = [
            x for x in filtered
            if f["departureTime"][0] <= _minutes_from_hhmm(x["departureTime"]) <= f["departureTime"][1]
        ]
        filtered = [
            x for x in filtered
            if f["arrivalTime"][0] <= _minutes_from_hhmm(x["arrivalTime"]) <= f["arrivalTime"][1]
        ]
        return sorted(filtered, key=lambda x: (x["price"], x["duration"], x["id"]))

    async def search_flights(self, params: Dict[str, Any]) -> Dict[str, Any]:
        normalized = self._validate_search(params)
        result = await self._dispatch_custom_event(
            "searchFlights",
            normalized,
            ensure_root=True,
        )
        page = await self.ensure_page()
        # Wait for navigation to results
        try:
            await page.wait_for_url("**/results**", timeout=5000)
        except:
            pass  # If not navigated, continue
        self.current_search = normalized
        self.current_filters = self._default_filters()

        note = None
        if not self._demo_query_supported():
            note = (
                "El demo oficial solo muestra resultados cuando "
                "origin=LON, destination=NYC y tripType=round-trip."
            )

        return {
            "ok": result.get("ok", False),
            "message": "Búsqueda enviada al demo.",
            "browser_url": page.url,
            "native_modelcontext_detected": await self.has_native_modelcontext(),
            "search": self.current_search,
            "supported_demo_query": self._demo_query_supported(),
            "note": note,
        }

    async def set_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        page = await self.ensure_page()
        if "/results" not in page.url:
            raise RuntimeError("Primero debes ejecutar una búsqueda para llegar a la pantalla de resultados.")

        payload = self._default_filters()
        payload.update({k: v for k, v in filters.items() if v is not None})

        result = await self._dispatch_custom_event(
            "setFilters",
            payload,
            ensure_results=True,
        )
        
        self.current_filters = payload
        return {
            "ok": result.get("ok", False),
            "message": "Filtros aplicados al demo.",
            "browser_url": page.url,
            "filters": self.current_filters,
            "supported_demo_query": self._demo_query_supported(),
        }

    async def reset_filters(self) -> Dict[str, Any]:
        page = await self.ensure_page()
        if "/results" not in page.url:
            raise RuntimeError("No hay resultados abiertos para resetear filtros.")

        result = await self._dispatch_custom_event(
            "resetFilters",
            {},
            ensure_results=True,
        )
        self.current_filters = self._default_filters()
        return {
            "ok": result.get("ok", False),
            "message": "Filtros reseteados.",
            "browser_url": page.url,
            "filters": self.current_filters,
            "supported_demo_query": self._demo_query_supported(),
        }

    async def list_flights(self, limit: int = 10) -> Dict[str, Any]:
        page = await self.ensure_page()

        if "/results" not in page.url:
            raise RuntimeError("Primero debes ejecutar una búsqueda para llegar a la pantalla de resultados.")

        # Scrape the displayed flights from the DOM
        flights = await page.evaluate("""
        const cards = document.querySelectorAll('.flight-card');
        Array.from(cards).map((card, index) => {
            const airline = card.querySelector('.airline')?.textContent || '';
            const departureTime = card.querySelector('.departure .time')?.textContent || '';
            const origin = card.querySelector('.departure .airport')?.textContent || '';
            const duration = card.querySelector('.duration')?.textContent || '';
            const stopsText = card.querySelector('.stops')?.textContent || '';
            const stops = parseInt(stopsText.replace(/ stops?/, '')) || 0;
            const arrivalTime = card.querySelector('.arrival .time')?.textContent || '';
            const destination = card.querySelector('.arrival .airport')?.textContent || '';
            const priceText = card.querySelector('.price')?.textContent || '';
            const price = parseFloat(priceText.replace('$', '')) || 0;
            // Approximate airlineCode from airline name
            const airlineCode = airline.split(' ')[0] || '';
            return {
                id: index + 1,  // Assign sequential id since not in DOM
                airline,
                airlineCode,
                origin,
                destination,
                departureTime,
                arrivalTime,
                duration,
                stops,
                price,
            };
        });
        """)

        filtered = flights  # Flights are already filtered by the page's current filters

        return {
            "ok": True,
            "supported_demo_query": self._demo_query_supported(),
            "browser_url": page.url,
            "search": self.current_search,
            "filters": self.current_filters,
            "total_results": len(filtered),
            "flights": filtered[: max(1, min(limit, 50))],
        }

    async def get_state(self) -> Dict[str, Any]:
        page = await self.ensure_page()
        return {
            "browser_url": page.url,
            "search": self.current_search,
            "filters": self.current_filters,
            "supported_demo_query": self._demo_query_supported(),
            "native_modelcontext_detected": await self.has_native_modelcontext(),
        }


bridge = BrowserFlightBridge()
mcp = FastMCP("webmcp-flightsearch-playwright-bridge")


@mcp.tool()
async def open_demo() -> str:
    """Abre el demo oficial de WebMCP Flight Search en Playwright."""
    return json.dumps(await bridge.open_demo(), ensure_ascii=False, indent=2)


@mcp.tool()
async def get_demo_capabilities() -> str:
    """Describe las capacidades reales y limitaciones conocidas del demo oficial."""
    payload = {
        "demo_url": APP_URL,
        "supported_query_required_for_visible_results": {
            "origin": "LON",
            "destination": "NYC",
            "tripType": "round-trip",
        },
        "notes": [
            "La aplicación oficial registra las tools searchFlights, listFlights, setFilters y resetFilters.",
            "El demo de resultados solo muestra vuelos para la consulta LON -> NYC con round-trip.",
            "Los filtros soportados incluyen stops, airlines, origins, destinations, minPrice, maxPrice, departureTime, arrivalTime y flightIds.",
            "Este bridge usa Playwright para automatizar la página y mantiene un espejo local del dataset oficial para listar resultados filtrados de forma consistente.",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


@mcp.tool()
async def search_flights(
    origin: str,
    destination: str,
    tripType: str = "round-trip",
    outboundDate: str = "2026-04-10",
    inboundDate: str = "2026-04-17",
    passengers: int = 2,
) -> str:
    """Ejecuta una búsqueda de vuelos en el demo oficial."""
    payload = {
        "origin": origin,
        "destination": destination,
        "tripType": tripType,
        "outboundDate": outboundDate,
        "inboundDate": inboundDate,
        "passengers": passengers,
    }
    return json.dumps(await bridge.search_flights(payload), ensure_ascii=False, indent=2)


@mcp.tool()
async def set_flight_filters(
    airlines: Optional[List[str]] = None,
    stops: Optional[List[int]] = None,
    minPrice: Optional[float] = None,
    maxPrice: Optional[float] = None,
    origins: Optional[List[str]] = None,
    destinations: Optional[List[str]] = None,
    departureTime: Optional[List[int]] = None,
    arrivalTime: Optional[List[int]] = None,
    flightIds: Optional[List[int]] = None,
) -> str:
    """Aplica filtros al demo y al espejo local del dataset."""
    payload = {
        "airlines": airlines,
        "stops": stops,
        "minPrice": minPrice,
        "maxPrice": maxPrice,
        "origins": origins,
        "destinations": destinations,
        "departureTime": departureTime,
        "arrivalTime": arrivalTime,
        "flightIds": flightIds,
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    return json.dumps(await bridge.set_filters(payload), ensure_ascii=False, indent=2)


@mcp.tool()
async def reset_flight_filters() -> str:
    """Resetea los filtros del demo."""
    return json.dumps(await bridge.reset_filters(), ensure_ascii=False, indent=2)


@mcp.tool()
async def list_flights(limit: int = 10) -> str:
    """Lista vuelos visibles según la búsqueda actual y filtros aplicados."""
    return json.dumps(await bridge.list_flights(limit=limit), ensure_ascii=False, indent=2)


@mcp.tool()
async def get_current_state() -> str:
    """Devuelve el estado actual del navegador, búsqueda y filtros."""
    return json.dumps(await bridge.get_state(), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    try:
        mcp.run()
    finally:
        try:
            asyncio.run(bridge.close())
        except RuntimeError:
            pass
