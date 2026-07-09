import "./globals.css";
import Link from "next/link";

export const metadata = {
  title: "가치가 GACHIGA",
  description: "광주 택시 동승 매칭 서비스",
};

export default function RootLayout({ children }) {
  return (
    <html lang="ko">
      <body>
        <div className="nav">
          <Link href="/rides">🚕 가치가</Link>
          <Link href="/" style={{ fontSize: 13, fontWeight: 400 }}>
            로그인
          </Link>
        </div>
        <main>{children}</main>
      </body>
    </html>
  );
}
