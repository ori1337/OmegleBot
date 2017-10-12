# OmegleBot v0.1
# Author: bhammel
# An Omegle bot that continuously posts pickup lines.

import json
import logging
import random
import re
import requests
import time
import urllib
import webbrowser

RESPONSES = [
    "Are you a magician? Because whenever I look at you, everyone else disappears!",
    "Did you sit in a pile of sugar? Cause you have a pretty sweet ass.",
    "Are you a camera? Because every time I look at you, I smile.",
    "Do you have a Band-Aid? Because I just scraped my knee falling for you.",
    "Do you know what my shirt is made of? Boyfriend material.",
    "Do you work at Starbucks? Because I like you a latte.",
    "If you were a vegetable you'd be a cute-cumber.",
    "I'm not a photographer, but I can picture me and you together.",
    "Do you have a pencil? Cause I want to erase your past and write our future.",
    "Are you religious? Because you're the answer to all my prayers.",
    "Are you my Appendix? Because I have a funny feeling in my stomach that makes me feel like I should take you out.",
    "Are you an interior decorator? Because when I saw you, the entire room became beautiful.",
    "Is your daddy a Baker? Because you've got some nice buns!",
    "I wanna live in your socks so I can be with you every step of the way.",
    "If God made anything more beautiful than you, I'm sure he'd keep it for himself.",
    "Do you have a map? I'm getting lost in your eyes.",
    "I don't have a library card, but do you mind if I check you out?",
    "Are you an orphanage? Cause I wanna give you kids.",
    "Do you have a sunburn, or are you always this hot?",
    "I was feeling a little off today, but you definitely turned me on.",
    "Are you a fruit, because Honeydew you know how fine you look right now?",
    "Sorry, but you owe me a drink. Because when I looked at you, I dropped mine.",
    "Even if there wasn't gravity on earth, I'd still fall for you.",
    "I'm not a hoarder but I really want to keep you forever.",
    "Are you a parking ticket? 'Cause you've got fine written all over you.",
    "You look cold. Want to use me as a blanket?",
    "Let me tie your shoes, cause I don't want you falling for anyone else.",
    "Do I know you? Cause you look exactly like my next girlfriend.",
    "I'm no organ donor but I'd be happy to give you my heart.",
    "I seem to have lost my phone number. Can I have yours?",
    "I'm not drunk, I'm just intoxicated by YOU.",
    "I was blinded by your beauty... I'm going to need your name and number for insurance purposes.",
    "Is there an airport nearby or is that just my heart taking off?",
    "I'm not staring at your boobs. I'm staring at your heart.",
    "Can I take your picture to prove to all my friends that angels do exist?",
    "Do you want to see a picture of a beautiful person? (holds up a mirror)",
    "There must be a lightswitch on my forehead because everytime I see you, you turn me on!"
]

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
    "front6", "front20", "front15", "front19", "front7", "front29", "front10", "front16", "front4", "front17", "front3",
    "front24", "front27", "front13", "front30", "front22", "front1", "front28", "front32", "front31", "front25",
    "front9", "front8", "front2", "front26", "front23", "front14", "front12", "front5", "front21", "front11", "front18"
]

class OmegleBot:
    SERVER_URL = "%s.omegle.com"
    BASE_URL = "https://%s/"
    START_URL = BASE_URL + "start?rcs=1&spid=&lang=en"
    SEND_URL = BASE_URL + "send"
    DISCONNECT_URL = BASE_URL + "disconnect"
    RECAPTCHA_URL = BASE_URL + "recaptcha"
    EVENTS_URL = BASE_URL + "events"
    TYPING_URL = BASE_URL + "typing"
    CAPTCHA_CHALLENGE_URL = "https://www.google.com/recaptcha/api/challenge?k=%s"
    CAPTCHA_IMAGE_URL = "http://www.google.com/recaptcha/api/image?c=%s"

    def __init__(self):
        self.server = ""
        self.cookies = None
        self.id = ""
        self.current_response_index = 0
        self.logger = logging.getLogger("OmegleBot")

    def run(self):
        self.start()
        self.process_forever()

    def process_forever(self):
        while True:
            disconnected = False
            try:
                events = self.get_events()
                if not events is None:
                    if len(events) == 0:
                        self.disconnect()
                        self.reconnect()
                        continue
                    for e in events:
                        if e[0] == "waiting":
                            self.handle_waiting()
                        elif e[0] == "count":
                            self.handle_count(e[1])
                        elif e[0] == "connected":
                            self.handle_connected()
                        elif e[0] == "typing":
                            self.handle_typing()
                        elif e[0] == "stoppedTyping":
                            self.handle_stoppedTyping()
                        elif e[0] == "gotMessage":
                            self.handle_gotMessage(e[1])
                        elif e[0] == "strangerDisconnected":
                            self.handle_strangerDisconnected()
                            disconnected = True
                        elif e[0] == "antinudeBanned":
                            self.handle_antinudeBanned()
                        elif e[0] == "recaptchaRequired":
                            self.handle_recaptchaRequired(e[1])
                        elif e[0] == "recaptchaRejected":
                            self.handle_recaptchaRejected(e[1])
                        elif e[0] == "identDigests":
                            pass
                        elif e[0] == "statusInfo":
                            pass
                        else:
                            self.handle_unrecognized(e)
            except Exception as ex:
                self.logger.error(ex.message)
            if disconnected:
                self.reconnect()

    def start(self):
        self.server = self.get_server()
        self.cookies = self.get_cookies()
        self.id = self.get_id()
        self.logger.info("Server: %s", self.server)
        self.logger.info("Cookies: %s", requests.utils.dict_from_cookiejar(self.cookies))
        self.logger.info("Got ID: %s", self.id)

    @staticmethod
    def get_server():
        return OmegleBot.SERVER_URL % random.choice(SERVER_LIST)

    def get_cookies(self):
        url = OmegleBot.BASE_URL % self.server
        r = requests.get(url)
        return r.cookies

    def get_id(self):
        url = OmegleBot.START_URL % self.server
        omegle_id = ""
        while not omegle_id.startswith("shard"):
            try:
                r = requests.post(url, headers=headers, cookies=self.cookies)
                omegle_id = r.content.strip("\"")
            except Exception as ex:
                self.logger.error(ex.message)
        return omegle_id

    def get_events(self):
        url = OmegleBot.EVENTS_URL % self.server
        data = "id=%s" % self.id
        r = requests.post(url, data, headers=headers, cookies=self.cookies)
        return json.loads(r.content)

    def reconnect(self):
        print "Reconnecting..."
        self.start()

    def send(self, msg):
        url = OmegleBot.SEND_URL % self.server
        data = "msg=%s&id=%s" % (urllib.quote_plus(msg), self.id)
        response_content = ""
        while response_content.strip() != "win":
            try:
                r = requests.post(url, data, headers=headers, cookies=self.cookies)
                response_content = r.content
            except Exception as ex:
                self.logger.error(ex.message)
        print "You: %s" % msg

    def disconnect(self):
        url = OmegleBot.DISCONNECT_URL % self.server
        data = "id=%s" % self.id
        response_content = ""
        while response_content.strip() != "win":
            try:
                r = requests.post(url, data, headers=headers, cookies=self.cookies)
                response_content = r.content
            except Exception as ex:
                self.logger.error(ex.message)
        print "You have disconnected."

    def recaptcha(self, challenge_k):
        recaptcha_challenge_regex = re.compile(r"challenge\s*:\s*'(.+)'")
        url = OmegleBot.CAPTCHA_CHALLENGE_URL % challenge_k
        r = requests.get(url, headers=headers, cookies=self.cookies)
        challenge = recaptcha_challenge_regex.search(r.content).group(1)
        url = OmegleBot.CAPTCHA_IMAGE_URL % challenge
        webbrowser.open_new(url)
        response = raw_input("Response: ")
        url = OmegleBot.RECAPTCHA_URL % self.server
        data = "challenge=%s&response=%s&id=%s" % (challenge, response, self.id)
        response_content = ""
        while response_content.strip() != "win":
            try:
                r = requests.post(url, data, headers=headers, cookies=self.cookies)
                response_content = r.content
            except Exception as ex:
                self.logger.error(ex.message)
        print "Response submitted."

    @staticmethod
    def handle_waiting():
        print "Waiting for a connection..."

    @staticmethod
    def handle_count(count):
        print "There are %s people connected to Omegle." % count

    def handle_connected(self):
        print "Connection established!"
        try:
            self.typing()
            time.sleep(2)
            self.send("Hi! Your day is about to get a whole lot better :)")
        except Exception as ex:
            self.logger.error(ex.message)

    @staticmethod
    def handle_typing():
        print "Stranger is typing..."

    @staticmethod
    def handle_stoppedTyping():
        print "Stranger stopped typing."

    def handle_gotMessage(self, msg):
        print "Stranger: %s" % msg
        try:
            self.typing()
            time.sleep(random.randint(4, 7))
            self.send(RESPONSES[self.current_response_index])
            self.current_response_index = (self.current_response_index + 1) % len(RESPONSES)
        except Exception as ex:
            self.logger.error(ex.message)

    def typing(self):
        url = OmegleBot.TYPING_URL % self.server
        data = "id=%s" % self.id
        response_content = ""
        while response_content.strip() != "win":
            try:
                r = requests.post(url, data, headers=headers, cookies=self.cookies)
                response_content = r.content
            except Exception as ex:
                self.logger.error(ex.message)

    @staticmethod
    def handle_strangerDisconnected():
        print "Stranger disconnected."

    @staticmethod
    def handle_antinudeBanned():
        print "Omegle thinks you should be a spy. Fuck Omegle."

    def handle_recaptchaRequired(self, challenge):
        print "Omegle thinks you're a bot (now where would it get a silly idea like that?). Fuckin Omegle. Check your browser."
        self.recaptcha(challenge)

    def handle_recaptchaRejected(self, challenge):
        print "Incorrect. Try again."
        self.recaptcha(challenge)

    @staticmethod
    def handle_unrecognized(e):
        print "Unrecognized event: %s" % json.dumps(e)

def main():
    logging.basicConfig(level=logging.INFO)
    omegle_bot = OmegleBot()
    omegle_bot.run()

if __name__ == '__main__':
    main()
