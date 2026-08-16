import type { Metadata } from "next";
import "./globals.css";
import "./evidence.css";
import "./m4.css";
import "@xyflow/react/dist/style.css";
import Shell from "./shell";
export const metadata: Metadata = {title:"ScratchLab // Financial Crime Control Center",description:"Synthetic AML control testing platform"};
export default function RootLayout({children}:{children:React.ReactNode}) {return <html lang="en"><body><Shell>{children}</Shell></body></html>}
