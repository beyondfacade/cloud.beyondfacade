"""글로벌 채팅 — 방·메시지·답장·삭제·1:1·읽음·실시간 스트림 API (실제 테스트 DB, 실시간 발행은 가짜)."""

import asyncio
import threading
import time
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

import apps.chat.adapter.inbound.api.v1.chat_message_router as chat_router
from apps.admin.dependencies.admin_dependencies import get_admin_user_use_case
from apps.chat.adapter.outbound.gateways.pg_listen_chat_feed import PgListenChatFeed
from apps.chat.adapter.outbound.gateways.pg_notify_chat_publisher import PgNotifyChatPublisher
from apps.chat.adapter.outbound.repositories.chat_message_repository import SqlAlchemyChatMessageRepository
from apps.chat.app.dtos.chat_message_dto import ChatEventDto
from apps.chat.app.ports.output.chat_message_port import ChatEventFeedPort, ChatEventPublisherPort, ChatSubscription
from apps.chat.dependencies.chat_dependencies import get_chat_event_feed, get_chat_event_publisher
from apps.chat.domain.entities.chat_message_entity import ChatMessage
from core.matrix.grid_oracle_database_manager import session_scope
from main import app

PASSWORD = "correct-horse-battery"
IPS = {"ops": "198.51.100.40", "viewer": "198.51.100.41", "guest2": "198.51.100.42"}


class _FakeSubscription(ChatSubscription):
    def __init__(self, feed: "_FakeFeed") -> None:
        self._feed = feed
        self._position = len(feed.events)

    async def next(self, timeout: float) -> ChatEventDto | None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._position < len(self._feed.events):
                self._position += 1
                return self._feed.events[self._position - 1]
            await asyncio.sleep(0.01)
        return None

    def close(self) -> None:
        self._feed.closed += 1


class _FakeFeed(ChatEventFeedPort, ChatEventPublisherPort):
    """발행한 이벤트를 목록에 쌓고, 구독은 구독한 뒤의 이벤트만 받는다 (스레드 사이 공유)."""

    def __init__(self) -> None:
        self.events: list[ChatEventDto] = []
        self.closed = 0

    def publish(self, event: ChatEventDto) -> None:
        self.events.append(event)

    def subscribe(self) -> ChatSubscription:
        return _FakeSubscription(self)


@pytest.fixture(autouse=True)
def feed():
    with session_scope() as session:
        session.execute(
            text(
                "truncate chat_read, chat_message, access_event, ip_block, admin_session, admin_audit, admin_user "
                "restart identity cascade"
            )
        )
    use_case = get_admin_user_use_case()
    use_case.upsert("ops", PASSWORD, "operator")  # id 1
    use_case.upsert("viewer", PASSWORD, "viewer")  # id 2
    use_case.upsert("guest2", PASSWORD, "viewer")  # id 3
    fake = _FakeFeed()
    app.dependency_overrides[get_chat_event_publisher] = lambda: fake
    app.dependency_overrides[get_chat_event_feed] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_chat_event_publisher, None)
    app.dependency_overrides.pop(get_chat_event_feed, None)


def _client(username: str) -> TestClient:
    client = TestClient(app, client=(IPS[username], 50000))
    assert client.post("/admin/auth/login", json={"username": username, "password": PASSWORD}).status_code == 200
    return client


def _send(client: TestClient, room: str, body: str, reply_to_id: int | None = None):
    return client.post(f"/chat/rooms/{room}/messages", json={"body": body, "reply_to_id": reply_to_id})


def _insert(room: str, count: int, prefix: str = "메시지") -> None:
    repository = SqlAlchemyChatMessageRepository()
    for index in range(count):
        repository.add(
            ChatMessage(
                room=room, sender_id=1, sender_username="ops", sender_role="operator", body=f"{prefix} {index}",
                created_at=datetime(2026, 10, 1, tzinfo=UTC),
            )
        )


def test_myself_배선이_200을_반환한다():
    assert TestClient(app).get("/chat/myself").json()["sender_username"] == "myself"
    assert TestClient(app).get("/chat/reads/myself").json() == {"room": "global", "last_read_id": 0}


def test_채팅은_로그인이_필요하다():
    guest = TestClient(app)
    assert guest.get("/chat/rooms").status_code == 401
    assert guest.get("/chat/rooms/global/messages").status_code == 401
    assert _send(guest, "global", "안녕").json()["error"]["code"] == "UNAUTHENTICATED"
    assert guest.get("/chat/stream").status_code == 401


def test_일반_회원은_전체방만_관리자는_관리자방도_본다():
    assert [room["key"] for room in _client("viewer").get("/chat/rooms").json()] == ["global"]
    rooms = _client("ops").get("/chat/rooms").json()
    assert [(room["key"], room["title"]) for room in rooms] == [("global", "전체"), ("operators", "관리자")]


def test_전체방에_보내면_보낸_사람_이름과_등급이_남는다():
    viewer = _client("viewer")
    sent = _send(viewer, "global", "  안녕하세요  ")
    assert sent.status_code == 201
    assert sent.json()["body"] == "안녕하세요"
    page = _client("ops").get("/chat/rooms/global/messages").json()
    assert [(m["sender_username"], m["sender_role"], m["body"]) for m in page["items"]] == [
        ("viewer", "viewer", "안녕하세요")
    ]
    assert page["has_more"] is False


def test_일반_회원은_관리자방에_들어갈_수_없고_없는_방은_404다():
    viewer = _client("viewer")
    assert viewer.get("/chat/rooms/operators/messages").json()["error"]["code"] == "CHAT_ROOM_FORBIDDEN"
    assert _send(viewer, "operators", "몰래").status_code == 403
    assert viewer.get("/chat/rooms/lobby/messages").status_code == 404
    assert _send(_client("ops"), "operators", "관리자끼리").status_code == 201


def test_빈_메시지와_500자_초과는_거절한다():
    viewer = _client("viewer")
    assert _send(viewer, "global", "   ").json()["error"]["code"] == "INVALID_CHAT_MESSAGE"
    assert _send(viewer, "global", "가" * 501).status_code == 400
    assert _send(viewer, "global", "가" * 500).status_code == 201


def test_10초에_5개를_넘기면_잠시_막는다():
    viewer = _client("viewer")
    for index in range(5):
        assert _send(viewer, "global", f"도배 {index}").status_code == 201
    too_fast = _send(viewer, "global", "여섯 번째")
    assert too_fast.status_code == 429
    assert too_fast.json()["error"]["code"] == "CHAT_TOO_FAST"


def test_답장은_원문_첫_줄을_미리보기로_담고_다른_방_메시지에는_못_한다():
    ops = _client("ops")
    original = _send(ops, "global", "첫 줄\n둘째 줄").json()
    reply = _send(_client("viewer"), "global", "답장입니다", original["id"]).json()
    assert reply["reply_to"] == {"id": original["id"], "sender_username": "ops", "preview": "첫 줄", "deleted": False}
    secret = _send(ops, "operators", "관리자방 글").json()
    assert _send(ops, "global", "엉뚱한 답장", secret["id"]).json()["error"]["code"] == "CHAT_MESSAGE_NOT_FOUND"


def test_삭제는_관리자만_하고_본문은_지워진_채_자리만_남는다(feed):
    viewer = _client("viewer")
    original = _send(viewer, "global", "지울 글").json()
    _send(viewer, "global", "그 글에 답장", original["id"])
    assert viewer.delete(f"/chat/messages/{original['id']}").json()["error"]["code"] == "FORBIDDEN_ROLE"
    ops = _client("ops")
    assert ops.delete(f"/chat/messages/{original['id']}").status_code == 204
    assert ops.delete(f"/chat/messages/{original['id']}").status_code == 204
    items = ops.get("/chat/rooms/global/messages").json()["items"]
    assert (items[0]["body"], items[0]["deleted"]) == (None, True)
    assert items[1]["reply_to"]["preview"] is None
    assert items[1]["reply_to"]["deleted"] is True
    assert [(e.type, e.message_id) for e in feed.events if e.type == "deleted"] == [("deleted", original["id"])]
    assert ops.delete("/chat/messages/9999").status_code == 404


def test_일반_회원은_전문가를_찾아_1대1_대화를_열고_전문가는_그_방에서_답한다():
    get_admin_user_use_case().set_role("guest2", "expert")
    viewer = _client("viewer")
    assert viewer.get("/chat/members", params={"q": "e"}).json() == [{"id": 3, "username": "guest2"}]  # 관리자 ops는 안 나온다
    assert viewer.get("/chat/members", params={"q": " "}).json() == []
    room = viewer.post("/chat/direct", json={"user_id": 3}).json()
    assert (room["key"], room["kind"], room["title"], room["partner_id"]) == ("dm:2:3", "direct", "guest2", 3)
    assert [r["key"] for r in viewer.get("/chat/rooms").json()] == ["global"]  # 메시지가 오가기 전엔 목록에 없다
    assert _send(viewer, "dm:2:3", "안녕하세요 전문가님").status_code == 201
    expert = _client("guest2")
    expert_rooms = {r["key"]: r for r in expert.get("/chat/rooms").json()}
    assert (expert_rooms["dm:2:3"]["title"], expert_rooms["dm:2:3"]["unread"]) == ("viewer", 1)
    assert _send(expert, "dm:2:3", "네 말씀하세요").status_code == 201
    ops = _client("ops")
    assert ops.get("/chat/rooms/dm:2:3/messages").status_code == 403
    assert "dm:2:3" not in [r["key"] for r in ops.get("/chat/rooms").json()]


def test_1대1은_일반_회원이_전문가에게만_걸고_다른_조합은_보낼_수도_없다():
    get_admin_user_use_case().set_role("guest2", "expert")
    viewer, expert, ops = _client("viewer"), _client("guest2"), _client("ops")
    forbidden = viewer.post("/chat/direct", json={"user_id": 1})  # 일반 → 관리자
    assert (forbidden.status_code, forbidden.json()["error"]["code"]) == (403, "CHAT_ROOM_FORBIDDEN")
    assert expert.post("/chat/direct", json={"user_id": 2}).status_code == 403  # 전문가가 먼저 걸 수는 없다
    assert ops.post("/chat/direct", json={"user_id": 3}).status_code == 403
    assert expert.get("/chat/members", params={"q": "v"}).json() == []
    assert ops.get("/chat/members", params={"q": "e"}).json() == []
    _insert("dm:1:2", 1)  # 규칙 전에 열린 일반↔관리자 방
    assert _send(viewer, "dm:1:2", "아직 되나요").status_code == 403


def test_나_자신이나_없는_회원과는_대화를_열_수_없다():
    viewer = _client("viewer")
    assert viewer.post("/chat/direct", json={"user_id": 2}).json()["error"]["code"] == "CHAT_MEMBER_NOT_FOUND"
    assert viewer.post("/chat/direct", json={"user_id": 999}).status_code == 404


def test_전문가와_연결하기는_활성_전문가와의_1대1_방을_연다():
    viewer = _client("viewer")
    response = viewer.post("/chat/expert")
    assert (response.status_code, response.json()["error"]["code"]) == (404, "CHAT_MEMBER_NOT_FOUND")
    get_admin_user_use_case().set_role("guest2", "expert")
    room = viewer.post("/chat/expert").json()
    assert (room["key"], room["kind"], room["title"], room["partner_id"]) == ("dm:2:3", "direct", "guest2", 3)


def test_안_읽은_개수는_남이_보낸_것만_세고_읽음_표시는_앞으로만_간다():
    viewer = _client("viewer")
    first = _send(viewer, "global", "하나").json()
    second = _send(viewer, "global", "둘").json()
    ops = _client("ops")
    _send(ops, "global", "내 글")
    unread = lambda client: {r["key"]: r["unread"] for r in client.get("/chat/rooms").json()}["global"]  # noqa: E731
    assert unread(ops) == 2
    assert unread(viewer) == 1
    assert ops.put("/chat/reads/global", json={"last_read_id": second["id"]}).json()["last_read_id"] == second["id"]
    assert unread(ops) == 0
    assert ops.put("/chat/reads/global", json={"last_read_id": first["id"]}).json()["last_read_id"] == second["id"]
    assert viewer.put("/chat/reads/operators", json={"last_read_id": 1}).status_code == 403


def test_메시지는_최신_50개씩_거꾸로_넘겨_본다():
    _insert("global", 55)
    ops = _client("ops")
    page = ops.get("/chat/rooms/global/messages").json()
    assert (len(page["items"]), page["has_more"]) == (50, True)
    assert page["items"][-1]["body"] == "메시지 54"
    older = ops.get("/chat/rooms/global/messages", params={"before_id": page["items"][0]["id"]}).json()
    assert ([m["body"] for m in older["items"]], older["has_more"]) == ([f"메시지 {i}" for i in range(5)], False)


def _read_stream(client: TestClient, headers: dict | None = None) -> str:
    with client.stream("GET", "/chat/stream", headers=headers or {}) as response:
        assert response.headers["content-type"].startswith("text/event-stream")
        return "".join(response.iter_text())


def test_스트림은_ready로_시작하고_볼_수_있는_방의_새_메시지만_보낸다(feed, monkeypatch):
    monkeypatch.setattr(chat_router, "STREAM_LIFETIME_SECONDS", 1.0)
    monkeypatch.setattr(chat_router, "PING_SECONDS", 0.3)
    viewer, ops = _client("viewer"), _client("ops")
    _insert("global", 1)

    def talk():
        time.sleep(0.3)
        _send(ops, "operators", "관리자 전용")
        _send(ops, "global", "모두 안녕")

    talker = threading.Thread(target=talk)
    talker.start()
    body = _read_stream(viewer)
    talker.join()
    assert body.startswith("retry: 3000\nid: 1\nevent: ready\n")
    assert "모두 안녕" in body
    assert "관리자 전용" not in body
    assert ": ping" in body
    assert feed.closed == 1


def test_다시_붙으면_Last_Event_ID_다음_메시지부터_따라잡는다(monkeypatch):
    monkeypatch.setattr(chat_router, "STREAM_LIFETIME_SECONDS", 0.2)
    _insert("global", 3)
    _insert("operators", 1, prefix="비밀")
    body = _read_stream(_client("viewer"), {"Last-Event-ID": "1"})
    assert body.index("메시지 1") < body.index("메시지 2") < body.index("event: ready")
    assert "id: 3\nevent: message" in body
    assert "id: 4\nevent: ready" in body
    assert "메시지 0" not in body
    assert "비밀" not in body


def test_NOTIFY로_발행하면_LISTEN_구독자가_받는다():
    event = ChatEventDto(type="deleted", room="global", message_id=42, message=None)

    async def roundtrip() -> ChatEventDto | None:
        from apps.chat.dependencies.chat_dependencies import get_chat_event_feed as real_feed

        dsn = real_feed.__wrapped__()._dsn
        listener = PgListenChatFeed(dsn)
        subscription = listener.subscribe()
        await asyncio.sleep(1.0)  # LISTEN 연결이 붙을 때까지
        await asyncio.to_thread(PgNotifyChatPublisher().publish, event)
        try:
            return await subscription.next(5.0)
        finally:
            subscription.close()
            listener._task.cancel()

    assert asyncio.run(roundtrip()) == event
