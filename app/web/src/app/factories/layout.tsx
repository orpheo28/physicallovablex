import type { Metadata } from "next";
import { FictionalBanner } from "@/components/FictionalBanner";

export const metadata: Metadata = { title: { default: "Factory portal", template: "%s · Factory portal · PhysicalLovableX" } };

export default function FactoriesLayout({ children }: LayoutProps<"/factories">) {
  return (
    <>
      <FictionalBanner />
      {children}
    </>
  );
}
