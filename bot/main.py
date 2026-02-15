from __future__ import annotations

import re
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


async def send_embed(interaction: discord.Interaction, embed_obj: discord.Embed, view: discord.ui.View | None = None, ephemeral: bool = False):
    if interaction.type is discord.InteractionType.component:
        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed_obj, view=view)
        else:
            await interaction.response.edit_message(embed=embed_obj, view=view)
        return

    await interaction.response.send_message(embed=embed_obj, view=view, ephemeral=ephemeral)


async def send_text(interaction: discord.Interaction, text: str, ephemeral: bool = False):
    if interaction.response.is_done():
        await interaction.followup.send(text, ephemeral=ephemeral)
    else:
        await interaction.response.send_message(text, ephemeral=ephemeral)


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


class ItemActionButton(discord.ui.Button):
    def __init__(self, cmd: str, item_id: int, row: int):
        super().__init__(label=cmd.title(), custom_id=f"{cmd}/{item_id}", row=row)
        self.cmd = cmd
        self.item_id = item_id

    async def callback(self, interaction: discord.Interaction):
        await run_component_action(interaction, self.cmd, str(self.item_id))


class ItemView(discord.ui.View):
    def __init__(self, item_id: int):
        super().__init__(timeout=600)
        buttons = ["item", "get", "preconditions", "package", "skills", "earn", "drop", "unpack", "reward", "buy"]
        for i, cmd in enumerate(buttons):
            self.add_item(ItemActionButton(cmd, item_id, row=0 if i < 5 else 1))


class PagedListView(discord.ui.View):
    def __init__(self, title: str, lines: list[str], page_size: int = 10):
        super().__init__(timeout=600)
        self.title = title
        self.lines = lines or ["No data."]
        self.page_size = page_size
        self.page = 0

    @property
    def page_count(self) -> int:
        return max(1, (len(self.lines) + self.page_size - 1) // self.page_size)

    def make_embed(self) -> discord.Embed:
        start = self.page * self.page_size
        end = start + self.page_size
        chunk = self.lines[start:end]
        e = embed(f"{self.title} ({self.page + 1}/{self.page_count})")
        e.description = "\n".join(chunk) if chunk else "No data."
        return e

    @discord.ui.button(label="Previous Page", style=discord.ButtonStyle.secondary, row=4)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="Next Page", style=discord.ButtonStyle.secondary, row=4)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < self.page_count - 1:
            self.page += 1
        await interaction.response.edit_message(embed=self.make_embed(), view=self)


class LUBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

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


async def run_component_action(interaction: discord.Interaction, cmd: str, value: str):
    handlers: dict[str, app_commands.Command] = {
        "item": item,
        "get": get,
        "preconditions": preconditions,
        "package": package,
        "skills": skills,
        "earn": earn,
        "drop": drop,
        "unpack": unpack,
        "reward": reward,
        "buy": buy,
    }
    handler = handlers.get(cmd)
    if not handler:
        await send_text(interaction, f"Unknown component action: {cmd}", ephemeral=True)
        return

    # app_commands decorators turn these into Command objects; invoke underlying callback.
    await handler.callback(interaction, value)


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
        await send_text(interaction, "Item not found.", ephemeral=True)
        return
    obj_name = locale.get_object_name(item_id)
    e = embed(f"{obj_name} [{item_id}]")
    e.url = f"{settings.explorer_domain}/objects/{item_id}"
    comp = cdclient.get_item_component(item_id)
    if comp:
        e.add_field(name="Rarity", value=str(row_value(comp, "rarity", default="Unknown")))
        e.add_field(name="Stack Size", value=str(row_value(comp, "stack_size", "stackSize", default="Unknown")))
        e.add_field(name="Price", value=str(row_value(comp, "baseValue", "basevalue", "currencyLOT", default="Unknown")))
    await send_embed(interaction, e, view=ItemView(item_id))


@app_commands.command(description="View how to get an item!")
@app_commands.autocomplete(item=object_autocomplete)
async def get(interaction: discord.Interaction, item: str):
    item_id = cdclient.get_item_id(item) or parse_id(item)
    if not item_id:
        await send_text(interaction, "Item not found.", ephemeral=True)
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
    await send_embed(interaction, e, view=ItemView(item_id))


@app_commands.command(description="View all smashables that drop an item!")
@app_commands.autocomplete(item=object_autocomplete)
async def drop(interaction: discord.Interaction, item: str):
    await send_embed(interaction, embed("Drop", f"Use LU Explorer link: {settings.explorer_domain}/objects/{item}"))


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
    lines = [f"{locale.get_mission_name(r['id'])} [{r['id']}]" for r in rows]
    view = PagedListView("Earn", lines)
    await send_embed(interaction, view.make_embed(), view=view)


@app_commands.command(description="View all vendors that sell an item!")
@app_commands.autocomplete(item=object_autocomplete)
async def buy(interaction: discord.Interaction, item: str):
    await send_embed(interaction, embed("Buy", "Vendor query available from local CDClient data."))


@app_commands.command(description="View all activities that drop an item!")
@app_commands.autocomplete(item=object_autocomplete)
async def reward(interaction: discord.Interaction, item: str):
    await send_embed(interaction, embed("Reward", "Activity reward output available from local CDClient data."))


@app_commands.command(description="View all packages that drop an item!")
@app_commands.autocomplete(package=object_autocomplete)
async def unpack(interaction: discord.Interaction, package: str):
    await send_embed(interaction, embed("Unpack", f"Package query for {package}."))


@app_commands.command(description="View all items given from a package!")
@app_commands.autocomplete(package=object_autocomplete)
async def package(interaction: discord.Interaction, package: str):
    await send_embed(interaction, embed("Package", f"Package content query for {package}."))


@app_commands.command(description="View all missions from an NPC!")
@app_commands.autocomplete(npc=object_autocomplete)
async def npc(interaction: discord.Interaction, npc: str):
    await send_embed(interaction, embed("NPC", f"Mission-giver query for {npc}."))


@app_commands.command(description="View all items sold from a vendor!")
@app_commands.autocomplete(vendor=object_autocomplete)
async def vendor(interaction: discord.Interaction, vendor: str):
    await send_embed(interaction, embed("Vendor", f"Vendor listing for {vendor}."))


@app_commands.command(description="View the stats of an enemy!")
@app_commands.autocomplete(enemy=object_autocomplete)
async def enemy(interaction: discord.Interaction, enemy: str):
    enemy_id = parse_id(enemy) or cdclient.get_object_id(enemy)
    if not enemy_id:
        await send_text(interaction, "Enemy not found.", ephemeral=True)
        return
    e = embed(f"{locale.get_object_name(enemy_id)} [{enemy_id}]")
    e.url = f"{settings.explorer_domain}/objects/{enemy_id}"
    await send_embed(interaction, e)


@app_commands.command(description="View all enemys given from a package!")
@app_commands.autocomplete(enemy=object_autocomplete)
async def smash(interaction: discord.Interaction, enemy: str):
    await send_embed(interaction, embed("Smash", f"Smash-drop query for {enemy}."))


@app_commands.command(description="View the stats of a mission!")
@app_commands.autocomplete(mission=mission_autocomplete)
async def mission(interaction: discord.Interaction, mission: str):
    mission_id = parse_id(mission)
    if not mission_id:
        await send_text(interaction, "Mission not found.", ephemeral=True)
        return
    row = cdclient.get_mission(mission_id)
    if not row:
        await send_text(interaction, "Mission not found.", ephemeral=True)
        return
    e = embed(f"{locale.get_mission_name(mission_id)} [{mission_id}]")
    e.description = locale.get_mission_description(mission_id)
    await send_embed(interaction, e)


@app_commands.command(description="View the stats of an achievement!")
@app_commands.autocomplete(achievement=mission_autocomplete)
async def achievement(interaction: discord.Interaction, achievement: str):
    mission_id = parse_id(achievement)
    if not mission_id:
        await send_text(interaction, "Achievement not found.", ephemeral=True)
        return
    row = cdclient.get_mission(mission_id)
    if not row:
        await send_text(interaction, "Achievement not found.", ephemeral=True)
        return
    e = embed(f"{locale.get_mission_name(mission_id)} [{mission_id}]")
    e.description = locale.get_mission_description(mission_id)
    await send_embed(interaction, e)


@app_commands.command(description="View all rewards given from an activity!")
@app_commands.autocomplete(activity=activity_autocomplete)
async def activity(interaction: discord.Interaction, activity: str):
    await send_embed(interaction, embed("Activity", f"Activity rewards for {activity}."))


@app_commands.command(description="View the stats of a brick!")
@app_commands.autocomplete(brick=object_autocomplete)
async def brick(interaction: discord.Interaction, brick: str):
    await send_embed(interaction, embed("Brick", f"Brick details for {brick}."))


@app_commands.command(description="View all skills attached to an item!")
@app_commands.autocomplete(item=object_autocomplete)
async def skills(interaction: discord.Interaction, item: str):
    item_id = parse_id(item) or cdclient.get_object_id(item)
    if not item_id:
        await send_text(interaction, "Item not found.", ephemeral=True)
        return
    rows = cdclient._q("SELECT skillID FROM ObjectSkills WHERE objectTemplate=? LIMIT 50", (item_id,)).fetchall()
    lines = [f"{locale.get_skill_name(r['skillID'])} [{r['skillID']}]" for r in rows]
    view = PagedListView("Skills", lines)
    await send_embed(interaction, view.make_embed(), view=view)


@app_commands.command(description="View the stats of a skill!")
@app_commands.autocomplete(skill=skill_autocomplete)
async def skill(interaction: discord.Interaction, skill: str):
    sid = parse_id(skill)
    if not sid:
        await send_text(interaction, "Skill not found.", ephemeral=True)
        return
    row = cdclient.get_skill_behavior(sid)
    e = embed(f"{locale.get_skill_name(sid)} [{sid}]")
    if row:
        e.add_field(name="Cooldown Group", value=str(row_value(row, "cooldownGroup", "cooldown_group", default=0)))
    await send_embed(interaction, e)


@app_commands.command(description="View all items that have a skill!")
@app_commands.autocomplete(skill=skill_autocomplete)
async def skillitems(interaction: discord.Interaction, skill: str):
    sid = parse_id(skill)
    if not sid:
        await send_text(interaction, "Skill not found.", ephemeral=True)
        return
    rows = cdclient.get_items_with_skill(sid)
    lines = [f"{r['name']} [{r['id']}]" for r in rows]
    view = PagedListView("Skill Items", lines)
    await send_embed(interaction, view.make_embed(), view=view)


@app_commands.command(description="View the skills in a cooldowngroup!")
async def cooldowngroup(interaction: discord.Interaction, group: int):
    rows = cdclient._q("SELECT skillID FROM SkillBehavior WHERE cooldownGroup=? LIMIT 100", (group,)).fetchall()
    e = embed(f"Cooldown Group {group}")
    e.description = "\n".join([f"{locale.get_skill_name(r['skillID'])} [{r['skillID']}]" for r in rows]) or "No skills found."
    await send_embed(interaction, e)


@app_commands.command(description="View all items in a loot table!")
async def loottable(interaction: discord.Interaction, loottable: int):
    rows = cdclient.get_loot_table_items(loottable)
    lines = [f"{r['name'] or 'Unknown'} [{r['id']}] - {r['chance']}%" for r in rows]
    view = PagedListView(f"Loot Table {loottable}", lines)
    await send_embed(interaction, view.make_embed(), view=view)


@app_commands.command(description="View the preconditions to use an item!")
@app_commands.autocomplete(item=object_autocomplete)
async def preconditions(interaction: discord.Interaction, item: str):
    item_id = cdclient.get_item_id(item) or parse_id(item)
    if not item_id:
        await send_text(interaction, "Item not found.", ephemeral=True)
        return
    ids = cdclient.get_preconditions(item_id)
    e = embed(f"Preconditions for {locale.get_object_name(item_id)}")
    e.description = "\n".join([f"[{i}] {locale.get_precondition(i)}" for i in ids]) or "None"
    await send_embed(interaction, e)


@app_commands.command(description="View stats about a level in LEGO Universe!")
async def level(interaction: discord.Interaction, level: int):
    rows = cdclient.get_level_rows(level)
    e = embed(f"Level {level}")
    e.description = "\n".join([", ".join([f"{k}={r[k]}" for k in r.keys()]) for r in rows])[:3900] or "No data."
    await send_embed(interaction, e)


@app_commands.command(description="Reload the data from the cdclient.sqlite and locale.xml!")
async def reload(interaction: discord.Interaction):
    cdclient.reload()
    await send_embed(interaction, embed("Reload", "Reload complete."), ephemeral=True)


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
