"use client";

import Link from "next/link";
import {usePathname} from "next/navigation";

const links=[
  ["/","Command Center"],["/forge","Scenario Forge"],["/scenarios","Scenario Library"],
  ["/investigations","Investigations"],["/controls","Control Management"],["/regression","Regression Runner"],
] as const;

export default function Shell({children}:{children:React.ReactNode}){
  const pathname=usePathname();
  return <main><header className="topbar"><div><span className="mark">◆</span><strong>SCRATCHLAB</strong><small>FINANCIAL CRIME CONTROL CENTER</small></div><div className="bank">DEMO BANK <i/> SYNTHETIC</div></header><div className="shell"><nav>{links.map(([href,label])=><Link href={href} className={pathname===href||href!=="/"&&pathname.startsWith(href)?"active":""} key={href}><span>{pathname===href||href!=="/"&&pathname.startsWith(href)?"◆":"◇"}</span>{label}</Link>)}<div className="navSoon">MILESTONE 05</div>{["Control Matrix","Evidence Vault","Defect Management"].map(item=><div key={item}><span>◇</span>{item}</div>)}</nav><section className="content">{children}<footer>ALL ENTITIES AND TRANSACTIONS ARE SYNTHETIC <span>•</span> HUMAN REVIEW REQUIRED <span>•</span> NO CRIMINAL DETERMINATIONS</footer></section></div></main>
}
