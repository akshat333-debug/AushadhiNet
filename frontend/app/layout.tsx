import type { Metadata } from "next";
import "./globals.css";
import ServiceWorkerRegister from "@/components/ServiceWorkerRegister";
import DevSignIn from "@/components/DevSignIn";

export const metadata: Metadata = {
  title: "AushadhiNet",
  description: "Federated AI for India's last-mile health resource network",
  manifest: "/manifest.json",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900">
        <ServiceWorkerRegister />
        <nav className="flex items-center gap-4 border-b bg-white px-4 py-3 text-sm">
          <a href="/" className="font-semibold">AushadhiNet</a>
          <a href="/orders">Orders</a>
          <a href="/agent">Agent</a>
          <a href="/sim">WhatsApp Simulator</a>
          <a href="/public">Public View</a>
          <DevSignIn />
        </nav>
        <main className="p-4">{children}</main>
      </body>
    </html>
  );
}
