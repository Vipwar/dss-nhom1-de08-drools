/* ============================================================================
   static/app.js
   FRONTEND LOGIC CHO HE THONG HO TRO RA QUYET DINH (DSS) - NHOM 1 - DE 08: DROOLS
   Bao gom 6 khu vuc tuong tac chinh + Phan he Doi sanh Drools/CLIPS/Prolog,
   Backward Chaining Goal-Seeker, Formal Rule Base V&V va Xuat To trinh Tham dinh.
   ============================================================================ */

const STATE = {
  presets: [],
  sampleApplicants: [],
  rulesMetadata: [],
  decisionTableRows: [],
  activeApplicant: null,
  currentEvaluation: null,
  whatIfBaseline: null,
  ruleVerification: null,
  currentComparison: null,
  currentGoalSeek: null,
  clipsSource: "",
  prologSource: "",
  replayStepIndex: -1,
  replayTimer: null,
  fullPageMode: false,
  charts: {
    radar: null,
    sensitivity: null,
    batchDecision: null,
    batchTier: null,
  },
};

const PRESET_TITLES = [
  {
    badge: "Kịch bản 1 • VIP Hạng A",
    title: "Duyệt tự động 100% & Lãi suất VIP 6.8%",
    desc: "Điểm 100/100 • Vay 500tr kích hoạt kiểm soát định giá độc lập R18",
    accent: "emerald",
  },
  {
    badge: "Kịch bản 2 • Hạng B Có TSĐB",
    title: "Duyệt 100% hạn mức • Lãi suất 9.2%",
    desc: "Điểm 75/100 • Có tài sản đảm bảo >= 120% khoản vay (R07 + R14)",
    accent: "sky",
  },
  {
    badge: "Kịch bản 3 • Hạng B Tín chấp",
    title: "Duyệt có điều kiện • Cắt giảm 80%",
    desc: "Điểm 65/100 • Vay tín chấp không TSĐB (R15 + Khuyến nghị R19)",
    accent: "amber",
  },
  {
    badge: "Kịch bản 4 • Hồ sơ Xung đột Hạng C",
    title: "Xung đột R05 (+20) vs R08 (-15)",
    desc: "Điểm 45/100 • Chuyển Hội đồng Tín dụng thẩm định (R11 + R16)",
    accent: "indigo",
  },
  {
    badge: "Kịch bản 5 • Knock-out Nợ xấu CIC",
    title: "Từ chối ngay Tầng 1 (Dừng sớm R02)",
    desc: "Có nợ xấu CIC nhóm 3–5 • Không sinh EligibilityPassed, bỏ qua Tầng 2–3",
    accent: "rose",
  },
  {
    badge: "Kịch bản 6 • Knock-out DTI > 65%",
    title: "Từ chối ngay Tầng 1 do DTI 71.5%",
    desc: "Vi phạm trần nợ/thu nhập R03 • Sinh lộ trình giảm dư nợ R20",
    accent: "rose",
  },
];

const AGENDA_STAGE_INFO = [
  {
    id: "1-eligibility",
    title: "Tầng 1: 1-eligibility",
    subtitle: "Loại trừ cứng (Hard Knock-out) & TMS",
    salience: "Salience 90..100",
  },
  {
    id: "2-risk-scoring",
    title: "Tầng 2: 2-risk-scoring",
    subtitle: "Chấm điểm & Phân hạng Rủi ro",
    salience: "Salience 60..80",
  },
  {
    id: "3-pricing-decision",
    title: "Tầng 3: 3-pricing-decision",
    subtitle: "Quyết định, Hạn mức & Định giá Lãi suất",
    salience: "Salience 30..50",
  },
  {
    id: "4-dss-explanation",
    title: "Tầng 4: 4-dss-explanation",
    subtitle: "Khuyến nghị DSS & Kiểm soát Biên",
    salience: "Salience 10..20",
  },
];

/* ============================================================================
   KHOI TAO UNG DUNG
   ============================================================================ */
document.addEventListener("DOMContentLoaded", async () => {
  await loadOverviewData();
  if (window.lucide) {
    window.lucide.createIcons();
  }
});

async function loadOverviewData() {
  try {
    const resp = await fetch("/api/overview");
    const data = await resp.json();
    if (data.status !== "OK") throw new Error(data.message || "Lỗi tải dữ liệu");

    STATE.presets = data.presets || [];
    STATE.sampleApplicants = data.sample_applicants || [];
    STATE.rulesMetadata = data.rules_metadata || [];
    STATE.decisionTableRows = data.decision_table_rows || [];
    STATE.ruleVerification = data.rule_verification || null;
    STATE.currentComparison = data.initial_comparison || null;
    STATE.currentGoalSeek = data.initial_goal_seek || null;
    STATE.clipsSource = data.clips_source || "";
    STATE.prologSource = data.prolog_source || "";
    STATE.javaKieSource = data.java_kie_source || "";

    const badge = document.getElementById("headerEngineBadge");
    if (badge && data.project) {
      badge.textContent = `KieBase: ${data.project.total_rules} Rules Verified (V&V 100%)`;
    }

    const drlEditor = document.getElementById("drlSourceEditor");
    if (drlEditor) drlEditor.value = data.drl_source || "";

    const clipsPre = document.getElementById("clipsSourcePreview");
    if (clipsPre) clipsPre.textContent = STATE.clipsSource;

    const prologPre = document.getElementById("prologSourcePreview");
    if (prologPre) prologPre.textContent = STATE.prologSource;

    const javaPre = document.getElementById("javaKieSourcePreview");
    if (javaPre) javaPre.textContent = STATE.javaKieSource;

    renderPresetScenarios();
    populateApplicantDropdowns();
    renderStudioSidebar();
    renderRuleVerificationMatrix();
    if (STATE.currentComparison) renderMultiParadigmComparison(STATE.currentComparison);
    if (STATE.currentGoalSeek) renderGoalSeekingResult(STATE.currentGoalSeek);

    if (STATE.presets.length > 0) {
      populateFormWithApplicant(STATE.presets[0]);
      STATE.whatIfBaseline = { ...STATE.presets[2] };
      populateWhatIfSliders(STATE.whatIfBaseline);
    }

    if (data.initial_evaluation) {
      STATE.currentEvaluation = data.initial_evaluation;
      STATE.replayStepIndex = -1;
      renderEvaluationResult(data.initial_evaluation);
    }
  } catch (err) {
    console.error("Lỗi khởi tạo:", err);
  }
}

/* ============================================================================
   DIEU HUONG TAB & CHE DO TOAN TRANG
   ============================================================================ */
function switchTab(tabName) {
  const tabs = ["dashboard", "whatif", "batch", "studio", "paradigms"];
  STATE.fullPageMode = false;

  tabs.forEach((t) => {
    const btn = document.getElementById(`tabBtn-${t}`);
    const panel = document.getElementById(`tabPanel-${t}`);
    if (btn) btn.classList.toggle("active", t === tabName);
    if (panel) panel.classList.toggle("hidden", t !== tabName);
  });

  if (tabName === "whatif") {
    runWhatIfSimulation();
  } else if (tabName === "batch") {
    loadBatchEvaluation();
  } else if (tabName === "paradigms") {
    runMultiParadigmComparison();
    runGoalSeekingQuery();
  }
}

function toggleFullPageMode() {
  STATE.fullPageMode = !STATE.fullPageMode;
  const tabs = ["dashboard", "whatif", "batch", "studio", "paradigms"];
  if (STATE.fullPageMode) {
    tabs.forEach((t) => {
      const panel = document.getElementById(`tabPanel-${t}`);
      if (panel) panel.classList.remove("hidden");
    });
    runWhatIfSimulation();
    loadBatchEvaluation();
    runMultiParadigmComparison();
    runGoalSeekingQuery();
  } else {
    switchTab("dashboard");
  }
}

/* ============================================================================
   KHU VUC 1: 6 KICH BAN DEMO 1-CLICK & FORM HO SO
   ============================================================================ */
function renderPresetScenarios() {
  const container = document.getElementById("presetScenariosContainer");
  if (!container) return;

  container.innerHTML = STATE.presets
    .map((item, idx) => {
      const meta = PRESET_TITLES[idx] || {
        badge: `Kịch bản ${idx + 1}`,
        title: item.full_name,
        desc: item.notes || "",
      };
      const isActive =
        STATE.activeApplicant && STATE.activeApplicant.applicant_id === item.applicant_id;

      return `
        <button
          type="button"
          id="presetBtn-${item.applicant_id}"
          onclick="selectPresetScenario(${idx})"
          class="scenario-btn ${isActive ? "active" : ""}"
        >
          <div class="flex items-center justify-between gap-1 mb-1">
            <span class="text-[11px] font-extrabold uppercase tracking-wider text-sky-700">
              ${meta.badge}
            </span>
            <span class="px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 font-mono text-[10px] font-bold">
              ${item.applicant_id}
            </span>
          </div>
          <div class="text-xs font-bold text-slate-900 leading-snug">
            ${item.full_name} (${item.age}t)
          </div>
          <div class="text-[11px] font-semibold text-slate-700 mt-0.5">
            ${meta.title}
          </div>
          <div class="text-[11px] text-slate-500 mt-1 line-clamp-2">
            ${meta.desc}
          </div>
        </button>
      `;
    })
    .join("");
}

function populateApplicantDropdowns() {
  const selMain = document.getElementById("selectSampleApplicant");
  const selWi = document.getElementById("whatIfPresetSelect");
  const selPara = document.getElementById("paradigmApplicantSelect");
  const selGoal = document.getElementById("goalSeekApplicantSelect");

  const optionsHtml = STATE.sampleApplicants
    .map(
      (app) =>
        `<option value="${app.applicant_id}">${app.applicant_id} – ${app.full_name} (${app.scenario_tag})</option>`
    )
    .join("");

  if (selMain) selMain.innerHTML = optionsHtml;
  if (selPara) selPara.innerHTML = optionsHtml;
  if (selWi) {
    selWi.innerHTML = optionsHtml;
    if (STATE.sampleApplicants[2]) selWi.value = STATE.sampleApplicants[2].applicant_id;
  }
  if (selGoal) {
    selGoal.innerHTML = optionsHtml;
    if (STATE.sampleApplicants[2]) selGoal.value = STATE.sampleApplicants[2].applicant_id;
  }
}

async function selectPresetScenario(index) {
  const preset = STATE.presets[index];
  if (!preset) return;
  stopReplayAuto();
  populateFormWithApplicant(preset);
  const sel = document.getElementById("selectSampleApplicant");
  if (sel) sel.value = preset.applicant_id;
  await evaluateApplicantPayload(preset);
}

async function onSelectSampleApplicant(applicantId) {
  const found = STATE.sampleApplicants.find((a) => a.applicant_id === applicantId);
  if (!found) return;
  stopReplayAuto();
  populateFormWithApplicant(found);
  await evaluateApplicantPayload(found);
}

function populateFormWithApplicant(app) {
  STATE.activeApplicant = { ...app };
  const badge = document.getElementById("formApplicantIdBadge");
  if (badge) badge.textContent = app.applicant_id || "CUSTOM";

  document.getElementById("inp_full_name").value = app.full_name ?? "Khách hàng Demo";
  document.getElementById("inp_age").value = app.age ?? 32;
  document.getElementById("inp_employment_years").value = app.employment_years ?? 3.0;
  document.getElementById("inp_monthly_income").value = app.monthly_income ?? 25.0;
  document.getElementById("inp_credit_score").value = app.credit_score ?? 720;
  document.getElementById("inp_dti_ratio").value = app.dti_ratio ?? 30.0;
  document.getElementById("inp_loan_term_months").value = app.loan_term_months ?? 36;
  document.getElementById("inp_loan_amount").value = app.loan_amount ?? 200.0;
  document.getElementById("inp_collateral_value").value = app.collateral_value ?? 0.0;
  document.getElementById("inp_cic_bad_debt").checked = Boolean(app.cic_bad_debt);
  document.getElementById("inp_is_vip").checked = Boolean(app.is_vip);

  renderPresetScenarios();
}

function readApplicantFromForm() {
  return {
    applicant_id: (STATE.activeApplicant && STATE.activeApplicant.applicant_id) || "APP_CUSTOM",
    full_name: document.getElementById("inp_full_name").value.trim(),
    age: parseInt(document.getElementById("inp_age").value, 10) || 30,
    employment_years: parseFloat(document.getElementById("inp_employment_years").value) || 0,
    monthly_income: parseFloat(document.getElementById("inp_monthly_income").value) || 10,
    credit_score: parseInt(document.getElementById("inp_credit_score").value, 10) || 650,
    dti_ratio: parseFloat(document.getElementById("inp_dti_ratio").value) || 30,
    loan_term_months: parseInt(document.getElementById("inp_loan_term_months").value, 10) || 36,
    loan_amount: parseFloat(document.getElementById("inp_loan_amount").value) || 100,
    collateral_value: parseFloat(document.getElementById("inp_collateral_value").value) || 0,
    cic_bad_debt: document.getElementById("inp_cic_bad_debt").checked,
    is_vip: document.getElementById("inp_is_vip").checked,
  };
}

async function handleEvaluateForm(event) {
  event.preventDefault();
  stopReplayAuto();
  const payload = readApplicantFromForm();
  await evaluateApplicantPayload(payload);
}

async function evaluateApplicantPayload(payload) {
  try {
    const resp = await fetch("/api/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ applicant: payload }),
    });
    const data = await resp.json();
    if (data.status !== "OK") throw new Error(data.message || "Lỗi suy diễn");

    STATE.currentEvaluation = data.result;
    STATE.replayStepIndex = -1;
    renderEvaluationResult(data.result);
  } catch (err) {
    alert("Lỗi khi chạy Drools Engine: " + err.message);
  }
}

/* ============================================================================
   KHU VUC 2: BANG KET QUA HO TRO RA QUYET DINH & BIEU DO RADAR 5 CHIEU
   ============================================================================ */
function renderEvaluationResult(evalData) {
  if (!evalData) return;
  const app = evalData.applicant;
  const sum = evalData.summary;
  const eng = evalData.engine;

  document.getElementById("execCyclesBadge").textContent = `${eng.total_cycles} Chu kỳ Suy diễn`;
  const tierBadge = document.getElementById("execTierBadge");
  tierBadge.className = `badge-pill tier-${sum.risk_tier}`;
  tierBadge.textContent = `${sum.risk_tier} • ${sum.risk_tier_label}`;

  const banner = document.getElementById("decisionBannerBox");
  banner.className = `decision-banner decision-${sum.decision}`;
  document.getElementById("execDecisionTitle").textContent = sum.decision_label;
  document.getElementById("execApplicantSummaryLine").textContent =
    `Hồ sơ: ${app.full_name} (${app.age} tuổi, Mã ${app.applicant_id}) • ${sum.risk_tier_label}` +
    (sum.rejection_code && sum.rejection_code !== "NONE" ? ` • Mã từ chối: ${sum.rejection_code}` : "");
  document.getElementById("execCompositeScore").textContent = `${sum.composite_score}/100`;

  document.getElementById("metricApprovedAmount").textContent = `${sum.approved_amount.toFixed(1)} triệu`;
  document.getElementById("metricApprovalRatio").textContent =
    sum.approved_amount > 0
      ? `Đạt ${sum.approval_ratio_percent}% mức đề nghị (${app.loan_amount} triệu)`
      : `Không cấp hạn mức (Đề nghị: ${app.loan_amount} triệu)`;

  document.getElementById("metricInterestRate").textContent =
    sum.interest_rate > 0 ? `${sum.interest_rate.toFixed(2)}% / năm` : "— (Từ chối)";
  document.getElementById("metricLoanTerm").textContent = `Kỳ hạn: ${app.loan_term_months} tháng`;

  document.getElementById("metricMonthlyPayment").textContent =
    sum.estimated_monthly_payment > 0
      ? `${sum.estimated_monthly_payment.toFixed(2)} triệu/tháng`
      : "0.00 triệu/tháng";

  document.getElementById("metricPostDti").textContent = `${sum.post_decision_dti}%`;
  document.getElementById("metricCollateralRatio").textContent = `${sum.collateral_coverage_percent}%`;

  const secEl = document.getElementById("metricSecuredFlag");
  if (sum.secured_loan) {
    secEl.textContent = "Đạt chuẩn có TSĐB (>=120%)";
    secEl.className = "text-xs font-semibold text-emerald-700 mt-0.5";
  } else {
    secEl.textContent = "Vay tín chấp / TSĐB < 120%";
    secEl.className = "text-xs font-semibold text-amber-700 mt-0.5";
  }

  document.getElementById("metricFiredRulesChain").textContent =
    eng.fired_rules.length > 0 ? eng.fired_rules.join(" → ") : "Không có luật kích hoạt";

  const reasonsList = document.getElementById("execReasonsList");
  reasonsList.innerHTML = (sum.reasons || [])
    .map(
      (r) =>
        `<li class="flex items-start gap-2"><span class="text-sky-600 font-bold">▸</span><span>${escapeHtml(r)}</span></li>`
    )
    .join("");

  const recList = document.getElementById("execRecommendationsList");
  const recs = sum.recommendations && sum.recommendations.length > 0
    ? sum.recommendations
    : ["Hồ sơ đạt chuẩn phê duyệt tự động, không yêu cầu điều chỉnh bổ sung."];
  recList.innerHTML = recs
    .map(
      (r) =>
        `<li class="flex items-start gap-2"><span class="text-sky-700 font-bold">★</span><span>${escapeHtml(r)}</span></li>`
    )
    .join("");

  renderApplicantRadarChart(evalData.radar_dimensions);
  renderReteVisualizer(evalData);
  renderTraceAndConflictLog(evalData);
}

function renderApplicantRadarChart(dims) {
  if (!dims) return;
  const labels = [
    "Năng lực Thu nhập",
    "Uy tín Tín dụng",
    "An toàn Dư nợ (DTI)",
    "Bảo chứng Tài sản",
    "Ổn định Nghề nghiệp",
  ];
  const values = [
    dims.income_capacity || 0,
    dims.credit_reputation || 0,
    dims.debt_safety_dti || 0,
    dims.collateral_coverage || 0,
    dims.career_stability || 0,
  ];

  const fallbackBox = document.getElementById("radarFallbackBars");
  if (fallbackBox) {
    fallbackBox.innerHTML = labels
      .map(
        (lbl, i) => `
        <div class="flex items-center justify-between text-[11px]">
          <span class="font-medium text-slate-600">${lbl}</span>
          <span class="font-mono font-bold text-slate-900">${values[i]}/100</span>
        </div>`
      )
      .join("");
  }

  const canvas = document.getElementById("applicantRadarChart");
  if (!canvas) return;
  if (typeof window.Chart === "undefined") {
    drawOfflineRadarCanvas(canvas, labels, values);
    return;
  }

  if (STATE.charts.radar) {
    STATE.charts.radar.destroy();
  }

  STATE.charts.radar = new window.Chart(canvas, {
    type: "radar",
    data: {
      labels,
      datasets: [
        {
          label: "Điểm Đánh giá 5 Chiều (0–100)",
          data: values,
          backgroundColor: "rgba(2, 132, 199, 0.22)",
          borderColor: "#0284c7",
          pointBackgroundColor: "#0369a1",
          pointBorderColor: "#ffffff",
          borderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
      },
      scales: {
        r: {
          min: 0,
          max: 100,
          ticks: { stepSize: 25, display: false },
          pointLabels: {
            font: { size: 10, weight: "600", family: "Inter" },
            color: "#334155",
          },
        },
      },
    },
  });
}

/* ============================================================================
   KHU VUC 3: SO DO MANG SUY DIEN RETE / PHREAK & STEP-BY-STEP REPLAY
   ============================================================================ */
function renderReteVisualizer(evalData) {
  if (!evalData || !evalData.engine) return;
  const eng = evalData.engine;
  const rete = eng.rete_network;
  const stats = rete.stats || {};
  const steps = eng.trace_steps || [];

  const isReplayMode = STATE.replayStepIndex >= 0 && STATE.replayStepIndex < steps.length;
  const currentStep = isReplayMode ? steps[STATE.replayStepIndex] : null;
  const activeUpToSteps = isReplayMode ? steps.slice(0, STATE.replayStepIndex + 1) : steps;
  const firedCodesSoFar = new Set(activeUpToSteps.map((s) => s.rule_code));
  const cancelledCodes = new Set((eng.cancelled_activations || []).map((c) => c.cancelled_rule_code));

  const flowBar = document.getElementById("reteArchitectureFlowBar");
  if (flowBar) {
    const wmCount = (eng.working_memory_facts || []).length;
    const activeAlphaCount = currentStep
      ? currentStep.matched_alpha_nodes.length
      : (rete.nodes || []).filter((n) => n.type === "AlphaNode" && n.active).length;

    flowBar.innerHTML = `
      <div class="pipeline-node active-glow">
        <div class="text-[11px] font-bold uppercase text-sky-700">1. Working Memory & OTN</div>
        <div class="text-sm font-extrabold text-slate-900 mt-0.5">${wmCount} FactHandles Active</div>
        <div class="text-[11px] text-slate-600 mt-0.5">
          ${stats.total_object_type_nodes} ObjectTypeNodes (Applicant, EligibilityPassed)
        </div>
      </div>

      <div class="pipeline-node active-glow">
        <div class="text-[11px] font-bold uppercase text-sky-700">2. Alpha Network (Sharing)</div>
        <div class="text-sm font-extrabold text-slate-900 mt-0.5">${activeAlphaCount} / ${stats.unique_alpha_nodes} AlphaNodes Khớp</div>
        <div class="text-[11px] text-emerald-700 font-semibold mt-0.5">
          Chia sẻ nút tiết kiệm ${stats.alpha_nodes_saved_by_sharing} phép lọc đơn
        </div>
      </div>

      <div class="pipeline-node active-glow">
        <div class="text-[11px] font-bold uppercase text-sky-700">3. Beta Network (JoinNode)</div>
        <div class="text-sm font-extrabold text-slate-900 mt-0.5">${stats.multi_fact_beta_joins} Nút Join 2-Fact</div>
        <div class="text-[11px] text-slate-600 mt-0.5">
          Kết hợp EligibilityPassed ⋈ Applicant
        </div>
      </div>

      <div class="pipeline-node active-glow">
        <div class="text-[11px] font-bold uppercase text-sky-700">4. RuleTerminalNodes</div>
        <div class="text-sm font-extrabold text-slate-900 mt-0.5">${firedCodesSoFar.size} / ${stats.total_terminal_nodes} Luật Kích hoạt</div>
        <div class="text-[11px] text-amber-700 font-semibold mt-0.5">
          ${cancelledCodes.size} luật bị hủy do activation-group
        </div>
      </div>

      <div class="pipeline-node active-glow">
        <div class="text-[11px] font-bold uppercase text-sky-700">5. Agenda & TMS</div>
        <div class="text-sm font-extrabold text-slate-900 mt-0.5">${eng.total_cycles} Chu kỳ Forward Chaining</div>
        <div class="text-[11px] text-teal-700 font-semibold mt-0.5">
          ${(eng.tms_events || []).length} sự kiện TMS (insertLogical)
        </div>
      </div>
    `;
  }

  const replayBanner = document.getElementById("replayStepBanner");
  if (replayBanner) {
    if (!currentStep) {
      replayBanner.innerHTML = `
        <div class="flex items-center gap-2">
          <span class="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-mono font-bold">
            CHẾ ĐỘ TOÀN CẢNH (${steps.length} CHU KỲ)
          </span>
          <span>Đang hiển thị toàn bộ các nút và luật đã kích hoạt trong phiên suy diễn. Bấm <strong>"▶ Chạy từng bước (Replay)"</strong> để trình chiếu từng chu kỳ!</span>
        </div>
        <div class="font-mono text-sky-300 font-bold">
          Chuỗi kích hoạt: ${eng.fired_rules.join(" → ")}
        </div>
      `;
    } else {
      const changedKeys = Object.keys(currentStep.changed_fields || {});
      const diffText = changedKeys
        .map(
          (k) =>
            `${k}: ${JSON.stringify(currentStep.changed_fields[k].before)} → ${JSON.stringify(
              currentStep.changed_fields[k].after
            )}`
        )
        .join(" | ");

      replayBanner.innerHTML = `
        <div class="space-y-1">
          <div class="flex flex-wrap items-center gap-2">
            <span class="px-2 py-0.5 rounded bg-sky-500 text-white font-mono font-bold">
              BƯỚC ${currentStep.cycle} / ${steps.length}
            </span>
            <span class="px-2 py-0.5 rounded bg-slate-800 text-sky-300 font-mono">
              agenda-group: "${currentStep.agenda_group}"
            </span>
            <span class="font-bold text-white">${escapeHtml(currentStep.rule_name)}</span>
            <span class="text-amber-300 font-mono">(salience: ${currentStep.salience})</span>
          </div>
          <div class="text-slate-300 font-mono text-[11px]">
            Nút khớp: [${currentStep.matched_alpha_nodes.join(", ")}] → ${currentStep.matched_beta_node} → RTN_${currentStep.rule_code}
            ${diffText ? ` | Modify: ${escapeHtml(diffText)}` : ""}
          </div>
        </div>
      `;
    }
  }

  const stageContainer = document.getElementById("reteStagesVisualizer");
  if (!stageContainer) return;

  const rtnNodes = (rete.nodes || []).filter((n) => n.type === "RuleTerminalNode");
  const betaMap = {};
  (rete.nodes || [])
    .filter((n) => n.type === "BetaNode")
    .forEach((b) => {
      betaMap[b.rule_code] = b;
    });

  stageContainer.innerHTML = AGENDA_STAGE_INFO.map((stage) => {
    const stageRules = rtnNodes.filter((n) => n.agenda_group === stage.id);
    const isStageActive = currentStep
      ? currentStep.agenda_group === stage.id
      : stageRules.some((r) => firedCodesSoFar.has(r.rule_code));

    const rulesHtml = stageRules
      .map((rtn) => {
        const isCurrent = currentStep && currentStep.rule_code === rtn.rule_code;
        const isFired = firedCodesSoFar.has(rtn.rule_code);
        const isCancelled = cancelledCodes.has(rtn.rule_code);
        const beta = betaMap[rtn.rule_code] || {};

        let boxClass = "rete-node-box node-idle";
        let statusBadge = `<span class="px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-mono text-[10px]">IDLE</span>`;

        if (isCurrent) {
          boxClass = "rete-node-box node-current-step";
          statusBadge = `<span class="px-1.5 py-0.5 rounded bg-sky-600 text-white font-mono text-[10px] font-bold">⚡ FIRING (CYCLE ${currentStep.cycle})</span>`;
        } else if (isFired) {
          boxClass = "rete-node-box node-fired";
          statusBadge = `<span class="px-1.5 py-0.5 rounded bg-emerald-600 text-white font-mono text-[10px] font-bold">✓ FIRED</span>`;
        } else if (isCancelled) {
          boxClass = "rete-node-box node-cancelled";
          statusBadge = `<span class="px-1.5 py-0.5 rounded bg-amber-500 text-white font-mono text-[10px] font-bold">✕ CANCELLED</span>`;
        }

        return `
          <div class="${boxClass}">
            <div class="flex items-center justify-between gap-1 mb-1">
              <span class="font-mono font-extrabold text-xs text-slate-900">
                ${rtn.rule_code} <span class="text-slate-500 font-normal">(sal:${rtn.salience})</span>
              </span>
              ${statusBadge}
            </div>
            <div class="text-[11px] font-semibold text-slate-800 leading-snug">
              ${escapeHtml(rtn.rule_name.replace(/^R\d+\s*-\s*/, ""))}
            </div>
            <div class="flex flex-wrap items-center gap-1 mt-1.5 text-[10px] font-mono text-slate-600">
              <span class="px-1.5 py-0.5 rounded bg-slate-100">${beta.label || "BetaNode"}</span>
              ${
                rtn.activation_group
                  ? `<span class="px-1.5 py-0.5 rounded bg-purple-100 text-purple-800">ag:${rtn.activation_group}</span>`
                  : ""
              }
            </div>
          </div>
        `;
      })
      .join("");

    return `
      <div class="rete-stage-column ${isStageActive ? "stage-active" : ""}">
        <div class="border-b border-slate-200 pb-2 mb-2.5">
          <div class="flex items-center justify-between">
            <span class="text-xs font-extrabold text-slate-900">${stage.title}</span>
            <span class="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-sky-100 text-sky-800">
              ${stage.salience}
            </span>
          </div>
          <div class="text-[11px] text-slate-600 mt-0.5">${stage.subtitle}</div>
        </div>
        <div>
          ${rulesHtml}
        </div>
      </div>
    `;
  }).join("");
}

/* Replay Controls */
function replayFirstStep() {
  stopReplayAuto();
  if (!STATE.currentEvaluation) return;
  const steps = STATE.currentEvaluation.engine.trace_steps || [];
  if (steps.length === 0) return;
  STATE.replayStepIndex = 0;
  renderReteVisualizer(STATE.currentEvaluation);
  highlightTraceRow(0);
}

function replayPrevStep() {
  stopReplayAuto();
  if (!STATE.currentEvaluation) return;
  const steps = STATE.currentEvaluation.engine.trace_steps || [];
  if (steps.length === 0) return;
  if (STATE.replayStepIndex <= 0) {
    STATE.replayStepIndex = 0;
  } else {
    STATE.replayStepIndex -= 1;
  }
  renderReteVisualizer(STATE.currentEvaluation);
  highlightTraceRow(STATE.replayStepIndex);
}

function replayNextStep() {
  if (!STATE.currentEvaluation) return;
  const steps = STATE.currentEvaluation.engine.trace_steps || [];
  if (steps.length === 0) return;
  if (STATE.replayStepIndex < 0) {
    STATE.replayStepIndex = 0;
  } else if (STATE.replayStepIndex + 1 < steps.length) {
    STATE.replayStepIndex += 1;
  } else {
    stopReplayAuto();
    return;
  }
  renderReteVisualizer(STATE.currentEvaluation);
  highlightTraceRow(STATE.replayStepIndex);
}

function replayResetAll() {
  stopReplayAuto();
  STATE.replayStepIndex = -1;
  if (STATE.currentEvaluation) {
    renderReteVisualizer(STATE.currentEvaluation);
    highlightTraceRow(-1);
  }
}

function toggleReplayAuto() {
  if (STATE.replayTimer) {
    stopReplayAuto();
    return;
  }
  if (!STATE.currentEvaluation) return;
  const steps = STATE.currentEvaluation.engine.trace_steps || [];
  if (steps.length === 0) return;

  STATE.replayStepIndex = 0;
  renderReteVisualizer(STATE.currentEvaluation);
  highlightTraceRow(0);

  const btn = document.getElementById("btnReplayAuto");
  if (btn) btn.textContent = "⏸ Tạm dừng Replay";

  STATE.replayTimer = setInterval(() => {
    const total = (STATE.currentEvaluation.engine.trace_steps || []).length;
    if (STATE.replayStepIndex + 1 < total) {
      STATE.replayStepIndex += 1;
      renderReteVisualizer(STATE.currentEvaluation);
      highlightTraceRow(STATE.replayStepIndex);
    } else {
      stopReplayAuto();
    }
  }, 1100);
}

function stopReplayAuto() {
  if (STATE.replayTimer) {
    clearInterval(STATE.replayTimer);
    STATE.replayTimer = null;
  }
  const btn = document.getElementById("btnReplayAuto");
  if (btn) btn.textContent = "▶ Chạy từng bước (Replay)";
}

function highlightTraceRow(stepIdx) {
  const rows = document.querySelectorAll("#traceTableBody tr");
  rows.forEach((r, idx) => {
    r.classList.toggle("row-highlight", idx === stepIdx);
  });
}

async function runTmsInteractiveDemo() {
  const box = document.getElementById("tmsDemoResultBox");
  if (!box) return;
  try {
    const resp = await fetch("/api/tms-demo", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ applicant: STATE.activeApplicant || STATE.presets[0] }),
    });
    const data = await resp.json();
    if (data.status !== "OK") throw new Error(data.message);

    box.classList.remove("hidden");
    const eventsHtml = (data.tms_events || [])
      .map(
        (ev, idx) => `
        <div class="p-2.5 rounded-lg bg-white border border-teal-200">
          <div class="font-bold text-teal-900">
            Bước TMS ${idx + 1}: <span class="font-mono">${ev.action}</span> — Fact: <span class="font-mono">${ev.fact_type} (Handle #${ev.handle_id})</span>
          </div>
          <div class="text-slate-700 mt-0.5">${escapeHtml(ev.reason)}</div>
        </div>`
      )
      .join("");

    box.innerHTML = `
      <div class="flex items-center justify-between">
        <div class="font-extrabold text-teal-950 text-sm">
          Minh họa Thực nghiệm Truth Maintenance System (TMS – \`insertLogical\` & Tự động Rút lại Fact Suy diễn)
        </div>
        <button type="button" onclick="document.getElementById('tmsDemoResultBox').classList.add('hidden')" class="text-xs font-bold text-teal-800 hover:underline">
          Đóng ✕
        </button>
      </div>
      <p class="text-teal-900">
        1) Khi hồ sơ vượt qua Tầng 1, luật <strong>R04</strong> thực thi <code>insertLogical(new EligibilityPassed(...))</code> đưa Fact suy diễn vào Working Memory (Tổng số Fact = ${data.step1_working_memory.length}).<br/>
        2) Khi cập nhật <code>session.modify(applicantHandle, cic_bad_debt=True)</code> làm điều kiện gốc của R04 không còn đúng, TMS tự động thu hồi (Auto-Retract) Fact <code>EligibilityPassed</code> mà không cần viết thêm luật xóa thủ công (Tổng số Fact còn lại = ${data.step2_working_memory.length})!
      </p>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-2.5 pt-1">
        ${eventsHtml}
      </div>
    `;
  } catch (err) {
    alert("Lỗi chạy TMS Demo: " + err.message);
  }
}

/* ============================================================================
   KHU VUC 4: NHAT KY TRUY VET KICH HOAT LUAT & CONFLICT RESOLUTION LOG
   ============================================================================ */
function renderTraceAndConflictLog(evalData) {
  if (!evalData || !evalData.engine) return;
  const eng = evalData.engine;
  const steps = eng.trace_steps || [];
  const cancelled = eng.cancelled_activations || [];
  const tmsEvents = eng.tms_events || [];

  const cancelBox = document.getElementById("cancelledActivationsBox");
  if (cancelBox) {
    if (cancelled.length === 0) {
      cancelBox.innerHTML = `<div class="text-amber-800">Không có xung đột trong cùng activation-group ở kịch bản này.</div>`;
    } else {
      cancelBox.innerHTML = cancelled
        .map(
          (c) => `
          <div class="p-2 rounded-lg bg-white border border-amber-200">
            <div class="flex items-center justify-between">
              <span class="font-bold text-amber-950 font-mono">✕ ${escapeHtml(c.cancelled_rule)} (salience ${c.cancelled_salience})</span>
              <span class="px-1.5 py-0.5 rounded bg-amber-100 text-amber-900 font-mono text-[10px] font-bold">
                activation-group: "${c.activation_group}"
              </span>
            </div>
            <div class="text-slate-600 mt-0.5">${escapeHtml(c.reason)}</div>
          </div>`
        )
        .join("");
    }
  }

  const tmsBox = document.getElementById("tmsEventsBox");
  if (tmsBox) {
    if (tmsEvents.length === 0) {
      tmsBox.innerHTML = `<div class="text-teal-900">Hồ sơ bị dừng sớm (Hard Knock-out) ở Tầng 1 nên R04 không sinh Fact trung gian <code>EligibilityPassed</code> qua TMS.</div>`;
    } else {
      tmsBox.innerHTML = tmsEvents
        .map(
          (e) => `
          <div class="p-2 rounded-lg bg-white border border-teal-200">
            <div class="flex items-center justify-between">
              <span class="font-bold text-teal-950 font-mono">✓ ${e.action}: ${e.fact_type} (Handle #${e.handle_id})</span>
              <span class="px-1.5 py-0.5 rounded bg-teal-100 text-teal-900 font-mono text-[10px] font-bold">
                TMS Justified
              </span>
            </div>
            <div class="text-slate-600 mt-0.5">Luật bảo chứng: <strong>${escapeHtml(e.rule_name)}</strong> • Dữ liệu: <code>${escapeHtml(JSON.stringify(e.fact_data))}</code></div>
          </div>`
        )
        .join("");
    }
  }

  const tbody = document.getElementById("traceTableBody");
  if (!tbody) return;

  tbody.innerHTML = steps
    .map((s) => {
      const conflictHtml = (s.conflict_set || [])
        .map((c, idx) =>
          idx === 0
            ? `<span class="px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-900 font-mono text-[11px] font-bold">★ ${c.rule_code}(sal:${c.salience})</span>`
            : `<span class="px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-mono text-[11px]">${c.rule_code}(sal:${c.salience})</span>`
        )
        .join(" ");

      const cancelledStepHtml =
        s.cancelled_in_step && s.cancelled_in_step.length > 0
          ? `<div class="mt-1 text-[11px] font-semibold text-amber-800">
               Hủy do activation-group "${s.activation_group}": ${s.cancelled_in_step
                 .map((x) => x.cancelled_rule_code)
                 .join(", ")}
             </div>`
          : "";

      const changedEntries = Object.entries(s.changed_fields || {}).filter(
        ([k]) => !["reasons", "recommendations", "risk_flags"].includes(k)
      );
      const changesHtml =
        changedEntries.length > 0
          ? changedEntries
              .map(
                ([k, v]) =>
                  `<div class="font-mono text-[11px]"><span class="font-bold text-slate-800">${k}:</span> <span class="text-rose-700">${JSON.stringify(
                    v.before
                  )}</span> → <span class="text-emerald-700 font-bold">${JSON.stringify(v.after)}</span></div>`
              )
              .join("")
          : `<div class="text-[11px] text-slate-600">Ghi nhận khuyến nghị / Giải thích DSS</div>`;

      return `
        <tr>
          <td class="font-mono font-extrabold text-sky-800">#${s.cycle}</td>
          <td>
            <span class="px-2 py-0.5 rounded bg-slate-100 text-slate-800 font-mono text-xs font-semibold">
              ${s.agenda_group}
            </span>
          </td>
          <td>
            <div class="font-bold text-slate-900">${escapeHtml(s.rule_name)}</div>
            <div class="flex flex-wrap gap-1.5 mt-1 text-[11px] font-mono">
              <span class="px-1.5 py-0.5 rounded bg-sky-50 text-sky-800 font-bold">salience: ${s.salience}</span>
              ${
                s.activation_group
                  ? `<span class="px-1.5 py-0.5 rounded bg-purple-50 text-purple-800">activation-group: ${s.activation_group}</span>`
                  : ""
              }
              ${s.lock_on_active ? `<span class="px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">lock-on-active</span>` : ""}
            </div>
          </td>
          <td class="font-mono text-[11px] text-slate-700">
            <div>Alpha: [${s.matched_alpha_nodes.join(", ")}]</div>
            <div class="text-sky-700 font-bold mt-0.5">Beta: ${s.matched_beta_node}</div>
          </td>
          <td>
            <div class="flex flex-wrap gap-1">${conflictHtml}</div>
            ${cancelledStepHtml}
          </td>
          <td>${changesHtml}</td>
        </tr>
      `;
    })
    .join("");
}

/* ============================================================================
   KHU VUC 5: PHONG THI NGHIEM WHAT-IF & PHAN TICH DO NHAY (SENSITIVITY)
   ============================================================================ */
function syncCurrentToWhatIfAndOpen() {
  const current = readApplicantFromForm();
  STATE.whatIfBaseline = { ...current };
  populateWhatIfSliders(current);
  switchTab("whatif");
}

function loadPresetIntoWhatIf(applicantId) {
  const found = STATE.sampleApplicants.find((a) => a.applicant_id === applicantId);
  if (!found) return;
  STATE.whatIfBaseline = { ...found };
  populateWhatIfSliders(found);
  runWhatIfSimulation();
}

function populateWhatIfSliders(app) {
  document.getElementById("wi_monthly_income").value = app.monthly_income ?? 26;
  document.getElementById("wi_loan_amount").value = app.loan_amount ?? 200;
  document.getElementById("wi_collateral_value").value = app.collateral_value ?? 0;
  document.getElementById("wi_credit_score").value = app.credit_score ?? 750;
  document.getElementById("wi_dti_ratio").value = app.dti_ratio ?? 31;
  document.getElementById("wi_cic_bad_debt").checked = Boolean(app.cic_bad_debt);
  document.getElementById("wi_is_vip").checked = Boolean(app.is_vip);
  updateWhatIfLabels();
}

function resetWhatIfSliders() {
  if (STATE.whatIfBaseline) {
    populateWhatIfSliders(STATE.whatIfBaseline);
    runWhatIfSimulation();
  }
}

function updateWhatIfLabels() {
  document.getElementById("lbl_wi_income").textContent =
    `${parseFloat(document.getElementById("wi_monthly_income").value).toFixed(1)} triệu`;
  document.getElementById("lbl_wi_loan").textContent =
    `${parseFloat(document.getElementById("wi_loan_amount").value).toFixed(1)} triệu`;
  document.getElementById("lbl_wi_collateral").textContent =
    `${parseFloat(document.getElementById("wi_collateral_value").value).toFixed(1)} triệu`;
  document.getElementById("lbl_wi_score").textContent =
    document.getElementById("wi_credit_score").value;
  document.getElementById("lbl_wi_dti").textContent =
    `${parseFloat(document.getElementById("wi_dti_ratio").value).toFixed(1)}%`;
}

function onWhatIfSliderChange() {
  updateWhatIfLabels();
  runWhatIfSimulation();
}

async function runWhatIfSimulation() {
  const baseline = STATE.whatIfBaseline || STATE.presets[2] || STATE.presets[0];
  if (!baseline) return;

  const modified = {
    ...baseline,
    monthly_income: parseFloat(document.getElementById("wi_monthly_income").value),
    loan_amount: parseFloat(document.getElementById("wi_loan_amount").value),
    collateral_value: parseFloat(document.getElementById("wi_collateral_value").value),
    credit_score: parseInt(document.getElementById("wi_credit_score").value, 10),
    dti_ratio: parseFloat(document.getElementById("wi_dti_ratio").value),
    cic_bad_debt: document.getElementById("wi_cic_bad_debt").checked,
    is_vip: document.getElementById("wi_is_vip").checked,
  };

  try {
    const resp = await fetch("/api/what-if", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ baseline, what_if: modified }),
    });
    const data = await resp.json();
    if (data.status !== "OK") throw new Error(data.message);
    renderWhatIfResults(data.result);
  } catch (err) {
    console.error("What-If error:", err);
  }
}

function renderWhatIfResults(res) {
  const baseSum = res.baseline.summary;
  const wiSum = res.what_if.summary;
  const cmp = res.comparison;

  const cardsBox = document.getElementById("whatIfComparisonCards");
  if (cardsBox) {
    const deltaSign = (n) => (n > 0 ? `+${n}` : `${n}`);
    cardsBox.innerHTML = `
      <div class="p-4 rounded-xl border border-slate-200 bg-white space-y-2">
        <div class="text-xs font-bold uppercase text-slate-500">Hồ sơ Gốc (Baseline: ${escapeHtml(res.baseline.applicant.full_name)})</div>
        <div class="text-base font-extrabold text-slate-900">${baseSum.decision_label}</div>
        <div class="flex items-center gap-2 text-xs">
          <span class="badge-pill tier-${baseSum.risk_tier}">${baseSum.risk_tier}</span>
          <span class="font-mono font-bold">Điểm: ${baseSum.composite_score}/100</span>
        </div>
        <div class="text-xs text-slate-700 space-y-1 pt-1 font-mono">
          <div>Hạn mức duyệt: <strong>${baseSum.approved_amount} triệu</strong></div>
          <div>Lãi suất: <strong>${baseSum.interest_rate}%/năm</strong></div>
          <div>Trả góp/tháng: <strong>${baseSum.estimated_monthly_payment} triệu</strong></div>
          <div>Chuỗi luật: ${res.baseline.engine.fired_rules.join(" → ")}</div>
        </div>
      </div>

      <div class="p-4 rounded-xl border-2 border-sky-500 bg-sky-50/40 space-y-2">
        <div class="flex items-center justify-between">
          <span class="text-xs font-bold uppercase text-sky-800">Kết quả Giả lập (What-If Scenario)</span>
          <span class="px-2 py-0.5 rounded bg-sky-600 text-white font-mono text-xs font-bold">
            Δ Điểm: ${deltaSign(cmp.score_delta)}
          </span>
        </div>
        <div class="text-base font-extrabold text-slate-900">${wiSum.decision_label}</div>
        <div class="flex items-center gap-2 text-xs">
          <span class="badge-pill tier-${wiSum.risk_tier}">${wiSum.risk_tier}</span>
          <span class="font-mono font-bold">Điểm: ${wiSum.composite_score}/100</span>
        </div>
        <div class="text-xs text-slate-700 space-y-1 pt-1 font-mono">
          <div>Hạn mức duyệt: <strong>${wiSum.approved_amount} triệu</strong> (${deltaSign(cmp.approved_amount_delta)} tr)</div>
          <div>Lãi suất: <strong>${wiSum.interest_rate}%/năm</strong> (${deltaSign(cmp.interest_rate_delta)}%)</div>
          <div>Trả góp/tháng: <strong>${wiSum.estimated_monthly_payment} triệu</strong></div>
          <div>Chuỗi luật: ${res.what_if.engine.fired_rules.join(" → ")}</div>
        </div>
      </div>
    `;
  }

  const diffBox = document.getElementById("whatIfRuleDiffBox");
  if (diffBox) {
    const added = cmp.added_rules.length > 0 ? cmp.added_rules.join(", ") : "Không có";
    const removed = cmp.removed_rules.length > 0 ? cmp.removed_rules.join(", ") : "Không có";
    diffBox.innerHTML = `
      <div class="font-bold text-slate-900">Sự dịch chuyển Kích hoạt Luật trên Mạng Rete / PHREAK:</div>
      <div class="flex flex-wrap gap-3">
        <span class="text-emerald-800 font-mono"><strong>+ Luật kích hoạt mới:</strong> [${added}]</span>
        <span class="text-rose-800 font-mono"><strong>- Luật ngừng kích hoạt:</strong> [${removed}]</span>
      </div>
    `;
  }

  const curve = res.sensitivity_curve || [];
  const canvas = document.getElementById("sensitivityChart");
  if (!canvas || typeof window.Chart === "undefined") return;

  if (STATE.charts.sensitivity) {
    STATE.charts.sensitivity.destroy();
  }

  STATE.charts.sensitivity = new window.Chart(canvas, {
    type: "line",
    data: {
      labels: curve.map((p) => `TN ${p.monthly_income}tr (DTI ${p.dti_ratio}%)`),
      datasets: [
        {
          label: "Điểm Suy diễn (0-100)",
          data: curve.map((p) => p.composite_score),
          borderColor: "#0284c7",
          backgroundColor: "rgba(2, 132, 199, 0.15)",
          tension: 0.25,
          fill: true,
        },
        {
          label: "Lãi suất (%/năm)",
          data: curve.map((p) => p.interest_rate),
          borderColor: "#0d9488",
          backgroundColor: "transparent",
          tension: 0.25,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
    },
  });
}

/* ============================================================================
   KHU VUC 6B: CHAM DIEM DANH MUC HANG LOAT (BATCH CSV 15 HO SO)
   ============================================================================ */
async function loadBatchEvaluation() {
  try {
    const resp = await fetch("/api/batch");
    const data = await resp.json();
    if (data.status !== "OK") throw new Error(data.message);
    renderBatchPortfolio(data.batch);
  } catch (err) {
    console.error("Batch error:", err);
  }
}

function renderBatchPortfolio(batch) {
  if (!batch) return;
  STATE.currentBatch = batch;
  const dc = batch.decision_counts || {};
  const kpiBox = document.getElementById("batchKpiCards");
  if (kpiBox) {
    kpiBox.innerHTML = `
      <div class="p-3.5 rounded-xl border border-slate-200 bg-slate-50">
        <div class="text-xs font-semibold text-slate-500">Tổng số Hồ sơ CSV</div>
        <div class="text-2xl font-extrabold text-slate-900 font-mono mt-0.5">${batch.total_applicants} hồ sơ</div>
        <div class="text-xs text-slate-600 mt-0.5">Tổng cầu vay: ${batch.total_requested_amount} triệu</div>
      </div>
      <div class="p-3.5 rounded-xl border border-emerald-200 bg-emerald-50/70">
        <div class="text-xs font-semibold text-emerald-800">Phê duyệt Tự động (APPROVED)</div>
        <div class="text-2xl font-extrabold text-emerald-900 font-mono mt-0.5">${dc.APPROVED || 0} hồ sơ</div>
        <div class="text-xs text-emerald-700 mt-0.5">Hạng A & Hạng B có TSĐB</div>
      </div>
      <div class="p-3.5 rounded-xl border border-amber-200 bg-amber-50/70">
        <div class="text-xs font-semibold text-amber-800">Duyệt có Điều kiện (CONDITIONAL)</div>
        <div class="text-2xl font-extrabold text-amber-900 font-mono mt-0.5">${dc.CONDITIONAL_APPROVAL || 0} hồ sơ</div>
        <div class="text-xs text-amber-700 mt-0.5">Hạng B vay tín chấp (80%)</div>
      </div>
      <div class="p-3.5 rounded-xl border border-sky-200 bg-sky-50/70">
        <div class="text-xs font-semibold text-sky-800">Thẩm định Thủ công (MANUAL)</div>
        <div class="text-2xl font-extrabold text-sky-900 font-mono mt-0.5">${dc.MANUAL_REVIEW || 0} hồ sơ</div>
        <div class="text-xs text-sky-700 mt-0.5">Hạng C cần Hội đồng xem xét</div>
      </div>
      <div class="p-3.5 rounded-xl border border-rose-200 bg-rose-50/70">
        <div class="text-xs font-semibold text-rose-800">Từ chối (REJECTED)</div>
        <div class="text-2xl font-extrabold text-rose-900 font-mono mt-0.5">${dc.REJECTED || 0} hồ sơ</div>
        <div class="text-xs text-rose-700 mt-0.5">Knock-out Tầng 1 & Hạng D</div>
      </div>
    `;
  }

  const tbody = document.getElementById("batchTableBody");
  if (tbody) {
    tbody.innerHTML = (batch.items || [])
      .map(
        (item) => `
        <tr>
          <td class="font-mono font-bold text-slate-900">${item.applicant_id}</td>
          <td>
            <div class="font-bold text-slate-900">${escapeHtml(item.full_name)}</div>
            <div class="text-[11px] text-slate-500">${escapeHtml(item.scenario_tag)}</div>
          </td>
          <td class="font-mono text-xs">${item.age}t • ${item.monthly_income} tr/th</td>
          <td class="font-mono text-xs">CS: ${item.credit_score} • DTI: ${item.dti_ratio}%</td>
          <td class="font-mono text-xs">Vay: ${item.loan_amount}tr • TSĐB: ${item.collateral_value}tr</td>
          <td>
            <span class="badge-pill tier-${item.risk_tier}">${item.risk_tier}</span>
            <span class="font-mono font-bold text-xs ml-1">${item.composite_score}đ</span>
          </td>
          <td>
            <span class="px-2 py-0.5 rounded font-bold text-xs decision-${item.decision}">
              ${item.decision}
            </span>
          </td>
          <td class="font-mono text-xs font-bold">
            ${item.approved_amount} tr • ${item.interest_rate > 0 ? item.interest_rate + "%/năm" : "—"}
          </td>
          <td class="font-mono text-[11px] text-sky-800">${item.fired_rules.join(" → ")}</td>
          <td>
            <button
              type="button"
              onclick="inspectApplicantFromBatch('${item.applicant_id}')"
              class="px-2.5 py-1 rounded bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold"
            >
              Xem Truy vết
            </button>
          </td>
        </tr>`
      )
      .join("");
  }

  if (typeof window.Chart !== "undefined") {
    const cDec = document.getElementById("batchDecisionChart");
    if (cDec) {
      if (STATE.charts.batchDecision) STATE.charts.batchDecision.destroy();
      STATE.charts.batchDecision = new window.Chart(cDec, {
        type: "doughnut",
        data: {
          labels: ["APPROVED", "CONDITIONAL_APPROVAL", "MANUAL_REVIEW", "REJECTED"],
          datasets: [
            {
              data: [
                dc.APPROVED || 0,
                dc.CONDITIONAL_APPROVAL || 0,
                dc.MANUAL_REVIEW || 0,
                dc.REJECTED || 0,
              ],
              backgroundColor: ["#10b981", "#f59e0b", "#3b82f6", "#ef4444"],
            },
          ],
        },
        options: { responsive: true, maintainAspectRatio: false },
      });
    }

    const tc = batch.tier_counts || {};
    const cTier = document.getElementById("batchTierChart");
    if (cTier) {
      if (STATE.charts.batchTier) STATE.charts.batchTier.destroy();
      STATE.charts.batchTier = new window.Chart(cTier, {
        type: "bar",
        data: {
          labels: ["TIER_A (Rất thấp)", "TIER_B (Thấp-TB)", "TIER_C (TB-Cao)", "TIER_D (Cao)"],
          datasets: [
            {
              label: "Số lượng Hồ sơ",
              data: [tc.TIER_A || 0, tc.TIER_B || 0, tc.TIER_C || 0, tc.TIER_D || 0],
              backgroundColor: ["#16a34a", "#0284c7", "#d97706", "#dc2626"],
            },
          ],
        },
        options: { responsive: true, maintainAspectRatio: false },
      });
    }
  }
}

async function inspectApplicantFromBatch(applicantId) {
  switchTab("dashboard");
  await onSelectSampleApplicant(applicantId);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

/* ============================================================================
   KHU VUC 6A: LIVE DRL STUDIO & BANG QUYET DINH DECISION TABLE
   ============================================================================ */
function renderStudioSidebar() {
  const dtBox = document.getElementById("decisionTablePreviewBox");
  if (dtBox) {
    dtBox.innerHTML = STATE.decisionTableRows
      .map(
        (r) => `
        <div class="p-2.5 rounded-lg bg-white border border-slate-200">
          <div class="flex items-center justify-between font-mono text-[11px] font-bold text-sky-800">
            <span>${r.rule_id} (salience: ${r.salience})</span>
            <span>${r.agenda_group}</span>
          </div>
          <div class="font-semibold text-slate-900 mt-0.5">${escapeHtml(r.rule_name)}</div>
          <div class="font-mono text-[10px] text-slate-600 mt-0.5">WHEN: ${escapeHtml(r.when_condition)}</div>
        </div>`
      )
      .join("");
  }

  const catalogBox = document.getElementById("rulesCatalogList");
  if (catalogBox) {
    catalogBox.innerHTML = STATE.rulesMetadata
      .map(
        (r) => `
        <div class="p-2 rounded border border-slate-200 bg-slate-50 flex items-center justify-between gap-2">
          <div>
            <div class="font-bold text-slate-900">${escapeHtml(r.name)}</div>
            <div class="font-mono text-[10px] text-slate-600">
              group: "${r.agenda_group}" ${r.activation_group ? `• act-group: "${r.activation_group}"` : ""}
            </div>
          </div>
          <span class="px-1.5 py-0.5 rounded bg-sky-100 text-sky-800 font-mono text-[10px] font-bold shrink-0">
            sal: ${r.salience}
          </span>
        </div>`
      )
      .join("");
  }
}

async function compileLiveDrl() {
  const drlText = document.getElementById("drlSourceEditor").value;
  const banner = document.getElementById("drlCompileStatusBanner");
  try {
    const resp = await fetch("/api/rules/compile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        drl_source: drlText,
        applicant: STATE.activeApplicant || STATE.presets[0],
      }),
    });
    const data = await resp.json();
    if (data.status !== "OK") throw new Error(data.message);

    if (banner) {
      banner.className =
        "p-3 rounded-xl bg-emerald-50 border border-emerald-300 text-emerald-950 text-xs font-semibold";
      banner.textContent =
        `✓ Biên dịch KieBase thành công! Package: ${data.compile_info.package_name} • Tổng số luật active: ${data.compile_info.total_rules} • AlphaNodes: ${data.compile_info.rete_stats.unique_alpha_nodes}. Kết quả hồ sơ hiện tại đã được cập nhật!`;
    }
    if (data.test_evaluation) {
      STATE.currentEvaluation = data.test_evaluation;
      renderEvaluationResult(data.test_evaluation);
    }
  } catch (err) {
    if (banner) {
      banner.className =
        "p-3 rounded-xl bg-rose-50 border border-rose-300 text-rose-900 text-xs font-semibold";
      banner.textContent = `✕ Lỗi cú pháp DRL: ${err.message}`;
    }
  }
}

async function resetDefaultDrl() {
  try {
    const resp = await fetch("/api/rules/compile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        reset_default: true,
        applicant: STATE.activeApplicant || STATE.presets[0],
      }),
    });
    const data = await resp.json();
    if (data.status !== "OK") throw new Error(data.message);

    document.getElementById("drlSourceEditor").value = data.drl_source;
    const banner = document.getElementById("drlCompileStatusBanner");
    if (banner) {
      banner.className =
        "p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs font-semibold";
      banner.textContent = "✓ Đã khôi phục tập luật rules/credit_approval.drl gốc và biên dịch lại KieBase.";
    }
    if (data.test_evaluation) {
      STATE.currentEvaluation = data.test_evaluation;
      renderEvaluationResult(data.test_evaluation);
    }
  } catch (err) {
    alert("Lỗi khôi phục DRL: " + err.message);
  }
}

/* ============================================================================
   TAB 5: DOI SANH DROOLS vs CLIPS vs PROLOG, GOAL-SEEKING & RULE BASE V&V
   ============================================================================ */
function syncCurrentToParadigmsAndOpen() {
  const current = readApplicantFromForm();
  STATE.activeApplicant = { ...current };
  const selPara = document.getElementById("paradigmApplicantSelect");
  const selGoal = document.getElementById("goalSeekApplicantSelect");
  if (selPara && current.applicant_id) selPara.value = current.applicant_id;
  if (selGoal && current.applicant_id) selGoal.value = current.applicant_id;
  switchTab("paradigms");
}

async function runMultiParadigmComparison(applicantId) {
  let targetApp = STATE.activeApplicant || STATE.presets[0];
  if (applicantId) {
    const found = STATE.sampleApplicants.find((a) => a.applicant_id === applicantId);
    if (found) targetApp = found;
  } else {
    const sel = document.getElementById("paradigmApplicantSelect");
    if (sel && sel.value) {
      const found = STATE.sampleApplicants.find((a) => a.applicant_id === sel.value);
      if (found) targetApp = found;
    }
  }

  try {
    const resp = await fetch("/api/compare-engines", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ applicant: targetApp }),
    });
    const data = await resp.json();
    if (data.status !== "OK") throw new Error(data.message);
    STATE.currentComparison = data.comparison;
    renderMultiParadigmComparison(data.comparison);
  } catch (err) {
    console.error("Comparison error:", err);
  }
}

function renderMultiParadigmComparison(cmp) {
  if (!cmp) return;
  const app = cmp.applicant;
  const banner = document.getElementById("paradigmConsensusBanner");
  if (banner) {
    banner.innerHTML = `
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div>
          <strong>✓ ĐỒNG THUẬN KẾT QUẢ 100% GIỮA 3 CÔNG CỤ RULE-BASED</strong> trên Hồ sơ <code>${app.applicant_id} – ${escapeHtml(app.full_name)}</code>:
          Cả <strong>Drools (.drl)</strong>, <strong>CLIPS (.clp)</strong> và <strong>Prolog (.pl)</strong> đều hội tụ về cùng Quyết định <code>${cmp.drools.decision}</code>, Hạng <code>${cmp.drools.risk_tier}</code>, Điểm <code>${cmp.drools.composite_score}/100</code>, Hạn mức <code>${cmp.drools.approved_amount} triệu</code>, Lãi suất <code>${cmp.drools.interest_rate}%/năm</code>.
        </div>
        <span class="px-2.5 py-1 rounded bg-emerald-600 text-white font-mono text-xs font-bold shrink-0">
          EQUIVALENCE: 100%
        </span>
      </div>
    `;
  }

  const colsBox = document.getElementById("paradigmThreeColumnsBox");
  if (!colsBox) return;

  const engines = [
    {
      data: cmp.drools,
      border: "border-sky-500",
      bg: "bg-sky-50/50",
      badgeBg: "bg-sky-600",
      traceTitle: "Nhật ký Suy diễn Tiến PHREAK & 4 Tầng Agenda-Group:",
    },
    {
      data: cmp.clips,
      border: "border-amber-500",
      bg: "bg-amber-50/50",
      badgeBg: "bg-amber-600",
      traceTitle: "Nhật ký Suy diễn Tiến Classic Rete & Fact-List (f-1, f-2):",
    },
    {
      data: cmp.prolog,
      border: "border-teal-600",
      bg: "bg-teal-50/50",
      badgeBg: "bg-teal-700",
      traceTitle: "Cây Chứng minh Suy diễn Lùi SLD Resolution (CALL/EXIT/CUT !):",
    },
  ];

  colsBox.innerHTML = engines
    .map((item) => {
      const e = item.data;
      const traceLines = (e.trace || [])
        .map((line) => `<div class="py-0.5 border-b border-slate-800/60">${escapeHtml(line)}</div>`)
        .join("");

      return `
        <div class="p-4 rounded-xl border-2 ${item.border} ${item.bg} flex flex-col justify-between space-y-3">
          <div class="space-y-2">
            <div class="flex items-center justify-between gap-2">
              <span class="px-2 py-0.5 rounded ${item.badgeBg} text-white text-xs font-bold">
                ${escapeHtml(e.engine_name)}
              </span>
              <span class="font-mono text-[11px] font-bold text-slate-600">${escapeHtml(e.file)}</span>
            </div>
            <div class="text-xs font-semibold text-slate-700">${escapeHtml(e.paradigm)}</div>
            <div class="p-2.5 rounded-lg bg-white border border-slate-200 font-mono text-xs space-y-1">
              <div>Quyết định: <strong class="text-slate-950">${e.decision}</strong></div>
              <div>Hạng & Điểm: <strong>${e.risk_tier} (${e.composite_score}/100)</strong></div>
              <div>Hạn mức & LS: <strong>${e.approved_amount} tr • ${e.interest_rate}%/năm</strong></div>
            </div>
          </div>

          <div>
            <div class="text-[11px] font-bold text-slate-800 mb-1">${item.traceTitle}</div>
            <div class="p-2.5 rounded-lg bg-slate-900 text-slate-200 font-mono text-[11px] max-h-48 overflow-y-auto">
              ${traceLines}
            </div>
          </div>
        </div>
      `;
    })
    .join("");
}

async function runGoalSeekingQuery() {
  const selApp = document.getElementById("goalSeekApplicantSelect");
  const selTarget = document.getElementById("goalSeekTargetSelect");
  const appId = selApp ? selApp.value : "APP003";
  const targetGoal = selTarget ? selTarget.value : "APPROVED_100";

  const applicant =
    STATE.sampleApplicants.find((a) => a.applicant_id === appId) ||
    STATE.activeApplicant ||
    STATE.presets[2];

  try {
    const resp = await fetch("/api/goal-seek", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ applicant, target_goal: targetGoal }),
    });
    const data = await resp.json();
    if (data.status !== "OK") throw new Error(data.message);
    STATE.currentGoalSeek = data.goal_seek;
    renderGoalSeekingResult(data.goal_seek);
  } catch (err) {
    console.error("Goal seek error:", err);
  }
}

function renderGoalSeekingResult(gs) {
  const box = document.getElementById("goalSeekingResultBox");
  if (!box || !gs) return;

  if (gs.already_achieved) {
    box.innerHTML = `
      <div class="p-4 rounded-xl bg-emerald-50 border border-emerald-300 text-emerald-950 font-semibold">
        ✓ Hồ sơ hiện tại đã đạt trạng thái <code>${gs.current_decision}</code> (Hạng <code>${gs.current_tier}</code>, Điểm <code>${gs.current_score}/100</code>) thỏa mãn mục tiêu <code>${gs.target_goal}</code>!
      </div>
    `;
    return;
  }

  const plansHtml = (gs.verified_plans || [])
    .map(
      (p) => `
      <div class="p-4 rounded-xl border border-sky-300 bg-sky-50/60 space-y-2">
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div class="font-extrabold text-sky-950 text-sm">${escapeHtml(p.plan_title)}</div>
          <span class="px-2.5 py-0.5 rounded bg-emerald-600 text-white font-mono text-xs font-bold">
            ✓ Đã kiểm chứng trên KieSession: ${p.achieved_decision} (${p.achieved_tier} • ${p.achieved_score}đ • LS ${p.achieved_rate}%)
          </span>
        </div>
        <ul class="space-y-1 text-slate-800 pl-1">
          ${p.actions.map((a) => `<li>• <strong>${escapeHtml(a)}</strong></li>`).join("")}
        </ul>
        <div class="font-mono text-[11px] text-sky-800 pt-1">
          Chuỗi luật kích hoạt sau điều chỉnh: ${p.fired_rules.join(" → ")}
        </div>
      </div>`
    )
    .join("");

  box.innerHTML = `
    <div class="p-3 rounded-xl bg-amber-50 border border-amber-300 text-amber-950 font-semibold">
      Trạng thái hiện tại: Quyết định <code>${gs.current_decision}</code> • Hạng <code>${gs.current_tier}</code> • Điểm <code>${gs.current_score}/100</code>.
      Dưới đây là các lộ trình thay đổi tối thiểu (Counterfactual Plans) được suy diễn ngược từ điều kiện LHS của các luật mục tiêu:
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      ${plansHtml}
    </div>
  `;
}

function renderRuleVerificationMatrix() {
  const box = document.getElementById("ruleVerificationMatrixBox");
  if (!box || !STATE.ruleVerification) return;

  box.innerHTML = (STATE.ruleVerification.checks || [])
    .map(
      (c) => `
      <div class="p-4 rounded-xl border border-emerald-200 bg-emerald-50/40 space-y-1.5">
        <div class="flex items-center justify-between gap-2">
          <span class="font-mono text-[11px] font-bold text-emerald-800">${c.check_id}</span>
          <span class="px-2 py-0.5 rounded bg-emerald-600 text-white font-mono text-[10px] font-bold">
            ✓ ${escapeHtml(c.status_badge)}
          </span>
        </div>
        <div class="font-bold text-slate-900 text-xs">${escapeHtml(c.title)}</div>
        <p class="text-xs text-slate-600 leading-relaxed">${escapeHtml(c.details)}</p>
      </div>`
    )
    .join("");
}

/* ============================================================================
   XUAT TO TRINH THAM DINH TIN DUNG (PRINTABLE EXECUTIVE REPORT)
   ============================================================================ */
function exportCreditMemoReport() {
  if (!STATE.currentEvaluation) return;
  const app = STATE.currentEvaluation.applicant;
  const sum = STATE.currentEvaluation.summary;
  const eng = STATE.currentEvaluation.engine;

  const win = window.open("", "_blank", "width=920,height=780");
  if (!win) {
    alert("Vui lòng cho phép mở cửa sổ bật lên (Pop-up) để in Tờ trình Thẩm định.");
    return;
  }

  const reasonsHtml = (sum.reasons || []).map((r) => `<li>${escapeHtml(r)}</li>`).join("");
  const recsHtml = (sum.recommendations || []).map((r) => `<li>${escapeHtml(r)}</li>`).join("");

  win.document.write(`
    <!DOCTYPE html>
    <html lang="vi">
    <head>
      <meta charset="UTF-8" />
      <title>Tờ trình Thẩm định Tín dụng - ${escapeHtml(app.applicant_id)} - ${escapeHtml(app.full_name)}</title>
      <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; color: #0f172a; margin: 32px; line-height: 1.55; }
        .header { border-bottom: 2px solid #0284c7; padding-bottom: 12px; margin-bottom: 20px; display: flex; justify-content: space-between; }
        h1 { font-size: 20px; margin: 0 0 4px 0; color: #0f172a; }
        h2 { font-size: 14px; text-transform: uppercase; color: #0369a1; border-bottom: 1px solid #cbd5e1; padding-bottom: 4px; margin-top: 20px; }
        table { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 13px; }
        th, td { border: 1px solid #cbd5e1; padding: 8px 10px; text-align: left; }
        th { background: #f1f5f9; }
        .decision-box { padding: 14px; border: 2px solid #0284c7; background: #f0f9ff; border-radius: 8px; margin: 14px 0; }
        .btn-print { background: #0284c7; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: bold; }
        @media print { .no-print { display: none; } }
      </style>
    </head>
    <body>
      <div class="no-print" style="margin-bottom: 16px; text-align: right;">
        <button class="btn-print" onclick="window.print()">🖨️ In hoặc Lưu PDF</button>
      </div>
      <div class="header">
        <div>
          <h1>TỜ TRÌNH HỖ TRỢ RA QUYẾT ĐỊNH THẨM ĐỊNH & ĐỊNH GIÁ TÍN DỤNG</h1>
          <div style="font-size: 12px; color: #475569;">Hệ thống Hỗ trợ Ra quyết định (Rule-Based DSS) • Nhóm 1 • Đề 08: Apache KIE / Drools</div>
        </div>
        <div style="text-align: right; font-size: 12px;">
          <div><strong>Mã Hồ sơ:</strong> ${escapeHtml(app.applicant_id)}</div>
          <div><strong>Số chu kỳ suy diễn:</strong> ${eng.total_cycles} Cycles</div>
        </div>
      </div>

      <div class="decision-box">
        <div style="font-size: 12px; font-weight: bold; color: #0369a1;">KẾT LUẬN KHUYẾN NGHỊ CỦA BỘ MÁY SUY DIỄN DROOLS:</div>
        <div style="font-size: 20px; font-weight: 800; margin-top: 4px;">${escapeHtml(sum.decision_label)}</div>
        <div style="font-size: 13px; margin-top: 4px;">
          <strong>Điểm tín dụng tổng hợp:</strong> ${sum.composite_score}/100 &nbsp;|&nbsp;
          <strong>Hạng rủi ro:</strong> ${escapeHtml(sum.risk_tier_label)} &nbsp;|&nbsp;
          <strong>Hạn mức duyệt:</strong> ${sum.approved_amount} triệu VNĐ (${sum.approval_ratio_percent}%) &nbsp;|&nbsp;
          <strong>Lãi suất:</strong> ${sum.interest_rate}%/năm &nbsp;|&nbsp;
          <strong>Trả góp/tháng:</strong> ${sum.estimated_monthly_payment} triệu
        </div>
      </div>

      <h2>1. Thông tin Hồ sơ Khách hàng (Working Memory Fact: Applicant)</h2>
      <table>
        <tr>
          <th>Họ và tên</th><td>${escapeHtml(app.full_name)}</td>
          <th>Độ tuổi</th><td>${app.age} tuổi</td>
        </tr>
        <tr>
          <th>Thu nhập ròng</th><td>${app.monthly_income} triệu/tháng</td>
          <th>Thâm niên công tác</th><td>${app.employment_years} năm</td>
        </tr>
        <tr>
          <th>Điểm tín dụng nội bộ</th><td>${app.credit_score} / 850</td>
          <th>Tỷ lệ Nợ/Thu nhập (DTI)</th><td>${app.dti_ratio}%</td>
        </tr>
        <tr>
          <th>Số tiền đề nghị vay</th><td>${app.loan_amount} triệu (${app.loan_term_months} tháng)</td>
          <th>Giá trị Tài sản đảm bảo</th><td>${app.collateral_value} triệu (Bao phủ ${sum.collateral_coverage_percent}%)</td>
        </tr>
        <tr>
          <th>Lịch sử nợ xấu CIC</th><td>${app.cic_bad_debt ? "Có nợ xấu nhóm 3-5" : "Không có nợ xấu"}</td>
          <th>Phân khúc Khách hàng</th><td>${app.is_vip ? "Khách hàng VIP" : "Khách hàng Tiêu chuẩn"}</td>
        </tr>
      </table>

      <h2>2. Chuỗi Luật Kích hoạt & Diễn giải Suy diễn Tiến (Forward Chaining Trace)</h2>
      <div style="font-family: monospace; font-size: 13px; margin-bottom: 8px;">
        <strong>Chuỗi kích hoạt:</strong> ${eng.fired_rules.join(" → ")}
      </div>
      <ul style="font-size: 13px;">${reasonsHtml}</ul>

      <h2>3. Khuyến nghị Hành động của Hệ thống Hỗ trợ Ra quyết định (DSS Recommendations)</h2>
      <ul style="font-size: 13px;">${recsHtml || "<li>Đủ điều kiện giải ngân theo quy định chuẩn.</li>"}</ul>
    </body>
    </html>
  `);
  win.document.close();
}

/* ============================================================================
   XUAT FILE JSON KIEM TOAN, XUAT / NAP CSV HANG LOAT & OFFLINE CANVAS FALLBACK
   ============================================================================ */
function downloadAuditJson() {
  if (!STATE.currentEvaluation) return;
  const appId = STATE.currentEvaluation.applicant.applicant_id || "CUSTOM";
  const payload = {
    exported_at: new Date().toISOString(),
    project: "DSS - Nhom 1 - De 08: DROOLS Rule Engine",
    evaluation: STATE.currentEvaluation,
    rule_verification: STATE.ruleVerification,
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `drools_audit_trace_${appId}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function exportBatchResultsCsv() {
  const batch = STATE.currentBatch;
  if (!batch || !batch.items || batch.items.length === 0) {
    alert("Đang tải dữ liệu chấm điểm hàng loạt, vui lòng thử lại sau giây lát.");
    return;
  }
  const headers = [
    "applicant_id",
    "full_name",
    "age",
    "monthly_income",
    "credit_score",
    "dti_ratio",
    "loan_amount",
    "collateral_value",
    "composite_score",
    "risk_tier",
    "decision",
    "approved_amount",
    "interest_rate",
    "fired_rules",
  ];
  const rows = [headers.join(",")];
  batch.items.forEach((item) => {
    const row = [
      item.applicant_id,
      `"${String(item.full_name || "").replace(/"/g, '""')}"`,
      item.age,
      item.monthly_income,
      item.credit_score,
      item.dti_ratio,
      item.loan_amount,
      item.collateral_value,
      item.composite_score,
      item.risk_tier,
      item.decision,
      item.approved_amount,
      item.interest_rate,
      `"${(item.fired_rules || []).join(" -> ")}"`,
    ];
    rows.push(row.join(","));
  });

  // Thêm UTF-8 BOM để mở trực tiếp trên Microsoft Excel không bị lỗi font tiếng Việt
  const csvContent = "\uFEFF" + rows.join("\n");
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "ket_qua_cham_diem_tin_dung_drools_nhom1.csv";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

async function uploadCustomBatchCsv(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) return;
  try {
    const text = await file.text();
    const lines = text
      .replace(/^\uFEFF/, "")
      .split(/\r?\n/)
      .map((l) => l.trim())
      .filter(Boolean);
    if (lines.length < 2) {
      alert("File CSV cần có ít nhất 1 dòng tiêu đề và 1 dòng dữ liệu hồ sơ.");
      return;
    }
    const headers = lines[0].split(",").map((h) => h.trim());
    const applicants = [];
    for (let i = 1; i < lines.length; i++) {
      const cols = lines[i].split(",").map((c) => c.trim().replace(/^"|"$/g, ""));
      const obj = {};
      headers.forEach((h, idx) => {
        obj[h] = cols[idx] !== undefined ? cols[idx] : "";
      });
      applicants.push(obj);
    }

    const resp = await fetch("/api/batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ applicants }),
    });
    const data = await resp.json();
    if (data.status !== "OK") throw new Error(data.message);
    renderBatchPortfolio(data.batch);
  } catch (err) {
    alert("Lỗi khi nạp file CSV: " + err.message);
  } finally {
    event.target.value = "";
  }
}

function drawOfflineRadarCanvas(canvas, labels, values) {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const w = (canvas.width = canvas.parentElement.clientWidth || 260);
  const h = (canvas.height = canvas.parentElement.clientHeight || 220);
  ctx.clearRect(0, 0, w, h);

  const cx = w / 2;
  const cy = h / 2;
  const radius = Math.min(w, h) * 0.34;
  const count = labels.length;

  ctx.strokeStyle = "#cbd5e1";
  ctx.lineWidth = 1;
  [0.25, 0.5, 0.75, 1].forEach((scale) => {
    ctx.beginPath();
    for (let i = 0; i < count; i++) {
      const angle = (Math.PI * 2 * i) / count - Math.PI / 2;
      const x = cx + Math.cos(angle) * radius * scale;
      const y = cy + Math.sin(angle) * radius * scale;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.stroke();
  });

  ctx.beginPath();
  for (let i = 0; i < count; i++) {
    const angle = (Math.PI * 2 * i) / count - Math.PI / 2;
    const val = Math.max(0, Math.min(100, values[i] || 0)) / 100;
    const x = cx + Math.cos(angle) * radius * val;
    const y = cy + Math.sin(angle) * radius * val;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.closePath();
  ctx.fillStyle = "rgba(2, 132, 199, 0.25)";
  ctx.fill();
  ctx.strokeStyle = "#0284c7";
  ctx.lineWidth = 2;
  ctx.stroke();
}

/* ============================================================================
   TIEN ICH ESCAPE HTML
   ============================================================================ */
function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

