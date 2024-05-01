import os
import json

from typing import Optional
from enum import StrEnum
from .locale import Locales

## GLOBAL CONFIGURATION

FETCH_INTERVAL = 5


class Singleton:
    __instance = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)

        return cls.__instance


class Region(Singleton):
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
    Gryphon = "gryphon"
    BattleNet = "bnet"


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
    wowlivetest2 = "Live Test Internal"
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
    fenristest = "Diablo IV PTR"
    fenrisdev = "Diablo IV Internal"
    fenrisdev2 = "Diablo IV Internal 2"
    fenrise = "Diablo IV Event"
    fenrisvendor1 = "Diablo IV Vendor"
    fenrisvendor2 = "Diablo IV Vendor 2"
    fenrisvendor3 = "Diablo IV Vendor 3"
    # Rumble
    gryphon = "Warcraft Rumble Live"
    gryphonb = "Warcraft Rumble Beta"
    gryphondev = "Warcraft Rumble Internal"
    # Bnet
    catalogs = "Catalogs"

    @classmethod
    def has_key(cls, value):
        return value in cls._member_names_


TEST_BRANCHES = [
    SUPPORTED_PRODUCTS.wowt,
    SUPPORTED_PRODUCTS.wowxptr,
    SUPPORTED_PRODUCTS.wow_beta,
    SUPPORTED_PRODUCTS.wowlivetest,
    SUPPORTED_PRODUCTS.wow_classic_beta,
    SUPPORTED_PRODUCTS.wow_classic_ptr,
    SUPPORTED_PRODUCTS.wow_classic_era_beta,
    SUPPORTED_PRODUCTS.wow_classic_era_ptr,
    SUPPORTED_PRODUCTS.fenrisb,
    SUPPORTED_PRODUCTS.fenristest,
    SUPPORTED_PRODUCTS.gryphonb,
]


class Indices(Singleton):
    LAST_UPDATED_BY = "last_updated_by"
    LAST_UPDATED_AT = "last_updated_at"
    BUILDINFO = "buildInfo"
    BUILD = "build"
    BUILDTEXT = "build_text"


## CACHE CONFIGURATION


class CacheStrings(Singleton):
    ## STRINGS
    REGION_UPDATED = "Region updated."
    REGION_LOCALE_CHANGED = "Region updated and locale reset."

    LOCALE_UPDATED = "Locale updated."

    ## LOGGING STRINGS
    LOG_FETCH_DATA = "Fetching CDN data..."
    LOG_PARSE_DATA = "Parsing CDN response..."


class CacheDefaults(Singleton):
    CHANNEL = 0000
    WATCHLIST = ["wow", "wowt", "wow_beta"]
    REGION = DEFAULT_REGION
    REGION_NAME = REGION.name
    LOCALE = REGION.locales[0]
    LOCALE_NAME = LOCALE.value
    BUILD = "0.0.0"
    BUILDTEXT = "no-data"


class Settings(Singleton):
    __defaults = CacheDefaults()

    CHANNEL = {"name": "channel", "default": __defaults.CHANNEL}
    D4_CHANNEL = {"name": "d4_channel", "default": __defaults.CHANNEL}
    GRYPHON_CHANNEL = {"name": "gryphon_channel", "default": __defaults.CHANNEL}
    BNET_CHANNEL = {"name": "bnet_channel", "default": __defaults.CHANNEL}
    WATCHLIST = {"name": "watchlist", "default": __defaults.WATCHLIST}
    REGION = {"name": "region", "default": __defaults.REGION_NAME}
    LOCALE = {"name": "locale", "default": __defaults.LOCALE_NAME}

    KEYS = [
        "channel",
        "d4_channel",
        "gryphon_channel",
        "bnet_channel",
        "watchlist",
        "region",
        "locale",
    ]


class Setting:
    def __init__(self, name, default):
        self.name = name
        self.default = default


class UserSettings(Singleton):
    WATCHLIST = Setting("watchlist", ["wow"])


class ErrorStrings(Singleton):
    REGION_SAME_AS_CURRENT = "New region is the same as the current region."
    REGION_NOT_SUPPORTED = "Region not supported."

    LOCALE_SAME_AS_CURRENT = "New locale is the same as the current locale."
    LOCALE_NOT_SUPPORTED = "Locale not supported by your region."

    VIEW_VALID_BRANCHES = "View all valid branches with {cmdlink}."

    BRANCH_NOT_VALID = "Branch is not a valid product."
    BRANCH_ALREADY_IN_WATCHLIST = "Branch is already on your watchlist."

    WATCHLIST_CANNOT_BE_EMPTY = "You cannot remove the last branch from your watchlist."

    ARG_BRANCH_NOT_ON_WATCHLIST = "Specified branch is not on your watchlist."
    ARG_BRANCH_NOT_VALID = "Specified branch is not a valid product."

    OK = "OK"


class CommonURL(Singleton):
    HTTPS = "http://"
    CDN_URL = ".patch.battle.net:1119/"  # does not include region


class CacheConfig(Singleton):
    CDN_URL = "http://us.patch.battle.net:1119/"

    PRODUCTS = SUPPORTED_PRODUCTS
    AREAS_TO_CHECK_FOR_UPDATES = ["build", "build_text"]
    CACHE_FOLDER_NAME = "cache"
    CACHE_FILE_NAME = "cdn.json"

    GUILD_CFG_FILE_NAME = "guild_cfg.json"
    USER_CFG_FILE_NAME = "user_cfg.json"

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
        "seqn": 0,
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


class CommonStrings(Singleton):
    EMBED_FOOTER = f"Data provided by Algalon {os.getenv('ENVIRONMENT', 'Dev')}."
    VALID_REGIONS = SUPPORTED_REGIONS_STRINGS

    SPEECH = "$$dalaran.speech$$"


## WATCHER CONFIGURATION


class WatcherStrings(Singleton):
    EMBED_WOWTOOLS_TITLE = "wow.tools builds page"
    EMBED_WOWTOOLS_URL = "https://wow.tools/builds/"

    EMBED_WAGOTOOLS_TITLE = "wago.tools"
    EMBED_WAGOTOOLS_URL = "https://wago.tools/builds"
    EMBED_WAGOTOOLS_DIFF_URL = "https://wago.tools/builds-diff?from={old}&to={new}"

    EMBED_DIABLO_TITLE = "Diablo 4"

    EMBED_GRYPHON_TITLE = "Warcraft Rumble"

    EMBED_BNET_TITLE = "Battle.net"

    EMBED_NAME = "Blizzard CDN Update"
    EMBED_NAME_WOW = "Warcraft CDN Update"
    EMBED_NAME_D4 = "Diablo 4 CDN Update"
    EMBED_NAME_GRYPHON = "Warcraft Rumble CDN Update"
    EMBED_NAME_BNET = "Battle.net CDN Update"

    EMBED_ICON_URL = (
        "https://bnetcmsus-a.akamaihd.net/cms/gallery/D2TTHKAPW9BH1534981363136.png"
    )
    EMBED_ICON_URL_WOW = "https://blz-contentstack-images.akamaized.net/v3/assets/blt72f16e066f85e164/bltc3d5627fa96394bf/world-of-warcraft.webp?width=96&format=webply&quality=95"
    EMBED_ICON_URL_D4 = "https://blz-contentstack-images.akamaized.net/v3/assets/blt72f16e066f85e164/blt15336eccf10cd269/diablo-IV.webp?width=96&format=webply&quality=95"
    EMBED_ICON_URL_GRYPHON = (
        "https://blznav.akamaized.net/img/games/logo-war-fb3f559702bed22f.png"
    )
    EMBED_ICON_URL_BNET = "https://blz-contentstack-images.akamaized.net/v3/assets/blt13393558c8f39060/blt99d316461099db22/644fe236d3c3ea26f40ed388/desktop-app.png"

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
        "gryphon": {
            "title": EMBED_GRYPHON_TITLE,
            "url": None,
            "name": EMBED_NAME_GRYPHON,
            "icon_url": EMBED_ICON_URL_GRYPHON,
        },
        "bnet": {
            "title": EMBED_BNET_TITLE,
            "url": None,
            "name": EMBED_NAME_BNET,
            "icon_url": EMBED_ICON_URL_BNET,
        },
    }


class WatcherConfig(Singleton):
    strings = WatcherStrings
    indices = Indices
    cache_defaults = CacheDefaults


## BLIZZARD API CONFIGURATION


class BlizzardAPIConfig(Singleton):
    assets = {
        "token_icon": "https://wow.zamimg.com/images/wow/icons/large/wow_token01.jpg"
    }


## LIVE CONFIG


class LiveConfig(Singleton):
    cfg_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "cache", "cfg.json"
    )

    def __init__(self):
        if not os.path.exists(self.cfg_path):
            with open(self.cfg_path, "w") as f:
                cfg = self.__get_default_cfg()
                json.dump(cfg, f, indent=4)

    def __get_default_cfg(self):
        cfg = {
            "products": {},
            "meta": {"fetch_interval": 5},
        }
        for branch in SUPPORTED_PRODUCTS:
            cfg["products"][branch.name] = {
                "public_name": branch.value,
                "test_branch": branch in TEST_BRANCHES,
            }
        return cfg

    def __open(self):
        with open(self.cfg_path, "r") as f:
            data = json.load(f)

        return data

    def get_cfg_value(self, category: str, key: str) -> Optional[str]:
        data = self.__open()

        if category in data.keys():
            section = data[category]
            if key in section.keys():
                return section[key]

        return

    def get_all_products(self):
        data = self.__open()
        return data["products"]

    def get_product_name(self, branch: str):
        data = self.__open()
        if branch in data["products"].keys():
            return data["products"][branch]["public_name"]

    def get_fetch_interval(self):
        data = self.__open()
        return data["meta"]["fetch_interval"]


## DEBUG CONFIGURATION


class DebugConfig(Singleton):
    debug_enabled = os.getenv("DEBUG", False)
    debug_guild_id = os.getenv("DEBUG_GUILD_ID")
    debug_channel_id = os.getenv("DEBUG_CHANNEL_ID")
    debug_channel_id_d4 = os.getenv("DEBUG_CHANNEL_ID_D4")
    debug_channel_id_gryphon = os.getenv("DEBUG_CHANNEL_ID_GRYPHON")
    debug_channel_id_bnet = os.getenv("DEBUG_CHANNEL_ID_BNET")

    debug_channel_id_by_game = {
        "wow": debug_channel_id,
        "d4": debug_channel_id_d4,
        "gryphon": debug_channel_id_gryphon,
        "bnet": debug_channel_id_bnet,
    }
