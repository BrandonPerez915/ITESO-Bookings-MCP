# ITESO Bookings Hub - LangChain Agent & MCP Server

Unified intelligent assistant and Model Context Protocol (MCP) server developed in **Python** using **LangChain**, **LangGraph**, and **Playwright**. It automates resource queries, availability checks, and reservations across ITESO's booking systems:

1. 🏸 **Sports Facilities (Microsoft Bookings)**: Tennis, padel, gym, soccer fields, pool, etc.
2. 📚 **Library Study Spaces (Smartway2book)**: Individual study cubicles, group study rooms, and quiet workspaces.
3. 🎥 **Department Materials & Spaces (WebCheckout Patron)**: Video & audio cameras, microphones, lighting kits, photo studios, audio recording booths, and specialized labs.

---

## 🚀 Key Features

- **Unified Multi-Platform Architecture**: Automatically routes queries to the corresponding portal based on the requested resource (e.g., *"Is there a padel court available tomorrow?"* $\rightarrow$ Sports, *"Find an individual cubicle for study"* $\rightarrow$ Library, *"Reserve a camera kit"* $\rightarrow$ WebCheckout).
- **Persistent ITESO SSO & MFA Session**: Log in once interactively with your `@iteso.mx` account and approve Microsoft Authenticator. Sessions, cookies, and tokens persist locally in `user_data/`.
- **LangChain ReAct Agent (`src/agent.py`)**: Conversational agent compatible with Gemini, OpenAI, and Anthropic.
- **FastMCP Server (`src/mcp_server.py`)**: Exposes booking tools to MCP clients such as Claude Desktop, Cursor, or Antigravity.
- **Dry-Run Safety Mode**: Validates reservation details in simulation mode before requesting explicit user confirmation to submit the final booking.

---

## 📁 Project Structure

```
iteso-bookings-mcp/
├── .env.example              # Environment variables template
├── .gitignore
├── requirements.txt          # Project dependencies
├── README.md
├── user_data/                # Local persistent browser profile (ignored by Git)
└── src/
    ├── __init__.py
    ├── config.py             # Portal URLs and student configuration
    ├── browser.py            # Playwright browser manager with persistent profile
    ├── bookings_service.py   # Unified facade service coordinating all platforms
    ├── tools.py              # Unified LangChain @tool definitions
    ├── agent.py              # Multi-platform conversational ReAct agent
    ├── mcp_server.py         # FastMCP Server exposing multi-platform tools
    ├── test.py               # Platform connectivity and session test script
    └── platforms/
        ├── __init__.py       # Platform exports
        ├── base.py           # BaseBookingPlatform abstract interface
        ├── sports.py         # Microsoft Bookings adapter (Sports)
        ├── library.py        # Smartway2book adapter (Library Cubicles)
        ├── departments.py    # WebCheckout Patron adapter (Gear & Labs)
        └── registry.py       # Central platform registry and auto-detection engine
```

---

## 🛠️ Installation and Setup

### 1. Navigate to the project directory
```bash
cd iteso-bookings-mcp
```

### 2. Set up virtual environment and install dependencies
Using `uv`:
```bash
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
playwright install chromium
```

Or using standard `pip`:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### 3. Configure environment variables
Copy the template:
```bash
cp .env.example .env
```
Fill in `.env`:
```ini
GEMINI_API_KEY="your_gemini_api_key"
STUDENT_NAME="Your Full Name"
STUDENT_EMAIL="your.email@iteso.mx"
STUDENT_ID="123456"
STUDENT_PHONE="3312345678"
```

---

## 🔑 ITESO Authentication (MFA)

Because ITESO uses Microsoft Entra ID single sign-on with two-factor authentication (MFA):

You can trigger login via the agent or test script:
```bash
python -m src.test
```
A visible browser window will open. Enter your `@iteso.mx` email, password, and approve the Microsoft Authenticator notification. The session will be saved in `user_data/` and shared across all platforms.

---

## 💬 Mode 1: Conversational Agent

Run the conversational agent in terminal:

```bash
python -m src.agent
```

**Example queries:**
- *"What platforms and resources can I book?"*
- *"Check if a tennis court is available tomorrow morning"*
- *"Are there individual cubicles free at the library for today at 3 PM?"*
- *"Reserve a video camera kit for Friday at 09:00"*

---

## 🔌 Mode 2: MCP Server (Model Context Protocol)

Test with MCP Inspector:
```bash
mcp dev src/mcp_server.py
```

Or configure in Claude Desktop / Cursor (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "iteso-bookings": {
      "command": "/absolute/path/to/iteso-bookings-mcp/.venv/bin/python",
      "args": ["-m", "src.mcp_server"],
      "cwd": "/absolute/path/to/iteso-bookings-mcp",
      "env": {
        "PYTHONPATH": "/absolute/path/to/iteso-bookings-mcp"
      }
    }
  }
}
```
