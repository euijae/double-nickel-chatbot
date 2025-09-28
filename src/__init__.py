__version__ = "0.1.0"

# Re-export frequently-used items for a tidy public API.
from .constants import (
    GREETING, PERSUASION_WITH_CDL, OFFTOPIC_NOTE,
    CDL_QUESTION, YEARS_QUESTION, YEARS_FOLLOWUP, NIGHTS_QUESTION,
    EARLY_EXIT_CDL, EARLY_EXIT_YEARS, EARLY_EXIT_NIGHTS,
    POST_THANKS_AND_Q, FINAL_GOODBYE, PAY_LINE,
)

from .state import (
    new_state, ensure_session_state, current_state,
    say_assistant, say_user, is_negative, mentions_no_experience,
    render_eligibility_panel,
)

from .llm import (
    classify, is_truck_related,
    answer_user_question, answer_user_question_anytopic,
)

from .names import generate_random_name, ensure_seed_room

__all__ = [
    # constants
    "GREETING", "PERSUASION_WITH_CDL", "OFFTOPIC_NOTE",
    "CDL_QUESTION", "YEARS_QUESTION", "YEARS_FOLLOWUP", "NIGHTS_QUESTION",
    "EARLY_EXIT_CDL", "EARLY_EXIT_YEARS", "EARLY_EXIT_NIGHTS",
    "POST_THANKS_AND_Q", "FINAL_GOODBYE", "PAY_LINE",
    # state helpers
    "new_state", "ensure_session_state", "current_state",
    "say_assistant", "say_user", "is_negative", "mentions_no_experience",
    "render_eligibility_panel",
    # llm utils
    "classify", "is_truck_related",
    "answer_user_question", "answer_user_question_anytopic",
    # names
    "generate_random_name", "ensure_seed_room",
]
