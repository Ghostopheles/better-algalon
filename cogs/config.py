import os
import json

from discord import Color
from dataclasses import dataclass
from typing import Optional, Any
from enum import StrEnum
from .locale import Locales

## GLOBAL CONFIGURATION

FETCH_INTERVAL = 1


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

    @classmethod
    def has_key(cls, value):
        return value in cls._value2member_map_.keys()

    @classmethod
    def get_game(cls, value):
        if cls.has_key(value):
            return cls._value2member_map_[value]


class SUPPORTED_PRODUCTS(StrEnum):
    """Supported Branches"""

    # if a product branch name (the key) does not include "wow", it will not be tweeted
    # WoW products
    wow = "Retail"
    wowt = "Retail PTR"
    wow_beta = "Beta"
    wowxptr = "Retail PTR 2"
    wow_classic = "Cata Classic"
    wow_classic_beta = "Classic Beta"
    wow_classic_ptr = "Cata Classic PTR"
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

INTERNAL_BRANCHES = (
    SUPPORTED_PRODUCTS.wowlivetest2,
    SUPPORTED_PRODUCTS.wowdev,
    SUPPORTED_PRODUCTS.wowdev2,
    SUPPORTED_PRODUCTS.wowdev3,
    SUPPORTED_PRODUCTS.wowv,
    SUPPORTED_PRODUCTS.wowv2,
    SUPPORTED_PRODUCTS.wowv3,
    SUPPORTED_PRODUCTS.wowv4,
    SUPPORTED_PRODUCTS.fenrise,
    SUPPORTED_PRODUCTS.fenrisvendor1,
    SUPPORTED_PRODUCTS.fenrisvendor2,
    SUPPORTED_PRODUCTS.fenrisvendor3,
    SUPPORTED_PRODUCTS.fenrisdev,
    SUPPORTED_PRODUCTS.fenrisdev2,
    SUPPORTED_PRODUCTS.gryphondev,
)

WOW_BRANCHES = [
    SUPPORTED_PRODUCTS.wow,
    SUPPORTED_PRODUCTS.wowt,
    SUPPORTED_PRODUCTS.wow_beta,
    SUPPORTED_PRODUCTS.wowxptr,
    SUPPORTED_PRODUCTS.wow_classic,
    SUPPORTED_PRODUCTS.wow_classic_beta,
    SUPPORTED_PRODUCTS.wow_classic_ptr,
    SUPPORTED_PRODUCTS.wow_classic_era,
    SUPPORTED_PRODUCTS.wow_classic_era_beta,
    SUPPORTED_PRODUCTS.wow_classic_era_ptr,
    SUPPORTED_PRODUCTS.wowz,
    SUPPORTED_PRODUCTS.wowlivetest,
    SUPPORTED_PRODUCTS.wowlivetest2,
    SUPPORTED_PRODUCTS.wowdev,
    SUPPORTED_PRODUCTS.wowdev2,
    SUPPORTED_PRODUCTS.wowdev3,
    SUPPORTED_PRODUCTS.wowv,
    SUPPORTED_PRODUCTS.wowv2,
    SUPPORTED_PRODUCTS.wowv3,
    SUPPORTED_PRODUCTS.wowv4,
    SUPPORTED_PRODUCTS.wowe1,
    SUPPORTED_PRODUCTS.wowe2,
    SUPPORTED_PRODUCTS.wowe3,
    SUPPORTED_PRODUCTS.wowdemo,
]

DIABLO_BRANCHES = [
    SUPPORTED_PRODUCTS.fenris,
    SUPPORTED_PRODUCTS.fenrisb,
    SUPPORTED_PRODUCTS.fenristest,
    SUPPORTED_PRODUCTS.fenrisdev,
    SUPPORTED_PRODUCTS.fenrisdev2,
    SUPPORTED_PRODUCTS.fenrise,
    SUPPORTED_PRODUCTS.fenrisvendor1,
    SUPPORTED_PRODUCTS.fenrisvendor2,
    SUPPORTED_PRODUCTS.fenrisvendor3,
]

RUMBLE_BRANCHES = [
    SUPPORTED_PRODUCTS.gryphon,
    SUPPORTED_PRODUCTS.gryphonb,
    SUPPORTED_PRODUCTS.gryphondev,
]

BNET_BRANCHES = [SUPPORTED_PRODUCTS.catalogs]


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
    BUILD = "no-data"
    BUILDTEXT = "no-data"


@dataclass
class Setting:
    name: str
    default: str


class Settings(Singleton):
    __defaults = CacheDefaults()

    CHANNEL = Setting("channel", __defaults.CHANNEL)
    D4_CHANNEL = Setting("d4_channel", __defaults.CHANNEL)
    GRYPHON_CHANNEL = Setting("gryphon_channel", __defaults.CHANNEL)
    BNET_CHANNEL = Setting("bnet_channel", __defaults.CHANNEL)
    WATCHLIST = Setting("watchlist", __defaults.WATCHLIST)
    REGION = Setting("region", __defaults.REGION_NAME)
    LOCALE = Setting("locale", __defaults.LOCALE_NAME)

    KEYS = [
        CHANNEL.name,
        D4_CHANNEL.name,
        GRYPHON_CHANNEL.name,
        BNET_CHANNEL.name,
        WATCHLIST.name,
        REGION.name,
        LOCALE.name,
    ]


class UserSettings(Singleton):
    WATCHLIST = Setting("watchlist", [])


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

    SETTING_BY_GAME = {
        SUPPORTED_GAMES.Warcraft: settings.CHANNEL,
        SUPPORTED_GAMES.Diablo4: settings.D4_CHANNEL,
        SUPPORTED_GAMES.Gryphon: settings.GRYPHON_CHANNEL,
        SUPPORTED_GAMES.BattleNet: settings.BNET_CHANNEL,
    }

    def get_setting_for_game(self, game: SUPPORTED_GAMES):
        return self.SETTING_BY_GAME[game]

    @staticmethod
    def is_valid_branch(branch) -> bool:
        return SUPPORTED_PRODUCTS.has_key(branch)


## COMMON CONFIGURATION


class CommonStrings(Singleton):
    EMBED_FOOTER = "Data provided by Algalon {version}"
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

    EMBED_GAME_CONFIG = {
        "wow": {
            "title": EMBED_WAGOTOOLS_TITLE,
            "url": EMBED_WAGOTOOLS_URL,
            "name": EMBED_NAME_WOW,
            "icon_url": EMBED_ICON_URL_WOW,
            "color": Color.dark_blue(),
        },
        "d4": {
            "title": EMBED_DIABLO_TITLE,
            "url": None,
            "name": EMBED_NAME_D4,
            "icon_url": EMBED_ICON_URL_D4,
            "color": Color.dark_red(),
        },
        "gryphon": {
            "title": EMBED_GRYPHON_TITLE,
            "url": None,
            "name": EMBED_NAME_GRYPHON,
            "icon_url": EMBED_ICON_URL_GRYPHON,
            "color": Color.dark_gold(),
        },
        "bnet": {
            "title": EMBED_BNET_TITLE,
            "url": None,
            "name": EMBED_NAME_BNET,
            "icon_url": EMBED_ICON_URL_BNET,
            "color": Color.dark_blue(),
        },
    }


class WatcherConfig(Singleton):
    strings = WatcherStrings
    indices = Indices
    cache_defaults = CacheDefaults

    @staticmethod
    def get_game_from_branch(branch: str) -> SUPPORTED_GAMES:
        product = SUPPORTED_PRODUCTS[branch]
        if product in WOW_BRANCHES:
            return SUPPORTED_GAMES.Warcraft
        elif product in DIABLO_BRANCHES:
            return SUPPORTED_GAMES.Diablo4
        elif product in RUMBLE_BRANCHES:
            return SUPPORTED_GAMES.Gryphon
        elif product in BNET_BRANCHES:
            return SUPPORTED_GAMES.BattleNet


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

    @staticmethod
    def __get_default_cfg():
        cfg = {
            "products": {},
            "meta": {"fetch_interval": FETCH_INTERVAL},
            "discord": {
                "owner_id": 130987844125720576,  # hey look it's me!
            },
            "debug": {
                "debug_mode": True,  # defaults to True because y'know, the file doesn't exist, probably first run or something
            },
            "features": {"monitoring_enabled": False},
        }
        for branch in SUPPORTED_PRODUCTS:
            cfg["products"][branch.name] = {
                "public_name": branch.value,
                "test_branch": branch in TEST_BRANCHES,
                "encrypted": False,
            }
        return cfg

    @staticmethod
    def __open():
        with open(LiveConfig.cfg_path, "r") as f:
            data = json.load(f)

        return data

    @staticmethod
    def get_cfg_value(
        category: str, key: str, default: Optional[Any] = None
    ) -> Optional[str]:
        data = LiveConfig.__open()

        if category in data:
            section = data[category]
            if key in section:
                return section[key]

        return default

    @staticmethod
    def get_all_products():
        data = LiveConfig.__open()
        return data["products"]

    @staticmethod
    def get_product_name(branch: str):
        data = LiveConfig.__open()
        if branch in data["products"].keys():
            return data["products"][branch]["public_name"]

    @staticmethod
    def get_product_encryption_state(branch: str):
        data = LiveConfig.__open()
        if branch in data["products"].keys():
            return data["products"][branch]["encrypted"]

    @staticmethod
    def get_debug_value(key: str, default: Optional[Any] = None) -> Optional[str]:
        data = LiveConfig.__open()
        dbg_data = data["debug"]
        if key in dbg_data:
            return dbg_data[key]

        return default


## DEBUG CONFIGURATION


class DebugConfig:
    debug_enabled = LiveConfig.get_debug_value("debug_mode", True)
    debug_guild_id = LiveConfig.get_debug_value("debug_guild")
    debug_channel_id = LiveConfig.get_debug_value("debug_channel")
    debug_channel_id_d4 = LiveConfig.get_debug_value("debug_channel_d4")
    debug_channel_id_gryphon = LiveConfig.get_debug_value("debug_channel_gryphon")
    debug_channel_id_bnet = LiveConfig.get_debug_value("debug_channel_bnet")

    debug_channel_id_by_game = {
        "wow": debug_channel_id,
        "d4": debug_channel_id_d4,
        "gryphon": debug_channel_id_gryphon,
        "bnet": debug_channel_id_bnet,
    }
