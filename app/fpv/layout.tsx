import type { Metadata } from "next";
import "./fpv.scss";
import { FpvHeader } from "@/components/fpv/FpvHeader";
import { LegacyHashRedirect } from "@/components/fpv/LegacyHashRedirect";

export const metadata: Metadata = {
  title: {
    default: "FPV Drone-Strike Dataset Viewer",
    template: "%s — FPV Drone-Strike Dataset",
  },
};

export default function FpvLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="fpv-app">
      <LegacyHashRedirect />
      <FpvHeader />
      <div className="fpv-wrap">{children}</div>
    </div>
  );
}
