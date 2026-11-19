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
            "Đề 08: Công cụ DROOLS (Nhóm Rule-Based: CLIPS • PROLOG • DROOLS)",
            [
                "• Nhóm thực hiện: Nhóm 1",
                "• Bài toán ứng dụng: Hệ thống Hỗ trợ Ra quyết định Thẩm định Tín dụng, Xếp hạng Rủi ro & Định giá Khoản vay Cá nhân (Credit Approval & Loan Pricing DSS)",
                "• Kiến trúc triển khai: Lõi Drools Engine (.drl + Rete/PHREAK + Agenda + TMS) + Đối chứng CLIPS (.clp) & Prolog (.pl) + Web FinTech Dashboard",
                "• Kiểm thử tự động: 22/22 Unit & Integration Tests PASS (100%) | Rule V&V: 5/5 Tiêu chuẩn Đạt 100%",
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
                "• 3 Ưu thế vượt trội của Rule-Based DSS:",
                "  1. Tách biệt hoàn toàn Luật nghiệp vụ (.drl / .csv) khỏi Mã nguồn ứng dụng (Hot-Reload chính sách không cần sửa code).",
                "  2. Suy diễn đa tầng tự động (Multi-stage Chaining) có kiểm soát xung đột chặt chẽ.",
                "  3. Giải thích hộp trắng minh bạch 100% (White-box Explainability & Audit Trail cho Hội đồng Tín dụng).",
            ],
            "Lời dẫn: Slide 2 làm rõ vai trò của Rule-Based DSS trong kiến trúc hệ hỗ trợ ra quyết định hiện đại.",
        ),
        (
            "SLIDE 03 • GIỚI THIỆU NỀN TẢNG APACHE KIE / RED HAT DROOLS",
            "Hệ quản trị Luật Nghiệp vụ Doanh nghiệp (Enterprise BRMS) hàng đầu thế giới",
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
                "• Điểm đặc biệt của đồ án Nhóm 1: Cài đặt tập luật trên cả 3 ngôn ngữ (credit_approval.drl, credit_approval.clp, credit_approval.pl) và kiểm chứng đồng thuận 100% trên cả 15 hồ sơ!",
            ],
            "Lời dẫn: Để đáp ứng trọn vẹn yêu cầu tìm hiểu các công cụ trong nhóm Rule-Based của đề bài, nhóm đã cài đặt đối chứng cả Drools, CLIPS và Prolog.",
        ),
        (
            "SLIDE 05 • KIẾN TRÚC LÕI CỦA BỘ MÁY DROOLS RULE ENGINE",
            "5 Thành phần kiến trúc chuẩn Apache KIE được cài đặt & trực quan hóa",
            [
                "• 1. KieBase (Production Memory): Lưu trữ Declared Types (Applicant, EligibilityPassed), 20 luật .drl + 3 luật Decision Table CSV và đồ thị mạng Rete/PHREAK.",
                "• 2. KieSession (Working Memory): Quản lý vòng đời FactHandle với 4 thao tác chuẩn: insert(), modify(), delete() và insertLogical() (TMS).",
                "• 3. RetePhreakNetwork: Đồ thị 5 lớp nút EntryPointNode -> ObjectTypeNode -> AlphaNode -> BetaNode -> RuleTerminalNode.",
                "• 4. Agenda & ConflictResolver: Quản lý Focus Stack của 4 tầng agenda-group, giải quyết xung đột theo Salience & Activation-Group.",
                "• 5. AgendaEventListener: Ghi nhận toàn bộ hồ sơ truy vết (Cycle, Conflict Set, Fact Diff Before/After, Cancelled Rules, TMS Events).",
            ],
            "Lời dẫn: Toàn bộ 5 thành phần kiến trúc chuẩn của Drools đều được cài đặt tường minh để bóc tách hộp trắng phục vụ trực quan hóa.",
        ),
        (
            "SLIDE 06 • GIẢI PHẪU MẠNG SUY DIỄN RETE / PHREAK TRONG ĐỒ ÁN",
            "Cơ chế Alpha Node Sharing & Phép nối quan hệ BetaNode 2-Fact Join",
            [
                "• Lớp 1 – EntryPointNode & ObjectTypeNode: Phân luồng tự động đối tượng vào OTN_Applicant và OTN_EligibilityPassed.",
                "• Lớp 2 – Alpha Network & Node Sharing: Từ 64 điều kiện lọc đơn trong 23 luật, mạng Rete/PHREAK tự động gom nhóm các điều kiện trùng nhau thành 26 AlphaNode duy nhất -> Tiết kiệm 38 phép đánh giá đơn ở mỗi chu kỳ!",
                "• Lớp 3 – Beta Network (JoinNode): 13 luật ở Tầng 2 và Tầng 3 thực hiện phép nối quan hệ 2-Fact: EligibilityPassed(status=='PASSED') ⋈ Applicant(applicant_id == $elig.applicant_id).",
                "• Lớp 4 – RuleTerminalNode (RTN): Sinh Activation đẩy vào Agenda khi nhánh Alpha và Beta thỏa mãn.",
            ],
            "Lời dẫn: Điểm ăn tiền về mặt học thuật của mạng Rete là Alpha Node Sharing và BetaNode Join 2-Fact giữa EligibilityPassed và Applicant.",
        ),
        (
            "SLIDE 07 • GIẢI QUYẾT XUNG ĐỘT (CONFLICT RESOLUTION) & BẢO TOÀN CHÂN LÝ (TMS)",
            "Cơ chế kiểm soát tất định 100% thứ tự nổ luật và tự động thu hồi Fact suy diễn",
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
            "SLIDE 08 • BÀI TOÁN DSS: THẨM ĐỊNH TÍN DỤNG & ĐỊNH GIÁ KHOẢN VAY CÁ NHÂN",
            "Mô hình hóa Fact trong rules/credit_approval.drl",
            [
                "• Đầu vào (Fact: Applicant): Độ tuổi (age), Thu nhập ròng (monthly_income - triệu/tháng), Thâm niên (employment_years), Điểm tín dụng (credit_score 300–850), Tỷ lệ nợ/thu nhập DTI (%), Số tiền vay (loan_amount), Kỳ hạn (loan_term_months), Giá trị TSĐB (collateral_value), Nợ xấu CIC (cic_bad_debt), Khách hàng VIP (is_vip).",
                "• Fact suy diễn trung gian (Fact: EligibilityPassed): Sinh tự động bởi R04 qua TMS insertLogical.",
                "• Đầu ra Hỗ trợ Ra quyết định:",
                "  - Quyết định: APPROVED | CONDITIONAL_APPROVAL | MANUAL_REVIEW | REJECTED",
                "  - Điểm suy diễn (0–100), Hạng rủi ro (TIER_A/B/C/D), Hạn mức duyệt, Lãi suất (%/năm), Trả góp/tháng & Khuyến nghị định lượng.",
            ],
            "Lời dẫn: Bài toán mô phỏng quy trình thẩm định và định giá khoản vay thực tế tại ngân hàng thương mại.",
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
                "• Cycle 6 [3-pricing-decision]: R13 (sal:50) -> APPROVED, hạn mức 500 triệu (100%), lãi suất VIP 6.8%/năm.",
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
            "Lời dẫn: Kịch bản 4 và Kịch bản 15 là bằng chứng sống động nhất về hiệu quả của Salience và Activation-Group.",
        ),
        (
            "SLIDE 12 • KIỂM ĐỊNH HÌNH THỨC TẬP LUẬT (FORMAL V&V) & BACKWARD GOAL-SEEKING",
            "Đảm bảo tập luật đạt chuẩn Hệ chuyên gia & hỗ trợ Truy vấn Mục tiêu Ngược",
            [
                "• Bộ Kiểm định Tập luật Tự động (RuleBaseVerifier – 5/5 Tiêu chuẩn V&V PASSED 100%):",
                "  1. Redundancy Check: 0 luật dư thừa hoặc trùng chữ ký LHS.",
                "  2. Conflict / Ambivalence Check: 100% luật cạnh tranh được khóa bởi 3 activation-group và salience phân biệt.",
                "  3. Reachability / Dead-Rule Check: 23/23 luật đều có tập dữ liệu kích hoạt thực tế (0 luật chết).",
                "  4. Termination & No-Loop Check: 100% luật có no-loop & lock-on-active, dừng hữu hạn sau 2–8 chu kỳ.",
                "  5. Completeness Check: Độ phủ 100% không gian quyết định trên toàn miền điểm (-∞, +∞).",
                "• Bộ Suy diễn Mục tiêu Ngược (BackwardGoalSeeker): Tự động tìm phương án thay đổi tối thiểu (bổ sung TSĐB, hạ DTI, tăng thu nhập) để nâng hồ sơ lên APPROVED 100% hoặc TIER_A.",
            ],
            "Lời dẫn: Nhóm đã tích hợp thêm bộ kiểm định hình thức V&V 5 tiêu chuẩn và suy diễn mục tiêu ngược Goal-Seeking.",
        ),
        (
            "SLIDE 13 • KIẾN TRÚC WEB FINTECH DSS DASHBOARD (7 PHÂN HỆ TƯƠNG TÁC)",
            "Chạy ngay lập tức với 1 lệnh `python app.py` – Trực quan hóa Hộp trắng 100%",
            [
                "• 1. Thanh 6 Kịch bản Demo 1-Click & Bộ chọn 15 Hồ sơ CSV.",
                "• 2. Executive Decision Card, 6 Gauges Tài chính, Biểu đồ Radar 5 Chiều & Xuất Tờ trình Thẩm định (In / Lưu PDF).",
                "• 3. Sơ đồ Mạng Suy diễn Rete / PHREAK Trực quan kèm Step-by-Step Replay phát sáng từng nút & Minh họa TMS (insertLogical).",
                "• 4. Nhật ký Truy vết Chu kỳ Suy diễn (Cycle Timeline) & Bằng chứng Hủy luật activation-group.",
                "• 5. Phòng Thí nghiệm What-If & Phân tích Độ nhạy (Sensitivity Curve).",
                "• 6. Live DRL Studio (Sửa & biên dịch nóng .drl trên trình duyệt) + Chấm điểm Hàng loạt 15 Hồ sơ CSV.",
                "• 7. Tab Đối sánh Thực nghiệm Drools (.drl) vs CLIPS (.clp) vs Prolog (.pl) + Goal-Seeker + Ma trận Kiểm định V&V.",
            ],
            "Lời dẫn: Giao diện Web Dashboard được thiết kế theo chuẩn FinTech hiện đại với 7 phân hệ tương tác toàn diện.",
        ),
        (
            "SLIDE 14 • KẾT QUẢ THỰC NGHIỆM 15 HỒ SƠ & KIỂM THỬ TỰ ĐỘNG (22/22 PASS)",
            "Đối chiếu khớp 100% giữa Lý thuyết, Truy vết tay và Thực thi trên 3 Bộ máy",
            [
                "• Kết quả Chấm điểm Danh mục 15 Hồ sơ Tín dụng (data/sample_applicants.csv):",
                "  - Phê duyệt tự động (APPROVED): 5 hồ sơ (33.3%) – Lãi suất 6.8% (VIP), 7.5% (Hạng A), 9.2% (Hạng B có TSĐB).",
                "  - Duyệt có điều kiện (CONDITIONAL_APPROVAL): 2 hồ sơ (13.3%) – Cắt giảm 80% hạn mức, lãi suất 10.8%.",
                "  - Chuyển Hội đồng Tín dụng (MANUAL_REVIEW): 3 hồ sơ (20.0%) – Đề xuất hạn mức an toàn 55%, lãi suất 12.5%.",
                "  - Từ chối (REJECTED): 5 hồ sơ (33.3%) – 4 hồ sơ Hard Knock-out Tầng 1 & 1 hồ sơ TIER_D Tầng 3.",
                "• Kiểm thử Tự động (python -m unittest discover -s tests -v): 22/22 Test Cases PASS 100%!",
                "• Kèm thư mục tham chiếu chuẩn Apache KIE Java Maven (java_kie_reference/pom.xml & kmodule.xml).",
            ],
            "Lời dẫn: Toàn bộ 22 test cases tự động đều PASS 100%, đảm bảo không có bất kỳ sai sót kỹ thuật nào.",
        ),
        (
            "SLIDE 15 • KỊCH BẢN DEMO TRỰC TIẾP 5 PHÚT TRÊN WEB DASHBOARD",
            "Trình tự thao tác ghi điểm tuyệt đối trước Hội đồng chấm thi",
            [
                "• Phút 1: Bấm 1-Click Kịch bản 1 (VIP Hạng A - 8 chu kỳ) đối chiếu với Kịch bản 5 (Knock-out CIC dừng sớm - 2 chu kỳ) & Bấm 'In Tờ trình Thẩm định'.",
                "• Phút 2: Chọn Kịch bản 4 (Hồ sơ xung đột Hạng C), bấm '▶ Chạy từng bước (Replay)' trên sơ đồ Rete/PHREAK và bấm nút 'Minh họa TMS (insertLogical)'.",
                "• Phút 3: Xem bảng Nhật ký Truy vết Khu vực 4 để chỉ rõ các luật bị hủy do activation-group (R10, R11 hoặc R03 ở APP015).",
                "• Phút 4: Sang Tab 2 (What-If Simulator) kéo thanh trượt TSĐB nâng hồ sơ APP003 từ CONDITIONAL lên APPROVED 100%.",
                "• Phút 5: Sang Tab 5 bấm 'Chạy Đối sánh 3 Bộ máy (Drools vs CLIPS vs Prolog)', xem Goal-Seeker & Ma trận V&V 5/5 PASSED.",
            ],
            "Lời dẫn: Bây giờ nhóm xin phép chuyển sang màn hình Web Dashboard để thực hiện phần Demo trực tiếp trong 5 phút.",
        ),
        (
            "SLIDE 16 • TỔNG KẾT & THẢO LUẬN / PHẢN BIỆN (Q&A)",
            "Cảm ơn Giảng viên và các bạn đã theo dõi phần trình bày của Nhóm 1!",
            [
                "• Tổng kết đóng góp của Đồ án Đề 08 – Nhóm 1:",
                "  1. Làm chủ sâu sắc kiến trúc Apache KIE / Drools (Rete/PHREAK, Agenda-Group, Activation-Group, Lock-on-Active, TMS insertLogical, Decision Table).",
                "  2. Đặt Drools trong bức tranh toàn cảnh nhóm Rule-Based DSS thông qua cài đặt đối chứng thực nghiệm với NASA CLIPS (.clp) và SWI-Prolog (.pl).",
                "  3. Xây dựng hệ thống DSS Thẩm định & Định giá Tín dụng hoàn chỉnh với Kiểm định hình thức V&V, What-If Simulator và Goal-Seeking.",
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
