"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { API_BASE, api, getToken } from "@/lib/api";

const STATUS_LABEL = {
  proposed: "수락 대기 중",
  confirmed: "매칭 확정",
  canceled: "무산됨",
  completed: "운행 완료",
};

// 지도 API 키 없이 좌표를 상대 배치하는 미니맵 (실서비스에서 Kakao Maps로 교체)
function MiniMap({ points }) {
  const pad = 20;
  const w = 400;
  const h = 220;
  const lats = points.map((p) => p.lat);
  const lngs = points.map((p) => p.lng);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLng = Math.min(...lngs);
  const maxLng = Math.max(...lngs);
  const x = (lng) => pad + ((lng - minLng) / (maxLng - minLng || 1)) * (w - pad * 2);
  const y = (lat) => h - pad - ((lat - minLat) / (maxLat - minLat || 1)) * (h - pad * 2);

  return (
    <svg viewBox={`0 0 ${w} ${h}`} style={{ width: "100%", background: "#eef2f7", borderRadius: 8 }}>
      {points.length >= 2 && (
        <line x1={x(points[0].lng)} y1={y(points[0].lat)} x2={x(points[1].lng)} y2={y(points[1].lat)} stroke="#2563eb" strokeWidth="2" strokeDasharray="6 4" />
      )}
      {points.map((p, i) => (
        <g key={i}>
          <circle cx={x(p.lng)} cy={y(p.lat)} r="7" fill={p.color} />
          <text x={x(p.lng)} y={y(p.lat) - 12} textAnchor="middle" fontSize="11" fill="#374151">
            {p.label}
          </text>
        </g>
      ))}
    </svg>
  );
}

export default function MatchPage() {
  const { id } = useParams();
  const router = useRouter();
  const [match, setMatch] = useState(null);
  const [locations, setLocations] = useState({});
  const [error, setError] = useState("");
  const wsRef = useRef(null);

  const load = useCallback(async () => {
    try {
      setMatch(await api(`/matches/${id}`));
    } catch (err) {
      setError(err.message);
    }
  }, [id]);

  useEffect(() => {
    if (!getToken()) {
      router.push("/");
      return;
    }
    load();
    const timer = setInterval(load, 5000);
    return () => clearInterval(timer);
  }, [load, router]);

  // 확정된 매칭이면 WebSocket으로 실시간 위치 공유 (안심 경로)
  useEffect(() => {
    if (match?.status !== "confirmed" || wsRef.current) return;
    const wsUrl = `${API_BASE.replace("http", "ws")}/ws/matches/${id}?token=${getToken()}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === "location") {
        setLocations((prev) => ({ ...prev, [msg.user_id]: msg }));
      }
    };

    const sendLocation = () => {
      if (ws.readyState !== WebSocket.OPEN || !navigator.geolocation) return;
      navigator.geolocation.getCurrentPosition((pos) => {
        ws.send(JSON.stringify({ type: "location", lat: pos.coords.latitude, lng: pos.coords.longitude }));
      });
    };
    const timer = setInterval(sendLocation, 7000);

    return () => {
      clearInterval(timer);
      ws.close();
      wsRef.current = null;
    };
  }, [match?.status, id]);

  async function action(name) {
    setError("");
    try {
      setMatch(await api(`/matches/${id}/${name}`, { method: "POST" }));
    } catch (err) {
      setError(err.message);
    }
  }

  if (!match) return <div className="card">{error ? <p className="error">{error}</p> : <p className="muted">불러오는 중...</p>}</div>;

  const mapPoints = [
    { lat: match.pickup_lat, lng: match.pickup_lng, color: "#2563eb", label: `탑승: ${match.pickup_name}` },
    ...Object.values(locations).map((l) => ({ lat: l.lat, lng: l.lng, color: "#10b981", label: "동승자 위치" })),
  ];

  return (
    <>
      <div className="card">
        <div className="row">
          <h2>매칭 #{match.id}</h2>
          <span className={`badge ${match.status}`}>{STATUS_LABEL[match.status]}</span>
        </div>
        <MiniMap points={mapPoints} />
        <p style={{ marginTop: 10 }}>
          <strong>탑승 지점</strong> {match.pickup_name}
        </p>
        <p className="muted">
          예상 총 요금 {match.estimated_fare_total.toLocaleString()}원 · 우회 지수 {match.detour_index.toFixed(2)}
        </p>
      </div>

      <div className="card">
        <h2>동승 멤버 & 분담액</h2>
        {match.members.map((m) => (
          <div key={m.user_id} className="row" style={{ padding: "8px 0" }}>
            <span>
              {m.name}
              <span className="muted"> {m.accepted === true ? "· 수락함" : m.accepted === false ? "· 거절함" : "· 대기 중"}</span>
            </span>
            <span>
              <strong>{m.share_amount.toLocaleString()}원</strong>
              <span className="muted"> (단독 {m.solo_fare.toLocaleString()}원)</span>
            </span>
          </div>
        ))}
        <p className="muted" style={{ marginTop: 8 }}>
          인당 평균{" "}
          {Math.round(
            (match.members.reduce((acc, m) => acc + (1 - m.share_amount / m.solo_fare), 0) / match.members.length) * 100
          )}
          % 절감
        </p>
        {error && <p className="error">{error}</p>}
        {match.status === "proposed" && (
          <div className="row">
            <button onClick={() => action("accept")}>수락</button>
            <button className="danger" onClick={() => action("reject")}>
              거절
            </button>
          </div>
        )}
        {match.status === "confirmed" && (
          <button onClick={() => action("complete")}>운행 완료 (정산 기록)</button>
        )}
      </div>
    </>
  );
}
