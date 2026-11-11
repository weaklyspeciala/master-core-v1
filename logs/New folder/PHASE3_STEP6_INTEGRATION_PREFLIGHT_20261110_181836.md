# Phase 3 Step 6 - Integration Preflight

- Timestamp: 2026-11-10 18:18:36
- Workspace: H:\MASTER_AI_WORKSTATION\MASTER_AI_WORKSTATION
- Mode: READ-ONLY static source inspection
- Project code executed: NO
- Source files modified: NO

## workstation.py

- Path: H:\MASTER_AI_WORKSTATION\MASTER_AI_WORKSTATION\workstation.py
- Bytes: 37662
- Lines: 578
- SHA256: DCBC0BA7E148070DF939B80F7E752DFFBFFCCB8D0040D6AB118E58F190CBB1A1

- Marker hits: 30
- Source excerpts (line-numbered):

```text
    1: import json
    2: import urllib.request
    3: import urllib.error
    4: import subprocess
    5: import sys
    6: import uuid
    7: import re
    8: from datetime import datetime, timezone
    9: from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
   10: from pathlib import Path
   11: from urllib.parse import urlparse, parse_qs
   12: 
   13: ROOT = Path(__file__).resolve().parent
   14: CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8-sig"))
-----
  106:     {"type":"function","function":{"name":"validate_cartoon_project","description":"Validate an existing video project folder, scene settings, duration and supported actions without rendering.","parameters":{"type":"object","properties":{"path":{"type":"string","description":"Relative project folder, for example videos/banana_story"}},"required":["path"]}}},
  107:     {"type":"function","function":{"name":"request_render_video","description":"Request user approval to render a validated silent cartoon project to MP4 using the bundled Pygame and FFmpeg renderer. Only call if user explicitly asks to render/export.","parameters":{"type":"object","properties":{"path":{"type":"string","description":"Relative project folder, for example videos/banana_story"}},"required":["path"]}}}
  108: ]
  109: 
  110: def safe_workspace_path(relative_path):
  111:     value = str(relative_path or ".").strip()
  112:     candidate = Path(value)
  113:     if candidate.is_absolute() or ":" in value:
  114:         raise ValueError("Use a relative path inside the workspace.")
  115:     resolved = (WORKSPACE / candidate).resolve()
  116:     try:
  117:         resolved.relative_to(WORKSPACE)
  118:     except ValueError:
  119:         raise ValueError("Access denied: path is outside the workspace.")
  120:     return resolved
-----
  144:             raise ValueError(f"Python syntax validation failed at line {exc.lineno or 'unknown'}: {exc.msg}. File was not saved.")
  145:     return content, repaired
  146: 
  147: def tool_list(args):
  148:     folder = safe_workspace_path(args.get("path", "."))
  149:     if not folder.is_dir():
  150:         return {"ok":False,"error":"Folder does not exist or is not a directory."}
  151:     entries=[]
  152:     for item in sorted(folder.iterdir(),key=lambda p:(not p.is_dir(),p.name.lower())):
  153:         try:
  154:             resolved=item.resolve()
  155:             resolved.relative_to(WORKSPACE)
  156:         except (ValueError,OSError):
  157:             continue
  158:         entries.append({"name":item.name,"path":resolved.relative_to(WORKSPACE).as_posix(),"type":"folder" if item.is_dir() else "file","size":item.stat().st_size if item.is_file() else None})
  159:     return {"ok":True,"folder":folder.relative_to(WORKSPACE).as_posix() or ".","entries":entries}
  160: 
  161: def tool_read(args):
  162:     path=safe_workspace_path(args.get("path",""))
  163:     if not path.is_file(): return {"ok":False,"error":"File not found."}
  164:     if path.stat().st_size>MAX_TEXT_BYTES:return {"ok":False,"error":"File exceeds 1 MB."}
  165:     try: content=path.read_text(encoding="utf-8")
  166:     except UnicodeDecodeError:return {"ok":False,"error":"File is not UTF-8 text."}
  167:     return {"ok":True,"path":path.relative_to(WORKSPACE).as_posix(),"content":content}
  168: 
  169: def tool_create(args):
  170:     path=safe_workspace_path(args.get("path",""))
  171:     if path.exists():return {"ok":False,"error":"File already exists. Ask the user before updating it."}
  172:     try: content,repaired=validate_python_source(path,args.get("content",""))
  173:     except ValueError as exc:return {"ok":False,"error":str(exc)}
  174:     path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content,encoding="utf-8")
  175:     rel=path.relative_to(WORKSPACE).as_posix();audit("create_file",rel,"success")
  176:     return {"ok":True,"created":rel,"bytes":path.stat().st_size,"python_syntax":"passed" if path.suffix.lower()==".py" else None,"newline_repair_applied":repaired}
  177: 
  178: def tool_update(args):
  179:     path=safe_workspace_path(args.get("path",""))
  180:     if not path.is_file():return {"ok":False,"error":"Existing file not found."}
  181:     try:path.read_text(encoding="utf-8")
  182:     except UnicodeDecodeError:return {"ok":False,"error":"File is not UTF-8 text."}
  183:     try:content,repaired=validate_python_source(path,args.get("content",""))
  184:     except ValueError as exc:return {"ok":False,"error":str(exc)}
  185:     path.write_text(content,encoding="utf-8");rel=path.relative_to(WORKSPACE).as_posix();audit("update_file",rel,"success")
  186:     return {"ok":True,"updated":rel,"bytes":path.stat().st_size,"python_syntax":"passed" if path.suffix.lower()==".py" else None,"newline_repair_applied":repaired}
  187: 
  188: def tool_mkdir(args):
  189:     path=safe_workspace_path(args.get("path",""))
  190:     if path.exists():return {"ok":False,"error":"A file or folder already exists at that path."}
  191:     path.mkdir(parents=True,exist_ok=False);rel=path.relative_to(WORKSPACE).as_posix();audit("create_directory",rel,"success")
  192:     return {"ok":True,"created_directory":rel}
  193: 
  194: def tool_check_one(args):
  195:     path=safe_workspace_path(args.get("path",""))
  196:     if not path.is_file() or path.suffix.lower()!=".py":return {"ok":False,"error":"Choose an existing .py file."}
  197:     try:compile(path.read_text(encoding="utf-8"),str(path),"exec");rel=path.relative_to(WORKSPACE).as_posix();audit("python_syntax_check",rel,"passed");return {"ok":True,"path":rel,"syntax":"passed","executed":False}
  198:     except SyntaxError as exc:return {"ok":False,"path":path.relative_to(WORKSPACE).as_posix(),"syntax":"failed","error":f"Line {exc.lineno}: {exc.msg}"}
  199:     except UnicodeDecodeError:return {"ok":False,"error":"File is not UTF-8 text."}
  200: 
  201: def tool_check_project(args):
  202:     folder=safe_workspace_path(args.get("path","."))
  203:     if not folder.is_dir():return {"ok":False,"error":"Project folder not found."}
  204:     checked=[];errors=[]
  205:     for path in folder.rglob("*.py"):
  206:         try:path.resolve().relative_to(WORKSPACE)
  207:         except ValueError:continue
  208:         if len(checked)+len(errors)>=MAX_PROJECT_FILES:return {"ok":False,"error":f"More than {MAX_PROJECT_FILES} Python files; narrow the folder."}
  209:         rel=path.relative_to(WORKSPACE).as_posix()
  210:         try:compile(path.read_text(encoding="utf-8"),str(path),"exec");checked.append(rel)
  211:         except SyntaxError as exc:errors.append({"path":rel,"line":exc.lineno,"error":exc.msg})
  212:         except (UnicodeDecodeError,OSError) as exc:errors.append({"path":rel,"error":str(exc)})
-----
  362:         "duration_minutes": round(total / 60, 2)
  363:     }
  364: 
  365: 
  366: def tool_create_cartoon(args):
  367:     name = str(args.get("name", "")).strip()
  368:     if not re.fullmatch(r"[A-Za-z0-9_-]{2,40}", name):
  369:         return {"ok": False, "error": "Project name must be 2-40 letters, numbers, underscore or hyphen."}
  370:     folder = safe_workspace_path("videos/" + name)
  371:     if folder.exists():
  372:         return {"ok": False, "error": "That video project already exists. Choose another name or ask before updating it."}
  373:     target = args.get("target_duration_seconds", 60)
  374:     try:
  375:         timeline, adjusted, source_count = expand_scene_timeline(args.get("scenes", []), target)
  376:     except ValueError as exc:
  377:         return {"ok": False, "error": str(exc)}
  378: 
  379:     project = {
  380:         "version": 1,
-----
  393:         meta = validate_video_data(project)
  394:     except ValueError as exc:
  395:         return {"ok": False, "error": str(exc)}
  396:     folder.mkdir(parents=True, exist_ok=False)
  397:     (folder / "project.json").write_text(json.dumps(project, indent=2, ensure_ascii=False), encoding="utf-8")
  398:     rel = folder.relative_to(WORKSPACE).as_posix()
  399:     audit("create_cartoon_project", rel, "success")
  400:     return {
  401:         "ok": True,
  402:         "project": rel,
  403:         "project_file": rel + "/project.json",
  404:         **meta,
  405:         "source_story_scenes": source_count,
  406:         "timeline_adjusted_to_selection": adjusted,
  407:         "rendered": False
  408:     }
  409: 
  410: def tool_validate_cartoon(args):
  411:     folder=safe_workspace_path(args.get("path",""))
  412:     project_file=folder/"project.json"
  413:     if not project_file.is_file():return {"ok":False,"error":"project.json not found in that project folder."}
  414:     try:
  415:         data=json.loads(project_file.read_text(encoding="utf-8"))
  416:         meta=validate_video_data(data)
  417:     except (ValueError,json.JSONDecodeError) as exc:return {"ok":False,"error":str(exc)}
  418:     audit("validate_cartoon_project",folder.relative_to(WORKSPACE).as_posix(),"passed")
  419:     return {"ok":True,"project":folder.relative_to(WORKSPACE).as_posix(),**meta,"rendered":False}
  420: 
  421: def tool_request_render(args):
  422:     folder=safe_workspace_path(args.get("path",""))
  423:     project_file=folder/"project.json"
  424:     if not project_file.is_file():return {"ok":False,"error":"project.json not found."}
  425:     try:
  426:         data=json.loads(project_file.read_text(encoding="utf-8"));meta=validate_video_data(data)
  427:     except Exception as exc:return {"ok":False,"error":"Project validation failed: "+str(exc)}
  428:     engine=ROOT/"tools"/"video_engine.py"
  429:     if not engine.is_file():return {"ok":False,"error":"Bundled video engine is missing. Reinstall the v0.7 update."}
  430:     approval_id=str(uuid.uuid4())
  431:     PENDING_APPROVALS[approval_id]={"kind":"video","path":folder.relative_to(WORKSPACE).as_posix()}
  432:     return {"ok":True,"approval_required":True,"approval_id":approval_id,"kind":"video","path":folder.relative_to(WORKSPACE).as_posix(),"command_preview":f'"{sys.executable}" "{engine}" --project "{project_file}"',"warning":f"Render {meta['duration_seconds']} seconds ({meta['duration_minutes']} min) at {meta['width']}x{meta['height']} / {meta['fps']} FPS. A 4-5 minute render can take several minutes depending on your PC. FFmpeg receives streamed frames; temporary PNG sequences are not stored."}
  433: 
  434: def tool_request_run(args):
  435:     path=safe_workspace_path(args.get("path",""))
  436:     if not path.is_file() or path.suffix.lower()!=".py":return {"ok":False,"error":"Only an existing .py file in the workspace can be run."}
  437:     approval_id=str(uuid.uuid4());rel=path.relative_to(WORKSPACE).as_posix()
  438:     PENDING_APPROVALS[approval_id]={"kind":"python","path":rel}
  439:     return {"ok":True,"approval_required":True,"approval_id":approval_id,"kind":"python","path":rel,"command_preview":f'"{sys.executable}" "{path}"',"warning":"Python runs with your Windows account permissions and may access files or network resources available to that account."}
  440: 
  441: TOOL_FUNCTIONS={
  442:     "list_workspace_files":tool_list,"read_workspace_file":tool_read,"create_workspace_file":tool_create,
  443:     "update_workspace_file":tool_update,"create_workspace_directory":tool_mkdir,
  444:     "check_python_syntax":tool_check_one,"check_python_project":tool_check_project,
  445:     "request_run_python":tool_request_run,"create_cartoon_project":tool_create_cartoon,
-----
  473:             actions.append(action)
  474:             messages.append({"role":"tool","tool_name":name,"content":json.dumps(tool_result,ensure_ascii=False)})
  475:     return "Tool-call limit reached. Completed actions are shown below; split the remaining work into a smaller request.",actions
  476: 
  477: def execute_approved(approval_id):
  478:     pending=PENDING_APPROVALS.pop(approval_id,None)
  479:     if not pending:return {"ok":False,"error":"Approval expired or already handled."}
  480:     kind=pending["kind"];rel=pending["path"];path=safe_workspace_path(rel)
  481:     if kind=="python":
  482:         command=[sys.executable,str(path)];cwd=str(WORKSPACE);timeout=MAX_RUN_SECONDS
  483:     elif kind=="video":
  484:         engine=ROOT/"tools"/"video_engine.py"
  485:         project_file=path/"project.json"
  486:         if not engine.is_file() or not project_file.is_file():return {"ok":False,"error":"Video engine or project.json is missing."}
  487:         command=[sys.executable,str(engine),"--project",str(project_file)];cwd=str(path);timeout=MAX_RENDER_SECONDS
  488:     else:return {"ok":False,"error":"Unknown approved operation."}
  489:     try:
  490:         result=subprocess.run(command,cwd=cwd,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=timeout,shell=False,check=False)
  491:         output={"ok":result.returncode==0,"path":rel,"returncode":result.returncode,"stdout":(result.stdout or "")[-MAX_OUTPUT_CHARS:],"stderr":(result.stderr or "")[-MAX_OUTPUT_CHARS:]}
  492:         audit("run_"+kind+"_approved",rel,f"returncode={result.returncode}")
  493:         return output
  494:     except subprocess.TimeoutExpired:
  495:         audit("run_"+kind+"_approved",rel,"timeout")
  496:         return {"ok":False,"path":rel,"timed_out":True,"stderr":f"Stopped after {timeout} seconds."}
  497:     except Exception as exc:
  498:         audit("run_"+kind+"_approved",rel,"error")
  499:         return {"ok":False,"path":rel,"error":str(exc)}
  500: 
  501: class Handler(BaseHTTPRequestHandler):
  502:     def send_data(self,status,data,kind="application/json; charset=utf-8"):
  503:         raw=data if isinstance(data,bytes) else data.encode("utf-8")
  504:         self.send_response(status);self.send_header("Content-Type",kind);self.send_header("Content-Length",str(len(raw)));self.send_header("Cache-Control","no-store");self.end_headers();self.wfile.write(raw)
-----
  518:             except Exception as exc:data["error"]=str(exc)
  519:             return self.send_json(200,data)
  520:         if parsed.path=="/api/files":
  521:             try:
  522:                 folder=safe_workspace_path(query.get("path",["."])[0])
  523:                 if not folder.is_dir():return self.send_json(404,{"error":"Folder not found."})
  524:                 entries=[]
  525:                 for item in sorted(folder.iterdir(),key=lambda p:(not p.is_dir(),p.name.lower())):
  526:                     try:resolved=item.resolve();resolved.relative_to(WORKSPACE)
  527:                     except (ValueError,OSError):continue
  528:                     entries.append({"name":item.name,"path":resolved.relative_to(WORKSPACE).as_posix(),"type":"folder" if item.is_dir() else "file","size":item.stat().st_size if item.is_file() else None})
  529:                 return self.send_json(200,{"path":folder.relative_to(WORKSPACE).as_posix() or ".","entries":entries})
  530:             except Exception as exc:return self.send_json(400,{"error":str(exc)})
  531:         if parsed.path=="/api/read":
  532:             try:
  533:                 path=safe_workspace_path(query.get("path",[""])[0])
  534:                 if not path.is_file():return self.send_json(404,{"error":"File not found."})
  535:                 if path.stat().st_size>MAX_TEXT_BYTES:return self.send_json(413,{"error":"File exceeds 1 MB."})
... excerpt truncated at 220 lines for this file ...
```

## autonomous_agent.py

- Path: H:\MASTER_AI_WORKSTATION\MASTER_AI_WORKSTATION\autonomous_agent.py
- Bytes: 24888
- Lines: 504
- SHA256: A1C10313AAC088C2DDD31389F2FA0129D289A49E573FE11586A4C93B7BEB290D

- Marker hits: 53
- Source excerpts (line-numbered):

```text
    2: MASTER AI WORKSTATION - Autonomous Core (v2.0 alpha)
    3: Project-scoped local coding agent. Uses Ollama; standard library only.
    4: """
    5: from __future__ import annotations
    6: import argparse, json, os, re, shutil, subprocess, sys, time, urllib.request, urllib.error
    7: from datetime import datetime, timezone
    8: from pathlib import Path
    9: 
   10: ROOT = Path(__file__).resolve().parent
   11: CFG_PATH = ROOT / "config.json"
   12: DEFAULT_CFG = {
   13:     "ollama_url": "http://127.0.0.1:11434",
   14:     "model": "qwen3:4b-instruct",
   15:     "fast_model": "qwen2.5-coder:3b",
   16:     "deep_model": "qwen3:4b-instruct",
-----
   26:     "allow_pytest": False,
   27:     "allow_npm_test": False
   28: }
   29: if not CFG_PATH.exists():
   30:     CFG_PATH.write_text(json.dumps(DEFAULT_CFG, indent=2), encoding="utf-8")
   31: CFG = {**DEFAULT_CFG, **json.loads(CFG_PATH.read_text(encoding="utf-8-sig"))}
   32: ACTIVE_MODE = str(CFG.get("default_mode", "fast")).strip().lower()
   33: if ACTIVE_MODE not in ("fast", "deep"):
   34:     ACTIVE_MODE = "fast"
   35: CFG["model"] = str(CFG.get(f"{ACTIVE_MODE}_model") or DEFAULT_CFG[f"{ACTIVE_MODE}_model"])
   36: CFG["num_ctx"] = int(CFG.get(f"{ACTIVE_MODE}_num_ctx", DEFAULT_CFG[f"{ACTIVE_MODE}_num_ctx"]))
   37: LOG_DIR = ROOT / "logs"; BACKUP_DIR = ROOT / "backups"
   38: LOG_DIR.mkdir(exist_ok=True); BACKUP_DIR.mkdir(exist_ok=True)
   39: AUDIT = LOG_DIR / "autonomous_actions.jsonl"
   40: 
   41: SYSTEM = """You are MASTER AI WORKSTATION, a local project development agent.
   42: Speak simply in the user's language. The selected project root is authoritative.
   43: Always use paths relative to that root. Never send absolute Windows paths to file tools.
   44: When the user names an exact file, call read_project_file directly; do not substitute a directory listing.
   45: For large files, use read_project_file with start_line and max_lines. Continue using next_start_line when has_more is true and the complete file is needed.
   46: Inspect actual source code before making technical claims. Never invent tool results or claim tests passed without evidence.
   47: Use tools for focused edits and configured validation only.
   48: Never delete files, install packages, use the network, access credentials, change Windows settings, execute arbitrary shell commands, or publish/upload anything.
   49: Before every file edit, the tool automatically creates a timestamped backup.
   50: If validation fails, report the observed error and propose a focused repair. Do not claim automatic rollback or successful repair unless verified.
   51: For tasks that cannot safely be completed with available tools, explain the limitation and required approval.
   52: """
   53: 
   54: def log(event, **fields):
   55:     row={"time":datetime.now(timezone.utc).isoformat(),"event":event,**fields}
   56:     with AUDIT.open("a",encoding="utf-8") as f: f.write(json.dumps(row,ensure_ascii=False)+"\n")
   57: 
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
   71: 
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
-----
   85:         raise ValueError("Access denied: requested project is outside configured project_roots.")
   86:     if not target.exists() or not target.is_dir(): raise ValueError(f"Project folder not found: {target}")
   87:     return target
   88: 
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
  102: 
  103: 
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
  114: 
  115: 
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
  127: 
  128: 
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
-----
  156:     return target
  157: 
  158: 
  159: 
  160: def tool_tree(args, project):
  161:     folder=safe_file(project,args.get("path","."))
  162:     if not folder.is_dir(): return {"ok":False,"error":"Folder not found"}
  163:     items=[]
  164:     for p in sorted(folder.rglob("*")):
  165:         if allowed_root_for(p, project) is None:
  166:             continue
  167:         if any(x in {".git","node_modules","__pycache__",".venv","venv"} for x in p.parts): continue
  168:         if len(items)>=250: break
  169:         items.append({"path":display_path(p, project),"type":"directory" if p.is_dir() else "file","bytes":p.stat().st_size if p.is_file() else None})
  170:     return {"ok":True,"root":str(project),"items":items}
  171: 
  172: def tool_read(args, project):
  173:     p=safe_file(project,args.get("path",""))
  174:     if not p.is_file(): return {"ok":False,"error":"File not found"}
  175:     try:
  176:         start_line=max(1,int(args.get("start_line",1)))
  177:         max_lines=max(1,min(int(args.get("max_lines",200)),400))
  178:         max_bytes=int(CFG.get("max_file_bytes",1000000))
  179:     except (TypeError,ValueError):
  180:         return {"ok":False,"error":"Invalid start_line, max_lines or file-size setting"}
  181: 
  182:     content_lines=[]
  183:     output_bytes=0
-----
  213:         "has_more":has_more,
  214:         "next_start_line":end_line+1 if has_more else None,
  215:         "content":"\n".join(content_lines)
  216:     }
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
  243: 
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
-----
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
  271: 
  272: TOOLS=[
  273:  {"type":"function","function":{"name":"list_project_files","description":"List project files. Ignore generated dependencies and git internals.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
  274:  {"type":"function","function":{"name":"read_project_file","description":"Read a UTF-8 project text file in chunks. start_line defaults to 1 and max_lines defaults to 200.","parameters":{"type":"object","properties":{"path":{"type":"string"},"start_line":{"type":"integer"},"max_lines":{"type":"integer"}},"required":["path"]}}},
  275:  {"type":"function","function":{"name":"write_project_file","description":"Create or update a project text file. Existing files are backed up automatically. Python and JSON syntax are validated before save.","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}}},
  276:  {"type":"function","function":{"name":"run_check","description":"Run only a configured safe validation: python_compile, node_check, pytest (if enabled), npm_test (if enabled).","parameters":{"type":"object","properties":{"kind":{"type":"string","enum":["python_compile","node_check","pytest","npm_test"]},"path":{"type":"string"}},"required":["kind","path"]}}}
  277: ]
  278: 
  279: def ollama(messages):
... excerpt truncated at 220 lines for this file ...
```

## safe_file_ops.py

- Path: H:\MASTER_AI_WORKSTATION\MASTER_AI_WORKSTATION\MASTER_CORE_V1\safety\safe_file_ops.py
- Bytes: 8464
- Lines: 212
- SHA256: F08D27028F624326F5ED287E27FE569C06028504B33621B0336F765693E2CEA8

- Marker hits: 15
- Source excerpts (line-numbered):

```text
   15: from typing import Optional
   16: 
   17: CORE_ROOT = Path(__file__).resolve().parents[1]
   18: WORKSPACE_ROOT = CORE_ROOT.parent.resolve()
   19: BACKUP_ROOT = (CORE_ROOT / "backups").resolve()
   20: APPROVAL_ROOT = (CORE_ROOT / "approvals").resolve()
   21: LOG_PATH = CORE_ROOT / "logs" / "safety_audit.jsonl"
   22: TICKET_TTL_SECONDS = 600
   23: 
   24: 
   25: class SafetyError(RuntimeError):
   26:     pass
   27: 
   28: 
   29: def sha256_bytes(data: bytes) -> str:
   30:     return hashlib.sha256(data).hexdigest()
   31: 
   32: 
   33: def sha256_file(path: Path) -> str:
   34:     h = hashlib.sha256()
   35:     with path.open("rb") as f:
   36:         for chunk in iter(lambda: f.read(1024 * 1024), b""):
   37:             h.update(chunk)
   38:     return h.hexdigest()
   39: 
   40: 
   41: def _inside(path: Path, root: Path) -> bool:
   42:     try:
   43:         path.resolve().relative_to(root.resolve())
-----
   45:     except (ValueError, OSError):
   46:         return False
   47: 
   48: 
   49: def safe_target(relative_path: str) -> Path:
   50:     """Resolve a workspace-relative target and reject path traversal."""
   51:     if not isinstance(relative_path, str) or not relative_path.strip():
   52:         raise SafetyError("A non-empty relative path is required.")
   53:     candidate = (WORKSPACE_ROOT / relative_path).resolve()
   54:     if candidate == WORKSPACE_ROOT or not _inside(candidate, WORKSPACE_ROOT):
   55:         raise SafetyError("Target must remain inside the workspace.")
   56:     if _inside(candidate, CORE_ROOT):
   57:         raise SafetyError("Phase 3 core files are protected from this generic writer.")
   58:     if candidate.exists() and candidate.is_dir():
   59:         raise SafetyError("Target is a directory, not a file.")
   60:     return candidate
   61: 
   62: 
   63: def _audit(event: str, details: dict) -> None:
   64:     LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
   65:     record = {
   66:         "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
   67:         "event": event,
   68:         "details": details,
   69:     }
   70:     with LOG_PATH.open("a", encoding="utf-8") as f:
   71:         f.write(json.dumps(record, ensure_ascii=False) + "\n")
   72: 
   73: 
   74: def create_approval_ticket(relative_path: str, proposed_content: str) -> dict:
   75:     """Create a short-lived ticket; this does NOT approve or apply the edit."""
   76:     target = safe_target(relative_path)
   77:     if not target.parent.exists():
   78:         raise SafetyError("Target parent directory must already exist.")
   79:     if not target.exists():
   80:         raise SafetyError("This initial version only supports edits to existing files.")
   81:     if not isinstance(proposed_content, str):
   82:         raise SafetyError("Proposed content must be text.")
   83: 
   84:     current_hash = sha256_file(target)
-----
   92:         "proposed_sha256": proposed_hash,
   93:         "proposed_content": proposed_content,
   94:         "status": "pending",
   95:     }
   96:     ticket_path = APPROVAL_ROOT / (ticket["ticket_id"] + ".json")
   97:     ticket_path.write_text(json.dumps(ticket, ensure_ascii=False, indent=2), encoding="utf-8")
   98:     _audit("approval_ticket_created", {
   99:         "ticket_id": ticket["ticket_id"],
  100:         "path": ticket["relative_path"],
  101:         "current_sha256": current_hash,
  102:         "proposed_sha256": proposed_hash,
  103:         "expires_at": ticket["expires_at"],
  104:     })
  105:     # Do not return proposed content to callers as part of the ticket summary.
  106:     return {k: v for k, v in ticket.items() if k != "proposed_content"}
  107: 
  108: 
  109: def reject_approval(ticket_id: str) -> dict:
  110:     ticket_path = APPROVAL_ROOT / (ticket_id + ".json")
  111:     if not _inside(ticket_path, APPROVAL_ROOT) or not ticket_path.is_file():
  112:         raise SafetyError("Approval ticket not found.")
  113:     ticket = json.loads(ticket_path.read_text(encoding="utf-8"))
  114:     if ticket.get("status") != "pending":
  115:         raise SafetyError("Ticket is no longer pending.")
  116:     ticket["status"] = "rejected"
  117:     ticket["proposed_content"] = ""
  118:     ticket_path.write_text(json.dumps(ticket, indent=2), encoding="utf-8")
  119:     _audit("approval_rejected", {"ticket_id": ticket_id, "path": ticket["relative_path"]})
  120:     return {"ok": True, "status": "rejected", "ticket_id": ticket_id}
  121: 
  122: 
  123: def approve_and_apply(ticket_id: str, typed_confirmation: str) -> dict:
  124:     """Apply only after caller supplies exact confirmation text APPROVE."""
  125:     if typed_confirmation != "APPROVE":
  126:         raise SafetyError("Explicit confirmation text must be exactly APPROVE.")
  127: 
  128:     ticket_path = APPROVAL_ROOT / (ticket_id + ".json")
  129:     if not _inside(ticket_path, APPROVAL_ROOT) or not ticket_path.is_file():
  130:         raise SafetyError("Approval ticket not found.")
  131:     ticket = json.loads(ticket_path.read_text(encoding="utf-8"))
  132: 
  133:     if ticket.get("status") != "pending":
  134:         raise SafetyError("Ticket is no longer pending.")
  135:     if time.time() > float(ticket.get("expires_at", 0)):
  136:         ticket["status"] = "expired"
  137:         ticket["proposed_content"] = ""
  138:         ticket_path.write_text(json.dumps(ticket, indent=2), encoding="utf-8")
  139:         _audit("approval_expired", {"ticket_id": ticket_id})
-----
  152: 
  153:     # Backup first, and verify it before changing the original.
  154:     stamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
  155:     backup_name = f"{target.name}.{stamp}.{ticket_id[:8]}.bak"
  156:     backup_path = BACKUP_ROOT / backup_name
  157:     BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
  158:     original_bytes = target.read_bytes()
  159:     backup_path.write_bytes(original_bytes)
  160:     if sha256_file(backup_path) != current_hash:
  161:         raise SafetyError("Backup verification failed; original was not changed.")
  162: 
  163:     # Recheck target immediately before atomic replacement.
  164:     if sha256_file(target) != current_hash:
  165:         raise SafetyError("Target changed during approval; original was not changed.")
  166: 
  167:     temp_name: Optional[str] = None
-----
```

## recovery_ops.py

- Path: H:\MASTER_AI_WORKSTATION\MASTER_AI_WORKSTATION\MASTER_CORE_V1\safety\recovery_ops.py
- Bytes: 10036
- Lines: 259
- SHA256: D9C5C11A76CFFD88EA71295472B5673CE377A93A6B107213F9A35673E3A7082A

- Marker hits: 6
- Source excerpts (line-numbered):

```text
   51:         raise RecoveryError("Ticket must be successfully applied before validation rollback.")
   52:     return ticket
   53: 
   54: 
   55: def _verified_backup(ticket: dict, applied: dict) -> Path:
   56:     backup_value = applied.get("backup")
   57:     if not isinstance(backup_value, str) or not backup_value.strip():
   58:         raise RecoveryError("Approved-write result did not provide a backup path.")
   59:     backup = Path(backup_value).resolve()
   60:     if not _contained(backup, _sfo.BACKUP_ROOT) or not backup.is_file():
   61:         raise RecoveryError("Backup is missing or is outside the protected backup directory.")
   62:     expected_original_hash = ticket.get("current_sha256")
   63:     actual_backup_hash = _sfo.sha256_file(backup)
   64:     if not expected_original_hash or actual_backup_hash != expected_original_hash:
   65:         raise RecoveryError("Backup SHA256 does not match the ticket's original file hash.")
   66:     return backup
   67: 
   68: 
   69: def _restore_verified_backup(
   70:     relative_path: str,
   71:     backup: Path,
   72:     expected_current_hash: str,
   73:     expected_backup_hash: str,
   74: ) -> dict:
   75:     target = _sfo.safe_target(relative_path)
   76:     if not target.is_file():
   77:         raise RecoveryError("Rollback target no longer exists.")
   78:     if _sfo.sha256_file(backup) != expected_backup_hash:
   79:         raise RecoveryError("Backup changed after verification; rollback refused.")
-----
  130:             except OSError:
  131:                 pass
  132: 
  133: 
  134: def approve_apply_and_validate(
  135:     ticket_id: str,
  136:     typed_confirmation: str,
  137:     validator: Callable[[Path], bool],
  138: ) -> dict:
  139:     """Apply one approved ticket, validate the result, and roll back on failure.
  140: 
  141:     The validator receives the edited Path and must return exactly True.
  142:     False or an exception triggers a guarded restore from the verified backup.
  143:     If the target changed after the edit, rollback is refused and the backup
  144:     remains available for manual recovery.
-----
  193:             backup=backup,
  194:             expected_current_hash=expected_applied_hash,
  195:             expected_backup_hash=ticket["current_sha256"],
  196:         )
  197:         _sfo._audit("automatic_rollback_completed", {
  198:             "ticket_id": ticket_id,
  199:             "path": relative_path,
  200:             "backup": str(backup),
  201:             "restored_sha256": restored["restored_sha256"],
  202:             "validation_error": validation_error,
  203:         })
  204:         return {
  205:             "ok": False,
  206:             "status": "rolled_back",
  207:             "ticket_id": ticket_id,
-----
  220:             "recovery_error": f"{type(exc).__name__}: {exc}",
  221:         })
  222:         return {
  223:             "ok": False,
  224:             "status": "recovery_required",
  225:             "ticket_id": ticket_id,
  226:             "path": relative_path,
  227:             "backup": str(backup),
  228:             "validation_passed": False,
  229:             "validation_error": validation_error,
  230:             "recovery_error": f"{type(exc).__name__}: {exc}",
  231:         }
  232: 
  233: 
  234: def restore_verified_backup(
  235:     relative_path: str,
  236:     backup_path: str,
  237:     expected_current_sha256: str,
  238:     expected_backup_sha256: str,
  239: ) -> dict:
  240:     """Manually request a guarded restore using both caller-supplied hashes."""
  241:     if not isinstance(backup_path, str) or not backup_path.strip():
  242:         raise RecoveryError("A backup path is required.")
  243:     backup = Path(backup_path).resolve()
  244:     if not _contained(backup, _sfo.BACKUP_ROOT) or not backup.is_file():
-----
```

## Integration safety notes

- This report is a static snapshot, not a runtime security certification.
- The next integration patch must preserve original files with timestamped backups.
- API write paths must use the approval + backup + validation + rollback flow.
- Dashboard approval must bind to the exact target and proposed content hashes.
- No delete, bulk edit, install, publish, or external network action is authorized by this preflight.

