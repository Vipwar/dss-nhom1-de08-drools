"""
scripts/generate_office_docs.py
===============================================================================
CONG CU TU DONG XUAT FILE BAO CAO WORD (.DOCX) & SLIDE POWERPOINT (.PPTX)
Do an Cuoi ky Mon He thong Ho tro Ra quyet dinh (DSS) - Nhom 1 - De 08: DROOLS
-------------------------------------------------------------------------------
Tao ra:
1. docs/BAO_CAO_DO_AN_DE_08_DROOLS_NHOM_1.docx
2. docs/SLIDE_THUYET_TRINH_DE_08_DROOLS_NHOM_1.pptx (16 slides 16:9 kem Speaker Notes)
===============================================================================
"""

from __future__ import annotations

import os
import re
from typing import List, Tuple

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

import pptx
from pptx import Presentation
from pptx.dml.color import RGBColor as PptRGB
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches as PptInches, Pt as PptPt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD_REPORT_PATH = os.path.join(BASE_DIR, "docs", "BAO_CAO_DO_AN_DE_08_DROOLS_NHOM_1.md")
DOCX_OUT_PATH = os.path.join(BASE_DIR, "docs", "BAO_CAO_DO_AN_DE_08_DROOLS_NHOM_1.docx")
PPTX_OUT_PATH = os.path.join(BASE_DIR, "docs", "SLIDE_THUYET_TRINH_DE_08_DROOLS_NHOM_1.pptx")


def set_cell_background(cell: Any, fill_hex: str) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    tcPr.append(shd)


def clean_md_inline(text: str) -> str:
    s = text.replace("**", "").replace("`", "")
    s = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", s)
    return s.strip()


def build_word_report() -> None:
    """Chuyen doi toan bo file BAO_CAO_DO_AN_DE_08_DROOLS_NHOM_1.md sang file Word (.docx) chuan hoc thuat."""
    doc = docx.Document()

    # Cau hinh le trang chuan A4
    for section in doc.sections:
        section.top_margin = Inches(0.9)
        section.bottom_margin = Inches(0.9)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(0.9)

    style_normal = doc.styles["Normal"]
    style_normal.font.name = "Arial"
    style_normal.font.size = Pt(11)

    # TRANG BIA (COVER PAGE)
    p_uni = doc.add_paragraph()
    p_uni.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_uni = p_uni.add_run("MÔN HỌC: HỆ THỐNG HỖ TRỢ RA QUYẾT ĐỊNH (DECISION SUPPORT SYSTEMS)\n")
    r_uni.bold = True
    r_uni.font.size = Pt(13)
    r_uni.font.color.rgb = RGBColor(15, 23, 42)

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_t1 = p_title.add_run("\nBÁO CÁO ĐỒ ÁN CUỐI KỲ\n")
    r_t1.bold = True
    r_t1.font.size = Pt(22)
    r_t1.font.color.rgb = RGBColor(2, 132, 199)

    r_t2 = p_title.add_run(
        "ĐỀ TÀI 08: TÌM HIỂU NHÓM CÔNG CỤ RULE-BASED (DROOLS • CLIPS • PROLOG)\n"
        "VÀ XÂY DỰNG HỆ THỐNG HỖ TRỢ RA QUYẾT ĐỊNH THẨM ĐỊNH TÍN DỤNG\n"
        "& ĐỊNH GIÁ KHOẢN VAY CÁ NHÂN\n"
    )
    r_t2.bold = True
    r_t2.font.size = Pt(14)
    r_t2.font.color.rgb = RGBColor(15, 23, 42)

    p_meta = doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_meta = p_meta.add_run(
        "\nNhóm thực hiện: Nhóm 1\n"
        "Đề tài: Đề 08 – DROOLS (Nhóm Rule-Based: CLIPS hay PROLOG hay DROOLS)\n"
        "Kho mã nguồn GitHub: https://github.com/Vipwar/dss-nhom1-de08-drools.git\n"
    )
    r_meta.font.size = Pt(11)
    r_meta.font.color.rgb = RGBColor(71, 85, 105)

    doc.add_page_break()

    with open(MD_REPORT_PATH, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    in_code_block = False
    code_buffer: List[str] = []
    table_buffer: List[List[str]] = []

    def flush_table() -> None:
        nonlocal table_buffer
        if not table_buffer:
            return
        rows = [
            r
            for r in table_buffer
            if not all(re.match(r"^[:\-]+$", cell.strip()) for cell in r if cell.strip())
        ]
        if not rows:
            table_buffer = []
            return
        num_cols = max(len(r) for r in rows)
        tbl = doc.add_table(rows=len(rows), cols=num_cols)
        tbl.style = "Table Grid"
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER

        for r_idx, row_data in enumerate(rows):
            for c_idx in range(num_cols):
                val = clean_md_inline(row_data[c_idx]) if c_idx < len(row_data) else ""
                cell = tbl.cell(r_idx, c_idx)
                cell.text = val
                for p in cell.paragraphs:
                    for run in p.runs:
                        run.font.size = Pt(9.5)
                        if r_idx == 0:
                            run.bold = True
                            run.font.color.rgb = RGBColor(255, 255, 255)
                if r_idx == 0:
                    set_cell_background(cell, "0F172A")
                elif r_idx % 2 == 1:
                    set_cell_background(cell, "F8FAFC")
        doc.add_paragraph()
        table_buffer = []

    for raw_line in lines:
        line = raw_line.rstrip()

        if line.strip().startswith("```"):
            flush_table()
            if not in_code_block:
                in_code_block = True
                code_buffer = []
            else:
                in_code_block = False
                p_code = doc.add_paragraph()
                r_code = p_code.add_run("\n".join(code_buffer))
                r_code.font.name = "Courier New"
                r_code.font.size = Pt(9)
                r_code.font.color.rgb = RGBColor(30, 41, 59)
                code_buffer = []
            continue

        if in_code_block:
            code_buffer.append(line)
            continue

        if line.strip().startswith("|") and line.strip().endswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            table_buffer.append(cells)
            continue
        else:
            flush_table()

        if not line.strip() or line.strip() == "---":
            continue

        if line.startswith("# "):
            h = doc.add_heading(clean_md_inline(line[2:]), level=1)
            for r in h.runs:
                r.font.color.rgb = RGBColor(2, 132, 199)
        elif line.startswith("## "):
            h = doc.add_heading(clean_md_inline(line[3:]), level=1)
            for r in h.runs:
                r.font.color.rgb = RGBColor(15, 23, 42)
        elif line.startswith("### "):
            h = doc.add_heading(clean_md_inline(line[4:]), level=2)
            for r in h.runs:
                r.font.color.rgb = RGBColor(3, 105, 161)
        elif line.startswith("#### "):
            h = doc.add_heading(clean_md_inline(line[5:]), level=3)
        elif line.lstrip().startswith(("- ", "* ")):
            txt = clean_md_inline(line.lstrip()[2:])
            doc.add_paragraph(txt, style="List Bullet")
        elif re.match(r"^\s*\d+\.\s+", line):
            txt = clean_md_inline(re.sub(r"^\s*\d+\.\s+", "", line))
            doc.add_paragraph(txt, style="List Number")
        elif line.lstrip().startswith(">"):
            txt = clean_md_inline(line.lstrip().lstrip(">").strip())
            p_q = doc.add_paragraph()
            r_q = p_q.add_run(txt)
            r_q.italic = True
            r_q.font.color.rgb = RGBColor(3, 105, 161)
        else:
            doc.add_paragraph(clean_md_inline(line))

    flush_table()
    doc.save(DOCX_OUT_PATH)
    print(f"[Office Generator] Da tao file Word: {DOCX_OUT_PATH}")


def build_powerpoint_slides() -> None:
    """Tao file PowerPoint 16 Slides (16:9 Widescreen) kem Speaker Notes chi tiet."""
    prs = Presentation()
    prs.slide_width = PptInches(13.333)
    prs.slide_height = PptInches(7.5)
    blank_layout = prs.slide_layouts[6]

    slides_data: List[Tuple[str, str, List[str], str]] = [
        (
            "SLIDE 01 • ĐỒ ÁN CUỐI KỲ MÔN HỆ THỐNG HỖ TRỢ RA QUYẾT ĐỊNH (DSS)",
            "Đề 08: Công cụ DROOLS (Drools • CLIPS • Prolog • Basel III)",
            [
                "• Nhóm thực hiện: Nhóm 1",
                "• Bài toán ứng dụng: Hệ thống Hỗ trợ Ra quyết định Thẩm định Tín dụng, Xếp hạng Rủi ro, Định lượng Basel III & Định giá Khoản vay Cá nhân",
                "• Kiến trúc triển khai: Lõi Drools Engine (.drl + Rete/PHREAK + SafeASTEvaluator + Alpha Cache + Agenda + TMS) + Đối chứng CLIPS & Prolog",
                "• Kiểm thử tự động: 28/28 Unit, Security, Basel III & Fuzzing Tests PASS (100%) | 100/100 Fuzzing Equivalence | Rule V&V: 5/5 Đạt 100%",
                "• Kho mã nguồn GitHub: https://github.com/Vipwar/dss-nhom1-de08-drools",
            ],
            "Lời dẫn: Xin chào Thầy/Cô và các bạn. Hôm nay Nhóm 1 xin trình bày Đồ án cuối kỳ môn Hệ thống Hỗ trợ Ra quyết định với Đề tài 08 – Công cụ Drools thuộc nhóm Rule-Based DSS.",
        ),
        (
            "SLIDE 02 • TỔNG QUAN VỀ HỆ HỖ TRỢ RA QUYẾT ĐỊNH DỰA TRÊN LUẬT (RULE-BASED DSS)",
            "Tại sao Tài chính – Ngân hàng cần Rule-Based DSS thay vì Hard-coded If/Else?",
            [
                "• Phân loại DSS (Turban et al.): Knowledge-driven / Rule-based DSS kết hợp Cơ sở tri thức (Knowledge Base) với Bộ máy suy diễn (Inference Engine).",
                "• Bài toán Thẩm định & Định giá Tín dụng là bài toán bán cấu trúc (Semi-structured): đòi hỏi tuân thủ quy chế cứng (CIC, DTI) kết hợp đánh giá rủi ro đa chiều.",
                "• 3 ưu điểm chính của Rule-Based DSS:",
                "  1. Tách biệt hoàn toàn Luật nghiệp vụ (.drl / .csv) khỏi Mã nguồn ứng dụng (Hot-Reload chính sách không cần sửa code).",
                "  2. Suy diễn đa tầng tự động (Multi-stage Chaining) có kiểm soát xung đột chặt chẽ.",
                "  3. Giải thích hộp trắng minh bạch 100% (White-box Explainability & Audit Trail cho Hội đồng Tín dụng).",
            ],
            "Lời dẫn: Slide 2 làm rõ vai trò của Rule-Based DSS trong kiến trúc hệ hỗ trợ ra quyết định hiện đại.",
        ),
        (
            "SLIDE 03 • GIỚI THIỆU NỀN TẢNG APACHE KIE / RED HAT DROOLS",
            "Hệ quản trị Luật Nghiệp vụ Doanh nghiệp (Enterprise BRMS) phổ biến trong doanh nghiệp",
            [
                "• Nguồn gốc: Khởi đầu từ JBoss Rules / Red Hat Decision Manager, hiện thuộc hệ sinh thái mã nguồn mở Apache KIE (Knowledge Is Everything).",
                "• 4 Trụ cột công nghệ tạo nên sức mạnh của Drools:",
                "  1. Thuật toán so khớp mẫu PHREAK (tiến hóa từ Rete & ReteOO): Đánh giá lười theo tầng (Lazy Segment Evaluation) & Chia sẻ nút (Alpha Node Sharing).",
                "  2. Ngôn ngữ khai báo chuẩn Drools Rule Language (.drl) kết hợp Bảng quyết định (Decision Tables .csv / .xlsx).",
                "  3. Điều phối luồng suy diễn chuyên sâu: agenda-group, activation-group, salience, no-loop, lock-on-active.",
                "  4. Hệ thống Bảo toàn Chân lý (Truth Maintenance System – TMS) qua cơ chế insertLogical() tự động rút lại sự kiện suy diễn.",
            ],
            "Lời dẫn: Drools không chỉ là một thư viện kiểm tra điều kiện mà là một hệ sinh thái BRMS hoàn chỉnh với thuật toán PHREAK và TMS.",
        ),
        (
            "SLIDE 04 • ĐỐI SÁNH 3 CÔNG CỤ TRONG NHÓM RULE-BASED: DROOLS vs CLIPS vs PROLOG",
            "Phân tích lý thuyết & Thực nghiệm đối chứng cả 3 công cụ theo đúng yêu cầu đề bài",
            [
                "• 1. DROOLS (.drl – Red Hat/Apache KIE): Suy diễn tiến (Forward Chaining), thuật toán PHREAK, dữ liệu Hướng đối tượng (OOP Fact), hỗ trợ agenda-group, activation-group, TMS và Decision Table. Tối ưu cho DSS Tài chính – Ngân hàng.",
                "• 2. CLIPS (.clp – NASA 1985): Suy diễn tiến (Forward Chaining), thuật toán Rete cổ điển (Eager Evaluation), biểu diễn deftemplate/defrule dạng S-expression kiểu Lisp. Phù hợp hệ chuyên gia kỹ thuật.",
                "• 3. PROLOG (.pl – Logic Programming 1972): Suy diễn lùi hướng mục tiêu (Goal-driven Backward Chaining), hợp giải SLD Resolution, Unification & Backtracking kèm toán tử cắt (!). Phù hợp chứng minh mệnh đề logic.",
                "• Điểm đặc biệt của đồ án Nhóm 1: Cài đặt tập luật trên cả 3 ngôn ngữ (.drl, .clp, .pl) và chứng minh hội tụ 100% trên 15 hồ sơ mẫu + 100 hồ sơ Fuzzing ngẫu nhiên!",
            ],
            "Lời dẫn: Để đáp ứng trọn vẹn yêu cầu tìm hiểu các công cụ trong nhóm Rule-Based của đề bài, nhóm đã cài đặt đối chứng cả Drools, CLIPS và Prolog.",
        ),
        (
            "SLIDE 05 • KIẾN TRÚC LÕI CỦA BỘ MÁY DROOLS V3 ULTIMATE & BẢO MẬT SAFE AST",
            "Chuẩn Apache KIE tích hợp SafeASTEvaluator Sandbox & StrictInputSanitizer",
            [
                "• 1. KieBase & SafeASTEvaluator: Biên dịch .drl + Decision Table CSV qua trình thông dịch cây cú pháp AST thuần (không dùng eval/compile), chặn chèn mã (Code Injection) trên Live DRL Studio.",
                "• 2. KieSession & StrictInputSanitizer: Quản lý FactHandle (insert, modify, delete, insertLogical) kèm bộ chuẩn hóa biên tránh lỗi chia cho 0.",
                "• 3. RetePhreakNetwork: Đồ thị 5 lớp nút EntryPointNode -> ObjectTypeNode -> AlphaNode -> BetaNode -> RuleTerminalNode.",
                "• 4. Agenda & ConflictResolver: Quản lý Focus Stack của 4 tầng agenda-group, giải quyết xung đột theo Salience & Activation-Group.",
                "• 5. AgendaEventListener: Ghi nhận toàn bộ hồ sơ truy vết (Cycle, Conflict Set, Fact Diff Before/After, Cancelled Rules, TMS Events).",
            ],
            "Lời dẫn: Phiên bản bổ sung SafeASTEvaluator ngăn chèn mã trên mục sửa luật DRL và StrictInputSanitizer chống chia cho 0.",
        ),
        (
            "SLIDE 06 • GIẢI PHẪU MẠNG RETE / PHREAK & INCREMENTAL ALPHA MEMORY CACHE",
            "Alpha Node Sharing, Bộ nhớ đệm theo (handle_id, fact.recency) & BetaNode 2-Fact Join",
            [
                "• Lớp 1 – EntryPointNode & ObjectTypeNode: Phân luồng tự động đối tượng vào OTN_Applicant và OTN_EligibilityPassed.",
                "• Lớp 2 – Alpha Network & Node Sharing: Gom các điều kiện đơn trùng nhau giữa 23 luật thành các AlphaNode dùng chung duy nhất.",
                "• Bổ sung: Incremental Alpha Memory Cache: Lưu đệm kết quả lọc theo cặp khóa (handle_id, fact.recency) trên từng AlphaNode, tránh tính lại biểu thức cho các Fact không đổi sau lệnh modify(), kèm thống kê cache_hits trực tiếp!",
                "• Lớp 3 & 4 – Beta Network (13 nút Join 2-Fact EligibilityPassed ⋈ Applicant) -> RuleTerminalNode sinh Activation vào Agenda.",
            ],
            "Lời dẫn: Bên cạnh Alpha Node Sharing, nhóm cài đặt thêm Incremental Alpha Memory Cache theo (handle_id, fact.recency) giúp giảm số lần tính lại điều kiện.",
        ),
        (
            "SLIDE 07 • GIẢI QUYẾT XUNG ĐỘT (CONFLICT RESOLUTION) & BẢO TOÀN CHÂN LÝ (TMS)",
            "Kiểm soát thứ tự kích hoạt luật và tự động thu hồi Fact suy diễn",
            [
                "• Chiến lược Giải quyết Xung đột (Conflict Resolution Strategy) theo 5 cấp:",
                "  (1) agenda-group trên đỉnh Focus Stack -> (2) salience từ cao xuống thấp -> (3) activation-group hủy tự động các luật cùng nhóm -> (4) no-loop & lock-on-active chống lặp vô hạn -> (5) recency.",
                "• Tại sao Tầng 2 phải dùng lock-on-active true? Vì R05, R06, R07, R08 cùng modify($app.composite_score); lock-on-active ngăn các luật chấm điểm kích hoạt chéo lặp lại vô hạn.",
                "• Hệ thống Bảo toàn Chân lý (Truth Maintenance System – insertLogical):",
                "  Luật R04 sinh Fact trung gian EligibilityPassed qua insertLogical(). Nếu Fact gốc Applicant bị cập nhật làm điều kiện R04 sai (ví dụ phát hiện nợ xấu CIC), TMS tự động rút lại (Auto-Retract) EligibilityPassed!",
            ],
            "Lời dẫn: Slide này giải thích hai câu hỏi phản biện quan trọng nhất: lock-on-active khác no-loop thế nào và TMS insertLogical hoạt động ra sao.",
        ),
        (
            "SLIDE 08 • BÀI TOÁN DSS: THẨM ĐỊNH TÍN DỤNG, ĐỊNH GIÁ & QUẢN TRỊ RỦI RO BASEL III",
            "Kết hợp Suy diễn Luật Drools với Chỉ số Ngân hàng Chuẩn Quốc tế Basel III",
            [
                "• Đầu vào (Fact: Applicant): Độ tuổi, Thu nhập ròng, Thâm niên, Credit Score (300–850), DTI (%), Số tiền vay, Kỳ hạn, Giá trị TSĐB, Nợ xấu CIC, Khách hàng VIP.",
                "• Đầu ra Quyết định Drools: APPROVED | CONDITIONAL_APPROVAL | MANUAL_REVIEW | REJECTED, Hạng rủi ro (TIER_A..D), Hạn mức & Lãi suất.",
                "• Mô hình Định lượng Rủi ro Tín dụng Basel III tích hợp trực tiếp:",
                "  - PD (Probability of Default), LGD (Loss Given Default theo độ bao phủ TSĐB), EAD (= Approved Amount).",
                "  - Expected Loss (EL = PD * LGD * EAD) & RAROC (Risk-Adjusted Return on Capital trên Vốn kinh tế 10.5% RWA).",
            ],
            "Lời dẫn: Không chỉ dừng lại ở nhãn phê duyệt, hệ thống tính toán đầy đủ bộ chỉ số rủi ro chuẩn ngân hàng Basel III gồm PD, LGD, EAD, EL và RAROC.",
        ),
        (
            "SLIDE 09 • PIPELINE SUY DIỄN TIẾN 4 TẦNG (20 LUẬT .DRL + 3 LUẬT DECISION TABLE)",
            "Thiết kế phân tầng chuẩn mực qua 4 agenda-group nối tiếp",
            [
                "• Tầng 1 – agenda-group '1-eligibility' (Salience 90..100): R01 (Tuổi ngoài 18–65), R02 (Nợ xấu CIC), R03 (DTI > 65%) -> Hard Knock-out dừng sớm. R04 -> Cấp 40 điểm nền tảng & insertLogical(EligibilityPassed).",
                "• Tầng 2 – agenda-group '2-risk-scoring' (Salience 60..80): R05 (+20đ thu nhập >=30tr & thâm niên >=2 năm), R06 (+25đ Credit >=750 & DTI <=35%), R07 (+15đ TSĐB >=120% & secured_loan=true), R08 (-15đ cảnh báo rủi ro). Phân hạng độc quyền R09..R12 (TIER_A >=80, TIER_B 60..79, TIER_C 40..59, TIER_D <40).",
                "• Tầng 3 – agenda-group '3-pricing-decision' (Salience 30..50): R13 (TIER_A: Duyệt 100%, LS 6.8% VIP / 7.5% chuẩn), R14 (TIER_B có TSĐB: Duyệt 100%, LS 9.2%), R15 (TIER_B tín chấp: Duyệt có ĐK 80%, LS 10.8%), R16 (TIER_C: Thẩm định 55%, LS 12.5%), R17 (TIER_D: Từ chối).",
                "• Tầng 4 – agenda-group '4-dss-explanation' (Salience 10..20): R18 (Khoản vay >=500tr cần định giá độc lập), R19 (Lộ trình nâng hạng), R20 (Khắc phục từ chối), DT01–DT03 (Decision Table CSV).",
            ],
            "Lời dẫn: Tập luật gồm 23 luật chia làm 4 tầng agenda-group rõ ràng từ sàng lọc, chấm điểm, định giá đến giải thích DSS.",
        ),
        (
            "SLIDE 10 • TRUY VẾT SUY DIỄN BẰNG TAY – KỊCH BẢN 1 (KHÁCH HÀNG VIP HẠNG A)",
            "Hồ sơ APP001 (Nguyễn Minh Quân, 38t, VIP): Vay 500 triệu, TSĐB 750 triệu, DTI 22%",
            [
                "• Cycle 1 [1-eligibility]: R04 (sal:90) kích hoạt -> modify(eligible=true, composite_score=40) & insertLogical(EligibilityPassed).",
                "• Cycle 2 [2-risk-scoring]: R05 (sal:80) kích hoạt -> composite_score = 40 + 20 = 60 (khóa bởi lock-on-active).",
                "• Cycle 3 [2-risk-scoring]: R06 (sal:78) kích hoạt -> composite_score = 60 + 25 = 85.",
                "• Cycle 4 [2-risk-scoring]: R07 (sal:75) kích hoạt -> composite_score = 85 + 15 = 100, secured_loan = true.",
                "• Cycle 5 [2-risk-scoring]: Conflict Set có [R09(68), R10(66), R11(64)]. R09 chiến thắng -> gán TIER_A và HỦY TỰ ĐỘNG R10, R11!",
                "• Cycle 6 [3-pricing-decision]: R13 (sal:50) -> APPROVED, EAD = 500tr (100%), LS 6.8%, PD 0.55%, LGD 10%, EL 0.28tr, RAROC 55.65%.",
                "• Cycle 7 & 8 [4-dss-explanation]: R18 (yêu cầu định giá độc lập do vay >=500tr) & DT01 (ưu đãi VIP từ Decision Table).",
            ],
            "Lời dẫn: Bảng truy vết bằng tay từng chu kỳ khớp 100% với nhật ký AgendaEventListener trên máy.",
        ),
        (
            "SLIDE 11 • TRUY VẾT BẰNG TAY – KỊCH BẢN 4 (XUNG ĐỘT) & KỊCH BẢN 5/15 (KNOCK-OUT)",
            "Minh họa sự giằng co điểm số và cơ chế cắt nhánh sớm (Short-Circuiting)",
            [
                "• Kịch bản 4 (APP004 – Phạm Quốc Bảo: Thu nhập cao 32tr nhưng DTI 52% cao):",
                "  - Cycle 1: R04 cấp 40đ -> Cycle 2: R05 cộng +20đ lên 60đ (tạm chạm ngưỡng Hạng B!).",
                "  - Cycle 3: R08 (sal:72 > R10 sal:66) chạy trước, trừ -15đ kéo điểm xuống 45đ -> R10 biến mất khỏi Conflict Set!",
                "  - Cycle 4..7: R11 gán TIER_C -> R16 chuyển Hội đồng Tín dụng (MANUAL_REVIEW, hạn mức an toàn 55% = 137.5tr, LS 12.5%) -> R19 & DT03.",
                "• Kịch bản 5 (APP005) & Kịch bản 15 (APP015 – Vi phạm kép CIC + DTI 74%):",
                "  - Ở APP015, cả R02(sal:98) và R03(sal:95) cùng vào Conflict Set; R02 thắng và hủy R03 nhờ activation-group 'hard-knockout'.",
                "  - Không sinh EligibilityPassed -> Cắt nhánh hoàn toàn 13 luật Tầng 2 & Tầng 3, nhảy thẳng sang R20 (chỉ tốn 2 chu kỳ!).",
            ],
            "Lời dẫn: Kịch bản 4 và Kịch bản 15 là ví dụ minh họa rõ về hiệu quả của Salience và Activation-Group.",
        ),
        (
            "SLIDE 12 • KIỂM ĐỊNH TẬP LUẬT (FORMAL V&V), GOAL-SEEKING & STRESS-TESTING BASEL III",
            "Kiểm tra tập luật, suy diễn ngược và stress test danh mục",
            [
                "• Bộ Kiểm định Tập luật Tự động (RuleBaseVerifier – 5/5 Tiêu chuẩn V&V PASSED 100%):",
                "  Redundancy Check, Conflict Control, Reachability (23/23 luật), Termination Safety & Decision Space Completeness.",
                "• Bộ Suy diễn Mục tiêu Ngược (BackwardGoalSeeker): Tìm phương án thay đổi tối thiểu đã kiểm chứng để nâng hồ sơ lên APPROVED 100% / TIER_A.",
                "• Mô phỏng Stress-Test Danh mục Vĩ mô Basel III (POST /api/stress-test):",
                "  - Giả lập cú sốc đồng thời: Sụt giảm thu nhập (-20%), Sụt giảm giá trị TSĐB (-25%), Tăng nghĩa vụ nợ DTI (+12 điểm %).",
                "  - Xuất trực tiếp Ma trận Dịch chuyển Hạng Rủi ro 4x4 (Risk Migration Matrix TIER_A..TIER_D) và đo lường mức tăng Expected Loss.",
            ],
            "Lời dẫn: Hệ thống tích hợp kiểm định V&V 5 tiêu chuẩn, suy diễn mục tiêu ngược và mô phỏng Stress-Test danh mục theo cú sốc vĩ mô chuẩn Basel III.",
        ),
        (
            "SLIDE 13 • KIẾN TRÚC WEB FINTECH DSS DASHBOARD V3 ULTIMATE",
            "Chạy ngay lập tức với 1 lệnh `python app.py` – Trực quan hóa Hộp trắng & Chuẩn RFC 4180",
            [
                "• 1. Thanh 6 Kịch bản Demo 1-Click & Bộ chọn 15 Hồ sơ CSV.",
                "• 2. Executive Decision Card, Dải chỉ số Basel III (PD, LGD, Expected Loss, RAROC), Radar 5D & Xuất Tờ trình Thẩm định PDF.",
                "• 3. Sơ đồ Mạng Suy diễn Rete / PHREAK kèm thống kê Incremental Alpha Cache Hits, Step-by-Step Replay & Minh họa TMS.",
                "• 4. Nhật ký Truy vết Chu kỳ Suy diễn (Cycle Timeline) & Bằng chứng Hủy luật activation-group.",
                "• 5. Phòng Thí nghiệm What-If & Phân tích Độ nhạy (Sensitivity Curve).",
                "• 6. Chấm điểm Hàng loạt (Trình đọc CSV chuẩn RFC 4180), Khung Basel III Stress-Testing & Live DRL Studio (SafeAST Sandbox).",
                "• 7. Tab Đối sánh Thực nghiệm Drools (.drl) vs CLIPS (.clp) vs Prolog (.pl) + Goal-Seeker + Ma trận Kiểm định V&V.",
            ],
            "Lời dẫn: Giao diện Web Dashboard bổ sung dải chỉ số Basel III, khung Stress-Testing danh mục và trình đọc CSV chuẩn RFC 4180.",
        ),
        (
            "SLIDE 14 • KẾT QUẢ THỰC NGHIỆM, FUZZING 100 HỒ SƠ & KIỂM THỬ (28/28 PASS 100%)",
            "Đối chiếu kết quả 3 bộ máy và kết quả chạy 28 bài kiểm thử",
            [
                "• Kết quả Chấm điểm Danh mục 15 Hồ sơ Mẫu (data/sample_applicants.csv):",
                "  APPROVED: 5 HS (33.3%) | CONDITIONAL: 2 HS (13.3%) | MANUAL_REVIEW: 3 HS (20.0%) | REJECTED: 5 HS (33.3%).",
                "• Kết quả Kiểm thử Tự động (`python3 -m unittest discover -s tests -v`): Đạt 28/28 Test Cases PASS 100%!",
                "  - test_25: SafeASTEvaluator chặn 100% payload Code Injection & StrictInputSanitizer chống chia cho 0.",
                "  - test_26: Kiểm chứng Incremental Alpha Memory Cache hits theo (handle_id, fact.recency).",
                "  - test_27: Kiểm chứng chỉ số Basel III (PD, LGD, EAD, EL, RAROC) & API POST /api/stress-test.",
                "  - test_28: Property-Based Fuzzing 100 hồ sơ ngẫu nhiên -> Drools, CLIPS và Prolog khớp quyết định 100/100 (100%)!",
            ],
            "Lời dẫn: Toàn bộ 28/28 test cases tự động, bao gồm kiểm thử bảo mật AST và Fuzzing 100 hồ sơ ngẫu nhiên trên 3 bộ máy, đều PASS 100%.",
        ),
        (
            "SLIDE 15 • KỊCH BẢN DEMO TRỰC TIẾP 5 PHÚT TRÊN WEB DASHBOARD",
            "Gợi ý trình tự thao tác khi trình bày",
            [
                "• Phút 1: Bấm 1-Click Kịch bản 1 (VIP Hạng A) xem quyết định + chỉ số Basel III (PD, LGD, EL, RAROC) đối chiếu Kịch bản 5 (Knock-out CIC).",
                "• Phút 2: Chọn Kịch bản 4 (Xung đột Hạng C), bấm '▶ Chạy từng bước (Replay)' xem Alpha Cache Hits & bấm 'Minh họa TMS (insertLogical)'.",
                "• Phút 3: Sang Tab 2 (What-If Simulator) kéo thanh trượt TSĐB nâng hồ sơ APP003 từ CONDITIONAL lên APPROVED 100%.",
                "• Phút 4: Sang Tab 3 chạy 'Mô phỏng Stress-Test Danh mục Vĩ mô Basel III' xem Ma trận Dịch chuyển Hạng Rủi ro 4x4 & thử Live DRL Studio ở Tab 4.",
                "• Phút 5: Sang Tab 5 bấm 'Chạy Đối sánh 3 Bộ máy (Drools vs CLIPS vs Prolog)', xem Goal-Seeker & Ma trận V&V 5/5 PASSED.",
            ],
            "Lời dẫn: Bây giờ nhóm xin phép chuyển sang màn hình Web Dashboard để thực hiện phần Demo trực tiếp trong 5 phút.",
        ),
        (
            "SLIDE 16 • TỔNG KẾT & THẢO LUẬN / PHẢN BIỆN (Q&A)",
            "Cảm ơn Giảng viên và các bạn đã theo dõi phần trình bày của Nhóm 1!",
            [
                "• Tổng kết đóng góp của Đồ án Đề 08 – Nhóm 1:",
                "  1. Làm chủ kiến trúc Apache KIE / Drools (Rete/PHREAK, Incremental Alpha Cache, SafeASTEvaluator, Agenda-Group, Activation-Group, TMS).",
                "  2. Chứng minh tương đương 100% giữa Drools (.drl), NASA CLIPS (.clp) và SWI-Prolog (.pl) trên cả 15 hồ sơ mẫu và 100 hồ sơ Fuzzing.",
                "  3. Tích hợp trọn vẹn mô hình định lượng rủi ro ngân hàng Basel III (PD, LGD, EAD, EL, RAROC) & Stress-Testing danh mục vĩ mô (28/28 Tests PASS).",
                "• Nhóm 1 xin trân trọng lắng nghe các câu hỏi phản biện và góp ý từ Thầy/Cô!",
            ],
            "Lời dẫn: Nhóm 1 xin chân thành cảm ơn Thầy/Cô và rất mong nhận được các câu hỏi phản biện từ Hội đồng.",
        ),
    ]

    for idx, (title, subtitle, bullets, notes) in enumerate(slides_data, start=1):
        slide = prs.slides.add_slide(blank_layout)

        # Background
        bg_shape = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, PptInches(0), PptInches(0), PptInches(13.333), PptInches(7.5)
        )
        bg_shape.fill.solid()
        bg_shape.fill.fore_color.rgb = PptRGB(244, 247, 251)
        bg_shape.line.fill.background()

        # Header Navy Banner
        header_shape = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, PptInches(0), PptInches(0), PptInches(13.333), PptInches(1.35)
        )
        header_shape.fill.solid()
        header_shape.fill.fore_color.rgb = PptRGB(15, 23, 42)
        header_shape.line.fill.background()

        tf_h = header_shape.text_frame
        tf_h.word_wrap = True
        p_h1 = tf_h.paragraphs[0]
        p_h1.text = title
        p_h1.font.size = PptPt(21)
        p_h1.font.bold = True
        p_h1.font.color.rgb = PptRGB(255, 255, 255)

        p_h2 = tf_h.add_paragraph()
        p_h2.text = subtitle
        p_h2.font.size = PptPt(13)
        p_h2.font.color.rgb = PptRGB(56, 189, 248)

        # Content White Card
        card_shape = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            PptInches(0.55),
            PptInches(1.65),
            PptInches(12.23),
            PptInches(5.15),
        )
        card_shape.fill.solid()
        card_shape.fill.fore_color.rgb = PptRGB(255, 255, 255)
        card_shape.line.color.rgb = PptRGB(203, 213, 225)
        card_shape.line.width = PptPt(1.5)

        tf_c = card_shape.text_frame
        tf_c.word_wrap = True
        tf_c.margin_left = PptInches(0.35)
        tf_c.margin_right = PptInches(0.35)
        tf_c.margin_top = PptInches(0.28)

        for b_idx, b_text in enumerate(bullets):
            p = tf_c.paragraphs[0] if b_idx == 0 else tf_c.add_paragraph()
            p.text = b_text
            p.space_after = PptPt(10)
            is_sub = b_text.startswith("  ")
            p.font.size = PptPt(14 if is_sub else 15.5)
            p.font.bold = not is_sub and (":" in b_text[:35])
            p.font.color.rgb = PptRGB(51, 65, 85) if is_sub else PptRGB(15, 23, 42)

        # Footer Bar
        footer_box = slide.shapes.add_textbox(
            PptInches(0.55), PptInches(6.92), PptInches(12.23), PptInches(0.4)
        )
        tf_f = footer_box.text_frame
        p_f = tf_f.paragraphs[0]
        p_f.text = f"Đồ án Cuối kỳ Hệ thống Hỗ trợ Ra quyết định (DSS) • Nhóm 1 • Đề 08: DROOLS  |  Trang {idx}/16"
        p_f.font.size = PptPt(10.5)
        p_f.font.color.rgb = PptRGB(100, 116, 139)
        p_f.alignment = PP_ALIGN.RIGHT

        # Speaker Notes
        notes_slide = slide.notes_slide
        notes_slide.notes_text_frame.text = notes

    prs.save(PPTX_OUT_PATH)
    print(f"[Office Generator] Da tao file PowerPoint 16 Slides: {PPTX_OUT_PATH}")


if __name__ == "__main__":
    build_word_report()
    build_powerpoint_slides()
