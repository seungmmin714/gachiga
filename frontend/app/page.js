"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, saveTokens, clearTokens } from "@/lib/api";

export default function AuthPage() {
  const router = useRouter();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ email: "", password: "", name: "", department: "", phone: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "signup") {
        await api("/auth/signup", {
          method: "POST",
          body: {
            email: form.email,
            password: form.password,
            name: form.name,
            department: form.department || null,
            phone: form.phone || null,
          },
        });
      }
      clearTokens();
      const tokens = await api("/auth/login", {
        method: "POST",
        body: { email: form.email, password: form.password },
      });
      saveTokens(tokens);
      router.push("/rides");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h2>{mode === "login" ? "로그인" : "회원가입"}</h2>
      <form onSubmit={submit}>
        <label>학교 이메일</label>
        <input type="email" value={form.email} onChange={set("email")} required placeholder="honggildong@jnu.ac.kr" />
        <label>비밀번호 (8자 이상)</label>
        <input type="password" value={form.password} onChange={set("password")} required minLength={8} />
        {mode === "signup" && (
          <>
            <label>이름</label>
            <input value={form.name} onChange={set("name")} required />
            <label>학과 (선택)</label>
            <input value={form.department} onChange={set("department")} />
            <label>연락처 (선택)</label>
            <input value={form.phone} onChange={set("phone")} placeholder="010-0000-0000" />
          </>
        )}
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={busy}>
          {mode === "login" ? "로그인" : "가입하고 시작하기"}
        </button>
      </form>
      <button className="secondary" onClick={() => setMode(mode === "login" ? "signup" : "login")}>
        {mode === "login" ? "처음이신가요? 회원가입" : "이미 계정이 있어요"}
      </button>
    </div>
  );
}
