import logging

from collections import defaultdict

from cogs import features as shared

logger = logging.getLogger("discord.features.panel")


class FeaturePanel:
    def __init__(self, bot, features: list | None):
        self.bot = bot
        self.flags = shared.FeatureFlagManager(bot)

        self.__enabled_features = features
        self.enabled = []

    def register_feature(self, feature: shared.Feature):
        logger.info(f"Registering feature {feature.id}...")
        self.enabled.append(feature)
        logger.info(
            f"Feature {feature.id} registered. Feature status: {feature.enabled} | {feature.status_text}"
        )

    def build_load_order(self) -> list[shared.Feature] | None:
        """Sort all enabled features into a load order to be loaded on start."""
        logger.info(f"Building feature load order...")

        if not self.__enabled_features:
            logger.debug("No features enabled.")
            return

        dependencies = []
        no_deps = []
        for feature in self.__enabled_features:
            if not feature.dependencies:
                no_deps.append(feature)
                continue

            dependencies.extend(feature.get_dependencies())

        if not dependencies:
            return self.__enabled_features

        # Initialize variables
        result = []
        visited = set()
        graph = defaultdict(list)

        # Build the graph
        for dependency in dependencies:
            dependent, dependency = dependency
            graph[dependent].append(dependency)

        # Recursive depth-first search
        def dfs(node):
            visited.add(node)
            for neighbor in graph[node]:
                if neighbor not in visited:
                    dfs(neighbor)
            result.append(node)  # type: ignore

        # Call depth-first search on all nodes
        for node in list(graph):
            if node not in visited:
                dfs(node)

        for feature in no_deps:
            if feature not in result:
                result.append(feature)
        logger.debug(f"Load order sorted. Result: {result}")
        return result

    def __load_cog(self, cog: shared.Feature) -> tuple[bool, str]:
        logger.info(f"Loading {cog.name} cog...")
        if not cog.feature_type == shared.FeatureType.COG:
            logger.error(f"{cog.name} is not a cog. Loading failed.")
            return False, "Non-cog in load_cog"

        try:
            path = f"cogs.{cog.sub_id + '.' + cog.id if cog.sub_id else cog.id}"
            self.bot.load_extension(path)
        except Exception as exc:
            logger.error(f"Error loading cog {cog.name}.")
            logger.error(exc)
            return False, "Loading failed"

        logger.info(f"{cog.name} cog loaded!")
        return True, "Healthy"

    def __load_standalone(self, feature: shared.Feature) -> tuple[bool, str]:
        # I'll do something here eventually, but right now there aren't any standalone modules
        return True, "Healthy"

    def init_features(self):
        if self.__enabled_features:
            logger.info("Initializing features...")
            load_order = self.build_load_order()
            feature_type = shared.FeatureType

            for feature in load_order:  # type: ignore
                logger.info(
                    f"Initializing {feature.name} feature...",
                )

                self.flags.add_group(feature.id)
                self.flags.add_flags_from_dict(feature.id, feature.flags)

                if feature.feature_type == feature_type.COG:
                    success, status_text = self.__load_cog(feature)
                elif feature.feature_type == feature_type.STANDALONE:
                    success, status_text = self.__load_standalone(feature)
                else:
                    success, status_text = False, "Unrecognized feature type"

                feature.enabled, feature.status_text = success, status_text

                if success:
                    self.register_feature(feature)
                else:
                    logger.error(f"Error initializing {feature.name} feature.")
                    self.flags.remove_group(feature.id)
        else:
            return False
