"""Export JSON Schemas from contracts/artifacts.py.

Usage (from mvp/):
    uv run python -m contracts.export_schemas
    cd web && npm run gen:types      # regenerates web/src/types/contracts.ts from contracts/schemas/_bundle.json
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from contracts import artifacts as a

OUT = Path(__file__).parent / "schemas"

EXPORTED: list[type[BaseModel]] = [
    a.LabeledValue,
    a.Assumption,
    a.Project,
    a.BriefArtifact,
    a.DesignArtifact,
    a.SpecArtifact,
    a.DFMArtifact,
    a.CostsArtifact,
    a.ProductionPlanArtifact,
    a.MatchingArtifact,
    a.NegotiationArtifact,
    a.ToolingArtifact,
    a.QCArtifact,
    a.LogisticsArtifact,
    a.FinancingArtifact,
    a.BrandArtifact,
    a.FactoryPack,
    a.Factory,
    a.CapacityProfile,
    a.RegisterFactoryRequest,
    a.AutorunStatus,
    a.RFQ,
    a.Quote,
    a.NegotiationTurn,
    a.Milestone,
    a.RFQWithQuotes,
    a.CreateProjectRequest,
    a.RunStageRequest,
    a.UpdateStageRequest,
    a.StageResult,
    a.StageSummary,
    a.ProjectDetail,
    a.AutorunResult,
    a.ResetResult,
    a.HealthResponse,
    a.ErrorResponse,
]


def bundle_model() -> type[BaseModel]:
    """One root model referencing every exported model, so TS generation emits them all."""
    from pydantic import create_model

    fields = {m.__name__: (m, ...) for m in EXPORTED}
    fields["Label"] = (a.Label, ...)
    fields["StageStatus"] = (a.StageStatus, ...)
    fields["ProcessType"] = (a.ProcessType, ...)
    return create_model("ContractsBundle", **fields)  # type: ignore[call-overload]


def _clean_for_ts(node: object, is_def_root: bool = False) -> object:
    """Drop keys that make json-schema-to-typescript emit duplicate types (LabeledValue1, Label2...):
    siblings of $ref and property-level titles. Definition-level titles are kept (they name the types)."""
    if isinstance(node, list):
        return [_clean_for_ts(x) for x in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        return {"$ref": node["$ref"]}
    out = {}
    for k, v in node.items():
        if k == "title" and not is_def_root:
            continue
        if k in ("$defs", "properties"):
            out[k] = {name: _clean_for_ts(sub, is_def_root=(k == "$defs")) for name, sub in v.items()}
        else:
            out[k] = _clean_for_ts(v)
    return out


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.json"):
        old.unlink()
    for m in EXPORTED:
        (OUT / f"{m.__name__}.json").write_text(json.dumps(m.model_json_schema(), indent=2) + "\n")
    bundle = _clean_for_ts(bundle_model().model_json_schema(mode="serialization"), is_def_root=True)
    (OUT / "_bundle.json").write_text(json.dumps(bundle, indent=2) + "\n")
    print(f"wrote {len(EXPORTED) + 1} schemas to {OUT}")


if __name__ == "__main__":
    main()
