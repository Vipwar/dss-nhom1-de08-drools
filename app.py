"""
app.py
===============================================================================
WEB SERVER & REST API CHO HE THONG HO TRO RA QUYET DINH (DSS) - DE 08: DROOLS
Nhom 1 - Bai toan: Tham dinh Tin dung, Xep hang Rui ro & Dinh gia Khoan vay Ca nhan
-------------------------------------------------------------------------------
Su dung thu vien chuan Python (http.server.ThreadingHTTPServer) de chay ngay lap tuc
100% tren moi may chi voi 1 lenh:
    python app.py
Truy cap giao dien Web tai: http://localhost:8000
===============================================================================
"""

from __future__ import annotations

import argparse
import csv
import json
import mimetypes
import os
import sys
import traceback
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict
from urllib.parse import urlparse

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from engine.drools_engine import CreditApprovalDSS, KieBase, UnsafeDRLExpressionError
from engine.multi_paradigm_comparator import (
    BackwardGoalSeeker,
    MultiParadigmComparator,
    RuleBaseVerifier,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DRL_PATH = os.path.join(BASE_DIR, "rules", "credit_approval.drl")
CLIPS_PATH = os.path.join(BASE_DIR, "rules", "credit_approval.clp")
PROLOG_PATH = os.path.join(BASE_DIR, "rules", "credit_approval.pl")
DT_CSV_PATH = os.path.join(BASE_DIR, "rules", "decision_table_rules.csv")
SAMPLE_CSV_PATH = os.path.join(BASE_DIR, "data", "sample_applicants.csv")
STATIC_DIR = os.path.join(BASE_DIR, "static")
JAVA_KIE_APP_PATH = os.path.join(
    BASE_DIR,
    "java_kie_reference",
    "src",
    "main",
    "java",
    "vn",
    "edu",
    "dss",
    "nhom1",
    "credit",
    "CreditApprovalDroolsApp.java",
)
JAVA_KMODULE_PATH = os.path.join(
    BASE_DIR, "java_kie_reference", "src", "main", "resources", "META-INF", "kmodule.xml"
)

# Khoi tao dich vu Drools DSS toan cuc & Bo doi sanh da cong cu (Drools vs CLIPS vs Prolog)
DSS_SERVICE = CreditApprovalDSS(
    drl_path=DRL_PATH,
    decision_table_csv=DT_CSV_PATH,
    sample_csv_path=SAMPLE_CSV_PATH,
)
RULE_VERIFIER = RuleBaseVerifier(DSS_SERVICE)
GOAL_SEEKER = BackwardGoalSeeker(DSS_SERVICE)
PARADIGM_COMPARATOR = MultiParadigmComparator(
    dss=DSS_SERVICE,
    clips_path=CLIPS_PATH,
    prolog_path=PROLOG_PATH,
)

with open(DRL_PATH, "r", encoding="utf-8") as _f:
    DEFAULT_DRL_TEXT = _f.read()

JAVA_KIE_SOURCE = ""
if os.path.exists(JAVA_KIE_APP_PATH):
    with open(JAVA_KIE_APP_PATH, "r", encoding="utf-8") as _jf:
        JAVA_KIE_SOURCE = _jf.read()
if os.path.exists(JAVA_KMODULE_PATH):
    with open(JAVA_KMODULE_PATH, "r", encoding="utf-8") as _kf:
        JAVA_KIE_SOURCE = f"<!-- META-INF/kmodule.xml -->\n{_kf.read()}\n\n// CreditApprovalDroolsApp.java\n{JAVA_KIE_SOURCE}"


def load_decision_table_rows() -> list[dict[str, Any]]:
    if not os.path.exists(DT_CSV_PATH):
        return []
    with open(DT_CSV_PATH, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class DroolsDSSRequestHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler phuc vu Giao dien Dashboard va REST API JSON."""

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[Drools-DSS API] {self.address_string()} - {fmt % args}")

    def _send_json(self, data: Any, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw) if raw.strip() else {}

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path == "/api/overview":
                presets = DSS_SERVICE.get_preset_scenarios()
                all_applicants = DSS_SERVICE.load_sample_applicants()
                default_eval = DSS_SERVICE.evaluate_applicant(presets[0]) if presets else {}
                verification = RULE_VERIFIER.verify_all()
                comparison = (
                    PARADIGM_COMPARATOR.compare_on_applicant(presets[0]) if presets else {}
                )
                goal_seek_default = (
                    GOAL_SEEKER.seek_goal(presets[2], "APPROVED_100")
                    if len(presets) > 2
                    else {}
                )
                initial_stress = DSS_SERVICE.run_portfolio_stress_test(
                    income_shock_pct=-20.0,
                    collateral_shock_pct=-25.0,
                    dti_shock_pts=12.0,
                )
                rules_meta = [
                    {
                        "rule_code": r.rule_code,
                        "name": r.name,
                        "salience": r.salience,
                        "agenda_group": r.agenda_group,
                        "activation_group": r.activation_group,
                        "no_loop": r.no_loop,
                        "lock_on_active": r.lock_on_active,
                        "source": r.source,
                        "when": [p.raw_pattern for p in r.lhs_patterns],
                        "then": r.rhs_statements,
                    }
                    for r in DSS_SERVICE.kie_base.rules
                ]
                self._send_json(
                    {
                        "status": "OK",
                        "project": {
                            "course": "Hệ thống Hỗ trợ Ra quyết định (Decision Support Systems - DSS)",
                            "group": "Nhóm 1",
                            "topic": "Đề 08 – DROOLS (Nhóm Rule-Based: Drools vs CLIPS vs Prolog)",
                            "problem": "Hệ thống Hỗ trợ Ra quyết định Thẩm định Tín dụng, Xếp hạng Rủi ro & Định giá Khoản vay Cá nhân",
                            "package_name": DSS_SERVICE.kie_base.package_name,
                            "total_rules": len(DSS_SERVICE.kie_base.rules),
                        },
                        "presets": presets,
                        "sample_applicants": all_applicants,
                        "rules_metadata": rules_meta,
                        "decision_table_rows": load_decision_table_rows(),
                        "drl_source": DSS_SERVICE.active_drl_text,
                        "clips_source": PARADIGM_COMPARATOR.clips_source,
                        "prolog_source": PARADIGM_COMPARATOR.prolog_source,
                        "java_kie_source": JAVA_KIE_SOURCE,
                        "initial_evaluation": default_eval,
                        "rule_verification": verification,
                        "initial_comparison": comparison,
                        "initial_goal_seek": goal_seek_default,
                        "initial_stress_test": initial_stress,
                    }
                )
                return

            if path == "/api/batch":
                batch_res = DSS_SERVICE.evaluate_batch()
                self._send_json({"status": "OK", "batch": batch_res})
                return

            if path == "/api/verify-rules":
                verification = RULE_VERIFIER.verify_all()
                self._send_json({"status": "OK", "verification": verification})
                return

            if path == "/api/rules":
                self._send_json(
                    {
                        "status": "OK",
                        "drl_source": DSS_SERVICE.active_drl_text,
                        "default_drl_source": DEFAULT_DRL_TEXT,
                        "clips_source": PARADIGM_COMPARATOR.clips_source,
                        "prolog_source": PARADIGM_COMPARATOR.prolog_source,
                        "java_kie_source": JAVA_KIE_SOURCE,
                        "total_rules": len(DSS_SERVICE.kie_base.rules),
                        "decision_table_rows": load_decision_table_rows(),
                    }
                )
                return

            # Phuc vu file tinh (index.html, styles.css, app.js)
            self._serve_static(path)
        except Exception as exc:
            traceback.print_exc()
            self._send_json(
                {"status": "ERROR", "message": str(exc)},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            payload = self._read_json_body()

            if path == "/api/evaluate":
                applicant_data = payload.get("applicant", payload)
                result = DSS_SERVICE.evaluate_applicant(applicant_data)
                self._send_json({"status": "OK", "result": result})
                return

            if path == "/api/what-if":
                baseline = payload.get("baseline", {})
                what_if = payload.get("what_if", {})
                result = DSS_SERVICE.run_what_if(baseline, what_if)
                self._send_json({"status": "OK", "result": result})
                return

            if path == "/api/batch":
                applicants = payload.get("applicants")
                batch_res = DSS_SERVICE.evaluate_batch(applicants)
                self._send_json({"status": "OK", "batch": batch_res})
                return

            if path == "/api/stress-test":
                income_shock_pct = float(payload.get("income_shock_pct", -20.0))
                collateral_shock_pct = float(payload.get("collateral_shock_pct", -25.0))
                dti_shock_pts = float(payload.get("dti_shock_pts", 12.0))
                applicants = payload.get("applicants")
                stress_res = DSS_SERVICE.run_portfolio_stress_test(
                    income_shock_pct=income_shock_pct,
                    collateral_shock_pct=collateral_shock_pct,
                    dti_shock_pts=dti_shock_pts,
                    applicants=applicants,
                )
                self._send_json(
                    {
                        "status": "OK",
                        "stress_test": stress_res,
                        "result": stress_res,
                    }
                )
                return

            if path == "/api/compare-engines":
                applicant_data = payload.get("applicant") or DSS_SERVICE.get_preset_scenarios()[0]
                comparison = PARADIGM_COMPARATOR.compare_on_applicant(applicant_data)
                self._send_json({"status": "OK", "comparison": comparison})
                return

            if path == "/api/goal-seek":
                applicant_data = payload.get("applicant") or DSS_SERVICE.get_preset_scenarios()[2]
                target_goal = str(payload.get("target_goal", "APPROVED_100"))
                plan_res = GOAL_SEEKER.seek_goal(applicant_data, target_goal)
                self._send_json({"status": "OK", "goal_seek": plan_res})
                return

            if path == "/api/rules/compile":
                reset_default = bool(payload.get("reset_default", False))
                drl_text = DEFAULT_DRL_TEXT if reset_default else str(payload.get("drl_source", ""))
                if not drl_text.strip():
                    self._send_json(
                        {"status": "ERROR", "message": "Nội dung file .drl không được để trống."},
                        status=HTTPStatus.BAD_REQUEST,
                    )
                    return
                compile_info = DSS_SERVICE.reload_drl(drl_text, save_to_disk=False)
                sample_applicant = payload.get("applicant") or DSS_SERVICE.get_preset_scenarios()[0]
                test_eval = DSS_SERVICE.evaluate_applicant(sample_applicant)
                self._send_json(
                    {
                        "status": "OK",
                        "compile_info": compile_info,
                        "drl_source": DSS_SERVICE.active_drl_text,
                        "test_evaluation": test_eval,
                    }
                )
                return

            if path == "/api/tms-demo":
                kb = KieBase(drl_text=DSS_SERVICE.active_drl_text)
                session = kb.new_kie_session()
                applicant_input = payload.get("applicant") or DSS_SERVICE.get_preset_scenarios()[0]
                fact = DSS_SERVICE.build_applicant_fact(applicant_input)
                handle = session.insert(fact)

                session.fire_all_rules(agenda_pipeline=["1-eligibility"])
                wm_after_step1 = [
                    {
                        "handle_id": h.handle_id,
                        "fact_type": h.fact_type,
                        "is_logical": h.is_logical,
                        "data": h.fact.snapshot(),
                    }
                    for h in session.handles.values()
                ]

                session.modify(handle, cic_bad_debt=True)
                wm_after_step2 = [
                    {
                        "handle_id": h.handle_id,
                        "fact_type": h.fact_type,
                        "is_logical": h.is_logical,
                        "data": h.fact.snapshot(),
                    }
                    for h in session.handles.values()
                ]

                self._send_json(
                    {
                        "status": "OK",
                        "step1_working_memory": wm_after_step1,
                        "step2_working_memory": wm_after_step2,
                        "tms_events": session.listener.tms_events,
                    }
                )
                return

            self._send_json(
                {"status": "ERROR", "message": f"Không tìm thấy endpoint {path}"},
                status=HTTPStatus.NOT_FOUND,
            )
        except UnsafeDRLExpressionError as sec_exc:
            self._send_json(
                {
                    "status": "ERROR",
                    "security_blocked": True,
                    "message": f"[SafeASTEvaluator Blocked] {sec_exc}",
                },
                status=HTTPStatus.BAD_REQUEST,
            )
        except Exception as exc:
            traceback.print_exc()
            self._send_json(
                {"status": "ERROR", "message": f"Lỗi xử lý: {exc}"},
                status=HTTPStatus.BAD_REQUEST,
            )

    def _serve_static(self, path: str) -> None:
        if path in ("/", "/index.html"):
            target_file = os.path.join(STATIC_DIR, "index.html")
        elif path.startswith("/static/"):
            rel = path[len("/static/") :]
            target_file = os.path.abspath(os.path.join(STATIC_DIR, rel))
        else:
            rel = path.lstrip("/")
            target_file = os.path.abspath(os.path.join(STATIC_DIR, rel))

        if not target_file.startswith(os.path.abspath(STATIC_DIR)) or not os.path.isfile(target_file):
            self._send_json(
                {"status": "ERROR", "message": f"File không tồn tại: {path}"},
                status=HTTPStatus.NOT_FOUND,
            )
            return

        mime_type, _ = mimetypes.guess_type(target_file)
        content_type = mime_type or "application/octet-stream"
        if content_type.startswith("text/") or content_type in ("application/javascript", "application/json"):
            content_type += "; charset=utf-8"

        with open(target_file, "rb") as f:
            data = f.read()

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)


def run_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), DroolsDSSRequestHandler)
    print(f"Đã nạp {len(DSS_SERVICE.kie_base.rules)} luật, {len(DSS_SERVICE.load_sample_applicants())} hồ sơ mẫu")
    print(f"Server chạy tại http://localhost:{port}  (Ctrl+C để dừng)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Drools-DSS] Đang dừng Web Server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chạy Web Server Demo Đồ án DSS Đề 08 - Drools (Nhóm 1)")
    parser.add_argument("--host", default="0.0.0.0", help="Địa chỉ host (mặc định: 0.0.0.0)")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", "8000")),
        help="Cổng HTTP (mặc định: 8000)",
    )
    args = parser.parse_args()
    run_server(host=args.host, port=args.port)
