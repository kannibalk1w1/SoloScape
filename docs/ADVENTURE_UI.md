# Adventure screens — first batch

In the SoloScape Controller plugin settings, enable **Custom quest journal** and **Custom skills screen** independently. Both default off. Open Quests or Skills from the Home wheel, then select an ordinary native entry. Quest journals show visible native objective text and completion markers; skills show current boosted/base levels and XP. D-pad changes focus/pages, right stick scrolls, and B uses the existing menu ancestry. Read-only objective rows offer no invented actions.

This batch also adds shared typography, focus colours, full detail text, pointer tooltips and page direction hints. Native item artwork can reappear from cache hits after relog without rendering an extra model. Sprite references are weak and copied artwork is bounded. Native presentation stays available through each independent toggle.

The combat, prayer and spellbook toggles currently provide the common grid presentation; their richer labels/state belong to the next batch.

Verified: client shadow jar and 157 tests, zero failures/errors, one existing optional SDL skip. The complete exported patch stack reproduces 90 source files. Claude reviewed the foundation; its native fallback and sprite ownership findings were addressed. Live quest/skill guide layouts and physical controller usability still need acceptance testing.

These images use the actual overlay renderer with synthetic journal data, not a live gameplay capture:

![765×503 journal renderer fixture](images/adventure-journal-765x503.png)

![1280×800 journal renderer fixture](images/adventure-journal-1280x800.png)
