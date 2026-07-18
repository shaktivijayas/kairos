import json

from google import genai
from google.genai import types

from kairos import config

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


CLASSIFY_PROMPT = """You are a transaction classifier for an Indian small-business compliance tool.
Given a bank SMS alert, return a JSON object with these keys:
"classification" ("business" or "personal"), "amount" (number), "payment_mode" ("cash", "upi", "card", or "unknown"), "vendor_name" (string or null).
SMS: {text}"""


def classify_transaction(text):
    client = _get_client()
    response = client.models.generate_content(
        model=config.GEMMA_MODEL,
        contents=CLASSIFY_PROMPT.format(text=text),
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return json.loads(response.text)


DOCUMENT_PROMPT = """You are reading a photographed Indian business invoice or cash slip.
Return a JSON object with these keys:
"vendor_name" (string or null), "vendor_gstin" (string or null), "invoice_number" (string or null),
"amount" (number or null), "category_hint" (short string describing what was purchased, or null)."""


def read_document_image(image_bytes, mime_type="image/jpeg"):
    client = _get_client()
    response = client.models.generate_content(
        model=config.GEMMA_MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            DOCUMENT_PROMPT,
        ],
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return json.loads(response.text)


ANSWER_PROMPT = """You are KAIROS, a compliance assistant for an Indian micro-merchant. Answer plainly and briefly.
Always end with: "Worth reviewing with your CA before you act."
Context (recent transactions and flags): {context}
Question: {question}"""


def answer_question(question, context):
    client = _get_client()
    response = client.models.generate_content(
        model=config.GEMMA_MODEL,
        contents=ANSWER_PROMPT.format(context=json.dumps(context), question=question),
    )
    return response.text
