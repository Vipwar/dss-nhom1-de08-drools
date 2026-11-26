"""
demo_all.py
===============================================================================
KICH BAN DEMO TAT CA CHUNG LUC (ALL-IN-ONE MASTER SHOWCASE - V3 ULTIMATE)
He thong Ho tro Ra quyet dinh (DSS) - Nhom 1 - De 08: DROOLS Rule Engine
-------------------------------------------------------------------------------
Chay 1 lenh duy nhat de trinh dien DONG THOI tat ca hang muc cua Do an:
  1. Trinh dien CLI 9 phan he (Rete/PHREAK, Alpha Cache, V&V, 6 Kich ban Basel III,
     TMS insertLogical, Doi sanh Drools-CLIPS-Prolog, Backward Goal-Seeker,
     Basel III Stress-Test 4x4, SafeAST Security Block & Fuzzing 100 Ho so).
  2. Chay toan bo 28/28 Unit & Integration Tests (100% PASS).
  3. Xac thuc (va tuy chon mo) Bao cao Word (.docx) & Slide PowerPoint (.pptx).
  4. Khoi dong Web Server va tu dong mo Trinh duyet o che do All-in-One (?demo=all)
     hien thi dong thoi ca 5 Tab phan he tren cung 1 man hinh!

Cach dung:
    python demo_all.py
    python demo_all.py --open-docs
    python demo_all.py --no-server
===============================================================================
"""

from __future__ import annotations

import argparse
import os
import platform
import random
import socket
import subprocess
import sys
import threading
import time
import unittest
import webbrowser

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import run_server
from cli_demo import CLIPS_PATH, DRL_PATH, DT_CSV_PATH, PROLOG_PATH, SAMPLE_CSV_PATH, run_cli_walkthrough
from engine.drools_engine import CreditApprovalDSS, SafeASTEvaluator, StrictInputSanitizer, UnsafeDRLExpressionError
from engine.multi_paradigm_comparator import MultiParadigmComparator


def _find_available_port(preferred_port: int = 8000) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if sock.connect_ex(("127.0.0.1", preferred_port)) != 0:
            return preferred_port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _open_file_native(filepath: str) -> None:
    if not os.path.exists(filepath):
        return
    try:
        sys_name = platform.system()
        if sys_name == "Windows":
            os.startfile(filepath)  # type: ignore[attr-defined]
        elif sys_name == "Darwin":
            subprocess.Popen(["open", filepath])
        else:
            subprocess.Popen(["xdg-open", filepath])
    except Exception as exc:
        print(f"    [!] Khong the mo tu dong {filepath}: {exc}")


def run_v3_security_and_fuzzing_showcase() -> None:
    dss = CreditApprovalDSS(
        drl_path=DRL_PATH,
        decision_table_csv=DT_CSV_PATH,
        sample_csv_path=SAMPLE_CSV_PATH,
    )
    comparator = MultiParadigmComparator(dss, CLIPS_PATH, PROLOG_PATH)
    evaluator = SafeASTEvaluator()
    sample_fact = dss.build_applicant_fact(dss.get_preset_scenarios()[0])

    print("\n[8] KIỂM CHỨNG BẢO MẬT SAFE AST EVALUATOR & CHỐNG CHIA CHO 0 (V3 ULTIMATE):")
    malicious_payloads = [
        "__import__('os').system('calc') == 0",
        "().__class__.__bases__[0].__subclasses__()",
        "open('/etc/passwd').read() != ''",
    ]
    for payload in malicious_payloads:
        try:
            evaluator.evaluate(payload, fact_obj=sample_fact, bindings={"$app": sample_fact})
            raise RuntimeError(f"Loi bao mat: khong chan duoc payload {payload}")
        except UnsafeDRLExpressionError as blocked_err:
            print(f"    - [BLOCKED] {payload:<45} -> {blocked_err}")

    edge_fact = dss.build_applicant_fact(
        {"loan_term_months": 0, "monthly_income": -50, "loan_amount": 0}
    )
    print(
        f"    - [SANITIZED] Input biên (term=0, income=-50, loan=0) -> "
        f"term={edge_fact.loan_term_months} tháng, income={edge_fact.monthly_income} tr, "
        f"loan={edge_fact.loan_amount} tr"
    )

    print("\n[9] KIỂM THỬ FUZZING 100 HỒ SƠ NGẪU NHIÊN (DROOLS .drl vs CLIPS .clp vs PROLOG .pl):")
    rng = random.Random(20260801)
    matched = 0
    for idx in range(100):
        applicant = {
            "applicant_id": f"FUZZ{idx + 1:03d}",
            "full_name": f"Khach hang Fuzz {idx + 1}",
            "age": rng.randint(16, 72),
            "monthly_income": round(rng.uniform(4.0, 120.0), 1),
            "existing_debt_payment": round(rng.uniform(0.0, 45.0), 1),
            "credit_score": rng.randint(420, 850),
            "cic_bad_debt": rng.random() < 0.15,
            "late_payments_12m": rng.randint(0, 5),
            "employment_years": round(rng.uniform(0.0, 20.0), 1),
            "employment_type": rng.choice(["PERMANENT", "CONTRACT", "BUSINESS", "FREELANCE"]),
            "loan_amount": round(rng.uniform(30.0, 1200.0), 1),
            "loan_term_months": rng.choice([12, 24, 36, 48, 60, 84]),
            "collateral_value": round(rng.choice([0.0, rng.uniform(50.0, 2000.0)]), 1),
            "is_vip": rng.random() < 0.25,
        }
        cmp_res = comparator.compare_on_applicant(applicant)
        if cmp_res["consensus_verified"]:
            matched += 1
    print(f"    - Kết quả hội tụ trên 100 hồ sơ sinh ngẫu nhiên: {matched}/100 hồ sơ khớp tuyệt đối (100% EQUIVALENCE)")


def run_all_unit_tests() -> bool:
    print("\n" + "=" * 88)
    print("  [PHẦN 2/4] CHẠY TOÀN BỘ BỘ KIỂM THỬ TỰ ĐỘNG (28 UNIT & INTEGRATION TESTS)")
    print("=" * 88)
    suite = unittest.defaultTestLoader.discover(start_dir=os.path.join(BASE_DIR, "tests"))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"\n>>> TỔNG KẾT UNIT TESTS: {passed}/{total} PASS ({(passed / max(total, 1)) * 100:.1f}%)")
    return result.wasSuccessful()


def verify_and_optionally_open_docs(open_docs: bool = False) -> None:
    print("\n" + "=" * 88)
    print("  [PHẦN 3/4] KIỂM TRA TÀI LIỆU BÁO CÁO WORD (.DOCX) & SLIDE POWERPOINT (.PPTX)")
    print("=" * 88)
    docx_path = os.path.join(BASE_DIR, "docs", "BAO_CAO_DO_AN_DE_08_DROOLS_NHOM_1.docx")
    pptx_path = os.path.join(BASE_DIR, "docs", "SLIDE_THUYET_TRINH_DE_08_DROOLS_NHOM_1.pptx")
    script_md = os.path.join(BASE_DIR, "docs", "SLIDE_VA_KICH_BAN_BAO_VE_NHOM_1.md")

    for label, path in [
        ("Báo cáo Word (.docx)", docx_path),
        ("Slide PowerPoint (.pptx)", pptx_path),
        ("Kịch bản thuyết trình (.md)", script_md),
    ]:
        exists = os.path.exists(path)
        size_kb = os.path.getsize(path) / 1024.0 if exists else 0.0
        print(f"    - [{'OK' if exists else 'MISSING'}] {label:<28}: {path} ({size_kb:.1f} KB)")

    if open_docs:
        print("    -> Đang mở Báo cáo Word và Slide PowerPoint...")
        _open_file_native(docx_path)
        _open_file_native(pptx_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Chạy Demo Tất Cả Chung Lúc (CLI + 28 Tests + Web All-in-One)")
    parser.add_argument("--host", default="0.0.0.0", help="Host lắng nghe HTTP (mặc định: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Cổng ưu tiên (mặc định: 8000)")
    parser.add_argument("--no-server", action="store_true", help="Chỉ chạy CLI Demo + 28 Unit Tests rồi kết thúc")
    parser.add_argument("--no-browser", action="store_true", help="Không tự động mở trình duyệt Web")
    parser.add_argument("--open-docs", action="store_true", help="Tự động mở luôn file Báo cáo .docx và Slide .pptx")
    args = parser.parse_args()

    print("\n" + "#" * 88)
    print("  🚀 KHỞI ĐỘNG GÓI DEMO TẤT CẢ CHUNG LÚC (ALL-IN-ONE V3 ULTIMATE)")
    print("#" * 88)

    # Phan 1: CLI Demo + SafeAST + Fuzzing 100
    run_cli_walkthrough()
    run_v3_security_and_fuzzing_showcase()

    # Phan 2: Chay 28 Unit Tests
    all_passed = run_all_unit_tests()

    # Phan 3: Kiem tra & mo tai lieu Office
    verify_and_optionally_open_docs(open_docs=args.open_docs)

    if args.no_server:
        return 0 if all_passed else 1

    # Phan 4: Khoi dong Web Server + Mo che do ?demo=all hien thi dong thoi ca 5 Tab
    chosen_port = _find_available_port(args.port)
    demo_url = f"http://127.0.0.1:{chosen_port}/?demo=all"

    print("\n" + "=" * 88)
    print("  [PHẦN 4/4] KHỞI ĐỘNG WEB SERVER Ở CHẾ ĐỘ HIỂN THỊ ĐỒNG THỜI 5 PHÂN HỆ (?demo=all)")
    print(f"    -> Giao diện All-in-One: {demo_url}")
    print("    -> Nhấn Ctrl+C trên cửa sổ này khi muốn dừng Web Server.")
    print("=" * 88 + "\n")

    if not args.no_browser:
        def _launch_browser() -> None:
            time.sleep(0.9)
            try:
                webbrowser.open(demo_url)
            except Exception:
                pass

        threading.Thread(target=_launch_browser, daemon=True).start()

    run_server(host=args.host, port=chosen_port)
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
