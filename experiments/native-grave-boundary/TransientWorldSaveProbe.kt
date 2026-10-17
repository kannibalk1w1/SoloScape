package content.soloscape

import WorldTest
import content.entity.combat.hit.damage
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Assertions.*
import world.gregs.voidps.engine.data.AccountManager
import world.gregs.voidps.engine.data.PlayerSave
import world.gregs.voidps.engine.data.Settings
import world.gregs.voidps.engine.entity.World
import world.gregs.voidps.engine.entity.character.npc.NPCs
import world.gregs.voidps.engine.entity.character.player.Player
import world.gregs.voidps.engine.entity.item.floor.FloorItems
import world.gregs.voidps.engine.get
import world.gregs.voidps.engine.inv.add
import world.gregs.voidps.engine.inv.inventory
import world.gregs.voidps.engine.timer.epochSeconds
import world.gregs.voidps.engine.timer.setCurrentTime
import world.gregs.voidps.type.Tile
import java.io.File
import java.nio.file.Files

/** Diagnostic only: a reported gap is not a successful persistence contract. No production patch. */
class TransientWorldSaveProbe : WorldTest() {
    private val account = "grave_probe"
    private val deathTile = Tile(3235, 3220)
    private val supplied = listOf("logs", "bronze_dagger", "bronze_sword", "tinderbox")
    private val output get() = File(requireNotNull(System.getenv("SOLOSCAPE_GRAVE_OUTPUT")))

    @Test
    fun `Observe unrecovered death loot on either side of a cold JVM boundary`() {
        val phase = requireNotNull(System.getenv("SOLOSCAPE_GRAVE_PHASE"))
        setCurrentTime { 0L } // Same unexpired native clock in both independent JVMs.
        // WorldTest disables routine saves; enable them and keep every shutdown output private.
        settings["storage.disabled"] = "false"
        for ((key, suffix) in mapOf(
            "storage.grand.exchange.offers.buy.path" to "buy/",
            "storage.grand.exchange.offers.sell.path" to "sell/",
            "storage.grand.exchange.offers.claim.path" to "claims.toml",
            "storage.grand.exchange.offers.path" to "offers.toml",
            "storage.grand.exchange.history.path" to "history/",
        )) settings[key] = File(output, "exchange/$suffix").absolutePath

        val player = when (phase) {
            "before" -> createPlayer(deathTile, account).also { p ->
                supplied.forEach { assertTrue(p.inventory.add(it)) }
                tick()
                p.damage(101)
                tick(9)
                assertEquals(Tile(3221, 3219), p.tile)
                assertEquals(1, FloorItems.firstOrNull(deathTile, "tinderbox")?.amount)
                assertNotNull(NPCs.firstOrNull(deathTile) { it.id.startsWith("gravestone_") })
                assertTrue(requireNotNull(p.get<Long>("gravestone_time")) > epochSeconds())
                assertEquals(deathTile, p.get<Tile>("gravestone_tile"))
            }
            "after" -> {
                val baseline = PlayerSave.load(File(output, "saved/grave_probe.toml"))
                val candidate = File(Settings["storage.players.path"], "$account.toml")
                assertEquals(File(output, "saved/grave_probe.toml").readBytes().toList(), candidate.readBytes().toList())
                val fresh = PlayerSave.load(candidate).toPlayer()
                val accounts = get<AccountManager>()
                accounts.setup(fresh, null, 0, viewport = true)
                assertTrue(accounts.index(fresh))
                accounts.spawn(fresh, null)
                tick(3)
                assertArrayEquals(baseline.experience, fresh.experience.experience)
                assertEquals(baseline.tile, fresh.tile)
                assertEquals(baseline.inventories.keys, fresh.inventories.instances.keys)
                for ((id, items) in baseline.inventories) assertArrayEquals(items, fresh.inventories.inventory(id).items)
                fresh
            }
            else -> error("Unexpected phase")
        }
        supplied.filter { it != "tinderbox" }.forEach { assertEquals(1, player.inventory.count(it)) }
        assertEquals(0, player.inventory.count("tinderbox"))
        val count = FloorItems.firstOrNull(deathTile, "tinderbox")?.amount ?: 0
        val graves = NPCs.count { it.tile == deathTile && it.id.startsWith("gravestone_") }
        val marker = player.contains("gravestone_time") && player.contains("gravestone_tile")
        val mapMarkers = (1..5).count { slot ->
            player.get<String>("world_map_marker_type_$slot") == "grave" &&
                player.get<Int>("world_map_marker_$slot") == deathTile.id
        }
        val keptCount = supplied.filter { it != "tinderbox" }.sumOf { player.inventory.count(it) }
        val clock = epochSeconds()
        val expires = player.get<Long>("gravestone_time", -1L)
        // Execute the real world shutdown hook, including the actual primary save gate.
        World.shutdown()
        val saved = File(Settings["storage.players.path"], "$account.toml")
        assertTrue(saved.isFile)
        val disk = PlayerSave.load(saved)
        assertEquals(player.tile, disk.tile)
        val snapshot = File(output, "$phase-saved.toml")
        Files.copy(saved.toPath(), snapshot.toPath())
        if (phase == "before") {
            val retain = File(output, "saved").apply { mkdir() }
            Files.copy(saved.toPath(), File(retain, "$account.toml").toPath())
        }
        File(output, "$phase.json").writeText("""{
          "phase":"$phase", "pid":${ProcessHandle.current().pid()}, "clock_seconds":$clock,
          "grave_expires_seconds":$expires, "death_floor_count":$count, "grave_npc_count":$graves,
          "live_grave_variables":$marker, "grave_map_markers":$mapMarkers,
          "saved_grave_time":${disk.variables.containsKey("gravestone_time")},
          "saved_grave_tile":${disk.variables.containsKey("gravestone_tile")},
          "kept_items":$keptCount, "lost_item_inventory_count":${player.inventory.count("tinderbox")},
          "primary_save_present":${saved.isFile}
        }""")
    }
}
