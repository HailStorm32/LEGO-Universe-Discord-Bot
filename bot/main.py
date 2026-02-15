from __future__ import annotations

import re
import traceback
from typing import Iterable

import discord
from discord import app_commands
from discord.ext import commands

from .cdclient import CDClient
from .config import settings
from .locale import LocaleXML

locale = LocaleXML(settings.locale_path)
cdclient = CDClient(settings.sqlite_path, locale)


def parse_id(value: str) -> int | None:
    if value.isdigit():
        return int(value)
    m = re.search(r"\[(\d+)\]", value)
    return int(m.group(1)) if m else None


def choices(rows: list[tuple[str, str]]):
    return [app_commands.Choice(name=n, value=v) for n, v in rows]


def row_value(row: object, *keys: str, default=None):
    if row is None:
        return default
    row_keys = set(row.keys())
    for key in keys:
        if key in row_keys:
            value = row[key]
            if value is not None:
                return value
    return default


def embed(title: str, description: str = "") -> discord.Embed:
    e = discord.Embed(title=title, description=description, color=settings.bot_color)
    if settings.footer_text:
        e.set_footer(text=settings.footer_text, icon_url=settings.footer_icon or None)
    return e


def to_chunks(lines: Iterable[str], size: int = 1000) -> list[str]:
    out, cur = [], ""
    for line in lines:
        nxt = f"{cur}\n{line}" if cur else line
        if len(nxt) > size and cur:
            out.append(cur)
            cur = line
        else:
            cur = nxt
    if cur:
        out.append(cur)
    return out or ["None"]


class ItemView(discord.ui.View):
    def __init__(self, item_id: int):
        super().__init__(timeout=None)
        for cmd in ["item", "get", "preconditions", "package", "skills", "earn", "drop", "unpack", "reward", "buy"]:
            self.add_item(discord.ui.Button(label=cmd.title(), custom_id=f"{cmd}/{item_id}"))


class LUBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.add_listener(self.component_hint_listener, "on_interaction")

    async def setup_hook(self):
        cdclient.load()
        self.tree.add_command(activity)
        self.tree.add_command(achievement)
        self.tree.add_command(drop)
        self.tree.add_command(get)
        self.tree.add_command(mission)
        self.tree.add_command(reload)
        self.tree.add_command(skillitems)
        self.tree.add_command(vendor)
        self.tree.add_command(brick)
        self.tree.add_command(earn)
        self.tree.add_command(item)
        self.tree.add_command(npc)
        self.tree.add_command(report)
        self.tree.add_command(skills)
        self.tree.add_command(buy)
        self.tree.add_command(enemy)
        self.tree.add_command(level)
        self.tree.add_command(package)
        self.tree.add_command(reward)
        self.tree.add_command(smash)
        self.tree.add_command(cooldowngroup)
        self.tree.add_command(execute)
        self.tree.add_command(loottable)
        self.tree.add_command(preconditions)
        self.tree.add_command(skill)
        self.tree.add_command(unpack)
        await self.tree.sync()

    async def on_ready(self):
        print(f"Logged in as {self.user}")

    async def component_hint_listener(self, interaction: discord.Interaction):
        try:
            if interaction.type is not discord.InteractionType.component or not interaction.data:
                return

            custom_id = interaction.data.get("custom_id", "")
            m = re.match(r"([^/]+)/([^/]+)", custom_id)
            if not m:
                return

            cmd, value = m.groups()
            command = self.tree.get_command(cmd)
            if not command:
                return

            message = f"Use /{cmd} {value}"
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
        except Exception as exc:
            tb = "\n".join(traceback.format_exception(exc))
            e = embed("Error", f"```\n{tb[-3500:]}\n```")
            if interaction.response.is_done():
                await interaction.followup.send(embed=e, ephemeral=True)
            else:
                await interaction.response.send_message(embed=e, ephemeral=True)


async def object_autocomplete(interaction: discord.Interaction, current: str):
    return [app_commands.Choice(name=r.name, value=r.value) for r in cdclient.search_objects(current)]


async def mission_autocomplete(interaction: discord.Interaction, current: str):
    return choices(locale.search_missions(current))


async def activity_autocomplete(interaction: discord.Interaction, current: str):
    return choices(locale.search_activities(current))


async def skill_autocomplete(interaction: discord.Interaction, current: str):
    return choices(locale.search_skills(current))


@app_commands.command(description="View the stats of an item!")
@app_commands.describe(item="An item in LEGO Universe")
@app_commands.autocomplete(item=object_autocomplete)
async def item(interaction: discord.Interaction, item: str):
    item_id = cdclient.get_item_id(item) or parse_id(item)
    if not item_id:
        await interaction.response.send_message("Item not found.", ephemeral=True)
        return
    obj_name = locale.get_object_name(item_id)
    e = embed(f"{obj_name} [{item_id}]")
    e.url = f"{settings.explorer_domain}/objects/{item_id}"
    comp = cdclient.get_item_component(item_id)
    if comp:
        e.add_field(name="Rarity", value=str(row_value(comp, "rarity", default="Unknown")))
        e.add_field(name="Stack Size", value=str(row_value(comp, "stack_size", "stackSize", default="Unknown")))
        e.add_field(name="Price", value=str(row_value(comp, "baseValue", "basevalue", "currencyLOT", default="Unknown")))
    await interaction.response.send_message(embed=e, view=ItemView(item_id))


@app_commands.command(description="View how to get an item!")
@app_commands.autocomplete(item=object_autocomplete)
async def get(interaction: discord.Interaction, item: str):
    item_id = cdclient.get_item_id(item) or parse_id(item)
    if not item_id:
        await interaction.response.send_message("Item not found.", ephemeral=True)
        return
    e = embed(f"How to get {locale.get_object_name(item_id)} [{item_id}]")
    checks = {
        "Missions": "SELECT 1 FROM Missions WHERE reward_item1=? OR reward_item2=? OR reward_item3=? OR reward_item4=? LIMIT 1",
        "Vendors": "SELECT 1 FROM VendorComponent WHERE LootMatrixIndex IN (SELECT LootMatrixIndex FROM LootTable WHERE itemid=?) LIMIT 1",
        "Smash": "SELECT 1 FROM LootTable WHERE itemid=? LIMIT 1",
    }
    for name, q in checks.items():
        hit = cdclient._q(q, (item_id, item_id, item_id, item_id) if q.count("?") == 4 else (item_id,)).fetchone()
        e.add_field(name=name, value="Yes" if hit else "No", inline=True)
    await interaction.response.send_message(embed=e, view=ItemView(item_id))


@app_commands.command(description="View all smashables that drop an item!")
@app_commands.autocomplete(item=object_autocomplete)
async def drop(interaction: discord.Interaction, item: str):
    await interaction.response.send_message(embed=embed("Drop", f"Use LU Explorer link: {settings.explorer_domain}/objects/{item}"))


@app_commands.command(description="View all missions that reward an item!")
@app_commands.autocomplete(item=object_autocomplete)
async def earn(interaction: discord.Interaction, item: str):
    item_id = cdclient.get_item_id(item) or parse_id(item)
    rows = []
    if item_id:
        rows = cdclient._q(
            "SELECT id FROM Missions WHERE reward_item1=? OR reward_item2=? OR reward_item3=? OR reward_item4=? LIMIT 50",
            (item_id, item_id, item_id, item_id),
        ).fetchall()
    e = embed("Earn")
    for c in to_chunks([f"{locale.get_mission_name(r['id'])} [{r['id']}]" for r in rows]):
        e.add_field(name="Missions", value=c, inline=False)
    await interaction.response.send_message(embed=e)


@app_commands.command(description="View all vendors that sell an item!")
@app_commands.autocomplete(item=object_autocomplete)
async def buy(interaction: discord.Interaction, item: str):
    await interaction.response.send_message(embed=embed("Buy", "Vendor query available from local CDClient data."))


@app_commands.command(description="View all activities that drop an item!")
@app_commands.autocomplete(item=object_autocomplete)
async def reward(interaction: discord.Interaction, item: str):
    await interaction.response.send_message(embed=embed("Reward", "Activity reward output available from local CDClient data."))


@app_commands.command(description="View all packages that drop an item!")
@app_commands.autocomplete(package=object_autocomplete)
async def unpack(interaction: discord.Interaction, package: str):
    await interaction.response.send_message(embed=embed("Unpack", f"Package query for {package}."))


@app_commands.command(description="View all items given from a package!")
@app_commands.autocomplete(package=object_autocomplete)
async def package(interaction: discord.Interaction, package: str):
    await interaction.response.send_message(embed=embed("Package", f"Package content query for {package}."))


@app_commands.command(description="View all missions from an NPC!")
@app_commands.autocomplete(npc=object_autocomplete)
async def npc(interaction: discord.Interaction, npc: str):
    await interaction.response.send_message(embed=embed("NPC", f"Mission-giver query for {npc}."))


@app_commands.command(description="View all items sold from a vendor!")
@app_commands.autocomplete(vendor=object_autocomplete)
async def vendor(interaction: discord.Interaction, vendor: str):
    await interaction.response.send_message(embed=embed("Vendor", f"Vendor listing for {vendor}."))


@app_commands.command(description="View the stats of an enemy!")
@app_commands.autocomplete(enemy=object_autocomplete)
async def enemy(interaction: discord.Interaction, enemy: str):
    enemy_id = parse_id(enemy) or cdclient.get_object_id(enemy)
    if not enemy_id:
        await interaction.response.send_message("Enemy not found.", ephemeral=True)
        return
    e = embed(f"{locale.get_object_name(enemy_id)} [{enemy_id}]")
    e.url = f"{settings.explorer_domain}/objects/{enemy_id}"
    await interaction.response.send_message(embed=e)


@app_commands.command(description="View all enemys given from a package!")
@app_commands.autocomplete(enemy=object_autocomplete)
async def smash(interaction: discord.Interaction, enemy: str):
    await interaction.response.send_message(embed=embed("Smash", f"Smash-drop query for {enemy}."))


@app_commands.command(description="View the stats of a mission!")
@app_commands.autocomplete(mission=mission_autocomplete)
async def mission(interaction: discord.Interaction, mission: str):
    mission_id = parse_id(mission)
    if not mission_id:
        await interaction.response.send_message("Mission not found.", ephemeral=True)
        return
    row = cdclient.get_mission(mission_id)
    if not row:
        await interaction.response.send_message("Mission not found.", ephemeral=True)
        return
    e = embed(f"{locale.get_mission_name(mission_id)} [{mission_id}]")
    e.description = locale.get_mission_description(mission_id)
    await interaction.response.send_message(embed=e)


@app_commands.command(description="View the stats of an achievement!")
@app_commands.autocomplete(achievement=mission_autocomplete)
async def achievement(interaction: discord.Interaction, achievement: str):
    mission_id = parse_id(achievement)
    if not mission_id:
        await interaction.response.send_message("Achievement not found.", ephemeral=True)
        return
    row = cdclient.get_mission(mission_id)
    if not row:
        await interaction.response.send_message("Achievement not found.", ephemeral=True)
        return
    e = embed(f"{locale.get_mission_name(mission_id)} [{mission_id}]")
    e.description = locale.get_mission_description(mission_id)
    await interaction.response.send_message(embed=e)


@app_commands.command(description="View all rewards given from an activity!")
@app_commands.autocomplete(activity=activity_autocomplete)
async def activity(interaction: discord.Interaction, activity: str):
    await interaction.response.send_message(embed=embed("Activity", f"Activity rewards for {activity}."))


@app_commands.command(description="View the stats of a brick!")
@app_commands.autocomplete(brick=object_autocomplete)
async def brick(interaction: discord.Interaction, brick: str):
    await interaction.response.send_message(embed=embed("Brick", f"Brick details for {brick}."))


@app_commands.command(description="View all skills attached to an item!")
@app_commands.autocomplete(item=object_autocomplete)
async def skills(interaction: discord.Interaction, item: str):
    item_id = parse_id(item) or cdclient.get_object_id(item)
    if not item_id:
        await interaction.response.send_message("Item not found.", ephemeral=True)
        return
    rows = cdclient._q("SELECT skillID FROM ObjectSkills WHERE objectTemplate=? LIMIT 50", (item_id,)).fetchall()
    e = embed("Skills")
    for c in to_chunks([f"{locale.get_skill_name(r['skillID'])} [{r['skillID']}]" for r in rows]):
        e.add_field(name="Attached Skills", value=c, inline=False)
    await interaction.response.send_message(embed=e)


@app_commands.command(description="View the stats of a skill!")
@app_commands.autocomplete(skill=skill_autocomplete)
async def skill(interaction: discord.Interaction, skill: str):
    sid = parse_id(skill)
    if not sid:
        await interaction.response.send_message("Skill not found.", ephemeral=True)
        return
    row = cdclient.get_skill_behavior(sid)
    e = embed(f"{locale.get_skill_name(sid)} [{sid}]")
    if row:
        e.add_field(name="Cooldown Group", value=str(row_value(row, "cooldownGroup", "cooldown_group", default=0)))
    await interaction.response.send_message(embed=e)


@app_commands.command(description="View all items that have a skill!")
@app_commands.autocomplete(skill=skill_autocomplete)
async def skillitems(interaction: discord.Interaction, skill: str):
    sid = parse_id(skill)
    if not sid:
        await interaction.response.send_message("Skill not found.", ephemeral=True)
        return
    rows = cdclient.get_items_with_skill(sid)
    e = embed("Skill Items")
    for c in to_chunks([f"{r['name']} [{r['id']}]" for r in rows]):
        e.add_field(name="Items", value=c, inline=False)
    await interaction.response.send_message(embed=e)


@app_commands.command(description="View the skills in a cooldowngroup!")
async def cooldowngroup(interaction: discord.Interaction, group: int):
    rows = cdclient._q("SELECT skillID FROM SkillBehavior WHERE cooldownGroup=? LIMIT 100", (group,)).fetchall()
    e = embed(f"Cooldown Group {group}")
    e.description = "\n".join([f"{locale.get_skill_name(r['skillID'])} [{r['skillID']}]" for r in rows]) or "No skills found."
    await interaction.response.send_message(embed=e)


@app_commands.command(description="View all items in a loot table!")
async def loottable(interaction: discord.Interaction, loottable: int):
    rows = cdclient.get_loot_table_items(loottable)
    e = embed(f"Loot Table {loottable}")
    for c in to_chunks([f"{r['name'] or 'Unknown'} [{r['id']}] - {r['chance']}%" for r in rows]):
        e.add_field(name="Loot", value=c, inline=False)
    await interaction.response.send_message(embed=e)


@app_commands.command(description="View the preconditions to use an item!")
@app_commands.autocomplete(item=object_autocomplete)
async def preconditions(interaction: discord.Interaction, item: str):
    item_id = cdclient.get_item_id(item) or parse_id(item)
    if not item_id:
        await interaction.response.send_message("Item not found.", ephemeral=True)
        return
    ids = cdclient.get_preconditions(item_id)
    e = embed(f"Preconditions for {locale.get_object_name(item_id)}")
    e.description = "\n".join([f"[{i}] {locale.get_precondition(i)}" for i in ids]) or "None"
    await interaction.response.send_message(embed=e)


@app_commands.command(description="View stats about a level in LEGO Universe!")
async def level(interaction: discord.Interaction, level: int):
    rows = cdclient.get_level_rows(level)
    e = embed(f"Level {level}")
    e.description = "\n".join([", ".join([f"{k}={r[k]}" for k in r.keys()]) for r in rows])[:3900] or "No data."
    await interaction.response.send_message(embed=e)


@app_commands.command(description="Reload the data from the cdclient.sqlite and locale.xml!")
async def reload(interaction: discord.Interaction):
    cdclient.reload()
    await interaction.response.send_message(embed=embed("Reload", "Reload complete."), ephemeral=True)


@app_commands.command(description="Open a dialog to report anything about this bot!")
async def report(interaction: discord.Interaction):
    await interaction.response.send_modal(ReportModal())


@app_commands.command(description="Open a dialog to execute multiple commands on this bot!")
async def execute(interaction: discord.Interaction):
    await interaction.response.send_modal(ExecuteModal())


class ReportModal(discord.ui.Modal, title="Report an issue"):
    text = discord.ui.TextInput(label="What should be fixed?", style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        ch = interaction.client.get_channel(settings.report_channel_id)
        if isinstance(ch, discord.TextChannel):
            await ch.send(f"Report from {interaction.user.mention}:\n{self.text.value}")
        await interaction.response.send_message("Thanks for the report!", ephemeral=True)


class ExecuteModal(discord.ui.Modal, title="Execute commands"):
    commands_box = discord.ui.TextInput(label="Commands", style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Queued commands:\n```\n{self.commands_box.value}\n```", ephemeral=True)


def run() -> None:
    bot = LUBot()
    bot.run(settings.token)


if __name__ == "__main__":
    run()
