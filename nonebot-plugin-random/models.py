from pathlib import Path
from typing import List

DRAW_OUTPUT_TYPES = ["text", "image", "record"]
MESSAGE_TYPES = ["command", "keyword", "regex"]

def is_list_str(l):
    return isinstance(l, list) and sum([isinstance(i, str) for i in l])

class RandomDetailConfig:
    draw_output: str
    message_type: str
    message: List[str]
    is_tome: bool
    output_prefix: str
    output_suffix: str
    is_at_sender: bool

    def __init__(self, dir_name: str, config_dict: dict):
        self.draw_output = config_dict.get("draw_output")
        if self.draw_output not in DRAW_OUTPUT_TYPES:
            self.draw_output = "image"
        
        self.message_type = config_dict.get("message_type")
        if self.message_type not in MESSAGE_TYPES:
            self.message_type = "command"
        
        self.message = config_dict.get("message")
        if not is_list_str(self.message):
            self.message = [f"随机{dir_name}"]

        self.is_tome = bool(config_dict.get("is_tome"))

        self.output_prefix = config_dict.get("output_prefix")
        if not isinstance(self.output_prefix, str):
            self.output_prefix = ""

        self.output_suffix = config_dict.get("output_suffix")
        if not isinstance(self.output_suffix, str):
            self.output_suffix = ""

        self.is_at_sender = bool(config_dict.get("is_at_sender"))