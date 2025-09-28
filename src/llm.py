# src/llm.py
import os
import json
import re
from dotenv import load_dotenv
from openai import OpenAI
from .constants import PAY_LINE, OFFTOPIC_NOTE

load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")

def _client():
    return OpenAI(api_key=API_KEY) if API_KEY else None

def classify(user_text: str, intent_hint: str = "generic"):
    """
    Classify user intent using OpenAI's API.
    :param user_text: user text
    :param intent_hint: type of intent to classify
    :return: type of intent to classify
    """
    client = _client()
    if client is None:
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
    # prompt
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

def is_truck_related(text: str) -> bool:
    """
    Determine if a text is related to a truck.
    :param text: question text
    :return: true if related question is truck related
    """
    t = (text or "").strip().lower()
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

    client = _client()
    if client is None:
        return False

    system = (
        "You are a binary classifier. Return exactly 'truck' if the user's message is about a truck driving job "
        "or company/job details (requirements, pay/compensation, location/where the job is based, schedule/home time, "
        "days off/PTO/vacation, benefits, routes/lanes, equipment, policies, HOS/DOT, CDL, endorsements, etc.). "
        "Otherwise return exactly 'other'."
    )
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": text}],
    )
    label = (resp.choices[0].message.content or "").strip().lower()
    return label == "truck"

def answer_user_question(user_question_text: str) -> str:
    """
    answer user question using OpenAI's API.
    :param user_question_text: question text
    :return: answer text
    """
    t = (user_question_text or "").lower()
    if any(k in t for k in ["pay", "salary", "wage", "rate", "cents per mile", "compensation", "money"]):
        return PAY_LINE

    client = _client()
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

def answer_user_question_anytopic(user_text: str) -> tuple[str, bool]:
    """
    Answer user's any question using OpenAI's API
    :param user_text: question text
    :return: answer text and true if truck related false otherwise
    """
    t = (user_text or "").lower()
    if any(k in t for k in ["pay", "salary", "wage", "rate", "cents per mile", "compensation", "money"]):
        return PAY_LINE, True

    client = _client()
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
        "still provide a brief, polite response, and do not encourage follow-up in chat; instead, they should email."
    )
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user_text}],
    )
    core = resp.choices[0].message.content.strip()
    return (core, True) if on_topic else (f"{core}\n\n The eligibility result will be displayed below. Thank you for taking the time to chat with us. \n\n{OFFTOPIC_NOTE}", False)
