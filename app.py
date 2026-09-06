import os
import requests

from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

client = OpenAI(api_key=OPENAI_API_KEY)


@app.route("/", methods=["GET"])
def home():
    return "WhatsApp AI Agent is running", 200


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200

    return "Verification failed", 403


def extract_message(data):
    try:
        value = data["entry"][0]["changes"][0]["value"]
        messages = value.get("messages", [])

        if not messages:
            return None

        message = messages[0]

        if message.get("type") != "text":
            return None

        return {
            "from": message.get("from"),
            "message_id": message.get("id"),
            "text": message["text"]["body"]
        }

    except (KeyError, IndexError, TypeError):
        return None


def analyze_message(text):
    prompt = f"""
You are an internal AI analyst for Violetta Laundry in Lebanon.

Analyze this customer WhatsApp message:

{text}

Return a concise structured analysis with:

Intent:
Choose one:
- pickup_request
- price_inquiry
- service_inquiry
- complaint
- b2b_lead
- delivery_question
- general_question
- other

Language:
Identify the customer's language.

Priority:
Choose:
- low
- medium
- high

Customer summary:
One short sentence.

Recommended next action:
One short sentence.

Important rules:
- Do not invent information.
- This analysis is internal only.
- Do not write a reply to the customer.
"""

    response = client.responses.create(
        model=OPENAI_MODEL,
        input=prompt
    )

    return response.output_text


def generate_customer_reply(text):
    prompt = f"""
You are the WhatsApp customer service assistant for Violetta Laundry in Lebanon.

Customer message:
{text}

Write a short, friendly WhatsApp reply.

Rules:
- Reply in the same language as the customer.
- Be concise and natural.
- Do not invent prices, schedules, delivery areas, or services.
- If information is missing, ask a short follow-up question.
- If the customer only says hello, greet them and ask how you can help.
- Do not mention that you are an AI.
"""

    response = client.responses.create(
        model=OPENAI_MODEL,
        input=prompt
    )

    return response.output_text


def send_whatsapp_message(to, message):
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        print("WhatsApp configuration missing")
        return None

    url = (
        f"https://graph.facebook.com/v23.0/"
        f"{PHONE_NUMBER_ID}/messages"
    )

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": message,
        },
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=15
    )

    print("WhatsApp send status:", response.status_code)
    print("WhatsApp send response:", response.text)

    return response


@app.route("/webhook", methods=["POST"])
def receive_webhook():
    data = request.get_json(silent=True) or {}

    print("WhatsApp event:")
    print(data)

    message = extract_message(data)

    if not message:
        return "EVENT_RECEIVED", 200

    print("Customer message:")
    print(message)

    try:
        analysis = analyze_message(message["text"])

        print("OpenAI Analysis:")
        print(analysis)

    except Exception as e:
        print("OpenAI analysis error:")
        print(str(e))

    try:
        reply = generate_customer_reply(message["text"])

        print("Customer reply:")
        print(reply)

        send_whatsapp_message(
            message["from"],
            reply
        )

    except Exception as e:
        print("Reply/send error:")
        print(str(e))

    return "EVENT_RECEIVED", 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "openai_configured": bool(OPENAI_API_KEY),
        "whatsapp_configured": bool(
            WHATSAPP_TOKEN and PHONE_NUMBER_ID
        )
    }), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
