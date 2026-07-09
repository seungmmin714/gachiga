"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, getToken } from "@/lib/api";
import { PLACES } from "@/lib/places";

const STATUS_LABEL = {
  waiting: "매칭 대기",
  proposed: "매칭 제안 도착",
  matched: "매칭 확정",
  completed: "운행 완료",
  canceled: "취소됨",
  expired: "만료됨",
};

export default function RidesPage() {
  const router = useRouter();
  const [rides, setRides] = useState(null);
  const [origin, setOrigin] = useState(PLACES[0].name);
  const [dest, setDest] = useState(PLACES[2].name);
  const [departAfter, setDepartAfter] = useState("");
  const [windowMin, setWindowMin] = useState(30);
  const [seats, setSeats] = useState(1);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setRides(await api("/rides/me"));
    } catch {
      router.push("/");
    }
  }, [router]);

  useEffect(() => {
    if (!getToken()) {
      router.push("/");
      return;
    }
    load();
    const timer = setInterval(load, 5000); // 매칭 상태 폴링
    return () => clearInterval(timer);
  }, [load, router]);

  async function createRide(e) {
    e.preventDefault();
    setError("");
    if (origin === dest) {
      setError("출발지와 목적지가 같습니다");
      return;
    }
    const o = PLACES.find((p) => p.name === origin);
    const d = PLACES.find((p) => p.name === dest);
    const after = departAfter ? new Date(departAfter) : new Date(Date.now() + 10 * 60 * 1000);
    setBusy(true);
    try {
      await api("/rides", {
        method: "POST",
        body: {
          origin_name: o.name,
          origin_lat: o.lat,
          origin_lng: o.lng,
          dest_name: d.name,
          dest_lat: d.lat,
          dest_lng: d.lng,
          depart_after: after.toISOString(),
          depart_before: new Date(after.getTime() + windowMin * 60 * 1000).toISOString(),
          seats: Number(seats),
        },
      });
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function cancelRide(id) {
    try {
      await api(`/rides/${id}`, { method: "DELETE" });
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  const hasActive = rides?.some((r) => ["waiting", "proposed", "matched"].includes(r.status));

  return (
    <>
      <div className="card">
        <h2>동승 호출하기</h2>
        <form onSubmit={createRide}>
          <label>출발지</label>
          <select value={origin} onChange={(e) => setOrigin(e.target.value)}>
            {PLACES.map((p) => (
              <option key={p.name}>{p.name}</option>
            ))}
          </select>
          <label>목적지</label>
          <select value={dest} onChange={(e) => setDest(e.target.value)}>
            {PLACES.map((p) => (
              <option key={p.name}>{p.name}</option>
            ))}
          </select>
          <label>출발 희망 시각 (비우면 10분 뒤부터)</label>
          <input type="datetime-local" value={departAfter} onChange={(e) => setDepartAfter(e.target.value)} />
          <label>대기 가능 시간 (분)</label>
          <select value={windowMin} onChange={(e) => setWindowMin(Number(e.target.value))}>
            {[15, 30, 45, 60].map((m) => (
              <option key={m} value={m}>
                {m}분
              </option>
            ))}
          </select>
          <label>인원</label>
          <select value={seats} onChange={(e) => setSeats(e.target.value)}>
            {[1, 2, 3].map((s) => (
              <option key={s} value={s}>
                {s}명
              </option>
            ))}
          </select>
          {error && <p className="error">{error}</p>}
          <button type="submit" disabled={busy || hasActive}>
            {hasActive ? "진행 중인 호출이 있습니다" : "동승자 찾기"}
          </button>
        </form>
      </div>

      <div className="card">
        <h2>내 호출</h2>
        {rides === null && <p className="muted">불러오는 중...</p>}
        {rides?.length === 0 && <p className="muted">아직 호출 내역이 없습니다.</p>}
        {rides?.map((r) => (
          <div key={r.id} className="row" style={{ padding: "10px 0", borderBottom: "1px solid #f0f0f0" }}>
            <div>
              <div style={{ fontWeight: 700, fontSize: 14 }}>
                {r.origin_name} → {r.dest_name}
              </div>
              <div className="muted">
                {new Date(r.depart_after).toLocaleString("ko-KR", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                {" · "}
                {r.seats}명
              </div>
            </div>
            <div style={{ textAlign: "right", minWidth: 110 }}>
              <span className={`badge ${r.status}`}>{STATUS_LABEL[r.status]}</span>
              {r.match_id && ["proposed", "matched"].includes(r.status) && (
                <button style={{ marginTop: 6, padding: "6px 10px", fontSize: 13 }} onClick={() => router.push(`/matches/${r.match_id}`)}>
                  매칭 보기
                </button>
              )}
              {["waiting", "proposed", "matched"].includes(r.status) && (
                <button className="secondary" style={{ marginTop: 6, padding: "6px 10px", fontSize: 13 }} onClick={() => cancelRide(r.id)}>
                  취소
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
