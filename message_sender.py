# message_sender.py
import os
import time
import webbrowser
import urllib.parse

try:
    import pyautogui
except Exception:
    pyautogui = None

class MessageSender:
    def __init__(self, speech):
        self.speech = speech

    def send_whatsapp(self, contact, message):
        """Send WhatsApp via WhatsApp Web"""
        try:
            encoded = urllib.parse.quote(message)
            # If contact is a number use this:
            # url = f"https://web.whatsapp.com/send?phone={contact}&text={encoded}"
            # If contact is a name use WhatsApp app:
            self.speech.speak(f"Opening WhatsApp to message {contact}")
            url = f"https://web.whatsapp.com/send?text={encoded}"
            webbrowser.open(url)
            self.speech.speak("WhatsApp opened. Please select the contact and send.")
        except Exception as e:
            self.speech.speak(f"WhatsApp error: {str(e)}")

    def send_email(self, to_email, subject, body):
        """Open default email app"""
        try:
            mailto = f"mailto:{to_email}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
            os.startfile(mailto)
            self.speech.speak(f"Email ready to send to {to_email}")
        except Exception as e:
            self.speech.speak(f"Email error: {str(e)}")

    def type_and_send(self, message):
        """Type message in current window and press enter"""
        time.sleep(0.5)
        pyautogui.typewrite(message, interval=0.04)
        time.sleep(0.3)
        pyautogui.press('enter')
        self.speech.speak("Message sent")

    def just_type(self, text):
        """Just type text without sending"""
        time.sleep(0.5)
        pyautogui.typewrite(text, interval=0.04)
        self.speech.speak("Typed")