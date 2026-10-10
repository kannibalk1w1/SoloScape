# SoloScape on Steam Deck: player guide

> [!info] What this is
> SoloScape runs a private, single-player world on your Steam Deck. Each character has its own
> local world, and nothing connects to an official game server. This build has been prepared
> for **owner testing**. The automated **New** and **Continue** runs passed on a computer and on
> the Deck. Each one went around Lumbridge castle and the bank, saved, and resumed with the same
> character data. Automated runs aren't the same as a person playing, though. **The controller
> experience on a real Deck, held in your hands, Gaming Mode, and suspend/resume have not been
> accepted yet.** That's what your testing is for. Please note anything odd (see [[#Reporting what you find]]).

---

## 1. Launch

1. In **Steam**, open **Library**, choose the **Non-Steam** collection (or search), and select
   **SoloScape**.
2. Press **Play**. The SoloScape launcher window opens. It runs as a native Linux app. In the
   shortcut's **Properties → Compatibility**, leave **"Force the use of a specific Steam Play
   compatibility tool" OFF**, so it doesn't run through Proton.
3. The first launch can take a little while as it checks your characters and runtime.

> [!tip] Steam controller layout
> The launcher and game read the Deck's built-in controller directly. In the shortcut's
> controller settings, choose a **Gamepad** layout whose **trackpad works as a mouse**. Avoid
> layouts that turn buttons or the D-pad into keyboard keys or mouse clicks, because those
> would compete with SoloScape's own controller handling and can cause double actions. The
> trackpad mouse and the touchscreen remain your fallback for any screen the controller
> doesn't handle.

---

## 2. The launcher

The launcher lists your characters on the left and shows details and status on the right.

| Button | What it does |
|---|---|
| **New Character** | Creates a brand-new character with its own private world. |
| **Start Character** / **Continue** | Starts the selected world and opens the game. Start Character appears for a character that has never been played yet. |
| **Save & Quit** | Saves the running world, closes the game and makes a backup. Wait for it to finish. |
| **Back Up** / **Restore Backup** / **Manage Backups** | Manual backups (only while the world is stopped). |
| **Recover Session** | Appears only if a previous session didn't close normally. See [[#9. If something goes wrong]]. |
| **Diagnostics** | Checks the install. Useful if something won't start. |
| **Launcher Settings** | Game port and launcher options. You shouldn't need it. |

**Controller in the launcher:**

| Control | Action |
|---|---|
| D-pad / left stick | Move between buttons and characters |
| A | Activate |
| B | Back, or close a dialog |
| LB / RB | Move between controls |

> [!warning] "Desktop keyboard navigation (disables launcher controller)"
> This checkbox at the top is for people using a real keyboard. Leave it **unticked** for
> controller play. If the controller suddenly stops working in the launcher, untick it with the
> touchscreen or trackpad.

---

## 3. Create your first character

1. Select **New Character**.
2. Fill in two fields:
   - **Character label:** your own name for this save slot (1–48 characters).
   - **Account name:** the in-game name (1–12 letters, numbers, spaces or underscores).
3. **Start on Tutorial Island** is **off** by default. Leave it off to start in **Lumbridge**,
   which this guide assumes.
4. Select **Create character**, then **Start Character**.

### Typing names: Steam keyboard or SoloScape keyboard
The dialog has a keyboard choice. Only **one** keyboard listens at a time, so you won't get
double letters.

- **Steam / physical keyboard** (used on the Deck):
  - The Steam on-screen keyboard opens for the first field.
  - Type, then press **Enter** on it to move to the next field. Enter on the last field moves
    to **Create character**.
  - While the Steam keyboard is typing, the launcher ignores the controller.
  - To edit a field again, move to it and press **A**. Just moving across a field doesn't open
    the keyboard.
  - If you close the Steam keyboard by accident, press **Steam + X**, select **Open Steam
    keyboard**, or tap the field.
  - **Steam + X** is one of the Deck's Steam-button shortcuts. **Hold the Steam button** to
    see the full list on screen. Valve's guide:
    [Steam Deck – Basic use](https://help.steampowered.com/en/faqs/view/69E3-14AF-9764-4C28).
- **SoloScape controller keyboard:**
  - An on-screen grid appears in the dialog. D-pad selects a key, **A** types it, **X**
    deletes, **Y** moves to the next field, and **B** leaves the keyboard but keeps your text.
  - **LB/RB** move between fields.

If the name is rejected, the form stays open with your text and shows why.

---

## 4. Inside the game

The first time, the game logs in automatically and loads your world. Wait until you see your
character standing in Lumbridge.

### SoloScape Controller starts enabled
For a **new character**, the controller plugin starts **on**. You can go straight to
the first-run setup below. An explicitly saved choice to disable the plugin is retained.

If controls are disabled, use the **trackpad** as a mouse: open the sidebar with the
arrow in the title bar, click **Configuration**, scroll to **SoloScape Controller**,
and switch it on.

**Ctrl+F11** toggles the sidebar. **Ctrl+F12** toggles its current or last-opened
plugin panel. These shortcuts can be assigned to a button in Steam Input. Closing
the sidebar gives focus back to the game. A direct remappable controller sidebar
action and full-screen Gaming Mode acceptance remain planned work.

### First-run controller setup
When the plugin first starts, **Home → Settings** opens by itself with SoloScape's controller
preferences. It has four pages; switch between them with **LB/RB**:

| Page | What's there |
|---|---|
| **Basics** | Preset, deadzone, overlay size, run threshold, movement mode, server features, invert camera, button labels, controller guide, text keyboard, classic UI, server text cancellation |
| **Bindings** | Which button does what (each must be different) |
| **Screens** | Optional easier-to-read custom screens |
| **Finish** | Open the game's own settings, finish setup, or open the text keyboard |

**Recommended first-run choices:**
1. **Basics → Preset → STEAM_DECK.** This sets the standard buttons and 125% overlay size.
   The preset then shows **Custom** again, so your later changes stick.
2. Optionally, turn **Controller guide** on for a reminder panel of the controls while you
   learn.
3. Go to **Finish** and select **Finish controller setup**. You can reopen this anytime from
   **Home → Settings**.

Use **D-pad** and **A** to change values; **B** goes back. Every option here is reversible.

---

## 5. Controls

### Default buttons
| Control | In the world | In menus and screens |
|---|---|---|
| **Left stick** | Walk (camera-relative) | — |
| **LT (hold)** | Aim at targets without walking | — |
| **Right stick** | Turn and tilt the camera | **Scroll** supported lists and panes |
| **A** | Interact with the highlighted target | Use or select |
| **X** | Open the target's full action list | Open the item's action list |
| **B** | Stop or cancel | **Back** on supported screens |
| **LB / RB** | Previous / next target | Previous / next pane |
| **D-pad** | — | Move the focus |
| **Y** | Open the inventory | — |
| **View** (left small button) | **Home wheel** (all game tabs) | — |
| **Start / Menu** (right small button) | **Quick-action wheel** | — |
| **Right-stick click** | Open the text keyboard for chat (Steam keyboard mode) | — |

### Walking
- **Default, destination walking.** Tilt the left stick to walk; a gentle tilt goes about one
  tile ahead and a full tilt about three. Outlined tiles show where you are and where you're
  heading (**Show movement tiles** is on by default). When you let go, your character finishes the step
  already queued.
- **Optional, direct movement.** Set **Basics → Direct movement** on, together with **SoloScape
  server features** on, and you walk only while you hold the stick. Full tilt runs, above the
  **Run threshold** (default 90%). It's an experimental option; turn both off to go back.

### Aiming and interacting
- Walk toward something, or **hold LT** to aim without moving. The nearest valid thing in
  front of you gets a **gold outline and label** with its default action.
- Press **A** to do that action once.
- Press **LB / RB** to cycle to other nearby targets.
- Press **X** for the target's full action list. Choose with the **D-pad**, then **A** to use it
  or **B** to close the list.
- Press **B** in the world to stop walking or cancel what you're doing.

### Menus, B and the way back
- Press **View** to open the **Home wheel**: 16 tabs, starting with Inventory at the top.
  Pick a tab with the left stick or D-pad, then press **A** to open it.
- **B goes back one step on the supported screens.**
  - A tab opened from Home returns to the **Home wheel**, and B on the wheel returns to the
    world.
  - Settings and its game-settings sub-screens step back to their parent.
  - An inventory you opened directly with **Y** goes straight back to the world.
  - Some less common pop-ups or chains of screens may not follow this. If B doesn't close
    something, use the **trackpad mouse** or the touchscreen on the screen's own close
    button.
- In supported scrolling screens (quest journal, bank, shop, other long lists), the **right
  stick scrolls** the list you're in.
- Action-choice lists (the **X** list) are chosen with the **D-pad**, not scrolled with the
  right stick.

### Look of the controller screens
**Classic controller UI** (stone, brown and gold) is on by default. Turn it off in **Basics**
for the older modern look; the controls don't change. **Overlay size** (75–175%) makes the
panels bigger or smaller. 125–140% is easier to read on the Deck.

---

## 6. Inventory, equipment, bank and text prompts

### Inventory and equipment
- Press **Y** to open the inventory, then **D-pad** to move between slots.
- **A** uses the item's default action, such as Wield or Eat. **X** opens all of its actions.
- To use one item on another, choose **Use**, then pick the target. When it's done, or
  cancelled with **B**, you return to where you started. You can turn that off with **Return
  to selection source**.
- Open **Equipment** from the Home wheel to remove worn items.

### Bank
- Talk to a banker (aim, then **A**, or **X → Bank**).
- Move with the **D-pad**, use **LB/RB** to switch between the bank and your inventory, and
  scroll long banks with the **right stick**.
- **Withdraw-X / Deposit-X** asks for an amount. Type it, then press **Enter**.
  - To change your mind, tap **Cancel** in the **top-left panel**. The bank stays open and
    nothing moves.
  - Pressing B on the **Steam** keyboard may only **hide the keyboard**, and the amount box
    stays open. Use the panel's **Cancel** to actually cancel.
  - With the SoloScape controller keyboard, **B** cancels.
- **Search:** select **Search** and type part of an item's name; the bank filters to matches.
  - To finish typing, tap **Done** (or **Cancel**) in the top-left panel. The controller
    stays paused until you do.
  - Then select **Search** again to switch it off and show everything.

### Typing in the game (amounts, names, chat)
**Text keyboard** in **Basics** is set to **Automatic**, which uses the **Steam keyboard on
the Deck**.

- **Amount, name and search boxes** open the Steam keyboard automatically. Steam numeric mode
  is used for amounts.
- **Chat:**
  - press the **right stick in** (if that button isn't assigned to anything else);
  - or use **Home → Settings → Finish → Open text keyboard**;
  - or just start typing on a real keyboard.
- **While you type, the controller is paused** on purpose, so your button presses only type.
  Press **Enter** to send or confirm.
- A small panel in the **top-left** offers **Reopen** (bring the keyboard back), **Done** and
  **Cancel**. **Steam + X** also reopens the keyboard.
- **Hiding the Steam keyboard (for example with its own B) doesn't cancel anything.** The game
  still waits for your text, and the controller stays paused. Tap **Done** to confirm, or
  **Cancel** to cancel the amount, name or search.
- When typing ends, let go of all buttons and sticks for a moment; the controller then comes
  back. Menus you were in are kept: B still leads back the way you came.

Prefer an on-screen grid inside the game? Set **Text keyboard → SoloScape controller
keyboard**. With a physical keyboard, choose **Steam / physical keyboard**.

### Quick-action wheel (Start)
Eight slots, all **empty** at first.

1. **To assign:** focus food, a potion, a prayer, a spell or a special attack in its screen.
   Press **Start**, pick a slot, and press **X**.
2. **To use:** press **Start**, pick the slot, and press **A**.
3. **To clear:** press **Y** on a slot. **B** closes the wheel.

Potion slots use the lowest dose you have.

---

## 7. Saving and quitting

- **Normal quit:** go back to the launcher and select **Save & Quit**. Wait until it says the
  session closed. It saves, then makes an automatic backup. Closing the game window or the
  launcher also asks the world to save and close normally. Either way, **wait for it**.
- **Don't** switch the Deck off, hold the power button or force-close SoloScape from Steam while
  a world is running. If that happens anyway, use **Recover Session** next time.
- Automatic backups are made before each launch and after each clean shutdown. You can also
  make one yourself with **Back Up** while the world is stopped.
- **Continue** later picks up exactly where you saved.

---

## 8. A gentle first session in Lumbridge (about 30–45 minutes)

You start in **Lumbridge**, next to the castle. Take it slowly; there's no rush and no other
players.

1. **Look around.** Turn the camera with the right stick. Walk a few steps with the left stick
   and watch the outlined destination tile. Press **B** once to stop.
2. **Aim and interact.** Hold **LT**, sweep the left stick, and watch the gold target label
   change. Use **LB/RB** to cycle. Talk to someone with **A**, and try **X** to see all of
   their actions.
3. **Dialogue.** In a conversation, **A** continues and the **D-pad** chooses a reply. **B**
   leaves a normal conversation.
4. **Inventory.** Press **Y**. Starting outside Tutorial Island, your items may include basics
   such as a bronze sword and an empty pot. Wield the weapon with **A** (or **X → Wield**), then remove it from
   **Home → Equipment**.
5. **The castle kitchen.** It's on the ground floor of the castle; the Cook is there. Doors
   open with **A** on the door.
6. **Up to the bank.** Find the castle staircase and **Climb-up** twice to the top floor. The
   bank is there.
   - Deposit an item.
   - Try **Withdraw-X**, type a number, then tap **Cancel** in the top-left panel. The bank
     should stay open with
     nothing changed.
   - Withdraw the item normally.
   - Try **Search** for it, tap **Done**, then select **Search** again to switch it off.
7. **Home wheel tour.** Press **View** and open Skills, Quests and Settings. Press **B**
   repeatedly to see the way back to the world.
8. **Quick wheel.** Assign some food if you have any, and try using it.
9. **Save & Quit** from the launcher. Then **Continue** and check you're where you left off,
   with the same items.

---

## 9. If something goes wrong

| Symptom | Try this |
|---|---|
| Controller does nothing in the game | Make sure the game window is focused (tap it). Let go of all buttons and sticks for a moment; after menus or typing the controller waits for neutral. Check the **SoloScape Controller** plugin is switched on (see [[#SoloScape Controller starts enabled]]). If you see "bindings overlap", fix it in **Settings → Bindings**, or reset the plugin's settings. |
| Controller does nothing in the launcher | Untick **Desktop keyboard navigation**. |
| Stuck while typing (controller paused) | Tap **Done** or **Cancel** in the top-left panel (Enter also confirms). Hiding the Steam keyboard alone doesn't end typing. **Steam + X** reopens the keyboard. |
| Buttons do two things at once, or the D-pad moves a text cursor | Your Steam controller layout is probably sending keyboard or mouse inputs as well. Switch to a **Gamepad** layout with a mouse trackpad. |
| A menu won't close | Press **B** a few times. Press **View** for the Home wheel, then **B** to return to the world. The trackpad mouse always works too. |
| Can't reach something | Walk closer from a different side. Some objects can only be used from certain edges. |
| Game froze or closed unexpectedly | Return to the launcher. If the character shows **Recover Session**, select it; it safely stops the leftover world and makes a backup. Note: after a recovery the save is treated as **unconfirmed**. |
| Save & Quit is slow | Wait. It never force-kills the world. |
| Something looks wrong with your save | Stop the world, then use **Restore Backup**. The previous save is kept, not deleted. |
| Won't start at all | Use **Diagnostics** in the launcher and note what it reports. |

---

## 10. What hasn't been tested yet (please don't assume these work)

- **Gaming Mode** and **suspend/resume** (sleeping the Deck while playing) **have not been
  tested**. If you try them, **Save & Quit first** in case something goes wrong.
- **Physical controller feel:** whether buttons, sticks and trackpads feel right in your hands,
  readability at arm's length, and comfort over a long session.
- **A person playing the route.** The automated New and Continue runs passed on a computer and
  on the Deck, but none of the routes have been played by a person holding the Deck.
- **Steam keyboard behaviour across all screens**, and how well the touchscreen and trackpad
  work alongside the controller.
- OpenGL or other graphics modes; the game uses its standard software renderer in a window.
- Content beyond early Lumbridge.

---

## 11. Overnight testing checklist

**Before you start**
- [ ] Launch from **Library → Non-Steam → SoloScape → Play**.
- [ ] Create a **new** test character (Tutorial Island off).
- [ ] Turn on the **SoloScape Controller** plugin (Configuration → search "SoloScape").
- [ ] Complete first-run setup (Preset **STEAM_DECK**, then **Finish controller setup**).

**Play**
- [ ] Walk, stop with **B**, and turn the camera.
- [ ] Aim with **LT**, cycle with **LB/RB**, interact with **A**, open actions with **X**.
- [ ] Hold a short conversation.
- [ ] Inventory (**Y**): wield, then remove from Equipment.
- [ ] Go through the castle door and up the stairs twice to the bank.
- [ ] Bank: deposit, Withdraw-X then the top-left **Cancel**, normal withdraw.
- [ ] Bank Search: type, then **Done**/**Cancel**, then Search again to switch it off.
- [ ] Home wheel (**View**): open a tab, then **B** back to the wheel and to the world.
- [ ] Settings: open the game's own settings, then **B** all the way back.
- [ ] Type in chat once (right-stick click), send with **Enter**.
- [ ] Quick wheel (**Start**): assign, use, clear.

**Save and resume**
- [ ] **Save & Quit**, then wait for it to finish.
- [ ] **Continue**: same place, same items.
- [ ] **Save & Quit** again before stopping for the night.

**Optional (back up first)**
- [ ] Try **Direct movement** with **SoloScape server features** on, then turn both off again.
- [ ] Try the custom **Screens** (inventory, bank and so on), then turn them back off if you
  prefer.
- [ ] Try Gaming Mode. It's untested; **Save & Quit first**.

---

## Reporting what you find
For each issue, note:
- what you were doing and what you expected;
- what happened instead;
- **Desktop or Gaming Mode**;
- overlay size, classic or modern look, and text keyboard mode;
- a screenshot if you can. **Hold the Steam button** to see the Deck's shortcuts, including
  the screenshot one.

Don't share your save files or any login files. Describe the problem instead.
