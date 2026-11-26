"""
demo_all.py - chạy toàn bộ phần demo bằng một lệnh:
  1. In kết quả ra terminal (cli_demo.py + kiểm tra SafeAST + 100 hồ sơ ngẫu nhiên)
  2. Chạy 28 test
  3. Kiểm tra file báo cáo .docx và slide .pptx
  4. Bật web server và mở trình duyệt ở chế độ xem tất cả (?demo=all)

    python demo_all.py               # chạy hết
    python demo_all.py --open-docs   # mở thêm file Word và PowerPoint
    python demo_all.py --no-server   # chỉ chạy phần terminal và test
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
from cli_demo import CLIPS_PATH, DRL_PATH, DT_CSV_PATH, PROLOG_PATH, SAMPLE_CSV_PATH, run_cli_walkthrough, section
from engine.drools_engine import CreditApprovalDSS, SafeASTEvaluator, UnsafeDRLExpressionError
from engine.multi_paradigm_comparator import MultiParadigmComparator


def find_free_port(preferred: int = 8000) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if sock.connect_ex(("127.0.0.1", preferred)) != 0:
            return preferred
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def open_file(path: str) -> None:
    if not os.path.exists(path):
        return
    try:
        if platform.system() == "Windows":
            os.startfile(path)  # type: ignore[attr-defined]
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as exc:
        print(f"Không mở được {path}: {exc}")


def security_and_fuzzing() -> None:
    dss = CreditApprovalDSS(drl_path=DRL_PATH, decision_table_csv=DT_CSV_PATH, sample_csv_path=SAMPLE_CSV_PATH)
    comparator = MultiParadigmComparator(dss, CLIPS_PATH, PROLOG_PATH)
    evaluator = SafeASTEvaluator()
    fact = dss.build_applicant_fact(dss.get_preset_scenarios()[0])

    section("8. Thử chèn mã độc vào biểu thức DRL")
    for payload in [
        "__import__('os').system('calc') == 0",
        "().__class__.__bases__[0].__subclasses__()",
        "open('/etc/passwd').read() != ''",
    ]:
        try:
            evaluator.evaluate(payload, fact_obj=fact, bindings={"$app": fact})
            print(f"KHÔNG chặn được: {payload}")
        except UnsafeDRLExpressionError:
            print(f"Đã chặn: {payload}")

    edge = dss.build_applicant_fact({"loan_term_months": 0, "monthly_income": -50, "loan_amount": 0})
    print(
        f"Dữ liệu lỗi (kỳ hạn 0, thu nhập -50, vay 0) được chỉnh thành: "
        f"kỳ hạn {edge.loan_term_months}, thu nhập {edge.monthly_income}, vay {edge.loan_amount}"
    )

    section("9. 100 hồ sơ ngẫu nhiên: so sánh Drools / CLIPS / Prolog")
    rng = random.Random(20260801)
    matched = 0
    for idx in range(100):
        applicant = {
            "applicant_id": f"RND{idx + 1:03d}",
            "full_name": f"Khach {idx + 1}",
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
        if comparator.compare_on_applicant(applicant)["consensus_verified"]:
            matched += 1
    print(f"Khớp {matched}/100 hồ sơ")


def run_tests() -> bool:
    section("Chạy test")
    suite = unittest.defaultTestLoader.discover(start_dir=os.path.join(BASE_DIR, "tests"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    print(f"Kết quả: {passed}/{result.testsRun} test đạt")
    return result.wasSuccessful()


def check_docs(open_docs: bool) -> None:
    section("Tài liệu")
    files = [
        os.path.join(BASE_DIR, "docs", "BAO_CAO_DO_AN_DE_08_DROOLS_NHOM_1.docx"),
        os.path.join(BASE_DIR, "docs", "SLIDE_THUYET_TRINH_DE_08_DROOLS_NHOM_1.pptx"),
    ]
    for path in files:
        if os.path.exists(path):
            print(f"{os.path.basename(path)} ({os.path.getsize(path) / 1024:.0f} KB)")
        else:
            print(f"Thiếu file: {os.path.basename(path)}")
    if open_docs:
        for path in files:
            open_file(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Chạy toàn bộ demo")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-server", action="store_true", help="không bật web server")
    parser.add_argument("--no-browser", action="store_true", help="không tự mở trình duyệt")
    parser.add_argument("--open-docs", action="store_true", help="mở file Word và PowerPoint")
    args = parser.parse_args()

    run_cli_walkthrough()
    security_and_fuzzing()
    ok = run_tests()
    check_docs(args.open_docs)

    if args.no_server:
        return 0 if ok else 1

    port = find_free_port(args.port)
    url = f"http://127.0.0.1:{port}/?demo=all"
    section("Web")
    print(f"Mở trình duyệt tại {url}  (Ctrl+C để dừng)")

    if not args.no_browser:
        def _open() -> None:
            time.sleep(0.9)
            try:
                webbrowser.open(url)
            except Exception:
                pass

        threading.Thread(target=_open, daemon=True).start()

    run_server(host=args.host, port=port)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
