"use client";

import Link from "next/link";
import {useEffect,useState} from "react";
import {api,Dashboard} from "./types";

export default function CommandCenter(){
  const [data,setData]=useState<Dashboard|null>(null),[error,setError]=useState("");
  useEffect(()=>{api<Dashboard>("/api/v1/dashboard").then(setData).catch(e=>setError(e.message))},[]);
  const max=Math.max(...(data?.transaction_activity.map(item=>item.count)??[1]),1);
  return <><div className="eyebrow">MILESTONE 04 / INVESTIGATOR UI</div><h1>Command Center</h1><p className="lede">Control performance, investigation demand, and evidence-source health at a glance.</p>{error&&<p className="error globalError">{error}</p>}<section className="metricCards"><Metric label="CONTROL HEALTH" value={data?.control_health==null?"—":`${data.control_health}%`}/><Metric label="OPEN CASES" value={data?String(data.open_cases):"—"}/><Metric label="TEST COVERAGE" value={data?.test_coverage==null?"—":`${data.test_coverage}%`}/><Metric label="LAST TEST RUN" value={data?.last_test_run?new Date(data.last_test_run).toLocaleString():"NOT RUN"}/></section><div className="dashboardGrid"><article className="panel dashboardPanel"><Title label="TRANSACTION ACTIVITY" status="14 SIMULATION DAYS"/>{data?.transaction_activity.length?<div className="bars">{data.transaction_activity.map(item=><div className="barSlot" key={item.date} title={`${item.date}: ${item.count} transactions / $${item.volume.toLocaleString()}`}><i style={{height:`${Math.max(item.count/max*100,4)}%`}}/><small>{item.date.slice(5)}</small></div>)}</div>:<Empty text="Run a scenario to populate transaction activity."/>}</article><article className="panel dashboardPanel"><Title label="SOURCE HEALTH" status={`${data?.total_alerts??0} ALERTS`}/>{data?.source_health.length?<div className="sourceList">{data.source_health.map(item=><div key={item.source}><b className={item.status}>{item.status==="completed"?"●":"▲"}</b><strong>{item.source.replaceAll("_"," ")}</strong><span>{item.status}</span><small>{new Date(item.observed_at).toLocaleString()}</small></div>)}</div>:<Empty text="Evidence sources report after the first alert."/>}</article></div><section className="recent"><Title label="RECENT CONTROL FAILURES" status="LATEST 5"/>{data?.recent_failures.length?data.recent_failures.map(item=><article key={item.run_id}><b>FAIL</b><strong>{item.scenario_key}</strong><span>{item.control_id}</span><p>{item.reason}</p></article>):<Empty text="No failed control tests are recorded."/>}</section><Link className="primaryLink" href="/investigations">OPEN INVESTIGATION QUEUE →</Link></>
}

function Metric({label,value}:{label:string;value:string}){return <article><span>{label}</span><strong>{value}</strong></article>}
export function Title({label,status}:{label:string;status:string}){return <div className="panelTitle"><span>{label}</span><em>{status}</em></div>}
export function Empty({text}:{text:string}){return <div className="empty"><div className="orbit">◎</div><strong>No results yet</strong><p>{text}</p></div>}
