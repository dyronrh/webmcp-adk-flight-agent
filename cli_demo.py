import asyncio
import os

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.genai import types

from flight_agent.agent import root_agent


async def main() -> None:
    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()

    session = await session_service.create_session(
        app_name="webmcp_flight_agent_app",
        user_id="local-user",
        state={},
    )

    runner = Runner(
        app_name="webmcp_flight_agent_app",
        agent=root_agent,
        session_service=session_service,
        artifact_service=artifact_service,
    )

    prompt = os.getenv(
        "DEMO_PROMPT",
        (
            "Abre el demo oficial, busca vuelos de LON a NYC para ida y vuelta "
            "con 2 pasajeros, lista los 5 más baratos y luego filtra solo vuelos "
            "sin escalas por debajo de 600 USD."
        ),
    )

    message = types.Content(role="user", parts=[types.Part(text=prompt)])

    async for event in runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=message,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                text = getattr(part, "text", None)
                if text:
                    print(text)


if __name__ == "__main__":
    asyncio.run(main())
