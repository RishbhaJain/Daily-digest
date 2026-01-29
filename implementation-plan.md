# Daily Digest Tool - Implementation Plan

## Overview
Build a working prototype of a Daily Digest Tool that generates personalized, role-based summaries from Slack messages for hardware engineering teams. Uses mock Slack data with a sophisticated multi-signal ranking engine that adapts to users' evolving context.

## Core Philosophy: Context-Aware Ranking

The key insight is that **relevance is temporal and personal**:
- What matters to a user TODAY (current projects, current phase) should rank highest
- What mattered YESTERDAY (past interests) should still influence ranking but with less weight
- The system must detect when a user's focus is shifting and adapt accordingly
- Ranking must be transparent - users should understand WHY something is shown

**Design Principles**:
1. **Current > Historical**: Prioritize current work context over past patterns
2. **Learn continuously**: Every interaction teaches the system about user preferences
3. **Multi-signal fusion**: Combine multiple signals (temporal, social, semantic, behavioral)
4. **Explainable rankings**: Always show WHY a message ranked where it did
5. **Graceful adaptation**: Detect context shifts without being too reactive

## What to Build (2-Day Scope)

### 1. System Architecture & Design (4-5 hours)
**Deliverable**: Professional architecture diagram showing:
- Data ingestion layer (Slack API integration points)
- Message processing pipeline
- Personalization engine architecture
- Storage layer
- Delivery mechanisms
- Feedback loop for adaptation

**Tools**: Use draw.io, Excalidraw, or similar for clean diagrams

### 2. Mock Data & Project Structure (3 hours)
**Create realistic mock Slack data representing**:
- 5-7 channels (e.g., #mechanical-team, #electrical-updates, #supply-chain, #project-alpha, #general, #blockers, #standups)
- 50-100 sample messages over a "week" with varying:
  - Message types (updates, questions, blockers, decisions, FYIs)
  - Urgency levels
  - Technical topics (CAD reviews, PCB issues, component delays, test results)
  - @mentions and thread conversations
- 5 user profiles (one for each role: mech engineer, electrical engineer, supply chain, eng manager, PM)
- **Historical interaction data** for each user (past 30 days):
  - Which messages they opened/ignored
  - Dwell times on different topics
  - Thread participation patterns
  - This demonstrates how ranking adapts over time

**Project Structure**:
```
evercurrent-digest/
├── architecture/
│   └── system_diagram.png
├── data/
│   ├── mock_messages.json
│   └── user_profiles.json
├── src/
│   ├── __init__.py
│   ├── ingest/
│   │   └── slack_parser.py
│   ├── processing/
│   │   ├── message_classifier.py
│   │   ├── relevance_scorer.py
│   │   └── personalization_engine.py
│   ├── models/
│   │   └── schemas.py
│   ├── api/
│   │   └── digest_api.py
│   └── utils/
│       └── llm_client.py
├── tests/
│   └── test_scoring.py
├── outputs/
│   └── sample_digests/
├── requirements.txt
├── README.md
└── demo.py
```

### 3. Core Ranking Engine (10-12 hours) ⭐ **PRIMARY FOCUS**

The ranking engine is the heart of the system - it must intelligently surface the most relevant items NOW while considering the user's evolving context over time.

#### A. Message Classification & Feature Extraction
**File**: `src/ingest/slack_parser.py`
- Parse mock Slack JSON messages
- Extract metadata: sender, channel, timestamp, thread context, mentions, reactions
- Identify message types: blocker, decision, update, question, FYI
- Extract entities: project names, component IDs, deadlines, people

#### B. User Context Model (Current + Historical)
**File**: `src/models/user_context.py`

Build a rich user context that evolves over time:

```python
@dataclass
class UserContext:
    # Static profile
    user_id: str
    role: str  # mechanical_engineer, electrical_engineer, etc.

    # CURRENT context (what user is working on RIGHT NOW)
    current_projects: List[str]  # ["ProjectAlpha", "FixtureDesign"]
    current_phase: Dict[str, str]  # {"ProjectAlpha": "testing", "FixtureDesign": "design"}
    active_threads: List[str]  # Threads user is participating in
    recent_keywords: List[Tuple[str, float, datetime]]  # (keyword, weight, last_seen)

    # HISTORICAL context (learned over time)
    interest_profile: Dict[str, float]  # Topic → interest score
    interaction_history: List[Interaction]  # Past 30 days
    collaboration_network: Dict[str, float]  # person → interaction frequency
    channel_preferences: Dict[str, float]  # channel → engagement rate

    # Temporal patterns
    topic_trajectory: List[Tuple[datetime, str]]  # Track shifting focus
    engagement_velocity: float  # How fast interests are changing
```

**Interaction tracking**:
```python
@dataclass
class Interaction:
    message_id: str
    timestamp: datetime
    action: str  # "opened", "clicked_thread", "marked_important", "ignored", "archived"
    dwell_time: float  # How long they spent on it
    topics: List[str]  # What topics were in this message
```

#### C. Multi-Signal Ranking System
**File**: `src/processing/ranking_engine.py`

Combine multiple signals into a final rank score. Each signal addresses a different aspect:

**Signal 1: Current Relevance (35% weight)**
```python
def compute_current_relevance(message, user_context):
    score = 0.0

    # Project alignment
    if any(proj in message.text for proj in user_context.current_projects):
        score += 0.4

    # Phase-specific keywords
    phase_keywords = get_phase_keywords(user_context.current_phase)
    keyword_overlap = len(set(message.keywords) & set(phase_keywords))
    score += 0.3 * (keyword_overlap / len(phase_keywords))

    # Active thread participation
    if message.thread_id in user_context.active_threads:
        score += 0.3

    return min(score, 1.0)
```

**Signal 2: Historical Interest (25% weight)**
```python
def compute_historical_interest(message, user_context):
    # Match message topics against learned interest profile
    topic_scores = []
    for topic in message.topics:
        if topic in user_context.interest_profile:
            topic_scores.append(user_context.interest_profile[topic])

    if not topic_scores:
        return 0.5  # Neutral for unknown topics

    return np.mean(topic_scores)
```

**Signal 3: Temporal Decay (15% weight)**
```python
def compute_temporal_score(message, current_time):
    hours_old = (current_time - message.timestamp).total_seconds() / 3600

    # Exponential decay: recent messages prioritized
    # Half-life of 8 hours
    decay_factor = 0.5 ** (hours_old / 8)

    # Urgency override
    if message.is_urgent:
        decay_factor = max(decay_factor, 0.9)

    return decay_factor
```

**Signal 4: Social Context (15% weight)**
```python
def compute_social_score(message, user_context):
    score = 0.0

    # Direct mention
    if user_context.user_id in message.mentions:
        score += 0.5

    # Message from frequent collaborator
    sender_collab_score = user_context.collaboration_network.get(
        message.sender, 0.0
    )
    score += 0.3 * sender_collab_score

    # Channel engagement
    channel_pref = user_context.channel_preferences.get(
        message.channel, 0.5
    )
    score += 0.2 * channel_pref

    return min(score, 1.0)
```

**Signal 5: LLM Semantic Understanding (10% weight)**
```python
def compute_llm_semantic_score(message, user_context):
    # Use LLM to understand nuanced relevance
    prompt = f"""
    User context:
    - Role: {user_context.role}
    - Current focus: {user_context.current_projects}
    - Recent interests: {user_context.recent_keywords[:10]}

    Message: {message.text}

    Score 0-1: How relevant is this message to what the user cares about NOW?
    Consider project alignment, actionability, and urgency.
    """

    llm_response = claude_api.score(prompt)
    return llm_response.score
```

**Final Ranking Formula**:
```python
def compute_final_rank(message, user_context, current_time):
    signals = {
        'current_relevance': compute_current_relevance(message, user_context),
        'historical_interest': compute_historical_interest(message, user_context),
        'temporal_decay': compute_temporal_score(message, current_time),
        'social_context': compute_social_score(message, user_context),
        'llm_semantic': compute_llm_semantic_score(message, user_context)
    }

    weights = {
        'current_relevance': 0.35,
        'historical_interest': 0.25,
        'temporal_decay': 0.15,
        'social_context': 0.15,
        'llm_semantic': 0.10
    }

    final_score = sum(signals[k] * weights[k] for k in signals)

    # Boost for urgent/blocking messages
    if message.is_blocker:
        final_score = min(final_score * 1.5, 1.0)

    return final_score, signals  # Return breakdown for transparency
```

#### D. Context Learning & Adaptation
**File**: `src/processing/context_learner.py`

After each digest, update the user context based on interactions:

```python
def update_user_context(user_context, interactions):
    """
    Learn from user behavior to refine future rankings.
    """
    for interaction in interactions:
        message = get_message(interaction.message_id)

        # Update interest profile
        for topic in message.topics:
            if interaction.action in ['opened', 'clicked_thread', 'marked_important']:
                # Boost interest in this topic
                current_score = user_context.interest_profile.get(topic, 0.5)
                user_context.interest_profile[topic] = min(current_score + 0.1, 1.0)

                # Add to recent keywords with timestamp
                user_context.recent_keywords.append(
                    (topic, current_score + 0.1, interaction.timestamp)
                )

            elif interaction.action in ['ignored', 'archived']:
                # Decrease interest
                current_score = user_context.interest_profile.get(topic, 0.5)
                user_context.interest_profile[topic] = max(current_score - 0.05, 0.0)

        # Update collaboration network
        if interaction.dwell_time > 30:  # Spent >30s on it
            sender = message.sender
            current_collab = user_context.collaboration_network.get(sender, 0.0)
            user_context.collaboration_network[sender] = min(current_collab + 0.05, 1.0)

        # Update channel preferences
        if interaction.action == 'opened':
            channel = message.channel
            current_pref = user_context.channel_preferences.get(channel, 0.5)
            user_context.channel_preferences[channel] = min(current_pref + 0.05, 1.0)

    # Detect context shifts
    detect_focus_shifts(user_context)

    return user_context

def detect_focus_shifts(user_context):
    """
    Detect when user's focus is changing (e.g., moving from design to testing phase).
    """
    recent_interactions = user_context.interaction_history[-20:]
    recent_topics = [topic for interaction in recent_interactions
                     for topic in get_message(interaction.message_id).topics]

    topic_frequency = Counter(recent_topics)

    # If new topics are emerging, increase engagement_velocity
    emerging_topics = [t for t, count in topic_frequency.items()
                       if t not in user_context.interest_profile]

    if len(emerging_topics) > 3:
        user_context.engagement_velocity = 'high'  # Context is shifting
        # Weight recent interactions more heavily in ranking
    else:
        user_context.engagement_velocity = 'stable'
```

#### E. Digest Generation with Ranked Results
**File**: `src/api/digest_api.py`

```python
def generate_digest(user_id, date):
    user_context = load_user_context(user_id)
    messages = fetch_messages_for_date(date)

    # Rank all messages
    ranked_messages = []
    for message in messages:
        score, signal_breakdown = compute_final_rank(
            message, user_context, datetime.now()
        )
        ranked_messages.append({
            'message': message,
            'rank_score': score,
            'signals': signal_breakdown
        })

    # Sort by rank score (highest first)
    ranked_messages.sort(key=lambda x: x['rank_score'], reverse=True)

    # Take top 20 messages
    digest_items = ranked_messages[:20]

    # Group into sections for better UX
    sections = {
        'urgent_now': [m for m in digest_items if m['rank_score'] > 0.8],
        'important_today': [m for m in digest_items if 0.6 <= m['rank_score'] <= 0.8],
        'keep_in_loop': [m for m in digest_items if 0.4 <= m['rank_score'] < 0.6],
    }

    # Generate digest with explanations
    return format_digest(sections, user_context)
```

### 4. Demo Interface with Ranking Transparency (4-5 hours)

#### Recommended: Simple Flask API + HTML Frontend
**File**: `src/api/digest_api.py`
- Endpoints:
  - `GET /digest/{user_id}?date=YYYY-MM-DD` - Get ranked digest
  - `POST /feedback` - Record user interaction (simulated learning)
  - `GET /users` - List available demo users
  - `GET /context/{user_id}` - Show user's current context profile
  - `GET /ranking-explanation/{message_id}?user_id={id}` - Explain why a message ranked where it did

**HTML Interface** should showcase the ranking engine:
- **Main Digest View**:
  - Dropdown to select role/user
  - Display digest in ranked order (highest → lowest)
  - Each message shows:
    - Rank score (e.g., 0.87/1.00)
    - Visual indicator (color-coded: red=urgent, yellow=important, green=FYI)
    - Concise summary
    - Source (channel, sender, time ago)
  - Expandable "Why this ranking?" section for each message showing signal breakdown

- **Ranking Breakdown Panel** (side panel or expandable):
  ```
  Message: "PCB layout ready for review"
  Final Rank: 0.82

  Signal Breakdown:
  ✓ Current Relevance: 0.90 (matches active project "ProjectAlpha")
  ✓ Historical Interest: 0.75 (you engage with PCB topics frequently)
  ✓ Temporal: 0.85 (posted 2 hours ago)
  ✓ Social: 0.60 (from collaborator, not direct mention)
  ✓ LLM Semantic: 0.80 (actionable, phase-relevant)
  ```

- **User Context Viewer** (separate tab):
  - Current projects and phases
  - Interest profile (top topics with scores)
  - Recent interaction patterns
  - Shows how context evolves

- **Demo Scenario Switcher**:
  - "Show same messages for different roles" - demonstrates personalization
  - "Show before/after learning" - demonstrates adaptation
  - "Simulate 1 week later" - shows how ranking changes as context shifts

### 5. Documentation & Presentation (2-3 hours)

**README.md** should include:
- Problem statement
- Solution approach (hybrid algorithm explanation)
- Architecture overview with diagram
- Key design decisions:
  - Why hybrid approach?
  - How does adaptation work?
  - Scalability considerations
  - Privacy and data handling
- Setup instructions
- Demo walkthrough
- Future enhancements (real Slack integration, ML models, mobile app)

**Sample outputs**:
- Generate and save sample digests for all 5 roles
- Show how the same day's messages produce different digests

## Technical Implementation Details

### Data Models

```python
# src/models/schemas.py

@dataclass
class SlackMessage:
    id: str
    channel: str
    sender: str
    text: str
    timestamp: datetime
    thread_ts: Optional[str]
    mentions: List[str]
    reactions: List[str]
    message_type: str  # update, question, blocker, decision, fyi
    topics: List[str]  # Extracted topics/keywords
    is_urgent: bool
    is_blocker: bool

@dataclass
class RankingSignals:
    """Breakdown of all signals that contributed to final rank"""
    current_relevance: float
    historical_interest: float
    temporal_decay: float
    social_context: float
    llm_semantic: float

@dataclass
class RankedMessage:
    message: SlackMessage
    rank_score: float  # 0-1, higher = more relevant NOW
    signals: RankingSignals  # For transparency
    summary: str  # LLM-generated concise summary
    reasoning: str  # Why this ranked high/low

@dataclass
class DigestItem:
    ranked_message: RankedMessage
    display_title: str
    display_summary: str
    action_items: List[str]
    slack_link: str
    rank_explanation: str  # User-friendly explanation of ranking
```

### LLM Integration

**Prompt Template for Semantic Ranking**:
```
You are helping rank Slack messages for {user_name}, a {role} on a robotics hardware team.

USER'S CURRENT CONTEXT:
- Active Projects: {current_projects}
- Current Phase: {current_phase}
- Recent Focus: {recent_keywords}
- Today's Date: {current_date}

USER'S HISTORICAL INTERESTS (learned over time):
- Top Topics: {top_interest_topics}
- Frequent Collaborators: {frequent_collaborators}

MESSAGE TO RANK:
Channel: {channel}
From: {sender}
Posted: {timestamp}
Text: {text}

TASK:
Consider the user's CURRENT work context and how this message relates to what they care about RIGHT NOW (not just their general role).

Provide:
1. relevance_score (0-1): How relevant is this to what the user cares about TODAY?
   - 0.9-1.0: Critical, needs immediate attention or directly impacts current work
   - 0.7-0.9: Important, relevant to current projects or close collaborators
   - 0.5-0.7: Moderately relevant, adjacent to current focus
   - 0.3-0.5: Tangentially relevant, may be useful context
   - 0.0-0.3: Not relevant to current priorities

2. summary (1-2 sentences): Concise summary of the message

3. reasoning (2-3 sentences): WHY this score? Consider:
   - Does it relate to their active projects?
   - Is it actionable for them?
   - Does it match their current phase (design vs testing vs production)?
   - Is it timely/urgent?

4. extracted_entities:
   - action_items: ["list", "of", "actions"]
   - deadlines: ["list", "of", "dates"]
   - components: ["PCB-v2", "Motor-Assembly"]
   - people_mentioned: ["names"]

Output as JSON only.
```

**Batch Ranking Optimization**:
For efficiency, batch multiple messages into a single LLM call:
```python
def rank_messages_with_llm_batch(messages, user_context, batch_size=10):
    """
    Process messages in batches to reduce API calls.
    Use Haiku for cost-effectiveness (~100 messages for ~$0.50).
    """
    results = []
    for i in range(0, len(messages), batch_size):
        batch = messages[i:i+batch_size]
        prompt = create_batch_ranking_prompt(batch, user_context)
        llm_response = claude_haiku.complete(prompt)
        results.extend(parse_batch_response(llm_response))
    return results
```

### Adaptation Logic

Simulate learning by:
1. For each generated digest, randomly mark some items as "opened" vs "ignored" based on their score
2. Update user profile's focus_keywords:
   - Boost keywords from opened high-score messages
   - Reduce weight of keywords from ignored messages
3. Show "before" and "after" digests to demonstrate adaptation

## Testing & Validation

**Test scenarios to demonstrate ranking engine**:

1. **Current vs Historical Context**:
   - User A is currently focused on "PCB testing" (current context)
   - User A historically cared about "CAD design" (past context)
   - Show that PCB-related messages rank higher than CAD messages
   - Demonstrates temporal prioritization

2. **Role differentiation**:
   - Same 50 messages, 3 different roles
   - Each role sees different top 10 messages
   - Demonstrates personalization

3. **Context Shift Detection**:
   - Day 1: User engages with design-phase messages
   - Day 7: User engages with testing-phase messages
   - Show ranking adjustment as user's focus shifts
   - Demonstrates adaptation

4. **Urgency Boosting**:
   - Low-scoring message marked "URGENT" or "BLOCKER"
   - Should rank near top despite low base relevance
   - Demonstrates signal overrides

5. **Social Network Effect**:
   - Messages from frequent collaborators rank higher
   - Messages from strangers rank lower (unless highly relevant)
   - Demonstrates social context

6. **Recency Decay**:
   - Two equally relevant messages, one 1hr old, one 48hrs old
   - Recent one ranks higher
   - Demonstrates temporal decay

7. **Comparative Ranking**:
   - Show top 20 ranked messages with scores
   - Verify ranking order makes intuitive sense
   - Show messages that ranked low and explain why

8. **Transparency Test**:
   - For each top-ranked message, show signal breakdown
   - Verify signals align with user context
   - User should understand WHY each message ranked where it did

## Success Criteria

✅ **Sophisticated ranking engine** that combines current + historical context
✅ **Demonstrable adaptation**: Show how rankings change as user context evolves
✅ **Transparency**: Clear explanation of why each message ranked where it did
✅ Working prototype that generates different digests for 5 different roles
✅ Clear system architecture diagram emphasizing ranking pipeline
✅ Multi-signal ranking algorithm (5 signals) implemented and testable
✅ Evidence of personalization beyond just role (learned preferences, shifting focus)
✅ Clean, documented code with ranking logic clearly separated
✅ Strong README explaining ranking design decisions
✅ Sample outputs showing ranking in action (before/after scenarios)

## Time Breakdown (Total: ~22-26 hours over 2 days)

**Day 1** (11-13 hours):
- [ ] Architecture diagram with ranking pipeline emphasis (2h)
- [ ] Project setup + mock data (messages + interaction history) (3h)
- [ ] Data models: messages, user context, ranking signals (1h)
- [ ] Core parsing and feature extraction (2h)
- [ ] User context model implementation (3h)

**Day 2** (11-13 hours):
- [ ] Multi-signal ranking engine implementation (5h)
  - [ ] Current relevance signal
  - [ ] Historical interest signal
  - [ ] Temporal decay signal
  - [ ] Social context signal
  - [ ] LLM semantic signal
  - [ ] Final ranking combiner
- [ ] Context learning & adaptation logic (2h)
- [ ] Demo interface with ranking transparency (4h)
- [ ] Testing ranking scenarios (2h)
- [ ] Documentation and polish (2h)

## Demonstrating the Ranking Engine

Create compelling demo scenarios that showcase ranking intelligence:

### Scenario 1: "Same Messages, Different Rankings"
- Show the same 50 messages to 3 different users
- Each sees a completely different top 10 based on their context
- Visually highlight how rankings differ

### Scenario 2: "Context Evolution"
- Day 1: User is in "design phase" → design-related messages rank high
- Day 7: User moves to "testing phase" → testing messages now rank high
- Show side-by-side ranking comparison
- Demonstrate how interest_profile weights shift

### Scenario 3: "Learning in Action"
- Initial digest: Mixed relevance based on role defaults
- User interacts: Opens 5 PCB messages, ignores 3 CAD messages
- Updated digest: PCB messages rank higher, CAD messages rank lower
- Show before/after with signal breakdown

### Scenario 4: "Urgency Override"
- Low-relevance message (score 0.4) marked "BLOCKER"
- Boosted to top of digest (score 0.9+)
- Show how urgency signal overrides other factors

### Scenario 5: "Ranking Transparency"
- Pick 3 messages from a digest (top, middle, bottom)
- For each, show complete signal breakdown with visual bar chart
- Explain in plain language why each ranked where it did

## Key Files to Create

1. `architecture/system_diagram.png` - Full system architecture
2. `data/mock_messages.json` - 50-100 realistic Slack messages
3. `data/user_profiles.json` - 5 role profiles
4. `src/processing/relevance_scorer.py` - Core hybrid scoring logic
5. `src/processing/personalization_engine.py` - Role-based personalization
6. `demo.py` or `src/api/digest_api.py` - Demo interface
7. `outputs/sample_digests/` - Pre-generated samples for all roles
8. `README.md` - Comprehensive documentation
9. `requirements.txt` - Dependencies (anthropic, flask, pydantic, etc.)

## Design Decisions to Highlight

1. **Hybrid approach**: Combines reliability of rules with intelligence of LLMs
2. **Adaptation mechanism**: Simple but effective keyword weight adjustment
3. **Transparency**: Show scoring breakdown so users understand why things are surfaced
4. **Scalability path**: Mock data → Real Slack → ML models
5. **Privacy**: No message content stored long-term, only aggregated preferences

## Optional Enhancements (if time permits)

- Simple visualization showing score distribution
- A/B test framework for trying different scoring weights
- Export digest to email/PDF format
- Slack-like UI mockup
- Video walkthrough/demo recording

---

This plan balances depth (working personalization algorithm) with breadth (full system design) to create an impressive take-home in 2 days.
