"""
Mock Data Generator for Daily Digest Tool
Uses OpenAI API to generate realistic Slack messages.
Generates: 3 projects, 10 users, 50-100 messages, UserProjectStates
"""

import json
import random
import os
from datetime import datetime, timedelta
from pathlib import Path
from openai import OpenAI

DATA_DIR = Path(__file__).parent.parent / "data"

client = OpenAI()

# =============================================================================
# Projects
# =============================================================================
PROJECTS = [
    {
        "project_id": "pcb-redesign",
        "name": "PCB Redesign",
        "channels": ["#pcb-review", "#electrical"],
        "keywords": ["PCB", "circuit", "layout", "schematic", "capacitor", "resistor", "trace", "board"]
    },
    {
        "project_id": "motor-assembly",
        "name": "Motor Assembly",
        "channels": ["#mechanical", "#motor-debug"],
        "keywords": ["motor", "assembly", "torque", "shaft", "bearing", "gear", "housing", "CAD"]
    },
    {
        "project_id": "firmware-update",
        "name": "Firmware Update",
        "channels": ["#firmware", "#embedded"],
        "keywords": ["firmware", "embedded", "flash", "bootloader", "register", "interrupt", "driver", "RTOS"]
    }
]

# =============================================================================
# Users
# =============================================================================
USERS = [
    {"user_id": "alice", "name": "Alice Chen", "role": "electrical_engineer", "primary": "pcb-redesign"},
    {"user_id": "bob", "name": "Bob Martinez", "role": "electrical_engineer", "primary": "pcb-redesign"},
    {"user_id": "carol", "name": "Carol Johnson", "role": "electrical_engineer", "primary": "pcb-redesign"},
    {"user_id": "david", "name": "David Kim", "role": "mechanical_engineer", "primary": "motor-assembly"},
    {"user_id": "emma", "name": "Emma Wilson", "role": "mechanical_engineer", "primary": "motor-assembly"},
    {"user_id": "frank", "name": "Frank Brown", "role": "mechanical_engineer", "primary": "motor-assembly"},
    {"user_id": "grace", "name": "Grace Lee", "role": "firmware_engineer", "primary": "firmware-update"},
    {"user_id": "henry", "name": "Henry Zhang", "role": "firmware_engineer", "primary": "firmware-update"},
    {"user_id": "ivan", "name": "Ivan Patel", "role": "pm", "primary": None},
    {"user_id": "julia", "name": "Julia Santos", "role": "engineering_lead", "primary": None},
]

def get_all_channels():
    return [ch for p in PROJECTS for ch in p["channels"]]

def get_project_for_channel(channel):
    for p in PROJECTS:
        if channel in p["channels"]:
            return p["project_id"]
    return None

def generate_timestamp(hours_ago_max=24):
    now = datetime.now()
    if random.random() < 0.6:
        hour = random.randint(9, 17)
    else:
        hour = random.randint(6, 8) if random.random() < 0.5 else random.randint(18, 22)
    hours_ago = random.uniform(0, hours_ago_max)
    base_time = now - timedelta(hours=hours_ago)
    result = base_time.replace(hour=hour, minute=random.randint(0, 59), second=random.randint(0, 59))
    return result.isoformat()

def generate_messages_with_llm(count=75):
    """Use OpenAI to generate realistic Slack messages."""

    channels = get_all_channels()
    user_names = {u["user_id"]: u["name"] for u in USERS}

    prompt = f"""Generate {count} realistic Slack messages for a hardware engineering team working on robotics.

PROJECTS:
1. PCB Redesign - electrical team working on circuit boards (#pcb-review, #electrical)
2. Motor Assembly - mechanical team working on motors and gears (#mechanical, #motor-debug)
3. Firmware Update - embedded team working on firmware (#firmware, #embedded)

TEAM MEMBERS (with primary/secondary projects):
- alice (Alice Chen) - electrical engineer, PRIMARY: PCB (#pcb-review, #electrical), SECONDARY: Motor
- bob (Bob Martinez) - electrical engineer, PRIMARY: PCB, SECONDARY: Firmware
- carol (Carol Johnson) - electrical engineer, PRIMARY: PCB, SECONDARY: Motor
- david (David Kim) - mechanical engineer, PRIMARY: Motor (#mechanical, #motor-debug), SECONDARY: PCB
- emma (Emma Wilson) - mechanical engineer, PRIMARY: Motor, SECONDARY: Firmware
- frank (Frank Brown) - mechanical engineer, PRIMARY: Motor, SECONDARY: PCB
- grace (Grace Lee) - firmware engineer, PRIMARY: Firmware (#firmware, #embedded), SECONDARY: Motor
- henry (Henry Zhang) - firmware engineer, PRIMARY: Firmware, SECONDARY: PCB
- ivan (Ivan Patel) - PM, monitors ALL projects (asks status questions, schedules)
- julia (Julia Santos) - engineering lead, active on ALL projects (reviews, unblocks, decisions)

POSTING BEHAVIOR:
- Engineers post ~70% in their PRIMARY project channels, ~20% in SECONDARY, ~10% cross-team
- PM posts across all channels asking for updates, scheduling
- Lead posts across all channels doing reviews and unblocking

MESSAGE TYPES (distribute roughly):
- 25% updates: status updates, completed work
- 20% questions: asking for help, clarification
- 15% fyi: announcements, heads up
- 10% blockers: blocked on something, need someone
- 10% urgent: time-sensitive, critical issues
- 20% filler/noise: casual chat, jokes, off-topic, lunch plans, "thanks!", memes, random banter

Generate messages as a JSON array. Each message should have:
- sender: user_id (alice, bob, carol, david, emma, frank, grace, henry, ivan, julia)
- channel: one of #pcb-review, #electrical, #mechanical, #motor-debug, #firmware, #embedded
- text: realistic Slack message (1-3 sentences, casual engineering tone)
- mentions: list of user_ids mentioned in the message (if any)
- is_urgent: true if urgent/critical
- is_blocker: true if blocked/waiting on someone

Make messages feel authentic - use technical jargon, reference specific components, include @mentions where appropriate.

Return ONLY the JSON array, no other text."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=8000,
    )

    # Parse the response
    response_text = response.choices[0].message.content.strip()

    # Handle potential markdown code blocks
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1])

    messages_raw = json.loads(response_text)

    # Add IDs and timestamps
    messages = []
    for i, msg in enumerate(messages_raw):
        messages.append({
            "id": f"msg_{i:04d}",
            "channel": msg.get("channel", random.choice(channels)),
            "thread_id": None,
            "sender": msg.get("sender", random.choice(list(user_names.keys()))),
            "text": msg.get("text", ""),
            "timestamp": generate_timestamp(),
            "mentions": msg.get("mentions", []),
            "is_dm": False,
            "is_urgent": msg.get("is_urgent", False),
            "is_blocker": msg.get("is_blocker", False),
        })

    messages.sort(key=lambda m: m["timestamp"], reverse=True)
    return messages

def count_messages_past_week(messages):
    """Count messages per (user, project) from the past 7 days."""
    now = datetime.now()
    one_week_ago = now - timedelta(days=7)

    counts = {}
    last_timestamps = {}

    for msg in messages:
        sender = msg["sender"]
        channel = msg["channel"]
        project_id = get_project_for_channel(channel)
        ts_str = msg["timestamp"]

        if not project_id:
            continue

        # Parse timestamp
        ts = datetime.fromisoformat(ts_str)

        key = (sender, project_id)

        # Count only messages from past week
        if ts >= one_week_ago:
            counts[key] = counts.get(key, 0) + 1

        # Track most recent timestamp (regardless of week filter)
        if key not in last_timestamps or ts_str > last_timestamps[key]:
            last_timestamps[key] = ts_str

    return counts, last_timestamps

def generate_user_project_states(messages):
    """Generate UserProjectState for each user based on actual message counts."""
    counts, last_timestamps = count_messages_past_week(messages)
    states = []
    project_ids = [p["project_id"] for p in PROJECTS]

    for user in USERS:
        if user["role"] == "pm":
            # PM has varied phases: one active (current focus), others review
            pm_phases = {"pcb-redesign": "active", "motor-assembly": "review", "firmware-update": "review"}
            for pid in project_ids:
                key = (user["user_id"], pid)
                msg_count = counts.get(key, 0)
                last_ts = last_timestamps.get(key, generate_timestamp(hours_ago_max=72))
                states.append({
                    "user_id": user["user_id"],
                    "project_id": pid,
                    "phase": pm_phases.get(pid, "review"),
                    "channels": next(p["channels"] for p in PROJECTS if p["project_id"] == pid),
                    "last_contributed": last_ts,
                    "messages_past_week": msg_count,
                })
        elif user["role"] == "engineering_lead":
            for pid in project_ids:
                key = (user["user_id"], pid)
                msg_count = counts.get(key, 0)
                last_ts = last_timestamps.get(key, generate_timestamp(hours_ago_max=24))
                states.append({
                    "user_id": user["user_id"],
                    "project_id": pid,
                    "phase": "active",
                    "channels": next(p["channels"] for p in PROJECTS if p["project_id"] == pid),
                    "last_contributed": last_ts,
                    "messages_past_week": msg_count,
                })
        else:
            primary = user.get("primary")
            other_projects = [pid for pid in project_ids if pid != primary]
            random.shuffle(other_projects)

            if primary:
                key = (user["user_id"], primary)
                msg_count = counts.get(key, 0)
                last_ts = last_timestamps.get(key, generate_timestamp(hours_ago_max=12))
                states.append({
                    "user_id": user["user_id"],
                    "project_id": primary,
                    "phase": "active",
                    "channels": next(p["channels"] for p in PROJECTS if p["project_id"] == primary),
                    "last_contributed": last_ts,
                    "messages_past_week": msg_count,
                })

            if other_projects:
                secondary = other_projects[0]
                key = (user["user_id"], secondary)
                msg_count = counts.get(key, 0)
                last_ts = last_timestamps.get(key, generate_timestamp(hours_ago_max=120))
                states.append({
                    "user_id": user["user_id"],
                    "project_id": secondary,
                    "phase": "review",
                    "channels": next(p["channels"] for p in PROJECTS if p["project_id"] == secondary),
                    "last_contributed": last_ts,
                    "messages_past_week": msg_count,
                })

            if len(other_projects) > 1 and random.random() < 0.5:
                third = other_projects[1]
                key = (user["user_id"], third)
                msg_count = counts.get(key, 0)
                last_ts = last_timestamps.get(key, generate_timestamp(hours_ago_max=336))
                states.append({
                    "user_id": user["user_id"],
                    "project_id": third,
                    "phase": "done",
                    "channels": next(p["channels"] for p in PROJECTS if p["project_id"] == third),
                    "last_contributed": last_ts,
                    "messages_past_week": msg_count,
                })

    return states

def generate_all():
    """Generate all mock data and save to JSON files."""
    DATA_DIR.mkdir(exist_ok=True)

    # Save projects
    with open(DATA_DIR / "projects.json", "w") as f:
        json.dump(PROJECTS, f, indent=2)
    print(f"Created {len(PROJECTS)} projects")

    # Save users
    users_data = [{"user_id": u["user_id"], "name": u["name"], "role": u["role"]} for u in USERS]
    with open(DATA_DIR / "users.json", "w") as f:
        json.dump(users_data, f, indent=2)
    print(f"Created {len(USERS)} users")

    # Generate messages with LLM
    print("Generating messages with OpenAI API...")
    messages = generate_messages_with_llm(75)
    with open(DATA_DIR / "messages.json", "w") as f:
        json.dump(messages, f, indent=2)
    print(f"Created {len(messages)} messages")

    # Generate user project states (based on actual message counts)
    states = generate_user_project_states(messages)
    with open(DATA_DIR / "user_project_states.json", "w") as f:
        json.dump(states, f, indent=2)
    print(f"Created {len(states)} user project states")

    # Summary
    print("\n--- Summary ---")
    print(f"Projects: {[p['name'] for p in PROJECTS]}")
    print(f"Channels: {get_all_channels()}")
    print(f"Users: {[u['name'] for u in USERS]}")

    blocker_count = sum(1 for m in messages if m["is_blocker"])
    urgent_count = sum(1 for m in messages if m["is_urgent"])
    print(f"Blockers: {blocker_count}, Urgent: {urgent_count}")

if __name__ == "__main__":
    generate_all()
