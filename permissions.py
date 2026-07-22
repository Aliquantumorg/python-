from telegram.constants import ChatMemberStatus
from config import OWNER_IDS

GROUP_ADMIN_STATUSES = (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)


def is_owner(user_id: int) -> bool:
    """مالک بات هستی یا نه - این دسترسی مستقل از هر گروهیه"""
    return user_id in OWNER_IDS


async def is_group_admin(context, chat_id: int, user_id: int) -> bool:
    """توی همین گروه خاص، ادمین/سازنده هست یا نه"""
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in GROUP_ADMIN_STATUSES
    except Exception:
        return False


async def can_run_admin_command(update, context) -> bool:
    """
    قانون دسترسی دستورات مدیریتی (بن/کیک/میوت و...):
    - مالک بات (OWNER_IDS): همیشه مجازه، حتی اگه توی اون گروه ادمین نباشه.
    - بقیه: فقط اگه خودشون توی همون گروه خاص ادمین/سازنده باشن.
    """
    user_id = update.effective_user.id
    if is_owner(user_id):
        return True
    return await is_group_admin(context, update.effective_chat.id, user_id)
