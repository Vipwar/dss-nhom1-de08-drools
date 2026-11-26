"""
cli_demo.py - chạy thử hệ thống trên terminal (không cần mở web).

    python cli_demo.py
"""

from __future__ import annotations

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from engine.drools_engine import CreditApprovalDSS, KieBase
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


def section(title: str) -> None:
    print(f"\n--- {title} ---")


def run_cli_walkthrough() -> None:
    dss = CreditApprovalDSS(
        drl_path=DRL_PATH,
        decision_table_csv=DT_CSV_PATH,
        sample_csv_path=SAMPLE_CSV_PATH,
    )
    verifier = RuleBaseVerifier(dss)
    comparator = MultiParadigmComparator(dss, CLIPS_PATH, PROLOG_PATH)
    goal_seeker = BackwardGoalSeeker(dss)

    print("Thẩm định tín dụng bằng Drools - Nhóm 1 - Đề 08")

    # 1. Tập luật và mạng Rete
    first_eval = dss.evaluate_applicant(dss.get_preset_scenarios()[0])
    rstats = first_eval["engine"]["rete_network"]["stats"]
    section("1. Tập luật và mạng Rete")
    print(f"Package: {dss.kie_base.package_name}")
    print(f"Số luật: {len(dss.kie_base.rules)} (20 trong .drl, 3 trong bảng quyết định .csv)")
    print(f"ObjectTypeNode: {rstats['total_object_type_nodes']}")
    print(
        f"AlphaNode: {rstats['total_raw_alpha_constraints']} điều kiện gộp còn {rstats['unique_alpha_nodes']} nút "
        f"(dùng chung {rstats['alpha_nodes_saved_by_sharing']})"
    )
    print(f"Cache AlphaNode: {rstats['cache_hits']} lần trúng ({rstats['cache_hit_rate_percent']}%)")
    print(f"BetaNode join 2 fact: {rstats['multi_fact_beta_joins']}/{rstats['total_beta_nodes']}")

    # 2. Kiểm tra tập luật
    vv = verifier.verify_all()
    section("2. Kiểm tra tập luật (V&V)")
    for chk in vv["checks"]:
        print(f"[{'đạt' if chk['passed'] else 'lỗi'}] {chk['title']}")

    # 3. Sáu hồ sơ mẫu
    section("3. Kết quả 6 hồ sơ mẫu")
    header = f"{'Mã':<7} {'Họ tên':<17} {'Điểm':>4} {'Hạng':<6} {'Quyết định':<20} {'Hạn mức':>8} {'PD%':>6} {'EL':>6} {'RAROC%':>7}  Luật"
    print(header)
    for preset in dss.get_preset_scenarios():
        res = dss.evaluate_applicant(preset)
        app = res["applicant"]
        s = res["summary"]
        print(
            f"{app['applicant_id']:<7} {app['full_name']:<17} {s['composite_score']:>4} {s['risk_tier']:<6} "
            f"{s['decision']:<20} {s['ead_amount']:>8.1f} {s['pd_percent']:>6.2f} {s['expected_loss']:>6.2f} "
            f"{s['raroc_percent']:>7.1f}  {' '.join(res['engine']['fired_rules'])}"
        )
    print("(Hạn mức và EL tính bằng triệu đồng)")

    # 4. TMS
    section("4. TMS (insertLogical)")
    kb = KieBase(drl_text=dss.active_drl_text)
    session = kb.new_kie_session()
    fact = dss.build_applicant_fact(dss.get_preset_scenarios()[0])
    handle = session.insert(fact)
    session.fire_all_rules(agenda_pipeline=["1-eligibility"])
    wm1 = [h.fact_type for h in session.handles.values()]
    print(f"Sau tầng 1: {wm1}")
    session.modify(handle, cic_bad_debt=True)
    wm2 = [h.fact_type for h in session.handles.values()]
    print(f"Sau khi đặt cic_bad_debt=True: {wm2}")
    print("-> EligibilityPassed tự bị rút lại vì điều kiện của R04 không còn đúng.")

    # 5. So sánh với CLIPS và Prolog
    section("5. So sánh Drools / CLIPS / Prolog")
    all_apps = dss.load_sample_applicants()
    matched = sum(1 for a in all_apps if comparator.compare_on_applicant(a)["consensus_verified"])
    print(f"Khớp {matched}/{len(all_apps)} hồ sơ")

    # 6. Suy diễn ngược
    preset3 = dss.get_preset_scenarios()[2]
    gs = goal_seeker.seek_goal(preset3, "APPROVED_100")
    section(f"6. Suy diễn ngược cho {preset3['applicant_id']} (hiện tại: {gs['current_decision']})")
    for idx, plan in enumerate(gs["verified_plans"], start=1):
        print(f"Cách {idx}: {'; '.join(plan['actions'])}")
        print(f"   -> {plan['achieved_decision']}, hạng {plan['achieved_tier']}, điểm {plan['achieved_score']}, lãi suất {plan['achieved_rate']}%")

    # 7. Stress test
    stress = dss.run_portfolio_stress_test(income_shock_pct=-20.0, collateral_shock_pct=-25.0, dti_shock_pts=12.0)
    imp = stress["impact_summary"]
    section("7. Stress test (thu nhập -20%, TSĐB -25%, DTI +12)")
    print(
        f"Tổng hạn mức: {stress['baseline_portfolio']['total_approved_amount']} -> "
        f"{stress['stressed_portfolio']['total_approved_amount']} triệu"
    )
    print(
        f"Tổng EL: {stress['baseline_portfolio']['total_expected_loss']:.2f} -> "
        f"{stress['stressed_portfolio']['total_expected_loss']:.2f} triệu"
    )
    print(f"Số hồ sơ bị hạ hạng: {imp['downgraded_count']}/{stress['total_applicants']}")
    tiers = ["TIER_A", "TIER_B", "TIER_C", "TIER_D"]
    matrix = stress["risk_migration_matrix"]
    print("Trước \\ Sau  " + "  ".join(t[-1] for t in tiers))
    for t in tiers:
        print(f"     {t[-1]}       " + "  ".join(str(matrix[t][u]) for u in tiers))

    print("\nXong. Chạy `python app.py` để mở giao diện web.")


if __name__ == "__main__":
    run_cli_walkthrough()
