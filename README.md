# better-algalon
![GitHub License](https://img.shields.io/github/license/ghostopheles/better-algalon?style=for-the-badge) ![GitHub commit activity](https://img.shields.io/github/commit-activity/m/ghostopheles/better-algalon?style=for-the-badge) ![GitHub last commit](https://img.shields.io/github/last-commit/ghostopheles/better-algalon?display_timestamp=author&style=for-the-badge)

v2.2.0 - Caesium

A bot that watches Blizzard's CDN and automatically posts new build updates to specified Discord channels.

Inspired by the original [Algalon bot by Ellypse](https://github.com/Ellypse/Algalon).

Includes some social integrations to post updates to different social media sites alongside Discord. This bot can be found on Twitter as [@algalon_ghost](https://algalon.ghst.tools/) and on Bluesky as [@algalon.ghst.tools](https://bsky.app/profile/algalon.ghst.tools/).

Check out the [changelog](CHANGELOG.md) to view the most recent changes.

Add Algalon to your server or account [here!](https://ghst.tools/algalon/install)

## Observable Branches
A lock indicates that the given branch is encrypted and not accessible to the public.
### Warcraft
| Branch Name | Readable Name |
| ----------- | ----------- |
| wow | Retail |
| wowt | Retail PTR |
| wowxptr | Retail PTR 2 |
| wow_beta | Beta |
| wow_classic | Cata Classic |
| wow_classic_ptr | Cata Classic PTR |
| wow_classic_beta | Classic Beta |
| wow_classic_era | Classic Era |
| wow_classic_era_beta | Classic Era Beta |
| wow_classic_era_ptr | Classic Era PTR |
| wowz | Submission |
| wowlivetest | Live Test |
| wowlivetest2 :lock: | Live Test Internal |
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
| fenristest | Diablo IV PTR |
| fenrisdev :lock: | Diablo IV Internal |
| fenrisdev2 :lock: | Diablo IV Internal 2 |
| fenrise :lock: | Diablo IV Event |
| fenrishf | Diablo IV Hotfix |
| fenrisvendor1 :lock: | Diablo IV Vendor |
| fenrisvendor2 :lock: | Diablo IV Vendor 2 |
| fenrisvendor3 :lock: | Diablo IV Vendor 3 |
| fenrisvendor4 :lock: | Diablo IV Vendor 4 |
| fenrisvendor5 :lock: | Diablo IV Vendor 5 |

### Warcraft Rumble
| Branch Name | Readable Name |
| ----------- | ----------- |
| gryphon | Warcraft Rumble Live |
| gryphonb | Warcraft Rumble Beta |
| gryphondev :lock: | Warcraft Rumble Internal |

### Battle.net
| Branch Name | Readable Name |
| ----------- | ----------- |
| catalogs | Catalogs |

## Commands

\*admin privileges required.

### CDN Watching

`/lastupdate`: Returns a timestamp displaying when Algalon last checked for CDN updates.

`/branches`: Returns a formatted list of all observable branches.

#### Watchlist Controls

`/watchlist edit`*: Returns a graphical editor for editing your guild's watchlist.

`/watchlist view`: Returns your guild's current watchlist.

#### Notification Channel Controls

`/channel set`*: Sets the channel in which it's invoked as the notification channel for your guild. Optionally, specify a game to set the notification channel for that game. Defaults to Warcraft.

`/channel get`: Returns the current notification channel for your guild. Optionally, specify a game to get the notification channel for that game. Defaults to Warcraft.

#### User DM Updates

`/dm edit`*: Returns a graphical editor for editing your personal watchlist.

`/dm view`: Returns all the branches you're currently subscribed to.

#### Metadata Monitoring

`/monitor edit`: Returns a graphical editor to configure DM notifications about game version metadata changes.

