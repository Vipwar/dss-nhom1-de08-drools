# BỘ SLIDE THUYẾT TRÌNH, KỊCH BẢN DEMO 5 PHÚT & CÂU HỎI PHẢN BIỆN BẢO VỆ ĐỒ ÁN

- **Môn học:** Hệ thống Hỗ trợ Ra quyết định (Decision Support Systems - DSS)
- **Đề tài:** Đề 08 – DROOLS (Thuộc Nhóm Rule-based: `CLIPS` hay `PROLOG` hay `DROOLS`)
- **Nhóm thực hiện:** Nhóm 1
- **Bài toán ứng dụng:** Hệ thống Hỗ trợ Ra quyết định Thẩm định Tín dụng, Xếp hạng Rủi ro & Định giá Khoản vay Cá nhân (*Credit Approval & Loan Pricing DSS*)

---

## PHẦN 1: NỘI DUNG CHI TIẾT 15 SLIDE THUYẾT TRÌNH (NHÓM 1)

### SLIDE 1: Trang Bìa (Title Slide)
- **Tiêu đề chính:** ĐỒ ÁN CUỐI KỲ MÔN HỆ THỐNG HỖ TRỢ RA QUYẾT ĐỊNH (DSS)
- **Chủ đề:** ĐỀ 08 – CÔNG CỤ **DROOLS** (NHÓM RULE-BASED DSS)
- **Ứng dụng:** Hệ thống Hỗ trợ Ra quyết định Thẩm định Tín dụng, Xếp hạng Rủi ro & Định giá Khoản vay Cá nhân
- **Đơn vị thực hiện:** Nhóm 1
- **Điểm nhấn trên Slide:** Logo Apache KIE / Drools, sơ đồ rút gọn `DRL Rules -> Rete/PHREAK -> Executive Credit Decision`.

---

### SLIDE 2: Bối cảnh & Vai trò của Rule-Based DSS trong Tài chính – Ngân hàng
- **Vấn đề thực tế:**
  - Quyết định phê duyệt tín dụng cá nhân là bài toán **bán cấu trúc (Semi-structured)**: vừa có các quy định loại trừ cứng (CIC, độ tuổi, trần DTI), vừa có sự đánh đổi đa tiêu chí (thu nhập, điểm tín dụng, tài sản đảm bảo, lãi suất bù đắp rủi ro).
  - Nếu viết cứng bằng hàng trăm câu lệnh `if/else` lồng nhau trong code ứng dụng: khó bảo trì khi ngân hàng đổi chính sách lãi suất, không thể giải thích minh bạch cho hội đồng thẩm định.
- **Giải pháp Rule-Based DSS:**
  - Tách biệt hoàn toàn **Cơ sở tri thức (Luật `.drl` & Bảng quyết định `.csv`)** khỏi **Bộ máy suy diễn (Inference Engine)** và **Giao diện hỗ trợ quyết định**.

---

### SLIDE 3: Giới thiệu Công cụ Drools (Apache KIE / Red Hat Decision Manager)
- **Drools là gì?**
  - Hệ quản trị luật nghiệp vụ (**Enterprise BRMS**) mã nguồn mở hàng đầu thuộc hệ sinh thái **Apache KIE** và là lõi của **Red Hat Decision Manager**.
- **4 Đặc trưng cốt lõi của Drools:**
  1. **Suy diễn tiến hướng dữ liệu (Data-driven Forward Chaining)** với khả năng mở rộng quy mô doanh nghiệp.
  2. **Thuật toán PHREAK** (tiến hóa từ **Rete** và **ReteOO**) tối ưu hóa so khớp mẫu qua cơ chế chia sẻ nút (`Node Sharing`) và đánh giá lười theo tầng (`Lazy Segment Evaluation`).
  3. **Cú pháp khai báo chuẩn `Drools Rule Language (.drl)`** và hỗ trợ trực tiếp **Bảng quyết định (`Decision Tables`)**.
  4. **Hệ thống Bảo toàn Chân lý (`Truth Maintenance System - TMS`)** qua cơ chế `insertLogical()`.

---

### SLIDE 4: So sánh Chuyên sâu các Công cụ Cùng Nhóm: Drools vs CLIPS vs Prolog
| Tiêu chí | **DROOLS** | **CLIPS** | **PROLOG** |
| :--- | :--- | :--- | :--- |
| **Hướng suy diễn chính** | **Forward Chaining** (Suy diễn tiến) | **Forward Chaining** (Suy diễn tiến) | **Backward Chaining** (Suy diễn lùi) |
| **Thuật toán lõi** | **PHREAK** (ReteOO cải tiến, Lazy) | **Classic Rete** (Eager Evaluation) | **SLD Resolution** & Backtracking |
| **Mô hình dữ liệu (Fact)** | Hướng đối tượng (`Applicant(age >= 18)`) | Deftemplate S-expression kiểu Lisp | Vị từ logic bậc nhất (`applicant(id, 38)`) |
| **Điều phối Pipeline** | `agenda-group`, `activation-group`, `lock-on-active` | `defmodule`, `salience` | Thứ tự mệnh đề & toán tử cắt `!` (`Cut`) |
| **Hỗ trợ Decision Table** | **Nguyên bản (`.csv`, `.xlsx`, DMN)** | Không hỗ trợ nguyên bản | Không hỗ trợ nguyên bản |
| **Thế mạnh ứng dụng** | **DSS Tài chính, Ngân hàng, Bảo hiểm** | Hệ chuyên gia kỹ thuật / chẩn đoán | Suy luận logic học thuật, ràng buộc |

---

### SLIDE 5: Kiến trúc Lõi của Drools Rule Engine
- **5 Thành phần kiến trúc chuẩn được triển khai trong đồ án:**
  1. **`KieBase` (Production Memory):** Lưu trữ các kiểu dữ liệu `declare`, 20 luật `.drl` + 3 luật Decision Table và đồ thị mạng `RetePhreakNetwork`.
  2. **`KieSession` (Working Memory):** Quản lý các đối tượng `FactHandle` với các thao tác `insert()`, `modify()`, `delete()` và `insertLogical()`.
  3. **`RetePhreakNetwork`:** Mạng nút suy diễn `EntryPointNode -> ObjectTypeNode -> AlphaNode -> BetaNode -> RuleTerminalNode`.
  4. **`Agenda` & `ConflictResolver`:** Quản lý ngăn xếp `agenda-group`, sắp xếp theo `salience`, hủy xung đột qua `activation-group`.
  5. **`AgendaEventListener`:** Ghi nhận toàn bộ hồ sơ truy vết (Audit Trail) ở từng chu kỳ suy diễn.

---

### SLIDE 6: Giải phẫu Mạng Suy diễn Rete / PHREAK trong Đồ án
- **Cấu trúc 5 tầng nút thực tế của hệ thống:**
  - **`EntryPointNode (DEFAULT)`** $\rightarrow$ **2 `ObjectTypeNode`**: `OTN_Applicant` và `OTN_EligibilityPassed`.
  - **26 `AlphaNode` (với cơ chế *Alpha Node Sharing*):** Từ 64 điều kiện đơn trong 23 luật, mạng gom nhóm các điều kiện trùng nhau (như `eligible == true`, `status == "PASSED"`, `age >= 18 && age <= 65`), **tiết kiệm 38 nút lọc đơn dư thừa**.
  - **23 `BetaNode` (trong đó có 13 nút Join 2-Fact):** Thực hiện phép nối quan hệ `EligibilityPassed` $\bowtie$ `Applicant(applicant_id == $elig.applicant_id)`.
  - **23 `RuleTerminalNode`:** Sinh `Activation` đẩy vào `Agenda`.

---

### SLIDE 7: Cơ chế Giải quyết Xung đột (`Conflict Resolution`) & Bảo toàn Chân lý (`TMS`)
- **Thứ tự Giải quyết Xung đột trên `Agenda`:**
  1. **`agenda-group` focus:** Chỉ các luật thuộc tầng đang nằm trên đỉnh ngăn xếp mới được xét.
  2. **`salience`:** Luật có độ ưu tiên cao hơn chạy trước (từ `100` xuống `12`).
  3. **`activation-group`:** Nhóm loại trừ lẫn nhau (XOR) – khi luật có `salience` cao nhất trong nhóm kích hoạt, tất cả các luật còn lại cùng nhóm bị **hủy kích hoạt tự động (`CANCELLED`)**.
  4. **`no-loop` & `lock-on-active`:** Ngăn vòng lặp vô hạn khi nhiều luật cùng tầng gọi `modify($app)` để cộng/trừ điểm.
- **Truth Maintenance System (`insertLogical`):**
  - Luật `R04` dùng `insertLogical(new EligibilityPassed(...))`. Nếu dữ liệu gốc `Applicant` bị sửa làm điều kiện của `R04` sai, TMS **tự động rút lại (`Auto-Retract`)** `EligibilityPassed`!

---

### SLIDE 8: Phát biểu Bài toán DSS & Mô hình Hóa Fact (`rules/credit_approval.drl`)
- **Bài toán:** Thẩm định Tín dụng, Xếp hạng Rủi ro & Định giá Khoản vay Cá nhân.
- **Đầu vào (`Fact: Applicant`):** Tuổi, Thu nhập ròng (triệu/tháng), Thâm niên (năm), Điểm tín dụng nội bộ (300–850), Tỷ lệ nợ trên thu nhập `DTI (%)`, Số tiền vay, Kỳ hạn vay, Giá trị Tài sản đảm bảo (TSĐB), Lịch sử nợ xấu CIC, Cờ khách hàng VIP.
- **Fact Trung gian suy diễn (`Fact: EligibilityPassed`):** Sinh tự động qua `insertLogical` khi hồ sơ vượt qua Tầng 1.
- **Đầu ra Hỗ trợ Ra quyết định:**
  - Quyết định: `APPROVED` | `CONDITIONAL_APPROVAL` | `MANUAL_REVIEW` | `REJECTED`.
  - Điểm suy diễn tổng hợp (`0–100`), Hạng rủi ro (`TIER_A/B/C/D`), Hạn mức phê duyệt, Lãi suất `%/năm`, Trả góp hàng tháng và Khuyến nghị hành động định lượng.

---

### SLIDE 9: Thiết kế Pipeline Suy diễn Tiến 4 Tầng (20 Luật `.drl` + 3 Luật Decision Table)
- **Tầng 1 – `agenda-group "1-eligibility"` (`salience 90..100`):**
  - `R01` (Tuổi ngoài 18–65), `R02` (Nợ xấu CIC), `R03` (`DTI > 65%`) $\rightarrow$ **Hard Knock-out (`REJECTED`)**, dừng sớm!
  - `R04`: Thỏa điều kiện tiên quyết $\rightarrow$ cấp `40 điểm nền tảng`, gọi `insertLogical(EligibilityPassed)` mở khóa Tầng 2.
- **Tầng 2 – `agenda-group "2-risk-scoring"` (`salience 60..80`):**
  - Chấm điểm (`lock-on-active`): `R05` (+20đ thu nhập & thâm niên), `R06` (+25đ điểm tín dụng & DTI thấp), `R07` (+15đ TSĐB $\ge 120\%$ & gắn `secured_loan=true`), `R08` (-15đ cảnh báo rủi ro).
  - Phân hạng độc quyền (`activation-group "risk-tier-assignment"`): `R09` ($\ge 80\text{đ} \rightarrow$ `TIER_A`), `R10` ($\ge 60\text{đ} \rightarrow$ `TIER_B`), `R11` ($\ge 40\text{đ} \rightarrow$ `TIER_C`), `R12` ($< 40\text{đ} \rightarrow$ `TIER_D`).
- **Tầng 3 – `agenda-group "3-pricing-decision"` (`salience 30..50`, `activation-group "final-decision"`):**
  - `R13` (`TIER_A`: Duyệt 100%, LS 6.8% VIP / 7.5% chuẩn), `R14` (`TIER_B` có TSĐB: Duyệt 100%, LS 9.2%), `R15` (`TIER_B` tín chấp: Duyệt có ĐK 80%, LS 10.8%), `R16` (`TIER_C`: Chuyển thẩm định 55%, LS 12.5%), `R17` (`TIER_D`: Từ chối).
- **Tầng 4 – `agenda-group "4-dss-explanation"` (`salience 10..20`):**
  - `R18` (Kiểm soát khoản vay lớn $\ge 500$ triệu), `R19` (Lộ trình nâng hạng), `R20` (Lộ trình khắc phục từ chối), `DT01–DT03` (Bảng quyết định CSV).

---

### SLIDE 10: Truy vết Suy diễn Bằng tay – Kịch bản 1 (Khách hàng VIP Hạng A)
- **Hồ sơ `APP001` (Nguyễn Minh Quân, 38t, VIP):** Thu nhập 65tr, Thâm niên 8 năm, Credit Score 820, DTI 22%, Vay 500tr, TSĐB 750tr.
- **Diễn biến 8 chu kỳ Forward Chaining:**
  - `Cycle 1` (`1-eligibility`): **`R04`** chạy $\rightarrow$ `eligible=true`, `composite_score=40`, `insertLogical(EligibilityPassed)`.
  - `Cycle 2..4` (`2-risk-scoring`): **`R05`** (+20đ $\rightarrow$ 60) $\rightarrow$ **`R06`** (+25đ $\rightarrow$ 85) $\rightarrow$ **`R07`** (+15đ $\rightarrow$ **100**, `secured_loan=true`).
  - `Cycle 5` (`2-risk-scoring`): Conflict Set có `[R09(sal:68), R10(sal:66), R11(sal:64)]`. **`R09`** thắng, gán `TIER_A` và **hủy tự động `R10`, `R11`**!
  - `Cycle 6` (`3-pricing-decision`): **`R13`** chạy $\rightarrow$ `APPROVED`, hạn mức 500tr (100%), lãi suất VIP `6.8%/năm`.
  - `Cycle 7..8` (`4-dss-explanation`): **`R18`** (yêu cầu định giá độc lập do vay $\ge 500$tr) $\rightarrow$ **`DT01`** (ưu đãi VIP từ Decision Table).

---

### SLIDE 11: Truy vết Suy diễn Bằng tay – Kịch bản 4 (Xung đột Luật) & Kịch bản 5 (Hard Knock-out)
- **Kịch bản 4 (`APP004` – Phạm Quốc Bảo): Minh họa sự giằng co giữa tín hiệu tốt và xấu:**
  - `R04` cấp 40đ $\rightarrow$ `R05` cộng +20đ (lên 60đ – chạm ngưỡng Hạng B) $\rightarrow$ nhưng `R08` phát hiện `DTI = 52%` nằm trong vùng cảnh báo `45%..65%` nên trừ `-15đ` kéo điểm xuống **45đ** $\rightarrow$ `R11` xếp hạng `TIER_C` $\rightarrow$ `R16` chuyển **Hội đồng Tín dụng (`MANUAL_REVIEW`)** với hạn mức an toàn 55% (137.5 triệu).
- **Kịch bản 5 (`APP005` – Đặng Văn Hùng): Minh họa Dừng sớm (Early Stopping):**
  - Có nợ xấu CIC $\rightarrow$ `R02` kích hoạt ở `Cycle 1` $\rightarrow$ Không sinh `EligibilityPassed` $\rightarrow$ Toàn bộ 13 luật ở Tầng 2 và Tầng 3 bị cắt nhánh hoàn toàn $\rightarrow$ Nhảy thẳng tới `R20` ở `Cycle 2` (`R02 -> R20`).

---

### SLIDE 12: Kiến trúc Ứng dụng Demo Web FinTech DSS Dashboard
- **Triển khai 100% tương thích Python chuẩn (`python app.py`):**
  - Tích hợp **`SafeASTEvaluator` Sandbox** (chặn chèn mã (Code Injection) trên Live DRL Studio), **`Incremental Alpha Memory Cache`** theo `(handle_id, fact.recency)` và **`StrictInputSanitizer`** chống chia cho 0.
- **7 Phân hệ tương tác trên Giao diện Single-Page Dashboard:**
  1. Thanh 6 Kịch bản Demo 1-Click & Bộ chọn 15 Hồ sơ CSV.
  2. Executive Decision Card, Chỉ số **Basel III (`PD`, `LGD`, `Expected Loss`, `RAROC`)** & Biểu đồ Radar 5 Chiều.
  3. Sơ đồ Mạng Rete / PHREAK Trực quan kèm `Alpha Cache Hits`, **Step-by-Step Replay** & **Minh họa TMS (`insertLogical`)**.
  4. Bảng Nhật ký Truy vết Chu kỳ Suy diễn & Bằng chứng Hủy luật `activation-group`.
  5. Phòng Thí nghiệm **What-If & Phân tích Độ nhạy (Sensitivity Simulator)**.
  6. **Chấm điểm Danh mục CSV (RFC 4180)** + **Mô phỏng Stress-Test Danh mục Vĩ mô Basel III (`Risk Migration Matrix 4×4`)** + **Live DRL Studio**.
  7. Đối sánh thực nghiệm 3 bộ máy (`Drools` vs `CLIPS` vs `Prolog`), `Backward Goal-Seeker` & `Formal Rule V&V`.

---

### SLIDE 13: Kết quả Thực nghiệm Danh mục 15 Hồ sơ, Stress-Testing Basel III & Kiểm thử 28/28
- **Kết quả chạy Batch 15 Hồ sơ (`data/sample_applicants.csv`) & Stress-Testing Vĩ mô:**
  - `APPROVED`: **5 hồ sơ (33.3%)** | `CONDITIONAL_APPROVAL`: **2 hồ sơ (13.3%)**
  - `MANUAL_REVIEW`: **3 hồ sơ (20.0%)** | `REJECTED`: **5 hồ sơ (33.3%)**
  - Mô phỏng cú sốc vĩ mô (`POST /api/stress-test`) xuất trực tiếp **Ma trận Dịch chuyển Hạng Rủi ro (`Risk Migration Matrix`)** và đo lường biến động `Expected Loss (EL)` & `RAROC`.
- **Kiểm thử Tự động & Fuzzing (`tests/test_drools_engine.py`):**
  - **28/28 Unit, Security, Basel III & Fuzzing Test Cases PASS 100%** (bao gồm kiểm thử bảo mật `SafeASTEvaluator`, `Incremental Alpha Cache`, `Basel III Stress-Test` và **Property-Based Fuzzing 100 hồ sơ ngẫu nhiên khớp 100/100 giữa Drools, CLIPS và Prolog**).

---

### SLIDE 14: Tổng kết Giá trị Học thuật & Thực tiễn của Đồ án
- **Về mặt Lý thuyết DSS & Rule Engine:**
  - Làm chủ trọn vẹn kiến trúc Apache KIE / Drools: từ cú pháp `.drl`, mạng Rete/PHREAK + Incremental Alpha Memory Cache, `SafeASTEvaluator`, cơ chế `agenda-group` pipeline, giải quyết xung đột `salience` + `activation-group` đến hệ thống bảo toàn chân lý `TMS (insertLogical)`.
- **Về mặt Thực tiễn Ứng dụng Ngân hàng (Basel III FinTech DSS):**
  - Xây dựng hệ thống DSS hoàn chỉnh cho bài toán Thẩm định & Định giá Tín dụng kết hợp chuẩn định lượng **Basel III (`PD`, `LGD`, `EAD`, `EL`, `RAROC`)**, **Macro Stress-Testing**, **giải thích hộp trắng** và **What-If / Goal-Seeking**.

---

### SLIDE 15: Demo Trực tiếp & Thảo luận / Hỏi đáp (Q&A)
- **Mời Giảng viên và Hội đồng theo dõi phần Demo trực tiếp trên Web Dashboard (`http://localhost:8000`).**
- **Xin chân thành cảm ơn Giảng viên và các bạn đã lắng nghe!**

---

## PHẦN 2: KỊCH BẢN DEMO TRỰC TIẾP 5 PHÚT TRÊN WEB UI 

> **Chuẩn bị trước khi lên bục:** Chạy lệnh `python app.py` trên Terminal, mở trình duyệt tại `http://localhost:8000`.

### Phút 1: Giới thiệu Tổng quan & Demo 1-Click Kịch bản 1 (VIP Hạng A) vs Kịch bản 5 (Knock-out CIC)
1. Chỉ vào **Khu vực 1 (Thanh Kịch bản Demo 1-Click)**: *"Thưa thầy/cô, hệ thống của nhóm đọc trực tiếp 20 luật từ file `rules/credit_approval.drl` và 3 luật từ bảng quyết định `decision_table_rules.csv` vào `KieBase`."*
2. Bấm vào **Kịch bản 1 (Khách hàng VIP – Hạng A)**:
   - Chỉ vào **Khu vực 2 (Executive Decision Card)**: Hệ thống duyệt tự động 100% hạn mức (`500 triệu`), lãi suất ưu đãi VIP `6.8%/năm`, điểm `100/100`, đồng thời vì khoản vay $\ge 500$ triệu nên luật `R18` tự động bật cờ yêu cầu định giá độc lập.
3. Bấm ngay sang **Kịch bản 5 (Từ chối do Nợ xấu CIC)**:
   - Chỉ vào chuỗi luật kích hoạt: Chỉ có `R02 → R20` (2 chu kỳ!). Giải thích: *"Nhờ kiến trúc PHREAK và cơ chế `insertLogical`, khi `R02` đánh rớt ở Tầng 1, Fact trung gian `EligibilityPassed` không được sinh ra nên toàn bộ 13 luật ở Tầng 2 và Tầng 3 được cắt nhánh hoàn toàn."*

### Phút 2: Trình diễn Sơ đồ Mạng Rete / PHREAK & Chạy Từng Bước (`Step-by-Step Replay`) + Minh họa `TMS`
1. Bấm chọn **Kịch bản 4 (Hồ sơ Xung đột Hạng C – Phạm Quốc Bảo)**.
2. Cuộn xuống **Khu vực 3 (Sơ đồ Mạng Suy diễn Rete / PHREAK)**:
   - Chỉ vào thanh thống kê kiến trúc: *"Mạng Rete của nhóm có cơ chế **Alpha Node Sharing** giúp gom 64 điều kiện đơn thành 26 nút Alpha duy nhất, tiết kiệm 38 phép lọc."*
   - Bấm nút **"▶ Chạy từng bước (Replay)"**: Giảng viên sẽ thấy từng nút luật phát sáng lần lượt từ Tầng 1 (`R04`) $\rightarrow$ Tầng 2 (`R05` cộng 20 điểm lên 60, sau đó `R08` phát sáng trừ 15 điểm xuống 45, rồi `R11` gán Hạng C) $\rightarrow$ Tầng 3 (`R16` chuyển Hội đồng Tín dụng) $\rightarrow$ Tầng 4 (`R19`, `DT03`).
3. Bấm nút **"Minh họa TMS (`insertLogical`)"** màu xanh cổ vịt ngay góc phải Khu vực 3:
   - Hộp thực nghiệm TMS hiện ra chứng minh: Khi `R04` chạy, Working Memory có 2 Fact (`Applicant` + `EligibilityPassed`). Ngay khi `modify(cic_bad_debt=True)`, TMS tự động rút lại (`AUTO_RETRACT_LOGICAL`) Fact `EligibilityPassed` về còn 1 Fact!

### Phút 3: Chứng minh Giải quyết Xung đột (`Conflict Resolution`) ở Khu vực 4
1. Bấm lại **Kịch bản 1** hoặc chọn **`APP015 – Hồ Trọng Nghĩa`** từ menu 15 hồ sơ CSV.
2. Cuộn xuống **Khu vực 4 (Nhật ký Truy vết & Conflict Resolution Log)**:
   - Chỉ vào ô màu vàng **"Bằng chứng Giải quyết Xung đột: Các Luật bị Hủy do `activation-group`"**:
   - Với `APP001`, chỉ rõ `R10` và `R11` bị hủy bởi `R09 (salience 68)` trong nhóm `risk-tier-assignment`.
   - Với `APP015` (vừa nợ xấu CIC vừa DTI 74% > 65%), chỉ rõ trong bảng Timeline Cycle #1: Tập xung đột `Conflict Set` có cả `★ R02(sal:98)` và `R03(sal:95)`, `R02` chiến thắng nhờ `salience` cao hơn và hủy `R03` trong `activation-group "hard-knockout"`.

### Phút 4: Phòng Thí nghiệm What-If & Phân tích Độ nhạy (Khu vực 5)
1. Chuyển sang **Tab 2: Phòng Thí nghiệm What-If & Độ nhạy**.
2. Hồ sơ gốc đang là **Kịch bản 3 (`APP003` – Lê Hoàng Nam)**: Hạng B vay tín chấp (TSĐB = 0), bị cắt giảm hạn mức còn 80% (`160 triệu`) với lãi suất `10.8%/năm` (`CONDITIONAL_APPROVAL`).
3. Kéo thanh trượt **"Giá trị Tài sản đảm bảo (TSĐB)"** từ `0 triệu` lên `250 triệu` ($\ge 120\% \times 200$ triệu):
   - Ngay lập tức thẻ **What-If** bên phải chuyển sang màu xanh **`PHÊ DUYỆT TỰ ĐỘNG (APPROVED)`**, điểm tăng `+15` (từ `65` lên `80` – đạt `TIER_A`!), hạn mức tăng lên `200 triệu` (100%) và lãi suất giảm mạnh từ `10.8%` xuống `7.5%/năm`!
   - Chỉ vào dòng **"+ Luật kích hoạt mới: [R07, R09, R13]"**: Đây chính là giá trị cốt lõi của một hệ thống DSS thực thụ!

### Phút 5: Chấm điểm Hàng loạt 15 Hồ sơ CSV & Live DRL Studio (Khu vực 6)
1. Bấm sang **Tab 3: Chấm điểm Hàng loạt 15 Hồ sơ CSV**: Hiển thị ngay biểu đồ phân bổ quyết định và bảng tổng hợp 15 hồ sơ trong `data/sample_applicants.csv`.
2. Bấm sang **Tab 4: Live DRL Studio & Bảng Quyết định**:
   - Cho giảng viên thấy mã nguồn `rules/credit_approval.drl` trực tiếp trên trình duyệt.
   - Thử sửa nhanh lãi suất VIP ở luật `R13` từ `6.8` thành `6.5` rồi bấm **"Biên dịch lại KieBase & Chạy thử Ngay"** $\rightarrow$ Hệ thống báo biên dịch thành công ngay lập tức, chứng minh tính tách biệt hoàn toàn giữa Luật nghiệp vụ và Code ứng dụng!

---

## PHẦN 3: 10 CÂU HỎI PHẢN BIỆN CHUYÊN SÂU CỦA GIẢNG VIÊN & CÂU TRẢ LỜI MẪU

### Câu 1: Vì sao đề tài của nhóm là công cụ Drools (vốn có nguồn gốc từ hệ sinh thái Java/Apache KIE), nhưng nhóm lại xây dựng bộ máy thực thi `.drl` và giao diện trực quan hóa Rete/PHREAK trên Python?
- **Trả lời mẫu:**
  Thưa thầy/cô, quyết định thiết kế này xuất phát từ 3 lý do học thuật và kỹ thuật:
  1. **Thứ nhất (Tính minh bạch hộp trắng – White-box Visualization):** Khi gọi Drools qua thư viện đóng gói JVM truyền thống, mạng Rete/PHREAK bên trong hoạt động như một hộp đen đã biên dịch bytecode, rất khó trích xuất trực tiếp trạng thái từng nút `AlphaNode`, `BetaNode`, danh sách `Conflict Set` trước khi nổ luật và sự kiện `TMS Auto-Retract` ra JSON để vẽ sơ đồ phát sáng từng bước (Step-by-step Replay) trên giao diện Web. Việc tự cài đặt lõi `DRLParser`, `RetePhreakNetwork`, `KieBase`, `KieSession`, `Agenda` và `TMS` bằng Python giúp nhóm chứng minh sự hiểu biết sâu sắc đến từng dòng thuật toán của Drools thay vì chỉ gọi hàm thư viện có sẵn.
  2. **Thứ hai (Chuẩn cú pháp `.drl` 100%):** Toàn bộ tập luật `rules/credit_approval.drl` của nhóm được viết **đúng chuẩn cú pháp Drools Rule Language (`package`, `import`, `declare`, `rule`, `salience`, `agenda-group`, `activation-group`, `no-loop`, `lock-on-active`, `when`, `then`, `modify`, `insertLogical`)**, hoàn toàn tương thích với đặc tả Apache KIE Drools.
  3. **Thứ ba (Tính khả chuyển và tích hợp Hệ sinh thái Khoa học Dữ liệu DSS):** Hệ thống chạy ngay lập tức bằng 1 lệnh `python app.py` trên mọi máy tính phòng máy mà không lo lỗi thiếu JDK/Maven, đồng thời sẵn sàng kết nối trực tiếp với hệ sinh thái Python Data Science / Machine Learning cho các mô hình DSS lai (Hybrid DSS).

---

### Câu 2: Thuật toán PHREAK trong các phiên bản Drools hiện đại khác gì so với thuật toán Rete cổ điển của Charles Forgy (1979)?
- **Trả lời mẫu:**
  - **Rete cổ điển** là thuật toán **đánh giá tức thời (Eager / Data-driven Propagation)**: Ngay khi một Fact được `insert` hoặc `modify`, token được đẩy lan truyền qua toàn bộ các nút Alpha và Beta của tất cả các luật trong hệ thống, dù luật đó thuộc tầng chưa được xét đến.
  - **PHREAK** (từ Drools 6+) chuyển sang **đánh giá lười định hướng mục tiêu (Lazy / Goal-driven Segment Evaluation)**:
    1. PHREAK chỉ đánh giá các phân đoạn mạng (Segments) thuộc `agenda-group` đang có **focus** hiện tại.
    2. Trong bài toán của nhóm, nếu một hồ sơ bị loại ngay ở Tầng 1 (`1-eligibility`) bởi `R02` (Nợ xấu CIC), PHREAK không cần tốn bộ nhớ và CPU để thực hiện phép nối Beta Join cho các luật ở Tầng 2 (`2-risk-scoring`) và Tầng 3 (`3-pricing-decision`).
    3. PHREAK quản lý bộ nhớ theo 3 cấp (`Node Memory`, `Segment Memory`, `Rule Memory`) và đánh giá theo lô (Set-oriented propagation) thay vì từng tuple đơn lẻ như Rete.

---

### Câu 3: Trong file `credit_approval.drl`, tại sao ở Tầng 2 (`2-risk-scoring`), các luật cộng/trừ điểm `R05, R06, R07, R08` phải dùng `lock-on-active true` mà chỉ dùng `no-loop true` thôi thì chưa đủ?
- **Trả lời mẫu:**
  Đây là một điểm kỹ thuật cực kỳ quan trọng trong Drools:
  - `no-loop true` chỉ ngăn một luật **tự kích hoạt lại chính nó** khi khối `then` của chính luật đó gọi `modify($app)`.
  - Tuy nhiên, ở Tầng 2, ta có chuỗi nhiều luật cùng sửa đối tượng `$app`: giả sử `R05` (`salience 80`) chạy trước và gọi `modify($app) { composite_score = $app.composite_score + 20 }`. Sau đó đến lượt `R06` (`salience 78`) chạy và cũng gọi `modify($app) { composite_score = $app.composite_score + 25 }`.
  - Khi `R06` gọi `modify($app)`, chỉ số `recency` của `$app` thay đổi nên Drools đánh giá lại toàn bộ các luật khớp `$app`. Nếu `R05` chỉ có `no-loop true` (mà không có `lock-on-active true`), sự thay đổi do `R06` gây ra sẽ làm `R05` kích hoạt lại lần thứ 2, rồi `R05` lại kích hoạt `R06` tạo thành **vòng lặp cộng điểm vô hạn giữa 2 luật (`Cross-rule infinite loop`)**!
  - Khi đặt `lock-on-active true`, ngay khi `agenda-group "2-risk-scoring"` đang active, bất kỳ luật nào trong tầng đó đã chạy 1 lần trên Fact `$app` sẽ bị khóa lại, không bao giờ chạy lần thứ 2 trong cùng phiên focus của tầng đó.

---

### Câu 4: Hãy giải thích sự khác biệt giữa `insert()` và `insertLogical()` (Truth Maintenance System) trong Drools và chỉ ra nhóm đã áp dụng nó ở đâu?
- **Trả lời mẫu:**
  - `insert(fact)` tạo ra một **Stated Fact** (sự kiện độc lập): Một khi đã đưa vào Working Memory, nó tồn tại vĩnh viễn trong phiên làm việc cho đến khi có câu lệnh `delete(fact)` / `retract(fact)` xóa nó một cách tường minh.
  - `insertLogical(fact)` tạo ra một **Logical Fact** (sự kiện suy diễn có điều kiện bảo chứng) do **Truth Maintenance System (TMS)** quản lý: Fact này chỉ tồn tại chừng nào điều kiện `WHEN` (LHS) của luật sinh ra nó còn đúng.
  - **Áp dụng trong đồ án:** Ở luật **`R04`** (cuối Tầng 1), khi khách hàng thỏa mãn `age 18..65 && cic_bad_debt == false && dti_ratio <= 65.0`, `R04` gọi `insertLogical(new EligibilityPassed(applicant_id = $app.applicant_id, status = "PASSED"))`. Toàn bộ các luật ở Tầng 2 và Tầng 3 (`R05..R17`) đều yêu cầu kết hợp (Beta Join) với Fact `EligibilityPassed` này. Nếu trong quá trình thẩm định động, dữ liệu khách hàng bị cập nhật phát hiện `cic_bad_debt = true`, điều kiện của `R04` lập tức trở thành `False` và TMS **tự động thu hồi (`Auto-Retract`)** `EligibilityPassed`, vô hiệu hóa ngay lập tức toàn bộ quyền đi tiếp vào Tầng 2–3 mà không cần viết thêm một luật xóa thủ công nào.

---

### Câu 5: Cơ chế `activation-group` hoạt động như thế nào trong quá trình Conflict Resolution? Nhóm đã dùng bao nhiêu `activation-group` trong đồ án?
- **Trả lời mẫu:**
  - `activation-group` gom một tập hợp các luật vào một nhóm **loại trừ lẫn nhau (Mutually Exclusive / XOR Group)**. Khi nhiều luật trong cùng một `activation-group` đều thỏa mãn điều kiện `WHEN` và cùng nằm trong `Conflict Set` trên Agenda, bộ giải quyết xung đột sẽ chọn luật có `salience` cao nhất để kích hoạt. **Ngay khi luật chiến thắng đó kích hoạt, toàn bộ các `Activation` còn lại trong cùng `activation-group` bị hủy bỏ (`CANCELLED`) ngay lập tức**.
  - Nhóm đã thiết kế **3 `activation-group` cốt lõi** trong `credit_approval.drl`:
    1. `"hard-knockout"` (Tầng 1: `R01`, `R02`, `R03`): Nếu khách hàng vi phạm nhiều lỗi loại trừ cứng cùng lúc (như hồ sơ `APP015` vừa có nợ xấu CIC vừa có DTI 74%), chỉ lỗi nghiêm trọng nhất có `salience` cao nhất (`R02 - sal:98`) kích hoạt và hủy `R03 (sal:95)`.
    2. `"risk-tier-assignment"` (Tầng 2: `R09`, `R10`, `R11`, `R12`): Vì các ngưỡng điểm được viết dạng bậc thang (`>= 80`, `>= 60`, `>= 40`, `< 40`), một khách hàng đạt 100 điểm sẽ khớp đồng thời cả `R09`, `R10` và `R11`. Nhờ `activation-group "risk-tier-assignment"`, `R09 (sal:68)` chạy trước, gán `TIER_A` và tự động hủy `R10`, `R11`.
    3. `"final-decision"` (Tầng 3: `R13`..`R17`): Đảm bảo mỗi hồ sơ chỉ nhận duy nhất một quyết định phê duyệt và biểu phí lãi suất cuối cùng.

---

### Câu 6: Thế nào là `Alpha Node Sharing` và `BetaNode Join` trong mạng Rete của nhóm?
- **Trả lời mẫu:**
  - **`AlphaNode`** kiểm tra điều kiện trên 1 Fact đơn lẻ (ví dụ `eligible == true` hoặc `age >= 18 && age <= 65`). Trong tập luật của nhóm có tới 13 luật ở Tầng 2 và Tầng 3 cùng kiểm tra `eligible == true` trên `Applicant` và `status == "PASSED"` trên `EligibilityPassed`. Thay vì tạo 13 nút kiểm tra lặp lại, `RetePhreakNetwork` sử dụng khóa chuẩn hóa `(fact_type, constraint_expression)` để tạo **1 `AlphaNode` dùng chung duy nhất** (chia sẻ cho cả 13 luật). Kết quả thực nghiệm cho thấy từ 64 điều kiện đơn ban đầu, mạng rút gọn xuống chỉ còn **26 `AlphaNode`**, tiết kiệm **38 nút lọc**.
  - **`BetaNode Join`** là nút có 2 đầu vào: đầu vào trái (*Left Input / Beta Memory*) nhận Fact `EligibilityPassed` và đầu vào phải (*Right Input / Alpha Memory*) nhận Fact `Applicant`, thực hiện phép kết nối quan hệ `applicant_id == $elig.applicant_id`.

---

### Câu 7: Tại sao nhóm lại chọn Drools (Suy diễn tiến) thay vì Prolog (Suy diễn lùi) cho bài toán Thẩm định & Định giá Tín dụng này?
- **Trả lời mẫu:**
  - Bài toán thẩm định và định giá khoản vay là một bài toán **biến đổi trạng thái dữ liệu qua nhiều công đoạn (Multi-stage State Transformation)** bắt đầu từ một bộ dữ liệu đầu vào đã biết (`Applicant`): từ dữ liệu thô $\rightarrow$ tính điểm cộng/trừ lũy tiến qua nhiều luật độc lập (`R05`, `R06`, `R07`, `R08`) $\rightarrow$ tổng hợp điểm để phân hạng rủi ro $\rightarrow$ tính toán hạn mức (`100%`, `80%`, `55%`) và lãi suất (`6.8%`..`12.5%`) $\rightarrow$ sinh danh sách khuyến nghị.
  - Cơ chế **Suy diễn tiến (Forward Chaining)** kết hợp `modify()` trên Working Memory của **Drools** mô hình hóa tự nhiên và trực tiếp luồng tích lũy điểm số và biến đổi trạng thái này.
  - Ngược lại, **Prolog (Backward Chaining)** phù hợp khi ta có một câu hỏi mục tiêu cố định kiểu đúng/sai (`is_approved(X)`), nhưng rất bất tiện khi phải cộng/trừ tích lũy điểm số qua nhiều luật tùy chọn và sinh đồng thời nhiều khuyến nghị phụ trợ ở Tầng 4.

---

### Câu 8: Hệ thống của nhóm hỗ trợ nhà quản trị ra quyết định như thế nào khi một hồ sơ bị "Duyệt có điều kiện" hoặc "Chuyển thẩm định thủ công"? (Tính chất DSS nằm ở đâu?)
- **Trả lời mẫu:**
  Một hệ thống DSS chân chính không chỉ đưa ra nhãn kết luận cuối cùng mà phải trả lời được câu hỏi **"Tại sao?" (Explainability)** và **"Cần làm gì để tốt hơn?" (What-If & Actionable Recommendations)**:
  1. Ở Tầng 4 (`4-dss-explanation`), các luật **`R19`** và **`R20`** tính toán định lượng ngay lập tức lộ trình cải thiện hồ sơ: ví dụ với hồ sơ `APP003` (vay 200 triệu tín chấp, chỉ được duyệt có điều kiện 80% = 160 triệu với lãi suất 10.8%), `R19` chỉ rõ khách hàng cần bổ sung tài sản đảm bảo tối thiểu $1.2 \times 200 = 240$ triệu VNĐ để nhận thêm `+15 điểm` bảo chứng và nâng lên gói duyệt 100% với lãi suất thấp hơn.
  2. Trên giao diện Web, **Khu vực 5 (Phòng Thí nghiệm What-If & Phân tích Độ nhạy)** cho phép chuyên viên tín dụng kéo thanh trượt giả lập ngay trước mặt khách hàng để thấy sự dịch chuyển của các luật kích hoạt (`+R07`, `+R09`, `+R13`) và đường cong độ nhạy lãi suất theo thu nhập/DTI.

---

### Câu 9: Tính năng Decision Table (`rules/decision_table_rules.csv`) hoạt động như thế nào trong hệ thống của nhóm?
- **Trả lời mẫu:**
  Trong thực tế ngân hàng, bên cạnh bộ luật khung cốt lõi trong file `.drl`, phòng Chính sách Sản phẩm thường xuyên ban hành các chương trình khuyến mãi hoặc quy tắc kiểm soát kỳ hạn dưới dạng bảng tính CSV/Excel.
  Trong đồ án, lớp `DecisionTableLoader` đọc trực tiếp file `rules/decision_table_rules.csv` (chứa các cột `rule_id`, `agenda_group`, `salience`, `activation_group`, `when_condition`, `then_action`), tự động dịch từng dòng trong bảng thành cấu trúc `DRLRule` chuẩn và biên dịch gộp thẳng vào mạng `RetePhreakNetwork` của `KieBase` (các luật `DT01`, `DT02`, `DT03`).

---

### Câu 10: Nếu muốn nâng cấp hệ thống này lên quy mô ngân hàng số thực tế với hàng triệu khách hàng, nhóm sẽ phát triển theo hướng nào?
- **Trả lời mẫu:**
  Nhóm đề xuất kiến trúc **Hybrid Intelligent DSS (Kết hợp Machine Learning + Drools Rule Engine + DMN)**:
  1. **Tầng Học máy (Predictive ML Layer):** Sử dụng mô hình Gradient Boosting (XGBoost / LightGBM) huấn luyện trên dữ liệu lịch sử trả nợ để dự báo xác suất vỡ nợ định lượng (`PD - Probability of Default`).
  2. **Tầng Luật Nghiệp vụ (Prescriptive Drools DRL / DMN Layer):** Đưa chỉ số `PD` từ mô hình ML vào làm một thuộc tính của Fact `Applicant` trong Drools. Mạng luật Drools sẽ kết hợp `PD` với các quy chế bắt buộc của Ngân hàng Nhà nước và chuẩn Basel III để ra quyết định cuối cùng, đảm bảo hệ thống vừa có độ chính xác dự báo cao của AI, vừa có tính tuân thủ pháp lý và giải thích minh bạch 100% của Rule Engine.
