import enum


class LocalesMeta(enum.EnumMeta):
    def __contains__(cls, item):
        return isinstance(item, cls) or item in [
            v.value for v in cls.__members__.values()  # type: ignore
        ]


class Locales(enum.Enum, metaclass=LocalesMeta):
    en_US = "en_US"
    en_GB = "en_GB"

    es_MX = "es_MX"
    es_ES = "es_ES"

    pt_BR = "pt_BR"
    pt_PT = "pt_PT"

    fr_FR = "fr_FR"
    ru_RU = "ru_RU"
    de_DE = "de_DE"
    it_IT = "it_IT"

    ko_KR = "ko_KR"

    zh_TW = "zh_TW"
    zh_CN = "zh_CN"
