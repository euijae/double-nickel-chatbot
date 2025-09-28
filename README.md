# Happy Hauler Recruiting Assistant

## Stack
- Streamlit
- OpenAI (Model: `GPT 4o Mini`)

## Highlight of the App

- Chatbot that screens truck-driver candidates for basic eligibility.
- Short, guided screening flow with up to 3 qualification questions.
- Answers common questions about the company or role (location, pay, days off, etc.).
- After each chat ends, shows an eligibility result and a brief summary.
- Past chats are viewable, each with its pass/fail mark.

## Conversation Flow

The app uses a deterministic conversation flow to check eligibility by asking three initial qualification questions. Once the candidate is found eligible, job-related questions are answered by GPT, guided by a system prompt that enforces the assistant's expected behavior.

State machine overview
1. Greeting -> The assistant opens with a friendly intro and asks to begin.
2. Consent Check
   - If the applicant clearly agrees, proceed. 
   - If not clear, the assistant sends a short persuasion line and moves on.
3. Qualification Questions (max 3)
   1. CDL - "Do you have a valid Class A CDL?"
      - No -> Early exit with a polite message. 
      - Yes -> proceed.
   2. Experience - "How many years of truck driving experience do you have?"
      - < 1 year or no experience → Early exit with a polite message.
      - ≥ 1 year -> proceed.
      - Ambiguous answer (e.g., "a while") -> assistant asks for an exact number.
   3. Nights - "This job requires being on the road for two nights each week. Is that okay?"
      - No -> Early exit with a polite message.
      - Yes -> proceed to Q&A.
   4. Post-screening Q&A
      - Assistant says: "Thank you. A recruiter will be in touch with you shortly. Do you have any questions about the role?"
      - The user may ask follow-up questions.
      - If a question is off-topic (unrelated to the job/company details), the assistant answers briefly and adds: "For non-role questions, please email us at help@getdoublenickel.com." Then the chat input is disabled for that conversation.
   5. Finish
      - The app displays an eligibility panel summarizing which requirements were met or missed.

Eligibility Rules
- Pass only if all are true:
  - Has a valid Class A CDL
  - ≥ 1 year of truck driving experience
  - Okay with two nights on the road each week
- Otherwise -> Not eligible (with reasons listed)

Chat History & Rooms
- Multiple chats ("rooms") are supported in the sidebar.
- Each chat shows a summary and pass/fail result after completion.


## Run it locally

Create a `.env` and copy the following into it

```
OPEN_API_KEY=
```

Then run the commands below to run the app
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run Main.py
```

## Demo

When the app runs, you’ll see demo chats in the sidebar.
Suggested examples include:
- Pass example
- Fail example — CDL
- Fail example — Nights
- Pass example with follow-up questions

_(If your app shows different example labels, update the list above to match your seeded chats.)_