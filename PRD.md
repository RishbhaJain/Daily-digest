# Product Requirements Document: EverCurrent Daily Digest Tool

## 1. Product Overview

A personalized daily digest system that surfaces relevant Slack messages for hardware engineering teams based on individual project involvement and changing priorities.

**Core Insight**: Instead of tracking all team communication, filter messages based on each user's project lifecycle phase. As users complete projects, messages from those projects automatically phase out.

---

## 2. Problem Statement

Hardware engineering teams at robotics companies face critical communication challenges:

- **Knowledge silos**: Important updates buried in Slack threads
- **Role-specific priorities**: Mechanical engineers, electrical engineers, supply chain, PMs, and engineering managers need different information
- **Shifting focus**: As projects progress from active development → review → completion, individuals need different levels of detail
- **Information overload**: Teams can't stay aligned on execution without manually filtering hundreds of messages

---

## 3. Target Users

**Primary**: Robotics hardware engineering teams
- Mechanical engineers
- Electrical engineers
- Supply chain specialists
- Engineering managers
- Product managers

**User Characteristics**:
- Works on 2-5 concurrent projects
- Project involvement changes over weeks/months
- Needs urgent blockers surfaced immediately
- Wants summaries for projects in review phase
- Doesn't want noise from completed projects

---

## 4. Goals & Success Metrics

### Goals
1. Surface the right information to the right person at the right time
2. Reduce time spent manually filtering Slack messages
3. Keep team aligned on execution across project phases
4. Automatically adapt to changing project priorities

### Success Metrics
- Time saved per user per day (target: 30+ minutes)
- Percentage of urgent/blocker messages surfaced within digest (target: 95%+)
- User satisfaction with digest relevance (target: 4/5+)
- Reduction in "missed critical update" incidents

---

## 5. Core Features

### 5.1 Project-Phase Tracking
Automatically track each user's relationship to projects through 4 phases:

| Phase | Definition | Digest Behavior |
|-------|-----------|-----------------|
| **Active** | Actively contributing | Show all messages, high priority |
| **Review** | Monitoring, not contributing | Show summaries only |
| **Done** | Completed work | Filter out completely |
| **Blocked** | Waiting on dependencies | Show blocker-related messages only |

**Phase Detection Logic**:
- Last contributed >2 weeks ago → "done"
- Zero messages past week from "active" → "review"
- User @mentioned or sends message → "active"
- LLM analyzes message patterns for phase signals

**Anomaly Re-activation**: Automatically move "done" → "review" when:
- User is @mentioned in that project
- Someone replies to user's old message
- Blocker references user's past work

### 5.2 Smart Message Classification

Extract metadata from each Slack message:
- **Project association**: Match via channel, thread name, or semantic content
- **Urgency detection**: Keywords like "ASAP", "urgent", "need by EOD"
- **Blocker detection**: "blocked", "waiting on", "can't proceed"
- **Mentions**: Direct @mentions of user
- **Thread context**: Track thread participation history

### 5.3 Relevance Ranking

Compute relevance score per message based on:
```
score = recency × urgency_boost × activity_boost × phase_multiplier

Where:
- recency: Temporal decay from timestamp
- urgency_boost: 1.5x if is_urgent, else 1.0
- activity_boost: 1.0 + (messages_past_week × 0.05), capped at 1.5
- phase_multiplier:
    - active: 1.0
    - review: 0.5
    - blocked: 0.1 (unless message.is_blocker)
    - done: 0.0 (filtered out)
```

### 5.4 Personalized Digest Generation

Daily digest structured as:

```
🚨 URGENT (blockers, urgent mentions)
  └─ Individual messages with full context

📌 ACTIVE PROJECTS
  └─ Individual messages from active projects

📋 REVIEW (summarized)
  └─ LLM-generated summaries (4 updates → 1-2 lines)
```

**Output caps**: Max 20 items per digest to prevent overload

### 5.5 Project Discovery

Automatically identify projects through:
- **Channel mapping**: Slack channels → projects (e.g., #pcb-review → PCB-Redesign)
- **Thread analysis**: Thread names containing project keywords
- **Semantic matching**: LLM classifies messages by content
- **Personal project**: Auto-created per user for 1:1s, career discussions, feedback

### 5.6 DM Handling

Direct messages require special logic:
1. LLM reads DM content
2. Match to existing project if work-related
3. If personal (promotion, career, 1:1) → route to "Personal" project
4. If unclear → create new project based on topic

---

## 6. User Stories

### As a Mechanical Engineer:
- I want blocker messages about my motor assembly work surfaced immediately
- I want summaries of PCB project updates (I contributed last month but it's not my focus now)
- I don't want messages from the firmware project I finished 3 weeks ago

### As an Engineering Manager:
- I want to see all blocker messages across projects
- I want summaries of projects in execution that I'm monitoring
- I want to be re-notified if someone @mentions me in an old project

### As a Supply Chain Specialist:
- I want urgent procurement requests highlighted
- I want updates only from projects where parts are being ordered
- I don't want noise from projects I handed off to manufacturing

---

## 7. Technical Requirements

### 7.1 Data Models

**Core Classes**:
- `UserProjectState`: Track user's phase per project
- `Project`: Define projects with channels and keywords
- `Message`: Slack message with extracted metadata
- `ProjectStateManager`: Manage phase transitions and anomaly detection
- `ProjectExtractor`: Map messages → projects
- `DigestGenerator`: Transform ranked messages → readable output

### 7.2 Pipeline Architecture

```
1. Fetch messages (past 24h from Slack API)
2. Load user project states
3. Update states:
   - detect_phase() for all projects
   - check_anomalies() for done projects
4. For each message:
   - Extract project association
   - Find/create UserProjectState
   - Apply phase filter
   - Compute relevance score
5. Rank messages by score
6. Generate digest (group by urgent/active/review)
7. Persist updated states
```

### 7.3 Storage (MVP)

Local JSON files:
- `projects.json`: List of known projects
- `messages.json`: Mock Slack data
- `user_project_states.json`: Phase tracking per user
- `digests/{user_id}_{date}.json`: Generated digests

**Future**: Migrate to Postgres/SQLite with proper migrations

### 7.4 Web UI

Simple Flask app:
- **Route 1**: `GET /` - User selection dropdown
- **Route 2**: `GET /digest?user_id=X` - Generate and display digest
- **Template**: Single HTML page with urgent/active/review sections

---

## 8. User Overrides

Users can manually override phase detection:
- Mark project as "done" even if still receiving messages
- Mark project as "active" to force-include updates
- **Rule**: User override always wins over automatic detection

---

## 9. Out of Scope (V1)

The following features are explicitly excluded from initial release:

- ❌ Tracking other users' posting patterns
- ❌ User credibility scoring
- ❌ Collaboration network graphs
- ❌ Topic authority ranking
- ❌ Real-time notifications (digest is daily only)
- ❌ Mobile app (web UI only)
- ❌ Integration with tools beyond Slack
- ❌ Team-wide analytics dashboard

**Rationale**: Focus on individual user's project lifecycle, not modeling entire team dynamics

---

## 10. Open Questions

1. **Delivery timing**: What time should daily digest be delivered? (Proposal: 8am local time)
2. **LLM provider**: Which LLM for phase detection and summarization? (OpenAI vs Anthropic)
3. **User onboarding**: Should users manually tag initial project phases, or bootstrap from Slack history?
4. **Digest frequency**: Daily only, or allow users to request on-demand?
5. **Thread depth**: Should we include replies-to-replies, or just top-level thread messages?

---

## 11. Implementation Phases

### Phase 1: MVP (Prototype)
- Mock data generator (3 projects, 10 users, 50-100 messages)
- Core pipeline with local JSON storage
- Basic Flask UI
- Manual project seeding

### Phase 2: Slack Integration
- Real Slack API integration
- Automatic project discovery from channels
- OAuth for multi-user authentication

### Phase 3: Intelligence Layer
- LLM-based phase detection
- Semantic project matching for DMs
- Smart summarization for review projects

### Phase 4: Production Ready
- Database migration (Postgres)
- Scheduled digest delivery (email/Slack DM)
- User preference controls
- Analytics and feedback loop

---

## 12. Success Criteria for MVP

The MVP is successful if:

1. ✅ Digest correctly filters out messages from "done" projects
2. ✅ Urgent/blocker messages always appear in top section
3. ✅ Users can view digest via web UI
4. ✅ Phase transitions work automatically based on activity patterns
5. ✅ Review projects show summaries instead of individual messages

**Target demo**: Show to 3 team members, collect feedback, iterate on ranking algorithm
