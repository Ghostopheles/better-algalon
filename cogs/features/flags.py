import logging

from dataclasses import dataclass

logger = logging.getLogger("discord.features.flags")


@dataclass
class FeatureFlag:
    name: str
    value: bool


@dataclass
class FeatureFlagGroup:
    name: str


class FeatureFlagManager:
    def __init__(self):
        self.wax = "HI!"

    def add_group(self, name: str):
        getter = lambda self: self

        setattr(self, name, property())

    def remove_group(self):
        pass

    def add_flag(self, owner: str, name: str, value: bool) -> bool:
        logger.info(f"Adding new feature flag {owner}:{name}...")

        if flag_group := getattr(self, owner):
            pass

        if not getattr(self, name):
            setattr(self, name, value)
            # self.flags.append(name)
            return True
        else:
            logger.error(
                f"Feature flag already exists or attribute already assigned. Exiting..."
            )
            return False

    def set_flag(self, name: str, value: bool) -> bool:
        logger.info(f"Setting feature flag ({name}) to {value}...")
        if not getattr(self, name):
            logger.error(f"Feature flag does not exist.")
            return False

        return getattr(self, name)

    def get_all_flags(self) -> list[str]:
        pass


if __name__ == "__main__":
    f = FeatureFlagManager()
