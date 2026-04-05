# WebMCP Flight Agent Pro

Este proyecto es un agente automatizado basado en el [Google ADK (Agent Development Kit)](https://github.com/google/adk) que utiliza el [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) para interactuar con un demo oficial de búsqueda de vuelos a través de [Playwright](https://playwright.dev/).

El agente puede realizar búsquedas, listar resultados y aplicar filtros directamente en la interfaz web del demo, resumiendo la información para el usuario.

## Requisitos Previos

- **Python 3.10+**
- **Clave de API de Gemini**: Para el razonamiento del agente.
- **Node.js** (opcional, para herramientas MCP externas si fuera necesario)
- **Playwright Browsers**: Necesarios para la automatización del navegador.

## Estructura del Proyecto

- `flight_agent/agent.py`: Define el agente principal, sus instrucciones y las herramientas MCP que utiliza.
- `flight_agent/webmcp_bridge_server.py`: Un servidor bridge utilizando `FastMCP` que expone herramientas para controlar Playwright.
- `cli_demo.py`: Script de entrada para ejecutar una demostración del agente desde la línea de comandos.
- `.env`: Archivo de configuración para variables de entorno (claves de API, URLs, etc.).

## Instalación Local

1.  **Clonar el repositorio** (o navegar a la carpeta del proyecto).

2.  **Crear y activar un entorno virtual**:
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # En Windows: .venv\Scripts\activate
    ```

3.  **Instalar las dependencias**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Instalar los navegadores de Playwright**:
    ```bash
    playwright install chromium
    ```

## Configuración

Copia el archivo `.example.env` a `.env` y completa la información necesaria:

Las implementación de OPIK estan comentadas en el codigo solo si quieres monitorear el agente necesitas una cuenta en opik y agregar las credenciales al .env 


```bash
cp .example.env .env
```

Asegúrate de configurar al menos:
- `GEMINI_API_KEY`: Tu clave de Google AI Studio.
- `WEBMCP_FLIGHTSEARCH_URL`: La URL del demo (por defecto ya está configurada).

## Ejecución

Para ejecutar el demo del agente, simplemente corre el script `cli_demo.py`:

```bash
python cli_demo.py
```

### Comportamiento del Demo
El script `cli_demo.py` por defecto enviará un prompt al agente para:
1. Abrir el demo oficial.
2. Buscar vuelos de Londres (LON) a Nueva York (NYC).
3. Listar los 5 más baratos.
4. Filtrar por vuelos sin escalas de menos de 600 USD.

**Nota Importante:** El demo oficial del sitio web actualmente solo devuelve resultados visibles para la ruta **LON -> NYC** con **tripType=round-trip**. Si pides otras rutas, el agente te lo notificará.

## Integración con Opik (Opcional)

Este proyecto tiene soporte preliminar para [Opik](https://www.comet.com/opik) para el rastreo y observabilidad de los agentes. Puedes habilitar la configuración en `.env` y descomentar las líneas correspondientes en `flight_agent/agent.py`.

## Tecnologías Utilizadas

- **Google ADK**: Framework para la creación de agentes.
- **MCP (Model Context Protocol)**: Estándar para conectar modelos con herramientas.
- **Playwright**: Automatización de navegador para interactuar con aplicaciones web modernas.
- **FastMCP**: Librería para crear servidores MCP de forma rápida.
- **LiteLLM**: Para la integración con diversos modelos de lenguaje.
