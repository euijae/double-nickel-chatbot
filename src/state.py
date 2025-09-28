# hauler/state.py
import re
import streamlit as st

def new_state():
    return {
        "step": "greeting",
        "has_greeted": False,
        "has_cdl": None,
        "years_experience": None,
        "nights_ok": None,
        "history": [],
        "input_enabled": True,
    }

def ensure_session_state():
    if "conversations" not in st.session_state:
        st.session_state.conversations = {}
    if "current_room" not in st.session_state:
        st.session_state.current_room = None

def current_state():
    return st.session_state.conversations[st.session_state.current_room]

def say_assistant(text: str):
    current_state()["history"].append({"role": "assistant", "content": text})

def say_user(text: str):
    current_state()["history"].append({"role": "user", "content": text})

def is_negative(user_text: str) -> bool:
    """
    Determine the tone of user's text
    :param user_text: user text
    :return: true if user has no more question false otherwise
    """
    t = (user_text or "").strip().lower()
    negative_terms = [
        "no", "nope", "nah", "not really", "i'm good", "im good", "all good",
        "no questions", "no question", "nothing", "that's all", "thats all", "i'm fine", "im fine",
        "no thanks", "no thank you"
    ]
    return any(term in t for term in negative_terms)

def mentions_no_experience(user_text: str) -> bool:
    """
    Determine what user responded regarding trucking experience.
    :param user_text: user text
    :return: true if user has no experience false otherwise
    """
    t = (user_text or "").strip().lower()
    patterns = [
        r"\bno experience\b", r"\bnone\b", r"\bzero\b", r"\b0\b", r"\bnever\b",
        r"\bno exp\b", r"\bnew driver\b", r"\bno driving experience\b"
    ]
    return any(re.search(p, t) for p in patterns)

def render_eligibility_panel(state_dict: dict):
    """
    Determine the user's job eligibility and render it
    :param state_dict: state dictionary
    :return: None
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
