"""
tests/test_drools_engine.py
===============================================================================
BO KIEM THU TU DONG TOAN DIEN (22 UNIT & INTEGRATION TESTS) CHO DROOLS ENGINE,
RULE BASE V&V, BACKWARD CHAINING GOAL-SEEKER & DOI SANH DROOLS vs CLIPS vs PROLOG
-------------------------------------------------------------------------------
Do an Cuoi ky Mon He thong Ho tro Ra quyet dinh (DSS) - Nhom 1 - De 08: DROOLS
Chay bang lenh:
    python -m unittest discover -s tests -v
===============================================================================
"""

import os
import unittest

from engine.drools_engine import (
    CreditApprovalDSS,
    DecisionTableLoader,
    DRLParser,
    Fact,
    KieBase,
)
from engine.multi_paradigm_comparator import (
    BackwardGoalSeeker,
    MultiParadigmComparator,
    RuleBaseVerifier,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRL_PATH = os.path.join(BASE_DIR, "rules", "credit_approval.drl")
CLIPS_PATH = os.path.join(BASE_DIR, "rules", "credit_approval.clp")
PROLOG_PATH = os.path.join(BASE_DIR, "rules", "credit_approval.pl")
DT_CSV_PATH = os.path.join(BASE_DIR, "rules", "decision_table_rules.csv")
SAMPLE_CSV_PATH = os.path.join(BASE_DIR, "data", "sample_applicants.csv")


class TestDroolsEngineAndCreditDSS(unittest.TestCase):
    """Bo kiem thu 22 test cases kiem chung toan bo kien truc Drools, CLIPS, Prolog & DSS."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.dss = CreditApprovalDSS(
            drl_path=DRL_PATH,
            decision_table_csv=DT_CSV_PATH,
            sample_csv_path=SAMPLE_CSV_PATH,
        )
        cls.applicants = {
            row["applicant_id"]: row for row in cls.dss.load_sample_applicants()
        }
        cls.verifier = RuleBaseVerifier(cls.dss)
        cls.goal_seeker = BackwardGoalSeeker(cls.dss)
        cls.comparator = MultiParadigmComparator(
            dss=cls.dss,
            clips_path=CLIPS_PATH,
            prolog_path=PROLOG_PATH,
        )

    def test_01_drl_parser_metadata_and_rules(self) -> None:
        """Kiem thu DRLParser: doc dung package, declare types va 20 luat R01-R20."""
        parser = DRLParser()
        pkg, imports, declared_types, rules = parser.parse_file(DRL_PATH)

        self.assertEqual(pkg, "vn.edu.dss.nhom1.credit")
        self.assertGreaterEqual(len(imports), 2)
        self.assertIn("Applicant", declared_types)
        self.assertIn("EligibilityPassed", declared_types)
        self.assertEqual(len(rules), 20)

        r01 = rules[0]
        self.assertEqual(r01.rule_code, "R01")
        self.assertEqual(r01.salience, 100)
        self.assertEqual(r01.agenda_group, "1-eligibility")
        self.assertEqual(r01.activation_group, "hard-knockout")
        self.assertTrue(r01.no_loop)
        self.assertTrue(r01.lock_on_active)

        r09 = next(r for r in rules if r.rule_code == "R09")
        self.assertEqual(r09.agenda_group, "2-risk-scoring")
        self.assertEqual(r09.activation_group, "risk-tier-assignment")
        self.assertEqual(r09.salience, 68)

    def test_02_decision_table_loader(self) -> None:
        """Kiem thu DecisionTableLoader: nap dung cac luat bo sung DT01-DT03 tu CSV."""
        loader = DecisionTableLoader()
        dt_rules = loader.load_csv(DT_CSV_PATH)
        self.assertEqual(len(dt_rules), 3)
        self.assertEqual(dt_rules[0].rule_code, "DT01")
        self.assertEqual(dt_rules[0].agenda_group, "4-dss-explanation")

    def test_03_rete_phreak_network_and_alpha_sharing(self) -> None:
        """Kiem thu RetePhreakNetwork: tao OTN, AlphaNode Sharing, BetaNode Join va RTN."""
        net_json = self.dss.kie_base.network.to_json()
        stats = net_json["stats"]

        self.assertGreaterEqual(stats["total_object_type_nodes"], 2)
        self.assertGreater(stats["unique_alpha_nodes"], 10)
        self.assertGreater(stats["shared_alpha_nodes"], 0)
        self.assertGreater(stats["alpha_nodes_saved_by_sharing"], 0)
        self.assertEqual(stats["multi_fact_beta_joins"], 13)
        self.assertEqual(stats["total_terminal_nodes"], 23)

    def test_04_conflict_resolution_salience_and_activation_group(self) -> None:
        """Kiem thu Conflict Resolution: APP015 vi pham ca CIC (R02, sal=98) va DTI (R03, sal=95)."""
        res = self.dss.evaluate_applicant(self.applicants["APP015"])
        fired = res["engine"]["fired_rules"]
        cancelled = res["engine"]["cancelled_activations"]

        self.assertIn("R02", fired)
        self.assertNotIn("R03", fired)
        self.assertEqual(res["summary"]["rejection_code"], "KO_CIC_BAD_DEBT")
        cancelled_codes = [c["cancelled_rule_code"] for c in cancelled]
        self.assertIn("R03", cancelled_codes)

    def test_05_no_loop_and_lock_on_active_prevent_infinite_loop(self) -> None:
        """Kiem thu no-loop va lock-on-active: modify() trong khoi THEN khong gay lap vo han."""
        custom_drl = """
        package test.loop;
        rule "L01 - Self modifying rule with no-loop"
            salience 50
            agenda-group "1-eligibility"
            no-loop true
        when
            $app : Applicant( composite_score < 100 )
        then
            modify($app) {
                composite_score = $app.composite_score + 10
            }
        end
        """
        kb = KieBase(drl_text=custom_drl)
        session = kb.new_kie_session()
        fact = Fact(fact_type="Applicant", composite_score=10)
        session.insert(fact)
        out = session.fire_all_rules(max_cycles=20, agenda_pipeline=["1-eligibility"])

        self.assertEqual(out["total_cycles"], 1)
        self.assertEqual(fact.composite_score, 20)

    def test_06_truth_maintenance_system_insert_logical_auto_retract(self) -> None:
        """Kiem thu TMS (insertLogical): Fact suy dien EligibilityPassed tu dong bi rut lai khi dieu kien goc sai."""
        kb = KieBase(drl_path=DRL_PATH)
        session = kb.new_kie_session()
        app_fact = self.dss.build_applicant_fact(self.applicants["APP001"])
        handle = session.insert(app_fact)

        session.fire_all_rules(agenda_pipeline=["1-eligibility"])
        elig_facts_before = session.get_facts("EligibilityPassed")
        self.assertEqual(len(elig_facts_before), 1)
        self.assertEqual(elig_facts_before[0].status, "PASSED")

        session.modify(handle, cic_bad_debt=True)
        elig_facts_after = session.get_facts("EligibilityPassed")
        self.assertEqual(len(elig_facts_after), 0)

        tms_actions = [e["action"] for e in session.listener.tms_events]
        self.assertIn("INSERT_LOGICAL", tms_actions)
        self.assertIn("AUTO_RETRACT_LOGICAL", tms_actions)

    def test_07_scenario_1_vip_tier_a_approved_and_large_loan_r18(self) -> None:
        """Kich ban 1 (APP001 - VIP Hang A, vay 500tr): Duyet 100%, lai suat 6.8%, kich hoat R18 & DT01."""
        res = self.dss.evaluate_applicant(self.applicants["APP001"])
        summ = res["summary"]
        fired = res["engine"]["fired_rules"]

        self.assertEqual(summ["decision"], "APPROVED")
        self.assertEqual(summ["risk_tier"], "TIER_A")
        self.assertEqual(summ["composite_score"], 100)
        self.assertEqual(summ["approved_amount"], 500.0)
        self.assertEqual(summ["interest_rate"], 6.8)
        self.assertTrue(summ["independent_valuation_required"])
        self.assertEqual(fired, ["R04", "R05", "R06", "R07", "R09", "R13", "R18", "DT01"])

        cancelled_codes = [c["cancelled_rule_code"] for c in res["engine"]["cancelled_activations"]]
        self.assertIn("R10", cancelled_codes)
        self.assertIn("R11", cancelled_codes)

    def test_08_scenario_2_tier_b_secured_approved(self) -> None:
        """Kich ban 2 (APP002 - Hang B co TSDB): Duyet 100% han muc, lai suat 9.2%/nam."""
        res = self.dss.evaluate_applicant(self.applicants["APP002"])
        summ = res["summary"]
        fired = res["engine"]["fired_rules"]

        self.assertEqual(summ["decision"], "APPROVED")
        self.assertEqual(summ["risk_tier"], "TIER_B")
        self.assertEqual(summ["composite_score"], 75)
        self.assertTrue(summ["secured_loan"])
        self.assertEqual(summ["approved_amount"], 300.0)
        self.assertEqual(summ["interest_rate"], 9.2)
        self.assertEqual(fired, ["R04", "R05", "R07", "R10", "R14"])

    def test_09_scenario_3_tier_b_unsecured_conditional_approval(self) -> None:
        """Kich ban 3 (APP003 - Hang B vay tin chap): Duyet co dieu kien 80% han muc (160tr), lai suat 10.8%."""
        res = self.dss.evaluate_applicant(self.applicants["APP003"])
        summ = res["summary"]
        fired = res["engine"]["fired_rules"]

        self.assertEqual(summ["decision"], "CONDITIONAL_APPROVAL")
        self.assertEqual(summ["risk_tier"], "TIER_B")
        self.assertEqual(summ["composite_score"], 65)
        self.assertFalse(summ["secured_loan"])
        self.assertEqual(summ["approved_amount"], 160.0)
        self.assertEqual(summ["interest_rate"], 10.8)
        self.assertEqual(fired, ["R04", "R06", "R10", "R15", "R19"])

    def test_10_scenario_4_tier_c_conflict_manual_review(self) -> None:
        """Kich ban 4 (APP004 - Ho so xung dot R05 +20 va R08 -15): Hang C, Chuyen tham dinh thu cong."""
        res = self.dss.evaluate_applicant(self.applicants["APP004"])
        summ = res["summary"]
        fired = res["engine"]["fired_rules"]

        self.assertEqual(summ["decision"], "MANUAL_REVIEW")
        self.assertEqual(summ["risk_tier"], "TIER_C")
        self.assertEqual(summ["composite_score"], 45)
        self.assertEqual(summ["approved_amount"], 137.5)
        self.assertEqual(summ["interest_rate"], 12.5)
        self.assertEqual(fired, ["R04", "R05", "R08", "R11", "R16", "R19", "DT03"])

    def test_11_scenario_5_hard_knockout_cic_bad_debt(self) -> None:
        """Kich ban 5 (APP005 - No xau CIC): Tu choi ngay o Tang 1 (R02), bo qua Tang 2 & Tang 3."""
        res = self.dss.evaluate_applicant(self.applicants["APP005"])
        summ = res["summary"]
        fired = res["engine"]["fired_rules"]

        self.assertEqual(summ["decision"], "REJECTED")
        self.assertFalse(summ["eligible"])
        self.assertEqual(summ["rejection_code"], "KO_CIC_BAD_DEBT")
        self.assertEqual(summ["approved_amount"], 0.0)
        self.assertEqual(fired, ["R02", "R20"])

    def test_12_scenario_6_hard_knockout_high_dti(self) -> None:
        """Kich ban 6 (APP006 - DTI 71.5% > 65%): Tu choi ngay o Tang 1 (R03), bo qua Tang 2 & Tang 3."""
        res = self.dss.evaluate_applicant(self.applicants["APP006"])
        summ = res["summary"]
        fired = res["engine"]["fired_rules"]

        self.assertEqual(summ["decision"], "REJECTED")
        self.assertFalse(summ["eligible"])
        self.assertEqual(summ["rejection_code"], "KO_EXCESSIVE_DTI")
        self.assertEqual(summ["approved_amount"], 0.0)
        self.assertEqual(fired, ["R03", "R20"])

    def test_13_age_knockout_r01_and_layer3_tier_d_rejection_r17(self) -> None:
        """Kiem thu R01 (Qua tuoi 68 > 65) va R12 -> R17 (Tu choi o Tang 3 do diem TIER_D = 25 < 40)."""
        res_age = self.dss.evaluate_applicant(self.applicants["APP012"])
        self.assertEqual(res_age["summary"]["decision"], "REJECTED")
        self.assertEqual(res_age["summary"]["rejection_code"], "KO_AGE_LIMIT")
        self.assertEqual(res_age["engine"]["fired_rules"], ["R01", "R20"])

        res_tier_d = self.dss.evaluate_applicant(self.applicants["APP011"])
        self.assertTrue(res_tier_d["summary"]["eligible"])
        self.assertEqual(res_tier_d["summary"]["composite_score"], 25)
        self.assertEqual(res_tier_d["summary"]["risk_tier"], "TIER_D")
        self.assertEqual(res_tier_d["summary"]["decision"], "REJECTED")
        self.assertEqual(res_tier_d["summary"]["rejection_code"], "LOW_COMPOSITE_SCORE")
        self.assertEqual(res_tier_d["engine"]["fired_rules"], ["R04", "R08", "R12", "R17", "R20"])

    def test_14_what_if_and_sensitivity_analysis(self) -> None:
        """Kiem thu What-If Simulator: Bo sung TSDB cho APP003 giup nang tu CONDITIONAL len APPROVED 100%."""
        baseline = dict(self.applicants["APP003"])
        what_if = dict(self.applicants["APP003"])
        what_if["collateral_value"] = 300.0

        sim = self.dss.run_what_if(baseline, what_if)
        self.assertEqual(sim["baseline"]["summary"]["decision"], "CONDITIONAL_APPROVAL")
        self.assertEqual(sim["what_if"]["summary"]["decision"], "APPROVED")
        self.assertEqual(sim["comparison"]["score_delta"], 15)
        self.assertTrue(sim["comparison"]["decision_changed"])
        self.assertIn("R07", sim["comparison"]["added_rules"])
        self.assertEqual(len(sim["sensitivity_curve"]), 6)

    def test_15_batch_csv_portfolio_evaluation(self) -> None:
        """Kiem thu Batch Evaluation: Cham diem toan bo 15 ho so trong data/sample_applicants.csv."""
        batch = self.dss.evaluate_batch()
        self.assertEqual(batch["total_applicants"], 15)
        self.assertEqual(len(batch["items"]), 15)
        total_decisions = sum(batch["decision_counts"].values())
        self.assertEqual(total_decisions, 15)
        self.assertGreater(batch["decision_counts"]["APPROVED"], 0)
        self.assertGreater(batch["decision_counts"]["CONDITIONAL_APPROVAL"], 0)
        self.assertGreater(batch["decision_counts"]["MANUAL_REVIEW"], 0)
        self.assertGreater(batch["decision_counts"]["REJECTED"], 0)

    def test_16_live_drl_hot_reload(self) -> None:
        """Kiem thu Live DRL Studio: Bien dich lai ma nguon .drl truc tiep tren bo nho."""
        info = self.dss.reload_drl(self.dss.active_drl_text, save_to_disk=False)
        self.assertEqual(info["status"], "SUCCESS")
        self.assertEqual(info["total_rules"], 23)

    def test_17_web_server_rest_api_endpoints(self) -> None:
        """Kiem thu Web Server & REST API trong app.py."""
        import json
        import threading
        import urllib.request
        from http.server import ThreadingHTTPServer
        from app import DroolsDSSRequestHandler

        server = ThreadingHTTPServer(("127.0.0.1", 0), DroolsDSSRequestHandler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            base_url = f"http://127.0.0.1:{port}"
            with urllib.request.urlopen(f"{base_url}/") as resp:
                self.assertEqual(resp.status, 200)
                html = resp.read().decode("utf-8")
                self.assertIn("Drools Credit Approval", html)

            with urllib.request.urlopen(f"{base_url}/api/overview") as resp:
                self.assertEqual(resp.status, 200)
                overview = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(overview["status"], "OK")
                self.assertEqual(len(overview["presets"]), 6)
                self.assertEqual(len(overview["sample_applicants"]), 15)
                self.assertTrue(overview["rule_verification"]["all_passed"])
        finally:
            server.shutdown()
            server.server_close()

    def test_18_rule_base_verification_and_validation_5_checks(self) -> None:
        """Kiem thu Formal Rule Base Verification & Validation (5 tieu chuan V&V)."""
        vv = self.verifier.verify_all()
        self.assertTrue(vv["all_passed"])
        self.assertEqual(vv["overall_status"], "VERIFIED_100_PERCENT")
        self.assertEqual(len(vv["checks"]), 5)
        for chk in vv["checks"]:
            self.assertTrue(chk["passed"], f"V&V check failed: {chk['check_id']}")

    def test_19_backward_chaining_goal_seeker_counterfactual_plans(self) -> None:
        """Kiem thu BackwardGoalSeeker: Tim lo trinh nang hang cho APP003, APP004 va APP005."""
        gs_03 = self.goal_seeker.seek_goal(self.applicants["APP003"], "APPROVED_100")
        self.assertFalse(gs_03["already_achieved"])
        self.assertGreaterEqual(len(gs_03["verified_plans"]), 1)
        for plan in gs_03["verified_plans"]:
            self.assertEqual(plan["achieved_decision"], "APPROVED")

        gs_04 = self.goal_seeker.seek_goal(self.applicants["APP004"], "TIER_A")
        self.assertFalse(gs_04["already_achieved"])
        self.assertGreaterEqual(len(gs_04["verified_plans"]), 1)
        self.assertEqual(gs_04["verified_plans"][0]["achieved_tier"], "TIER_A")

    def test_20_multi_paradigm_comparison_drools_vs_clips_vs_prolog_all_15_applicants(self) -> None:
        """Kiem thu Doi sanh 3 Cong cu (Drools .drl vs CLIPS .clp vs Prolog .pl) khop 100% tren ca 15 ho so."""
        for app_id, payload in self.applicants.items():
            cmp_res = self.comparator.compare_on_applicant(payload)
            self.assertTrue(
                cmp_res["consensus_verified"],
                f"Khong khop ket qua giua Drools, CLIPS va Prolog tren ho so {app_id}",
            )

    def test_21_java_kie_maven_reference_structure_integrity(self) -> None:
        """Kiem thu cau hinh tham chieu Apache KIE Drools Java Maven trong java_kie_reference/."""
        pom_path = os.path.join(BASE_DIR, "java_kie_reference", "pom.xml")
        kmodule_path = os.path.join(
            BASE_DIR, "java_kie_reference", "src", "main", "resources", "META-INF", "kmodule.xml"
        )
        java_app_path = os.path.join(
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
        self.assertTrue(os.path.exists(pom_path))
        self.assertTrue(os.path.exists(kmodule_path))
        self.assertTrue(os.path.exists(java_app_path))

    def test_22_extended_rest_api_endpoints_vv_goalseek_paradigms(self) -> None:
        """Kiem thu cac REST API nang cao: /api/verify-rules, /api/compare-engines, /api/goal-seek."""
        import json
        import threading
        import urllib.request
        from http.server import ThreadingHTTPServer
        from app import DroolsDSSRequestHandler

        server = ThreadingHTTPServer(("127.0.0.1", 0), DroolsDSSRequestHandler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            base_url = f"http://127.0.0.1:{port}"

            with urllib.request.urlopen(f"{base_url}/api/verify-rules") as resp:
                self.assertEqual(resp.status, 200)
                vv_data = json.loads(resp.read().decode("utf-8"))
                self.assertTrue(vv_data["verification"]["all_passed"])

            req_cmp = urllib.request.Request(
                f"{base_url}/api/compare-engines",
                data=json.dumps({"applicant": self.applicants["APP004"]}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req_cmp) as resp:
                self.assertEqual(resp.status, 200)
                cmp_data = json.loads(resp.read().decode("utf-8"))
                self.assertTrue(cmp_data["comparison"]["consensus_verified"])

            req_gs = urllib.request.Request(
                f"{base_url}/api/goal-seek",
                data=json.dumps({"applicant": self.applicants["APP003"], "target_goal": "APPROVED_100"}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req_gs) as resp:
                self.assertEqual(resp.status, 200)
                gs_data = json.loads(resp.read().decode("utf-8"))
                self.assertGreaterEqual(len(gs_data["goal_seek"]["verified_plans"]), 1)
        finally:
            server.shutdown()
            server.server_close()

    def test_23_academic_report_and_slides_docx_pptx_deliverables(self) -> None:
        """Kiem thu cac file Bao cao Word (.docx), Slide PowerPoint (.pptx) va Markdown (.md) ton tai va day du."""
        docx_path = os.path.join(BASE_DIR, "docs", "BAO_CAO_DO_AN_DE_08_DROOLS_NHOM_1.docx")
        pptx_path = os.path.join(BASE_DIR, "docs", "SLIDE_THUYET_TRINH_DE_08_DROOLS_NHOM_1.pptx")
        md_report_path = os.path.join(BASE_DIR, "docs", "BAO_CAO_DO_AN_DE_08_DROOLS_NHOM_1.md")
        md_slide_path = os.path.join(BASE_DIR, "docs", "SLIDE_VA_KICH_BAN_BAO_VE_NHOM_1.md")

        for path in [docx_path, pptx_path, md_report_path, md_slide_path]:
            self.assertTrue(os.path.exists(path), f"Missing academic deliverable: {path}")
            self.assertGreater(os.path.getsize(path), 10000, f"Deliverable file too small: {path}")


if __name__ == "__main__":
    unittest.main(verbosity=2)

