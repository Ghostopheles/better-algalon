import os

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
    BUILDTEXT = "untracked"


class Settings:
    __defaults = CacheDefaults()

    CHANNEL = {"name": "channel", "default": __defaults.CHANNEL}
    WATCHLIST = {"name": "watchlist", "default": __defaults.WATCHLIST}
    REGION = {"name": "region", "default": __defaults.REGION_NAME}
    LOCALE = {"name": "locale", "default": __defaults.LOCALE_NAME}

    KEYS = ["channel", "watchlist", "region", "locale"]


class ErrorStrings:
    REGION_SAME_AS_CURRENT = "New region is the same as the current region."
    REGION_NOT_SUPPORTED = "Region not supported."

    LOCALE_SAME_AS_CURRENT = "New locale is the same as the current locale."
    LOCALE_NOT_SUPPORTED = "Locale not supported by your region."

    BRANCH_NOT_VALID = "Branch is not a valid product."
    BRANCH_ALREADY_IN_WATCHLIST = "Branch is already on your watchlist."

    ARG_BRANCH_NOT_ON_WATCHLIST = "Argument 'branch' is not on the watchlist."


class CommonURL:
    HTTPS = "http://"
    CDN_URL = ".patch.battle.net:1119/"  # does not include region


class CacheConfig:
    CDN_URL = "http://us.patch.battle.net:1119/"
    PRODUCTS = {
        "wow": "Retail",
        "wowt": "Retail PTR",
        "wow_beta": "Beta",
        "wow_classic": "WotLK Classic",
        "wow_classic_ptr": "WotLK Classic PTR",
        "wow_classic_beta": "Classic Beta",
        "wow_classic_era": "Classic Era",
        "wow_classic_era_ptr": "Classic Era PTR",
        "wowz": "Submission",
        "wowlivetest": "Live Test",
        "wowdev": "Internal",
        "fenrisdev": "Diablo IV Internal",
        "fenris": "Diablo IV Retail",
        "fenrisb": "Diablo IV Beta",
    }
    AREAS_TO_CHECK_FOR_UPDATES = ["build", "build_text"]
    CACHE_FOLDER_NAME = "cache"
    CACHE_FILE_NAME = "cdn.json"

    GUILD_CFG_FILE_NAME = "guild_cfg.json"

    SUPPORTED_REGIONS = SUPPORTED_REGIONS
    SUPPORTED_REGIONS_STRING = SUPPORTED_REGIONS_STRINGS

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


## COMMON CONFIGURATION


class CommonStrings:
    EMBED_FOOTER = f"Data provided by Algalon {os.getenv('ENVIRONMENT', 'Redstone')}."
    VALID_REGIONS = SUPPORTED_REGIONS_STRINGS

    SPEECH = "$$dalaran.speech$$"


## WATCHER CONFIGURATION


class WatcherStrings:
    EMBED_WOWTOOLS_TITLE = "wow.tools builds page"
    EMBED_WOWTOOLS_URL = "https://wow.tools/builds/"

    EMBED_WAGOTOOLS_TITLE = "wago.tools"
    EMBED_WAGOTOOLS_URL = "https://wago.tools/"

    EMBED_NAME = "Blizzard CDN Update"
    EMBED_ICON_URL = (
        "https://bnetcmsus-a.akamaihd.net/cms/gallery/D2TTHKAPW9BH1534981363136.png"
    )

    EMBED_UPDATE_TITLE = "Build Updates"


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


## OPENAI CONFIGURATION


class OpenAIStrings:
    TOKEN_COUNT_FAILED = "Token count failed. Please try again or let Ghost know."
    TOKEN_COUNT_MAX_REACHED = (
        "Prompt exceeds maximum token count. Please shorten your prompt and try again."
    )


class OpenAIConfig:
    strings = OpenAIStrings()

    chat_model = "gpt-3.5-turbo"
    max_tokens = 4096
    max_tokens_per_month = 20000000

    default_encoding = "cl100k_base"

    conversations_enabled = False

    default_messages = []
