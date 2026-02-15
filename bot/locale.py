from __future__ import annotations

import re
from pathlib import Path

LOCALE_KEYS = [
    "Activities_ID_ActivityName",
    "Missions_ID_name",
    "MissionText_ID_description",
    "MissionText_ID_in_progress",
    "MissionText_ID_completion_succeed_tip",
    "Objects_ID_name",
    "Objects_ID_description",
    "Preconditions_ID_FailureReason",
    "SkillBehavior_ID_name",
    "SkillBehavior_ID_descriptionUI",
]


class LocaleXML:
    def __init__(self, locale_path: str):
        self.locale_path = Path(locale_path)
        self.locale: dict[str, dict[str, str]] = {}

    def load(self) -> None:
        text = self.locale_path.read_text(encoding="utf-8", errors="ignore")
        self.locale.clear()
        for name in LOCALE_KEYS:
            key = name.replace("ID", r"(?P<num>\d+)")
            pattern = re.compile(fr'id="{key}">[^"]+"en_US">(?P<content>[^<]+)', re.I)
            data: dict[str, str] = {}
            for m in pattern.finditer(text):
                content = m.group("content")
                content = re.sub(r"\&lt;([^&]+(&apos;)?)+\&gt;", "", content)
                content = content.replace("&apos;", "'")
                data[m.group("num")] = content
            self.locale[name] = data

    def get(self, table: str, obj_id: int, fallback: str = "") -> str:
        return self.locale.get(table, {}).get(str(obj_id), fallback)

    def get_object_name(self, obj_id: int) -> str:
        return self.get("Objects_ID_name", obj_id, f"Object_{obj_id}")

    def get_mission_name(self, mission_id: int) -> str:
        return self.get("Missions_ID_name", mission_id, f"Mission_{mission_id}")

    def get_mission_description(self, mission_id: int) -> str:
        return (
            self.get("MissionText_ID_description", mission_id)
            or self.get("MissionText_ID_in_progress", mission_id)
            or self.get("MissionText_ID_completion_succeed_tip", mission_id)
            or "No mission description available."
        )

    def get_skill_name(self, skill_id: int) -> str:
        return self.get("SkillBehavior_ID_name", skill_id, f"Skill_{skill_id}")

    def get_precondition(self, precondition_id: int) -> str:
        return self.get("Preconditions_ID_FailureReason", precondition_id, "Unknown precondition")

    def search(self, table: str, query: str, limit: int = 25) -> list[tuple[str, str]]:
        re_query = re.compile(re.escape(query), re.I)
        out: list[tuple[str, str]] = []
        for obj_id, name in self.locale.get(table, {}).items():
            if re_query.search(name):
                out.append((f"{name} [{obj_id}]", obj_id))
                if len(out) >= limit:
                    break
        return out


    def search_objects(self, query: str, limit: int = 25) -> list[tuple[str, str]]:
        return self.search("Objects_ID_name", query, limit)

    def search_missions(self, query: str, limit: int = 25) -> list[tuple[str, str]]:
        return self.search("Missions_ID_name", query, limit)

    def search_skills(self, query: str, limit: int = 25) -> list[tuple[str, str]]:
        return self.search("SkillBehavior_ID_name", query, limit)

    def search_activities(self, query: str, limit: int = 25) -> list[tuple[str, str]]:
        return self.search("Activities_ID_ActivityName", query, limit)
