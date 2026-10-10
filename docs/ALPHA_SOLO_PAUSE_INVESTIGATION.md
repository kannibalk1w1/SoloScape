# Solo pause: contained implementation investigation

Decision for this alpha: do not expose a world-pause toggle yet. Movement cancellation, menu focus and client suspension handling are implemented, but they do not freeze the world. The approved pause investigation is complete; a safe prototype needs the stage and clock separation below.

Inspected pinned implementation: `game/src/main/kotlin/GameTick.kt`, `Main.kt`, `engine/.../GameLoop.kt`, `InstructionTask.kt`, `entity/World.kt` and `timer/Ticks.kt`. The loop executes every stage, delays to its 600 ms cadence, and increments the shared `GameLoop.tick`. Gameplay timers use that counter; other content uses epoch time, including exchange history, buy limits and player kill timers.

A full-loop stop would also stop login/logout input, update traffic and queued saves. A stage-only stop that keeps incrementing GameLoop.tick would expire timers immediately on resume. Neither is suitable as a pause implementation.

A contained prototype should be default off and allowed only for one human in a local profile with bots disabled. It needs these separate paths:

| During pause | Required behavior |
|---|---|
| Network selector and connection queue | Keep running; accept disconnect/logout, reject or resume before a guest enters. |
| Instruction task | Drain input and discard gameplay actions; process only validated pause/resume, capability and logout instructions. Never replay queued clicks after resume. |
| World, NPC/player logic, hunting, item/object timers, exchange matching | Freeze simulation stages. |
| Shared game tick | Freeze simulation tick; maintain a separate network/housekeeping cadence. |
| Player/NPC reset and character updates | Continue enough bookkeeping and traffic to keep the client connected without progressing simulation. Test flag consumption carefully. |
| Save queue and logging | Keep running; saving must not wait for an unpaused simulation stage. |
| Second player/bot | Reject pause or automatically resume before their first gameplay tick. |
| Shutdown | Clear pause before normal World.shutdown/despawn/save hooks. Owned Save & Quit must finish while paused. |
| Wall-clock timers | Decide explicitly which should freeze. Existing epoch deadlines otherwise continue aging; never call that a complete freeze. |

Required tests before exposing it: idle connection stays alive, simulation tile/HP/counters remain fixed, resume requires neutral input, queued actions are discarded, guest login resumes, disconnect saves, Save & Quit finishes, and both tick- and epoch-based deadlines behave as documented. Run on disposable worlds first. No live game process, original save or running clock was altered for this investigation.

Native special attack investigation: controller navigation already exposes Combat tab 884's fresh native controls. The server's `SpecialAttack.drain` validates whether the current weapon supports a special and checks energy, including the ring-of-vigour reduction. A future quick slot should identify a fresh permitted native component and use ordinary interface dispatch; it must not set player variables or invent an opcode. A universal special shortcut is deliberately not claimed in this alpha.
