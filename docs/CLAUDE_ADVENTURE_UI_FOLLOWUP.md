# Actual Claude foundation follow-up — 9 October 2026

Read-only review through the existing Claude terminal. Request `3d03ed6e-2e39-4aab-abd4-ab1b80017b24` was accepted with `turn_started`. Verbatim terminal findings:

```text
● No blockers remain; all four fixes are correct. I only read the current source, wrote nothing, and didn't look at the earlier draft.
  - Native fallback (275/499/741): the journal text now goes into Panel.details instead of a pane (ControllerUi.java:406-407). With the custom setting off, the native screen keeps only its real panes. With it on, PanelPresentation.present
    (lines 29-31) adds the Journal/Details pane, laid out as one column. These three groups never had a native "Controls" pane, so the journal text was the only thing in that list and no native control is lost.
  - Inventory grid: it is always laid out as 4 columns × 7 rows (PanelPresentation.java:25), whatever screen is open.
  - Artwork cache: native sprite reuse now uses a WeakHashMap capped at 256 (ControllerItemImages.java:16-21). Its values hold only the copied image, item and amount, so the cache can't keep a game sprite alive once the game drops it. The
    128-image cache is unchanged.
  - Journal text in the side column: the selected row's text is now word-wrapped and clipped to the content area (SoloScapePanelOverlay.java:81-86).
  One cosmetic leftover:
  - Line breaks: a journal line containing a <br> keeps its line break inside the text. The wrapper only splits on spaces, so that break may show as a stray character instead of a new line. Splitting the name on \n the same way the detail
    text already is would fix it.
```

The remaining journal newline rendering finding is fixed in the subsequent combat batch. Hardware/live layout acceptance remains separate.
