# OmegleBot
Brighten a stranger's day! An Omegle bot that continuously posts cheesy pickup lines!

# Requirements
* **Python** (>= 2.7.11, may work with earlier)
* **requests** (>= 2.18.4, may work with earlier)

# Installation
``pip install -r requirements.txt``

# Usage
``` python
from OmegleBot import OmegleBot

def main():
    topics = ["add", "your", "interests", "here"]
    omegle_bot = OmegleBot(wpm=68, topics=topics, save_chat_logs=False)
    omegle_bot.run()

if __name__ == "__main__":
    main()
```

## Notes
The bot will start out with a greeting message, and will then loop through a list of pickup lines and post one after each of the
stranger's replies. It will also simulate a typing delay to make it seem like less of a bot. It will also automatically disconnect and
reconnect if no reply is received after a long time.
