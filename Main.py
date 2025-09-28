# Happy Hauler Recruiting Assistant
# State machine + JSON classification + post-qualification Q&A + off-topic lock
# ---------------------------------------------------------------------------
# Usage:
#   1) pip install -r requirements.txt
#   2) Create a .env file with: OPENAI_API_KEY=sk-...
#   3) streamlit run Main.py

import os
import json
import re
import random
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# ---------- Load environment ----------
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")

# ---------- Multi-room State ----------
def new_state():
    return {
        "step": "greeting",
        "has_greeted": False,
        "has_cdl": None,
        "years_experience": None,
        "nights_ok": None,
        "history": [],
        # per-room control: chat input enabled unless off-topic or early-exit triggers
        "input_enabled": True,
    }

first_names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Timothy", "Kate", "Jane", "Kimberly", "Robert"]
last_names  = ["Smith", "Jones", "Williams", "Brown", "Davis", "James", "Davis", "Doe", "Kim", "Emily"]

# Precompute all unique combinations
all_combos = [f"{f} {l}" for f in first_names for l in last_names]
random.shuffle(all_combos)  # shuffle so order is random

existing_names = set()

def generate_random_name():
    if not all_combos:  # exhausted all unique combinations
        raise RuntimeError("No more unique names available")
    full = all_combos.pop()
    existing_names.add(full)
    return full

if "conversations" not in st.session_state:
    curr = generate_random_name()
    st.session_state.conversations = {curr: new_state()}
    st.session_state.current_room   = curr

def current_state():
    return st.session_state.conversations[st.session_state.current_room]

state = current_state()

# ---------- Page ----------
st.set_page_config(page_title="Happy Hauler Assistant", page_icon="🚚", layout="wide")
st.header(f"💬 {st.session_state.current_room or 'Double Nickel Chatbot'}")
st.caption("🚀 Recruiting Assistant Chatbot Powered by Double Nickel")

# ---------- Copy + Constants ----------
GREETING = (
    f"Hi {st.session_state.current_room.split(' ')[0] or ''} 👋, I'm the Happy Hauler recruiting assistant. "
    "Thanks for your interest in our driving role. Can I ask you a few quick questions?"
)
PERSUASION_WITH_CDL = (
    "This will only take about a minute and just confirms basic qualifications.\n"
    "Do you have a valid Class A CDL?"
)
OFFTOPIC_NOTE = "Note: For non-role questions, please email us at help@getdoublenickel.com."

CDL_QUESTION     = "Do you have a valid Class A CDL?"
YEARS_QUESTION   = "How many years of truck driving experience do you have?"
YEARS_FOLLOWUP   = "Could you tell me exactly how many years?"
NIGHTS_QUESTION  = "This job requires being on the road for two nights each week. Is that okay?"

EARLY_EXIT_CDL    = "This role requires a valid Class A CDL. Thank you for your time and best of luck in your job search."
EARLY_EXIT_YEARS  = "This role requires at least one year of truck driving experience. Thank you for your time and best of luck in your job search."
EARLY_EXIT_NIGHTS = "This role requires being on the road for two nights each week. Thank you for your time and best of luck in your job search."

POST_THANKS_AND_Q = "Thank you. A recruiter will be in touch with you shortly. Do you have any questions about the role?"
FINAL_GOODBYE     = "Thank you so much. Have a great day."
PAY_LINE          = "The pay range is 60 to 65 cents per mile based on experience."

# ---------- Helpers ----------
def say_assistant(text: str):
    state["history"].append({"role": "assistant", "content": text})

def say_user(text: str):
    state["history"].append({"role": "user", "content": text})

def is_negative(user_text: str) -> bool:
    t = (user_text or "").strip().lower()
    negative_terms = [
        "no", "nope", "nah", "not really", "i'm good", "im good", "all good",
        "no questions", "no question", "nothing", "that's all", "thats all", "i'm fine", "im fine",
        "no thanks", "no thank you"
    ]
    return any(term in t for term in negative_terms)

def mentions_no_experience(user_text: str) -> bool:
    t = (user_text or "").strip().lower()
    patterns = [
        r"\bno experience\b", r"\bnone\b", r"\bzero\b", r"\b0\b", r"\bnever\b",
        r"\bno exp\b", r"\bnew driver\b", r"\bno driving experience\b"
    ]
    return any(re.search(p, t) for p in patterns)

def render_eligibility_panel(state_dict: dict):
    """
    Show an eligibility summary panel based on answers gathered so far.
    Eligible if: has_cdl == True, years_experience >= 1, nights_ok == True
    """
    missing = []

    if state_dict.get("has_cdl") is not True:
        missing.append("a valid Class A CDL")
    years = state_dict.get("years_experience")
    if years is None or not isinstance(years, int) or years < 1:
        missing.append("at least one year of truck driving experience")
    if state_dict.get("nights_ok") is not True:
        missing.append("availability for two nights on the road each week")

    if missing:
        bullets = "".join(f"- {m}\n" for m in missing)
        st.warning(
            "You're not eligible because you're missing at least one of the following requirement(s):\n\n" + bullets
        )
    else:
        st.info("You're eligible. We will reach out to you soon.")

# ---------- OpenAI helpers ----------
def get_client():
    if not API_KEY:
        return None
    return OpenAI(api_key=API_KEY)

def classify(user_text: str, intent_hint: str = "generic"):
    """
    Returns a dict:
      {"answer_type": "affirmative"|"negative"|"number"|"unknown"|"other",
       "number_value": int|None, "reason": str}
    """
    client = get_client()
    if client is None:
        # heuristic fallback
        txt = (user_text or "").strip().lower()
        if any(x in txt for x in ["yes", "yep", "yeah", "sure", "ok", "okay", "affirmative", "yup", "ya"]):
            return {"answer_type": "affirmative", "number_value": None, "reason": "heuristic yes"}
        if any(x in txt for x in ["no", "nope", "nah", "don't have", "do not have", "not really"]):
            return {"answer_type": "negative", "number_value": None, "reason": "heuristic no"}
        m = re.search(r"\b(-?\d+)\b", txt)
        if m:
            return {"answer_type": "number", "number_value": int(m.group(1)), "reason": "heuristic number"}
        return {"answer_type": "unknown", "number_value": None, "reason": "heuristic unknown"}

    system = (
        "You extract structured answers from applicants for a truck driving role. "
        "Return ONLY valid JSON with keys: "
        '{"answer_type": one of ["affirmative","negative","number","unknown","other"], '
        '"number_value": integer or null, "reason": short string}. Be strict JSON (no prose).'
    )
    examples = """
User: "yep I have it" -> {"answer_type":"affirmative","number_value":null,"reason":"yes cdl"}
User: "nope" -> {"answer_type":"negative","number_value":null,"reason":"no"}
User: "about 3 years" -> {"answer_type":"number","number_value":3,"reason":"3 years"}
User: "a while" -> {"answer_type":"unknown","number_value":null,"reason":"vague"}
"""
    user_msg = f"Current question intent: {intent_hint}.\nApplicant said: {user_text}\n{examples}"
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user_msg}],
    )
    try:
        return json.loads(resp.choices[0].message.content)
    except Exception:
        txt = (user_text or "").strip().lower()
        if any(x in txt for x in ["yes", "yep", "yeah", "sure", "ok", "okay"]):
            return {"answer_type": "affirmative", "number_value": None, "reason": "fallback yes"}
        if any(x in txt for x in ["no", "nope", "nah"]):
            return {"answer_type": "negative", "number_value": None, "reason": "fallback no"}
        m = re.search(r"\b(-?\d+)\b", txt)
        if m:
            return {"answer_type": "number", "number_value": int(m.group(1)), "reason": "fallback number"}
        return {"answer_type": "unknown", "number_value": None, "reason": "parse_error"}

def answer_user_question(user_question_text: str) -> str:
    t = (user_question_text or "").lower()
    if any(k in t for k in ["pay", "salary", "wage", "rate", "cents per mile", "compensation", "money"]):
        return PAY_LINE

    client = get_client()
    if client is None:
        return ("A recruiter can share more details about that during the next step. "
                "If you have any additional questions, please email us at help@getdoublenickel.com.")

    system = (
        "You are the Happy Hauler recruiting assistant. Be concise, factual, and friendly. "
        "If asked about pay, respond with: 'The pay range is 60 to 65 cents per mile based on experience.' "
        "If you don't have a specific fact, say the recruiter can provide details. "
        "Avoid making up benefits or policies not provided. Keep answers to 1–3 short sentences."
    )
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": user_question_text}]
    resp = client.chat.completions.create(model="gpt-4o-mini", temperature=0.2, messages=messages)
    return resp.choices[0].message.content.strip()

def is_truck_related(text: str) -> bool:
    """True if the message is about the truck job or company/job details (incl. location, days off/PTO)."""
    t = (text or "").strip().lower()
    # Fast path: keyword heuristic
    truck_keywords = [
        "truck", "driv", "cdl", "class a", "mvr", "routes", "lanes", "miles", "cents per mile",
        "orientation", "ot", "home time", "dispatch", "equipment", "benefit", "policy", "policies",
        "pay", "salary", "wage", "compensation", "dedicated", "regional", "otr",
        "night", "shift", "schedule", "hazmat", "endorsement", "hours of service", "hos", "dot",
        "pre-trip", "post-trip", "trailer", "reefer", "flatbed",
        "location", "where", "based", "days off", "pto", "vacation", "holiday"
    ]
    if any(k in t for k in truck_keywords):
        return True

    # LLM fallback
    client = get_client()
    if client is None:
        return False

    system = (
        "You are a binary classifier. Return exactly 'truck' if the user's message is about a truck driving job "
        "or company/job details (requirements, pay/compensation, location/where the job is based, schedule/home time, "
        "days off/PTO/vacation, benefits, routes/lanes, equipment, policies, HOS/DOT, CDL, endorsements, etc.). "
        "Otherwise return exactly 'other'."
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
        )
        label = (resp.choices[0].message.content or "").strip().lower()
        # Be strict: only 'truck' counts as on-topic
        return label == "truck"
    except Exception:
        # On any API error, default to off-topic
        return False

def answer_user_question_anytopic(user_text: str) -> tuple[str, bool]:
    """
    Answers any question; appends a note for off-topic.
    Returns (answer, on_topic_flag).
    """
    t = (user_text or "").lower()
    if any(k in t for k in ["pay", "salary", "wage", "rate", "cents per mile", "compensation", "money"]):
        return PAY_LINE, True

    client   = get_client()
    on_topic = is_truck_related(user_text)

    if client is None:
        if on_topic:
            return "A recruiter can share more details about that during the next step. Anything else I can help with?", True
        return f"{answer_user_question(user_text)}\n\n{OFFTOPIC_NOTE}", False

    system = (
        "You are the Happy Hauler recruiting assistant. "
        "Be concise, factual, and friendly. "
        "If the user asks about pay, the exact line to use is: "
        "'The pay range is 60 to 65 cents per mile based on experience.' "
        "If you don't have a specific fact, say the recruiter can provide details. "
        "Avoid inventing policies. Keep answers to 1–3 short sentences. "
        "If the user's question is unrelated to the truck driving role or the company/job details, "
        "still provide a brief, polite response but avoid to mention 'feel free to ask' or 'let me know'."
    )
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user_text}],
    )
    core = resp.choices[0].message.content.strip()
    return (core, True) if on_topic else (f"{core}\n\n The eligibility result will be displayed below. Thank you for taking the time to chat with us. \n\n{OFFTOPIC_NOTE}", False)

# ---------- Sidebar ----------
with st.sidebar:
    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown("### Chats")
    with col2:
        new_clicked = st.button("➕", key="btn_new_room", type="tertiary", help="New chat")

    if new_clicked:
        name = generate_random_name()
        st.session_state.conversations[name] = new_state()
        st.session_state.current_room       = name
        st.rerun()

    rooms       = list(st.session_state.conversations.keys())
    current_idx = rooms.index(st.session_state.current_room)
    selected    = st.radio("Select a chat", rooms, index=current_idx)
    if selected != st.session_state.current_room:
        st.session_state.current_room = selected
        state = current_state()
        st.rerun()

# ---------- Render existing history ----------
for m in state["history"]:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# ---------- First-load greeting ----------
if state["step"] == "greeting" and not state["has_greeted"]:
    say_assistant(GREETING)
    state["has_greeted"] = True
    state["step"] = "await_consent"
    with st.chat_message("assistant"):
        st.markdown(GREETING)

# ---------- User input & eligibility panel (single place, no duplicates) ----------
def lock_and_rerun():
    # Helper: lock the chat and immediately refresh UI
    state["input_enabled"] = False
    st.rerun()

if not state["input_enabled"]:
    # Disabled state: show locked input + eligibility, then stop
    st.chat_input(
        "Conversation ended. Please reach out to help@getdoublenickel.com for further assistance",
        disabled=True,
        key="chat_disabled",
    )
    st.divider()
    render_eligibility_panel(state)
    st.stop()  # nothing else should run in this render

# Enabled state: render the single active input
user_text = st.chat_input("Type your reply")
if not user_text:
    st.stop()  # no message to process this render

# From here on, we have user_text AND input is enabled
say_user(user_text)
with st.chat_message("user"):
    st.markdown(user_text)

step = state["step"]

if step == "await_consent":
    result  = classify(user_text, intent_hint="consent_boolean")
    nextmsg = CDL_QUESTION if result["answer_type"] == "affirmative" else PERSUASION_WITH_CDL
    say_assistant(nextmsg)
    with st.chat_message("assistant"):
        st.markdown(nextmsg)
    state["step"] = "ask_cdl"

elif step == "ask_cdl":
    result = classify(user_text, intent_hint="cdl_boolean")
    if result["answer_type"] == "negative":
        state["has_cdl"] = False
        say_assistant(EARLY_EXIT_CDL)
        with st.chat_message("assistant"):
            st.markdown(EARLY_EXIT_CDL)
        state["step"] = "done"
        lock_and_rerun()  # <—— immediately refresh so only the disabled panel appears
    elif result["answer_type"] == "affirmative":
        state["has_cdl"] = True
        say_assistant(YEARS_QUESTION)
        with st.chat_message("assistant"):
            st.markdown(YEARS_QUESTION)
        state["step"] = "ask_years"
    else:
        msg = "Just to confirm — do you have a valid Class A CDL? (Yes/No)"
        say_assistant(msg)
        with st.chat_message("assistant"):
            st.markdown(msg)

elif step == "ask_years":
    result = classify(user_text, intent_hint="years_number")
    no_exp = (
        result["answer_type"] == "negative"
        or (result["answer_type"] == "number" and isinstance(result["number_value"], int) and result["number_value"] <= 0)
        or mentions_no_experience(user_text)
    )
    if no_exp:
        state["years_experience"] = 0
        say_assistant(EARLY_EXIT_YEARS)
        with st.chat_message("assistant"):
            st.markdown(EARLY_EXIT_YEARS)
        state["step"] = "done"
        lock_and_rerun()
    elif result["answer_type"] == "number" and isinstance(result["number_value"], int) and result["number_value"] >= 1:
        state["years_experience"] = result["number_value"]
        say_assistant(NIGHTS_QUESTION)
        with st.chat_message("assistant"):
            st.markdown(NIGHTS_QUESTION)
        state["step"] = "ask_nights"
    else:
        say_assistant(YEARS_FOLLOWUP)
        with st.chat_message("assistant"):
            st.markdown(YEARS_FOLLOWUP)

elif step == "ask_nights":
    result = classify(user_text, intent_hint="nights_boolean")
    if result["answer_type"] == "negative":
        state["nights_ok"] = False
        say_assistant(EARLY_EXIT_NIGHTS)
        with st.chat_message("assistant"):
            st.markdown(EARLY_EXIT_NIGHTS)
        state["step"] = "done"
        lock_and_rerun()
    elif result["answer_type"] == "affirmative":
        state["nights_ok"] = True
        say_assistant(POST_THANKS_AND_Q)
        with st.chat_message("assistant"):
            st.markdown(POST_THANKS_AND_Q)
        state["step"] = "post_offer"
    else:
        msg = "Please let me know if two nights on the road each week is okay. (Yes/No)"
        say_assistant(msg)
        with st.chat_message("assistant"):
            st.markdown(msg)

elif step in ("post_offer", "post_qa_chat"):
    if is_negative(user_text):
        say_assistant(FINAL_GOODBYE)
        with st.chat_message("assistant"):
            st.markdown(FINAL_GOODBYE)
        state["step"] = "done"
        lock_and_rerun()
    else:
        answer, on_topic = answer_user_question_anytopic(user_text)
        say_assistant(answer)
        with st.chat_message("assistant"):
            st.markdown(answer)
        if not on_topic:
            state["step"] = "done"
            lock_and_rerun()
        else:
            state["step"] = "post_qa_chat"

elif step == "done":
    lock_and_rerun()