# Steam Deck deployment and measurement sprint — 10 October 2026

Authorized real-device sprint. Preserve SteamOS, original desktop worlds/cache, public main and user Steam configuration. Use owner-transferred assets only in a private home-folder test snapshot. This is not a distributable release.

- [x] D1 Reproducible private snapshot/manifest validation; exclude saves, credentials and local settings.
- [x] D2 Deploy compatible project-local Java 21/8, matched archives/content/cache and run Deck diagnostics.
- [ ] D3 Actual Deck Desktop launcher, native New/Continue, settings, logout/relog and save/restart checks.
- [ ] D4 Repeatable native render interval/resource/power observations; distinguish software/Desktop evidence from GPU/Gaming Mode acceptance.
- [ ] D5 Investigate and fix reproducible Deck blockers; maintain reversible settings and source patch reproduction.
- [ ] D6 Real-device owned-server recovery and lifecycle checks; bounded actual Claude review and verified commits/pushes.
- [ ] D7 Leave a usable launcher, Gaming Mode instructions, updated combined report/handoff/roadmap and physical acceptance checklist.

Physical sticks/buttons, ergonomics, Gaming Mode switching and suspend/resume may require owner participation. Do not infer them from SSH, synthetic input or render callbacks.

Deployment checkpoint: real SteamOS 3.8.28 Deck Desktop diagnostics pass with project-local Java 21/8. Snapshot listed files match; inherited matched-build checks remain intact. Actual SDL 2.32.56 detected the Steam Deck Controller in 100/100 samples. The actual Swing launcher adapter/backend probe passes after fixing a live-timer/synthetic held-A race in the harness (no production input change). Core native New/Continue/save/cancel passes, with four backups and unchanged legacy mutable-path fingerprints. Broad native adventure validation remains in progress: its first Desktop run failed at the mouse logout step. No Gaming Mode or physical mapping acceptance is inferred.
