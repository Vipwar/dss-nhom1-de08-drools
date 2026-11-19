% ============================================================================
% rules/credit_approval.pl
% CO SO TRI THUC PROLOG (SWI-PROLOG BACKWARD CHAINING & SLD RESOLUTION)
% Do an Cuoi ky Mon He thong Ho tro Ra quyet dinh (DSS) - Nhom 1 - De 08
% Dung de doi chung Suy dien lui (Prolog) voi Suy dien tien (Drools & CLIPS)
% ============================================================================

% --- MUC TIEU CHINH (TOP-LEVEL GOAL QUERY) ---
% ?- evaluate_credit(ApplicantId, Decision, RiskTier, CompositeScore, ApprovedAmount, InterestRate, RejectionCode).

% 1. Kiem tra Loai tru cung Tang 1 (Hard Knock-out Clauses voi toan tu Cut '!')
evaluate_credit(Id, 'REJECTED', 'TIER_D', 10, 0.0, 0.0, 'KO_AGE_LIMIT') :-
    applicant(Id, Age, _Income, _Emp, _CS, _DTI, _Loan, _Col, _CIC, _VIP),
    (Age < 18 ; Age > 65), !.

evaluate_credit(Id, 'REJECTED', 'TIER_D', 15, 0.0, 0.0, 'KO_CIC_BAD_DEBT') :-
    applicant(Id, Age, _Income, _Emp, _CS, _DTI, _Loan, _Col, CIC, _VIP),
    Age >= 18, Age =< 65,
    CIC == true, !.

evaluate_credit(Id, 'REJECTED', 'TIER_D', 20, 0.0, 0.0, 'KO_EXCESSIVE_DTI') :-
    applicant(Id, Age, _Income, _Emp, _CS, DTI, _Loan, _Col, false, _VIP),
    Age >= 18, Age =< 65,
    DTI > 65.0, !.

% 2. Chung minh ho so hop le (Goal: eligibility_passed/1) va suy dien diem + quyet dinh
evaluate_credit(Id, Decision, RiskTier, CompositeScore, ApprovedAmount, InterestRate, RejCode) :-
    eligibility_passed(Id),
    compute_composite_score(Id, CompositeScore, SecuredLoan),
    classify_risk_tier(CompositeScore, RiskTier),
    pricing_decision(Id, RiskTier, SecuredLoan, Decision, ApprovedAmount, InterestRate, RejCode), !.

% --- TANG 1 SUB-GOAL: ELIGIBILITY PASSED ---
eligibility_passed(Id) :-
    applicant(Id, Age, _Income, _Emp, _CS, DTI, _Loan, _Col, false, _VIP),
    Age >= 18, Age =< 65,
    DTI =< 65.0.

% --- TANG 2 SUB-GOALS: RISK SCORING & TIER CLASSIFICATION ---
compute_composite_score(Id, TotalScore, SecuredLoan) :-
    applicant(Id, _Age, Income, Emp, CS, DTI, Loan, Col, _CIC, _VIP),
    BaseScore = 40,
    ( (Income >= 30.0, Emp >= 2.0) -> BonusR05 = 20 ; BonusR05 = 0 ),
    ( (CS >= 750, DTI =< 35.0)     -> BonusR06 = 25 ; BonusR06 = 0 ),
    ( (Loan > 0, Col >= 1.2 * Loan) -> (BonusR07 = 15, SecuredLoan = true) ; (BonusR07 = 0, SecuredLoan = false) ),
    ( (Income < 10.0 ; Emp < 1.0 ; (DTI > 45.0, DTI =< 65.0)) -> PenaltyR08 = -15 ; PenaltyR08 = 0 ),
    TotalScore is BaseScore + BonusR05 + BonusR06 + BonusR07 + PenaltyR08.

classify_risk_tier(Score, 'TIER_A') :- Score >= 80, !.
classify_risk_tier(Score, 'TIER_B') :- Score >= 60, !.
classify_risk_tier(Score, 'TIER_C') :- Score >= 40, !.
classify_risk_tier(Score, 'TIER_D') :- Score < 40, !.

% --- TANG 3 SUB-GOALS: PRICING & APPROVAL DECISION ---
pricing_decision(Id, 'TIER_A', _Secured, 'APPROVED', Loan, Rate, 'NONE') :-
    applicant(Id, _Age, _Income, _Emp, _CS, _DTI, Loan, _Col, _CIC, VIP),
    ( VIP == true -> Rate = 6.8 ; Rate = 7.5 ), !.

pricing_decision(Id, 'TIER_B', true, 'APPROVED', Loan, 9.2, 'NONE') :-
    applicant(Id, _Age, _Income, _Emp, _CS, _DTI, Loan, _Col, _CIC, _VIP), !.

pricing_decision(Id, 'TIER_B', false, 'CONDITIONAL_APPROVAL', ApprovedAmt, 10.8, 'NONE') :-
    applicant(Id, _Age, _Income, _Emp, _CS, _DTI, Loan, _Col, _CIC, _VIP),
    ApprovedAmt is round(Loan * 80.0) / 100.0, !.

pricing_decision(Id, 'TIER_C', _Secured, 'MANUAL_REVIEW', ApprovedAmt, 12.5, 'NONE') :-
    applicant(Id, _Age, _Income, _Emp, _CS, _DTI, Loan, _Col, _CIC, _VIP),
    ApprovedAmt is round(Loan * 55.0) / 100.0, !.

pricing_decision(_Id, 'TIER_D', _Secured, 'REJECTED', 0.0, 0.0, 'LOW_COMPOSITE_SCORE') :- !.
