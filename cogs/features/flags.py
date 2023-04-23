import logging

from dataclasses import dataclass

logger = logging.getLogger("discord.features.flags")


@dataclass
class FeatureFlag:
    name: str
    value: bool

    def __bool__(self):
        return self.value


@dataclass
class FeatureFlagGroup:
    name: str
    all_flags = []

    def add_flag(self, flag: FeatureFlag):
        logger.debug(f"Adding flag ({flag}) to group ({self.name})...")
        if not hasattr(self, flag.name):
            setattr(self, flag.name, flag)
            self.all_flags.append(flag.name)
        else:
            logger.error(f"Flag ({flag.name}) already exists in group ({self.name})!")

    def remove_flag(self, name: str):
        logger.debug(f"Removing flag ({name}) from group ({self.name})...")
        if hasattr(self, name):
            self.all_flags.remove(name)
            delattr(self, name)
        else:
            logger.error(f"Flag ({name}) does not exist in group ({self.name})!")

    def set_flag_by_name(self, name: str, value: bool):
        logger.debug(f"Setting flag ({name}) in group {self.name} to {value}...")
        if hasattr(self, name):
            flag = getattr(self, name)
            flag.value = value
        else:
            logger.error(f"Flag ({name}) does not exist in group ({self.name})!")

    def get_flag_by_name(self, name: str) -> FeatureFlag | None:
        logger.debug(f"Getting flag ({name}) from group ({self.name})...")
        if hasattr(self, name):
            return getattr(self, name)
        else:
            logger.error(f"Flag ({name}) does not exist in group ({self.name})!")

    def get_all_flags(self):
        all_flags = []
        for k, v in self.__dict__.items():
            if isinstance(v, FeatureFlag):
                all_flags.append(v)

        return all_flags


class FeatureFlagManager:
    def __init__(self, bot=None):
        self.__bot = bot
        self.__global_string = "globals"
        self.globals = None

        self.add_group(self.__global_string)

    def add_group(self, name: str):
        logger.debug(f"Adding flag group with name {name}...")
        if not hasattr(self, name):
            newGroup = FeatureFlagGroup(name)
            setattr(self, name, newGroup)

    def remove_group(self, name: str):
        logger.debug(f"Removing flag group with name {name}...")
        if hasattr(self, name):
            delattr(self, name)

    def add_flags_from_dict(self, flag_group_name: str, flags: dict):
        logger.info(f"Adding flags from dict to group {flag_group_name}...")

        if not hasattr(self, flag_group_name):
            logger.error(f"Flag group does not exist! Adding a new one...")
            self.add_group(flag_group_name)

        for flag_name, flag_value in flags.items():
            if not isinstance(flag_value, bool):
                logger.error(f"Flag value {flag_value} is not a boolean!")
                continue
            self.add_flag_to_group(flag_group_name, flag_name, flag_value)

    def add_flag_to_group(
        self, flag_group_name: str, flag_name: str, flag_value: bool
    ) -> bool:
        logger.info(f"Adding new feature flag {flag_group_name}:{flag_name}...")

        flag = FeatureFlag(flag_name, flag_value)

        if flag_group := getattr(self, flag_group_name):
            flag_group.add_flag(flag)
            return True
        else:
            logger.error(
                f"Flag group does not exist and flag is not global. Flag not added."
            )
            return False

    def remove_flag_from_group(self, flag_group_name: str, flag_name: str) -> bool:
        logger.info(f"Removing feature flag {flag_group_name}:{flag_name}...")

        if flag_group := getattr(self, flag_group_name):
            flag_group.remove_flag(flag_name)
            return True
        else:
            logger.error(f"Flag group does not exist. Flag not removed.")
            return False

    def set_flag_in_group(
        self, flag_group_name: str, flag_name: str, flag_value: bool
    ) -> bool:
        logger.info(
            f"Setting feature flag for {flag_group_name}:{flag_name} to {flag_value}..."
        )

        if flag_group := getattr(self, flag_group_name):
            flag_group.set_flag_by_name(flag_name, flag_value)
            return True
        else:
            logger.error(f"Flag group does not exist. Flag not set.")
            return False

    def get_flag_from_group(self, flag_group_name: str, flag_name: str):
        logger.info(f"Getting feature flag for {flag_group_name}:{flag_name}...")

        if flag_group := getattr(self, flag_group_name):
            return flag_group.get_flag_by_name(flag_name)
        else:
            logger.error(f"Flag group does not exist. Flag not found.")
            return None

    def add_global_flag(self, name: str, value: bool):
        logger.debug(f"Adding global flag ({name}) with value {value}...")
        if not hasattr(self.globals, name):
            setattr(self.globals, name, FeatureFlag(name, value))
            return True
        else:
            logger.error(f"Global flag ({name}) already exists!")
            return False

    def remove_global_flag(self, name: str):
        logger.debug(f"Removing global flag ({name})...")
        if hasattr(self.globals, name):
            delattr(self.globals, name)
            return True
        else:
            logger.error(f"Global flag ({name}) does not exist!")
            return False

    def set_global_flag(self, name: str, value: bool):
        logger.debug(f"Setting global flag ({name}) to {value}...")
        if hasattr(self.globals, name):
            flag = getattr(self.globals, name)
            flag.value = value
            return True
        else:
            logger.error(f"Global flag ({name}) does not exist!")
            return False

    def get_global_flag(self, name: str) -> FeatureFlag | None:
        logger.debug(f"Getting global flag ({name})...")
        if hasattr(self.globals, name):
            return getattr(self.globals, name)
        else:
            logger.error(f"Global flag ({name}) does not exist!")
            return None

    def get_all_flags(self):
        for group_name, group in self.__dict__.items():
            if group_name.startswith("__"):
                continue
            logger.debug(
                f"Group: {group.name or group}\nFlags: {group.get_all_flags()}"
            )
            flags[group_name] = group.get_all_flags()
        return flags


if __name__ == "__main__":
    flag_manager = FeatureFlagManager()
    flag_manager.add_group("test_group")
    flags = {
        "test_flag": True,
        "test_flag_2": False,
        "test_flag_3": True,
    }
    flag_manager.add_flags_from_dict("test_group", flags)
