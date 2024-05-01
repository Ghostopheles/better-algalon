# Changelog v1.9 - Yttrium

## Added

- Algalon is now able to DM users when a build update appears. These DMs are purposefully slimmed down to allow them to actually be readable via mobile push notifications.
- Added a live config file that can be used to update certain configuration values without needing to rebuild and redeploy the bot. Namely, product names can now be updated live.

## Removed

- The `cdn` prefix on all of the slash commands has been deleted.

## Fixed

- Update checking is now significantly faster.
- Global config objects are now handled more efficiently.

# Changelog v1.8 - Niobium

## Added

 - `wowlivetest2`, `fenristest`, `gryphon`, `gryphonb`, `gryphondev` products can now be observed.

## Fixed

 - Various backend fixes and optimizations to improve uptime and performance.

# Changelog v1.7 - Beryllium

## Added

 - Algalon can now be added to any server by clicking the 'Add to Server' button on his profile on Discord! Use at your own risk. ;)
 - As such, I've added a new welcome message when Algalon first joins a server. This message will be sent to the system channel if possible, otherwise it'll fall back to the 'community updates' channel. Both of these channels are set by server admins in the server settings, and if neither are available he just remains silent.
 - Algalon will now publish messages to a channel in the Official™️ GhostBots Discord server, so if you don't want to add Algalon to your server, let me know and I'll invite to the GhostBots server where you can follow the announcement channel, and have all the messages propagated to your server! (you lose the ability to customize branches you wanna watch though)
 - Some minor debugging/administration commands.

## Fixed

 - Servers subscribed to Diablo 4 updates but that haven't set their Diablo 4 channel will now automatically have the Diablo 4 channel set to whatever their Warcraft channel is.
 - Minor optimizations in the guild configuration area.



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