"""Local-only Safety Approval Panel for MASTER AI WORKSTATION."""
from __future__ import annotations

def render_panel() -> str:
    return r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark">
<meta name="referrer" content="no-referrer">
<title>Master AI | Safety Approval</title>
<style>
:root{color-scheme:dark;--bg:#0b1020;--panel:#121a2d;--panel2:#182238;--line:#2b3954;--text:#edf3ff;--muted:#9aabc5;--blue:#6aa8ff;--green:#4bd4a0;--red:#ff7777;--amber:#ffc86b}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 15% 0%,#18294a 0,transparent 42%),var(--bg);color:var(--text);font:15px/1.5 Segoe UI,Arial,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:28px 18px 60px}.top{display:flex;justify-content:space-between;gap:16px;align-items:center;flex-wrap:wrap;margin-bottom:22px}
h1{font-size:26px;margin:0 0 4px;letter-spacing:.2px}.sub{color:var(--muted);font-size:13px}
.pill{border:1px solid #31547d;background:#142744;color:#b9d8ff;padding:7px 12px;border-radius:999px;font-size:12px}
.grid{display:grid;grid-template-columns:340px minmax(0,1fr);gap:18px}.panel{background:rgba(18,26,45,.96);border:1px solid var(--line);border-radius:16px;overflow:hidden;box-shadow:0 12px 40px #0003}
.panelhead{padding:15px 17px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center;gap:10px}
.panelhead h2{font-size:15px;margin:0}.count{color:var(--muted);font-size:12px}
.list{padding:9px;max-height:72vh;overflow:auto}.ticket{width:100%;display:block;text-align:left;border:1px solid transparent;background:transparent;color:var(--text);padding:12px;border-radius:11px;margin:3px 0;cursor:pointer}
.ticket:hover{background:var(--panel2)}.ticket.active{background:#1a2a45;border-color:#416b9c}.ticket strong{display:block;font-size:13px;overflow-wrap:anywhere}.ticket small{display:block;color:var(--muted);margin-top:5px;overflow-wrap:anywhere}
.tag{display:inline-block;font-size:10px;padding:2px 7px;border-radius:999px;background:#303044;color:#d7d7ed;margin-top:7px}.tag.test{background:#49351d;color:#ffd58e}.tag.expired{background:#4b252b;color:#ffb2b2}
.detail{padding:19px}.empty{padding:45px 20px;text-align:center;color:var(--muted)}
.path{font:13px Consolas,monospace;color:#b8d5ff;overflow-wrap:anywhere}.hash{font:11px Consolas,monospace;color:#aebbd0;overflow-wrap:anywhere;word-break:break-all}
.meta{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:16px 0}.meta>div{background:var(--panel2);border:1px solid #273752;border-radius:10px;padding:10px}.label{display:block;color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.6px;margin-bottom:5px}
pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:340px;overflow:auto;background:#080d18;border:1px solid #293751;padding:14px;border-radius:10px;font:12px/1.55 Consolas,monospace;color:#d9e7ff}
input{width:100%;background:#080d18;border:1px solid #344762;border-radius:9px;color:white;padding:12px;font-size:14px;outline:none}input:focus{border-color:var(--blue)}
.actions{display:flex;gap:9px;flex-wrap:wrap;margin-top:13px}button.action{border:0;border-radius:9px;padding:11px 16px;font-weight:600;cursor:pointer}
.approve{background:var(--green);color:#08251c}.reject{background:#512d35;color:#ffd7dc;border:1px solid #74414b!important}.secondary{background:#25344d;color:#e3edff}.action:disabled{opacity:.35;cursor:not-allowed}
.notice{padding:11px 13px;border-radius:10px;margin:12px 0;font-size:13px;background:#1c2c42;border:1px solid #354e70;color:#c8dfff}.notice.warn{background:#3e2e19;border-color:#70552d;color:#ffdda2}.notice.bad{background:#40252b;border-color:#79414a;color:#ffc0c6}
.status{margin-top:12px;min-height:22px;color:var(--muted);font-size:13px}.footer{margin-top:18px;color:var(--muted);font-size:11px}
@media(max-width:780px){.grid{grid-template-columns:1fr}.list{max-height:280px}.meta{grid-template-columns:1fr}.detail{padding:14px}h1{font-size:22px}}
</style>
</head>
<body>
<div class="wrap">
<header class="top"><div><h1>Safety Approval Center</h1><div class="sub">MASTER AI WORKSTATION · Local review before file changes</div></div><div class="pill">127.0.0.1 · LOCAL ONLY</div></header>
<div class="notice">No file is changed while a ticket is pending. Review the target, proposed content and both SHA256 fingerprints before approving.</div>
<main class="grid">
<section class="panel"><div class="panelhead"><h2>Pending approvals</h2><span class="count" id="count">Loading…</span></div><div class="list" id="ticketList"><div class="empty">Loading pending tickets…</div></div></section>
<section class="panel"><div class="panelhead"><h2>Review details</h2><button class="action secondary" id="refreshBtn" type="button">Refresh</button></div><div class="detail" id="detail"><div class="empty">Select a ticket to inspect its proposed change.</div></div></section>
</main>
<div class="footer">Approval tickets expire automatically. Known test-sandbox tickets cannot be approved here. Reject test tickets to clear them. This page uses only the local Workstation API.</div>
</div>
<script>
"use strict";
const listEl=document.getElementById("ticketList"),detailEl=document.getElementById("detail"),countEl=document.getElementById("count");
let tickets=[],selectedId=null,selectedTicket=null;
const $=id=>document.getElementById(id);
function make(tag,cls,text){const el=document.createElement(tag);if(cls)el.className=cls;if(text!==undefined)el.textContent=text;return el;}
async function api(path,options={}){const headers={"Accept":"application/json",...(options.body?{"Content-Type":"application/json"}:{}),...(options.headers||{})};const response=await fetch(path,{...options,headers,cache:"no-store",credentials:"same-origin"});let data={};try{data=await response.json()}catch(_){}if(!response.ok)throw new Error(data.error||("HTTP "+response.status));return data;}
function isTestTicket(path){const p=String(path||"").replaceAll("\\","/").toUpperCase();return /(^|\/)MASTER_CORE_V1_(TEST|STEP\d|RECOVERY).*SANDBOX/.test(p)||p.includes("LIVE_HTTP_SANDBOX");}
function isExpired(ticket){return Number(ticket.expires_at||0)*1000<Date.now();}
function renderList(){listEl.replaceChildren();countEl.textContent=tickets.length+" ticket(s)";if(!tickets.length){listEl.append(make("div","empty","No pending approvals. Your workspace is clear."));return;}for(const t of tickets){const b=make("button","ticket"+(t.ticket_id===selectedId?" active":""));b.type="button";b.addEventListener("click",()=>loadTicket(t.ticket_id));b.append(make("strong","",t.relative_path||"Unknown file"),make("small","","Expires: "+(t.expires_at?new Date(t.expires_at*1000).toLocaleString():"Unknown")));if(isTestTicket(t.relative_path))b.append(make("span","tag test","TEST SANDBOX · approval disabled"));else if(isExpired(t))b.append(make("span","tag expired","EXPIRED"));else b.append(make("span","tag","PENDING REVIEW"));listEl.append(b);}}
function renderDetail(t){detailEl.replaceChildren();detailEl.append(make("div","path",t.relative_path||"Unknown target"));const meta=make("div","meta");for(const [label,value] of [["Ticket ID",t.ticket_id],["Status",t.status],["Original SHA256",t.current_sha256],["Proposed SHA256",t.proposed_sha256],["Created",t.created_at?new Date(t.created_at*1000).toLocaleString():"Unknown"],["Expires",t.expires_at?new Date(t.expires_at*1000).toLocaleString():"Unknown"]]){const cell=make("div");cell.append(make("span","label",label),make("div","hash",value||"—"));meta.append(cell);}detailEl.append(meta,make("span","label","Proposed file content"));const pre=make("pre");pre.textContent=typeof t.proposed_content==="string"?t.proposed_content:"(No proposed content supplied)";detailEl.append(pre);const sandbox=isTestTicket(t.relative_path),expired=isExpired(t);if(sandbox)detailEl.append(make("div","notice warn","This is a known test-sandbox ticket. Approval is disabled to protect test artifacts. Reject it to clear the queue."));else if(expired)detailEl.append(make("div","notice bad","This ticket has expired. It cannot be approved. Reject it or refresh the queue."));else detailEl.append(make("div","notice","To apply this exact proposal, enter APPROVE below. The server checks both SHA256 values again before writing."));detailEl.append(make("span","label","Type APPROVE to confirm"));const input=make("input");input.id="confirmText";input.placeholder="APPROVE";input.autocomplete="off";input.spellcheck=false;detailEl.append(input);const actions=make("div","actions");const approve=make("button","action approve","Approve & apply");approve.id="approveBtn";approve.type="button";approve.disabled=sandbox||expired;approve.addEventListener("click",approveSelected);const reject=make("button","action reject","Reject ticket");reject.id="rejectBtn";reject.type="button";reject.addEventListener("click",rejectSelected);actions.append(approve,reject);detailEl.append(actions);const status=make("div","status","");status.id="actionStatus";detailEl.append(status);}
async function loadList(){const data=await api("/api/safety/pending");tickets=Array.isArray(data.tickets)?data.tickets:[];renderList();if(selectedId&&tickets.some(t=>t.ticket_id===selectedId)){await loadTicket(selectedId);}else{selectedId=null;selectedTicket=null;detailEl.replaceChildren(make("div","empty","Select a ticket to inspect its proposed change."));}}
async function loadTicket(id){try{const data=await api("/api/safety/ticket?ticket_id="+encodeURIComponent(id));selectedId=id;selectedTicket=data.ticket;renderList();renderDetail(selectedTicket);}catch(e){detailEl.replaceChildren(make("div","notice bad",e.message));await loadList();}}
async function approveSelected(){if(!selectedTicket)return;const typed=$("confirmText").value;if(typed!=="APPROVE"){$("actionStatus").textContent="Type exactly APPROVE. No file was changed.";return;}const btn=$("approveBtn");btn.disabled=true;try{const result=await api("/api/safety/approve",{method:"POST",body:JSON.stringify({ticket_id:selectedTicket.ticket_id,typed_confirmation:typed,expected_current_sha256:selectedTicket.current_sha256,expected_proposed_sha256:selectedTicket.proposed_sha256})});await loadList();detailEl.replaceChildren(make("div","notice",result.status==="validated"?"Change approved and validation passed. Backup: "+result.backup:"Operation completed: "+result.status));}catch(e){$("actionStatus").textContent=e.message;btn.disabled=false;}}
async function rejectSelected(){if(!selectedTicket)return;const btn=$("rejectBtn");btn.disabled=true;try{await api("/api/safety/reject",{method:"POST",body:JSON.stringify({ticket_id:selectedTicket.ticket_id})});selectedId=null;selectedTicket=null;await loadList();detailEl.replaceChildren(make("div","notice","Ticket rejected. No file was changed."));}catch(e){$("actionStatus").textContent=e.message;btn.disabled=false;}}
$("refreshBtn").addEventListener("click",()=>loadList().catch(e=>detailEl.replaceChildren(make("div","notice bad",e.message))));
loadList().catch(e=>detailEl.replaceChildren(make("div","notice bad",e.message)));
</script>
</body></html>"""