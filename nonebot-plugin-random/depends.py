from nonebot.rule import Rule
from nonebot.adapters.onebot.v11 import MessageEvent

def check_tome(is_tome: bool) -> Rule:
    def checker(event: MessageEvent) -> bool:
        if not is_tome:
            return True
        return event.is_tome()

    return Rule(checker)