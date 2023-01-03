from nonebot.rule import Rule
from nonebot.permission import SUPERUSER, Permission
from nonebot.adapters.onebot.v11.permission import (
    GROUP_ADMIN,
    GROUP_OWNER,
)
from nonebot.adapters.onebot.v11 import MessageEvent

def check_tome(is_tome: bool) -> Rule:
    def checker(event: MessageEvent) -> bool:
        if not is_tome:
            return True
        return event.is_tome()

    return Rule(checker)

def check_modify(modify_admin_only: bool) -> Permission:
    if modify_admin_only:
        return GROUP_OWNER | GROUP_ADMIN | SUPERUSER
    
    def permission() -> bool:
        return True

    return Permission(permission)