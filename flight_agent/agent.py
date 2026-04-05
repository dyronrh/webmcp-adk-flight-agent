from pathlib import Path
from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
#opik

from google.adk.models.lite_llm import LiteLlm
from opik.integrations.adk import OpikTracer, track_adk_agent_recursive
from dotenv import load_dotenv
load_dotenv()

BRIDGE_PATH = Path(__file__).parent / "webmcp_bridge_server.py"



root_agent = Agent(
    name="webmcp_flight_agent",
    model="gemini-2.5-flash",
    description="Agente ADK que automatiza el demo oficial de WebMCP Flight Search.",
    instruction=(
        "Eres un asistente para automatizar el demo oficial de WebMCP Flight Search. "
        "Tu trabajo es usar las tools MCP disponibles para abrir el demo, buscar vuelos, "
        "listar resultados y aplicar filtros. "
        "IMPORTANTE: el demo oficial actualmente solo muestra resultados para "
        "origin=LON, destination=NYC y tripType=round-trip; si el usuario pide otra ruta, "
        "explícalo con claridad y ofrece usar el demo soportado. "
        "Cuando listes vuelos, resume primero los mejores resultados por precio. "
        "Si el usuario pide filtros, usa set_flight_filters. "
        "Si hay dudas, consulta get_demo_capabilities o get_current_state."
    ),
    tools=[
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="python",
                    args=[str(BRIDGE_PATH)],
                )
            )
        )
    ],
)


# Configure Opik tracer
# opik_tracer = OpikTracer(
#     name="basic-flight-agent",
#     tags=["basic", "flight", "time", "single-agent"],
#     metadata={
#         "environment": "development",
#         "model": "gpt-4o",
#         "framework": "google-adk",
#         "example": "basic"
#     },
#     project_name="adk-basic-demo"
# )

# Instrument the agent with a single function call - this is the recommended approach
#track_adk_agent_recursive(root_agent, opik_tracer)