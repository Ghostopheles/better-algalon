import logging

# logger = logging.getLogger("discord.features")

watcher = Feature(
    id="watcher",
    name="CDN Watcher",
    toggle_at_runtime=True,
    feature_type=FeatureType.COG,
)

api_blizzard = Feature(
    id="api.blizzard",
    name="Blizzard API",
    toggle_at_runtime=True,
    feature_type=FeatureType.COG,
)
