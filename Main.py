import os
from pathlib import Path
from sqlalchemy.sql.functions import session_user
from utils.models import User, session, Problem
import lightbulb
import hikari
import dotenv
from utils.query import Query
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    # https://github.com/cheran-senthil/TLE/blob/bae59c2de6a2313be4a6ba4a5a5cbba81352e229/tle/__main__.py
    dotenv.load_dotenv()
    BOT_TOKEN = os.environ.get("JOMD_BOT_TOKEN")

    if not BOT_TOKEN:
        logger.critical("Missing bot token")
        return

    pref = "+"
    bot = lightbulb.BotApp(
        token=BOT_TOKEN, prefix=pref, banner=None, intents=hikari.Intents.ALL)

    bot.load_extensions_from("./extensions/")
    # TESTING
    # extensions = ["admin", "meta", "gitgud", "handles", "user", "plot"]
    # for extension in extensions:
    #     bot.load_extensions(f"extensions.{extension}")
    logger.debug("Extensions loaded: %s", ", ".join(bot.extensions))

    loop = asyncio.get_event_loop()
    # Get preliminary data
    if session.query(User).count() == 0:
        q = Query()
        loop.run_until_complete(q.get_users())
    if session.query(Problem).count() == 0:
        q = Query()
        loop.run_until_complete(q.get_problems())

    # Restrict bot usage to inside guild channels only.
    bot.check(lightbulb.checks.guild_only)
    # TODO Make something that will automatically fetch recent contests
    bot.run()


if __name__ == "__main__":
    main()
