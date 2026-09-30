import ipaddress

from starlette.types import Scope


# ipaddress.is_private는 문서용 대역(203.0.113.0/24 등)까지 포함해 프록시 판정에 쓸 수 없다
_TRUSTED_PROXY_NETWORKS = tuple(
    ipaddress.ip_network(cidr)
    for cidr in ("127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "::1/128", "fc00::/7")
)


def _is_trusted_proxy(ip: str) -> bool:
    address = ipaddress.ip_address(ip)
    return any(address in network for network in _TRUSTED_PROXY_NETWORKS if network.version == address.version)


def _parse(value: str) -> str | None:
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        return None


def resolve_client_ip(peer: str | None, forwarded_for: str | None) -> str | None:
    """루프백·사설망 피어(Next 개발 프록시·도커 네트워크)만 프록시로 믿고, 그 프록시가 덧붙인
    X-Forwarded-For의 마지막 값을 쓴다. 앞쪽 값은 클라이언트가 위조할 수 있다."""
    peer_ip = _parse(peer) if peer else None
    if peer_ip and forwarded_for and _is_trusted_proxy(peer_ip):
        forwarded = _parse(forwarded_for.split(",")[-1])
        if forwarded:
            return forwarded
    return peer


def client_ip_from_scope(scope: Scope) -> str | None:
    client = scope.get("client")
    headers = dict(scope.get("headers") or [])
    forwarded = headers.get(b"x-forwarded-for")
    return resolve_client_ip(client[0] if client else None, forwarded.decode("latin-1") if forwarded else None)
