import logging

from enum import Enum
from dataclasses import dataclass, field


logger = logging.getLogger("discord.features.feature")


class FeatureType(Enum):
    """Various types of features that can be toggled."""

    COG = 1
    STANDALONE = 2


@dataclass
class Feature:
    id: str  # Internal name, used for loading cogs n' stuff
    name: str  # Readable name
    toggle_at_runtime: bool  # Whether the feature can be toggled while the bot is running
    feature_type: FeatureType  # The type of feature
    sub_id: str = ""  # Sub ID, used for loading cogs n' stuff
    flags: dict = field(default_factory=dict)
    dependencies: list = field(default_factory=list)  # List of dependencies, if any
    enabled: bool = False  # Feature enable state
    status_text: str = ""

    def __iter__(self):
        yield self.id
        yield self.name
        yield self.toggle_at_runtime
        yield self.feature_type

    def __hash__(self):
        return hash(tuple(self))

    def __eq__(self, other):
        return isinstance(other, type(self)) and tuple(self) == tuple(other)

    def __lt__(self, other):
        if not self.dependencies:
            return True
        else:
            return other in self.dependencies

    def __repr__(self):
        return f"<Feature {self.id}>"

    def __can_be_disabled(self):
        if not self.dependencies and self.toggle_at_runtime:
            return True

    def get_dependencies(self) -> list:
        logger.info("Getting feature dependencies...")
        all_deps = []
        for dep in self.dependencies:
            all_deps.append((self, dep))

        return all_deps
