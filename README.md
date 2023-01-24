# better-algalon
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0) ![LastUpdate](https://img.shields.io/github/last-commit/Ghostamoose/better-algalon?style=flat-square) [![Docker](https://github.com/Ghostamoose/better-algalon/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/Ghostamoose/better-algalon/actions/workflows/docker-publish.yml)

v1.5

A bot that watches Blizzard's Warcraft CDN and automatically posts new build updates to a specified Discord channel.

Inspired by, and vaguely based on the original [Algalon bot by Ellypse](https://github.com/Ellypse/Algalon).

## commands

Algalon provides a number of commands with questionable value.

\*admin privileges required.

### cdn watching

`/cdncurrentdata`: Returns a paginator (lil flipbook) containing the current CDN data Algalon has.

`/cdnlastupdate`: Returns a timestamp displaying when Algalon last checked for CDN updates.

#### watchlist

`/cdnaddtowatchlist`*: Adds a specific branch to your guild's watchlist.

`/cdnremovefromwatchlist`*: Removes a specific branch to your guild's watchlist.

`/cdnwatchlist`: Returns your guild's current watchlist.

`/cdnedit`*: Returns a graphical editor for your guild's watchlist. (prone to breaking)

#### customization

`/cdnsetchannel`*: Sets the channel in which it's invoked as the notification channel for your guild.

`/cdngetchannel`: Returns the current notification channel for your guild.

### blizzard api

`/cdntokenprice`: Returns the current WoW token price in the "us" region.

