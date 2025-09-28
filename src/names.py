import random
import streamlit as st
from src.state import new_state

# Randomly generate client's name
first_names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Timothy", "Kate", "Jane", "Kimberly", "Robert"]
last_names  = ["Smith", "Jones", "Williams", "Brown", "Davis", "James", "Miller", "Doe", "Kim", "Garcia"]

# Precompute all unique combinations once per process
_all_combos = [f"{f} {l}" for f in first_names for l in last_names]
random.shuffle(_all_combos)

def generate_random_name():
    if not _all_combos:
        raise RuntimeError("No more unique names available")
    return _all_combos.pop()

def ensure_seed_room():
    if "current_room" not in st.session_state or not st.session_state.current_room:
        name = generate_random_name()
        st.session_state.conversations[name] = new_state()
        st.session_state.current_room = name
