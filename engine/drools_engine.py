"""
engine/drools_engine.py
===============================================================================
BO MAY THUC THI LUAT DROOLS TREN PYTHON (APACHE KIE / RED HAT DROOLS ARCHITECTURE)
Do an Cuoi ky Mon He thong Ho tro Ra quyet dinh (DSS) - Nhom 1 - De 08: DROOLS
===============================================================================
Cac thanh phan kien truc chuan Drools duoc mo phong chinh xac:
1. DRLParser & DecisionTableLoader -> Bien dich truc tiep file .drl & .csv/.xlsx
2. KieBase (Production Memory) -> Luu tru Declared Types, Rules va Rete/PHREAK
3. RetePhreakNetwork -> EntryPointNode -> ObjectTypeNode -> AlphaNode (co Node Sharing)
   -> BetaNode (Join 2+ Facts) -> RuleTerminalNode -> Agenda
4. KieSession (Working Memory) -> Quan ly FactHandle, insert, modify, delete,
   va insertLogical (Truth Maintenance System - TMS tu dong rut lai Fact suy dien)
5. Agenda & ConflictResolver -> Giai quyet xung dot theo:
   (1) agenda-group focus stack
   (2) salience (cao xuong thap)
   (3) activation-group (1 luat chay se huy cac luat cung nhom)
   (4) no-loop & lock-on-active
   (5) recency & rule order
6. AgendaEventListener -> Truy vet chi tiet tung chu ky Forward Chaining
"""

from __future__ import annotations

import ast
import copy
import csv
import math
import os
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


# ============================================================================
# TIEN ICH BIEN DICH BIEU THUC DROOLS DRL (MVEL / JAVA EXPRESSION -> PYTHON)
# ============================================================================

def _drools_add(a: Any, b: Any) -> Any:
    """Ho tro phep cong so hoc va noi chuoi kieu Java/MVEL trong Drools RHS."""
    if isinstance(a, str) or isinstance(b, str):
        if isinstance(a, float) and a.is_integer():
            a_str = f"{a:.1f}"
        else:
            a_str = str(a)
        if isinstance(b, float) and b.is_integer():
            b_str = f"{b:.1f}"
        else:
            b_str = str(b)
        return a_str + b_str
    return a + b


def round2(val: Union[int, float]) -> float:
    """Lam tron 2 chu so thap phan cho cac phep tinh tai chinh DSS."""
    return round(float(val), 2)


class _DroolsAddTransformer(ast.NodeTransformer):
    """Chuyen phep '+' trong AST sang ham _drools_add(left, right) de ho tro noi chuoi + so."""

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        self.generic_visit(node)
        if isinstance(node.op, ast.Add):
            return ast.Call(
                func=ast.Name(id="_drools_add", ctx=ast.Load()),
                args=[node.left, node.right],
                keywords=[],
            )
        return node


def _split_top_level(text: str, delimiter: str = ",") -> List[str]:
    """Tach chuoi theo delimiter o muc ngoac ngoai cung, bo qua dau phay ben trong chuoi hoac ngoac."""
    parts: List[str] = []
    current: List[str] = []
    depth_paren = 0
    depth_bracket = 0
    depth_brace = 0
    in_quote: Optional[str] = None
    escape = False

    for ch in text:
        if escape:
            current.append(ch)
            escape = False
            continue
        if ch == "\\":
            current.append(ch)
            escape = True
            continue
        if in_quote:
            current.append(ch)
            if ch == in_quote:
                in_quote = None
            continue
        if ch in ('"', "'"):
            in_quote = ch
            current.append(ch)
            continue
        if ch == "(":
            depth_paren += 1
        elif ch == ")":
            depth_paren = max(0, depth_paren - 1)
        elif ch == "[":
            depth_bracket += 1
        elif ch == "]":
            depth_bracket = max(0, depth_bracket - 1)
        elif ch == "{":
            depth_brace += 1
        elif ch == "}":
            depth_brace = max(0, depth_brace - 1)

        if (
            ch == delimiter
            and depth_paren == 0
            and depth_bracket == 0
            and depth_brace == 0
        ):
            piece = "".join(current).strip()
            if piece:
                parts.append(piece)
            current = []
        else:
            current.append(ch)

    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def _convert_ternary(expr: str) -> str:
    """Chuyen bieu thuc 3 ngoi Java/MVEL (cond ? a : b) sang Python (a if cond else b)."""
    # Xu ly de quy cac bieu thuc (cond ? a : b)
    pattern = re.compile(r"\(([^()?:]+)\?([^()?:]+):([^()?:]+)\)")
    prev = None
    out = expr
    while prev != out:
        prev = out
        out = pattern.sub(
            lambda m: f"(({m.group(2).strip()}) if ({m.group(1).strip()}) else ({m.group(3).strip()}))",
            out,
        )
    # Neu khong boc ngoac
    if "?" in out and ":" in out:
        m = re.match(r"^([^?:]+)\?([^?:]+):([^?:]+)$", out.strip())
        if m:
            out = f"(({m.group(2).strip()}) if ({m.group(1).strip()}) else ({m.group(3).strip()}))"
    return out


def translate_drl_expression(expr: str) -> str:
    """
    Dich bieu thuc dieu kien / hanh dong DRL sang bieu thuc Python an toan:
    - Chuyen $var -> _var_var
    - Chuyen && -> and, || -> or, true -> True, false -> False, null -> None (ngoai chuoi)
    - Chuyen toan tu 3 ngoi ? : sang if/else
    """
    tokens: List[str] = []
    current: List[str] = []
    in_quote: Optional[str] = None
    escape = False

    def flush_code(segment: str) -> str:
        s = _convert_ternary(segment)
        s = re.sub(r"\$([A-Za-z_][A-Za-z0-9_]*)", r"_var_\1", s)
        s = s.replace("&&", " and ").replace("||", " or ")
        # Toan tu phu dinh '!' (khong phai '!=')
        s = re.sub(r"!(?!=)", " not ", s)
        s = re.sub(r"\btrue\b", "True", s)
        s = re.sub(r"\bfalse\b", "False", s)
        s = re.sub(r"\bnull\b", "None", s)
        return s

    for ch in expr:
        if escape:
            current.append(ch)
            escape = False
            continue
        if ch == "\\":
            current.append(ch)
            escape = True
            continue
        if in_quote:
            current.append(ch)
            if ch == in_quote:
                tokens.append("".join(current))
                current = []
                in_quote = None
            continue
        if ch in ('"', "'"):
            if current:
                tokens.append(flush_code("".join(current)))
                current = []
            in_quote = ch
            current.append(ch)
            continue
        current.append(ch)

    if current:
        if in_quote:
            tokens.append("".join(current))
        else:
            tokens.append(flush_code("".join(current)))

    return "".join(tokens).strip()


def evaluate_drl_expression(
    expr: str,
    fact_obj: Optional[Any] = None,
    bindings: Optional[Dict[str, Any]] = None,
) -> Any:
    """Danh gia mot bieu thuc DRL voi ngữ cảnh Fact hien tai va cac bien binding ($app, $elig)."""
    py_expr = translate_drl_expression(expr)
    env: Dict[str, Any] = {
        "_drools_add": _drools_add,
        "round2": round2,
        "round": round,
        "min": min,
        "max": max,
        "abs": abs,
        "int": int,
        "float": float,
        "str": str,
        "len": len,
        "True": True,
        "False": False,
        "None": None,
    }
    if fact_obj is not None:
        if isinstance(fact_obj, Fact):
            env.update(fact_obj.to_dict())
        elif isinstance(fact_obj, dict):
            env.update(fact_obj)
        else:
            for k in dir(fact_obj):
                if not k.startswith("_"):
                    env[k] = getattr(fact_obj, k)

    if bindings:
        for var_name, bound_val in bindings.items():
            clean_name = var_name.lstrip("$")
            env[f"_var_{clean_name}"] = bound_val
            env[clean_name] = bound_val

    tree = ast.parse(py_expr, mode="eval")
    tree = _DroolsAddTransformer().visit(tree)
    ast.fix_missing_locations(tree)
    code = compile(tree, filename="<drl_expr>", mode="eval")
    return eval(code, {"__builtins__": {}}, env)


# ============================================================================
# 1. FACT & FACTHANDLE (WORKING MEMORY OBJECTS)
# ============================================================================

class Fact:
    """
    Doi tuong du lieu (Fact) trong Working Memory cua Drools.
    Ho tro truy cap thuoc tinh kieu object (fact.age) va kieu dict (fact['age']).
    """

    def __init__(self, fact_type: str = "Applicant", **kwargs: Any) -> None:
        object.__setattr__(self, "_fact_type", fact_type)
        object.__setattr__(self, "_data", {})
        for k, v in kwargs.items():
            self._data[k] = v

    @property
    def fact_type(self) -> str:
        return object.__getattribute__(self, "_fact_type")

    def __getattr__(self, item: str) -> Any:
        data = object.__getattribute__(self, "_data")
        if item in data:
            return data[item]
        raise AttributeError(f"Fact '{self.fact_type}' khong co thuoc tinh '{item}'")

    def __setattr__(self, key: str, value: Any) -> None:
        if key in ("_fact_type", "_data"):
            object.__setattr__(self, key, value)
        else:
            self._data[key] = value

    def __getitem__(self, item: str) -> Any:
        return self._data[item]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        out = copy.deepcopy(self._data)
        out["_fact_type"] = self.fact_type
        return out

    def snapshot(self) -> Dict[str, Any]:
        return copy.deepcopy(self._data)

    def signature_key(self) -> Tuple[Any, ...]:
        """Khoa nhan diện ngữ nghĩa cua Fact (phuc vu Truth Maintenance System - insertLogical)."""
        items = []
        for k in sorted(self._data.keys()):
            v = self._data[k]
            if isinstance(v, (int, float, str, bool)) or v is None:
                items.append((k, v))
        return (self.fact_type, tuple(items))

    def __repr__(self) -> str:
        fields = ", ".join(f"{k}={v!r}" for k, v in self._data.items() if not isinstance(v, list))
        return f"{self.fact_type}({fields})"


@dataclass
class LogicalJustification:
    """Thong tin bao chung chan ly (TMS Justification) cho mot Fact duoc insertLogical."""
    rule_name: str
    supporting_handles: List[int]
    condition_checker: Optional[Callable[[], bool]] = None
    reason: str = ""


@dataclass
class FactHandle:
    """
    FactHandle trong KieSession (Working Memory):
    Quan ly dinh danh, phien ban cap nhat (recency), co logical (TMS) va danh sach bao chung.
    """
    handle_id: int
    fact: Fact
    recency: int
    is_logical: bool = False
    justifications: List[LogicalJustification] = field(default_factory=list)

    @property
    def fact_type(self) -> str:
        return self.fact.fact_type


# ============================================================================
# 2. CAU TRUC LUAT DRL & DRL PARSER + DECISION TABLE LOADER
# ============================================================================

@dataclass
class PatternCondition:
    """Mot mau dieu kien Fact trong khoi WHEN (LHS), vi du: $app : Applicant(age >= 18, ...)."""
    fact_type: str
    binding: Optional[str]
    constraints: List[str]
    alpha_constraints: List[str] = field(default_factory=list)
    beta_constraints: List[str] = field(default_factory=list)
    raw_pattern: str = ""


@dataclass
class DRLRule:
    """Bieu dien mot luat Drools sau khi parse tu file .drl hoac Decision Table."""
    name: str
    salience: int = 0
    agenda_group: str = "MAIN"
    activation_group: Optional[str] = None
    no_loop: bool = False
    lock_on_active: bool = False
    dialect: str = "mvel"
    lhs_patterns: List[PatternCondition] = field(default_factory=list)
    rhs_raw: str = ""
    rhs_statements: List[str] = field(default_factory=list)
    order_index: int = 0
    source: str = "DRL"

    @property
    def rule_code(self) -> str:
        m = re.match(r"^([A-Za-z]+\d+)", self.name.strip())
        return m.group(1) if m else f"R{self.order_index:02d}"


@dataclass
class DeclaredType:
    """Thong tin kieu du lieu khai bao trong khoi `declare ... end` cua DRL."""
    type_name: str
    fields: Dict[str, str] = field(default_factory=dict)


class DRLParser:
    """
    Bo phan tich cu phap Drools Rule Language (.drl):
    Doc truc tiep package, import, declare, rule "...", salience, agenda-group,
    activation-group, no-loop, lock-on-active, khoi when (LHS) va khoi then (RHS).
    """

    def parse_file(self, file_path: str) -> Tuple[str, List[str], Dict[str, DeclaredType], List[DRLRule]]:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return self.parse_text(content, source=os.path.basename(file_path))

    def parse_text(
        self, drl_text: str, source: str = "DRL"
    ) -> Tuple[str, List[str], Dict[str, DeclaredType], List[DRLRule]]:
        # Loai bo comment // va /* ... */
        cleaned = self._strip_comments(drl_text)

        # 1. Package
        pkg_match = re.search(r"^\s*package\s+([\w\.]+)\s*;?", cleaned, re.MULTILINE)
        package_name = pkg_match.group(1) if pkg_match else "default_pkg"

        # 2. Imports
        imports = re.findall(r"^\s*import\s+([\w\.\*]+)\s*;?", cleaned, re.MULTILINE)

        # 3. Declare blocks
        declared_types: Dict[str, DeclaredType] = {}
        declare_pattern = re.compile(
            r"^\s*declare\s+([A-Za-z_][A-Za-z0-9_]*)\s*(.*?)^\s*end\b",
            re.MULTILINE | re.DOTALL,
        )
        for m in declare_pattern.finditer(cleaned):
            t_name = m.group(1).strip()
            body = m.group(2)
            fields: Dict[str, str] = {}
            for line in body.splitlines():
                line_s = line.strip()
                if ":" in line_s:
                    fname, ftype = line_s.split(":", 1)
                    fields[fname.strip()] = ftype.strip()
            declared_types[t_name] = DeclaredType(type_name=t_name, fields=fields)

        # 4. Rules
        rules: List[DRLRule] = []
        rule_pattern = re.compile(
            r'^\s*rule\s+"([^"]+)"\s*(.*?)^\s*end\b',
            re.MULTILINE | re.DOTALL,
        )
        for idx, m in enumerate(rule_pattern.finditer(cleaned), start=1):
            rule_name = m.group(1).strip()
            rule_body = m.group(2)
            parsed_rule = self._parse_single_rule(rule_name, rule_body, idx, source)
            rules.append(parsed_rule)

        return package_name, imports, declared_types, rules

    def _strip_comments(self, text: str) -> str:
        # Xoa block comments /* ... */
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        # Xoa line comments // nhung giu nguyen // ben trong chuoi
        out_lines: List[str] = []
        for line in text.splitlines():
            in_q: Optional[str] = None
            esc = False
            cut_idx: Optional[int] = None
            for i, ch in enumerate(line):
                if esc:
                    esc = False
                    continue
                if ch == "\\":
                    esc = True
                    continue
                if in_q:
                    if ch == in_q:
                        in_q = None
                    continue
                if ch in ('"', "'"):
                    in_q = ch
                    continue
                if ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                    cut_idx = i
                    break
            out_lines.append(line[:cut_idx] if cut_idx is not None else line)
        return "\n".join(out_lines)

    def _parse_single_rule(
        self, rule_name: str, body: str, order_index: int, source: str
    ) -> DRLRule:
        when_match = re.search(r"^\s*when\b", body, re.MULTILINE)
        then_match = re.search(r"^\s*then\b", body, re.MULTILINE)
        if not when_match or not then_match:
            raise ValueError(f"Luat '{rule_name}' thieu khoi 'when' hoac 'then'.")

        attr_section = body[: when_match.start()]
        lhs_section = body[when_match.end() : then_match.start()].strip()
        rhs_section = body[then_match.end() :].strip()

        salience = 0
        agenda_group = "MAIN"
        activation_group: Optional[str] = None
        no_loop = False
        lock_on_active = False
        dialect = "mvel"

        m_sal = re.search(r"\bsalience\s+(-?\d+)", attr_section)
        if m_sal:
            salience = int(m_sal.group(1))

        m_ag = re.search(r'\bagenda-group\s+"([^"]+)"', attr_section)
        if m_ag:
            agenda_group = m_ag.group(1).strip()

        m_act = re.search(r'\bactivation-group\s+"([^"]+)"', attr_section)
        if m_act:
            activation_group = m_act.group(1).strip()

        m_nl = re.search(r"\bno-loop\s+(true|false)?", attr_section, re.IGNORECASE)
        if m_nl:
            val = (m_nl.group(1) or "true").lower()
            no_loop = val == "true"

        m_loa = re.search(r"\block-on-active\s+(true|false)?", attr_section, re.IGNORECASE)
        if m_loa:
            val = (m_loa.group(1) or "true").lower()
            lock_on_active = val == "true"

        m_dia = re.search(r'\bdialect\s+"([^"]+)"', attr_section)
        if m_dia:
            dialect = m_dia.group(1).strip()

        lhs_patterns = self._parse_lhs(lhs_section)
        rhs_statements = self._parse_rhs(rhs_section)

        return DRLRule(
            name=rule_name,
            salience=salience,
            agenda_group=agenda_group,
            activation_group=activation_group,
            no_loop=no_loop,
            lock_on_active=lock_on_active,
            dialect=dialect,
            lhs_patterns=lhs_patterns,
            rhs_raw=rhs_section,
            rhs_statements=rhs_statements,
            order_index=order_index,
            source=source,
        )

    def _parse_lhs(self, lhs_text: str) -> List[PatternCondition]:
        patterns: List[PatternCondition] = []
        bound_vars_so_far: Set[str] = set()

        # Tim tung pattern: [$var :] FactType( ... )
        pattern_regex = re.compile(
            r"(?:(\$[A-Za-z_][A-Za-z0-9_]*)\s*:\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)",
            re.DOTALL,
        )
        for raw_line in lhs_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            m = pattern_regex.match(line)
            if not m:
                continue
            binding = m.group(1).strip() if m.group(1) else None
            fact_type = m.group(2).strip()
            inner = m.group(3).strip()
            constraints = _split_top_level(inner, ",") if inner else []

            alpha_constraints: List[str] = []
            beta_constraints: List[str] = []
            for c in constraints:
                referenced_vars = set(re.findall(r"\$[A-Za-z_][A-Za-z0-9_]*", c))
                other_vars = referenced_vars - ({binding} if binding else set())
                if other_vars & bound_vars_so_far or other_vars:
                    beta_constraints.append(c)
                else:
                    alpha_constraints.append(c)

            if binding:
                bound_vars_so_far.add(binding)

            patterns.append(
                PatternCondition(
                    fact_type=fact_type,
                    binding=binding,
                    constraints=constraints,
                    alpha_constraints=alpha_constraints,
                    beta_constraints=beta_constraints,
                    raw_pattern=line,
                )
            )
        return patterns

    def _parse_rhs(self, rhs_text: str) -> List[str]:
        """Tach khoi THEN thanh danh sach cac cau lenh modify(...) { ... }, insertLogical(...), addReason(...)."""
        statements: List[str] = []
        i = 0
        n = len(rhs_text)
        while i < n:
            while i < n and rhs_text[i].isspace():
                i += 1
            if i >= n:
                break

            # Kiem tra khoi modify($var) { ... }
            m_mod = re.match(r"modify\s*\(\s*(\$[A-Za-z_][A-Za-z0-9_]*)\s*\)\s*\{", rhs_text[i:])
            if m_mod:
                brace_start = i + m_mod.end() - 1
                depth = 0
                j = brace_start
                in_q: Optional[str] = None
                esc = False
                while j < n:
                    ch = rhs_text[j]
                    if esc:
                        esc = False
                        j += 1
                        continue
                    if ch == "\\":
                        esc = True
                        j += 1
                        continue
                    if in_q:
                        if ch == in_q:
                            in_q = None
                        j += 1
                        continue
                    if ch in ('"', "'"):
                        in_q = ch
                        j += 1
                        continue
                    if ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            j += 1
                            break
                    j += 1
                stmt = rhs_text[i:j].strip()
                statements.append(stmt)
                i = j
                while i < n and rhs_text[i] in (";", " ", "\t", "\r", "\n"):
                    i += 1
                continue

            # Cau lenh ket thuc bang ';' hoac het dong
            j = i
            in_q = None
            esc = False
            depth_p = 0
            while j < n:
                ch = rhs_text[j]
                if esc:
                    esc = False
                    j += 1
                    continue
                if ch == "\\":
                    esc = True
                    j += 1
                    continue
                if in_q:
                    if ch == in_q:
                        in_q = None
                    j += 1
                    continue
                if ch in ('"', "'"):
                    in_q = ch
                    j += 1
                    continue
                if ch == "(":
                    depth_p += 1
                elif ch == ")":
                    depth_p = max(0, depth_p - 1)
                elif ch == ";" and depth_p == 0:
                    j += 1
                    break
                j += 1
            stmt = rhs_text[i:j].strip().rstrip(";").strip()
            if stmt:
                statements.append(stmt)
            i = j

        return statements


class DecisionTableLoader:
    """
    Bo nap luat tu Bang Quyet dinh (Drools Decision Table .csv / .xlsx):
    Chuyen doi cac dong trong bang quyet dinh thanh DRLRule hoac ma nguon .drl.
    """

    def load_csv(self, csv_path: str, start_order: int = 100) -> List[DRLRule]:
        rules: List[DRLRule] = []
        parser = DRLParser()
        drl_chunks: List[str] = []

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, start=start_order):
                rule_name = (row.get("rule_name") or row.get("rule_id") or f"DT_{idx}").strip()
                agenda_group = (row.get("agenda_group") or "4-dss-explanation").strip()
                salience = int(row.get("salience") or 10)
                activation_group = (row.get("activation_group") or "").strip() or None
                no_loop = str(row.get("no_loop", "true")).lower() == "true"
                lock_on_active = str(row.get("lock_on_active", "true")).lower() == "true"
                fact_type = (row.get("fact_type") or "Applicant").strip()
                when_cond = (row.get("when_condition") or "").strip()
                then_act = (row.get("then_action") or "").strip()

                act_line = f'    activation-group "{activation_group}"\n' if activation_group else ""
                drl_block = (
                    f'rule "{rule_name}"\n'
                    f"    salience {salience}\n"
                    f'    agenda-group "{agenda_group}"\n'
                    f"{act_line}"
                    f"    no-loop {'true' if no_loop else 'false'}\n"
                    f"    lock-on-active {'true' if lock_on_active else 'false'}\n"
                    f"when\n"
                    f"    $app : {fact_type}( {when_cond} )\n"
                    f"then\n"
                    f"    {then_act}\n"
                    f"end\n"
                )
                drl_chunks.append(drl_block)

        if drl_chunks:
            _, _, _, parsed_rules = parser.parse_text(
                "\n".join(drl_chunks), source=os.path.basename(csv_path)
            )
            for i, r in enumerate(parsed_rules):
                r.order_index = start_order + i
            rules.extend(parsed_rules)
        return rules


# ============================================================================
# 3. MANG SUY DIEN RETE / PHREAK (RETE-OO / PHREAK NETWORK)
# ============================================================================

@dataclass
class EntryPointNode:
    node_id: str = "EP_DEFAULT"
    entry_point_name: str = "DEFAULT"
    object_type_nodes: Dict[str, "ObjectTypeNode"] = field(default_factory=dict)
    facts_entered: int = 0


@dataclass
class ObjectTypeNode:
    node_id: str
    fact_type: str
    alpha_nodes: List["AlphaNode"] = field(default_factory=list)
    matched_handles: List[int] = field(default_factory=list)


@dataclass
class AlphaNode:
    """
    Nut loc dieu kien don tren 1 Fact (Alpha Memory).
    Ho tro Alpha Node Sharing: nhieu luat dung chung 1 dieu kien se chia se cung AlphaNode.
    """
    node_id: str
    fact_type: str
    constraint: str
    shared_by_rules: List[str] = field(default_factory=list)
    evaluated_count: int = 0
    passed_handles: List[int] = field(default_factory=list)

    def evaluate(self, handle: FactHandle) -> bool:
        self.evaluated_count += 1
        try:
            res = bool(evaluate_drl_expression(self.constraint, fact_obj=handle.fact))
        except Exception:
            res = False
        if res and handle.handle_id not in self.passed_handles:
            self.passed_handles.append(handle.handle_id)
        return res


@dataclass
class BetaNode:
    """
    Nut ket hop (Beta / JoinNode):
    Ket hop cac AlphaNode cua 1 Fact va/hoac Join nhieu Fact ($elig + $app).
    """
    node_id: str
    rule_name: str
    agenda_group: str
    alpha_node_ids: List[str] = field(default_factory=list)
    join_constraints: List[str] = field(default_factory=list)
    fact_types: List[str] = field(default_factory=list)
    evaluated_tuples: int = 0
    matched_tuples: List[Dict[str, int]] = field(default_factory=list)


@dataclass
class RuleTerminalNode:
    """Nut dau cuoi cua Luat (RuleTerminalNode - RTN), sinh Activation day vao Agenda."""
    node_id: str
    rule: DRLRule
    beta_node_id: str
    activation_count: int = 0
    fired_count: int = 0
    cancelled_count: int = 0
    status: str = "IDLE"  # IDLE, ACTIVATED, FIRED, CANCELLED


class RetePhreakNetwork:
    """
    Do thi mang suy dien Rete / PHREAK cua Drools:
    EntryPointNode -> ObjectTypeNode -> AlphaNode (shared) -> BetaNode -> RuleTerminalNode.
    """

    def __init__(self, rules: List[DRLRule]) -> None:
        self.entry_point = EntryPointNode()
        self.object_type_nodes: Dict[str, ObjectTypeNode] = {}
        self.alpha_nodes: Dict[str, AlphaNode] = {}
        self._alpha_key_map: Dict[Tuple[str, str], AlphaNode] = {}
        self.beta_nodes: Dict[str, BetaNode] = {}
        self.terminal_nodes: Dict[str, RuleTerminalNode] = {}
        self.total_raw_alpha_constraints: int = 0
        self._build_network(rules)

    def _build_network(self, rules: List[DRLRule]) -> None:
        alpha_counter = 1
        for idx, rule in enumerate(rules, start=1):
            rule_alpha_ids: List[str] = []
            rule_join_constraints: List[str] = []
            rule_fact_types: List[str] = []

            for pat in rule.lhs_patterns:
                if pat.fact_type not in self.object_type_nodes:
                    otn = ObjectTypeNode(
                        node_id=f"OTN_{pat.fact_type}",
                        fact_type=pat.fact_type,
                    )
                    self.object_type_nodes[pat.fact_type] = otn
                    self.entry_point.object_type_nodes[pat.fact_type] = otn
                otn = self.object_type_nodes[pat.fact_type]
                if pat.fact_type not in rule_fact_types:
                    rule_fact_types.append(pat.fact_type)

                for a_cond in pat.alpha_constraints:
                    self.total_raw_alpha_constraints += 1
                    norm_key = (pat.fact_type, a_cond.strip())
                    if norm_key not in self._alpha_key_map:
                        alpha_id = f"ALPHA_{alpha_counter:02d}"
                        alpha_counter += 1
                        alpha_node = AlphaNode(
                            node_id=alpha_id,
                            fact_type=pat.fact_type,
                            constraint=a_cond.strip(),
                            shared_by_rules=[rule.name],
                        )
                        self._alpha_key_map[norm_key] = alpha_node
                        self.alpha_nodes[alpha_id] = alpha_node
                        otn.alpha_nodes.append(alpha_node)
                    else:
                        alpha_node = self._alpha_key_map[norm_key]
                        if rule.name not in alpha_node.shared_by_rules:
                            alpha_node.shared_by_rules.append(rule.name)
                    rule_alpha_ids.append(alpha_node.node_id)

                for b_cond in pat.beta_constraints:
                    rule_join_constraints.append(b_cond.strip())

            beta_id = f"BETA_{rule.rule_code}"
            beta_node = BetaNode(
                node_id=beta_id,
                rule_name=rule.name,
                agenda_group=rule.agenda_group,
                alpha_node_ids=rule_alpha_ids,
                join_constraints=rule_join_constraints,
                fact_types=rule_fact_types,
            )
            self.beta_nodes[beta_id] = beta_node

            rtn_id = f"RTN_{rule.rule_code}"
            self.terminal_nodes[rule.name] = RuleTerminalNode(
                node_id=rtn_id,
                rule=rule,
                beta_node_id=beta_id,
            )

    def reset_runtime_state(self) -> None:
        self.entry_point.facts_entered = 0
        for otn in self.object_type_nodes.values():
            otn.matched_handles.clear()
        for alpha in self.alpha_nodes.values():
            alpha.evaluated_count = 0
            alpha.passed_handles.clear()
        for beta in self.beta_nodes.values():
            beta.evaluated_tuples = 0
            beta.matched_tuples.clear()
        for rtn in self.terminal_nodes.values():
            rtn.activation_count = 0
            rtn.fired_count = 0
            rtn.cancelled_count = 0
            rtn.status = "IDLE"

    def evaluate_handles(
        self, handles: List[FactHandle]
    ) -> List[Tuple[DRLRule, Dict[str, FactHandle], List[str], str]]:
        """
        Danh gia Working Memory qua mang Rete/PHREAK:
        1. Day Fact qua EntryPointNode -> ObjectTypeNode
        2. Loc qua cac AlphaNode (co bo nho Alpha Memory)
        3. Ket hop qua BetaNode (Cartesian join giua cac Pattern + Beta constraints)
        4. Kich hoat RuleTerminalNode sinh danh sach (rule, matched_bindings, alpha_ids, beta_id)
        """
        for otn in self.object_type_nodes.values():
            otn.matched_handles.clear()
        for alpha in self.alpha_nodes.values():
            alpha.passed_handles.clear()
        for beta in self.beta_nodes.values():
            beta.matched_tuples.clear()

        self.entry_point.facts_entered = len(handles)
        handles_by_type: Dict[str, List[FactHandle]] = {}
        for h in handles:
            handles_by_type.setdefault(h.fact_type, []).append(h)
            if h.fact_type in self.object_type_nodes:
                self.object_type_nodes[h.fact_type].matched_handles.append(h.handle_id)

        # Danh gia AlphaNodes
        alpha_results: Dict[Tuple[str, int], bool] = {}
        for alpha in self.alpha_nodes.values():
            type_handles = handles_by_type.get(alpha.fact_type, [])
            for h in type_handles:
                passed = alpha.evaluate(h)
                alpha_results[(alpha.node_id, h.handle_id)] = passed

        # Danh gia BetaNodes & RuleTerminalNodes
        matched_outputs: List[Tuple[DRLRule, Dict[str, FactHandle], List[str], str]] = []
        for rtn in self.terminal_nodes.values():
            rule = rtn.rule
            beta = self.beta_nodes[rtn.beta_node_id]

            # Tim cac to hop Fact thoa man tung pattern trong LHS
            candidate_bindings: List[Dict[str, FactHandle]] = [{}]
            all_patterns_satisfiable = True

            for pat_idx, pat in enumerate(rule.lhs_patterns):
                type_handles = handles_by_type.get(pat.fact_type, [])
                if not type_handles:
                    all_patterns_satisfiable = False
                    break

                bind_key = pat.binding or f"$pat_{pat_idx}"
                next_bindings: List[Dict[str, FactHandle]] = []

                for partial in candidate_bindings:
                    for h in type_handles:
                        # Kiem tra tat ca AlphaNode cua pattern nay
                        alpha_ok = True
                        for a_cond in pat.alpha_constraints:
                            a_node = self._alpha_key_map[(pat.fact_type, a_cond.strip())]
                            if not alpha_results.get((a_node.node_id, h.handle_id), False):
                                alpha_ok = False
                                break
                        if not alpha_ok:
                            continue

                        trial = dict(partial)
                        trial[bind_key] = h

                        # Kiem tra Beta constraints cua pattern nay
                        beta.evaluated_tuples += 1
                        beta_ok = True
                        if pat.beta_constraints:
                            fact_bindings = {k: v.fact for k, v in trial.items()}
                            for b_cond in pat.beta_constraints:
                                try:
                                    if not bool(
                                        evaluate_drl_expression(
                                            b_cond,
                                            fact_obj=h.fact,
                                            bindings=fact_bindings,
                                        )
                                    ):
                                        beta_ok = False
                                        break
                                except Exception:
                                    beta_ok = False
                                    break
                        if beta_ok:
                            next_bindings.append(trial)

                candidate_bindings = next_bindings
                if not candidate_bindings:
                    all_patterns_satisfiable = False
                    break

            if all_patterns_satisfiable and candidate_bindings:
                for valid_binding in candidate_bindings:
                    tuple_ids = {k: v.handle_id for k, v in valid_binding.items()}
                    beta.matched_tuples.append(tuple_ids)
                    rtn.activation_count += 1
                    if rtn.status == "IDLE":
                        rtn.status = "ACTIVATED"
                    matched_outputs.append(
                        (rule, valid_binding, list(beta.alpha_node_ids), beta.node_id)
                    )

        return matched_outputs

    def to_json(self) -> Dict[str, Any]:
        """Xuat cau truc do thi Rete/PHREAK va trang thai kich hoat ra JSON cho Web Visualizer."""
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []

        nodes.append(
            {
                "id": self.entry_point.node_id,
                "type": "EntryPointNode",
                "label": f"EntryPoint ({self.entry_point.entry_point_name})",
                "facts_count": self.entry_point.facts_entered,
                "active": self.entry_point.facts_entered > 0,
            }
        )

        for otn in self.object_type_nodes.values():
            nodes.append(
                {
                    "id": otn.node_id,
                    "type": "ObjectTypeNode",
                    "fact_type": otn.fact_type,
                    "label": f"OTN: {otn.fact_type}",
                    "facts_count": len(otn.matched_handles),
                    "active": len(otn.matched_handles) > 0,
                }
            )
            edges.append({"from": self.entry_point.node_id, "to": otn.node_id})

        for alpha in self.alpha_nodes.values():
            otn_id = f"OTN_{alpha.fact_type}"
            nodes.append(
                {
                    "id": alpha.node_id,
                    "type": "AlphaNode",
                    "fact_type": alpha.fact_type,
                    "label": alpha.constraint,
                    "shared_by_rules": alpha.shared_by_rules,
                    "is_shared": len(alpha.shared_by_rules) > 1,
                    "evaluated_count": alpha.evaluated_count,
                    "facts_count": len(alpha.passed_handles),
                    "active": len(alpha.passed_handles) > 0,
                }
            )
            edges.append({"from": otn_id, "to": alpha.node_id})

        for beta in self.beta_nodes.values():
            rtn = self.terminal_nodes[beta.rule_name]
            nodes.append(
                {
                    "id": beta.node_id,
                    "type": "BetaNode",
                    "rule_name": beta.rule_name,
                    "rule_code": rtn.rule.rule_code,
                    "agenda_group": beta.agenda_group,
                    "label": (
                        f"Join ({' ⋈ '.join(beta.fact_types)})"
                        if len(beta.fact_types) > 1
                        else f"LIA ({beta.fact_types[0]})"
                    ),
                    "join_constraints": beta.join_constraints,
                    "is_multi_fact_join": len(beta.fact_types) > 1,
                    "facts_count": len(beta.matched_tuples),
                    "active": len(beta.matched_tuples) > 0,
                }
            )
            for a_id in beta.alpha_node_ids:
                edges.append({"from": a_id, "to": beta.node_id})

        for rtn in self.terminal_nodes.values():
            r = rtn.rule
            nodes.append(
                {
                    "id": rtn.node_id,
                    "type": "RuleTerminalNode",
                    "rule_code": r.rule_code,
                    "rule_name": r.name,
                    "agenda_group": r.agenda_group,
                    "activation_group": r.activation_group,
                    "salience": r.salience,
                    "status": rtn.status,
                    "activation_count": rtn.activation_count,
                    "fired_count": rtn.fired_count,
                    "cancelled_count": rtn.cancelled_count,
                    "active": rtn.fired_count > 0,
                }
            )
            edges.append({"from": rtn.beta_node_id, "to": rtn.node_id})

        unique_alpha_count = len(self.alpha_nodes)
        shared_alpha_count = sum(1 for a in self.alpha_nodes.values() if len(a.shared_by_rules) > 1)

        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_object_type_nodes": len(self.object_type_nodes),
                "total_raw_alpha_constraints": self.total_raw_alpha_constraints,
                "unique_alpha_nodes": unique_alpha_count,
                "shared_alpha_nodes": shared_alpha_count,
                "alpha_nodes_saved_by_sharing": max(0, self.total_raw_alpha_constraints - unique_alpha_count),
                "total_beta_nodes": len(self.beta_nodes),
                "multi_fact_beta_joins": sum(1 for b in self.beta_nodes.values() if len(b.fact_types) > 1),
                "total_terminal_nodes": len(self.terminal_nodes),
            },
        }


# ============================================================================
# 4. AGENDA, ACTIVATION & CONFLICT RESOLVER
# ============================================================================

@dataclass
class Activation:
    """Mot phien kich hoat luat tren Agenda (Rule + Tuple cac FactHandle thoa man LHS)."""
    rule: DRLRule
    bindings: Dict[str, FactHandle]
    matched_alpha_nodes: List[str]
    matched_beta_node: str
    created_cycle: int = 0

    @property
    def tuple_key(self) -> Tuple[Tuple[str, int], ...]:
        return tuple(sorted((k, v.handle_id) for k, v in self.bindings.items()))

    @property
    def max_recency(self) -> int:
        if not self.bindings:
            return 0
        return max(v.recency for v in self.bindings.values())


class ConflictResolver:
    """
    Chien luoc Giai quyet Xung dot (Conflict Resolution Strategy) chuan Drools:
    1. agenda-group dang co focus tren đỉnh stack
    2. salience (tu cao xuong thap)
    3. recency (Fact duoc insert/modify gan nhat)
    4. thu tu khai bao luat (order_index tu nho den lon)
    """

    @staticmethod
    def sort_activations(activations: List[Activation]) -> List[Activation]:
        return sorted(
            activations,
            key=lambda act: (
                -act.rule.salience,
                -act.max_recency,
                act.rule.order_index,
            ),
        )


class Agenda:
    """
    Quan ly Focus Stack cua cac agenda-group, hang doi Activation,
    activation-group cancellation, no-loop va lock-on-active.
    """

    def __init__(self) -> None:
        self.focus_stack: List[str] = ["MAIN"]
        self.fired_activation_groups: Dict[str, str] = {}
        # Luu (rule_name, tuple_key, tuple_recency) da chay de tranh chay lai tren cung trang thai Fact
        self.fired_rule_tuples: Set[Tuple[str, Tuple[Tuple[str, int], ...], Tuple[int, ...]]] = set()
        # Luu (agenda_group, rule_name, tuple_key) cho lock-on-active
        self.locked_on_active_rules: Set[Tuple[str, str, Tuple[Tuple[str, int], ...]]] = set()
        self.cancelled_history: List[Dict[str, Any]] = []

    def set_focus(self, agenda_group: str) -> None:
        if agenda_group in self.focus_stack:
            self.focus_stack.remove(agenda_group)
        self.focus_stack.append(agenda_group)

    def current_focus(self) -> Optional[str]:
        return self.focus_stack[-1] if self.focus_stack else None

    def pop_focus(self) -> Optional[str]:
        if self.focus_stack:
            return self.focus_stack.pop()
        return None


# ============================================================================
# 5. AGENDA EVENT LISTENER (AUDIT & FORWARD CHAINING TRACE)
# ============================================================================

@dataclass
class AgendaEventListener:
    """Bo lang nghe va ghi nhan nhat ky truy vet suy dien tien (Forward Chaining Trace)."""
    steps: List[Dict[str, Any]] = field(default_factory=list)
    tms_events: List[Dict[str, Any]] = field(default_factory=list)
    cancelled_activations: List[Dict[str, Any]] = field(default_factory=list)

    def record_step(self, step_data: Dict[str, Any]) -> None:
        self.steps.append(step_data)

    def record_tms_event(self, event_data: Dict[str, Any]) -> None:
        self.tms_events.append(event_data)

    def record_cancellation(self, cancel_data: Dict[str, Any]) -> None:
        self.cancelled_activations.append(cancel_data)


# ============================================================================
# 6. KIEBASE (PRODUCTION MEMORY) & KIESESSION (WORKING MEMORY)
# ============================================================================

class KieBase:
    """
    Production Memory trong Drools (KieBase):
    Chua cac Declared Types, danh sach DRLRule da bien dich va mang RetePhreakNetwork.
    """

    def __init__(
        self,
        drl_path: Optional[str] = None,
        drl_text: Optional[str] = None,
        decision_table_csv: Optional[str] = None,
    ) -> None:
        self.parser = DRLParser()
        self.dt_loader = DecisionTableLoader()
        self.package_name: str = "vn.edu.dss.nhom1.credit"
        self.imports: List[str] = []
        self.declared_types: Dict[str, DeclaredType] = {}
        self.rules: List[DRLRule] = []

        if drl_path:
            pkg, imps, decls, r_list = self.parser.parse_file(drl_path)
            self.package_name = pkg
            self.imports.extend(imps)
            self.declared_types.update(decls)
            self.rules.extend(r_list)

        if drl_text:
            pkg, imps, decls, r_list = self.parser.parse_text(drl_text, source="LIVE_DRL")
            self.package_name = pkg
            self.imports.extend(imps)
            self.declared_types.update(decls)
            self.rules.extend(r_list)

        if decision_table_csv and os.path.exists(decision_table_csv):
            dt_rules = self.dt_loader.load_csv(
                decision_table_csv, start_order=len(self.rules) + 1
            )
            self.rules.extend(dt_rules)

        self.network = RetePhreakNetwork(self.rules)

    def add_decision_table_csv(self, csv_path: str) -> List[DRLRule]:
        dt_rules = self.dt_loader.load_csv(csv_path, start_order=len(self.rules) + 1)
        self.rules.extend(dt_rules)
        self.network = RetePhreakNetwork(self.rules)
        return dt_rules

    def new_kie_session(self) -> "KieSession":
        return KieSession(self)


class KieSession:
    """
    Working Memory trong Drools (KieSession):
    Quan ly FactHandle, thuc thi insert(), modify(), delete(), insertLogical() (TMS),
    va dieu phoi vong lap Suy dien tien fire_all_rules().
    """

    DEFAULT_PIPELINE = [
        "1-eligibility",
        "2-risk-scoring",
        "3-pricing-decision",
        "4-dss-explanation",
    ]

    def __init__(self, kie_base: KieBase) -> None:
        self.kie_base = kie_base
        self.handles: Dict[int, FactHandle] = {}
        self._next_handle_id: int = 1
        self._recency_counter: int = 1
        self.agenda = Agenda()
        self.listener = AgendaEventListener()
        self._current_firing_rule: Optional[DRLRule] = None
        self._current_firing_bindings: Dict[str, FactHandle] = {}
        self._no_loop_suppressed: Set[Tuple[str, Tuple[Tuple[str, int], ...], Tuple[int, ...]]] = set()

    def insert(self, fact: Union[Fact, Dict[str, Any]], fact_type: str = "Applicant") -> FactHandle:
        """Them mot Fact moi vao Working Memory (Stated Fact)."""
        if isinstance(fact, dict):
            f_type = fact.pop("_fact_type", fact_type)
            fact_obj = Fact(fact_type=f_type, **fact)
        elif isinstance(fact, Fact):
            fact_obj = fact
        else:
            raise TypeError("Fact phai la doi tuong Fact hoac dict.")

        handle = FactHandle(
            handle_id=self._next_handle_id,
            fact=fact_obj,
            recency=self._recency_counter,
            is_logical=False,
        )
        self.handles[handle.handle_id] = handle
        self._next_handle_id += 1
        self._recency_counter += 1
        return handle

    def insertLogical(
        self,
        fact: Union[Fact, Dict[str, Any]],
        reason: str = "",
        rule_name: Optional[str] = None,
        supporting_handles: Optional[List[int]] = None,
        condition_checker: Optional[Callable[[], bool]] = None,
    ) -> FactHandle:
        """
        He thong Bao toan Chan ly (Truth Maintenance System - TMS):
        Them mot Fact suy dien (Logical Fact) vao Working Memory.
        Neu dieu kien goc cua luat sinh ra Fact nay khong con dung sau khi modify/delete,
        TMS se tu dong rut lai (retract) Fact nay khoi Working Memory!
        """
        if isinstance(fact, dict):
            f_type = fact.pop("_fact_type", "LogicalFact")
            fact_obj = Fact(fact_type=f_type, **fact)
        else:
            fact_obj = fact

        active_rule_name = rule_name or (
            self._current_firing_rule.name if self._current_firing_rule else "MANUAL_TMS"
        )
        sup_handles = supporting_handles or [
            h.handle_id for h in self._current_firing_bindings.values()
        ]

        # Neu khong truyen condition_checker tu ben ngoai, tu dong tao condition_checker
        # kiem tra LHS cua luat sinh ra Fact nay!
        if condition_checker is None and self._current_firing_rule is not None:
            rule_ref = self._current_firing_rule
            bindings_ref = dict(self._current_firing_bindings)

            def _auto_checker() -> bool:
                for pat_idx, pat in enumerate(rule_ref.lhs_patterns):
                    b_key = pat.binding or f"$pat_{pat_idx}"
                    h_ref = bindings_ref.get(b_key)
                    if h_ref is None or h_ref.handle_id not in self.handles:
                        return False
                    for cond in pat.constraints:
                        try:
                            f_map = {k: v.fact for k, v in bindings_ref.items() if v.handle_id in self.handles}
                            if not bool(evaluate_drl_expression(cond, fact_obj=h_ref.fact, bindings=f_map)):
                                return False
                        except Exception:
                            return False
                return True

            condition_checker = _auto_checker

        justification = LogicalJustification(
            rule_name=active_rule_name,
            supporting_handles=sup_handles,
            condition_checker=condition_checker,
            reason=reason or f"Logically inserted by {active_rule_name}",
        )

        # Kiem tra xem Fact cung signature da ton tai chua
        sig = fact_obj.signature_key()
        for existing in self.handles.values():
            if existing.is_logical and existing.fact.signature_key() == sig:
                existing.justifications.append(justification)
                return existing

        handle = FactHandle(
            handle_id=self._next_handle_id,
            fact=fact_obj,
            recency=self._recency_counter,
            is_logical=True,
            justifications=[justification],
        )
        self.handles[handle.handle_id] = handle
        self._next_handle_id += 1
        self._recency_counter += 1

        self.listener.record_tms_event(
            {
                "action": "INSERT_LOGICAL",
                "handle_id": handle.handle_id,
                "fact_type": fact_obj.fact_type,
                "fact_data": fact_obj.snapshot(),
                "rule_name": active_rule_name,
                "supporting_handles": sup_handles,
                "reason": justification.reason,
            }
        )
        return handle

    def modify(self, fact_or_handle: Union[FactHandle, Fact], **updates: Any) -> FactHandle:
        """
        Cap nhat thuoc tinh cua Fact trong Working Memory, tang chi so recency,
        va kich hoat TMS kiem tra lai cac Logical Facts phu thuoc.
        """
        handle = self._resolve_handle(fact_or_handle)
        for k, v in updates.items():
            handle.fact[k] = v
        handle.recency = self._recency_counter
        self._recency_counter += 1

        # Neu luat hien tai co no-loop=True, ngan luat nay tu kich hoat lai tren trang thai recency moi
        if self._current_firing_rule and self._current_firing_rule.no_loop:
            t_key = tuple(sorted((k, v.handle_id) for k, v in self._current_firing_bindings.items()))
            rec_sig = tuple(
                v.recency for _, v in sorted(self._current_firing_bindings.items(), key=lambda x: x[0])
            )
            self._no_loop_suppressed.add((self._current_firing_rule.name, t_key, rec_sig))

        # Kiem tra Truth Maintenance System (TMS)
        self._verify_truth_maintenance()
        return handle

    def delete(self, fact_or_handle: Union[FactHandle, Fact]) -> None:
        """Xoa (retract) mot Fact khoi Working Memory va rut lai cac Logical Facts phu thuoc."""
        handle = self._resolve_handle(fact_or_handle)
        if handle.handle_id in self.handles:
            del self.handles[handle.handle_id]
        self._verify_truth_maintenance()

    retract = delete

    def _resolve_handle(self, fact_or_handle: Union[FactHandle, Fact]) -> FactHandle:
        if isinstance(fact_or_handle, FactHandle):
            return fact_or_handle
        for h in self.handles.values():
            if h.fact is fact_or_handle:
                return h
        raise KeyError("Fact khong ton tai trong Working Memory (KieSession).")

    def _verify_truth_maintenance(self) -> None:
        """
        Kiem tra toan bo cac Logical Facts trong Working Memory:
        Neu tat ca justifications cua mot Logical Fact deu khong con thoa man,
        TMS tu dong rut lai (retract) Logical Fact do!
        """
        retracted_any = True
        while retracted_any:
            retracted_any = False
            for h_id, handle in list(self.handles.items()):
                if not handle.is_logical:
                    continue
                valid_justifications: List[LogicalJustification] = []
                for just in handle.justifications:
                    supports_exist = all(sh in self.handles for sh in just.supporting_handles)
                    cond_holds = True
                    if supports_exist and just.condition_checker is not None:
                        try:
                            cond_holds = bool(just.condition_checker())
                        except Exception:
                            cond_holds = False
                    if supports_exist and cond_holds:
                        valid_justifications.append(just)

                handle.justifications = valid_justifications
                if not handle.justifications:
                    del self.handles[h_id]
                    retracted_any = True
                    self.listener.record_tms_event(
                        {
                            "action": "AUTO_RETRACT_LOGICAL",
                            "handle_id": h_id,
                            "fact_type": handle.fact_type,
                            "fact_data": handle.fact.snapshot(),
                            "reason": "Điều kiện gốc không còn thỏa mãn (Truth Maintenance System tự động rút lại Fact suy diễn).",
                        }
                    )

    def get_facts(self, fact_type: Optional[str] = None) -> List[Fact]:
        if fact_type is None:
            return [h.fact for h in self.handles.values()]
        return [h.fact for h in self.handles.values() if h.fact_type == fact_type]

    def set_focus(self, agenda_group: str) -> None:
        self.agenda.set_focus(agenda_group)

    def fire_all_rules(
        self,
        max_cycles: int = 100,
        agenda_pipeline: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Thuc thi vong lap Suy dien tien nhieu tang (Multi-stage Forward Chaining):
        Match (Rete/PHREAK) -> Conflict Resolution (Agenda) -> Act (RHS) -> Loop.
        """
        pipeline = agenda_pipeline if agenda_pipeline is not None else list(self.DEFAULT_PIPELINE)

        # Day pipeline vao focus stack theo thu tu nguoc de tang 1 nam tren dinh stack
        self.agenda.focus_stack = ["MAIN"]
        for group_name in reversed(pipeline):
            self.agenda.set_focus(group_name)

        self.kie_base.network.reset_runtime_state()
        cycle = 0

        while self.agenda.focus_stack and cycle < max_cycles:
            current_group = self.agenda.current_focus()
            if current_group is None:
                break

            # Buoc 1: Match - Danh gia Working Memory qua mang Rete/PHREAK
            raw_matches = self.kie_base.network.evaluate_handles(list(self.handles.values()))

            # Buoc 2: Loc cac Activation thuoc agenda-group dang co focus
            group_activations: List[Activation] = []
            for rule, bindings, alpha_ids, beta_id in raw_matches:
                if rule.agenda_group != current_group:
                    continue

                act = Activation(
                    rule=rule,
                    bindings=bindings,
                    matched_alpha_nodes=alpha_ids,
                    matched_beta_node=beta_id,
                    created_cycle=cycle + 1,
                )
                t_key = act.tuple_key
                rec_sig = tuple(
                    v.recency for _, v in sorted(bindings.items(), key=lambda x: x[0])
                )

                # Kiem tra luat da chay tren cung trang thai Fact chua
                if (rule.name, t_key, rec_sig) in self.agenda.fired_rule_tuples:
                    continue

                # Kiem tra no-loop suppression
                if (rule.name, t_key, rec_sig) in self._no_loop_suppressed:
                    continue

                # Kiem tra lock-on-active trong cung agenda-group
                if rule.lock_on_active and (current_group, rule.name, t_key) in self.agenda.locked_on_active_rules:
                    continue

                # Kiem tra activation-group da co luat chien thang chua
                if rule.activation_group and rule.activation_group in self.agenda.fired_activation_groups:
                    winner_name = self.agenda.fired_activation_groups[rule.activation_group]
                    self._record_activation_group_cancel(
                        cancelled_rule=rule,
                        winner_rule_name=winner_name,
                        cycle=cycle,
                    )
                    continue

                group_activations.append(act)

            if not group_activations:
                # Khong con Activation nao trong agenda-group hien tai -> chuyen focus sang tang tiep theo
                self.agenda.pop_focus()
                continue

            # Buoc 3: Conflict Resolution - Sap xep theo Salience, Recency, Rule Order
            sorted_activations = ConflictResolver.sort_activations(group_activations)
            selected = sorted_activations[0]
            conflict_set_summary = [
                {
                    "rule_code": a.rule.rule_code,
                    "rule_name": a.rule.name,
                    "salience": a.rule.salience,
                    "activation_group": a.rule.activation_group,
                    "recency": a.max_recency,
                }
                for a in sorted_activations
            ]

            cycle += 1

            # Neu luat duoc chon thuoc mot activation-group, huy tat ca cac luat khac cung activation-group tren Agenda
            cancelled_in_this_step: List[Dict[str, Any]] = []
            if selected.rule.activation_group:
                ag_name = selected.rule.activation_group
                self.agenda.fired_activation_groups[ag_name] = selected.rule.name
                for other_act in sorted_activations[1:]:
                    if other_act.rule.activation_group == ag_name:
                        cancel_info = self._record_activation_group_cancel(
                            cancelled_rule=other_act.rule,
                            winner_rule_name=selected.rule.name,
                            cycle=cycle,
                        )
                        if cancel_info:
                            cancelled_in_this_step.append(cancel_info)

            # Buoc 4: Act - Thuc thi khoi THEN (RHS) cua luat chien thang
            primary_handle = self._get_primary_applicant_handle(selected.bindings)
            before_snapshot = primary_handle.fact.snapshot() if primary_handle else {}

            self._execute_rhs(selected)

            after_snapshot = primary_handle.fact.snapshot() if primary_handle else {}
            changed_fields = self._diff_snapshots(before_snapshot, after_snapshot)

            # Cap nhat trang thai fired & lock-on-active
            t_key = selected.tuple_key
            rec_sig_after = tuple(
                v.recency for _, v in sorted(selected.bindings.items(), key=lambda x: x[0])
            )
            self.agenda.fired_rule_tuples.add((selected.rule.name, t_key, rec_sig_after))
            if selected.rule.lock_on_active:
                self.agenda.locked_on_active_rules.add((current_group, selected.rule.name, t_key))

            rtn = self.kie_base.network.terminal_nodes.get(selected.rule.name)
            if rtn:
                rtn.fired_count += 1
                rtn.status = "FIRED"

            self.listener.record_step(
                {
                    "cycle": cycle,
                    "agenda_group": selected.rule.agenda_group,
                    "rule_code": selected.rule.rule_code,
                    "rule_name": selected.rule.name,
                    "salience": selected.rule.salience,
                    "activation_group": selected.rule.activation_group,
                    "no_loop": selected.rule.no_loop,
                    "lock_on_active": selected.rule.lock_on_active,
                    "matched_alpha_nodes": selected.matched_alpha_nodes,
                    "matched_beta_node": selected.matched_beta_node,
                    "when_summary": " AND ".join(p.raw_pattern for p in selected.rule.lhs_patterns),
                    "then_summary": "; ".join(selected.rule.rhs_statements),
                    "conflict_set": conflict_set_summary,
                    "cancelled_in_step": cancelled_in_this_step,
                    "changed_fields": changed_fields,
                    "before_snapshot": before_snapshot,
                    "after_snapshot": after_snapshot,
                }
            )

        # Danh gia lai mang Rete/PHREAK lan cuoi de dong bo trang thai do thi hien thi
        self.kie_base.network.evaluate_handles(list(self.handles.values()))

        return {
            "total_cycles": cycle,
            "fired_rules": [s["rule_code"] for s in self.listener.steps],
            "fired_rule_names": [s["rule_name"] for s in self.listener.steps],
            "trace_steps": self.listener.steps,
            "cancelled_activations": self.listener.cancelled_activations,
            "tms_events": self.listener.tms_events,
            "rete_network": self.kie_base.network.to_json(),
            "working_memory_facts": [
                {
                    "handle_id": h.handle_id,
                    "fact_type": h.fact_type,
                    "recency": h.recency,
                    "is_logical": h.is_logical,
                    "data": h.fact.snapshot(),
                }
                for h in self.handles.values()
            ],
        }

    def _record_activation_group_cancel(
        self, cancelled_rule: DRLRule, winner_rule_name: str, cycle: int
    ) -> Optional[Dict[str, Any]]:
        already = any(
            c["cancelled_rule"] == cancelled_rule.name
            and c["activation_group"] == cancelled_rule.activation_group
            for c in self.listener.cancelled_activations
        )
        if already:
            return None
        rtn = self.kie_base.network.terminal_nodes.get(cancelled_rule.name)
        if rtn:
            rtn.cancelled_count += 1
            if rtn.fired_count == 0:
                rtn.status = "CANCELLED"
        info = {
            "cycle": cycle,
            "cancelled_rule_code": cancelled_rule.rule_code,
            "cancelled_rule": cancelled_rule.name,
            "cancelled_salience": cancelled_rule.salience,
            "activation_group": cancelled_rule.activation_group,
            "winner_rule": winner_rule_name,
            "reason": (
                f"Bị hủy kích hoạt do luật '{winner_rule_name}' có độ ưu tiên Salience cao hơn "
                f"đã chiến thắng trong cùng activation-group '{cancelled_rule.activation_group}'."
            ),
        }
        self.listener.record_cancellation(info)
        return info

    def _get_primary_applicant_handle(
        self, bindings: Dict[str, FactHandle]
    ) -> Optional[FactHandle]:
        if "$app" in bindings:
            return bindings["$app"]
        for h in bindings.values():
            if h.fact_type == "Applicant":
                return h
        return next(iter(bindings.values()), None)

    def _diff_snapshots(
        self, before: Dict[str, Any], after: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        diffs: Dict[str, Dict[str, Any]] = {}
        for k, after_val in after.items():
            before_val = before.get(k)
            if before_val != after_val:
                diffs[k] = {"before": before_val, "after": after_val}
        return diffs

    def _execute_rhs(self, activation: Activation) -> None:
        """Thuc thi cac cau lenh trong khoi THEN (RHS) cua luat Drools."""
        self._current_firing_rule = activation.rule
        self._current_firing_bindings = activation.bindings
        fact_bindings = {k: v.fact for k, v in activation.bindings.items()}

        try:
            for stmt in activation.rule.rhs_statements:
                self._execute_rhs_statement(stmt, activation.bindings, fact_bindings)
        finally:
            self._current_firing_rule = None
            self._current_firing_bindings = {}

    def _execute_rhs_statement(
        self,
        stmt: str,
        handle_bindings: Dict[str, FactHandle],
        fact_bindings: Dict[str, Fact],
    ) -> None:
        # 1. modify($var) { field1 = expr1, field2 = expr2 }
        m_mod = re.match(
            r"^modify\s*\(\s*(\$[A-Za-z_][A-Za-z0-9_]*)\s*\)\s*\{(.*)\}$",
            stmt,
            re.DOTALL,
        )
        if m_mod:
            var_name = m_mod.group(1).strip()
            body = m_mod.group(2).strip()
            target_handle = handle_bindings[var_name]
            assignments = _split_top_level(body, ",")
            updates: Dict[str, Any] = {}
            for assign in assignments:
                if "=" not in assign:
                    continue
                field_name, expr_str = assign.split("=", 1)
                f_key = field_name.strip()
                val = evaluate_drl_expression(
                    expr_str.strip(),
                    fact_obj=target_handle.fact,
                    bindings=fact_bindings,
                )
                # Cap nhat tam thoi de cac phep gan sau trong cung modify() doc duoc gia tri moi
                target_handle.fact[f_key] = val
                updates[f_key] = val
            self.modify(target_handle, **updates)
            return

        # 2. insertLogical(new FactType(k1 = v1, ...)) hoac insert(new FactType(...))
        m_ins = re.match(
            r"^(insertLogical|insert)\s*\(\s*new\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)\s*\)$",
            stmt,
            re.DOTALL,
        )
        if m_ins:
            op_name = m_ins.group(1).strip()
            new_type = m_ins.group(2).strip()
            args_str = m_ins.group(3).strip()
            arg_pairs = _split_top_level(args_str, ",") if args_str else []
            kwargs: Dict[str, Any] = {}
            for idx, pair in enumerate(arg_pairs):
                if "=" in pair:
                    k_str, v_str = pair.split("=", 1)
                    kwargs[k_str.strip()] = evaluate_drl_expression(
                        v_str.strip(), bindings=fact_bindings
                    )
                else:
                    kwargs[f"arg_{idx}"] = evaluate_drl_expression(
                        pair.strip(), bindings=fact_bindings
                    )
            new_fact = Fact(fact_type=new_type, **kwargs)
            if op_name == "insertLogical":
                self.insertLogical(
                    new_fact,
                    reason=f"Suy diễn logic từ luật '{self._current_firing_rule.name if self._current_firing_rule else ''}'",
                )
            else:
                self.insert(new_fact)
            return

        # 3. delete($var) / retract($var)
        m_del = re.match(r"^(?:delete|retract)\s*\(\s*(\$[A-Za-z_][A-Za-z0-9_]*)\s*\)$", stmt)
        if m_del:
            var_name = m_del.group(1).strip()
            if var_name in handle_bindings:
                self.delete(handle_bindings[var_name])
            return

        # 4. addReason($var, expr) / addRecommendation($var, expr) / addFlag($var, expr)
        m_helper = re.match(
            r"^(addReason|addRecommendation|addFlag)\s*\(\s*(\$[A-Za-z_][A-Za-z0-9_]*)\s*,\s*(.*)\)$",
            stmt,
            re.DOTALL,
        )
        if m_helper:
            fn_name = m_helper.group(1).strip()
            var_name = m_helper.group(2).strip()
            msg_expr = m_helper.group(3).strip()
            target_handle = handle_bindings[var_name]
            msg_val = str(
                evaluate_drl_expression(
                    msg_expr, fact_obj=target_handle.fact, bindings=fact_bindings
                )
            )
            if fn_name == "addReason":
                reasons = list(target_handle.fact.get("reasons", []))
                reasons.append(msg_val)
                target_handle.fact["reasons"] = reasons
            elif fn_name == "addRecommendation":
                recs = list(target_handle.fact.get("recommendations", []))
                recs.append(msg_val)
                target_handle.fact["recommendations"] = recs
            elif fn_name == "addFlag":
                flags = list(target_handle.fact.get("risk_flags", []))
                flags.append(msg_val)
                target_handle.fact["risk_flags"] = flags
            return


# ============================================================================
# 7. DICH VU DSS THAM DINH TIN DUNG & DINH GIA KHOAN VAY (CREDIT APPROVAL DSS)
# ============================================================================

class CreditApprovalDSS:
    """
    Dich vu He thong Ho tro Ra quyet dinh Tham dinh Tin dung & Dinh gia Khoan vay:
    - Quan ly KieBase (.drl + decision_table_rules.csv)
    - Chuan hoa Fact Applicant, tinh toan chi so tai chinh & Radar 5 chieu
    - Ho tro 6 Kich ban Demo 1-Click, What-If & Sensitivity Analysis,
      Batch CSV Scoring (15 ho so) va Live DRL Hot-Reload.
    """

    DECISION_LABELS = {
        "APPROVED": "PHÊ DUYỆT TỰ ĐỘNG (APPROVED)",
        "CONDITIONAL_APPROVAL": "PHÊ DUYỆT CÓ ĐIỀU KIỆN (CONDITIONAL)",
        "MANUAL_REVIEW": "CHUYỂN HỘI ĐỒNG TÍN DỤNG (MANUAL REVIEW)",
        "REJECTED": "TỪ CHỐI CẤP TÍN DỤNG (REJECTED)",
        "PENDING": "ĐANG CHỜ XỬ LÝ (PENDING)",
    }

    TIER_LABELS = {
        "TIER_A": "Hạng A – Rủi ro rất thấp",
        "TIER_B": "Hạng B – Rủi ro thấp - trung bình",
        "TIER_C": "Hạng C – Rủi ro trung bình - cao",
        "TIER_D": "Hạng D – Rủi ro cao",
        "UNRATED": "Chưa xếp hạng",
    }

    def __init__(
        self,
        drl_path: str,
        decision_table_csv: Optional[str] = None,
        sample_csv_path: Optional[str] = None,
    ) -> None:
        self.drl_path = drl_path
        self.decision_table_csv = decision_table_csv
        self.sample_csv_path = sample_csv_path
        with open(drl_path, "r", encoding="utf-8") as f:
            self.active_drl_text = f.read()
        self.kie_base = KieBase(
            drl_text=self.active_drl_text,
            decision_table_csv=decision_table_csv,
        )

    def reload_drl(self, new_drl_text: str, save_to_disk: bool = False) -> Dict[str, Any]:
        """Bien dich lai KieBase tu ma nguon .drl moi ngay tren trinh duyet (Live DRL Studio)."""
        new_kb = KieBase(
            drl_text=new_drl_text,
            decision_table_csv=self.decision_table_csv,
        )
        self.active_drl_text = new_drl_text
        self.kie_base = new_kb
        if save_to_disk and self.drl_path:
            with open(self.drl_path, "w", encoding="utf-8") as f:
                f.write(new_drl_text)
        return {
            "status": "SUCCESS",
            "package_name": new_kb.package_name,
            "total_rules": len(new_kb.rules),
            "declared_types": list(new_kb.declared_types.keys()),
            "rete_stats": new_kb.network.to_json()["stats"],
        }

    @staticmethod
    def build_applicant_fact(payload: Dict[str, Any]) -> Fact:
        """Chuan hoa du lieu dau vao thanh Fact Applicant day du cac truong chuan DRL."""
        def _to_bool(val: Any) -> bool:
            if isinstance(val, bool):
                return val
            return str(val).strip().lower() in ("true", "1", "yes", "y")

        loan_amount = float(payload.get("loan_amount", 200.0))
        loan_term_months = max(1, int(payload.get("loan_term_months", 36)))
        monthly_income = max(0.1, float(payload.get("monthly_income", 25.0)))
        collateral_value = float(payload.get("collateral_value", 0.0))

        return Fact(
            fact_type="Applicant",
            applicant_id=str(payload.get("applicant_id", "APP_DEMO")),
            full_name=str(payload.get("full_name", "Khách hàng Demo")),
            age=int(payload.get("age", 32)),
            monthly_income=round(monthly_income, 2),
            employment_years=round(float(payload.get("employment_years", 3.0)), 2),
            credit_score=int(payload.get("credit_score", 720)),
            dti_ratio=round(float(payload.get("dti_ratio", 30.0)), 2),
            loan_amount=round(loan_amount, 2),
            loan_term_months=loan_term_months,
            collateral_value=round(collateral_value, 2),
            cic_bad_debt=_to_bool(payload.get("cic_bad_debt", False)),
            is_vip=_to_bool(payload.get("is_vip", False)),
            eligible=False,
            secured_loan=False,
            composite_score=0,
            risk_flag_count=0,
            risk_tier="UNRATED",
            decision="PENDING",
            approved_amount=0.0,
            interest_rate=0.0,
            rejection_code="NONE",
            independent_valuation_required=False,
            stage_reached="1-eligibility",
            reasons=[],
            recommendations=[],
            risk_flags=[],
            scenario_tag=str(payload.get("scenario_tag", "CUSTOM")),
            notes=str(payload.get("notes", "")),
        )

    @staticmethod
    def compute_monthly_payment(principal: float, annual_rate_percent: float, months: int) -> float:
        """Tinh khoan tra gop hang thang (Goc + Lai theo du no giam dan / Annuity) don vi Trieu VND."""
        if principal <= 0 or months <= 0:
            return 0.0
        if annual_rate_percent <= 0:
            return round(principal / months, 2)
        r = (annual_rate_percent / 100.0) / 12.0
        payment = principal * (r * (1 + r) ** months) / (((1 + r) ** months) - 1)
        return round(payment, 2)

    @staticmethod
    def compute_radar_dimensions(app_data: Dict[str, Any]) -> Dict[str, int]:
        """Tinh diem 5 chieu (thang 0..100) phuc vu bieu do Radar danh gia ho so."""
        # 1. Nang luc thu nhap
        income_score = min(100, int(round((float(app_data["monthly_income"]) / 50.0) * 100)))
        # 2. Uy tin tin dung (Credit Score & CIC)
        if app_data["cic_bad_debt"]:
            credit_dim = 15
        else:
            cs = int(app_data["credit_score"])
            credit_dim = max(10, min(100, int(round(((cs - 450) / 380.0) * 100))))
        # 3. An toan du no (DTI)
        dti = float(app_data["dti_ratio"])
        dti_dim = max(5, min(100, int(round(100 - max(0.0, dti - 15.0) * 1.45))))
        # 4. Bao chung tai san (Collateral coverage)
        loan_amt = max(1.0, float(app_data["loan_amount"]))
        cov = float(app_data["collateral_value"]) / loan_amt
        collateral_dim = min(100, int(round((cov / 1.5) * 100)))
        # 5. On dinh nghe nghiep & do tuoi
        emp = float(app_data["employment_years"])
        age = int(app_data["age"])
        age_ok = 1.0 if 18 <= age <= 65 else 0.2
        stability_dim = min(100, int(round(min(100.0, (emp / 6.0) * 85 + 15) * age_ok)))

        return {
            "income_capacity": income_score,
            "credit_reputation": credit_dim,
            "debt_safety_dti": dti_dim,
            "collateral_coverage": collateral_dim,
            "career_stability": stability_dim,
        }

    def evaluate_applicant(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Chay phien suy dien Drools KieSession day du cho 1 ho so khach hang."""
        session = self.kie_base.new_kie_session()
        app_fact = self.build_applicant_fact(payload)
        session.insert(app_fact)
        engine_result = session.fire_all_rules()

        final_data = app_fact.snapshot()
        monthly_payment = self.compute_monthly_payment(
            principal=final_data["approved_amount"],
            annual_rate_percent=final_data["interest_rate"],
            months=final_data["loan_term_months"],
        )
        loan_amt = max(0.01, float(final_data["loan_amount"]))
        collateral_ratio = round((float(final_data["collateral_value"]) / loan_amt) * 100.0, 1)
        approval_ratio = round((float(final_data["approved_amount"]) / loan_amt) * 100.0, 1)

        # Tinh DTI uoc tinh sau khi dieu chinh han muc
        if final_data["approved_amount"] > 0 and final_data["approved_amount"] < final_data["loan_amount"]:
            scale = final_data["approved_amount"] / loan_amt
            post_loan_dti = round(final_data["dti_ratio"] * (0.45 + 0.55 * scale), 2)
        elif final_data["approved_amount"] == 0:
            post_loan_dti = round(final_data["dti_ratio"] * 0.45, 2)
        else:
            post_loan_dti = final_data["dti_ratio"]

        radar = self.compute_radar_dimensions(final_data)

        return {
            "applicant": final_data,
            "summary": {
                "decision": final_data["decision"],
                "decision_label": self.DECISION_LABELS.get(final_data["decision"], final_data["decision"]),
                "risk_tier": final_data["risk_tier"],
                "risk_tier_label": self.TIER_LABELS.get(final_data["risk_tier"], final_data["risk_tier"]),
                "composite_score": final_data["composite_score"],
                "approved_amount": final_data["approved_amount"],
                "approval_ratio_percent": approval_ratio,
                "interest_rate": final_data["interest_rate"],
                "estimated_monthly_payment": monthly_payment,
                "collateral_coverage_percent": collateral_ratio,
                "post_decision_dti": post_loan_dti,
                "eligible": final_data["eligible"],
                "secured_loan": final_data["secured_loan"],
                "independent_valuation_required": final_data["independent_valuation_required"],
                "rejection_code": final_data["rejection_code"],
                "stage_reached": final_data["stage_reached"],
                "reasons": final_data["reasons"],
                "recommendations": final_data["recommendations"],
                "risk_flags": final_data["risk_flags"],
            },
            "radar_dimensions": radar,
            "engine": engine_result,
        }

    def run_what_if(
        self, baseline_payload: Dict[str, Any], modified_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Phong Thi nghiem What-If & Phan tich Do nhay (Sensitivity Simulator):
        So sanh song song Baseline vs What-If va quet duong cong do nhay theo quy mo khoan vay / DTI.
        """
        base_res = self.evaluate_applicant(baseline_payload)
        whatif_res = self.evaluate_applicant(modified_payload)

        base_rules = set(base_res["engine"]["fired_rules"])
        whatif_rules = set(whatif_res["engine"]["fired_rules"])

        added_rules = [r for r in whatif_res["engine"]["fired_rules"] if r not in base_rules]
        removed_rules = [r for r in base_res["engine"]["fired_rules"] if r not in whatif_rules]

        # Quet duong cong do nhay (Sensitivity Curve) theo 6 muc thu nhap / DTI
        sensitivity_points: List[Dict[str, Any]] = []
        for factor in (0.6, 0.8, 1.0, 1.2, 1.4, 1.6):
            probe = copy.deepcopy(modified_payload)
            base_inc = max(5.0, float(modified_payload.get("monthly_income", 25.0)))
            probe["monthly_income"] = round(base_inc * factor, 1)
            # Khi thu nhap tang, DTI giam tuong ung theo ty le nghich
            base_dti = float(modified_payload.get("dti_ratio", 35.0))
            probe["dti_ratio"] = round(min(90.0, max(10.0, base_dti / factor)), 1)
            probe_eval = self.evaluate_applicant(probe)
            sensitivity_points.append(
                {
                    "income_multiplier": factor,
                    "monthly_income": probe["monthly_income"],
                    "dti_ratio": probe["dti_ratio"],
                    "composite_score": probe_eval["summary"]["composite_score"],
                    "risk_tier": probe_eval["summary"]["risk_tier"],
                    "decision": probe_eval["summary"]["decision"],
                    "approved_amount": probe_eval["summary"]["approved_amount"],
                    "interest_rate": probe_eval["summary"]["interest_rate"],
                }
            )

        return {
            "baseline": base_res,
            "what_if": whatif_res,
            "comparison": {
                "score_delta": whatif_res["summary"]["composite_score"] - base_res["summary"]["composite_score"],
                "approved_amount_delta": round(
                    whatif_res["summary"]["approved_amount"] - base_res["summary"]["approved_amount"], 2
                ),
                "interest_rate_delta": round(
                    whatif_res["summary"]["interest_rate"] - base_res["summary"]["interest_rate"], 2
                ),
                "monthly_payment_delta": round(
                    whatif_res["summary"]["estimated_monthly_payment"]
                    - base_res["summary"]["estimated_monthly_payment"],
                    2,
                ),
                "tier_changed": base_res["summary"]["risk_tier"] != whatif_res["summary"]["risk_tier"],
                "decision_changed": base_res["summary"]["decision"] != whatif_res["summary"]["decision"],
                "added_rules": added_rules,
                "removed_rules": removed_rules,
            },
            "sensitivity_curve": sensitivity_points,
        }

    def load_sample_applicants(self, csv_path: Optional[str] = None) -> List[Dict[str, Any]]:
        target = csv_path or self.sample_csv_path
        if not target or not os.path.exists(target):
            return []
        rows: List[Dict[str, Any]] = []
        with open(target, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(
                    {
                        "applicant_id": row["applicant_id"],
                        "full_name": row["full_name"],
                        "age": int(row["age"]),
                        "monthly_income": float(row["monthly_income"]),
                        "employment_years": float(row["employment_years"]),
                        "credit_score": int(row["credit_score"]),
                        "dti_ratio": float(row["dti_ratio"]),
                        "loan_amount": float(row["loan_amount"]),
                        "loan_term_months": int(row["loan_term_months"]),
                        "collateral_value": float(row["collateral_value"]),
                        "cic_bad_debt": str(row["cic_bad_debt"]).lower() == "true",
                        "is_vip": str(row["is_vip"]).lower() == "true",
                        "scenario_tag": row.get("scenario_tag", ""),
                        "notes": row.get("notes", ""),
                    }
                )
        return rows

    def get_preset_scenarios(self) -> List[Dict[str, Any]]:
        """Lay 6 kich ban Demo 1-Click dau tien tu data/sample_applicants.csv."""
        all_rows = self.load_sample_applicants()
        return all_rows[:6]

    def evaluate_batch(self, applicants: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Cham diem hang loat danh muc ho so (Batch DSS Scoring) qua Drools Engine."""
        records = applicants if applicants is not None else self.load_sample_applicants()
        results: List[Dict[str, Any]] = []
        decision_counts: Dict[str, int] = {
            "APPROVED": 0,
            "CONDITIONAL_APPROVAL": 0,
            "MANUAL_REVIEW": 0,
            "REJECTED": 0,
        }
        tier_counts: Dict[str, int] = {
            "TIER_A": 0,
            "TIER_B": 0,
            "TIER_C": 0,
            "TIER_D": 0,
        }
        total_requested = 0.0
        total_approved = 0.0
        rates: List[float] = []

        for item in records:
            res = self.evaluate_applicant(item)
            app = res["applicant"]
            summ = res["summary"]
            dec = summ["decision"]
            tier = summ["risk_tier"]
            decision_counts[dec] = decision_counts.get(dec, 0) + 1
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
            total_requested += float(app["loan_amount"])
            total_approved += float(summ["approved_amount"])
            if summ["interest_rate"] > 0:
                rates.append(float(summ["interest_rate"]))

            results.append(
                {
                    "applicant_id": app["applicant_id"],
                    "full_name": app["full_name"],
                    "age": app["age"],
                    "monthly_income": app["monthly_income"],
                    "credit_score": app["credit_score"],
                    "dti_ratio": app["dti_ratio"],
                    "loan_amount": app["loan_amount"],
                    "collateral_value": app["collateral_value"],
                    "cic_bad_debt": app["cic_bad_debt"],
                    "is_vip": app["is_vip"],
                    "composite_score": summ["composite_score"],
                    "risk_tier": tier,
                    "decision": dec,
                    "decision_label": summ["decision_label"],
                    "approved_amount": summ["approved_amount"],
                    "interest_rate": summ["interest_rate"],
                    "estimated_monthly_payment": summ["estimated_monthly_payment"],
                    "fired_rules": res["engine"]["fired_rules"],
                    "total_cycles": res["engine"]["total_cycles"],
                    "scenario_tag": app.get("scenario_tag", ""),
                    "notes": app.get("notes", ""),
                }
            )

        avg_rate = round(sum(rates) / len(rates), 2) if rates else 0.0
        return {
            "total_applicants": len(results),
            "decision_counts": decision_counts,
            "tier_counts": tier_counts,
            "total_requested_amount": round(total_requested, 2),
            "total_approved_amount": round(total_approved, 2),
            "portfolio_approval_ratio_percent": (
                round((total_approved / total_requested) * 100.0, 1) if total_requested > 0 else 0.0
            ),
            "average_interest_rate": avg_rate,
            "items": results,
        }
