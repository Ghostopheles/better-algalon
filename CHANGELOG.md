# Changelog v1.6 - Diamond

## Added

 - `/cdnbranches` allows you to view a list of all branches that Algalon can watch for your server.
 - Support for Diablo IV returns.
 - You can now split up notifications for Diablo IV and Warcraft into seperate channels if you so desire.

## Changed

 - Update embeds are now a little prettier.
 - Most commands have been restricted to only being available in servers only and are now unable to be called from DMs.
 - The paginator command has been changed to `/cdndata`.
    - The paginator returned by the above command is no longer missing a newline on the second-to-last line.
 - `/cdnsetchannel` now allows you to specify a game when setting your notification channel. Defaults to Warcraft.
    - Existing servers will have their Diablo IV notification channel automatically set to the channel that is currently selected for notifications.
    - `/cdngetchannel` has also been updated to reflect this change.
 - `/cdnaddtowatchlist` now supports comma-delimited lists of branches to add to the watchlist.
 - A few slash commands now have proper docstrings.
 - The `/cdnaddtowatchlist` and `/cdnremovefromwatchlist` commands now have a clickable command button to view all valid branches.

## Removed

 - The commented out code for the watchlist editor UI has been removed  (rip). This will return in the future when I have the time (and patience) to work on it.
 - The commands for locale and region configuration have been removed. They didn't actually do anything in the first place and it's safer to remove them for now until I can get them working correctly.
 - The Blizzard API integration (`/cdntokenprice`) has been disabled. This wasn't really useful and doesn't fit with the rest of the bot's functionality, so it's getting yeeted.