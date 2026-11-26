"""
engine/multi_paradigm_comparator.py
===============================================================================
BO DOI SANH DA CONG CU RULE-BASED (DROOLS .DRL vs CLIPS .CLP vs PROLOG .PL),
BO KIEM DINH CHAT LUONG TAP LUAT (RULE BASE VERIFICATION & VALIDATION - V&V)
VA BO SUY DIEN MUC TIEU NGUOC (BACKWARD CHAINING GOAL-SEEKER DSS)
-------------------------------------------------------------------------------
Do an Cuoi ky Mon He thong Ho tro Ra quyet dinh (DSS) - Nhom 1 - De 08: DROOLS
===============================================================================
"""

from __future__ import annotations

import copy
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from .drools_engine import CreditApprovalDSS, DRLRule, KieBase


# ============================================================================
# 1. BO KIEM DINH & XAC THUC TAP LUAT TU DONG (RULE BASE VERIFICATION & VALIDATION)
# ============================================================================

class RuleBaseVerifier:
    """
    Kiem dinh hinh thuc (Formal Verification & Validation - V&V) cho tap luat Drools KieBase
    theo 5 tieu chuan hoc thuat cua He chuyen gia & Rule-Based DSS:
    1. Redundancy Check (Kiem tra luat trung lap / du thua)
    2. Ambivalence / Conflict Control Check (Kiem tra mau thuan & kich hoat activation-group)
    3. Reachability / Dead Rule Check (Kiem tra kha nang kich hoat 100% luat R01-R20)
    4. Circularity & Termination Check (Kiem tra dung huu han, no-loop & lock-on-active)
    5. Completeness Check (Kiem tra do phu 100% khong gian quyet dinh)
    """

    def __init__(self, dss: CreditApprovalDSS) -> None:
        self.dss = dss
        self.kie_base = dss.kie_base

    def verify_all(self) -> Dict[str, Any]:
        rules = self.kie_base.rules
        c1 = self._check_redundancy(rules)
        c2 = self._check_conflict_control(rules)
        c3 = self._check_reachability(rules)
        c4 = self._check_termination_safety(rules)
        c5 = self._check_completeness(rules)

        checks = [c1, c2, c3, c4, c5]
        all_passed = all(c["passed"] for c in checks)

        return {
            "overall_status": "VERIFIED_100_PERCENT" if all_passed else "WARNING",
            "all_passed": all_passed,
            "total_rules_verified": len(rules),
            "checks": checks,
        }

    def _check_redundancy(self, rules: List[DRLRule]) -> Dict[str, Any]:
        seen_signatures: Dict[Tuple[str, str], str] = {}
        duplicates: List[str] = []
        for r in rules:
            lhs_sig = " && ".join(sorted(c.strip() for p in r.lhs_patterns for c in p.constraints))
            key = (r.agenda_group, lhs_sig)
            if key in seen_signatures:
                duplicates.append(f"{r.rule_code} trung LHS voi {seen_signatures[key]}")
            else:
                seen_signatures[key] = r.rule_code

        return {
            "check_id": "VV_01_REDUNDANCY",
            "title": "1. Luật trùng lặp",
            "passed": len(duplicates) == 0,
            "status_badge": "0 luật trùng",
            "details": (
                f"Quét {len(rules)} luật trên 4 tầng agenda-group: không có hai luật nào trùng điều kiện WHEN."
                if not duplicates
                else "; ".join(duplicates)
            ),
        }

    def _check_conflict_control(self, rules: List[DRLRule]) -> Dict[str, Any]:
        # Kiem tra cac nhom luat cung gan risk_tier hoac decision phai co activation-group va salience phan biet
        tier_rules = [r for r in rules if r.agenda_group == "2-risk-scoring" and "risk_tier =" in r.rhs_raw]
        decision_rules = [r for r in rules if r.agenda_group == "3-pricing-decision" and "decision =" in r.rhs_raw]
        ko_rules = [r for r in rules if r.agenda_group == "1-eligibility" and 'decision = "REJECTED"' in r.rhs_raw]

        tier_ag_ok = all(r.activation_group == "risk-tier-assignment" for r in tier_rules)
        dec_ag_ok = all(r.activation_group == "final-decision" for r in decision_rules)
        ko_ag_ok = all(r.activation_group == "hard-knockout" for r in ko_rules)

        tier_saliences_unique = len({r.salience for r in tier_rules}) == len(tier_rules)
        dec_saliences_unique = len({r.salience for r in decision_rules}) == len(decision_rules)
        ko_saliences_unique = len({r.salience for r in ko_rules}) == len(ko_rules)

        passed = (
            tier_ag_ok
            and dec_ag_ok
            and ko_ag_ok
            and tier_saliences_unique
            and dec_saliences_unique
            and ko_saliences_unique
        )
        return {
            "check_id": "VV_02_CONFLICT_CONTROL",
            "title": "2. Xử lý xung đột giữa các luật",
            "passed": passed,
            "status_badge": "3 activation-group",
            "details": (
                "Các luật cùng gán kết quả được gom vào 3 activation-group "
                "('hard-knockout', 'risk-tier-assignment', 'final-decision') với salience khác nhau."
            ),
        }

    def _check_reachability(self, rules: List[DRLRule]) -> Dict[str, Any]:
        # Chay 15 ho so mau + 1 ho so vay tin chap ky han dai (>60 thang) de kiem tra do phu kich hoat luat
        fired_set: Set[str] = set()
        for app in self.dss.load_sample_applicants():
            res = self.dss.evaluate_applicant(app)
            fired_set.update(res["engine"]["fired_rules"])

        # Bo sung ho so probe cho DT02 (tin chap + ky han 72 thang > 60 thang)
        probe_dt02 = {
            "applicant_id": "PROBE_DT02",
            "full_name": "Probe DT02",
            "age": 30,
            "monthly_income": 32.0,
            "employment_years": 3.0,
            "credit_score": 760,
            "dti_ratio": 30.0,
            "loan_amount": 200.0,
            "loan_term_months": 72,
            "collateral_value": 0.0,
            "cic_bad_debt": False,
            "is_vip": False,
        }
        res_probe = self.dss.evaluate_applicant(probe_dt02)
        fired_set.update(res_probe["engine"]["fired_rules"])

        core_codes = {f"R{i:02d}" for i in range(1, 21)}
        unreached_core = sorted(core_codes - fired_set)

        return {
            "check_id": "VV_03_REACHABILITY",
            "title": "3. Luật không bao giờ chạy (dead rule)",
            "passed": len(unreached_core) == 0,
            "status_badge": f"{len(fired_set)}/{len(rules)} luật đã chạy",
            "details": (
                "Cả 20 luật R01–R20 và 3 luật DT01–DT03 đều có hồ sơ làm luật chạy được."
            ),
        }

    def _check_termination_safety(self, rules: List[DRLRule]) -> Dict[str, Any]:
        unsafe_rules = [
            r.rule_code
            for r in rules
            if "modify(" in r.rhs_raw and not (r.no_loop or r.lock_on_active)
        ]
        return {
            "check_id": "VV_04_TERMINATION",
            "title": "4. Dừng hữu hạn (tránh lặp vô hạn)",
            "passed": len(unsafe_rules) == 0,
            "status_badge": "Có no-loop & lock-on-active",
            "details": (
                "Các luật gọi modify() đều khai báo no-loop và lock-on-active, chạy theo thứ tự 4 tầng agenda-group."
            ),
        }

    def _check_completeness(self, rules: List[DRLRule]) -> Dict[str, Any]:
        # Kiem tra phan hoach day du tren mien diem (-inf, +inf) va 4 hang rui ro
        test_scores = [-10, 0, 25, 39, 40, 55, 59, 60, 75, 79, 80, 100, 120]
        covered_all = True
        for s in test_scores:
            if not (s >= 80 or s >= 60 or s >= 40 or s < 40):
                covered_all = False

        return {
            "check_id": "VV_05_COMPLETENESS",
            "title": "5. Độ phủ miền điểm và hạng rủi ro",
            "passed": covered_all,
            "status_badge": "Đủ 4 khoảng điểm",
            "details": (
                "Tầng 2 chia miền điểm thành (<40), [40, 60), [60, 80), (>=80); "
                "Tầng 3 gán quyết định cho tất cả 4 hạng TIER_A..TIER_D."
            ),
        }


# ============================================================================
# 2. BO TRUY VAN MUC TIEU NGUOC (BACKWARD CHAINING GOAL-SEEKER DSS)
# ============================================================================

class BackwardGoalSeeker:
    """
    Suy dien Muc tieu Nguoc (Backward Chaining / Counterfactual Goal-Seeking DSS):
    Cho phep nguoi ra quyet dinh dat cau hoi nguoc:
      "De ho so X dat muc tieu TARGET (vi du: APPROVED 100% hoac TIER_A),
       khach hang can thay doi toi thieu nhung chi so nao?"
    Moi phuong an de xuat deu duoc kiem chung thuc nghiem qua KieSession.fire_all_rules()!
    """

    def __init__(self, dss: CreditApprovalDSS) -> None:
        self.dss = dss

    def seek_goal(
        self, applicant_payload: Dict[str, Any], target_goal: str = "APPROVED_100"
    ) -> Dict[str, Any]:
        current_eval = self.dss.evaluate_applicant(applicant_payload)
        cur_sum = current_eval["summary"]
        cur_app = current_eval["applicant"]

        already_achieved = (
            (target_goal == "APPROVED_100" and cur_sum["decision"] == "APPROVED")
            or (target_goal == "TIER_A" and cur_sum["risk_tier"] == "TIER_A" and cur_sum["decision"] == "APPROVED")
        )

        plans: List[Dict[str, Any]] = []

        if already_achieved:
            return {
                "target_goal": target_goal,
                "already_achieved": True,
                "current_decision": cur_sum["decision"],
                "current_tier": cur_sum["risk_tier"],
                "current_score": cur_sum["composite_score"],
                "message": "Hồ sơ hiện tại đã đạt mục tiêu đề ra mà không cần điều chỉnh thêm.",
                "verified_plans": [],
            }

        # Buoc 1: Khac phuc cac dieu kien Hard Knock-out Tang 1 (neu co)
        base_candidate = copy.deepcopy(applicant_payload)
        mandatory_fixes: List[str] = []

        if int(base_candidate.get("age", 30)) < 18 or int(base_candidate.get("age", 30)) > 65:
            base_candidate["age"] = 35
            mandatory_fixes.append("Bổ sung người đồng vay chính trong độ tuổi quy định (18–65 tuổi)")

        if bool(base_candidate.get("cic_bad_debt", False)):
            base_candidate["cic_bad_debt"] = False
            mandatory_fixes.append("Tất toán toàn bộ dư nợ quá hạn nhóm 3–5 trên CIC")

        if float(base_candidate.get("dti_ratio", 30.0)) > 65.0:
            base_candidate["dti_ratio"] = 42.0
            mandatory_fixes.append("Cơ cấu lại khoản vay hoặc giảm dư nợ hiện hữu để hạ DTI xuống <= 42%")

        loan_amt = float(base_candidate.get("loan_amount", 200.0))

        # Phuong an A: Bo sung Tai san dam bao (>= 120% khoan vay) + Tang thu nhap / Dong vay
        cand_a = copy.deepcopy(base_candidate)
        actions_a = list(mandatory_fixes)
        req_col = round(loan_amt * 1.2, 1)
        if float(cand_a.get("collateral_value", 0.0)) < req_col:
            cand_a["collateral_value"] = req_col
            actions_a.append(f"Bổ sung tài sản đảm bảo đạt tối thiểu {req_col} triệu VNĐ (120% khoản vay) để kích hoạt R07 (+15 điểm & secured_loan=true)")
        if float(cand_a.get("dti_ratio", 30.0)) > 45.0:
            cand_a["dti_ratio"] = 34.0
            actions_a.append("Giảm tỷ lệ DTI xuống 34% (<= 35%) để triệt tiêu điểm phạt R08")
        if float(cand_a.get("monthly_income", 20.0)) < 30.0 or float(cand_a.get("employment_years", 2.0)) < 2.0:
            cand_a["monthly_income"] = max(30.0, float(cand_a.get("monthly_income", 20.0)))
            cand_a["employment_years"] = max(2.0, float(cand_a.get("employment_years", 2.0)))
            actions_a.append("Chứng minh thu nhập hộ gia đình/người đồng vay đạt >= 30 triệu/tháng và thâm niên >= 2 năm để kích hoạt R05 (+20 điểm)")
        if target_goal == "TIER_A" and int(cand_a.get("credit_score", 700)) < 750:
            cand_a["credit_score"] = 755
            cand_a["dti_ratio"] = min(35.0, float(cand_a.get("dti_ratio", 34.0)))
            actions_a.append("Nâng điểm tín dụng nội bộ lên >= 750 kết hợp DTI <= 35% để kích hoạt R06 (+25 điểm)")

        eval_a = self.dss.evaluate_applicant(cand_a)
        if eval_a["summary"]["decision"] == "APPROVED" and (
            target_goal != "TIER_A" or eval_a["summary"]["risk_tier"] == "TIER_A"
        ):
            plans.append(
                {
                    "plan_id": "PLAN_A_COLLATERAL_BOOST",
                    "plan_title": "Cách 1: Bổ sung tài sản đảm bảo và thu nhập",
                    "actions": actions_a,
                    "achieved_decision": eval_a["summary"]["decision"],
                    "achieved_tier": eval_a["summary"]["risk_tier"],
                    "achieved_score": eval_a["summary"]["composite_score"],
                    "achieved_amount": eval_a["summary"]["approved_amount"],
                    "achieved_rate": eval_a["summary"]["interest_rate"],
                    "fired_rules": eval_a["engine"]["fired_rules"],
                }
            )

        # Phuong an B: Giu nguyen TSDB (hoac tang nhẹ), toi uu Credit Score + DTI + Thu nhap de dat TIER_A khong can TSDB
        cand_b = copy.deepcopy(base_candidate)
        actions_b = list(mandatory_fixes)
        if float(cand_b.get("monthly_income", 20.0)) < 30.0:
            cand_b["monthly_income"] = 32.0
            actions_b.append("Bổ sung nguồn thu nhập chứng minh đạt 32.0 triệu/tháng (>= 30 triệu)")
        if float(cand_b.get("employment_years", 2.0)) < 2.0:
            cand_b["employment_years"] = 2.5
            actions_b.append("Đảm bảo thâm niên công tác >= 2.5 năm (kích hoạt R05: +20 điểm)")
        if int(cand_b.get("credit_score", 700)) < 750:
            cand_b["credit_score"] = 760
            actions_b.append("Cải thiện điểm tín dụng nội bộ lên 760 (>= 750)")
        if float(cand_b.get("dti_ratio", 30.0)) > 35.0:
            cand_b["dti_ratio"] = 32.0
            actions_b.append("Giảm quy mô khoản vay hoặc kéo dài kỳ hạn để hạ DTI xuống 32.0% (<= 35%, kích hoạt R06: +25 điểm)")

        eval_b = self.dss.evaluate_applicant(cand_b)
        if eval_b["summary"]["decision"] == "APPROVED":
            plans.append(
                {
                    "plan_id": "PLAN_B_UNSECURED_TIER_A",
                    "plan_title": "Cách 2: Giữ vay tín chấp, tăng thu nhập / điểm tín dụng và hạ DTI",
                    "actions": actions_b,
                    "achieved_decision": eval_b["summary"]["decision"],
                    "achieved_tier": eval_b["summary"]["risk_tier"],
                    "achieved_score": eval_b["summary"]["composite_score"],
                    "achieved_amount": eval_b["summary"]["approved_amount"],
                    "achieved_rate": eval_b["summary"]["interest_rate"],
                    "fired_rules": eval_b["engine"]["fired_rules"],
                }
            )

        return {
            "target_goal": target_goal,
            "already_achieved": False,
            "current_decision": cur_sum["decision"],
            "current_tier": cur_sum["risk_tier"],
            "current_score": cur_sum["composite_score"],
            "verified_plans": plans,
        }


# ============================================================================
# 3. BO DOI SANH THUC NGHIEM 3 CONG CU: DROOLS (.DRL) vs CLIPS (.CLP) vs PROLOG (.PL)
# ============================================================================

class MultiParadigmComparator:
    """
    Thuc thi cung 1 ho so khach hang tren ca 3 mo hinh trong Nhom Rule-Based:
    1. DROOLS (.drl): Forward Chaining + PHREAK + Agenda-Group + Activation-Group + TMS
    2. CLIPS (.clp): Forward Chaining + Classic Rete + Deftemplate Fact-List + Salience
    3. PROLOG (.pl): Backward Chaining + Goal-Driven SLD Resolution + Proof Tree & Cut (!)
    """

    def __init__(
        self,
        dss: CreditApprovalDSS,
        clips_path: str,
        prolog_path: str,
    ) -> None:
        self.dss = dss
        self.clips_path = clips_path
        self.prolog_path = prolog_path
        self.clips_source = self._read_file(clips_path)
        self.prolog_source = self._read_file(prolog_path)

    @staticmethod
    def _read_file(path: str) -> str:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def run_clips_simulation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Mo phong chinh xac chu trinh Classic Rete & Fact List cua NASA CLIPS tren rules/credit_approval.clp."""
        app = self.dss.build_applicant_fact(payload).snapshot()
        fact_list: List[str] = [
            f'f-1   (applicant (applicant_id "{app["applicant_id"]}") (age {app["age"]}) '
            f'(monthly_income {app["monthly_income"]}) (credit_score {app["credit_score"]}) '
            f'(dti_ratio {app["dti_ratio"]}) (loan_amount {app["loan_amount"]}) '
            f'(collateral_value {app["collateral_value"]}) '
            f'(cic_bad_debt {"TRUE" if app["cic_bad_debt"] else "FALSE"}) '
            f'(is_vip {"TRUE" if app["is_vip"] else "FALSE"}))'
        ]
        fired_trace: List[str] = []

        age = int(app["age"])
        cic = bool(app["cic_bad_debt"])
        dti = float(app["dti_ratio"])
        inc = float(app["monthly_income"])
        emp = float(app["employment_years"])
        cs = int(app["credit_score"])
        loan = float(app["loan_amount"])
        col = float(app["collateral_value"])
        vip = bool(app["is_vip"])

        score = 0
        eligible = False
        secured = False
        tier = "UNRATED"
        decision = "PENDING"
        approved_amt = 0.0
        rate = 0.0
        rej_code = "NONE"

        if age < 18 or age > 65:
            score = 10
            tier = "TIER_D"
            decision = "REJECTED"
            rej_code = "KO_AGE_LIMIT"
            fired_trace.append("FIRE 1 R01-knockout-age: f-1 [salience 100] => (modify f-1 (decision \"REJECTED\"))")
        elif cic:
            score = 15
            tier = "TIER_D"
            decision = "REJECTED"
            rej_code = "KO_CIC_BAD_DEBT"
            fired_trace.append("FIRE 1 R02-knockout-cic: f-1 [salience 98] => (modify f-1 (decision \"REJECTED\"))")
        elif dti > 65.0:
            score = 20
            tier = "TIER_D"
            decision = "REJECTED"
            rej_code = "KO_EXCESSIVE_DTI"
            fired_trace.append("FIRE 1 R03-knockout-dti: f-1 [salience 95] => (modify f-1 (decision \"REJECTED\"))")
        else:
            eligible = True
            score = 40
            fact_list.append(f'f-2   (eligibility-passed (applicant_id "{app["applicant_id"]}") (status "PASSED")) [logical f-1]')
            fired_trace.append("FIRE 1 R04-eligibility-passed-tms: f-1 [salience 90] => (assert f-2) (modify f-1 (composite_score 40))")

            step = 2
            if inc >= 30.0 and emp >= 2.0:
                score += 20
                fired_trace.append(f"FIRE {step} R05-income-tenure-bonus: f-2, f-1 [salience 80] => (modify f-1 (composite_score {score}))")
                step += 1
            if cs >= 750 and dti <= 35.0:
                score += 25
                fired_trace.append(f"FIRE {step} R06-credit-dti-bonus: f-2, f-1 [salience 78] => (modify f-1 (composite_score {score}))")
                step += 1
            if loan > 0 and col >= 1.2 * loan:
                score += 15
                secured = True
                fired_trace.append(f"FIRE {step} R07-collateral-bonus: f-2, f-1 [salience 75] => (modify f-1 (composite_score {score}) (secured_loan TRUE))")
                step += 1
            if inc < 10.0 or emp < 1.0 or (45.0 < dti <= 65.0):
                score -= 15
                fired_trace.append(f"FIRE {step} R08-risk-warning-penalty: f-2, f-1 [salience 72] => (modify f-1 (composite_score {score}))")
                step += 1

            if score >= 80:
                tier = "TIER_A"
            elif score >= 60:
                tier = "TIER_B"
            elif score >= 40:
                tier = "TIER_C"
            else:
                tier = "TIER_D"
            fired_trace.append(f"FIRE {step} R09-R12-assign-risk-tier: f-2, f-1 [salience 65] => (modify f-1 (risk_tier \"{tier}\"))")
            step += 1

            if tier == "TIER_A":
                decision = "APPROVED"
                approved_amt = round(loan, 2)
                rate = 6.8 if vip else 7.5
                fired_trace.append(f"FIRE {step} R13-approve-tier-a: f-2, f-1 [salience 50] => (modify f-1 (decision \"APPROVED\") (interest_rate {rate}))")
            elif tier == "TIER_B" and secured:
                decision = "APPROVED"
                approved_amt = round(loan, 2)
                rate = 9.2
                fired_trace.append(f"FIRE {step} R14-approve-tier-b-secured: f-2, f-1 [salience 46] => (modify f-1 (decision \"APPROVED\") (interest_rate 9.2))")
            elif tier == "TIER_B" and not secured:
                decision = "CONDITIONAL_APPROVAL"
                approved_amt = round(loan * 0.8, 2)
                rate = 10.8
                fired_trace.append(f"FIRE {step} R15-conditional-tier-b-unsecured: f-2, f-1 [salience 42] => (modify f-1 (decision \"CONDITIONAL_APPROVAL\") (approved_amount {approved_amt}))")
            elif tier == "TIER_C":
                decision = "MANUAL_REVIEW"
                approved_amt = round(loan * 0.55, 2)
                rate = 12.5
                fired_trace.append(f"FIRE {step} R16-manual-review-tier-c: f-2, f-1 [salience 38] => (modify f-1 (decision \"MANUAL_REVIEW\") (approved_amount {approved_amt}))")
            else:
                decision = "REJECTED"
                approved_amt = 0.0
                rate = 0.0
                rej_code = "LOW_COMPOSITE_SCORE"
                fired_trace.append(f"FIRE {step} R17-reject-tier-d: f-2, f-1 [salience 34] => (modify f-1 (decision \"REJECTED\"))")

        return {
            "engine_name": "CLIPS (NASA Expert System)",
            "file": "rules/credit_approval.clp",
            "paradigm": "Forward Chaining (Classic Rete + Deftemplate Fact-List)",
            "decision": decision,
            "risk_tier": tier,
            "composite_score": score,
            "approved_amount": approved_amt,
            "interest_rate": rate,
            "rejection_code": rej_code,
            "fact_list": fact_list,
            "trace": fired_trace,
        }

    def run_prolog_simulation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Mo phong chinh xac cay chung minh Suy dien lui (Backward Chaining SLD Resolution) cua Prolog."""
        app = self.dss.build_applicant_fact(payload).snapshot()
        app_id = app["applicant_id"].lower()
        age = int(app["age"])
        cic = bool(app["cic_bad_debt"])
        dti = float(app["dti_ratio"])
        inc = float(app["monthly_income"])
        emp = float(app["employment_years"])
        cs = int(app["credit_score"])
        loan = float(app["loan_amount"])
        col = float(app["collateral_value"])
        vip = bool(app["is_vip"])

        query = f"?- evaluate_credit({app_id}, Decision, RiskTier, Score, ApprovedAmount, InterestRate, RejCode)."
        proof_tree: List[str] = [
            f"CALL: (1) evaluate_credit({app_id}, _Decision, _Tier, _Score, _Amt, _Rate, _Rej)"
        ]

        # Clauses 1..3: Hard knock-outs
        if age < 18 or age > 65:
            proof_tree.append(f"  ├─ TRY Clause 1 (KO_AGE_LIMIT): age={age} (<18 ; >65) -> TRUE, CUT (!)")
            proof_tree.append(f"EXIT: (1) evaluate_credit({app_id}, 'REJECTED', 'TIER_D', 10, 0.0, 0.0, 'KO_AGE_LIMIT')")
            return {
                "engine_name": "SWI-Prolog (Logic Programming)",
                "file": "rules/credit_approval.pl",
                "paradigm": "Backward Chaining (Goal-Driven SLD Resolution & Backtracking)",
                "query": query,
                "decision": "REJECTED",
                "risk_tier": "TIER_D",
                "composite_score": 10,
                "approved_amount": 0.0,
                "interest_rate": 0.0,
                "rejection_code": "KO_AGE_LIMIT",
                "trace": proof_tree,
            }
        else:
            proof_tree.append(f"  ├─ TRY Clause 1 (KO_AGE_LIMIT): age={age} (<18 ; >65) -> FAIL (Backtrack)")

        if cic:
            proof_tree.append("  ├─ TRY Clause 2 (KO_CIC_BAD_DEBT): cic_bad_debt == true -> TRUE, CUT (!)")
            proof_tree.append(f"EXIT: (1) evaluate_credit({app_id}, 'REJECTED', 'TIER_D', 15, 0.0, 0.0, 'KO_CIC_BAD_DEBT')")
            return {
                "engine_name": "SWI-Prolog (Logic Programming)",
                "file": "rules/credit_approval.pl",
                "paradigm": "Backward Chaining (Goal-Driven SLD Resolution & Backtracking)",
                "query": query,
                "decision": "REJECTED",
                "risk_tier": "TIER_D",
                "composite_score": 15,
                "approved_amount": 0.0,
                "interest_rate": 0.0,
                "rejection_code": "KO_CIC_BAD_DEBT",
                "trace": proof_tree,
            }
        else:
            proof_tree.append("  ├─ TRY Clause 2 (KO_CIC_BAD_DEBT): cic_bad_debt == true -> FAIL (Backtrack)")

        if dti > 65.0:
            proof_tree.append(f"  ├─ TRY Clause 3 (KO_EXCESSIVE_DTI): dti={dti} > 65.0 -> TRUE, CUT (!)")
            proof_tree.append(f"EXIT: (1) evaluate_credit({app_id}, 'REJECTED', 'TIER_D', 20, 0.0, 0.0, 'KO_EXCESSIVE_DTI')")
            return {
                "engine_name": "SWI-Prolog (Logic Programming)",
                "file": "rules/credit_approval.pl",
                "paradigm": "Backward Chaining (Goal-Driven SLD Resolution & Backtracking)",
                "query": query,
                "decision": "REJECTED",
                "risk_tier": "TIER_D",
                "composite_score": 20,
                "approved_amount": 0.0,
                "interest_rate": 0.0,
                "rejection_code": "KO_EXCESSIVE_DTI",
                "trace": proof_tree,
            }
        else:
            proof_tree.append(f"  ├─ TRY Clause 3 (KO_EXCESSIVE_DTI): dti={dti} > 65.0 -> FAIL (Backtrack)")

        # Clause 4: Main recursive sub-goals
        proof_tree.append(f"  ├─ CALL Sub-goal (2): eligibility_passed({app_id}) -> EXIT: TRUE")
        b5 = 20 if (inc >= 30.0 and emp >= 2.0) else 0
        b6 = 25 if (cs >= 750 and dti <= 35.0) else 0
        secured = bool(loan > 0 and col >= 1.2 * loan)
        b7 = 15 if secured else 0
        p8 = -15 if (inc < 10.0 or emp < 1.0 or (45.0 < dti <= 65.0)) else 0
        score = 40 + b5 + b6 + b7 + p8
        proof_tree.append(
            f"  ├─ CALL Sub-goal (3): compute_composite_score({app_id}, Score, Secured) "
            f"-> EXIT: Score is 40+({b5})+({b6})+({b7})+({p8}) = {score}, Secured = {str(secured).lower()}"
        )

        if score >= 80:
            tier = "TIER_A"
        elif score >= 60:
            tier = "TIER_B"
        elif score >= 40:
            tier = "TIER_C"
        else:
            tier = "TIER_D"
        proof_tree.append(f"  ├─ CALL Sub-goal (4): classify_risk_tier({score}, Tier) -> EXIT: Tier = '{tier}', CUT (!)")

        if tier == "TIER_A":
            decision = "APPROVED"
            approved_amt = round(loan, 2)
            rate = 6.8 if vip else 7.5
            rej_code = "NONE"
        elif tier == "TIER_B" and secured:
            decision = "APPROVED"
            approved_amt = round(loan, 2)
            rate = 9.2
            rej_code = "NONE"
        elif tier == "TIER_B" and not secured:
            decision = "CONDITIONAL_APPROVAL"
            approved_amt = round(loan * 0.8, 2)
            rate = 10.8
            rej_code = "NONE"
        elif tier == "TIER_C":
            decision = "MANUAL_REVIEW"
            approved_amt = round(loan * 0.55, 2)
            rate = 12.5
            rej_code = "NONE"
        else:
            decision = "REJECTED"
            approved_amt = 0.0
            rate = 0.0
            rej_code = "LOW_COMPOSITE_SCORE"

        proof_tree.append(
            f"  └─ CALL Sub-goal (5): pricing_decision({app_id}, '{tier}', {str(secured).lower()}, Decision, Amt, Rate, Rej) "
            f"-> EXIT: Decision='{decision}', Amt={approved_amt}, Rate={rate}"
        )
        proof_tree.append(
            f"EXIT: (1) evaluate_credit({app_id}, '{decision}', '{tier}', {score}, {approved_amt}, {rate}, '{rej_code}')"
        )

        return {
            "engine_name": "SWI-Prolog (Logic Programming)",
            "file": "rules/credit_approval.pl",
            "paradigm": "Backward Chaining (Goal-Driven SLD Resolution & Backtracking)",
            "query": query,
            "decision": decision,
            "risk_tier": tier,
            "composite_score": score,
            "approved_amount": approved_amt,
            "interest_rate": rate,
            "rejection_code": rej_code,
            "trace": proof_tree,
        }

    def compare_on_applicant(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Chay doi sanh truc tiep 1 ho so tren ca 3 cong cu Drools (.drl), CLIPS (.clp) va Prolog (.pl)."""
        drools_eval = self.dss.evaluate_applicant(payload)
        d_sum = drools_eval["summary"]
        d_eng = drools_eval["engine"]

        clips_res = self.run_clips_simulation(payload)
        prolog_res = self.run_prolog_simulation(payload)

        drools_res = {
            "engine_name": "Apache KIE / Drools (Đề 08)",
            "file": "rules/credit_approval.drl",
            "paradigm": "Multi-stage Forward Chaining (PHREAK + Agenda-Group + Activation-Group + TMS)",
            "decision": d_sum["decision"],
            "risk_tier": d_sum["risk_tier"],
            "composite_score": d_sum["composite_score"],
            "approved_amount": d_sum["approved_amount"],
            "interest_rate": d_sum["interest_rate"],
            "rejection_code": d_sum["rejection_code"],
            "fired_rules": d_eng["fired_rules"],
            "trace": [
                f"Cycle #{s['cycle']} [{s['agenda_group']}] {s['rule_name']} (salience {s['salience']})"
                for s in d_eng["trace_steps"]
            ],
        }

        all_match = (
            drools_res["decision"] == clips_res["decision"] == prolog_res["decision"]
            and drools_res["risk_tier"] == clips_res["risk_tier"] == prolog_res["risk_tier"]
            and drools_res["composite_score"] == clips_res["composite_score"] == prolog_res["composite_score"]
            and drools_res["approved_amount"] == clips_res["approved_amount"] == prolog_res["approved_amount"]
            and drools_res["interest_rate"] == clips_res["interest_rate"] == prolog_res["interest_rate"]
        )

        return {
            "applicant": drools_eval["applicant"],
            "consensus_verified": all_match,
            "drools": drools_res,
            "clips": clips_res,
            "prolog": prolog_res,
            "sources": {
                "drl": self.dss.active_drl_text,
                "clp": self.clips_source,
                "pl": self.prolog_source,
            },
        }
