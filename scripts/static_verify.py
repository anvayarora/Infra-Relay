#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []

required = [
    "backend/app/__init__.py",
    "backend/app/engine.py",
    "backend/app/api/routes.py",
    "frontend/src/App.tsx",
    "frontend/src/pages/WorkflowBuilderPage.tsx",
    "automation/playbooks/component_update.yml",
    "docker-compose.yml",
]
for item in required:
    if not (ROOT / item).exists():
        errors.append(f"Missing required path: {item}")

for path in (ROOT / "backend").rglob("*.py"):
    try:
        ast.parse(path.read_text(), filename=str(path))
    except SyntaxError as exc:
        errors.append(f"Python syntax: {path.relative_to(ROOT)}: {exc}")

try:
    yaml.safe_load((ROOT / "docker-compose.yml").read_text())
except Exception as exc:
    errors.append(f"Compose YAML: {exc}")

source_root = ROOT / "frontend" / "src"
for path in source_root.rglob("*"):
    if path.suffix not in {".ts", ".tsx"}:
        continue
    text = path.read_text()
    for specifier in re.findall(r"from\s+['\"]([^'\"]+)['\"]", text):
        if specifier.startswith("@/"):
            base = source_root / specifier[2:]
        elif specifier.startswith("."):
            base = (path.parent / specifier).resolve()
        else:
            continue
        candidates = [Path(f"{base}{suffix}") for suffix in (".ts", ".tsx", ".js", ".jsx")]
        candidates += [base / "index.ts", base / "index.tsx"]
        if not any(candidate.exists() for candidate in candidates):
            errors.append(f"Missing local import in {path.relative_to(ROOT)}: {specifier}")

node_script = r'''
const fs=require('fs'),path=require('path'),ts=require('/opt/nvm/versions/node/v22.16.0/lib/node_modules/typescript');
const root=process.argv[1];let errors=[];
function walk(dir){for(const entry of fs.readdirSync(dir,{withFileTypes:true})){const p=path.join(dir,entry.name);if(entry.isDirectory())walk(p);else if(/\.tsx?$/.test(p)){const source=fs.readFileSync(p,'utf8');const result=ts.transpileModule(source,{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext},fileName:p,reportDiagnostics:true});for(const d of result.diagnostics||[])errors.push(p+': '+ts.flattenDiagnosticMessageText(d.messageText,' '));}}}
walk(root);if(errors.length){console.error(errors.join('\n'));process.exit(1)}
'''
try:
    subprocess.run(["node", "-e", node_script, str(source_root)], check=True, capture_output=True, text=True)
except Exception as exc:
    errors.append(f"TypeScript parsing failed: {exc}")

if errors:
    print("Static verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

summary = {
    "python_files": len(list((ROOT / "backend").rglob("*.py"))),
    "frontend_sources": len([p for p in source_root.rglob("*") if p.suffix in {".ts", ".tsx"}]),
    "automation_files": len(list((ROOT / "automation").rglob("*"))),
}
print("Static verification passed")
print(json.dumps(summary, indent=2))
