import os
from flask import Flask, request

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")


@app.route("/", methods=["GET"])
def home():
    return "WhatsApp AI Agent is running", 200


# Meta uses this to verify our webhook
@app.route("/webhook", methods=["GET"])
def verify_webhook():

    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200

    return "Verification failed", 403


# WhatsApp messages will arrive here
@app.route("/webhook", methods=["POST"])
def receive_webhook():

    data = request.get_json()

    print("WhatsApp event:")
    print(data)

    return "EVENT_RECEIVED", 200
