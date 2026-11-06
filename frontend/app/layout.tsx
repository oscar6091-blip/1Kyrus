import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "연구 워크플로 프로토타입",
  description: "아이디어에서 논문 초안까지 단계별 검토·승인 워크플로 (수업 과제용 프로토타입)",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
