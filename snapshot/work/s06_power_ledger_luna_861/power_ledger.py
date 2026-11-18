"""Account for a 1 W source using measured, disjoint outgoing-power channels.

The caller must establish the physical control surface, modal decomposition,
field provenance and absence of double counting. This calculator cannot infer
those facts from numbers and never grants a COMSOL validation gate.
"""
from __future__ import annotations

import json
import math
import re
from decimal import Decimal, localcontext
from pathlib import Path


CHANNELS = (
    "source_clipped",
    "source_return",
    "he11_subspace",
    "other_guided",
    "unclassified_downstream",
    "other_escape",
    "material_absorption",
)
CASES = {"LD974-WEDGE-BASE-001", "LD974-WEDGE-LAT1-001"}
G07A_NUMERIC_CLOSURE_LIMIT = Decimal("0.005")
NUMERIC_INPUT_REPRESENTATION = (
    "JSON_DECIMAL_TOKENS_PRESERVED; PYTHON_FLOAT_USES_SHORTEST_ROUNDTRIP_DECIMAL"
)


def _binary64(value: Decimal, label: str) -> float:
    numeric = float(value)
    if value != 0 and numeric == 0.0:
        raise ValueError(
            f"{label} is nonzero ({value}) but underflows binary64 to 0.0; refusing to report it as zero"
        )
    return numeric


def _decimal_number(value: object, label: str) -> tuple[Decimal, float]:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError(f"{label} must be a finite, nonnegative power in watts")
    exact = value if isinstance(value, Decimal) else Decimal(str(value))
    if not exact.is_finite() or exact < 0:
        raise ValueError(f"{label} must be a finite, nonnegative power in watts")
    numeric = _binary64(exact, label)
    if not math.isfinite(numeric):
        raise ValueError(f"{label} must be a finite, nonnegative power in watts")
    return exact, numeric


def _number(value: object, label: str) -> float:
    return _decimal_number(value, label)[1]


def _decimal_precision(values: list[Decimal]) -> int:
    nonzero = [value for value in values if value]
    if not nonzero:
        return 1
    min_exponent = min(value.as_tuple().exponent for value in nonzero)
    max_adjusted = max(value.adjusted() for value in nonzero)
    carry_digits = len(str(len(nonzero) - 1)) if len(nonzero) > 1 else 0
    return max(1, max_adjusted - min_exponent + 1 + carry_digits)


def _decimal_sum(values: list[Decimal]) -> Decimal:
    with localcontext() as context:
        context.prec = _decimal_precision(values)
        return sum(values, Decimal(0))


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", value):
        raise ValueError(f"{label} must be a SHA-256 hex digest")
    return value.lower()


def _wavelength(value: object, label: str) -> float:
    wave = _number(value, label)
    if not math.isclose(wave, 974e-9, rel_tol=0.0, abs_tol=1e-15):
        raise ValueError(f"{label} must declare the 974 nm case in meters")
    return wave


def _provenance(value: object) -> dict:
    fields = {"lambda_m", "model_sha256", "config_sha256", "source_field_sha256",
              "field_data_sha256", "study_tag", "dataset_tag", "solution_index"}
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError("provenance must include wavelength, model/config/source/field hashes and study/dataset/solution")
    result = dict(value)
    result["lambda_m"] = _wavelength(value["lambda_m"], "provenance.lambda_m")
    for key in ("model_sha256", "config_sha256", "source_field_sha256", "field_data_sha256"):
        result[key] = _digest(value[key], "provenance." + key)
    for key in ("study_tag", "dataset_tag"):
        if not isinstance(value[key], str) or not value[key].strip():
            raise ValueError("provenance." + key + " must be nonempty")
    if isinstance(value["solution_index"], bool) or not isinstance(value["solution_index"], int) or value["solution_index"] < 1:
        raise ValueError("provenance.solution_index must be a positive integer")
    return result


def _evidence(value: object, label: str, case_id: str) -> dict:
    if not isinstance(value, dict) or set(value) != {"artifact_sha256", "lambda_m", "case_id"}:
        raise ValueError(f"{label} needs a structured artifact SHA-256, wavelength and case")
    if value["case_id"] != case_id:
        raise ValueError(f"{label}: evidence belongs to a different case")
    return {"artifact_sha256": _digest(value["artifact_sha256"], label + ".artifact_sha256"),
            "lambda_m": _wavelength(value["lambda_m"], label + ".lambda_m"), "case_id": case_id}


def _measurement(item: object, label: str, case_id: str) -> dict:
    if not isinstance(item, dict) or set(item) != {"power_W", "reason", "evidence"}:
        raise ValueError(f"{label} requires exactly power_W, reason and evidence")
    value, reason, evidence = item["power_W"], item["reason"], item["evidence"]
    if value is None:
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"{label}: an unknown power needs a reason")
        reference = None if evidence is None else _evidence(evidence, label + ".evidence", case_id)
        return {"power_W": None, "power_W_decimal": None, "reason": reason, "evidence": reference}
    if reason is not None:
        raise ValueError(f"{label}: reason is reserved for unknown powers")
    reference = _evidence(evidence, label + ".evidence", case_id)
    exact, numeric = _decimal_number(value, label)
    return {"power_W": numeric, "power_W_decimal": str(exact), "reason": None, "evidence": reference}


def calculate_ledger(record: dict) -> dict:
    """Calculate a preliminary ledger; missing channels remain unknown.

    Each input channel is a non-overlapping amount of outgoing power. In
    particular, other_escape may include flux entering a PML, but never that
    same flux again as absorption or as a downstream/port contribution.
    The returned status remains NOT_ASSESSED until the source fields, spatial
    and modal partition, numerical evidence and independent review are checked.
    """
    if not isinstance(record, dict) or set(record) != {
        "case_id", "source_reference_W", "channels", "partition_evidence",
        "polarization_basis", "polarization_powers_W", "polarization_unavailable_reason", "provenance",
    }:
        raise ValueError("record has missing or unexpected fields")
    if record["case_id"] not in CASES:
        raise ValueError("case_id must be the frozen BASE or LAT1 case")
    case_id = record["case_id"]
    provenance = _provenance(record["provenance"])
    source_decimal, source = _decimal_number(record["source_reference_W"], "source_reference_W")
    if source_decimal != Decimal("1"):
        raise ValueError("source_reference_W must be the original normalized 1 W source")
    partition = _evidence(record["partition_evidence"], "partition_evidence", case_id)
    incoming = record["channels"]
    if not isinstance(incoming, dict) or set(incoming) != set(CHANNELS):
        raise ValueError("all named channels must be supplied, with null and reason if unknown")
    channels = {name: _measurement(incoming[name], name, case_id) for name in CHANNELS}

    pol = record["polarization_powers_W"]
    basis = record["polarization_basis"]
    pol_reason = record["polarization_unavailable_reason"]
    pol_result = None
    if pol is None:
        if basis is not None:
            raise ValueError("polarization_basis must be null when individual powers are unavailable")
        if not isinstance(pol_reason, str) or not pol_reason.strip():
            raise ValueError("unavailable individual polarization powers need a reason")
    else:
        if pol_reason is not None:
            raise ValueError("polarization_unavailable_reason must be null when components are supplied")
        if not isinstance(pol, dict) or set(pol) != {"x", "y"}:
            raise ValueError("polarization powers must contain x and y")
        if not isinstance(basis, dict) or set(basis) != {"label", "evidence"}:
            raise ValueError("individual powers require a labelled physical basis and evidence reference")
        if not isinstance(basis["label"], str) or not basis["label"].strip():
            raise ValueError("polarization basis label must be nonempty")
        basis = {"label": basis["label"], "evidence": _evidence(basis["evidence"], "polarization_basis", case_id)}
        pol_result = {name: _measurement(pol[name], "polarization_" + name, case_id) for name in ("x", "y")}
        values = [pol_result[name]["power_W"] for name in ("x", "y")]
        total = channels["he11_subspace"]["power_W"]
        if total is None and any(value is not None for value in values):
            raise ValueError("individual HE11 powers require the identified subspace power")
        if total is not None and any(
            value is not None and value > total
            and not math.isclose(value, total, rel_tol=1e-8, abs_tol=1e-12)
            for value in values
        ):
            raise ValueError("an individual HE11 polarization power exceeds the subspace power")
        if total is not None and all(value is not None for value in values):
            if not math.isclose(sum(values), total, rel_tol=1e-8, abs_tol=1e-12):
                raise ValueError("x/y powers do not sum to the HE11 subspace power")

    he11 = channels["he11_subspace"]["power_W"]
    he11_decimal_text = channels["he11_subspace"]["power_W_decimal"]
    he11_decimal = None if he11_decimal_text is None else Decimal(he11_decimal_text)
    eta = None if he11_decimal is None else _binary64(he11_decimal, "eta_he11")
    eta_decimal = he11_decimal
    eta_above_reference = None if eta_decimal is None else eta_decimal > Decimal("1")
    if eta_above_reference is None:
        eta_reference_status = "NOT_ASSESSED_HE11_POWER_UNKNOWN"
    elif eta_above_reference:
        eta_reference_status = "DECLARED_ABOVE_1W_PHYSICAL_AND_SOURCE_REVIEW_REQUIRED"
    else:
        eta_reference_status = "NOT_ABOVE_1W_NOT_A_PHYSICAL_GATE"
    eta_reference_reason = (
        "Declared HE11 power exceeds the original normalized 1 W forward reference; retain the declared value and review source/provenance and physical partition. This flag alone does not establish active gain or a real power partition."
        if eta_above_reference else None
    )
    polarization_efficiencies = {}
    for name in ("x", "y"):
        value = None if pol_result is None else pol_result[name]["power_W"]
        value_decimal_text = None if pol_result is None else pol_result[name]["power_W_decimal"]
        polarization_efficiencies[name] = {
            "eta": None if value is None else _binary64(
                Decimal(value_decimal_text), f"polarization_efficiencies.{name}.eta"
            ),
            "reason": (pol_reason if pol_result is None else pol_result[name]["reason"])
                      if value is None else None,
        }
    missing = [name for name, item in channels.items() if item["power_W"] is None]
    known = [name for name, item in channels.items() if item["power_W"] is not None]
    known_decimals = [Decimal(channels[name]["power_W_decimal"]) for name in known]
    partial_known_decimal = None if not known else _decimal_sum(known_decimals)
    channel_decimals = [Decimal(channels[name]["power_W_decimal"]) for name in CHANNELS if name not in missing]
    outgoing_decimal = None if missing else _decimal_sum(channel_decimals)
    residual_decimal = None if outgoing_decimal is None else _decimal_sum(
        [source_decimal, outgoing_decimal.copy_negate()]
    )
    closure_error_decimal = None if residual_decimal is None else residual_decimal.copy_abs()
    partial_known = None if partial_known_decimal is None else _binary64(
        partial_known_decimal, "partial_known_outgoing_sum_W"
    )
    outgoing = None if outgoing_decimal is None else _binary64(outgoing_decimal, "outgoing_sum_W")
    residual = None if residual_decimal is None else _binary64(residual_decimal, "signed_residual_W")
    closure_error = None if closure_error_decimal is None else _binary64(
        closure_error_decimal, "closure_relative_error"
    )
    equivalent_decimal = None
    equivalent = None
    if eta_decimal is not None:
        factor = Decimal("0.600")
        with localcontext() as context:
            context.prec = max(1, len(eta_decimal.as_tuple().digits) + len(factor.as_tuple().digits))
            equivalent_decimal = eta_decimal * factor
        equivalent = _binary64(equivalent_decimal, "equivalent_974nm_power_from_0_600W_W")
    return {
        "case_id": record["case_id"],
        "record_status": "DECLARED_INPUTS_UNVERIFIED_SOFTWARE_ARITHMETIC_ONLY",
        "provenance": provenance,
        "provenance_verification": "HASH_FORMAT_ONLY_BYTES_STUDY_AND_COMSOL_READBACK_NOT_VERIFIED",
        "wavelength_verification": "DECLARED_974_NM_NOT_INDEPENDENTLY_VERIFIED",
        "physical_partition_verification": "NOT_ASSESSED",
        "polarization_basis_verification": "NOT_ASSESSED" if pol_result is not None else "UNAVAILABLE",
        "source_reference_W": source,
        "source_reference_scope": "original forward source; not net power in the presence of reflection",
        "channels": channels,
        "partition_evidence": partition,
        "polarization_basis": basis,
        "polarization_powers_W": pol_result,
        "polarization_efficiencies": polarization_efficiencies,
        "polarization_unavailable_reason": pol_reason,
        "numeric_input_representation": NUMERIC_INPUT_REPRESENTATION,
        "source_reference_W_decimal": str(source_decimal),
        "eta_he11": eta,
        "eta_he11_decimal": None if eta_decimal is None else str(eta_decimal),
        "eta_he11_above_reference_power": eta_above_reference,
        "eta_he11_reference_power_status": eta_reference_status,
        "eta_he11_above_reference_power_reason": eta_reference_reason,
        "eta_he11_reason": channels["he11_subspace"]["reason"] if eta is None else None,
        "equivalent_974nm_power_from_0_600W_W": equivalent,
        "equivalent_974nm_power_from_0_600W_W_decimal": (
            None if equivalent_decimal is None else str(equivalent_decimal)
        ),
        "equivalent_power_reason": channels["he11_subspace"]["reason"] if eta is None else None,
        "equivalent_power_scope": "monochromatic equivalent only; not measured 974 nm or broadband power",
        "known_channels": known,
        "partial_known_outgoing_sum_W": partial_known,
        "partial_known_outgoing_sum_W_decimal": None if partial_known_decimal is None else str(partial_known_decimal),
        "partial_known_outgoing_sum_reason": None if known else "No channel power is available",
        "missing_channels": missing,
        "outgoing_sum_W": outgoing,
        "outgoing_sum_W_decimal": None if outgoing_decimal is None else str(outgoing_decimal),
        "signed_residual_W": residual,
        "signed_residual_W_decimal": None if residual_decimal is None else str(residual_decimal),
        "closure_relative_error": closure_error,
        "closure_relative_error_decimal": None if closure_error_decimal is None else str(closure_error_decimal),
        "numeric_closure_within_0_005": (
            None if closure_error_decimal is None
            else closure_error_decimal <= G07A_NUMERIC_CLOSURE_LIMIT
        ),
        "closure_unavailable_reason": None if not missing else "Missing channel powers: " + ", ".join(missing),
        "G07a_status": "NOT_ASSESSED_PHYSICAL_PARTITION_AND_REVIEW_REQUIRED",
        "pml_accounting": "numerical outflow only; never material absorption or duplicate port/PML flux",
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    result = calculate_ledger(json.loads(args.input.read_text(encoding="utf-8"), parse_float=Decimal))
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
