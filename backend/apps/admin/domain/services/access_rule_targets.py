"""규칙 대상별 값 검증·일치 판정 (Strategy) — IP는 대역 포함, 디바이스는 같은 ID."""

import ipaddress
from abc import ABC, abstractmethod
from datetime import datetime

from apps.admin.domain.entities.access_rule_entity import AccessRule, RuleTarget
from apps.admin.domain.entities.client_entity import Client
from apps.admin.domain.services.device_id import is_device_id

_MIN_PREFIX = {4: 8, 6: 32}  # 이보다 넓은 대역은 사실상 전체 허용이라 받지 않는다


class RuleTargetStrategy(ABC):
    label: str

    @abstractmethod
    def normalize(self, value: str) -> str:
        """저장할 표준 형태. 받을 수 없는 값이면 ValueError."""

    @abstractmethod
    def matches(self, rule_value: str, client: Client) -> bool: ...


class IpTarget(RuleTargetStrategy):
    label = "IP"

    def normalize(self, value: str) -> str:
        try:
            network = ipaddress.ip_network(value.strip(), strict=False)
        except ValueError as error:
            raise ValueError(f"IP 주소나 대역(CIDR) 형식이 아닙니다: {value}") from error
        if network.prefixlen < _MIN_PREFIX[network.version]:
            raise ValueError(f"대역이 너무 넓습니다 — IPv4는 /{_MIN_PREFIX[4]}, IPv6는 /{_MIN_PREFIX[6]}보다 좁게 적어 주세요.")
        return str(network.network_address) if network.num_addresses == 1 else str(network)

    def matches(self, rule_value: str, client: Client) -> bool:
        if client.ip is None:
            return False
        try:
            address = ipaddress.ip_address(client.ip)
        except ValueError:
            return False
        network = ipaddress.ip_network(rule_value)
        return address.version == network.version and address in network


class DeviceTarget(RuleTargetStrategy):
    label = "디바이스"

    def normalize(self, value: str) -> str:
        device_id = value.strip()
        if not is_device_id(device_id):
            raise ValueError("디바이스 ID 형식이 아닙니다 — 이벤트 목록의 22자 ID를 그대로 붙여 넣으세요.")
        return device_id

    def matches(self, rule_value: str, client: Client) -> bool:
        return client.device_id == rule_value


TARGETS: dict[RuleTarget, RuleTargetStrategy] = {RuleTarget.IP: IpTarget(), RuleTarget.DEVICE: DeviceTarget()}


def matching_rule(rules: list[AccessRule], client: Client, now: datetime) -> AccessRule | None:
    return next(
        (rule for rule in rules if rule.is_active(now) and TARGETS[rule.target].matches(rule.value, client)), None
    )
