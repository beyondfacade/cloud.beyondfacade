"""채팅 도메인 — 방 종류별 입장 규칙, 메시지 본문·도배 규칙."""

from datetime import UTC, datetime, timedelta

import pytest

from apps.chat.domain.services.chat_policy import (
    MAX_BODY_LENGTH,
    RATE_LIMIT_COUNT,
    RATE_LIMIT_WINDOW,
    clean_body,
    rate_window_start,
    reply_preview,
)
from apps.chat.domain.value_objects.chat_room import (
    ChatMember,
    DirectRoom,
    direct_room,
    parse_room,
    rooms_for,
)

VIEWER = ChatMember(id=3, username="viewer", can_operate=False)
OPS = ChatMember(id=7, username="ops", can_operate=True)


def test_전체_방은_로그인한_회원_누구나_들어간다():
    room = parse_room("global")
    assert room.admits(VIEWER) and room.admits(OPS)
    assert room.title_for(VIEWER) == "전체"


def test_관리자_방은_관리자만_들어간다():
    room = parse_room("operators")
    assert room.admits(OPS)
    assert not room.admits(VIEWER)


def test_DM은_두_사람만_들어가고_방_이름은_작은_번호가_앞이다():
    room = direct_room(7, 3)
    assert room.key == "dm:3:7"
    assert parse_room("dm:3:7") == room
    assert room.admits(VIEWER) and room.admits(OPS)
    assert not room.admits(ChatMember(id=9, username="other", can_operate=True))
    assert room.partner_of(3) == 7


@pytest.mark.parametrize("key", ["", "lobby", "dm:3", "dm:7:3", "dm:3:3", "dm:a:b", "dm:0:3"])
def test_모르는_방_이름이나_잘못된_DM_이름은_거절한다(key):
    with pytest.raises(ValueError):
        parse_room(key)


def test_자기_자신과의_DM은_만들_수_없다():
    with pytest.raises(ValueError):
        direct_room(3, 3)


def test_고정_방_목록은_등급을_따른다():
    assert [room.key for room in rooms_for(VIEWER)] == ["global"]
    assert [room.key for room in rooms_for(OPS)] == ["global", "operators"]
    assert not any(isinstance(room, DirectRoom) for room in rooms_for(OPS))


def test_본문은_앞뒤_공백을_떼고_빈_글과_너무_긴_글은_거절한다():
    assert clean_body("  안녕하세요\n반가워요  ") == "안녕하세요\n반가워요"
    assert clean_body("가" * MAX_BODY_LENGTH) == "가" * MAX_BODY_LENGTH
    assert clean_body("   \n ") is None
    assert clean_body("가" * (MAX_BODY_LENGTH + 1)) is None


def test_도배_판정_창은_지금부터_정해진_시간_전이다():
    now = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
    assert rate_window_start(now) == now - RATE_LIMIT_WINDOW
    assert RATE_LIMIT_COUNT == 5 and RATE_LIMIT_WINDOW == timedelta(seconds=10)


def test_답장_미리보기는_첫_줄을_80자로_줄인다():
    assert reply_preview("첫 줄\n둘째 줄") == "첫 줄"
    assert reply_preview("가" * 100) == "가" * 80 + "…"
