# Upstream acknowledgements

SoloScape builds on the 2011Scape/Void project and its RuneLite-style revision-634
client. The source checkouts, game cache, binaries and save files are not included
in this repository.

- [2011Scape game server](https://github.com/2011Scape/game-server), pinned at
  `9f9113559eb686abd917893b5dca16404be07f93`: BSD 3-Clause, copyright GregHib.
  See [retained licence](licenses/2011scape-game-server-BSD-3-Clause.txt).
- [2011Scape client](https://github.com/2011Scape/runelite-client), pinned at
  `297bc8a4861755b676855664d32859054779c067`: BSD 3-Clause, copyright Greg Hibberd.
  See [retained licence](licenses/2011scape-client-BSD-3-Clause.txt).
- [634 reference client](https://github.com/2011Scape/634-client), pinned at
  `b39d45f49a0480f3f200fe3e31ad0798faf163ab`, is an optional reference checkout.
- RuneLite-derived files retain their own copyright and BSD notices within
  upstream source. JNA, SDL2, Java runtimes and other dependencies retain their
  respective licences; no dependency binaries are published here.

Patches that modify upstream files remain subject to those files' applicable
licences and notices. This repository does not grant rights to RuneScape assets,
trademarks or proprietary game resources. SoloScape is an independent project
and is not affiliated with Jagex, RuneLite or the upstream maintainers.

## Original SoloScape material

Original SoloScape material in this repository (scripts, launcher and updater
code, tests, documentation and the original parts of the patches) is licensed
under the [MIT License](LICENSE), copyright 2026 Kannibalkiwi.

The MIT License does not cover:

- upstream source files, or the lines of a patch that come from them; these keep
  the licences and notices listed above;
- RuneScape or Jagex assets, trademarks, the game cache, art and other
  proprietary game resources, none of which are included or licensed here;
- built jars, server data, JDKs, Gradle dependencies and other third-party
  binaries or data, which retain their own terms. A complete licence and
  dependency review is still required before distributing a game package.
