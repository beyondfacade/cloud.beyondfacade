from apps.chat.app.errors import ChatRoomForbidden, ChatRoomNotFound
from apps.chat.domain.value_objects.chat_room import ChatMember, ChatRoom, parse_room


def admitted_room(member: ChatMember, key: str) -> ChatRoom:
    try:
        room = parse_room(key)
    except ValueError:
        raise ChatRoomNotFound("없는 채팅방입니다.") from None
    if not room.admits(member):
        raise ChatRoomForbidden("들어갈 수 없는 채팅방입니다.")
    return room
