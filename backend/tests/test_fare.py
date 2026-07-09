from app.services.fare import ROUND_UNIT, estimate_fare, split_fare
from app.services.geo import haversine_km


def test_haversine_known_distance():
    # 전남대 정문 → 광주송정역 직선거리 약 11km
    d = haversine_km(35.1760, 126.9059, 35.1372, 126.7935)
    assert 9.5 < d < 12.0


def test_estimate_fare_base():
    assert estimate_fare(1.0) == 4800
    assert estimate_fare(2.0) == 4800


def test_estimate_fare_distance():
    fare = estimate_fare(15.6)  # 전남대→송정역 실도로 근사
    assert 15000 < fare < 17500
    assert fare % ROUND_UNIT == 0


def test_split_fare_preserves_total():
    total = 17300
    shares = split_fare(total, [12.0, 11.5, 13.1])
    assert sum(shares) == total
    assert all(s % ROUND_UNIT == 0 for s in shares)


def test_split_fare_proportional():
    shares = split_fare(10000, [3.0, 1.0])
    assert shares[0] > shares[1]
    assert sum(shares) == 10000


def test_split_fare_equal_weights():
    shares = split_fare(10000, [5.0, 5.0])
    assert shares == [5000, 5000]
