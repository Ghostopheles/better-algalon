import logging

from collections import defaultdict

from cogs import features as shared

logger = logging.getLogger("discord.features.panel")


class FeaturePanel:
    def __init__(self, bot, features: list | None):
        self.bot = bot
        self.flags = shared.FeatureFlags()

        self.__enabled_features = features

    def build_load_order(self) -> list[shared.Feature] | None:
        """Sort all enabled features into a load order to be loaded on start."""
        logger.info(f"Building feature load order...")

        if not self.__enabled_features:
            return

        dependencies = []
        for feature in self.__enabled_features:
            if not feature.dependencies:
                continue

            dependencies.extend(feature.get_dependencies())

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
            result.append(node)

        # Call depth-first search on all nodes
        for node in list(graph):
            if node not in visited:
                dfs(node)

        # Reverse the result to get the correct order
        return result

    def __load_cog(self, cog: shared.Feature) -> tuple[bool, str]:
        logger.info(f"Loading {cog.name} cog...")
        if not cog.feature_type == shared.FeatureType.COG:
            logger.error(f"{cog.name} is not a cog. Loading failed.")
            return False, "Non-cog in load_cog"

        try:
            self.bot.load_extension(f"cogs.{cog.id}")
        except Exception as exc:
            logger.error(f"Error loading cog {cog.name}.")
            logger.error(exc)
            return False, "Loading failed"

        logger.info(f"{cog.name} cog loaded!")
        return True, "Healthy"

    def __load_standalone(self) -> tuple[bool, str]:
        # I'll do something here eventually, but right now there aren't any standalone modules
        return False, ""

    def init_flags(self):
        pass

    def init_features(self):
        if self.__enabled_features:
            logger.info("Initializing features...")
            load_order = self.build_load_order()
            feature_type = shared.FeatureType

            for feature in load_order:  # type: ignore
                logger.info(
                    f"Initializing {feature.name} feature...",
                )
                if feature.feature_type == feature_type.COG:
                    success, status_text = self.__load_cog(feature)
                elif feature.feature_type == feature_type.STANDALONE:
                    success, status_text = self.__load_standalone()
                else:
                    success, status_text = False, "Unrecognized feature type"

                feature.status, feature.status_text = success, status_text
                # self.flags.add_flag(feature.name, feature.status)
        else:
            return False
