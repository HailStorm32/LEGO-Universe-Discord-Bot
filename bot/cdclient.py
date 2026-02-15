from __future__ import annotations

import sqlite3
from dataclasses import dataclass


from .locale import LocaleXML


def format_icon_path(icon: str | None) -> str | None:
    if not icon:
        return None
    icon = icon.replace("..\\..\\", "/lu-res/")
    icon = icon.replace("\\", "/")
    icon = icon.replace(" ", "%20")
    icon = icon.replace(".dds", ".png").replace(".DDS", ".png")
    return icon.lower()


@dataclass
class SearchRow:
    name: str
    value: str


class CDClient:
    def __init__(self, sqlite_path: str, locale: LocaleXML):
        self.sqlite_path = sqlite_path
        self.locale = locale
        self.db: sqlite3.Connection | None = None

    def connect(self) -> None:
        self.db = sqlite3.connect(self.sqlite_path)
        self.db.row_factory = sqlite3.Row

    def load(self) -> None:
        self.connect()
        self.locale.load()

    def reload(self) -> None:
        if self.db:
            self.db.close()
        self.load()

    def _q(self, sql: str, args: tuple = ()):
        assert self.db is not None
        return self.db.execute(sql, args)

    def get_object_id(self, name_or_id: str) -> int | None:
        if name_or_id.isdigit():
            return int(name_or_id)
        row = self._q(
            "SELECT id FROM Objects WHERE LOWER(name)=LOWER(?) OR LOWER(displayName)=LOWER(?) LIMIT 1",
            (name_or_id, name_or_id),
        ).fetchone()
        return int(row[0]) if row else None

    def get_item_id(self, value: str) -> int | None:
        obj_id = self.get_object_id(value)
        if not obj_id:
            return None
        row = self._q("SELECT 1 FROM ComponentsRegistry WHERE id=? AND component_type=11", (obj_id,)).fetchone()
        return obj_id if row else None

    def search_objects(self, query: str, component_type: int | None = None) -> list[SearchRow]:
        if component_type is None:
            rows = self._q("SELECT id, name FROM Objects WHERE name LIKE ? LIMIT 25", (f"%{query}%",)).fetchall()
        else:
            rows = self._q(
                """
                SELECT o.id, o.name FROM Objects o
                JOIN ComponentsRegistry c ON c.id=o.id
                WHERE c.component_type=? AND o.name LIKE ? LIMIT 25
                """,
                (component_type, f"%{query}%"),
            ).fetchall()
        return [SearchRow(f"{r['name']} [{r['id']}]", str(r["id"])) for r in rows]

    def get_components(self, object_id: int) -> list[sqlite3.Row]:
        return self._q("SELECT * FROM ComponentsRegistry WHERE id=?", (object_id,)).fetchall()

    def get_item_component(self, object_id: int) -> sqlite3.Row | None:
        row = self._q("SELECT component_id FROM ComponentsRegistry WHERE id=? and component_type=11", (object_id,)).fetchone()
        if not row:
            return None
        return self._q("SELECT * FROM ItemComponent WHERE id=?", (row["component_id"],)).fetchone()

    def get_mission(self, mission_id: int) -> sqlite3.Row | None:
        return self._q("SELECT * FROM Missions WHERE id=?", (mission_id,)).fetchone()

    def get_skill_behavior(self, skill_id: int) -> sqlite3.Row | None:
        return self._q("SELECT * FROM SkillBehavior WHERE skillID=? LIMIT 1", (skill_id,)).fetchone()

    def get_items_with_skill(self, skill_id: int):
        return self._q(
            """SELECT DISTINCT o.id, o.name FROM ObjectSkills s
            JOIN Objects o ON o.id=s.objectTemplate
            WHERE s.skillID=? LIMIT 100""",
            (skill_id,),
        ).fetchall()

    def get_preconditions(self, item_id: int) -> list[int]:
        row = self.get_item_component(item_id)
        if not row or not row["reqPrecondition"]:
            return []
        return [int(x) for x in str(row["reqPrecondition"]).split(",") if x.strip().isdigit()]

    def get_loot_table_items(self, loot_table_id: int):
        return self._q(
            """SELECT l.itemid as id, l.percent as chance, o.name as name
            FROM LootTable l LEFT JOIN Objects o ON o.id=l.itemid
            WHERE l.LootTableIndex=? ORDER BY l.percent DESC LIMIT 100""",
            (loot_table_id,),
        ).fetchall()

    def get_level_rows(self, level: int):
        return self._q("SELECT * FROM LevelProgressionLookup WHERE id=?", (level,)).fetchall()

    def get_render_icon_asset(self, object_id: int) -> str | None:
        row = self._q("SELECT component_id FROM ComponentsRegistry WHERE id=? AND component_type=2 LIMIT 1", (object_id,)).fetchone()
        if not row:
            return None
        render = self._q("SELECT icon_asset, IconID FROM RenderComponent WHERE id=? LIMIT 1", (row["component_id"],)).fetchone()
        if not render:
            return None
        asset = render["icon_asset"] if "icon_asset" in render.keys() else None
        if asset:
            return format_icon_path(asset)
        icon_id = render["IconID"] if "IconID" in render.keys() else None
        if icon_id:
            icon = self._q("SELECT IconPath FROM Icons WHERE IconID=? LIMIT 1", (icon_id,)).fetchone()
            if icon:
                return format_icon_path(icon["IconPath"])
        return None

    def get_destructible_component(self, object_id: int) -> sqlite3.Row | None:
        row = self._q("SELECT component_id FROM ComponentsRegistry WHERE id=? and component_type=7", (object_id,)).fetchone()
        if not row:
            return None
        return self._q("SELECT * FROM DestructibleComponent WHERE id=?", (row["component_id"],)).fetchone()

    def search_items(self, query: str) -> list[SearchRow]:
        return self.search_objects(query, component_type=11)

    def search_packages(self, query: str) -> list[SearchRow]:
        return self.search_objects(query, component_type=53)

    def search_vendors(self, query: str) -> list[SearchRow]:
        return self.search_objects(query, component_type=16)

    def search_npcs(self, query: str) -> list[SearchRow]:
        rows = self._q(
            """
            SELECT DISTINCT o.id, o.name FROM Objects o
            JOIN MissionNPCComponent m ON m.id=o.id
            WHERE o.name LIKE ? LIMIT 25
            """,
            (f"%{query}%",),
        ).fetchall()
        return [SearchRow(f"{r['name']} [{r['id']}]", str(r['id'])) for r in rows]

    def search_enemies(self, query: str) -> list[SearchRow]:
        rows = self._q(
            """
            SELECT DISTINCT o.id, o.name FROM Objects o
            JOIN ComponentsRegistry c ON c.id=o.id AND c.component_type=7
            JOIN DestructibleComponent d ON d.id=c.component_id
            WHERE d.isnpc=1 AND o.name LIKE ? LIMIT 25
            """,
            (f"%{query}%",),
        ).fetchall()
        return [SearchRow(f"{r['name']} [{r['id']}]", str(r['id'])) for r in rows]

    def search_smashables(self, query: str) -> list[SearchRow]:
        rows = self._q(
            """
            SELECT DISTINCT o.id, o.name FROM Objects o
            JOIN ComponentsRegistry c ON c.id=o.id AND c.component_type=7
            JOIN DestructibleComponent d ON d.id=c.component_id
            WHERE d.isSmashable=1 AND o.name LIKE ? LIMIT 25
            """,
            (f"%{query}%",),
        ).fetchall()
        return [SearchRow(f"{r['name']} [{r['id']}]", str(r['id'])) for r in rows]

    def search_bricks(self, query: str) -> list[SearchRow]:
        rows = self._q(
            """
            SELECT DISTINCT o.id, o.name FROM Objects o
            JOIN BrickIDTable b ON b.NDObjectID=o.id
            WHERE o.name LIKE ? LIMIT 25
            """,
            (f"%{query}%",),
        ).fetchall()
        return [SearchRow(f"{r['name']} [{r['id']}]", str(r['id'])) for r in rows]

