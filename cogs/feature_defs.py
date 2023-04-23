"""A place to define all features that will be enabled on bot startup."""

import logging

from cogs import features as shared

logger = logging.getLogger("discord.features")

titan = shared.Feature(
    id="titan",
    sub_id="admin",
    name="Titan",
    toggle_at_runtime=False,
    feature_type=shared.FeatureType.COG,
    flags={},
)

api_twitter = shared.Feature(
    id="twitter",
    sub_id="api",
    name="Twitter API",
    toggle_at_runtime=True,
    feature_type=shared.FeatureType.STANDALONE,
    flags={
        "doTweets": False,
    },
)

watcher = shared.Feature(
    id="watcher",
    name="CDN Watcher",
    toggle_at_runtime=True,
    feature_type=shared.FeatureType.COG,
    flags={
        "doCDNCheck": False,
        "paginatorEnabled": True,
        "watchlistEditingEnabled": True,
        "channelEditingEnabled": True,
        "regionEditingEnabled": True,
        "localeEditingEnabled": True,
    },
    dependencies=[api_twitter],
)

api_blizzard = shared.Feature(
    id="blizzard",
    sub_id="api",
    name="Blizzard API",
    toggle_at_runtime=True,
    feature_type=shared.FeatureType.COG,
    flags={
        "allowTokenPriceCheck": False,
    },
)

ALL_FEATURES = [titan, watcher, api_blizzard, api_twitter]
