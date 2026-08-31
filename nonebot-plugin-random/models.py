from __future__ import annotations

import re
from typing import Any, Dict, List, Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictStr,
    field_validator,
    model_validator,
)


DrawOutput = Literal["text", "image", "record", "video"]
DrawMode = Literal["direct", "indirect"]
MessageType = Literal["command", "keyword", "regex"]
SwitchSource = Literal[
    "group_enabled",
    "group_disabled",
    "global_disabled",
    "default",
]


class RandomPoolConfig(BaseModel):
    """A validated resource-pool configuration."""

    model_config = ConfigDict(extra="forbid")

    pool_id: StrictStr
    display_name: StrictStr = ""
    draw_output: DrawOutput = "image"
    draw_mode: DrawMode = "direct"
    cooldown_seconds: int = Field(default=10, ge=0, strict=True)
    message_type: MessageType = "command"
    message: List[StrictStr] = Field(default_factory=list)
    insert_message: List[StrictStr] = Field(default_factory=list)
    delete_message: List[StrictStr] = Field(default_factory=list)
    modify_admin_only: StrictBool = True
    is_tome: StrictBool = False
    output_prefix: StrictStr = ""
    output_suffix: StrictStr = ""
    is_at_sender: StrictBool = False

    @field_validator("pool_id")
    @classmethod
    def validate_pool_id(cls, value: str) -> str:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,31}", value):
            raise ValueError("资源池 ID 仅允许小写字母、数字、_、-，且长度为 1～32")
        return value

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) > 30:
            raise ValueError("展示名称不能超过 30 个字符")
        return value

    @field_validator("message", "insert_message", "delete_message")
    @classmethod
    def validate_message_list(cls, value: List[str]) -> List[str]:
        result = [item.strip() for item in value]
        if any(not item for item in result):
            raise ValueError("命令列表不能包含空字符串")
        if len(result) != len(set(result)):
            raise ValueError("命令列表不能包含重复项")
        return result

    @model_validator(mode="after")
    def fill_and_validate_defaults(self) -> "RandomPoolConfig":
        if not self.display_name:
            self.display_name = self.pool_id
        if not self.message:
            self.message = [f"随机{self.pool_id}"]
        if self.message_type == "regex":
            if len(self.message) < 2:
                raise ValueError("正则模式的 message 至少需要表达式和展示文本两项")
            try:
                re.compile(self.message[0])
            except re.error as error:
                raise ValueError(f"正则表达式无效：{error}") from error
        if self.draw_output == "image":
            default_modify_messages = self.message
            if self.message_type == "regex":
                default_modify_messages = [self.message[1]]
            if not self.insert_message:
                self.insert_message = [
                    f"添加{item}" for item in default_modify_messages
                ]
            if not self.delete_message:
                self.delete_message = [
                    f"删除{item}" for item in default_modify_messages
                ]
        else:
            self.insert_message = []
            self.delete_message = []
        return self

    @classmethod
    def from_dict(
        cls,
        pool_id: str,
        raw_config: Dict[str, Any],
    ) -> "RandomPoolConfig":
        return cls.model_validate({"pool_id": pool_id, **raw_config})

    def to_config_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude={"pool_id"})

    @property
    def help_text(self) -> str:
        if self.message_type == "command":
            prefix = "@我 + " if self.is_tome else ""
            return prefix + "/".join(self.message)
        if self.message_type == "keyword":
            suffix = " 并@我" if self.is_tome else ""
            return f"关键词含有{'/'.join(self.message)}{suffix}"
        prefix = "@我 + " if self.is_tome else ""
        return prefix + self.message[1]


class PoolView(BaseModel):
    pool_id: str
    display_name: str
    draw_output: DrawOutput
    draw_mode: DrawMode
    cooldown_seconds: int
    command: str
    file_count: Optional[int] = None
    enabled: bool = True
    switch_source: SwitchSource = "default"
    global_disabled: bool = False

    @property
    def status_text(self) -> str:
        if self.switch_source == "group_enabled":
            if self.global_disabled:
                return "群内开启（覆盖全局）"
            return "群内已开启"
        if self.switch_source == "group_disabled":
            return "群内已关闭"
        if self.switch_source == "global_disabled":
            return "全局默认关闭"
        return "默认开启"

    @property
    def status_tone(self) -> str:
        if self.switch_source == "group_enabled":
            return "override"
        if not self.enabled:
            return "disabled"
        return "default"

    @property
    def output_text(self) -> str:
        return {
            "text": "文本",
            "image": "图片",
            "record": "语音",
            "video": "视频",
        }[self.draw_output]

    @property
    def mode_text(self) -> str:
        return {"direct": "直接", "indirect": "分层"}[self.draw_mode]
