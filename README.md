# better-algalon
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0) ![LastUpdate](https://img.shields.io/github/last-commit/Ghostamoose/better-algalon?style=flat-square) [![Docker](https://github.com/Ghostamoose/better-algalon/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/Ghostamoose/better-algalon/actions/workflows/docker-publish.yml)

v1.5 - Onyx

A bot that watches Blizzard's CDN and automatically posts new build updates to a specified Discord channel.

Inspired by, and vaguely based on the original [Algalon bot by Ellypse](https://github.com/Ellypse/Algalon).

Includes a frankenstein Twitter integration to post updates to Twitter alongside Discord. This will be replaced in the future with Algalon 3.0. This bot can be found on Twitter as [@algalon_ghost](https://twitter.kivatech.io).

## supported branches (what it watches)
| Branch Name | Readable Name |
| ----------- | ----------- |
| wow | Retail |
| wowt | Retail PTR |
| wow_beta | Beta |
| wow_classic | WotLK Classic |
| wow_classic_ptr | WotLK Classic PTR|
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


## commands

Algalon provides a number of commands with questionable value.

\*admin privileges required.

### cdn watching

`/cdncurrentdata`: Returns a paginator (lil flipbook) containing the current CDN data Algalon has.

`/cdnlastupdate`: Returns a timestamp displaying when Algalon last checked for CDN updates.

#### watchlist controls

`/cdnaddtowatchlist`*: Adds a specific branch to your guild's watchlist.

`/cdnremovefromwatchlist`*: Removes a specific branch to your guild's watchlist.

`/cdnwatchlist`: Returns your guild's current watchlist.

#### notifcation channel controls

`/cdnsetchannel`*: Sets the channel in which it's invoked as the notification channel for your guild.

`/cdngetchannel`: Returns the current notification channel for your guild.

### blizzard API

`/cdntokenprice`: Returns the current WoW token price in the "us" region.

