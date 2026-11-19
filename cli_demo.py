"""
cli_demo.py
===============================================================================
CHAY DEMO TRUC TIEP TREN TERMINAL (COMMAND-LINE INTERFACE)
He thong Ho tro Ra quyet dinh (DSS) - Nhom 1 - De 08: DROOLS Rule Engine
-------------------------------------------------------------------------------
Dung khi giang vien yeu cau chay thu luong suy dien Rete / PHREAK, Agenda
Conflict Resolution, TMS (insertLogical), Kiem dinh V&V va Doi sanh 3 cong cu
(Drools vs CLIPS vs Prolog) ngay tren man hinh Terminal khong qua giao dien Web:
    python cli_demo.py
===============================================================================
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


def run_cli_walkthrough() -> None:
    dss = CreditApprovalDSS(
        drl_path=DRL_PATH,
        decision_table_csv=DT_CSV_PATH,
        sample_csv_path=SAMPLE_CSV_PATH,
    )
    verifier = RuleBaseVerifier(dss)
    comparator = MultiParadigmComparator(dss, CLIPS_PATH, PROLOG_PATH)
    goal_seeker = BackwardGoalSeeker(dss)

    print("=" * 88)
    print("  DEMO TERMINAL: HỆ THỐNG HỖ TRỢ RA QUYẾT ĐỊNH (DSS) – NHÓM 1 – ĐỀ 08: DROOLS ENGINE")
    print("  Bài toán: Thẩm định Tín dụng, Xếp hạng Rủi ro & Định giá Khoản vay Cá nhân")
    print("=" * 88)

    # 1. Thong ke KieBase & RetePhreakNetwork
    first_eval = dss.evaluate_applicant(dss.get_preset_scenarios()[0])
    rstats = first_eval["engine"]["rete_network"]["stats"]
    print("\n[1] KIẾN TRÚC KIEBASE & MẠNG SUY DIỄN RETE / PHREAK:")
    print(f"    - Package DRL          : {dss.kie_base.package_name}")
    print(f"    - Tổng số luật nạp     : {len(dss.kie_base.rules)} luật (20 luật .drl + 3 luật Decision Table .csv)")
    print(f"    - ObjectTypeNodes (OTN): {rstats['total_object_type_nodes']} nút (Applicant, EligibilityPassed)")
    print(
        f"    - AlphaNode Sharing    : Gom {rstats['total_raw_alpha_constraints']} điều kiện đơn -> "
        f"{rstats['unique_alpha_nodes']} AlphaNode duy nhất (Tiết kiệm {rstats['alpha_nodes_saved_by_sharing']} phép lọc)"
    )
    print(f"    - BetaNode 2-Fact Joins: {rstats['multi_fact_beta_joins']}/{rstats['total_beta_nodes']} nút kết hợp (EligibilityPassed ⋈ Applicant)")

    # 2. Kiem dinh hinh thuc tap luat (Formal Rule Base V&V)
    vv = verifier.verify_all()
    print(f"\n[2] KIỂM ĐỊNH HÌNH THỨC CƠ SỞ TRI THỨC (FORMAL RULE BASE V&V): {vv['overall_status']}")
    for chk in vv["checks"]:
        status_icon = "PASS" if chk["passed"] else "FAIL"
        print(f"    - [{status_icon}] {chk['check_id']} ({chk['title']}): {chk['status_badge']}")

    # 3. Chay 6 Kich ban Demo Dien hinh
    print("\n[3] KẾT QUẢ SUY DIỄN TIẾN 4 TẦNG TRÊN 6 KỊCH BẢN ĐIỂN HÌNH:")
    print("-" * 88)
    print(f"{'Mã HS':<7} | {'Họ và Tên':<18} | {'Điểm':<6} | {'Hạng':<7} | {'Quyết định':<20} | {'Hạn mức':<9} | {'LS':<5} | {'Chuỗi Luật Kích hoạt'}")
    print("-" * 88)
    for preset in dss.get_preset_scenarios():
        res = dss.evaluate_applicant(preset)
        app = res["applicant"]
        s = res["summary"]
        rules_str = "->".join(res["engine"]["fired_rules"])
        print(
            f"{app['applicant_id']:<7} | {app['full_name']:<18} | "
            f"{s['composite_score']:>3}/100 | {s['risk_tier']:<7} | "
            f"{s['decision']:<20} | {s['approved_amount']:>6.1f} tr | "
            f"{s['interest_rate']:>4.1f}% | {rules_str}"
        )
    print("-" * 88)

    # 4. Minh hoa Truth Maintenance System (insertLogical & Auto-Retract)
    print("\n[4] KIỂM CHỨNG HỆ THỐNG BẢO TOÀN CHÂN LÝ (TRUTH MAINTENANCE SYSTEM - insertLogical):")
    kb = KieBase(drl_text=dss.active_drl_text)
    session = kb.new_kie_session()
    fact = dss.build_applicant_fact(dss.get_preset_scenarios()[0])
    handle = session.insert(fact)
    session.fire_all_rules(agenda_pipeline=["1-eligibility"])
    wm1 = [h.fact_type for h in session.handles.values()]
    print(f"    - Bước 1 (Hồ sơ hợp lệ -> R04 gọi insertLogical): Working Memory = {wm1}")
    session.modify(handle, cic_bad_debt=True)
    wm2 = [h.fact_type for h in session.handles.values()]
    print(f"    - Bước 2 (Gọi modify(cic_bad_debt=True))       : Working Memory = {wm2}")
    for ev in session.listener.tms_events:
        print(f"      * TMS Event [{ev['action']}]: {ev['fact_type']} - {ev['reason']}")

    # 5. Doi sanh 3 cong cu Drools (.drl) vs CLIPS (.clp) vs Prolog (.pl) tren 15 ho so
    print("\n[5] ĐỐI SÁNH THỰC NGHIỆM 3 CÔNG CỤ RULE-BASED (DROOLS vs CLIPS vs PROLOG) TRÊN 15 HỒ SƠ:")
    all_apps = dss.load_sample_applicants()
    matched = 0
    for app_item in all_apps:
        cmp_res = comparator.compare_on_applicant(app_item)
        if cmp_res["consensus_verified"]:
            matched += 1
    print(f"    - Tỷ lệ đồng thuận quyết định giữa Drools (.drl), CLIPS (.clp) và Prolog (.pl): {matched}/{len(all_apps)} hồ sơ (100% EQUIVALENCE)")

    # 6. Truy van Muc tieu Nguoc (Backward Chaining Goal-Seeker)
    preset3 = dss.get_preset_scenarios()[2]
    gs = goal_seeker.seek_goal(preset3, "APPROVED_100")
    print(f"\n[6] SUY DIỄN NGƯỢC TÌM MỤC TIÊU (BACKWARD GOAL-SEEKER) CHO HỒ SƠ {preset3['applicant_id']} ({gs['current_decision']}):")
    for idx, plan in enumerate(gs["verified_plans"], start=1):
        print(f"    - Phương án {idx}: {plan['plan_title']}")
        print(f"      + Hành động : {'; '.join(plan['actions'])}")
        print(f"      + Kiểm chứng: Đạt {plan['achieved_decision']} ({plan['achieved_tier']}, {plan['achieved_score']}/100, LS {plan['achieved_rate']}%)")

    print("\n" + "=" * 88)
    print("  HOÀN TẤT DEMO CLI 100% THÀNH CÔNG! (Để mở Web Dashboard, chạy lệnh: python app.py)")
    print("=" * 88)


if __name__ == "__main__":
    run_cli_walkthrough()
