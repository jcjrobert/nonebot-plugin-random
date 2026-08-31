from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

from .models import SwitchSource

SwitchData = Dict[str, Any]


@dataclass(frozen=True)
class FeatureSwitchState:
    enabled: bool
    source: SwitchSource
    global_disabled: bool


class GroupFeatureSwitchStore:
    """Store global defaults and explicit per-group feature overrides."""

    VERSION = 2

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or Path("data") / "random" / "group_switches.json"
        self._data: Optional[SwitchData] = None
        self._lock = asyncio.Lock()

    async def is_enabled(self, namespace: str, group_id: str, feature_id: str) -> bool:
        states = await self.get_states(namespace, group_id, [feature_id])
        return states[feature_id].enabled

    async def get_states(
        self,
        namespace: str,
        group_id: str,
        feature_ids: Iterable[str],
    ) -> Dict[str, FeatureSwitchState]:
        async with self._lock:
            data = await self._load_unlocked()
            namespace_data = self._get_namespace(data, namespace)
            global_disabled = set(namespace_data["global_disabled"])
            group_data = namespace_data["groups"].get(
                group_id,
                {"enabled": [], "disabled": []},
            )
            group_enabled = set(group_data["enabled"])
            group_disabled = set(group_data["disabled"])
            return {
                feature_id: self._resolve_state(
                    feature_id,
                    global_disabled,
                    group_enabled,
                    group_disabled,
                )
                for feature_id in feature_ids
            }

    async def set_enabled(
        self,
        namespace: str,
        group_id: str,
        feature_id: str,
        enabled: bool,
    ) -> None:
        await self.set_many_enabled(
            namespace,
            group_id,
            [feature_id],
            enabled,
        )

    async def set_many_enabled(
        self,
        namespace: str,
        group_id: str,
        feature_ids: Iterable[str],
        enabled: bool,
    ) -> None:
        feature_set = set(feature_ids)
        if not feature_set:
            return
        async with self._lock:
            data = await self._load_unlocked()
            namespace_data = self._get_namespace(data, namespace)
            group_data = namespace_data["groups"].setdefault(
                group_id,
                {"enabled": [], "disabled": []},
            )
            enabled_features = set(group_data["enabled"])
            disabled_features = set(group_data["disabled"])
            if enabled:
                enabled_features.update(feature_set)
                disabled_features.difference_update(feature_set)
            else:
                disabled_features.update(feature_set)
                enabled_features.difference_update(feature_set)
            group_data["enabled"] = sorted(enabled_features)
            group_data["disabled"] = sorted(disabled_features)
            self._clean(data)
            await self._save_unlocked(data)

    async def set_global_enabled(
        self,
        namespace: str,
        feature_ids: Iterable[str],
        enabled: bool,
    ) -> None:
        feature_set = set(feature_ids)
        if not feature_set:
            return
        async with self._lock:
            data = await self._load_unlocked()
            namespace_data = self._get_namespace(data, namespace)
            global_disabled = set(namespace_data["global_disabled"])
            if enabled:
                global_disabled.difference_update(feature_set)
            else:
                global_disabled.update(feature_set)
            namespace_data["global_disabled"] = sorted(global_disabled)
            self._clean(data)
            await self._save_unlocked(data)

    async def remove_feature(self, namespace: str, feature_id: str) -> None:
        async with self._lock:
            data = await self._load_unlocked()
            namespace_data = self._get_namespace(data, namespace)
            if feature_id in namespace_data["global_disabled"]:
                namespace_data["global_disabled"].remove(feature_id)
            for group_data in namespace_data["groups"].values():
                for key in ("enabled", "disabled"):
                    if feature_id in group_data[key]:
                        group_data[key].remove(feature_id)
            self._clean(data)
            await self._save_unlocked(data)

    async def reload(self) -> None:
        async with self._lock:
            self._data = None
            await self._load_unlocked()

    async def _load_unlocked(self) -> SwitchData:
        if self._data is None:
            self._data = await asyncio.to_thread(self._read_file)
        return self._data

    def _read_file(self) -> SwitchData:
        if not self.path.exists():
            return self._empty_data()
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("random 群开关配置必须是 JSON 对象")
        if raw.get("version") == self.VERSION:
            return self._normalize_current(raw)
        if "version" in raw:
            raise ValueError("random 群开关配置版本不受支持")
        return self._migrate_legacy(raw)

    async def _save_unlocked(self, data: SwitchData) -> None:
        await asyncio.to_thread(self._write_file, data)
        self._data = data

    def _write_file(self, data: SwitchData) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(data, ensure_ascii=False, indent=4),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def _normalize_current(self, raw: SwitchData) -> SwitchData:
        namespaces = raw.get("namespaces")
        if not isinstance(namespaces, dict):
            raise ValueError("random 群开关 namespaces 格式错误")
        result = self._empty_data()
        for namespace, namespace_data in namespaces.items():
            if not isinstance(namespace, str) or not isinstance(namespace_data, dict):
                raise ValueError("random 群开关命名空间格式错误")
            global_disabled = self._normalize_features(
                namespace_data.get("global_disabled", []),
                "全局默认禁用",
            )
            groups = namespace_data.get("groups", {})
            if not isinstance(groups, dict):
                raise ValueError("random 群开关 groups 格式错误")
            normalized_groups: Dict[str, Dict[str, List[str]]] = {}
            for group_id, group_data in groups.items():
                if not isinstance(group_id, str) or not isinstance(group_data, dict):
                    raise ValueError("random 群开关群配置格式错误")
                group_enabled = self._normalize_features(
                    group_data.get("enabled", []),
                    "群显式开启",
                )
                group_disabled = self._normalize_features(
                    group_data.get("disabled", []),
                    "群显式关闭",
                )
                if set(group_enabled) & set(group_disabled):
                    raise ValueError("random 群开关不能同时开启和关闭同一资源池")
                normalized_groups[group_id] = {
                    "enabled": group_enabled,
                    "disabled": group_disabled,
                }
            result["namespaces"][namespace] = {
                "global_disabled": global_disabled,
                "groups": normalized_groups,
            }
        self._clean(result)
        return result

    def _migrate_legacy(self, raw: SwitchData) -> SwitchData:
        result = self._empty_data()
        for namespace, groups in raw.items():
            if not isinstance(namespace, str) or not isinstance(groups, dict):
                raise ValueError("random 旧版群开关命名空间格式错误")
            normalized_groups: Dict[str, Dict[str, List[str]]] = {}
            for group_id, features in groups.items():
                if not isinstance(group_id, str):
                    raise ValueError("random 旧版群开关群号格式错误")
                normalized_groups[group_id] = {
                    "enabled": [],
                    "disabled": self._normalize_features(features, "群禁用"),
                }
            result["namespaces"][namespace] = {
                "global_disabled": [],
                "groups": normalized_groups,
            }
        self._clean(result)
        return result

    @staticmethod
    def _normalize_features(value: Any, label: str) -> List[str]:
        if not isinstance(value, list) or any(
            not isinstance(feature, str) for feature in value
        ):
            raise ValueError(f"random {label}资源池 ID 必须是字符串列表")
        return sorted(set(value))

    @staticmethod
    def _resolve_state(
        feature_id: str,
        global_disabled: Set[str],
        group_enabled: Set[str],
        group_disabled: Set[str],
    ) -> FeatureSwitchState:
        is_global_disabled = feature_id in global_disabled
        if feature_id in group_enabled:
            return FeatureSwitchState(True, "group_enabled", is_global_disabled)
        if feature_id in group_disabled:
            return FeatureSwitchState(False, "group_disabled", is_global_disabled)
        if is_global_disabled:
            return FeatureSwitchState(False, "global_disabled", True)
        return FeatureSwitchState(True, "default", False)

    @staticmethod
    def _empty_data() -> SwitchData:
        return {"version": GroupFeatureSwitchStore.VERSION, "namespaces": {}}

    @staticmethod
    def _get_namespace(data: SwitchData, namespace: str) -> SwitchData:
        return data["namespaces"].setdefault(
            namespace,
            {"global_disabled": [], "groups": {}},
        )

    @staticmethod
    def _clean(data: SwitchData) -> None:
        namespaces = data["namespaces"]
        for namespace in list(namespaces):
            namespace_data = namespaces[namespace]
            groups = namespace_data["groups"]
            for group_id in list(groups):
                group_data = groups[group_id]
                if not group_data["enabled"] and not group_data["disabled"]:
                    groups.pop(group_id)
            if not namespace_data["global_disabled"] and not groups:
                namespaces.pop(namespace)


group_feature_switches = GroupFeatureSwitchStore()
