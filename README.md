# better-algalon
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0) ![LastUpdate](https://img.shields.io/github/last-commit/Ghostamoose/better-algalon?style=flat-square) [![Docker](https://github.com/Ghostamoose/better-algalon/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/Ghostamoose/better-algalon/actions/workflows/docker-publish.yml)

v1.6 - Diamond

A bot that watches Blizzard's CDN and automatically posts new build updates to specified Discord channels.

Inspired by, and vaguely based on the original [Algalon bot by Ellypse](https://github.com/Ellypse/Algalon).

Includes a Twitter integration to post updates to Twitter alongside Discord. This will be replaced in the future with Algalon 3.0 (lol). This bot can be found on Twitter as [@algalon_ghost](https://twitter.kivatech.io).

Check out the [[CHANGELOG]] to view the most recent changes.

## Observable Branches
A lock indicates that the given branch is encrypted and not accessible to the public.
### Warcraft
| Branch Name | Readable Name |
| ----------- | ----------- |
| wow | Retail |
| wowt | Retail PTR |
| wowxptr | Retail PTR 2 |
| wow_beta | Beta |
| wow_classic | WotLK Classic |
| wow_classic_ptr | WotLK Classic PTR |
| wow_classic_beta | Classic Beta |
| wow_classic_era | Classic Era |
| wow_classic_era_beta | Classic Era Beta |
| wow_classic_era_ptr | Classic Era PTR |
| wowz | Submission |
| wowlivetest | Live Test|
| wowdev :lock: | Internal |
| wowdev2 :lock: | Internal 2 |
| wowdev3 :lock: | Internal 3 |
| wowv :lock: | Vendor |
| wowv2 :lock: | Vendor 2 |
| wowv3 :lock: | Vendor 3 |
| wowv4 :lock: | Vendor 4 |
| wowe1 | Event |
| wowe2 | Event 2 |
| wowe3 | Event 3 |
| wowdemo :lock: | Demo |

### Diablo IV
| Branch Name | Readable Name |
| ----------- | ----------- |
| fenris | Diablo IV |
| fenrisb | Diablo IV Beta |
| fenrisdev :lock: | Diablo IV Internal |
| fenrisdev2 :lock: | Diablo IV Internal 2 |
| fenrise :lock: | Diablo IV Event |
| fenrisvendor1 :lock: | Diablo IV Vendor |
| fenrisvendor2 :lock: | Diablo IV Vendor 2 |
| fenrisvendor3 :lock: | Diablo IV Vendor 3 |

## Commands

Algalon provides a number of commands to control your guild's (server) watchlist.

\*admin privileges required.

### CDN Watching

`/cdndata`: Returns a paginator containing the currently cached CDN data.

`/cdnlastupdate`: Returns a timestamp displaying when Algalon last checked for CDN updates.

#### Watchlist Controls

`/cdnaddtowatchlist`*: Adds a specific branch to your guild's watchlist. Specify multiple branches at once by separating them with a comma.

`/cdnremovefromwatchlist`*: Removes a specific branch to your guild's watchlist.

`/cdnwatchlist`: Returns your guild's current watchlist.

#### Notification Channel Controls

`/cdnsetchannel`*: Sets the channel in which it's invoked as the notification channel for your guild. Optionally, specify a game to set the notification channel for that game. Defaults to Warcraft.

`/cdngetchannel`: Returns the current notification channel for your guild. Optionally, specify a game to get the notification channel for that game. Defaults to Warcraft.

