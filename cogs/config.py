import os

from enum import StrEnum
from .locale import Locales

## GLOBAL CONFIGURATION

FETCH_INTERVAL = 5


class Region:
    def __init__(self, region_name: str, valid_locales: list):
        self.name = region_name
        self.locales = valid_locales


region_US = Region("us", [Locales.en_US, Locales.es_MX, Locales.pt_BR])
region_EU = Region(
    "eu",
    [
        Locales.en_GB,
        Locales.es_ES,
        Locales.fr_FR,
        Locales.ru_RU,
        Locales.de_DE,
        Locales.pt_PT,
        Locales.it_IT,
    ],
)
region_KR = Region("kr", [Locales.ko_KR])
region_TW = Region("tw", [Locales.zh_TW])
region_CN = Region("cn", [Locales.zh_CN])

SUPPORTED_REGIONS = [region_US, region_EU, region_KR, region_TW, region_CN]
SUPPORTED_REGIONS_STRINGS = [region.name for region in SUPPORTED_REGIONS]
DEFAULT_REGION = region_US


class SUPPORTED_GAMES(StrEnum):
    """Supported Games"""

    Warcraft = "wow"
    Diablo4 = "d4"


class SUPPORTED_PRODUCTS(StrEnum):
    """Supported Branches"""

    # if a product branch name (the key) does not include "wow", it will not be tweeted
    # WoW products
    wow = "Retail"
    wowt = "Retail PTR"
    wow_beta = "Beta"
    wowxptr = "Retail PTR 2"
    wow_classic = "WotLK Classic"
    wow_classic_beta = "Classic Beta"
    wow_classic_ptr = "WotLK Classic PTR"
    wow_classic_era = "Classic Era"
    wow_classic_era_beta = "Classic Era Beta"
    wow_classic_era_ptr = "Classic Era PTR"
    wowz = "Submission"
    wowlivetest = "Live Test"
    wowdev = "Internal"
    wowdev2 = "Internal 2"
    wowdev3 = "Internal 3"
    wowv = "Vendor"
    wowv2 = "Vendor 2"
    wowv3 = "Vendor 3"
    wowv4 = "Vendor 4"
    wowe1 = "Event"
    wowe2 = "Event 2"
    wowe3 = "Event 3"
    wowdemo = "Demo"
    # Diablo 4 products
    fenris = "Diablo IV"
    fenrisb = "Diablo IV Beta"
    fenrisdev = "Diablo IV Internal"
    fenrisdev2 = "Diablo IV Internal 2"
    fenrise = "Diablo IV Event"
    fenrisvendor1 = "Diablo IV Vendor"
    fenrisvendor2 = "Diablo IV Vendor 2"
    fenrisvendor3 = "Diablo IV Vendor 3"

    @classmethod
    def has_key(cls, value):
        return value in cls._member_names_


class Indices:
    LAST_UPDATED_BY = "last_updated_by"
    LAST_UPDATED_AT = "last_updated_at"
    BUILDINFO = "buildInfo"
    BUILD = "build"
    BUILDTEXT = "build_text"


## CACHE CONFIGURATION


class CacheStrings:
    ## STRINGS
    REGION_UPDATED = "Region updated."
    REGION_LOCALE_CHANGED = "Region updated and locale reset."

    LOCALE_UPDATED = "Locale updated."

    ## LOGGING STRINGS
    LOG_FETCH_DATA = "Fetching CDN data..."
    LOG_PARSE_DATA = "Parsing CDN response..."


class CacheDefaults:
    CHANNEL = 0000
    WATCHLIST = ["wow", "wowt", "wow_beta"]
    REGION = DEFAULT_REGION
    REGION_NAME = REGION.name
    LOCALE = REGION.locales[0]
    LOCALE_NAME = LOCALE.value
    BUILD = "0.0.0"
    BUILDTEXT = "no-data"


class Settings:
    __defaults = CacheDefaults()

    CHANNEL = {"name": "channel", "default": __defaults.CHANNEL}
    D4_CHANNEL = {"name": "d4_channel", "default": __defaults.CHANNEL}
    WATCHLIST = {"name": "watchlist", "default": __defaults.WATCHLIST}
    REGION = {"name": "region", "default": __defaults.REGION_NAME}
    LOCALE = {"name": "locale", "default": __defaults.LOCALE_NAME}

    KEYS = ["channel", "d4_channel", "watchlist", "region", "locale"]


class ErrorStrings:
    REGION_SAME_AS_CURRENT = "New region is the same as the current region."
    REGION_NOT_SUPPORTED = "Region not supported."

    LOCALE_SAME_AS_CURRENT = "New locale is the same as the current locale."
    LOCALE_NOT_SUPPORTED = "Locale not supported by your region."

    # TODO: replace the hardcoded command with a clickable button to the command
    VIEW_VALID_BRANCHES = "View all valid branches with {cmdlink}."

    BRANCH_NOT_VALID = "Branch is not a valid product."
    BRANCH_ALREADY_IN_WATCHLIST = "Branch is already on your watchlist."

    WATCHLIST_CANNOT_BE_EMPTY = "You cannot remove the last branch from your watchlist."

    ARG_BRANCH_NOT_ON_WATCHLIST = "Specified branch is not on your watchlist."
    ARG_BRANCH_NOT_VALID = "Specified branch is not a valid product."

    OK = "OK"


class CommonURL:
    HTTPS = "http://"
    CDN_URL = ".patch.battle.net:1119/"  # does not include region


class CacheConfig:
    CDN_URL = "http://us.patch.battle.net:1119/"

    PRODUCTS = SUPPORTED_PRODUCTS
    AREAS_TO_CHECK_FOR_UPDATES = ["build", "build_text"]
    CACHE_FOLDER_NAME = "cache"
    CACHE_FILE_NAME = "cdn.json"

    GUILD_CFG_FILE_NAME = "guild_cfg.json"

    SUPPORTED_REGIONS = SUPPORTED_REGIONS
    SUPPORTED_REGIONS_STRING = SUPPORTED_REGIONS_STRINGS

    FILE_BACKUP_COUNT = 10

    REQUIRED_KEYS_DEFAULTS = {
        "region": "us",
        "build_config": "no-data",
        "cdn_config": "no-data",
        "build": "no-data",
        "build_text": "no-data",
        "product_config": "no-data",
        "encrypted": None,
    }

    settings = Settings()
    strings = CacheStrings()
    indices = Indices()
    defaults = CacheDefaults()
    errors = ErrorStrings()
    urls = CommonURL()

    def __init__(self):
        self.CDN_URL = (
            self.urls.HTTPS + self.settings.REGION["default"] + self.urls.CDN_URL
        )

    @staticmethod
    def is_valid_branch(branch) -> bool:
        return SUPPORTED_PRODUCTS.has_key(branch)


## COMMON CONFIGURATION


class CommonStrings:
    EMBED_FOOTER = f"Data provided by Algalon {os.getenv('ENVIRONMENT', 'Dev')}."
    VALID_REGIONS = SUPPORTED_REGIONS_STRINGS

    SPEECH = "$$dalaran.speech$$"


## WATCHER CONFIGURATION


class WatcherStrings:
    EMBED_WOWTOOLS_TITLE = "wow.tools builds page"
    EMBED_WOWTOOLS_URL = "https://wow.tools/builds/"

    EMBED_WAGOTOOLS_TITLE = "wago.tools"
    EMBED_WAGOTOOLS_URL = "https://wago.tools/"

    EMBED_DIABLO_TITLE = "Diablo 4"

    EMBED_NAME = "Blizzard CDN Update"
    EMBED_NAME_WOW = "Warcraft CDN Update"
    EMBED_NAME_D4 = "Diablo 4 CDN Update"

    EMBED_ICON_URL = (
        "https://bnetcmsus-a.akamaihd.net/cms/gallery/D2TTHKAPW9BH1534981363136.png"
    )
    EMBED_ICON_URL_WOW = "https://blz-contentstack-images.akamaized.net/v3/assets/blt72f16e066f85e164/bltc3d5627fa96394bf/world-of-warcraft.webp?width=96&format=webply&quality=95"
    EMBED_ICON_URL_D4 = "https://blz-contentstack-images.akamaized.net/v3/assets/blt72f16e066f85e164/blt15336eccf10cd269/diablo-IV.webp?width=96&format=webply&quality=95"

    EMBED_UPDATE_TITLE = "Build Updates"

    EMBED_GAME_STRINGS = {
        "wow": {
            "title": EMBED_WAGOTOOLS_TITLE,
            "url": EMBED_WAGOTOOLS_URL,
            "name": EMBED_NAME_WOW,
            "icon_url": EMBED_ICON_URL_WOW,
        },
        "d4": {
            "title": EMBED_DIABLO_TITLE,
            "url": None,
            "name": EMBED_NAME_D4,
            "icon_url": EMBED_ICON_URL_D4,
        },
    }


class WatcherConfig:
    strings = WatcherStrings
    indices = Indices
    cache_defaults = CacheDefaults


## BLIZZARD API CONFIGURATION


class BlizzardAPIConfig:
    assets = {
        "token_icon": "https://wow.zamimg.com/images/wow/icons/large/wow_token01.jpg"
    }


## DEBUG CONFIGURATION


class DebugConfig:
    debug_enabled = os.getenv("DEBUG", False)
    debug_guild_id = os.getenv("DEBUG_GUILD_ID")
    debug_channel_id = os.getenv("DEBUG_CHANNEL_ID")
    debug_channel_id_d4 = os.getenv("DEBUG_CHANNEL_ID_D4")

    debug_channel_id_by_game = {
        "wow": debug_channel_id,
        "d4": debug_channel_id_d4,
    }
