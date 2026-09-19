#!/usr/bin/env python3
"""Concept Packager: goal-conditioned knowledge compilation + reconstruction testing."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests

API_KEY = ""  # Prefer OPENROUTER_API_KEY; this remains as a paste-in fallback.
API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "nex-agi/nex-n2.5-mini:free"
MAX_TOKENS, TIMEOUT, RETRIES = 8192, 120, 3
FRONTIER = (2.0, 4.0, 6.0, 8.0, 10.0, 12.0)
GOALS = {
    "solve-problems": "Prioritize procedures, equations, decision rules, constraints, inputs/outputs, failure conditions, edge cases.",
    "teach": "Prioritize definitions, prerequisites, causal relationships, intuition, examples, contrasts, misconceptions.",
    "retain": "Prioritize conceptual skeleton, retrieval cues, critical relationships, prerequisite chains, memorable anchors, strategic redundancy.",
    "reference": "Prioritize definitions, formulas, properties, tables/lists, constraints, lookup information, clear categorization.",
}
SESSION = requests.Session()

try:
    import tiktoken  # type: ignore

    ENCODER = tiktoken.get_encoding("cl100k_base")
except Exception:
    ENCODER = None


def obj(properties: dict[str, Any]) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


S = {"type": "string"}
N = {"type": "number", "minimum": 0, "maximum": 100}
I = {"type": "integer", "minimum": 1, "maximum": 5}
SS = {"type": "array", "items": S}
IR_SCHEMA = obj({
    "title": S,
    "scope": S,
    "concepts": {"type": "array", "items": obj({
        "id": S, "name": S, "type": S, "content": S, "importance": I,
        "components": SS, "equations": SS, "examples": SS, "misconceptions": SS, "retrieval_cues": SS,
    })},
    "relationships": {"type": "array", "items": obj({
        "source": S, "type": S, "target": S, "description": S, "importance": I,
    })},
    "constraints": {"type": "array", "items": obj({
        "concept_id": S, "kind": S, "condition": S, "importance": I,
    })},
    "procedures": {"type": "array", "items": obj({
        "id": S, "name": S, "steps": SS, "inputs": SS, "outputs": SS,
        "failure_conditions": SS, "importance": I,
    })},
})
JUDGE_SCHEMA = obj({
    "concept_preservation": N,
    "relationship_preservation": N,
    "constraint_preservation": N,
    "procedure_preservation": N,
    "reconstruction_score": N,
    "missing_concepts": SS,
    "missing_relationships": SS,
    "missing_constraints": SS,
    "missing_procedures": SS,
    "unsupported_additions": SS,
    "notes": S,
})

IR_SYSTEM = """Extract a faithful Knowledge IR from the supplied source before compression.
Use only source-supported information. Atomize distinct knowledge, explicitly type relationships,
preserve assumptions/boundaries/exceptions/failure conditions, and separate ordered procedures.
Importance: 5=load-bearing, 1=peripheral. IDs: short snake_case. Required top-level keys are
 title, scope, concepts, relationships, constraints, procedures. Return JSON only."""

MERGE_SYSTEM = """Merge Knowledge IR fragments into one faithful global IR. Deduplicate only
semantic duplicates, repair IDs/references, retain load-bearing concepts/relationships/constraints/
procedures, and add no outside knowledge. Return JSON only."""

PACKAGE_SYSTEM = """Compile the supplied Knowledge IR into a compact Markdown Concept Package.
The IR is the only factual authority. Preserve the minimum structure needed to reconstruct and use
important knowledge for the stated goal. Preserve critical relationships, assumptions, exceptions,
and failure conditions. Prefer equations, relational notation, pseudo-code, generative rules, and
dense fragments. Merge redundancy only when meaning remains reconstructable. Output only Markdown."""

RECONSTRUCT_SYSTEM = """You receive ONLY a compressed Concept Package. Reconstruct every important
concept, relationship, constraint, and procedure supported by it. Do not use outside knowledge or
fill gaps. Return the same Knowledge IR shape used by Concept Packager, as JSON only."""

JUDGE_SYSTEM = """Compare ORIGINAL and RECONSTRUCTED Knowledge IR semantically, not by wording.
Score 0-100 for concept, relationship, constraint, and procedure preservation plus holistic
reconstruction. Weight important items more heavily. Do not reward invented knowledge. Return JSON only."""

BASELINES = {
    "Standard Summary": "Summarize the source accurately and concisely in ordinary prose. Preserve main ideas; add no outside knowledge. Output only the summary.",
    "Detailed LLM Notes": "Create detailed study notes preserving key definitions, mechanisms, relationships, constraints, procedures, equations, and useful examples. Add no outside knowledge.",
}


def eprint(*args: Any) -> None:
    print(*args, file=sys.stderr)


def tokens(text: str) -> int:
    if ENCODER:
        return len(ENCODER.encode(text))
    return max(1, int(len(re.findall(r"\w+|[^\w\s]", text)) * 1.05))


def budget(source: str, ratio: float) -> int:
    if ratio <= 1:
        raise ValueError("Compression ratio must be > 1")
    n = tokens(source)
    return max(64, min(int(n / ratio), int(n * 0.9)))


def split_text(text: str, limit: int = 12000) -> list[str]:
    if tokens(text) <= limit:
        return [text]
    chunks, current, size = [], [], 0
    for paragraph in filter(None, (p.strip() for p in re.split(r"\n\s*\n", text))):
        n = tokens(paragraph)
        if n > limit:
            if current:
                chunks.append("\n\n".join(current)); current, size = [], 0
            width = max(4000, limit * 4)
            chunks.extend(paragraph[i:i + width] for i in range(0, len(paragraph), width))
        elif current and size + n > limit:
            chunks.append("\n\n".join(current)); current, size = [paragraph], n
        else:
            current.append(paragraph); size += n
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def read_source(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.suffix.lower() != ".pdf":
        return path.read_text(encoding="utf-8", errors="replace")
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError as exc:
        raise RuntimeError("PDF input requires pypdf: pip install pypdf") from exc
    text = "\n\n".join((p.extract_text() or "").strip() for p in PdfReader(str(path)).pages).strip()
    if not text:
        raise RuntimeError("PDF contains no extractable text; scanned PDFs need OCR first.")
    return text


def parse_json(text: str) -> dict[str, Any]:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text):
        try:
            value, _ = decoder.raw_decode(text[match.start():])
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            continue
    raise ValueError("Model did not return valid JSON")


def call_llm(
    system: str,
    user: str,
    *,
    api_key: str,
    model: str,
    max_tokens: int = MAX_TOKENS,
    schema: dict[str, Any] | None = None,
    schema_name: str = "response",
) -> str | dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "max_tokens": max_tokens,
        "temperature": 0,
    }
    if schema:
        payload["response_format"] = {"type": "json_schema", "json_schema": {"name": schema_name, "strict": True, "schema": schema}}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    for attempt in range(RETRIES + 1):
        try:
            started = time.time()
            response = SESSION.post(API_URL, headers=headers, json=payload, timeout=TIMEOUT)
            if response.status_code == 400 and schema and "response_format" in payload:
                eprint("  Structured output unsupported; falling back to prompt-only JSON.")
                payload.pop("response_format")
                continue
            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                if isinstance(content, list):
                    content = "\n".join(x.get("text", "") if isinstance(x, dict) else str(x) for x in content)
                text = str(content).strip()
                eprint(f"  {model}: {time.time() - started:.1f}s")
                return parse_json(text) if schema else text
            error = RuntimeError(f"OpenRouter HTTP {response.status_code}: {response.text[:800]}")
            if response.status_code not in {408, 409, 425, 429, 500, 502, 503, 504} or attempt == RETRIES:
                raise error
        except (requests.RequestException, KeyError, IndexError, TypeError, ValueError) as exc:
            error = exc
            if attempt == RETRIES:
                raise RuntimeError(f"OpenRouter request failed: {exc}") from exc
        delay = min(8, 2 ** attempt)
        eprint(f"  Request failed; retrying in {delay}s...")
        time.sleep(delay)
    raise RuntimeError(f"OpenRouter request failed: {error}")


def clean_ir(ir: dict[str, Any]) -> dict[str, Any]:
    """Minimal shape guard; structured output handles field-level validation."""
    return {
        "title": str(ir.get("title", "Untitled source")),
        "scope": str(ir.get("scope", "")),
        **{key: value if isinstance((value := ir.get(key)), list) else []
           for key in ("concepts", "relationships", "constraints", "procedures")},
    }


def extract_ir(source: str, api_key: str, model: str) -> dict[str, Any]:
    chunks = split_text(source)
    eprint(f"[1/3] Structural extraction: {len(chunks)} chunk(s)")
    partials = [clean_ir(call_llm(
        IR_SYSTEM, f"SOURCE CHUNK {i}/{len(chunks)}:\n\n{chunk}", api_key=api_key, model=model,
        schema=IR_SCHEMA, schema_name="knowledge_ir",
    )) for i, chunk in enumerate(chunks, 1)]
    if len(partials) == 1:
        return partials[0]
    eprint("  Merging chunk IRs...")
    return clean_ir(call_llm(
        MERGE_SYSTEM, json.dumps(partials, ensure_ascii=False), api_key=api_key, model=model,
        schema=IR_SCHEMA, schema_name="merged_knowledge_ir",
    ))


def compile_package(ir: dict[str, Any], source: str, goal: str, ratio: float, api_key: str, model: str) -> str:
    target = budget(source, ratio)
    eprint(f"[2/3] Adaptive compilation: {goal}, target≈{ratio:g}x, budget≈{target:,} tokens")
    prompt = (
        f"GOAL: {goal}\nPRIORITIES: {GOALS[goal]}\nTARGET: <= {target} tokens (~{ratio:g}x).\n\n"
        f"KNOWLEDGE IR:\n{json.dumps(ir, ensure_ascii=False, separators=(',', ':'))}"
    )
    cap = min(MAX_TOKENS, max(256, int(target * 1.35)))
    package = str(call_llm(PACKAGE_SYSTEM, prompt, api_key=api_key, model=model, max_tokens=cap)).strip()
    if tokens(package) > max(target + 40, int(target * 1.15)):
        eprint("  Package exceeded budget; recompiling once.")
        package = str(call_llm(
            PACKAGE_SYSTEM, prompt + "\nHARD LIMIT: fit within the target. Preserve high-importance structure first.",
            api_key=api_key, model=model, max_tokens=min(MAX_TOKENS, max(192, int(target * 1.1))),
        )).strip()
    return package


def reconstruct(package: str, api_key: str, judge_model: str) -> dict[str, Any]:
    return clean_ir(call_llm(
        RECONSTRUCT_SYSTEM, f"CONCEPT PACKAGE:\n\n{package}", api_key=api_key, model=judge_model,
        schema=IR_SCHEMA, schema_name="reconstructed_ir",
    ))


def evaluate(source: str, original: dict[str, Any], package: str, api_key: str, judge_model: str, label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    eprint(f"[3/3] Reconstructability evaluation: {label}")
    rebuilt = reconstruct(package, api_key, judge_model)
    judged = call_llm(
        JUDGE_SYSTEM,
        "ORIGINAL:\n" + json.dumps(original, ensure_ascii=False, separators=(",", ":"))
        + "\n\nRECONSTRUCTED:\n" + json.dumps(rebuilt, ensure_ascii=False, separators=(",", ":")),
        api_key=api_key, model=judge_model, max_tokens=4096, schema=JUDGE_SCHEMA, schema_name="evaluation",
    )
    score_keys = ("concept_preservation", "relationship_preservation", "constraint_preservation", "procedure_preservation", "reconstruction_score")
    scores = {k: max(0.0, min(100.0, float(judged.get(k, 0)))) for k in score_keys}
    preservation = .4 * scores["concept_preservation"] + .3 * scores["relationship_preservation"] + .2 * scores["constraint_preservation"] + .1 * scores["procedure_preservation"]
    reconstruction = scores["reconstruction_score"]
    quality = 0 if not preservation or not reconstruction else 2 * preservation * reconstruction / (preservation + reconstruction)
    source_n, package_n = tokens(source), tokens(package)
    report = {
        "label": label, "source_tokens": source_n, "package_tokens": package_n,
        "compression_ratio": round(source_n / max(package_n, 1), 3), **{k: round(v, 1) for k, v in scores.items()},
        "preservation_score": round(preservation, 1), "quality_score": round(quality, 1),
        **{k: judged.get(k, []) for k in ("missing_concepts", "missing_relationships", "missing_constraints", "missing_procedures", "unsupported_additions")},
        "notes": judged.get("notes", ""),
        "original_ir_counts": {k: len(original.get(k, [])) for k in ("concepts", "relationships", "constraints", "procedures")},
        "reconstructed_ir_counts": {k: len(rebuilt.get(k, [])) for k in ("concepts", "relationships", "constraints", "procedures")},
    }
    return report, rebuilt


def generate_baselines(source: str, ratio: float, api_key: str, model: str) -> dict[str, str]:
    eprint("[benchmark] Generating baselines...")
    source_n = tokens(source)
    budgets = {"Standard Summary": max(120, int(source_n / (ratio * 1.3))), "Detailed LLM Notes": max(180, int(source_n / (ratio * .8)))}
    return {name: str(call_llm(
        system, f"TARGET: approximately {budgets[name]} tokens maximum.\n\nSOURCE:\n{source}",
        api_key=api_key, model=model, max_tokens=min(MAX_TOKENS, max(256, int(budgets[name] * 1.35))),
    )).strip() for name, system in BASELINES.items()}


def compression_frontier(source: str, ir: dict[str, Any], goal: str, ratios: tuple[float, ...], api_key: str, model: str, judge_model: str, preserve_min: float, reconstruct_min: float) -> tuple[list[dict[str, Any]], dict[str, str], dict[str, Any] | None]:
    eprint("[benchmark] Searching compression frontier...")
    rows, packages = [], {}
    for ratio in ratios:
        eprint(f"  Candidate {ratio:g}x")
        package = compile_package(ir, source, goal, ratio, api_key, model)
        report, _ = evaluate(source, ir, package, api_key, judge_model, f"Frontier {ratio:g}x")
        row = {
            "target_compression": ratio, "actual_compression": report["compression_ratio"], "package_tokens": report["package_tokens"],
            "preservation_score": report["preservation_score"], "reconstruction_score": report["reconstruction_score"], "quality_score": report["quality_score"],
            "meets_threshold": report["preservation_score"] >= preserve_min and report["reconstruction_score"] >= reconstruct_min,
        }
        rows.append(row); packages[f"{ratio:g}"] = package
    viable = [r for r in rows if r["meets_threshold"]]
    return rows, packages, max(viable, key=lambda r: r["actual_compression"]) if viable else None


def print_report(report: dict[str, Any]) -> None:
    print("\nPACKAGE EVALUATION")
    for label, key, suffix in (
        ("Source tokens", "source_tokens", ""), ("Package tokens", "package_tokens", ""), ("Compression", "compression_ratio", "x"),
        ("Concept preservation", "concept_preservation", "%"), ("Relationship preservation", "relationship_preservation", "%"),
        ("Constraint preservation", "constraint_preservation", "%"), ("Procedure preservation", "procedure_preservation", "%"),
        ("Reconstruction", "reconstruction_score", "%"), ("Quality", "quality_score", "%"),
    ):
        print(f"{label:<26} {report[key]}{suffix}")


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def save_artifacts(out: Path, package: str, ir: dict[str, Any], metadata: dict[str, Any], evaluation: dict[str, Any] | None = None, rebuilt: dict[str, Any] | None = None, baselines: dict[str, str] | None = None, baseline_reports: list[dict[str, Any]] | None = None, frontier: list[dict[str, Any]] | None = None, frontier_packages: dict[str, str] | None = None, selected: dict[str, Any] | None = None) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "concept_package.md").write_text(package.rstrip() + "\n", encoding="utf-8")
    for name, data in {"knowledge_ir.json": ir, "run_metadata.json": metadata, "evaluation.json": evaluation, "reconstructed_ir.json": rebuilt, "baseline_comparison.json": baseline_reports}.items():
        if data is not None:
            write_json(out / name, data)
    if baselines:
        folder = out / "baselines"; folder.mkdir(exist_ok=True)
        for name, text in baselines.items():
            filename = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") + ".md"
            (folder / filename).write_text(text.rstrip() + "\n", encoding="utf-8")
    if frontier is not None:
        folder = out / "frontier"; folder.mkdir(exist_ok=True)
        write_json(folder / "frontier.json", frontier); write_json(folder / "selected.json", selected)
        for ratio, text in (frontier_packages or {}).items():
            (folder / f"package_{ratio.replace('.', '_')}x.md").write_text(text.rstrip() + "\n", encoding="utf-8")
        if selected and frontier_packages:
            text = frontier_packages.get(f"{selected['target_compression']:g}")
            if text:
                (folder / "selected_package.md").write_text(text.rstrip() + "\n", encoding="utf-8")


def parse_ratios(value: str) -> tuple[float, ...]:
    try:
        ratios = tuple(float(x.strip().lower().rstrip("x")) for x in value.split(",") if x.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Ratios must be comma-separated numbers") from exc
    if not ratios or any(x <= 1 for x in ratios):
        raise argparse.ArgumentTypeError("Every frontier ratio must be > 1")
    return ratios


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Compile learning material into a reconstructable Concept Package.")
    p.add_argument("source", type=Path)
    p.add_argument("--goal", choices=GOALS, default="retain")
    p.add_argument("--compression", type=float, default=4.0)
    p.add_argument("--model", default=os.getenv("CONCEPT_PACKAGER_MODEL", DEFAULT_MODEL))
    p.add_argument("--judge-model", default=os.getenv("CONCEPT_PACKAGER_JUDGE_MODEL"))
    p.add_argument("--api-key", default=None)
    p.add_argument("--no-evaluate", action="store_true")
    p.add_argument("--baselines", action="store_true")
    p.add_argument("--frontier", action="store_true")
    p.add_argument("--benchmark", action="store_true", help="Enable baselines + frontier")
    p.add_argument("--frontier-ratios", type=parse_ratios, default=FRONTIER)
    p.add_argument("--preservation-threshold", type=float, default=90.0)
    p.add_argument("--reconstruction-threshold", type=float, default=90.0)
    p.add_argument("--output-dir", type=Path)
    p.add_argument("--no-save", action="store_true")
    return p


def run(args: argparse.Namespace) -> None:
    if args.compression <= 1:
        raise ValueError("--compression must be > 1")
    for name in ("preservation_threshold", "reconstruction_threshold"):
        if not 0 <= getattr(args, name) <= 100:
            raise ValueError(f"--{name.replace('_', '-')} must be 0-100")
    if args.no_evaluate and (args.baselines or args.frontier or args.benchmark):
        raise ValueError("Benchmarking requires evaluation")

    api_key = (args.api_key or os.getenv("OPENROUTER_API_KEY") or API_KEY).strip()
    if not api_key:
        raise RuntimeError("Set OPENROUTER_API_KEY, pass --api-key, or fill API_KEY at the top of the file.")
    judge_model = args.judge_model or args.model
    source_path = args.source.expanduser()
    source = read_source(source_path)
    eprint(f"Loaded {tokens(source):,} tokens from {source_path.name}")

    ir = extract_ir(source, api_key, args.model)
    package = compile_package(ir, source, args.goal, args.compression, api_key, args.model)
    print("\n--- CONCEPT PACKAGE ---\n\n" + package)

    evaluation = rebuilt = None
    if not args.no_evaluate:
        evaluation, rebuilt = evaluate(source, ir, package, api_key, judge_model, "Concept Package")
        print_report(evaluation)

    baseline_outputs = None
    baseline_reports = None
    if args.baselines or args.benchmark:
        baseline_outputs = generate_baselines(source, args.compression, api_key, args.model)
        baseline_reports = [evaluation]
        for name, text in baseline_outputs.items():
            report, _ = evaluate(source, ir, text, api_key, judge_model, name)
            baseline_reports.append(report)
        print("\nBASELINES")
        for report in baseline_reports:
            print(f"{report['label']:<20} {report['compression_ratio']:>6.2f}x  preserve={report['preservation_score']:>5.1f}%  reconstruct={report['reconstruction_score']:>5.1f}%")

    frontier_rows = frontier_packages = selected = None
    if args.frontier or args.benchmark:
        frontier_rows, frontier_packages, selected = compression_frontier(
            source, ir, args.goal, args.frontier_ratios, api_key, args.model, judge_model,
            args.preservation_threshold, args.reconstruction_threshold,
        )
        print("\nCOMPRESSION FRONTIER")
        for row in frontier_rows:
            print(f"{row['target_compression']:>4g}x -> {row['actual_compression']:>6.2f}x  preserve={row['preservation_score']:>5.1f}%  reconstruct={row['reconstruction_score']:>5.1f}%  {'PASS' if row['meets_threshold'] else 'FAIL'}")
        print("Selected:", f"{selected['target_compression']:g}x" if selected else "none")

    out = args.output_dir or source_path.with_name(source_path.stem + "_concept_packager")
    if not args.no_save:
        metadata = {
            "source_file": str(source_path), "goal": args.goal, "requested_compression": args.compression,
            "model": args.model, "judge_model": judge_model, "source_tokens": tokens(source),
            "ir_counts": {k: len(ir[k]) for k in ("concepts", "relationships", "constraints", "procedures")},
        }
        save_artifacts(out, package, ir, metadata, evaluation, rebuilt, baseline_outputs, baseline_reports, frontier_rows, frontier_packages, selected)
        print(f"\nSaved artifacts to: {out}")


def main() -> int:
    try:
        run(parser().parse_args())
        return 0
    except KeyboardInterrupt:
        eprint("\nCancelled."); return 130
    except (RuntimeError, ValueError, OSError) as exc:
        eprint(f"Error: {exc}"); return 1


if __name__ == "__main__":
    raise SystemExit(main())
