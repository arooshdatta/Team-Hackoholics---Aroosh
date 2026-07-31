from dotenv import load_dotenv
load_dotenv()
import litellm, json

text = "We're building a hackathon coaching bot called Huddle. Team of 5, deadline in 20 hours. Ayush knows Python and backend, Priya knows React and Figma, Arjun knows Python, Sana knows design, Rohan is new to coding."

prompt = (
    "Extract hackathon team setup info from this message. Return ONLY "
    "JSON, no markdown fences, matching exactly:\n"
    '{"team_name": string|null, "deadline_hours_from_now": number|null, '
    '"headcount": number|null, "skills": {"name": ["skill1","skill2"]}}\n\n'
    "If a field isn't mentioned, use null (or {} for skills).\n\n"
    f"Message:\n{text}"
)

response = litellm.completion(
    model="gemini/gemini-2.5-flash",
    messages=[{"role": "user", "content": prompt}],
)
raw = response["choices"][0]["message"]["content"]
print("=== RAW RESPONSE ===")
print(repr(raw))
print("=== END RAW ===")

cleaned = raw.strip()
if cleaned.startswith("```"):
    cleaned = cleaned.strip("`")
    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:]
    cleaned = cleaned.strip()

parsed = json.loads(cleaned)
print("=== PARSED ===")
print(json.dumps(parsed, indent=2))