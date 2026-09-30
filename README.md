# UX Studio

A multi-agent design synthesis platform utilizing a Blackboard architectural pattern to orchestrate autonomous frontend agents across five AI frameworks: **Agno**, **Google ADK**, **Strands**, **Mastra**, and **MAF**.

---

## Architecture Overview

UX Studio separates campaign orchestration from variant synthesis using an SQLite-backed blackboard:

1. **Orchestrator**: Deconstructs campaign goals, personas, design systems, and value propositions into discrete tasks written to `data/blackboard.db`.
2. **Worker Pool**: Five framework workers independently poll the blackboard, claim pending jobs with atomic locking, synthesize single-file responsive HTML, and report execution telemetry.
3. **Viewer Interface**: A live preview dashboard allowing side-by-side inspection, status tracking, and deliverable exports.

---

## Project Structure

```text
.
├── .github
│   └── workflows
│       ├── lint.yaml                  # Automated ruff static analysis
│       └── test.yaml                  # Pytest runner with mock offline env
├── data
│   └── blackboard.db                  # SQLite blackboard state store
├── db
│   ├── __init__.py
│   └── database.py                    # Schema initialization & task persistence
├── orchestrator
│   ├── __init__.py
│   ├── orchestrator.py                # Blackboard campaign task dispatcher
│   └── prompt_templates.py            # Framework persona & brief prompt definitions
├── tests
│   ├── conftest.py
│   ├── e2e
│   │   └── test_full_studio_loop.py
│   ├── integration
│   │   ├── test_concurrency.py
│   │   └── test_worker_lifecycle.py
│   └── unit
│       ├── test_database.py
│       ├── test_orchestrator.py
│       ├── test_sanitizer.py
│       └── test_workers.py
├── utils
│   ├── __init__.py
│   ├── logger.py                      # Centralized UX Studio logging
│   └── sanitizer.py                   # Markdown fence & HTML payload cleanup
├── viewer
│   └── app.py                         # Live blackboard preview UI
├── workers
│   ├── __init__.py
│   ├── base_worker.py                 # Abstract polling worker, lifecycle & validation
│   ├── mastra_agent.js                # Node runtime harness for Mastra worker
│   ├── worker_agno.py                 # Agno agent integration
│   ├── worker_google_adk.py           # Google ADK agent integration
│   ├── worker_maf.py                  # Microsoft AutoGen (MAF) integration
│   ├── worker_mastra.py               # Python-to-JS bridge for Mastra
│   └── worker_strands.py              # Strands framework agent integration
├── .gitignore
├── package.json
├── package-lock.json
├── pytest.ini
├── requirements.txt
└── run_studio.py                      # Multi-threaded background worker orchestrator

```

## Prerequisites

- **Python**: `3.10+` (tested on `3.11`)
- **Node.js**: `v18.0.0+` (required for Mastra agent execution)
- **npm** or **pnpm**

---

## Installation & Setup

### 1. Clone & Enter Repository
```bash
git clone <your-repo-url>
cd ux-studio
```

### 2. Python Virtual Environment Setup
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Node Dependencies Setup
Mastra relies on a local Node runtime bridge:
```bash
npm install
```

### 4. Environment Configuration
Create a `.env` file in the project root:
```bash
cp .env.example .env
```

Add your API credentials:
```env
OPENAI_API_KEY=your_openai_api_key
GOOGLE_API_KEY=your_gemini_api_key
GEMINI_API_KEY=your_gemini_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### 5. Initialize the Blackboard Database
Ensure the `data/` and `outputs/` directories exist and seed the SQLite tables:
```bash
python -c "from db.database import init_db; init_db()"
```

---

## Running UX Studio

UX Studio follows a decoupled Blackboard architecture: the worker runtime and the UI dashboard run simultaneously in separate terminal sessions.

### Step 1: Start Worker Runtime & Orchestrator (Terminal 1)
Launches the worker orchestrator to continuously poll `blackboard.db` and synthesize variants across all 5 framework agents:
```bash
source .venv/bin/activate
python run_studio.py
```

### Step 2: Launch the Live Dashboard (Terminal 2)
In a second terminal window, launch the Streamlit frontend to dispatch campaigns, monitor task state transitions, and preview variants live:
```bash
source .venv/bin/activate
streamlit run viewer/app.py
```

---

## Testing & Quality Assurance

### Run Unit and Lifecycle Tests (Offline)
Tests execute against in-memory SQLite instances and simulated mock workers without live LLM calls:
```bash
pytest tests/ -v
```

### Run Static Analysis
```bash
ruff check .
```

## CI/CD Pipeline

Automated checks run on every pull request and push to `main` via GitHub Actions:

- **Lint Workflow (`lint.yaml`)**: Executes static code analysis with `ruff` to enforce formatting and syntax correctness.
- **Test Workflow (`test.yaml`)**: Executes the unit and concurrent worker lifecycle test suites in a mock environment using in-memory SQLite instances (`:memory:`). Live API credentials are not required to run automated CI checks.