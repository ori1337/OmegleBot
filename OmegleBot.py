# OmegleBot v0.1
# Author: bhammel
# Brighten a stranger's day! An Omegle bot that continuously posts cheesy pickup lines!

import errno
import json
import logging
import os
import Queue
import random
import re
import requests
import smtplib
import threading
import time
import urllib
import webbrowser
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

class OmegleBot:
    INTRO_MESSAGE = "hi! your day is about to get a whole lot better :)"

    headers = {
        'Connection': 'keep-alive',
        'Accept': 'application/json',
        'Origin': 'https://www.omegle.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36',
        'Content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Referer': 'https://www.omegle.com/',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.8'
    }

    SERVER_LIST = [
        "front6", "front20", "front15", "front19", "front7", "front29", "front10", "front16", "front4", "front17",
        "front3", "front24", "front27", "front13", "front30", "front22", "front1", "front28", "front32", "front31",
        "front25", "front9", "front8", "front2", "front26", "front23", "front14", "front12", "front5", "front21",
        "front11", "front18"
    ]

    SERVER_URL =                "%s.omegle.com"
    BASE_URL =                  "https://%s/"
    STATUS_URL =                "https://%s/status?nocache=%s&randid=%s"
    START_URL =                 "https://%s/start?rcs=1&spid=&lang=en"
    RECAPTCHA_URL =             "https://%s/recaptcha"
    EVENTS_URL =                "https://%s/events"
    TYPING_URL =                "https://%s/typing"
    STOPPED_TYPING_URL =        "https://%s/stoppedtyping"
    DISCONNECT_URL =            "https://%s/disconnect"
    SEND_URL =                  "https://%s/send"
    STOP_COMMON_LIKES_URL =     "https://%s/stoplookingforcommonlikes"

    RECAPTCHA_CHALLENGE_URL =   "https://www.google.com/recaptcha/api/challenge?k=%s"
    RECAPTCHA_IMAGE_URL =       "http://www.google.com/recaptcha/api/image?c=%s"
    recaptcha_challenge_regex = re.compile(r"challenge\s*:\s*'(.+)'")

    CHATS_FOLDER = "chats"

    def __init__(self, wpm=42, topics=None, save_chat_logs=False, email_address="", email_password=""):
        logging.basicConfig(level=logging.INFO)
        self.server = ""
        self.cookies = None
        self.id = ""
        self.unmon = False
        self.responses = [line.strip().lower() for line in open("responses.txt")]
        self.current_response_index = 0
        self.topics = topics
        self.no_common_likes_found = False
        self.wpm = wpm
        self.email_address = email_address
        self.email_password = email_password
        self.is_typing = False
        self.typing_lock = threading.Lock()
        self.response_queue = Queue.Queue()
        self.typing_thread = threading.Thread(target=self.get_next_message)
        self.logger = logging.getLogger("OmegleBot")
        self.save_chat_logs = save_chat_logs
        self.file = None
        if self.save_chat_logs:
            self.create_chats_folder()
        self.typing_thread.start()

    def get_next_message(self):
        while True:
            try:
                msg, delay, client_id = self.response_queue.get()
                if client_id == self.id:
                    if self.typing_lock.acquire(False):
                        self.is_typing = True
                        self.send_message(msg, delay, client_id)
                        self.is_typing = False
                        self.typing_lock.release()
            except Exception as ex:
                self.logger.error(ex.message)
            finally:
                self.response_queue.task_done()

    def send_message(self, msg, delay, client_id):
        typing_time = self.calculate_typing_time(len(msg))
        time.sleep(delay)
        if client_id != self.id:
            return
        self.typing()
        time.sleep(typing_time)
        if client_id != self.id:
            return
        self.send(msg)

    def calculate_typing_time(self, msg_len):
        return float(msg_len * 12) / self.wpm

    def create_chats_folder(self):
        try:
            os.makedirs(self.CHATS_FOLDER)
        except OSError as ex:
            if ex.errno != errno.EEXIST:
                raise

    def run(self):
        self.start()
        self.process_forever()

    def start(self):
        if self.save_chat_logs:
            self.close_file()
        print("Connecting to server...")
        self.server = self.get_server()
        self.cookies = self.get_cookies()
        self.id = self.get_id()
        self.logger.info("Server:   %s", self.server)
        self.logger.info("ClientID: %s", self.id)
        self.unmon = False
        self.no_common_likes_found = False

    def close_file(self):
        try:
            if not self.file is None:
                self.file.close()
                self.file = None
        except Exception as ex:
            self.logger.error(ex.message)

    def get_server(self):
        return self.SERVER_URL % random.choice(self.SERVER_LIST)

    def get_cookies(self):
        url = self.BASE_URL % self.server
        r = requests.get(url)
        return r.cookies

    def get_id(self):
        url = self.START_URL % self.server
        if self.unmon:
            url += "&group=unmon"
        if not self.topics is None:
            url += "&" + urllib.urlencode({"topics": json.dumps(self.topics)})
        omegle_id = ""
        while len(omegle_id) < 10:
            try:
                r = requests.post(url, headers=self.headers, cookies=self.cookies)
                omegle_id = r.content.strip('"')
            except Exception as ex:
                self.logger.error(ex.message)
        return omegle_id

    def process_forever(self):
        while True:
            disconnect = False
            restart = False
            try:
                events = self.get_events()
                if events is None or len(events) == 0:
                    self.disconnect()
                    self.start()
                    continue
                for e in events:
                    if e[0] == "waiting":
                        self.handle_waiting()
                    elif e[0] == "connected":
                        self.handle_connected()
                        self.send_greeting()
                    elif e[0] == "typing":
                        self.handle_typing()
                    elif e[0] == "stoppedTyping":
                        self.handle_stoppedTyping()
                    elif e[0] == "gotMessage":
                        self.handle_gotMessage(e[1])
                        if self.is_self(e[1]):
                            disconnect = True
                            restart = True
                        else:
                            self.send_response()
                    elif e[0] == "commonLikes":
                        self.handle_commonLikes(e[1])
                    elif e[0] == "strangerDisconnected":
                        self.handle_strangerDisconnected()
                        restart = True
                    elif e[0] == "antinudeBanned":
                        self.handle_antinudeBanned()
                        self.unmon = True
                    elif e[0] == "recaptchaRequired":
                        self.handle_recaptchaRequired(e[1])
                    elif e[0] == "recaptchaRejected":
                        self.handle_recaptchaRejected(e[1])
                    elif e[0] == "serverMessage":
                        self.handle_serverMessage(e[1])
                    elif e[0] == "identDigests":
                        self.handle_identDigests()
                    elif e[0] == "statusInfo":
                        self.handle_statusInfo()
                    else:
                        print("Unhandled event: %s" % e)
            except Exception as ex:
                self.logger.error(ex.message)
            if disconnect:
                self.disconnect()
            if restart:
                self.start()

    def get_events(self):
        url = self.EVENTS_URL % self.server
        data = "id=%s" % self.id
        events = None
        keep_trying = True
        while keep_trying:
            try:
                t = threading.Timer(10, self.stop_looking_for_common_likes)
                t.start()
                r = requests.post(url, data, headers=self.headers, cookies=self.cookies)
                t.cancel()
                events = json.loads(r.content)
                keep_trying = False
            except Exception as ex:
                self.logger.error(ex.message)
        return events

    def stop_looking_for_common_likes(self):
        url = self.STOP_COMMON_LIKES_URL % self.server
        data = "id=%s" % self.id
        response_content = ""
        while response_content.strip() != "win":
            try:
                r = requests.post(url, data, headers=self.headers, cookies=self.cookies)
                response_content = r.content
            except Exception as ex:
                self.logger.error(ex.message)
        self.no_common_likes_found = True

    def send(self, msg):
        url = self.SEND_URL % self.server
        data = "msg=%s&id=%s" % (urllib.quote_plus(msg), self.id)
        response_content = ""
        while response_content.strip() != "win":
            try:
                r = requests.post(url, data, headers=self.headers, cookies=self.cookies)
                response_content = r.content
            except Exception as ex:
                self.logger.error(ex.message)
        print("You: %s" % msg)
        if self.save_chat_logs:
            self.write_message_to_file("You: %s" % msg)

    def disconnect(self):
        url = self.DISCONNECT_URL % self.server
        data = "id=%s" % self.id
        response_content = ""
        while response_content.strip() != "win":
            try:
                r = requests.post(url, data, headers=self.headers, cookies=self.cookies)
                response_content = r.content
            except Exception as ex:
                self.logger.error(ex.message)
        print("You have disconnected.")

    def recaptcha(self, challenge, response):
        url = self.RECAPTCHA_URL % self.server
        data = "challenge=%s&response=%s&id=%s" % (challenge, response, self.id)
        response_content = ""
        while response_content.strip() != "win":
            try:
                r = requests.post(url, data, headers=self.headers, cookies=self.cookies)
                response_content = r.content
            except Exception as ex:
                self.logger.error(ex.message)
        print("Response submitted.")

    def typing(self):
        url = self.TYPING_URL % self.server
        data = "id=%s" % self.id
        response_content = ""
        while response_content.strip() != "win":
            try:
                r = requests.post(url, data, headers=self.headers, cookies=self.cookies)
                response_content = r.content
            except Exception as ex:
                self.logger.error(ex.message)
        print("You are typing...")

    def is_self(self, msg):
        return msg.strip() == self.INTRO_MESSAGE

    def send_greeting(self):
        try:
            self.response_queue.put((self.INTRO_MESSAGE, 0.5, self.id))
        except Exception as ex:
            self.logger.error(ex.message)

    def send_response(self):
        try:
            if self.is_typing:
                return
            response = self.responses[self.current_response_index]
            self.current_response_index = (self.current_response_index + 1) % len(self.responses)
            self.response_queue.put((response, 2, self.id))
        except Exception as ex:
            self.logger.error(ex.message)

    @staticmethod
    def handle_waiting():
        print("Looking for someone you can chat with...")

    def handle_connected(self):
        print("You're now chatting with a random stranger. Say hi!")
        if self.no_common_likes_found:
            print("Omegle couldn't find anyone who shares interests with you, so this stranger is completely random. Try adding more interests!")

    @staticmethod
    def handle_typing():
        print("Stranger is typing...")

    @staticmethod
    def handle_stoppedTyping():
        print("Stranger has stopped typing.")

    def handle_gotMessage(self, msg):
        print("Stranger: %s" % msg)
        if self.save_chat_logs:
            self.write_message_to_file("Stranger: %s" % msg)

    @staticmethod
    def handle_commonLikes(likes):
        print("You both like %s." % ", ".join(likes))

    @staticmethod
    def handle_strangerDisconnected():
        print("Stranger has disconnected.")

    @staticmethod
    def handle_antinudeBanned():
        print("Omegle thinks you should be a spy. Fuck Omegle.")

    def handle_recaptchaRequired(self, challenge_k):
        print("Omegle thinks you're a bot (now where would it get a silly idea like that?). Fuckin Omegle. Check your browser.")
        challenge, response = self.get_captcha_response(challenge_k)
        self.recaptcha(challenge, response)

    def handle_recaptchaRejected(self, challenge_k):
        print("Incorrect. Try again.")
        challenge, response = self.get_captcha_response(challenge_k)
        self.recaptcha(challenge, response)

    @staticmethod
    def handle_serverMessage(msg):
        print(msg)

    def handle_identDigests(self):
        pass

    def handle_statusInfo(self):
        pass

    def write_message_to_file(self, msg):
        try:
            if self.file is None:
                self.file = open(os.path.join(self.CHATS_FOLDER, self.id.replace(":", "_") + ".txt"), "w+")
            self.file.write(msg.encode("utf8") + "\n")
        except Exception as ex:
            self.logger.error(ex.message)

    def get_captcha_response(self, challenge_k):
        url = self.RECAPTCHA_CHALLENGE_URL % challenge_k
        r = requests.get(url, headers=self.headers, cookies=self.cookies)
        challenge = self.recaptcha_challenge_regex.search(r.content).group(1)
        url = self.RECAPTCHA_IMAGE_URL % challenge
        webbrowser.open_new(url)
        response = raw_input("Response: ")
        return challenge, response

    def send_email(self, subject, body):
        try:
            msg = MIMEMultipart()
            msg["From"] = self.email_address
            msg["To"] = self.email_address
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.ehlo()
            server.starttls()
            server.login(self.email_address, self.email_password)
            server.sendmail(self.email_address, self.email_address, msg.as_string())
            server.quit()
        except Exception as ex:
            self.logger.error(ex.message)
