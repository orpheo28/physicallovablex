import type { Metadata } from "next";
import { FictionalBanner } from "@/components/FictionalBanner";

export const metadata: Metadata = { title: { default: "Factory portal", template: "%s · Factory portal · PhysicalLovableX" } };

export default function FactoriesLayout({ children }: LayoutProps<"/factories">) {
  return (
    <div className="flex h-full min-h-0 flex-col">
      <FictionalBanner />
      <div className="min-h-0 flex-1">{children}</div>
    </div>
  );
}
