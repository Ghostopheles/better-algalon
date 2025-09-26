# Changelog v2.1.1 - Thorium

## Fixed
- Transitioned from the old websocket-based Ribbit system to one that uses HTTP instead
   - TCP websockets appear to no longer be supported by Ribbit
- Fixed an issue that caused the `/dm subscribe` command for new users to break Algalon entirely (oops)
- Improved error messages