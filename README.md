# Daily Digest Tool - Project-Phase Filtering System

A smart digest system that filters Slack messages based on your relationship to projects. Messages automatically phase out as you complete projects, without needing to track everyone else's patterns.

## Architecture

The system implements the architecture described in [class-summary.md](class-summary.md):

- **Project-Phase Filtering**: Messages filtered based on your project involvement
- **Automatic Phase Detection**: Projects transition between active/review/done based on your activity
- **Smart Ranking**: Relevance scoring based on recency, urgency, and project phase
- **Anomaly Detection**: Re-activates "done" projects when you're mentioned
- **AI-Powered Summaries**: OpenAI-generated summaries for each project group with expandable details

## Project Structure

```
EverCurrent/
├── src/                          # Core implementation
│   ├── models.py                 # Data models (dataclasses)
│   ├── storage.py                # Data persistence layer
│   ├── project_extractor.py     # Project identification
│   ├── project_state_manager.py # Phase transitions & anomaly detection
│   ├── ranking.py                # Relevance scoring
│   ├── digest_generator.py      # Digest creation
│   ├── digest_pipeline.py       # Main orchestration pipeline
│   └── generate_mock_data.py    # Mock data generator
├── web/                          # Flask web UI
│   ├── app.py                    # Flask application
│   ├── templates/                # HTML templates
│   │   ├── index.html
│   │   └── digest.html
│   └── static/
│       └── style.css
├── data/                         # JSON data storage
│   ├── projects.json             # Project definitions
│   ├── users.json                # User information
│   ├── messages.json             # Mock Slack messages
│   ├── user_project_states.json  # User-project relationships
│   └── digests/                  # Generated digests
├── test_pipeline.py              # Pipeline test script
├── run_web_ui.py                 # Web UI launcher
└── requirements.txt              # Python dependencies
```

## Setup

### 1. Create and activate virtual environment (already exists)

```bash
# Virtual environment is already set up at ./venv
source venv/bin/activate  # On macOS/Linux
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Generate mock data (already done)

Mock data has been pre-generated with 3 projects, 10 users, and ~75 messages:

- **Projects**: PCB Redesign, Motor Assembly, Firmware Update
- **Users**: Engineers, PM, Engineering Lead
- **Messages**: Mix of updates, blockers, urgent items, and casual chat

To regenerate:
```bash
python src/generate_mock_data.py
```

## Usage

### Option 1: Web UI (Recommended)

Start the web server:

```bash
./venv/bin/python3 run_web_ui.py
```

Then open your browser to: **http://127.0.0.1:5001**

1. Select a user from the dropdown
2. Click "Generate Digest"
3. View the organized digest with urgent/active/review sections

### Option 2: Command Line

Test the digest pipeline directly:

```bash
./venv/bin/python3 test_pipeline.py
```

### Option 3: Python API

```python
from src.digest_pipeline import DigestPipeline

pipeline = DigestPipeline()
digest = pipeline.generate_digest("alice", hours_back=24)

print(f"Urgent: {len(digest.urgent)}")
print(f"Active: {len(digest.active)}")
print(f"Review: {len(digest.review)}")
```

## How It Works

### 1. Message Collection
- Loads messages from the past 24 hours
- Extracts metadata (sender, channel, mentions, urgency)

### 2. Project Extraction
- Matches messages to projects via channel or keywords
- Handles DMs by content analysis

### 3. State Management
- Updates user-project states based on activity
- Detects phase transitions (active → review → done)
- Checks for anomalies (mentions, urgent items)

### 4. Filtering & Ranking
- **Done projects**: Filtered out (score = 0)
- **Blocked projects**: Only show blocker messages
- **Active projects**: Full visibility, high priority
- **Review projects**: Summarized, medium priority

### 5. Relevance Scoring

```
score = recency × urgency_boost × mention_boost × activity_boost

Phase adjustments:
- Review: score × 0.5
- Done: score = 0
- Blocked: score = 0.1 (unless is_blocker)
```

### 6. Digest Generation
Groups ranked messages by project with AI summaries:
- 🚨 **Urgent**: Blockers and time-sensitive items
- 📌 **Active Projects**: High-priority active work
- 📋 **Review**: Lower-priority monitoring items

Each project group displays:
- **AI-generated summary** of all messages (powered by OpenAI GPT-4o-mini)
- **Click-to-expand** interface to view individual messages
- Message count and sender information

## AI-Powered Summaries

The digest now features intelligent summarization:

### How It Works

1. **Project Grouping**: Messages are grouped by project within each section
2. **AI Summary**: OpenAI generates a concise 1-2 sentence summary for each project
3. **Expandable Details**: Click any project to see individual messages
4. **Fallback Mode**: Works without API key using simple summaries

### Enabling AI Summaries

To use OpenAI-powered summaries, set your API key:

```bash
export OPENAI_API_KEY='your-openai-api-key'
```

Without an API key, the system uses simple summaries showing:
- Number of messages and senders
- Count of blockers and urgent items
- Sample of the first message

### Testing AI Summaries

```bash
# Test with AI summaries (if API key is set)
./venv/bin/python3 test_ai_summaries.py
```

## Sample Users

Test with these users to see different perspectives:

- **alice** (Electrical Engineer) - Active on PCB Redesign
- **bob** (Electrical Engineer) - Active on PCB, reviews Firmware
- **david** (Mechanical Engineer) - Active on Motor Assembly
- **ivan** (PM) - Monitors all projects (mixed phases)
- **julia** (Engineering Lead) - Active on all projects

## Key Features

### Automatic Phase Detection
```
Active: 3+ messages/week → high visibility
Review: 1-2 messages/week → summaries only
Done: No activity for 2+ weeks → filtered out
```

### Anomaly Re-activation
Done projects come back to "review" when:
- You're @mentioned
- Urgent/blocker message appears
- Someone replies to your thread

### Smart Ranking
- Temporal decay (8-hour half-life)
- Urgency boost (×1.5)
- Mention boost (×1.8)
- Activity boost (up to ×1.5)

## Files Created

### Core Components
- ✅ [src/models.py](src/models.py) - Data models
- ✅ [src/storage.py](src/storage.py) - JSON storage layer
- ✅ [src/project_extractor.py](src/project_extractor.py) - Project identification
- ✅ [src/project_state_manager.py](src/project_state_manager.py) - Phase management
- ✅ [src/ranking.py](src/ranking.py) - Relevance scoring
- ✅ [src/digest_generator.py](src/digest_generator.py) - Digest creation
- ✅ [src/digest_pipeline.py](src/digest_pipeline.py) - Main pipeline

### Web Interface
- ✅ [web/app.py](web/app.py) - Flask application
- ✅ [web/templates/index.html](web/templates/index.html) - Home page
- ✅ [web/templates/digest.html](web/templates/digest.html) - Digest view
- ✅ [web/static/style.css](web/static/style.css) - Styling

### Testing & Utilities
- ✅ [test_pipeline.py](test_pipeline.py) - Pipeline tests
- ✅ [run_web_ui.py](run_web_ui.py) - Web UI launcher

## Next Steps (Production)

For a production deployment:

1. **Real Slack Integration**: Replace mock data with Slack API
2. **Database**: Switch from JSON to PostgreSQL/SQLite
3. **LLM Integration**: Add Claude for better summarization
4. **User Authentication**: Add login system
5. **Cron Jobs**: Schedule daily digest generation
6. **Email/Slack Delivery**: Send digests to users
7. **User Controls**: Let users override phase assignments
8. **Analytics**: Track digest engagement

## Architecture Decision

This system focuses on **your project lifecycle** rather than building complex graphs of all users. Messages naturally phase out as you complete projects, providing a simple and effective filtering mechanism.

See [class-summary.md](class-summary.md) for complete architecture details.
