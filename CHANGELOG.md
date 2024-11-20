# Changelog v2.2.0 - Caesium

- Algalon is moving up in the world. With increased demand, speed has dropped and latency has increased. Algalon has now been (mostly) transitioned over to using an actual database instead of JSON files.
   - Ideally this would come with zero user-facing changes apart from increased speed and snapiness. Ideally.
   - If you encounter and issues or oddities, please let me know ASAP.

### Removed
- The commands to add/remove single branches to/from your guild watchlist and user watchlist have been removed. These have been replaced by the graphical editors found using `/watchlist edit` or `/dm edit`.
   - I know the UI is not amazing. My hands are tied by Discord, however, I do plan on building a website to handle configuration so we can finally save ourselves from this UX nightmare of Discord's making.