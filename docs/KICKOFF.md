# SoloScape 2011+ — Codex Kickoff Brief

## 0. Executive summary

Build a **fully local, single-player RuneScape experience based on the maintained 2011Scape/Void stack**, designed primarily for **Steam Deck and controller play**.

The target fantasy is:

> **“What if RuneScape had received a proper single-player console release around 2010–2011, then continued receiving carefully selected Old School RuneScape content without ever adopting Evolution of Combat?”**

This is **not** intended to become a public RSPS, MMO service, or modern OSRS clone.

The project should eventually provide:

- a local/offline RuneScape world;
- pre-EoC combat;
- Dungeoneering and Summoning-era progression;
- native Steam Deck/controller support inspired by **Diablo console controls**;
- a console-like launcher and save experience;
- adaptations for MMO systems that do not make sense in single player;
- curated backports of good OSRS content, reimplemented to fit the 2010–2011 ruleset and aesthetic;
- a clean separation between upstream 2011Scape code, SoloScape changes, and reference/import tooling;
- optional **private multiplayer hosting**, allowing a player to host their SoloScape world for a small group of friends without turning the project into a public MMO;
- a lightweight population of persistent **AI adventurers** who move, skill, fight, bank and chat so the offline world still feels inhabited.

The immediate goal is **not to implement all of this**.

The immediate goal is to establish a reliable development baseline, understand the current upstream projects, create a one-command local development workflow, and prototype the first native controller systems without destabilising the game.

---

# 1. Project principles

## 1.1 The game comes first

Do not turn this into a framework project that never becomes playable.

Every development phase should move toward a build that can be launched and played locally.

Prefer small, testable improvements over large rewrites.

## 1.2 Start from maintained 2011Scape, not an abandoned historical snapshot

Use the **currently maintained 2011Scape game server / Void fork** as the primary server base:

- https://github.com/2011Scape/game-server

The active 2011Scape client path currently centres on the **revision 634 client (2010-12-14)**:

- https://github.com/2011Scape/634-client
- https://github.com/2011Scape/runelite-client

The older revision 667 work is useful historical/reference material but is archived:

- https://github.com/2011Scape/rsmod-667-archive
- https://github.com/2011Scape/667-client-archive

Do **not** move the project onto the archived 667 stack simply because October 2011 sounds closer to the ideal date.

Revision 634 is already post-Dungeoneering and pre-EoC and, more importantly, is part of the maintained stack.

First prove the project on the supported upstream.

Treat a future move to a later 2011 revision as a separate engineering decision.

## 1.3 Single-player first, private multiplayer preserved

The default experience assumes one human player.

Networking should remain a first-class architectural capability because the upstream project is already a multiplayer client/server game.

The default user experience should be:

> launch game → continue save → play.

However, SoloScape should also preserve an optional private-host mode:

> host world → invite a few friends → play the same world together.

Do not design around public account registration, multiple public worlds, large public populations, donations, vote systems, web account panels, or other RSPS conventions.

Private multiplayer is a supported secondary mode, not the primary product identity.

Unless a feature is explicitly single-player-only, avoid implementing it in a way that assumes exactly one connected player.

## 1.4 Steam Deck is the primary platform

Primary target:

- Steam Deck / SteamOS
- Linux desktop

Secondary target later:

- Windows

Do not make Windows-only architectural choices unless unavoidable.

## 1.5 Native controller support, not “mouse mapped to a gamepad”

Steam Input can remain a useful fallback and development tool, but the goal is a client that understands controller intent natively.

The model is **Diablo on console**, not desktop RuneScape with joystick mouse emulation.

## 1.6 Preserve RuneScape mechanics

Controller support should change **how the player communicates intent**, not fundamentally alter RuneScape combat or skilling rules.

Examples:

- analogue stick movement may translate into normal RuneScape tile destinations;
- contextual interaction may choose a nearby NPC/object and call the existing interaction path;
- combat still uses normal RuneScape attack speeds, pathfinding, stats and server logic.

## 1.7 Curated OSRS backports, not a wholesale merge

Long term, SoloScape may implement selected OSRS content.

Examples that may fit well:

- Motherlode Mine
- Rooftop Agility
- Mahogany Homes
- Wintertodt
- Tempoross
- Guardians of the Rift
- selected Slayer monsters/bosses
- suitable quests
- clue additions
- quality-of-life systems

These should be **reimplemented** for the 2010–2011 ruleset and visual language rather than dumped into the old client unchanged.

## 1.8 Keep copyrighted game data out of the source repository

Do not commit proprietary RuneScape cache files, music, models, textures, dialogue dumps, or other Jagex assets into the SoloScape source repository.

The development/build tooling may work with game data supplied separately by the user where appropriate.

Do not connect to, impersonate, or automate interaction with official Jagex game servers.

---

# 2. Useful upstream/reference projects

## Primary base

### 2011Scape Game Server / Void

https://github.com/2011Scape/game-server

Current upstream characteristics worth preserving:

- Kotlin;
- Gradle;
- Java 21+;
- scriptable content architecture;
- configurable `game.properties`;
- local account creation;
- Linux startup support;
- cache tooling;
- AI player character support already exists in the wider Void project;
- server is designed to be customised without constantly modifying engine internals.

Upstream documentation currently describes local startup using `run-server.sh` or Gradle and a local client.

### Active client

https://github.com/2011Scape/634-client

and/or:

https://github.com/2011Scape/runelite-client

Determine which client repository is the correct current development target before making controller changes.

Do not assume based on repository names.

Record the result in `docs/UPSTREAM_RECON.md`.

### Cache editor

https://github.com/2011Scape/filestore-editor

Potentially useful later for custom/backported content.

Do not make cache editing part of the first milestone unless it is required to get upstream running.

## Historical/reference material

### 667 archive

https://github.com/2011Scape/rsmod-667-archive

Useful as a reference for later-2011 behaviour/content.

Do not make it the initial codebase.

### OpenRS2 Archive

https://archive.openrs2.org/

The archive preserves historical RuneScape and OSRS caches, including 2011-era caches.

Use it as a research/reference source where useful.

Do not automatically redistribute archived proprietary assets with SoloScape.

## OSRS behaviour/reference sources

Future OSRS backports can be informed by:

- OSRS Wiki mechanics and drop-rate documentation;
- RuneLite/OpenOSRS-derived public tooling where licence-compatible;
- OpenRS2 cache metadata;
- open-source OSRS server projects;
- historical Jagex update posts;
- community reverse-engineering/testing;
- documented formulas and probability tables.

Treat these as behavioural specifications.

Do not blindly copy code from projects with incompatible licences.

For every imported idea, track:

- source/reference;
- observed behaviour;
- SoloScape implementation;
- deliberate deviations for single-player balance.

---

# 3. Product vision

## 3.1 Player-facing experience

Eventually, launching SoloScape should feel like launching a normal game.

Target flow:

```text
Steam / Gaming Mode
        ↓
    SOLOSCAPE
        ↓
      PLAY
        ↓
local services start silently
        ↓
client opens
        ↓
Continue / New Character
        ↓
game world
```

The player should not need to know:

- what localhost is;
- that a RuneScape game server is running;
- what port it uses;
- how to launch Java;
- how to run Gradle;
- where server and client repositories live.

That abstraction comes later.

During development, terminal-based startup is acceptable.

---

# 4. Controller design target

## 4.1 Core philosophy

Controller input should operate on **game concepts**.

Bad long-term design:

```text
A = mouse left click
X = mouse right click
stick = mouse pointer
```

Acceptable temporary fallback:

```text
Steam Input / trackpad mouse
```

Desired design:

```text
A = primary interaction with focused world target
X = open context actions for focused target
B = cancel / close / back
Y = inventory or configurable primary panel

Left stick = direct character movement
Right stick = camera rotate / pitch

D-pad = interface navigation / quick access
Bumpers = tab/target cycling
Triggers = modifiers/radial actions
```

The mouse and Steam Deck trackpad should continue to work as a fallback.

## 4.2 Direct movement

RuneScape remains tile/path based.

Do not attempt to replace server movement with analogue physics.

Prototype:

```text
left stick direction
        ↓
deadzone + magnitude
        ↓
project a short destination in that direction
        ↓
existing client pathfinding / walking request
        ↓
existing movement protocol
```

Design goals:

- movement should feel continuous;
- avoid constant micro-repathing;
- avoid twitching;
- use a configurable update interval;
- preserve collision and existing pathfinding;
- stop immediately/cleanly when stick returns to deadzone.

Suggested first prototype:

- deadzone: configurable;
- target projection: 2–5 tiles depending on stick magnitude;
- destination update: approximately 100–200 ms;
- feature-flagged so keyboard/mouse behaviour is untouched.

Do not hardcode these values permanently before testing.

## 4.3 Camera

Desired:

```text
Right stick X → rotate camera
Right stick Y → pitch
R3 → optional camera reset / face movement direction
```

Reuse existing camera functions wherever possible.

Do not create a second camera system.

## 4.4 Contextual world interaction

This is one of the most important systems.

The client should maintain a focused nearby interactable based on factors such as:

- distance from player;
- direction of left-stick movement or camera;
- screen-space proximity to reticle/centre;
- target type;
- whether it is currently reachable;
- recent target selection;
- combat state.

Potential focused types:

- NPC
- player-like AI NPC
- object
- ground item
- door
- resource node
- enemy

Basic presentation:

```text
        Oak tree
      [ Chop down ]
```

Press `A`:

- invoke the normal first/default interaction for that object.

Press `X`:

- open the normal RuneScape context actions in a controller-friendly list.

Do not duplicate server interaction logic.

The controller layer should ultimately resolve to the same existing interaction pipeline used by mouse actions.

## 4.5 Combat target behaviour

Do not implement hard Souls-style lock-on as the default.

Desired behaviour is a soft focus:

```text
Goblin
Attack
```

Potential controls:

- A = default attack/interact
- L1/R1 = cycle valid nearby targets
- X = context actions
- B = cancel focus

The exact mapping can change after testing.

## 4.6 Interface navigation

RuneScape's grid interfaces are very suitable for controllers.

Controller focus should eventually support:

- inventory;
- equipment;
- bank;
- shops;
- prayer;
- magic;
- skills;
- dialogue options;
- Dungeoneering interfaces;
- reward shops;
- settings.

Basic inventory behaviour:

```text
D-pad / stick → move focus between slots
A             → default action
X             → context menu
B             → back
```

Do not attempt to convert every interface immediately.

Create a reusable focus-navigation system and migrate interfaces incrementally.

## 4.7 Radial menus

Potential later feature.

Useful for:

- prayers;
- spells;
- teleports;
- food/potions;
- common tabs;
- emotes.

Example:

```text
Hold L2

           Protect Melee

Protect Range       Protect Magic

              Piety
```

Do not implement in first sprint.

---

# 5. Single-player systems

These are later milestones but architecture should not block them.

## 5.1 Save model

Eventually the user experience should be character/save based rather than account/server based.

Possible presentation:

```text
Kieran
Combat 73
Total 1186
Falador
42h 17m

[ Continue ]
```

Multiple local saves may be supported later.

For now:

- preserve normal upstream account persistence;
- make sure clean local shutdown saves reliably;
- document where character state is stored;
- do not invent a new persistence layer in sprint 1.

## 5.2 Pause / suspend

Long-term goal:

- game should tolerate Steam Deck suspend/resume;
- local server should not treat Deck sleep like an MMO disconnect catastrophe;
- ideally world simulation can be paused when appropriate.

Do not implement this until the local launcher lifecycle is understood.

## 5.3 Simulated economy

Long-term design:

- optional local Grand Exchange simulation;
- configurable price model;
- not an infinite instant shop;
- trades can take simulated time;
- economy can respond to player activity;
- period RuneScape and later OSRS price data may be used as reference, not blindly mirrored.

This is out of scope for initial implementation.

### Historical Grand Exchange data

Do not invent the starting economy if usable historical data exists.

Research and snapshot appropriate public/community datasets before implementing the economy model.

Useful reference sources include:

- RuneScape Wiki **Grand Exchange Market Watch**;
- Wiki historical item price charts/data;
- WeirdGloop exchange-history API;
- documented historical market indices;
- archived wiki pages around 2010–2012;
- later OSRS price histories where they help model comparable goods;
- historical update dates that explain major discontinuities.

Known useful facts at project kickoff:

- the Grand Exchange Market Watch tracks market indices from late 2007 onward;
- historical index adjustments are explicitly documented in 2011 and 2012;
- community tooling was generating historical charts for thousands of GE items by 2009;
- WeirdGloop exposes historical exchange endpoints used by RuneScape community tooling.

Do **not** assume complete daily 2011 history exists for every tradeable item.

Build a data-quality report.

Create:

`docs/GE_HISTORICAL_DATA.md`

For each source/data series record:

```text
item
item id/revision context
source
earliest available date
latest available date
sampling interval
price available?
volume available?
missing ranges
known discontinuities
licence/attribution requirements
```

### How to use historical data

The objective is not necessarily to replay the exact real-world 2011 economy day-by-day.

Use historical information to derive:

- plausible starting price;
- relative item values;
- long-term trend;
- volatility;
- liquidity;
- typical spread/price movement;
- response to game updates;
- relationships between raw materials and finished goods.

Example:

```text
2011 historical series
        ↓
baseline value + volatility profile
        ↓
SoloScape simulated market
        ↓
player/bot supply and demand alters it over time
```

This allows a new SoloScape world to feel like the correct era while still becoming its own local economy.

### Era presets

Consider eventually supporting an economy seed preset:

```text
2010
2011
late-2011
custom
```

A preset may establish initial/reference prices without forcing the simulated world to follow historical prices forever.

### Price relationships

Where full historic series are absent, infer carefully from:

- alchemy values;
- NPC shop prices;
- production inputs;
- skill requirements;
- known historical snapshots;
- neighbouring/comparable items;
- documented market indices.

Record inferred values separately from observed historical values.

### Avoid exact-market false precision

If historical data for an item is sparse, do not fabricate a detailed curve and present it as authentic.

Track confidence:

```text
HIGH      dense historic series
MEDIUM    multiple snapshots / index context
LOW       inferred from related items
CUSTOM    SoloScape balance decision
```

The final economy should be believable, explainable and tunable rather than pretending to reproduce data that does not exist.

## 5.4 AI adventurers / living-world population

This is a meaningful SoloScape feature rather than decorative NPC spawning.

Current Void already contains a substantial bot framework with:

- bot/player entities;
- activity management;
- behaviour state;
- navigation;
- perception;
- combat actions;
- equipment/loadout handling;
- bot management/debug tooling;
- contextual public chat;
- short-term conversational memory;
- personality/persona values;
- skill/item/NPC/location/quest entity recognition.

Before implementing anything new, audit and reuse upstream bot systems.

Create:

`docs/AI_ADVENTURERS.md`

### Design goal

The offline world should feel like a low-population RuneScape world rather than an abandoned MMO.

The player should naturally encounter believable adventurers:

```text
Lumbridge
- new player killing goblins
- fisher walking to the bank
- woodcutter at normal trees
- player cooking food

Varrock
- players entering/leaving banks
- smith/miner travelling through
- occasional trader/bankstander

Grand Exchange
- larger concentration of idle/trading/skilling players

Slayer/dungeons
- occasional combat-oriented adventurer
```

Do not attempt to simulate thousands of human-equivalent agents.

### Population director

Prefer a server-side **population director** rather than static fixed bots everywhere.

It should decide how many simulated players should be visible in a region based on:

- location;
- activity type;
- time/context;
- player proximity;
- configured world-population setting.

Initial rough density targets may look like:

```text
remote countryside     0–2
ordinary skilling spot 2–4
small town             3–8
Lumbridge              5–10
Varrock/Falador        6–15
Grand Exchange         12–25
obscure dungeon        0–3
```

These are design starting points, not hard requirements.

### Persistent identities

Prefer a stable pool of persistent bot accounts over generating anonymous new characters every visit.

A bot may retain:

- account/display name;
- appearance;
- combat level;
- skill XP/levels;
- bank;
- inventory;
- equipment;
- coin balance;
- preferred activities;
- home/preferred regions;
- personality;
- current long-term goal;
- relationships/recent conversations where useful.

This allows the player to repeatedly see familiar adventurers progressing over time.

Example:

```text
Monday:
KebabLord — Mining in Falador

Wednesday:
KebabLord — banking coal

Next week:
KebabLord — wearing upgraded armour
```

This persistence is more valuable than highly sophisticated AI.

### Activity model

Bots should use a goal/activity system rather than an LLM deciding every action.

Example:

```text
Goal: Train Woodcutting

choose suitable tree for level
        ↓
travel to activity area
        ↓
use normal Woodcutting interaction
        ↓
gain normal XP/resources
        ↓
inventory full
        ↓
bank / burn / drop depending on persona/activity
        ↓
continue
```

Good initial activity candidates:

- woodcutting;
- fishing;
- mining;
- cooking;
- firemaking;
- basic melee combat;
- banking;
- walking between nearby towns.

Later:

- Slayer;
- ranged/magic combat;
- smithing;
- crafting;
- Agility;
- minigames;
- Dungeoneering;
- trading.

Do not require every bot to support every activity.

### Archetypes

Bots may have weighted archetypes to make the population varied.

Examples:

```text
Noob
- Lumbridge/Varrock
- low combat
- mixed equipment
- goblins/basic skilling
- occasional confused chat

Skiller
- several non-combat goals
- banks resources
- low/moderate combat

PvMer
- trains combat
- Slayer
- uses food/potions
- upgrades equipment

Traveller
- spends more time moving between towns/content

Bankstander
- remains around busy social/economic hubs
- occasional chat/trading flavour
```

Archetypes should affect probabilities rather than rigidly lock behaviour.

### Full simulation vs background simulation

Do not fully simulate every bot in the entire world every tick.

Use two levels where practical.

**Active/local simulation**

For bots near a human player:

- real pathfinding;
- visible movement;
- normal object/NPC interactions;
- normal animations;
- normal combat;
- real inventory/bank effects;
- contextual chat.

**Background simulation**

For distant persistent bots:

```text
current activity
+
elapsed time
+
skill/equipment state
        ↓
coarse progression update
```

Example:

```text
Bot is fishing in Draynor
10 minutes pass while no human is nearby
→ award an appropriate bounded amount of fishing progress/resources
→ update inventory/bank/activity state
```

When the human enters the area, materialise the bot back into normal simulation at a plausible state/location.

Background simulation must never give impossible progress or bypass important requirements.

### Chat

Reuse Void's existing lightweight bot-chat system before considering any generative AI.

The upstream system already supports:

- RuneScape-style slang/typo normalisation;
- intent recognition;
- entities such as skills, items, NPCs, quests and locations;
- short conversational memory;
- persona-driven reply style;
- awareness of current activity and travel destination;
- typed and Quick Chat-style replies.

SoloScape should extend the training/reply data with period-appropriate ambient conversation.

Examples:

```text
"wc lvl?"
"gz"
"nice"
"brb"
"where varrock"
"any1 dung?"
"selling lobs"
```

Avoid cloud/LLM dependencies for baseline bot chatter.

### Bot-to-bot chatter

Do not allow unrestricted bots to recursively respond to each other.

That can create noisy artificial conversations and unnecessary processing.

If desired, add occasional population-director-authored ambient exchanges such as:

```text
Bot A: wc lvl?
Bot B: 73
Bot A: nice
```

These should be infrequent flavour events.

### World navigation

Audit Void's existing bot navigation graph and `go_to` behaviours.

Build reliable long-distance navigation incrementally.

Initial travel network might prioritise:

```text
Lumbridge
↔ Draynor
↔ Varrock
↔ Grand Exchange
↔ Edgeville
↔ Falador
```

Support traversal actions such as:

- doors;
- gates;
- stairs;
- ladders;
- common teleports;
- transport systems;

only as required by activities.

Do not block the first ambient-bot release on universal world navigation.

### Interaction with multiplayer

AI adventurers belong to the **server world**, not to individual clients.

If a private multiplayer host has AI adventurers enabled:

- all human players see the same bots;
- bot inventories/XP are shared authoritative state;
- bot actions are simulated once;
- the population director should account for number of human players.

### Performance target

Start with a modest persistent population and benchmark on Steam Deck.

Suggested architecture target:

```text
persistent simulated identities: ~50–150
fully active around humans:      ~10–40
```

These are targets for experimentation, not promises.

The world should feel inhabited before bot count is increased.

### Economy integration — later

AI adventurers may eventually become one input into the simulated Grand Exchange.

Examples:

```text
bot mines coal
→ banks coal
→ may list some on simulated GE

player sells equipment
→ suitable bot may consume/buy it

bot kills monsters
→ loot enters its inventory/economy
```

Do not couple the first AI-adventurer implementation to the economy simulator.

Ambient life must work independently.

### Staging

Implement in steps:

1. **Ambient population** — names, appearance, movement, idle behaviour.
2. **Simple activities** — basic skilling/combat/banking.
3. **Contextual chat** — configure/extend existing Void chat.
4. **Persistent progression** — XP, equipment, banks and goals survive.
5. **Regional/world travel** — bots move between activities.
6. **Advanced content** — Slayer, Dungeoneering, minigames.
7. **Economy participation** — optional later integration.

This feature is out of scope for the controller/bootstrap sprint, but architecture should avoid preventing it.

## 5.5 Multiplayer activities

Long term, classify activities as:

1. already solo-capable;
2. suitable for AI teammates/opponents;
3. suitable for mechanical redesign;
4. not worth adapting.

Examples:

- Dungeoneering: real solo mode;
- Pest Control: AI adventurer teammates;
- Castle Wars: bot teams if worth doing;
- Duel Arena: generated opponents;
- Barbarian Assault: potentially AI party, but expensive to implement.

Do not attempt these before core single-player play is stable.

---

# 6. Optional private multiplayer

## 6.1 Goal

SoloScape should preserve the ability for a player to host their game as a small private RuneScape server.

Typical target:

```text
Host
  +
1–7 friends
```

The exact supported player count does not need to be artificially capped if the upstream server naturally supports more, but all SoloScape-specific UX and testing should prioritise small friend groups rather than MMO-scale operation.

This should reuse the normal Void/2011Scape networking architecture.

Do not build a second networking stack.

## 6.2 Desired player-facing modes

Long-term launcher concept:

```text
SOLOSCAPE

[ Continue Solo ]

[ Host Private World ]

[ Join Private World ]

[ Settings ]
```

### Continue Solo

- starts a local server bound safely for local use;
- auto-connects the local client;
- behaves like a normal single-player game;
- requires no networking knowledge.

### Host Private World

- starts the same game server with private-host networking enabled;
- makes the host's world available to invited players;
- displays connection information in a human-readable way;
- optionally supports a join password / allow-list;
- should default to secure/private behaviour.

### Join Private World

- connect to a friend's SoloScape host;
- server address should be entered once and remembered;
- later consider Steam friend/invite integration if practical;
- direct IP/LAN/Tailscale-style connectivity is acceptable before any richer invite system.

Do not create a public server browser in early development.

## 6.3 Architecture rule

**Solo mode and multiplayer mode should use the same core server simulation.**

Avoid:

```text
SoloGameEngine
MultiplayerGameEngine
```

Prefer:

```text
Void / SoloScape Server
        │
        ├── 1 connected human = solo
        └── N connected humans = private multiplayer
```

This greatly reduces divergence and lets multiplayer benefit automatically from content improvements.

## 6.4 Persistence model

Research upstream persistence before changing anything.

Preferred long-term behaviour:

### Solo

The local world owns the player's save.

### Hosted multiplayer

The host owns the world/server data and the characters created on that host.

A friend connecting to Host A and Host B may therefore have different character saves unless a later portable-character system is deliberately designed.

Do **not** attempt portable cross-server characters in the first implementation.

This avoids duplication, rollback and authority problems.

Document the final persistence choice in:

`docs/MULTIPLAYER_DESIGN.md`

## 6.5 Single-player adaptations must degrade safely in multiplayer

This is the biggest architectural consideration.

Future SoloScape systems must declare whether they are:

- safe in both solo and multiplayer;
- host-authoritative;
- disabled in multiplayer;
- require a multiplayer-specific implementation.

Examples:

### Pause

Single player:

```text
Pause menu
→ world simulation may pause
```

Multiplayer:

```text
Pause menu
→ only local UI pauses
→ server world continues
```

Never freeze a hosted world because one guest opens a menu.

### Steam Deck suspend

Solo:
- local server may pause or suspend safely.

Host:
- suspending the host may disconnect guests;
- UI must warn the host if connected players exist.

Guest:
- guest suspension should behave like a normal disconnect/reconnect.

### Simulated Grand Exchange

The economy simulation should be host/server authoritative.

All players on that private world interact with the same local simulated market.

### AI adventurers

AI population belongs to the server/world, not each client.

Do not spawn duplicate ambience NPCs for every connected human.

### Save & Quit

Solo:
- save and stop local server.

Host:
- warn if guests are connected;
- cleanly save all connected characters;
- shut down server.

Guest:
- save/disconnect only that guest.

## 6.6 Cooperative content

Do not redesign every activity for multiplayer immediately.

Preserve existing upstream multiplayer behaviour wherever it already works.

Later, private co-op creates useful options for:

- Dungeoneering parties;
- group skilling;
- bosses;
- minigames;
- trading;
- quests where multiple players happen to be nearby.

Solo adaptations should not unnecessarily remove original multiplayer capability.

Dungeoneering in particular should support both:

```text
1-player party
```

and:

```text
small friend party
```

using the same dungeon system where upstream architecture permits it.

## 6.7 Controller support is client-side

Native controller work should remain independent of whether the player is:

- solo;
- hosting;
- joining another server.

Controller intent should resolve into the same normal client actions/network messages.

Never create special server packets purely because an action came from a controller.

## 6.8 Networking/security scope

Early private hosting can be intentionally simple.

Prioritise:

1. localhost;
2. LAN;
3. user-managed VPN/overlay networking such as Tailscale;
4. direct remote hosting with explicit configuration.

Do not immediately implement:

- NAT punch-through;
- relay infrastructure;
- matchmaking;
- central accounts;
- public discovery;
- anti-cheat;
- public moderation infrastructure.

Those would turn a small co-op feature into an online-service project.

If Steam networking/invite APIs can later provide private friend joining without operating SoloScape backend infrastructure, investigate it as a separate milestone.

## 6.9 Private multiplayer acceptance milestone

Before calling private multiplayer supported, verify:

1. Host launches a world.
2. Host can play locally.
3. Second client joins from another machine.
4. Each player has independent persisted character state.
5. Both see each other's movement.
6. Trading/basic player interaction works if upstream supports it.
7. Both can interact with the same NPC/object systems.
8. Server remains authoritative.
9. Guest disconnect does not damage host save.
10. Host clean shutdown saves all character data.
11. Controller and keyboard/mouse clients can coexist.
12. Solo-only pause/suspend logic does not freeze or corrupt hosted sessions.

## 6.10 Complexity judgement

Preserving small-scale multiplayer is expected to be **low-to-moderate incremental complexity** because the upstream project is already a multiplayer server.

The expensive mistake would be removing or bypassing networking while building SoloScape, then trying to reconstruct it later.

Therefore:

> preserve multiplayer architecture now; polish private hosting later.

If a future single-player feature would require substantial architectural compromise to remain multiplayer-safe, document the trade-off and prefer a clean feature flag or multiplayer-safe implementation rather than silently breaking hosting.

---

# 7. Dungeoneering

Dungeoneering is a core identity feature.

The project should eventually audit current upstream support for:

- dungeon generation;
- floors/themes;
- complexity;
- party size = 1;
- room generation;
- keys/doors;
- skill doors;
- resources;
- equipment;
- binding;
- bosses;
- prestige;
- XP;
- death handling;
- reward shop;
- tokens;
- progression.

Create a dedicated future document:

`docs/DUNGEONEERING_AUDIT.md`

Do not assume missing features.

Inspect upstream implementation first.

For each system mark:

- complete;
- partial;
- stub;
- absent;
- bugged;
- multiplayer-dependent.

Dungeoneering should remain mechanically RuneScape, while controller traversal should make it feel excellent on Steam Deck.

---

# 8. OSRS backport philosophy

## 7.1 The 2011 Rule

A later OSRS feature may be considered when:

1. it does not require EoC-style abilities;
2. it does not destroy 2011 progression;
3. it can be visually reconciled with the older RuneScape aesthetic;
4. it can work well for a single player;
5. it adds meaningful gameplay;
6. it can be independently reimplemented from documented behaviour.

## 7.2 Behaviour over asset dumping

Prefer:

> understand how an OSRS mechanic works → implement equivalent behaviour in Void.

Avoid:

> copy a modern cache blob into the project and hope.

## 7.3 Content manifests

Create a future backport metadata format.

Suggested location:

```text
content-reference/
├── 2011/
├── osrs/
└── backports/
```

Example manifest:

```yaml
content: motherlode_mine

source_game: osrs

references:
  - osrs_wiki
  - runelite
  - open_source_server_reference

target:
  ruleset: soloscape-2011
  client_style: 2010-2011

status:
  mechanics: planned
  map: planned
  assets: planned
  controller: planned

adaptations:
  - reward progression rebalanced for solo economy
```

This should eventually distinguish:

- authentic source behaviour;
- inferred behaviour;
- SoloScape-specific changes.

Do not build this full database during bootstrap.

A small schema/proposal document is enough.

## 7.4 Candidate backports by difficulty

### Good early candidates

- new Slayer tasks;
- drop tables;
- simple shops;
- skilling recipes;
- QoL features;
- clue steps;
- monsters using existing asset families.

### Medium candidates

- Motherlode Mine;
- Mahogany Homes;
- Rooftop Agility;
- Kraken-style bosses;
- Wintertodt.

### Large expansion candidates

- Tempoross;
- Guardians of the Rift;
- large quest lines;
- new continents;
- raids;
- Varlamore-scale areas.

Do not touch large expansion candidates during early development.

---

# 9. Proposed workspace layout

Do not collapse everything into one giant modified upstream repository immediately.

Suggested local workspace:

```text
soloscape-workspace/
│
├── server/
│   └── fork/clone of 2011Scape game-server
│
├── client/
│   └── correct active 2011Scape client
│
├── launcher/
│   └── SoloScape lifecycle/packaging work
│
├── tools/
│   └── reference/import/audit tooling
│
├── docs/
│   ├── UPSTREAM_RECON.md
│   ├── ARCHITECTURE.md
│   ├── CONTROLLER_DESIGN.md
│   ├── CONTENT_ROADMAP.md
│   ├── MULTIPLAYER_DESIGN.md
│   ├── AI_ADVENTURERS.md
│   ├── GE_HISTORICAL_DATA.md
│   └── DUNGEONEERING_AUDIT.md
│
└── scripts/
    ├── dev-run.sh
    ├── dev-stop.sh
    └── doctor.sh
```

If a different structure is substantially better after inspecting upstream, document why before changing direction.

Preserve upstream git history where practical.

---

# 10. Configuration

Introduce a SoloScape-specific development configuration rather than scattering constants.

Possible future settings:

```properties
soloscape.enabled=true
soloscape.singlePlayer=true

soloscape.controller.enabled=true
soloscape.controller.deadzone=0.18
soloscape.controller.movement.enabled=true
soloscape.controller.worldFocus.enabled=true

soloscape.local.autoLogin=false
soloscape.pauseOnSuspend=false
```

Do not overbuild configuration during bootstrap.

Only add settings that are actually used.

---

# 11. Logging and diagnostics

Controller and interaction work will be much easier with explicit diagnostics.

Add development-only logging for:

- detected controller name/GUID;
- connect/disconnect;
- stick values after deadzone;
- current controller mode;
- movement destination requests;
- currently focused world target;
- interaction action dispatched;
- server/client lifecycle state.

Avoid per-frame log spam.

Support a verbose/debug flag.

A future on-screen debug overlay could show:

```text
Controller: Steam Deck
Move: (0.72, -0.14)
Movement target: (3214, 3421)
Focused entity: Oak tree [ID ...]
Action: Chop down
```

Do not make the debug overlay mandatory in the first change.

---

# 12. Testing strategy

Do not rely solely on “it seems to work.”

## Server

Preserve upstream tests.

Add focused unit/integration tests for SoloScape server changes.

## Client

Where possible, separate controller calculations from rendering/input polling so they can be tested as pure logic.

Good test candidates:

- deadzone function;
- stick-to-direction conversion;
- tile projection;
- focus scoring;
- target cycling;
- grid navigation;
- mode transitions.

## Statistical tests later

For OSRS backports/drop tables:

- simulate large numbers of rolls;
- compare observed probability to configured expected probability;
- test tertiary rolls independently where required.

## Manual Steam Deck checklist

Maintain:

`docs/STEAM_DECK_TEST_CHECKLIST.md`

Eventually cover:

- launch from Gaming Mode;
- controller detected;
- keyboard not required for basic play;
- movement;
- camera;
- interaction;
- inventory;
- dialogue;
- suspend/resume;
- save/quit;
- 1280×800;
- UI scaling;
- trackpad fallback.

---

# 13. Do not do these things yet

Codex should explicitly avoid the following in the first implementation pass:

- rewriting the server;
- porting the client to another engine;
- changing the network protocol;
- migrating from 634 to 667;
- importing modern OSRS maps;
- implementing a Grand Exchange simulation;
- implementing AI adventurers;
- implementing raids;
- rebuilding Dungeoneering from scratch;
- replacing account persistence;
- adding dozens of configuration options;
- trying to support every controller;
- refactoring unrelated upstream code;
- mass-formatting the upstream repositories;
- committing proprietary caches/assets;
- building a public multiplayer service.

---

# 14. First development phase — Upstream reconnaissance

This is mandatory before significant modification.

## Deliverable

Create:

`docs/UPSTREAM_RECON.md`

It should answer:

### Server

- What exact upstream commit is being used?
- What Java/Kotlin/Gradle versions are required?
- How is the cache supplied?
- How are accounts persisted?
- What storage backend is used by default?
- What is the clean server shutdown path?
- Which settings already exist for local/offline development?
- Where are player movement requests handled?
- Where are NPC/object interactions handled?
- What Dungeoneering code currently exists?
- What AI-player code currently exists?
- Is there already a single-player/local mode?
- What address/interface does the server bind to by default?
- What configuration is needed for LAN/private remote clients?
- How are simultaneous logins/accounts handled?
- Which player-to-player systems are currently implemented?
- What assumptions would break if SoloScape-specific systems used one-player-only global state?
- Are there existing hooks useful for SoloScape?

### Client

- Which current client repo should SoloScape modify?
- What revision does it target?
- How is client input currently handled?
- Where are keyboard inputs handled?
- Where are mouse clicks translated into menu actions?
- Where is camera movement implemented?
- Where does pathfinding/walk-click begin?
- How are inventory/widget clicks handled?
- What rendering modes/resizable modes already exist?
- Does the client already use RuneLite-style plugin/input abstractions?
- Is controller/gamepad support already partially present through any dependency?
- What library would be the least invasive choice for Linux/Steam Deck gamepad input if no support exists?

### Licensing

- Record licences of every upstream dependency/repository touched.
- Do not copy code across incompatible licences.

---

# 15. Second development phase — Reproducible local launch

Before native controller work, make the current upstream stack easy to run.

## Goal

From the workspace root:

```bash
./scripts/doctor.sh
./scripts/dev-run.sh
```

should be enough for a developer who has supplied the required game data/cache.

### `doctor.sh`

Check:

- Java version;
- Gradle prerequisites;
- required cache/data directories;
- required client files;
- ports;
- basic Linux dependencies;
- expected repo directories.

Give actionable errors.

Do not download proprietary game assets automatically.

### `dev-run.sh`

Development version may:

1. start server;
2. wait for server readiness;
3. start client;
4. stream useful logs;
5. cleanly stop child processes on Ctrl+C.

Later this becomes the basis for a graphical/Steam launcher.

### Acceptance criteria

- confirmed on Linux;
- server launches;
- client connects locally;
- new local player can be created;
- character persists across restart;
- shutdown does not corrupt state;
- instructions captured in `README-SOLOSCAPE.md`.

---

# 16. Third development phase — Controller input foundation

Do not immediately implement the full Diablo scheme.

First create a clean input abstraction.

## Desired abstraction

Something conceptually similar to:

```text
InputDeviceManager
├── KeyboardMouseInput
└── GamepadInput
```

and a controller state such as:

```text
GamepadState
- leftStickX/Y
- rightStickX/Y
- triggers
- buttonsPressed
- buttonsHeld
- buttonsReleased
```

Exact names should follow surrounding client style.

## Requirements

- Steam Deck controls detected on Linux;
- standard Xbox-style controller should also work if straightforward;
- controller hot-plug should not crash client;
- keyboard/mouse remains functional;
- controller support can be disabled;
- no per-frame object allocation if avoidable;
- no arbitrary heavyweight framework if a small existing dependency already fits.

Before adding a dependency, document:

- licence;
- Linux/Steam Deck support;
- maintenance status;
- native library implications;
- packaging implications.

---

# 17. Fourth development phase — First playable controller prototype

After input abstraction is stable, implement only:

## A. Right-stick camera

Acceptance:

- rotate with right-stick X;
- pitch with right-stick Y;
- configurable deadzone;
- keyboard/mouse camera still works.

## B. Left-stick RuneScape movement

Prototype tile projection into the existing walking/pathfinding system.

Acceptance:

- pushing stick moves character;
- releasing stick stops issuing destinations;
- collision/pathfinding remains normal RuneScape;
- no wild oscillation;
- no direct manipulation of server coordinates;
- movement implementation is feature-flagged.

## C. A-button contextual interaction — simplest version

Do not build the ultimate targeting algorithm yet.

First version may choose the nearest sensible interactable within a small radius/cone.

Acceptance:

- visibly/logically identify one focused NPC/object;
- A invokes its normal default action through existing interaction code;
- mouse actions still work;
- no server-side special case specifically for controller input.

## D. Inventory controller focus

Implement one reusable grid-navigation proof of concept for inventory.

Acceptance:

- D-pad navigates inventory slots;
- clear visual focus;
- A invokes default inventory action;
- X opens normal item context actions if practical;
- B exits controller focus;
- mouse remains usable.

---

# 18. First sprint output

Codex should aim to finish with:

```text
docs/
├── UPSTREAM_RECON.md
├── ARCHITECTURE.md
├── CONTROLLER_DESIGN.md
└── STEAM_DECK_TEST_CHECKLIST.md

scripts/
├── doctor.sh
├── dev-run.sh
└── dev-stop.sh     (only if actually useful)

plus:
- minimal SoloScape configuration;
- controller input abstraction;
- right-stick camera prototype;
- left-stick movement prototype;
- basic world-focus/A interaction prototype;
- inventory navigation proof of concept;
- tests for pure controller math where feasible.
```

If upstream architecture makes any of the controller prototypes unsafe or substantially larger than expected, do **not** hack around it.

Instead:

1. implement the clean infrastructure that is possible;
2. document the blocker;
3. provide the smallest next experiment.

---

# 19. Definition of success for the first playable milestone

On a Steam Deck or Linux PC with a controller:

1. User runs one development command.
2. Local server starts.
3. Client starts and connects.
4. Existing character loads.
5. User can move around Lumbridge using left stick.
6. User can rotate/pitch camera using right stick.
7. Nearby NPC/object can be focused.
8. User can press A to perform a normal RuneScape interaction.
9. User can open/navigate the inventory without using a mouse.
10. Mouse/keyboard still function.
11. Character state persists after a clean restart.

Nothing beyond this is required to validate the controller concept.

---

# 20. Next milestones after controller proof

Do not begin these until the first milestone is demonstrably usable.

## Milestone 2 — Controller UX

- better focus scoring;
- target cycling;
- dialogue navigation;
- bank/shop navigation;
- prayer/spell navigation;
- contextual button hints;
- controller glyphs;
- larger UI/text options;
- radial menu experiment;
- trackpad/mouse fallback behaviour.

## Milestone 3 — Deck-native application lifecycle

- launcher;
- bundled/runtime-managed Java where legally/licensably appropriate;
- silent local server lifecycle;
- auto-connect;
- save/quit flow;
- clean error UI;
- Steam Gaming Mode launch;
- 1280×800 defaults;
- suspend/resume investigation.

## Milestone 4 — Private multiplayer smoke test

Before introducing systems that substantially alter world simulation:

- run two clients against one SoloScape server;
- confirm two persisted human accounts;
- test LAN connection;
- test one controller client and one keyboard/mouse client;
- document server binding/firewall configuration;
- verify future solo-specific features are not relying on one-player global state.

Create:

`docs/MULTIPLAYER_DESIGN.md`

This is a compatibility milestone, not yet a polished host/join UI.

## Milestone 5 — Single-player audit

Create:

- `DUNGEONEERING_AUDIT.md`
- `SOLO_CONTENT_AUDIT.md`
- `MMO_DEPENDENCY_AUDIT.md`
- `AI_ADVENTURERS.md`
- `GE_HISTORICAL_DATA.md`

Classify existing content by how well it works alone.

## Milestone 6 — First single-player adaptation

Pick one contained improvement.

Examples:

- Dungeoneering solo polish;
- one multiplayer activity converted for solo;
- basic local-world lifecycle improvement.

Do not start with the Grand Exchange simulation unless research shows it is unusually easy.

## Milestone 7 — Living-world prototype

Audit the existing Void bot framework before adding new AI infrastructure.

Prototype a small population around Lumbridge/Draynor:

- persistent names/appearances;
- simple movement;
- one or two skilling activities;
- banking;
- existing contextual bot chat;
- clean enable/disable configuration.

Benchmark CPU/RAM/tick impact on Steam Deck.

Do not implement full economy participation yet.

## Milestone 8 — First OSRS-style backport

Choose a small content addition that proves the pipeline.

Do **not** start with a raid or new continent.

Prefer something like:

- a new Slayer monster;
- small skilling activity;
- small quest/mechanic;
- simple drop-table/content backport.

For the first backport, create a complete content manifest and document every reference source.

---

# 21. Engineering rules for Codex

## Keep changes small

Do not generate thousands of lines before testing.

Prefer a sequence of small commits:

```text
docs: document upstream client/server architecture
build: add Linux development doctor script
dev: add local server/client launcher
client: add gamepad input abstraction
client: add right-stick camera
client: prototype controller movement
client: prototype world target focus
client: add inventory focus navigation
```

## Preserve upstream style

Before modifying a subsystem:

- inspect neighbouring classes;
- follow existing naming;
- follow existing dependency patterns;
- follow existing test style.

Do not impose an unrelated architecture because it is fashionable.

## Feature flags

Experimental SoloScape behaviour should be easy to disable while stabilising it.

## Document uncertain assumptions

If behaviour is inferred rather than confirmed, mark it.

## Avoid magic numbers

Controller tuning values should have named constants/configuration.

## No speculative refactor

Do not “clean up” unrelated code.

## Prefer reuse

If RuneScape already has:

- pathfinding;
- menu actions;
- widget focus;
- camera controls;
- entity selection;

route controller intent into those systems.

Do not duplicate them.

---

# 22. Questions Codex should answer during reconnaissance

Do not ask the user these questions until the repositories have been inspected.

Resolve as many as possible from code first.

1. Which 2011Scape client is the correct maintained target?
2. Is the client currently fixed or resizable?
3. What is the safest input insertion point?
4. Can controller movement reuse an existing “walk to tile” method directly?
5. How are right-click menu actions represented internally?
6. Can a world entity's default action be invoked without synthesising a mouse event?
7. Is there already entity-under-cursor or entity-picking code reusable for controller focus?
8. Is there an existing focus/navigation abstraction for widgets?
9. Which controller library, if any, is already transitively available?
10. How does the server persist accounts?
11. Can the server cleanly stop after the client exits?
12. What Dungeoneering implementation is already present?
13. Which current upstream features would be broken by assuming one human player?
14. What bot activities, navigation, combat and chat systems are already implemented upstream?
15. How are bot identities/state persisted, if at all?
16. Can bot activities call the same skilling/content systems as human players?
17. What is the practical cost of 10, 25, 50 and 100 active bots?
18. Which historical GE datasets can provide actual 2010–2012 item prices and at what resolution?
19. What is the minimum legal/distributable package we can build without bundling proprietary assets?

---

# 23. Research notes for later OSRS implementation

When implementing later content, use community-documented information as a specification.

For each mechanic capture:

```text
Name
Source game/version
Reference URLs
Requirements
Inputs
Outputs
XP
Timing/ticks
Success formula
Combat formula
Drop table
Tertiary rolls
NPC/object IDs used only as reference
State variables
Edge cases
Known uncertainties
SoloScape deviations
```

For probabilistic content, add automated statistical tests.

For example:

```text
Expected unique drop: 1 / 128
Simulated rolls: 5,000,000
Observed frequency must remain within an appropriate statistical tolerance.
```

The goal is to avoid traditional “private-server guesswork.”

---

# 24. Naming

Working title:

**SoloScape**

Variant/branch name:

**SoloScape 2011+**

Use this as a working development name only.

Do not spend time on logos, branding or public release infrastructure during bootstrap.

---

# 25. Initial Codex instruction

Start by doing the following, in order:

1. Create a new working branch named something like `soloscape/bootstrap`.
2. Inspect the current 2011Scape server and active client repositories.
3. Build/run both **without modification** on Linux if the required user-supplied game data is available.
4. Write `docs/UPSTREAM_RECON.md`.
5. Propose the minimum-change architecture in `docs/ARCHITECTURE.md`.
6. Add a Linux `doctor.sh` and reproducible development launch script.
7. Confirm clean persistence across a restart.
8. Identify the client input/camera/pathfinding/menu-action code paths.
9. Add a gamepad input abstraction behind a SoloScape feature flag.
10. Implement right-stick camera as the first real controller feature.
11. Then prototype left-stick tile movement.
12. Then implement the smallest possible contextual A-button interaction.
13. Then implement inventory grid navigation.
14. Keep each change small and test it before moving to the next.
15. Stop and document rather than performing a broad rewrite if a subsystem proves substantially different from the assumptions in this brief.

At the end of the first pass, provide:

- what runs;
- what changed;
- exact launch instructions;
- tests performed;
- controller hardware/input detected;
- known bugs;
- architectural discoveries;
- what should be implemented next.

---

# 26. Source/reference links

Primary references at project kickoff:

- 2011Scape organisation: https://github.com/2011Scape/
- Game server: https://github.com/2011Scape/game-server
- Active 634 client: https://github.com/2011Scape/634-client
- RuneLite-style client repo: https://github.com/2011Scape/runelite-client
- Cache editor: https://github.com/2011Scape/filestore-editor
- Archived 667 server work: https://github.com/2011Scape/rsmod-667-archive
- OpenRS2 archive: https://archive.openrs2.org/
- RuneScape Wiki Grand Exchange Market Watch: https://runescape.wiki/w/RuneScape:Grand_Exchange_Market_Watch
- WeirdGloop API: https://api.weirdgloop.org/

Keep this list updated in the repository as the project discovers better or more authoritative references.

---

# 27. Final intent

The target is not:

> “a private server that happens to run on a Steam Deck.”

The target is:

> **a coherent single-player-first RuneScape RPG with 2010–2011 mechanics, native console controls, excellent Steam Deck UX, carefully curated later content, and optional small-scale private multiplayer.**

The first milestone is successful when walking around and interacting with RuneScape using a controller feels natural enough that the project is obviously worth continuing.
