;; ============================================================================
;; rules/credit_approval.clp
;; TAP LUAT THAM DINH TIN DUNG & DINH GIA KHOAN VAY BANG NGON NGU CLIPS (NASA)
;; Do an Cuoi ky Mon He thong Ho tro Ra quyet dinh (DSS) - Nhom 1 - De 08
;; Dung de doi chung truc tiep voi Drools (.drl) va Prolog (.pl)
;; ============================================================================

(deftemplate applicant
    (slot applicant_id (type STRING))
    (slot full_name (type STRING))
    (slot age (type INTEGER))
    (slot monthly_income (type FLOAT))
    (slot employment_years (type FLOAT))
    (slot credit_score (type INTEGER))
    (slot dti_ratio (type FLOAT))
    (slot loan_amount (type FLOAT))
    (slot loan_term_months (type INTEGER))
    (slot collateral_value (type FLOAT))
    (slot cic_bad_debt (type SYMBOL) (allowed-values TRUE FALSE))
    (slot is_vip (type SYMBOL) (allowed-values TRUE FALSE))
    (slot eligible (type SYMBOL) (default FALSE))
    (slot secured_loan (type SYMBOL) (default FALSE))
    (slot composite_score (type INTEGER) (default 0))
    (slot risk_tier (type STRING) (default "UNRATED"))
    (slot decision (type STRING) (default "PENDING"))
    (slot approved_amount (type FLOAT) (default 0.0))
    (slot interest_rate (type FLOAT) (default 0.0))
    (slot rejection_code (type STRING) (default "NONE"))
)

(deftemplate eligibility-passed
    (slot applicant_id (type STRING))
    (slot status (type STRING) (default "PASSED"))
)

;; --- TANG 1: HARD KNOCK-OUT & ELIGIBILITY (Salience 90..100) ---

(defrule R01-knockout-age
    (declare (salience 100))
    ?app <- (applicant (decision "PENDING") (age ?a&:(or (< ?a 18) (> ?a 65))))
    =>
    (modify ?app (eligible FALSE) (composite_score 10) (risk_tier "TIER_D")
                 (decision "REJECTED") (approved_amount 0.0) (interest_rate 0.0)
                 (rejection_code "KO_AGE_LIMIT"))
)

(defrule R02-knockout-cic
    (declare (salience 98))
    ?app <- (applicant (decision "PENDING") (age ?a&:(and (>= ?a 18) (<= ?a 65))) (cic_bad_debt TRUE))
    =>
    (modify ?app (eligible FALSE) (composite_score 15) (risk_tier "TIER_D")
                 (decision "REJECTED") (approved_amount 0.0) (interest_rate 0.0)
                 (rejection_code "KO_CIC_BAD_DEBT"))
)

(defrule R03-knockout-dti
    (declare (salience 95))
    ?app <- (applicant (decision "PENDING") (age ?a&:(and (>= ?a 18) (<= ?a 65)))
                       (cic_bad_debt FALSE) (dti_ratio ?d&:(> ?d 65.0)))
    =>
    (modify ?app (eligible FALSE) (composite_score 20) (risk_tier "TIER_D")
                 (decision "REJECTED") (approved_amount 0.0) (interest_rate 0.0)
                 (rejection_code "KO_EXCESSIVE_DTI"))
)

(defrule R04-eligibility-passed-tms
    (declare (salience 90))
    (logical (applicant (applicant_id ?id) (age ?a&:(and (>= ?a 18) (<= ?a 65)))
                        (cic_bad_debt FALSE) (dti_ratio ?d&:(<= ?d 65.0))))
    ?app <- (applicant (applicant_id ?id) (decision "PENDING") (eligible FALSE))
    =>
    (modify ?app (eligible TRUE) (composite_score 40))
    (assert (eligibility-passed (applicant_id ?id) (status "PASSED")))
)

;; --- TANG 2: RISK SCORING & TIERING (Salience 60..80) ---

(defrule R05-income-tenure-bonus
    (declare (salience 80))
    (eligibility-passed (applicant_id ?id) (status "PASSED"))
    ?app <- (applicant (applicant_id ?id) (eligible TRUE)
                       (monthly_income ?inc&:(>= ?inc 30.0))
                       (employment_years ?emp&:(>= ?emp 2.0))
                       (composite_score ?s))
    =>
    (modify ?app (composite_score (+ ?s 20)))
)

(defrule R06-credit-dti-bonus
    (declare (salience 78))
    (eligibility-passed (applicant_id ?id) (status "PASSED"))
    ?app <- (applicant (applicant_id ?id) (eligible TRUE)
                       (credit_score ?cs&:(>= ?cs 750))
                       (dti_ratio ?dti&:(<= ?dti 35.0))
                       (composite_score ?s))
    =>
    (modify ?app (composite_score (+ ?s 25)))
)

(defrule R07-collateral-bonus
    (declare (salience 75))
    (eligibility-passed (applicant_id ?id) (status "PASSED"))
    ?app <- (applicant (applicant_id ?id) (eligible TRUE)
                       (loan_amount ?loan&:(> ?loan 0))
                       (collateral_value ?col&:(>= ?col (* 1.2 ?loan)))
                       (composite_score ?s))
    =>
    (modify ?app (composite_score (+ ?s 15)) (secured_loan TRUE))
)

(defrule R08-risk-warning-penalty
    (declare (salience 72))
    (eligibility-passed (applicant_id ?id) (status "PASSED"))
    ?app <- (applicant (applicant_id ?id) (eligible TRUE)
                       (monthly_income ?inc) (employment_years ?emp) (dti_ratio ?dti)
                       (composite_score ?s))
    (test (or (< ?inc 10.0) (< ?emp 1.0) (and (> ?dti 45.0) (<= ?dti 65.0))))
    =>
    (modify ?app (composite_score (- ?s 15)))
)

(defrule R09-R12-assign-risk-tier
    (declare (salience 65))
    (eligibility-passed (applicant_id ?id) (status "PASSED"))
    ?app <- (applicant (applicant_id ?id) (eligible TRUE) (risk_tier "UNRATED") (composite_score ?s))
    =>
    (if (>= ?s 80) then (modify ?app (risk_tier "TIER_A"))
     else (if (>= ?s 60) then (modify ?app (risk_tier "TIER_B"))
     else (if (>= ?s 40) then (modify ?app (risk_tier "TIER_C"))
     else (modify ?app (risk_tier "TIER_D")))))
)

;; --- TANG 3: PRICING & FINAL DECISION (Salience 30..50) ---

(defrule R13-approve-tier-a
    (declare (salience 50))
    (eligibility-passed (applicant_id ?id) (status "PASSED"))
    ?app <- (applicant (applicant_id ?id) (risk_tier "TIER_A") (decision "PENDING")
                       (loan_amount ?loan) (is_vip ?vip))
    =>
    (bind ?rate (if (eq ?vip TRUE) then 6.8 else 7.5))
    (modify ?app (decision "APPROVED") (approved_amount ?loan) (interest_rate ?rate))
)

(defrule R14-approve-tier-b-secured
    (declare (salience 46))
    (eligibility-passed (applicant_id ?id) (status "PASSED"))
    ?app <- (applicant (applicant_id ?id) (risk_tier "TIER_B") (secured_loan TRUE)
                       (decision "PENDING") (loan_amount ?loan))
    =>
    (modify ?app (decision "APPROVED") (approved_amount ?loan) (interest_rate 9.2))
)

(defrule R15-conditional-tier-b-unsecured
    (declare (salience 42))
    (eligibility-passed (applicant_id ?id) (status "PASSED"))
    ?app <- (applicant (applicant_id ?id) (risk_tier "TIER_B") (secured_loan FALSE)
                       (decision "PENDING") (loan_amount ?loan))
    =>
    (modify ?app (decision "CONDITIONAL_APPROVAL") (approved_amount (* 0.8 ?loan)) (interest_rate 10.8))
)

(defrule R16-manual-review-tier-c
    (declare (salience 38))
    (eligibility-passed (applicant_id ?id) (status "PASSED"))
    ?app <- (applicant (applicant_id ?id) (risk_tier "TIER_C")
                       (decision "PENDING") (loan_amount ?loan))
    =>
    (modify ?app (decision "MANUAL_REVIEW") (approved_amount (* 0.55 ?loan)) (interest_rate 12.5))
)

(defrule R17-reject-tier-d
    (declare (salience 34))
    (eligibility-passed (applicant_id ?id) (status "PASSED"))
    ?app <- (applicant (applicant_id ?id) (risk_tier "TIER_D") (decision "PENDING"))
    =>
    (modify ?app (decision "REJECTED") (approved_amount 0.0) (interest_rate 0.0)
                 (rejection_code "LOW_COMPOSITE_SCORE"))
)
