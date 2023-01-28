import os
import time
import logging

from datetime import datetime

logger = logging.getLogger("discord.cdn.utils")


def log_start():
    log_separator()
    logger.info(f"{get_date()} - Starting CDNBot...")
    log_separator()


def log_separator():
    logger.info("-----------------------------------------------------")


def get_discord_timestamp(relative=False):
    """Returns a formatted timestamp for use in Discord embeds or messages."""
    current_time = int(time.time())
    if relative:
        return f"<t:{current_time}:R>"
    else:
        return f"<t:{current_time}:f>"


def get_timestamp(day_only=False):
    if day_only:
        return datetime.now().strftime("%Y-%m-%d")
    else:
        return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def get_date():
    return datetime.now().strftime("%m-%d-%Y @ %H:%M")
