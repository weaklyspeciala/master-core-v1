# Phase 3 Step 8 - Agent Integration Read-Only Audit

- Timestamp local: 2026-11-11 09:12:11
- Workspace root: H:\MASTER_AI_WORKSTATION\MASTER_AI_WORKSTATION
- Inspection mode: AST + source text only
- Project code imported/executed: NO
- Source/config modified: NO

## Source fingerprints

- autonomous_agent.py SHA256: `5631e6eed7b805a7ced7a37b5948aa3cfa366708dbee967051ccfd9ac2ef9378`
- autonomous_agent.py lines: 513
- config.json SHA256: `6206d37d65cbb085169db4f7b8fcb040159a59467be3b8ad04780f8a4c12bbca`
- workstation safety bridge SHA256: `572a13b17c1f0772efa1ece506d602051b2665d222d8f399d77bdf162aa517d1`

## Model and project configuration (selected non-secret fields)

- `ollama_url`: `"http://127.0.0.1:11434"`
- `model`: `"qwen3:4b-instruct"`
- `project_roots`: `["H:\\LOCAL_CARTOON_STUDIO\\stickman-video-director-AUTOPILOT-DEV", "H:\\MASTER_AI_WORKSTATION\\MASTER_AI_WORKSTATION"]`
- `max_file_bytes`: `1000000`
- `command_timeout_seconds`: `120`
- `allow_python_compile`: `true`
- `allow_node_check`: `true`
- `allow_pytest`: `false`
- `allow_npm_test`: `false`

## Python top-level structure

- top-level assignment `ROOT`: line 10
- top-level assignment `CFG_PATH`: line 11
- top-level assignment `DEFAULT_CFG`: line 12
- top-level assignment `CFG`: line 31
- top-level assignment `BACKUP_DIR`: line 37
- top-level assignment `AUDIT`: line 39
- top-level assignment `SYSTEM`: line 41
- `FunctionDef log`: lines 54-56
- `FunctionDef roots`: lines 58-70
- `FunctionDef resolve_project`: lines 72-87
- `FunctionDef _trusted_project_roots`: lines 89-101
- `FunctionDef allowed_root_for`: lines 104-113
- `FunctionDef display_path`: lines 116-126
- `FunctionDef safe_file`: lines 129-156
- `FunctionDef tool_tree`: lines 160-170
- `FunctionDef tool_read`: lines 172-216
- `FunctionDef tool_write`: lines 217-242
- `FunctionDef tool_check`: lines 244-270
- top-level assignment `TOOLS`: line 272
- `FunctionDef ollama`: lines 279-284
- `FunctionDef _parse_text_tool_calls`: lines 286-345
- `FunctionDef run_task`: lines 347-435
- `FunctionDef set_mode`: lines 438-444
- `FunctionDef read_multiline_task`: lines 446-459
- `FunctionDef main`: lines 460-507

## Relevant function source

The following functions are extracted from the current local source. Line numbers are preserved.

### `tool_write` (lines 217-242)

```python
  217: def tool_write(args, project):
  218:     p=safe_file(project,args.get("path","")); content=args.get("content")
  219:     if not isinstance(content,str): return {"ok":False,"error":"content must be text"}
  220:     if len(content.encode("utf-8"))>CFG["max_file_bytes"]: return {"ok":False,"error":"File exceeds size limit"}
  221:     if p.suffix.lower() not in {".py",".js",".mjs",".cjs",".json",".html",".css",".md",".txt",".yml",".yaml",".toml",".ps1"}:
  222:         return {"ok":False,"error":"File extension is not enabled for editing"}
  223:     if p.exists() and not p.is_file(): return {"ok":False,"error":"Target is not a regular file"}
  224:     backup=None
  225:     if p.exists():
  226:         stamp=datetime.now().strftime("%Y%m%d-%H%M%S-%f")
  227:         backup_dir=BACKUP_DIR/stamp
  228:         backup_dir.mkdir(parents=True,exist_ok=True)
  229:         backup=backup_dir/(p.name+".before")
  230:         shutil.copy2(p,backup)
  231:     # Validate before writing wherever possible.
  232:     try:
  233:         if p.suffix.lower()==".py": compile(content,str(p),"exec")
  234:         elif p.suffix.lower()==".json": json.loads(content)
  235:     except (SyntaxError, json.JSONDecodeError) as e:
  236:         return {"ok":False,"error":f"Validation failed; file not changed: {e}"}
  237:     p.parent.mkdir(parents=True,exist_ok=True)
  238:     tmp=p.with_name(p.name+".agent-tmp")
  239:     tmp.write_text(content,encoding="utf-8")
  240:     os.replace(tmp,p)
  241:     log("file_write",path=str(p),backup=str(backup) if backup else None)
  242:     return {"ok":True,"path":display_path(p, project),"backup":str(backup) if backup else None,"bytes":p.stat().st_size}
```

### `safe_file` (lines 129-156)

```python
  129: def safe_file(project_root, rel):
  130:     """Resolve relative paths in selected project and absolute paths in any configured root."""
  131:     raw = str(rel or "").strip().strip('"')
  132:     if not raw:
  133:         raise ValueError("A file path is required.")
  134: 
  135:     selected = Path(project_root).resolve()
  136:     expanded = Path(os.path.expandvars(raw)).expanduser()
  137: 
  138:     # Optional named-root form: @MASTER_AI_WORKSTATION/autonomous_agent.py
  139:     if raw.startswith("@") and not expanded.is_absolute():
  140:         alias, sep, remainder = raw[1:].partition("/")
  141:         if not sep:
  142:             alias, sep, remainder = raw[1:].partition("\\")
  143:         match = next((r for r in _trusted_project_roots(selected) if r.name.lower() == alias.lower()), None)
  144:         if match is None or not remainder:
  145:             raise ValueError("Unknown trusted-root alias. Use a configured root name and a relative file path.")
  146:         target = (match / remainder).resolve()
  147:     elif expanded.is_absolute():
  148:         target = expanded.resolve()
  149:     else:
  150:         if ":" in raw:
  151:             raise ValueError("Use a project-relative path or an absolute path inside a configured trusted root.")
  152:         target = (selected / expanded).resolve()
  153: 
  154:     if allowed_root_for(target, selected) is None:
  155:         raise ValueError("Access denied: path is outside all configured trusted project roots.")
  156:     return target
```

### `allowed_root_for` (lines 104-113)

```python
  104: def allowed_root_for(path, selected_project):
  105:     """Return the trusted root containing path, or None when path is outside all roots."""
  106:     target = Path(path).resolve()
  107:     for root in _trusted_project_roots(selected_project):
  108:         try:
  109:             target.relative_to(root)
  110:             return root
  111:         except ValueError:
  112:             continue
  113:     return None
```

### `resolve_project` (lines 72-87)

```python
   72: def resolve_project(project):
   73:     candidates=roots()
   74:     if not candidates: raise ValueError("No project roots configured. Edit project_roots in config.json.")
   75:     if project in ("", ".", "workspace"):
   76:         return candidates[0]
   77:     p=Path(os.path.expandvars(project)).expanduser()
   78:     if p.is_absolute():
   79:         target=p.resolve()
   80:     else:
   81:         # Named root alias or path relative to first configured root.
   82:         matches=[r for r in candidates if r.name.lower()==project.lower()]
   83:         target=matches[0] if matches else (candidates[0]/p).resolve()
   84:     if not any(target==r or r in target.parents for r in candidates):
   85:         raise ValueError("Access denied: requested project is outside configured project_roots.")
   86:     if not target.exists() or not target.is_dir(): raise ValueError(f"Project folder not found: {target}")
   87:     return target
```

### `roots` (lines 58-70)

```python
   58: def roots():
   59:     out=[]
   60:     for raw in CFG.get("project_roots",[]):
   61:         p=Path(os.path.expandvars(str(raw))).expanduser()
   62:         if p.exists() and p.is_dir(): out.append(p.resolve())
   63:     # Existing workstation workspace is always available.
   64:     ws=(ROOT/"workspace")
   65:     if ws.exists(): out.append(ws.resolve())
   66:     # Deduplicate preserving order.
   67:     result=[]
   68:     for p in out:
   69:         if p not in result: result.append(p)
   70:     return result
```

### `ollama` (lines 279-284)

```python
  279: def ollama(messages):
  280:     url=CFG["ollama_url"].rstrip("/")+"/api/chat"
  281:     payload={"model":CFG["model"],"stream":False,"messages":messages,"tools":TOOLS,
  282:              "options":{"temperature":0.15,"num_predict":4096,"num_ctx":int(CFG.get("num_ctx",8192))}}
  283:     req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
  284:     with urllib.request.urlopen(req,timeout=600) as r:return json.loads(r.read().decode())
```

### `main` (lines 460-507)

```python
  460: def main():
  461:     _p3_agent_integration = ROOT / "MASTER_CORE_V1" / "integration"
  462:     if not _p3_agent_integration.is_dir():
  463:         raise RuntimeError("MASTER_CORE_V1 Agent safety integration is missing; refusing to run without approval protection.")
  464:     if str(_p3_agent_integration) not in sys.path:
  465:         sys.path.insert(0, str(_p3_agent_integration))
  466:     import agent_safety_adapter_v2 as _p3_agent_safety
  467:     _p3_agent_safety.install(globals())
  468:     ap=argparse.ArgumentParser(description="MASTER AI WORKSTATION Autonomous Core")
  469:     ap.add_argument("--project",default=".",help="Configured project folder or absolute path inside an allowed root")
  470:     ap.add_argument("--task",help="Task to perform; omit for interactive mode")
  471:     args=ap.parse_args()
  472:     try: project=resolve_project(args.project)
  473:     except Exception as e: print("PROJECT ERROR:",e); return 2
  474:     print("\nMASTER AI WORKSTATION Ã¢â‚¬â€ AUTONOMOUS CORE v2.0 ALPHA")
  475:     print("Project:",project); print("Mode:",ACTIVE_MODE); print("Model:",CFG["model"]); print("Context:",CFG["num_ctx"])
  476:     print("Safety: project-scoped files, automatic backups, allowlisted checks; no deletion/admin/install/publishing.")
  477:     while True:
  478:         task=args.task if args.task is not None else read_multiline_task()
  479:         if task.strip().lower()=="/fast":
  480:             set_mode("fast")
  481:             print(f"\nMode switched: FAST | Model: {CFG['model']} | Context: {CFG['num_ctx']}")
  482:             continue
  483:         if task.strip().lower()=="/deep":
  484:             set_mode("deep")
  485:             print(f"\nMode switched: DEEP | Model: {CFG['model']} | Context: {CFG['num_ctx']}")
  486:             continue
  487:         if task.lower() in {"/exit","exit","quit"}: break
  488:         if not task: 
  489:             if args.task is not None: break
  490:             continue
  491:         print("\nWorking...")
  492:         try:
  493:             answer,actions=run_task(task,project)
  494:             print("\nAI REPORT\n"+answer)
  495:             print(f"\nTool actions: {len(actions)}")
  496:             for a in actions:
  497:                 print(f"- {a['tool']}: {'OK' if a['result'].get('ok') else 'CHECK'}")
  498:             log("task_finished",project=str(project),task=task,tool_actions=len(actions))
  499:         except urllib.error.HTTPError as e:
  500:             print("OLLAMA HTTP ERROR:", e.code)
  501:             print("DETAILS:", e.read().decode("utf-8", errors="replace"))
  502:         except urllib.error.URLError as e:
  503:             print("Ollama connection error:",e)
  504:         except Exception as e:
  505:             print("Agent error:",e); log("agent_error",error=str(e))
  506:         if args.task is not None: break
  507:     return 0
```

### `_trusted_project_roots` (lines 89-101)

```python
   89: def _trusted_project_roots(selected_project):
   90:     """Return only configured project roots plus the currently selected project."""
   91:     candidates = [Path(selected_project).resolve()]
   92:     try:
   93:         candidates.extend(Path(p).resolve() for p in roots())
   94:     except Exception:
   95:         pass
   96:     unique = []
   97:     for item in candidates:
   98:         if item.exists() and item.is_dir() and item not in unique:
   99:             unique.append(item)
  100:     # Prefer the most specific root when configured roots are nested.
  101:     return sorted(unique, key=lambda p: len(p.parts), reverse=True)
```

### `display_path` (lines 116-126)

```python
  116: def display_path(path, selected_project):
  117:     """Display paths relative to their trusted root; label secondary roots clearly."""
  118:     target = Path(path).resolve()
  119:     root = allowed_root_for(target, selected_project)
  120:     if root is None:
  121:         return "<outside-trusted-roots>"
  122:     relative = target.relative_to(root).as_posix()
  123:     selected = Path(selected_project).resolve()
  124:     if root == selected:
  125:         return relative or "."
  126:     return f"@{root.name}/{relative}" if relative else f"@{root.name}/"
```

### `tool_check` (lines 244-270)

```python
  244: def tool_check(args, project):
  245:     kind=args.get("kind"); rel=args.get("path",".")
  246:     p=safe_file(project,rel)
  247:     timeout=int(CFG.get("command_timeout_seconds",120))
  248:     if kind=="python_compile" and CFG.get("allow_python_compile"):
  249:         if p.is_file(): files=[p] if p.suffix==".py" else []
  250:         else: files=list(p.rglob("*.py"))
  251:         if not files:return {"ok":False,"error":"No Python files found"}
  252:         cmd=[sys.executable,"-m","compileall","-q",*[str(x) for x in files]]
  253:     elif kind=="node_check" and CFG.get("allow_node_check"):
  254:         if not p.is_file() or p.suffix.lower() not in {".js",".mjs",".cjs"}:return {"ok":False,"error":"Choose one JS/MJS/CJS file"}
  255:         cmd=["node","--check",str(p)]
  256:     elif kind=="pytest" and CFG.get("allow_pytest"):
  257:         cmd=["pytest","-q",str(p)]
  258:     elif kind=="npm_test" and CFG.get("allow_npm_test"):
  259:         if not (p/"package.json").is_file():return {"ok":False,"error":"package.json not found"}
  260:         cmd=["npm","test","--","--runInBand"]
  261:     else:return {"ok":False,"error":"This check is disabled or unsupported in config.json"}
  262:     try:
  263:         result=subprocess.run(cmd,cwd=str(p if p.is_dir() else p.parent),capture_output=True,text=True,
  264:             encoding="utf-8",errors="replace",timeout=timeout,shell=False)
  265:         out={"ok":result.returncode==0,"kind":kind,"command":cmd,"returncode":result.returncode,
  266:              "stdout":result.stdout[-10000:],"stderr":result.stderr[-10000:]}
  267:     except FileNotFoundError as e: out={"ok":False,"kind":kind,"error":str(e)}
  268:     except subprocess.TimeoutExpired as e: out={"ok":False,"kind":kind,"error":f"Timed out after {timeout}s","stdout":str(e.stdout or "")[-3000:],"stderr":str(e.stderr or "")[-3000:]}
  269:     log("check",project=str(project),kind=kind,ok=out.get("ok"))
  270:     return out
```

### `run_task` (lines 347-435)

```python
  347: def run_task(task, project):
  348:     """Run a bounded task. Supports native Ollama calls and JSON tool calls in text."""
  349:     messages = [
  350:         {"role": "system", "content": SYSTEM + "\n\nTOOL RULES: Use project-relative file paths whenever possible. If an absolute path is supplied, it must be inside any configured trusted project root. Never print tool-call JSON as a report when you can call a tool. Make only necessary tool calls."},
  351:         {"role": "user", "content": f"Selected project root: {project}\nTask: {task}\nInspect first. Work only inside this project root. Validate changes when appropriate."},
  352:     ]
  353:     history = []
  354:     max_rounds = max(1, int(CFG.get("max_tool_rounds", 8)))
  355:     max_calls = max(1, int(CFG.get("max_tool_calls_per_task", 6)))
  356:     max_calls = min(max_calls, 12)  # Hard safety ceiling; config cannot remove the ceiling.
  357:     total_calls = 0
  358:     seen = set()
  359:     duplicate_limit = max(1, int(CFG.get("max_duplicate_tool_calls", 1)))
  360: 
  361:     for _round_index in range(max_rounds):
  362:         response = ollama(messages)
  363:         msg = response.get("message", {}) if isinstance(response, dict) else {}
  364:         if not isinstance(msg, dict):
  365:             return "Stopped safely: Ollama returned an invalid message structure.", history
  366: 
  367:         content = msg.get("content", "") or ""
  368:         calls = msg.get("tool_calls") or []
  369:         source_was_text = False
  370:         if not calls:
  371:             calls = _parse_text_tool_calls(content)
  372:             source_was_text = bool(calls)
  373: 
  374:         if not calls:
  375:             # A JSON-looking but unparseable tool request must not trigger another model retry.
  376:             if isinstance(content, str) and '"arguments"' in content and '"name"' in content:
  377:                 return ("Stopped safely: the model emitted a malformed or unsupported JSON tool request. "
  378:                         "No tool was executed. Use one valid tool request at a time."), history
  379:             return content.strip() or "The model returned no final response.", history
  380: 
  381:         # Convert text-emitted calls into the same message shape used by native tool calls.
  382:         messages.append({"role": "assistant", "content": content, "tool_calls": calls})
  383: 
  384:         for call in calls:
  385:             if total_calls >= max_calls:
  386:                 return (f"Stopped safely: this task reached the hard limit of {max_calls} tool calls. "
  387:                         "Review the actions already completed, then submit a smaller next task."), history
  388: 
  389:             fn = call.get("function", {}) if isinstance(call, dict) else {}
  390:             if not isinstance(fn, dict):
  391:                 history.append({"tool": "invalid_call", "args": {}, "result": {"ok": False, "error": "Malformed tool-call structure"}})
  392:                 return "Stopped safely: the model returned a malformed tool-call structure.", history
  393: 
  394:             name = fn.get("name")
  395:             args = fn.get("arguments", {})
  396:             if isinstance(args, str):
  397:                 try:
  398:                     args = json.loads(args)
  399:                 except Exception:
  400:                     args = None
  401:             if not isinstance(args, dict):
  402:                 history.append({"tool": str(name), "args": {}, "result": {"ok": False, "error": "Tool arguments must be a JSON object"}})
  403:                 return "Stopped safely: invalid tool arguments; no further retry was attempted.", history
  404: 
  405:             signature = json.dumps({"tool": name, "args": args}, sort_keys=True, ensure_ascii=False, default=str)
  406:             seen_count = sum(1 for item in seen if item == signature)
  407:             if seen_count >= duplicate_limit:
  408:                 return (f"Stopped safely: the model repeated the same tool request ({name}) "
  409:                         "without making progress."), history
  410:             seen.add(signature)
  411: 
  412:             try:
  413:                 if name == "list_project_files":
  414:                     result = tool_tree(args, project)
  415:                 elif name == "read_project_file":
  416:                     result = tool_read(args, project)
  417:                 elif name == "write_project_file":
  418:                     result = tool_write(args, project)
  419:                 elif name == "run_check":
  420:                     result = tool_check(args, project)
  421:                 else:
  422:                     result = {"ok": False, "error": f"Unknown tool: {name}"}
  423:             except Exception as exc:
  424:                 result = {"ok": False, "error": str(exc)}
  425: 
  426:             total_calls += 1
  427:             history.append({"tool": name, "args": args, "result": result})
  428:             if result.get("status") == "pending_approval":
  429:                 return ("A project file change is waiting for your review in the Safety Approval Center. No project file has been changed yet. Approve or reject the ticket, then submit the next task."), history
  430:             messages.append({"role": "tool", "tool_name": name or "unknown", "content": json.dumps(result, ensure_ascii=False, default=str)})
  431: 
  432:         # Continue only after real tool execution. The next iteration is bounded by max_rounds/max_calls.
  433: 
  434:     return (f"Stopped safely after {max_rounds} model rounds and {total_calls} tool calls. "
  435:             "The agent did not continue retrying. Submit a narrower task to continue."), history
```

### `read_multiline_task` (lines 446-459)

```python
  446: def read_multiline_task():
  447:     print("\nEnter your task. Type /done on a new line to submit.")
  448:     print("Commands: /fast, /deep, /exit")
  449:     first=input("\nTask: ")
  450:     command=first.strip().lower()
  451:     if command in {"/fast","/deep","/exit","exit","quit"}:
  452:         return command
  453:     lines=[first]
  454:     while True:
  455:         line=input("... ")
  456:         if line.strip().lower()=="/done":
  457:             break
  458:         lines.append(line)
  459:     return "\n".join(lines).strip()
```

## Tool registry and routing references

- line 308: `fn = obj.get("function")`
- line 329: `found.append({"type": "function", "function": {"name": name, "arguments": arguments}})`
- line 382: `messages.append({"role": "assistant", "content": content, "tool_calls": calls})`
- line 314: `if isinstance(obj.get("tool_calls"), list):`
- line 354: `max_rounds = max(1, int(CFG.get("max_tool_rounds", 8)))`
- line 355: `max_calls = max(1, int(CFG.get("max_tool_calls_per_task", 6)))`
- line 359: `duplicate_limit = max(1, int(CFG.get("max_duplicate_tool_calls", 1)))`
- line 368: `calls = msg.get("tool_calls") or []`
- line 427: `history.append({"tool": name, "args": args, "result": result})`
- line 430: `messages.append({"role": "tool", "tool_name": name or "unknown", "content": json.dumps(result, ensure_ascii=False, default=str)})`
- line 389: `fn = call.get("function", {}) if isinstance(call, dict) else {}`
- line 391: `history.append({"tool": "invalid_call", "args": {}, "result": {"ok": False, "error": "Malformed tool-call structure"}})`
- line 402: `history.append({"tool": str(name), "args": {}, "result": {"ok": False, "error": "Tool arguments must be a JSON object"}})`
- line 497: `print(f"- {a['tool']}: {'OK' if a['result'].get('ok') else 'CHECK'}")`

## Safety compatibility analysis

- Current Agent project roots can include multiple directories, including the separate Stickman repository.
- The Step 6 safe_file_ops module is intentionally restricted to the MASTER workspace root.
- Therefore Step 8 must use an agent-specific trusted-root resolver rather than passing external project paths into safe_file_ops.safe_target().
- A compatible design must keep approval tickets in MASTER_CORE_V1 but store the approved target's trusted-root identity, relative path, original SHA256 and proposed SHA256.
- Apply must re-resolve the selected project root, reject path escapes, backup original bytes, verify backup, recheck target hash, atomically replace, run configured static validation, and restore only if the target still matches the just-written SHA256.
- Existing tool_check policy and disabled-by-default test commands must remain unchanged.
- The local Approval Panel should list both workstation-file and Agent-project tickets, and approval must dispatch by ticket kind.

## Read-only audit result

- Functions selected for detailed review: 12
- Project code executed: NO
- Source/config files modified: NO
- Next step: build a separately backed-up Agent safety adapter and extend the approval bridge/panel with an agent-project ticket handler.
