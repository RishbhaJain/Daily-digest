# Class Architecture Summary

## Core Concept: Project-Phase Filtering

Messages are filtered/ranked based on **your relationship to projects**. If you're done with a project, messages from that project phase out automatically.

---

## 1. UserProjectState (dataclass)
**Purpose**: Track a user's involvement phase in a project.

| Fields | Type | Description |
|--------|------|-------------|
| `user_id` | str | User identifier |
| `project_id` | str | Project identifier |
| `phase` | str | "active", "review", "done", "blocked" |
| `channels` | List[str] | Channels/threads associated with this project |
| `last_contributed` | datetime | When user last posted/reacted |
| `messages_past_week` | int | User's message count in this project (last 7 days) |

**Phase meanings**:
- `active` → Show all messages, high priority
- `review` → Show summaries only, medium priority
- `done` → Filter out or minimal visibility
- `blocked` → Show blocker-related messages only

---

## 2. Project (dataclass)
**Purpose**: Define a project and its associated channels/keywords.

| Fields | Type | Description |
|--------|------|-------------|
| `project_id` | str | Unique identifier |
| `name` | str | Display name |
| `channels` | List[str] | Slack channels for this project |
| `keywords` | List[str] | Terms for semantic matching |

**Source**: Seeded manually or inferred from Slack channel naming patterns.

**Example**:
```
Project(
    project_id="pcb-redesign",
    name="PCB Redesign",
    channels=["#pcb-review", "#electrical"],
    keywords=["PCB", "circuit", "layout", "schematic"]
)
```

---

## 3. Message (dataclass)
**Purpose**: Represents a Slack message with extracted metadata.

| Fields | Type | Description |
|--------|------|-------------|
| `id` | str | Message identifier |
| `channel` | Optional[str] | Channel name (None if DM) |
| `thread_id` | Optional[str] | Thread identifier (if in thread) |
| `sender` | str | Who sent it |
| `text` | str | Message content |
| `timestamp` | datetime | When sent |
| `mentions` | List[str] | Users @mentioned |
| `is_dm` | bool | True if direct message |
| `is_urgent` | bool | Contains urgency signals (ASAP, urgent, etc.) |
| `is_blocker` | bool | Identified as a blocker |

**Urgency/blocker detection** (via LLM or keyword matching):
- `is_urgent`: "ASAP", "urgent", "need by EOD", etc.
- `is_blocker`: "blocked", "waiting on", "can't proceed", etc.

---

## 4. ProjectStateManager
**Purpose**: Manage phase transitions and detect anomalies that re-activate projects.

| Functions | Description |
|-----------|-------------|
| `detect_phase(project_state, user_messages)` | Infer phase from activity patterns |
| `check_anomalies(project_state, new_messages)` | Detect triggers that re-activate closed projects |
| `transition(project_state, new_phase)` | Apply state transition |
| `create_state(user_id, project_id, trigger_message)` | Initialize state for new project |

**Phase detection logic**:
1. If `last_contributed` > 2 weeks ago → "done"
2. If `messages_past_week` == 0 and was "active" → "review"
3. Else, LLM analyzes message content for signals

**New project initialization**:
- If you're @mentioned → start as "active"
- If you sent a message → start as "active"
- If just observing → start as "review"

**Anomaly triggers** (re-activate "done" → "review"):
- You're @mentioned in the project
- You're tagged in a thread you previously participated in
- Blocker message references your past work
- Someone replies to your old message

**State transitions**:
```
active ←→ review ←→ done
   ↓         ↓
blocked ←────┘

Anomaly can jump: done → review
```

User override always wins.

---

## 5. ProjectExtractor
**Purpose**: Identify which project a message belongs to.

| Variables | Type | Description |
|-----------|------|-------------|
| `projects` | List[Project] | All known projects |

| Functions | Description |
|-----------|-------------|
| `extract_project(message)` | Returns project_id from channel, thread, or content |

**Extraction logic**:
1. Channel match → if message.channel in any project.channels, return that project
2. Thread match → if thread name contains project.name
3. Semantic match → check message against project.keywords, or LLM fallback

**DM handling**:
DMs don't have a channel, so:
1. LLM reads DM content and tries to match to existing project
2. If matches project → associate with that project
3. If personal (promotion, 1:1, career, etc.) → create/use "personal" project
4. If unclear → create new project based on DM topic

**Personal project**:
```
Project(
    project_id="personal",
    name="Personal",
    channels=[],
    keywords=["promotion", "1:1", "career", "feedback", "review"]
)
```
Auto-created per user. Phase is always "review" (summarized, not urgent unless @mentioned).

---

## 6. Digest Pipeline

```
1. Fetch messages from past 24h
2. Load user's project states: List[UserProjectState]

3. Run state updates (before filtering):
   a. For each project_state:
      - detect_phase() → update if activity patterns changed
   b. For each message:
      - check_anomalies() → re-activate done projects if triggered

4. For each message:
   a. Extract project → project_extractor.extract_project(message)
   b. Find matching UserProjectState (or create_state() if new project)
   c. Apply phase filter:
      - done:    skip
      - blocked: skip (unless message.is_blocker)
      - active/review: compute relevance score

5. Rank remaining messages by relevance score
6. Generate digest
7. Persist updated project states
```

---

## 7. Ranking Function

```python
def compute_relevance(message, project_state: UserProjectState):
    if not project_state:
        return 0.3  # Unknown project, low priority

    # Phase gate
    if project_state.phase == "done":
        return 0.0
    if project_state.phase == "blocked" and not message.is_blocker:
        return 0.1

    # Compute relevance
    recency_score = temporal_decay(message.timestamp)
    urgency_boost = 1.5 if message.is_urgent else 1.0
    activity_boost = min(1.0 + (project_state.messages_past_week * 0.05), 1.5)

    final = recency_score * urgency_boost * activity_boost

    if project_state.phase == "review":
        final *= 0.5

    return final
```

---

## 8. DigestGenerator
**Purpose**: Transform ranked messages into a readable digest.

| Functions | Description |
|-----------|-------------|
| `generate(ranked_messages, user_id)` | Produces final digest output |

**Output structure**:
```
Digest:
  - generated_at: datetime
  - user_id: str
  - sections:
      - urgent: List[DigestItem]     # is_blocker or is_urgent
      - active: List[DigestItem]     # from active projects
      - review: List[DigestItem]     # from review projects (summarized)
```

**DigestItem**:
| Field | Type | Description |
|-------|------|-------------|
| `message_id` | str | Link back to original |
| `project_id` | str | Which project |
| `summary` | str | LLM-generated 1-liner |
| `relevance_score` | float | Why it ranked here |

**Generation logic**:
1. Group ranked messages by section (urgent/active/review)
2. For `active` projects: show individual messages
3. For `review` projects: LLM summarizes multiple messages into 1-2 lines
4. Cap total items (e.g., 20 max)

---

## 9. Storage (Local JSON)
**Purpose**: Persist data between runs. Local JSON files for prototype.

**Files**:
```
data/
├── projects.json          # List[Project]
├── messages.json          # List[Message] (mock data)
├── user_project_states.json   # List[UserProjectState]
└── digests/
    └── {user_id}_{date}.json  # Generated digests
```

**Storage class**:

| Functions | Description |
|-----------|-------------|
| `load_projects()` | Returns List[Project] |
| `load_messages(since: datetime)` | Returns messages from last N hours |
| `load_user_states(user_id)` | Returns List[UserProjectState] for user |
| `save_user_states(states)` | Persist updated states |
| `save_digest(digest)` | Save generated digest |

**Example structure**:

`projects.json`:
```json
[
  {
    "project_id": "pcb-redesign",
    "name": "PCB Redesign",
    "channels": ["#pcb-review", "#electrical"],
    "keywords": ["PCB", "circuit", "layout"]
  }
]
```

`user_project_states.json`:
```json
[
  {
    "user_id": "alice",
    "project_id": "pcb-redesign",
    "phase": "active",
    "channels": ["#pcb-review", "#electrical"],
    "last_contributed": "2024-01-15T10:30:00Z",
    "messages_past_week": 12
  }
]
```

**Note**: In production, replace with Postgres/SQLite + proper migrations.

---

## 10. Web UI (Flask)
**Purpose**: Simple HTML interface to view digests per user.

**Routes**:
| Route | Description |
|-------|-------------|
| `GET /` | Home page with user dropdown |
| `GET /digest?user_id=X` | Generate and display digest for user X |

**Page layout**:
```
┌─────────────────────────────────────────┐
│  Daily Digest                           │
│  User: [Dropdown ▼]  [Generate]         │
├─────────────────────────────────────────┤
│  🚨 Urgent (2)                          │
│  ├─ PCB layout blocked - waiting on...  │
│  └─ URGENT: Motor test failing...       │
├─────────────────────────────────────────┤
│  📌 Active Projects (5)                 │
│  ├─ [PCB-Redesign] Schematic review...  │
│  ├─ [PCB-Redesign] New component spec...|
│  └─ ...                                 │
├─────────────────────────────────────────┤
│  📋 Review (summarized) (3)             │
│  └─ [Motor-Assembly] 4 updates: testing │
│     complete, moving to integration...  │
└─────────────────────────────────────────┘
```

**Implementation**:
- Flask app with Jinja2 templates
- Single `app.py` with 2 routes
- `templates/index.html` - dropdown + digest display
- Calls digest pipeline on demand when user selects

**Files**:
```
web/
├── app.py
├── templates/
│   └── index.html
└── static/
    └── style.css
```

---

## 11. MockDataGenerator
**Purpose**: Generate realistic test data for development/demo.

**Data to generate**:

| Data | Count |
|------|-------|
| Projects | 3 |
| Users | 10 |
| Messages | 50-100 (across 24h) |
| Channels | ~6 (2 per project) |

**Projects**:
```
1. PCB-Redesign    → #pcb-review, #electrical
2. Motor-Assembly  → #mechanical, #motor-debug
3. Firmware-Update → #firmware, #embedded
```

**Users** (10):
- 3 electrical engineers (focus: PCB)
- 3 mechanical engineers (focus: Motor)
- 2 firmware engineers (focus: Firmware)
- 1 PM (all projects, review phase)
- 1 engineering lead (all projects, active)

**Message types**:
- `blocker`: "Blocked on X - waiting for Y"
- `urgent`: "URGENT: need X by EOD"
- `update`: "Finished X, ready for review"
- `question`: "What's the status on X?"
- `fyi`: "FYI - X is now available"

**Timestamp distribution** (24h):
- 60% work hours (9am-6pm)
- 40% outside hours

**UserProjectState per user**:
- Primary project → "active"
- Secondary project → "review"
- Third project → "done" or no association

---

## Removed from Original Plan

- ~~UserMessageGraph~~ — Not tracking other users
- ~~UserTopicNode~~ — Not tracking other users' posting patterns
- ~~user_urgency_credibility~~ — Not evaluating other users
- ~~collaboration_network~~ — Simplified out
- ~~topic_authorities~~ — Not needed
- ~~Interaction~~ — Redundant with project_states activity tracking
- ~~interest_profile~~ — Redundant with project_states
- ~~channel_preferences~~ — Channels already mapped to projects
- ~~UserContext~~ — Redundant wrapper, use UserProjectState directly

---

## Key Insight

Instead of building a complex graph of all users and their patterns, we focus on **your project lifecycle**. Messages naturally phase out as you complete projects, without needing to track everyone else.
