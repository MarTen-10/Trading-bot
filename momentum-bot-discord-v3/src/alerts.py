import logging, requests, json

class Alerts:
    def __init__(self, webhook_url:str=""):
        self.webhook_url = webhook_url

    def send(self, msg:str):
        logging.info(f"ALERT: {msg}")
        if not self.webhook_url:
            return
        try:
            payload = {"content": msg}
            headers = {"Content-Type": "application/json"}
            requests.post(self.webhook_url, data=json.dumps(payload), headers=headers, timeout=10)
        except Exception as e:
            logging.error(f"Discord alert error: {e}")
