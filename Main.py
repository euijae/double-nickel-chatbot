# Main.py
# Run: streamlit run Main.py

import streamlit as st
from dotenv import load_dotenv

from src import (
    GREETING, PERSUASION_WITH_CDL,
    CDL_QUESTION, YEARS_QUESTION, YEARS_FOLLOWUP, NIGHTS_QUESTION,
    EARLY_EXIT_CDL, EARLY_EXIT_YEARS, EARLY_EXIT_NIGHTS,
    POST_THANKS_AND_Q, FINAL_GOODBYE,
    ensure_seed_room, generate_random_name,
    ensure_session_state, current_state, new_state,
    say_assistant, say_user, is_negative, mentions_no_experience,
    render_eligibility_panel,
    classify, answer_user_question_anytopic
)

# --------- Boot ---------
load_dotenv()
st.set_page_config(page_title="Happy Hauler Assistant", page_icon="🚚", layout="wide")

# Ensure conversations & current_room exist
ensure_session_state()
ensure_seed_room()

# Aliases
state = current_state()

# --------- Header ---------
st.header(f"💬 {st.session_state.current_room or 'Double Nickel Chatbot'}")
st.caption("🚀 Recruiting Assistant Chatbot Powered by Double Nickel")

# --------- Sidebar: Chats ---------
with st.sidebar:
    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown("### Chats")
    with col2:
        new_clicked = st.button("➕", key="btn_new_room", type="tertiary", help="New chat")

    if new_clicked:
        name = generate_random_name()
        st.session_state.conversations[name] = new_state()
        st.session_state.current_room = name
        st.rerun()

    rooms = list(st.session_state.conversations.keys())
    current_idx = rooms.index(st.session_state.current_room)
    selected = st.radio("Select a chat", rooms, index=current_idx)
    if selected != st.session_state.current_room:
        st.session_state.current_room = selected
        st.rerun()

# --------- Render history ---------
for m in state["history"]:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --------- First-load greeting ---------
if state["step"] == "greeting" and not state["has_greeted"]:
    say_assistant(GREETING)
    state["has_greeted"] = True
    state["step"] = "await_consent"
    with st.chat_message("assistant"):
        st.markdown(GREETING)

# --------- Lock helper ---------
def lock_and_rerun():
    state["input_enabled"] = False
    st.rerun()

# --------- Disabled pane (single place) ---------
if not state["input_enabled"]:
    st.chat_input(
        "Conversation ended. Please reach out to help@getdoublenickel.com for further assistance",
        disabled=True,
        key="chat_disabled",
    )
    st.divider()
    render_eligibility_panel(state)
    st.stop()

# --------- Active input ---------
user_text = st.chat_input("Type your reply")
if not user_text:
    st.stop()

# Process
say_user(user_text)
with st.chat_message("user"):
    st.markdown(user_text)

step = state["step"]

if step == "await_consent":
    result = classify(user_text, intent_hint="consent_boolean")
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
        lock_and_rerun()
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
