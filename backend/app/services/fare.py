"""광주 택시 요금 추정 및 분담(Split-fare) 계산.

실요금 연동 전까지 거리 기반 추정치를 사용한다.
분담액은 100원 단위로 내림 후, 잔액을 소수부가 큰 순서대로 100원씩 배분해
합계가 총액과 정확히 일치하도록 한다.
"""

BASE_FARE = 4800  # 기본요금 (첫 2km)
BASE_KM = 2.0
PER_KM = 850  # 2km 초과 km당 요금
ROUND_UNIT = 100


def estimate_fare(distance_km: float) -> int:
    extra_km = max(0.0, distance_km - BASE_KM)
    raw = BASE_FARE + extra_km * PER_KM
    return int(round(raw / ROUND_UNIT) * ROUND_UNIT)


def split_fare(total: int, weights: list[float]) -> list[int]:
    if not weights or total <= 0:
        return [0 for _ in weights]
    weight_sum = sum(weights)
    raw = [total * w / weight_sum for w in weights]
    shares = [int(x // ROUND_UNIT) * ROUND_UNIT for x in raw]
    remainder = total - sum(shares)
    # 소수부가 큰 순서로 100원씩 배분
    order = sorted(range(len(raw)), key=lambda i: raw[i] - shares[i], reverse=True)
    i = 0
    while remainder >= ROUND_UNIT:
        shares[order[i % len(order)]] += ROUND_UNIT
        remainder -= ROUND_UNIT
        i += 1
    return shares
