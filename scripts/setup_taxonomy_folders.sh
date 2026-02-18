#!/usr/bin/env bash
# setup_taxonomy_folders.sh — Sinh cây thư mục ~/MedicalDevices theo taxonomy
# Idempotent: chạy lại không tạo duplicate, không xóa thư mục hiện có
# Chạy: bash scripts/setup_taxonomy_folders.sh [--base-dir /path/to/dir]
# Yêu cầu: macOS ARM, không cần sudo

set -euo pipefail

# ── Cấu hình ──────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Đọc BASE_DIR từ .env nếu có
if [[ -f "$PROJECT_ROOT/.env" ]]; then
    BASE_DIR=$(grep -E '^MEDICAL_DEVICES_DIR=' "$PROJECT_ROOT/.env" | cut -d'=' -f2 | tr -d '"' | tr -d "'")
fi
BASE_DIR="${BASE_DIR:-$HOME/MedicalDevices}"

# Override từ argument
while [[ $# -gt 0 ]]; do
    case "$1" in
        --base-dir) BASE_DIR="$2"; shift 2 ;;
        *) echo "Tham số không hợp lệ: $1" >&2; exit 1 ;;
    esac
done

echo "=== MedicalDocBot: Setup Taxonomy Folders ==="
echo "Thư mục gốc: $BASE_DIR"
echo ""

# ── Hàm tạo thư mục + README ──────────────────────────────────────────────────
make_dir() {
    local dir="$1"
    local readme_title="$2"
    local readme_en="$3"

    mkdir -p "$dir"

    local readme="$dir/README.md"
    if [[ ! -f "$readme" ]]; then
        cat > "$readme" <<EOF
# $readme_title

> $readme_en

Thư mục này được quản lý bởi **MedicalDocBot**.  
Đặt tài liệu thiết bị vào các thư mục con tương ứng.
EOF
        echo "  [+] README.md: $readme_title"
    fi
}

# ── Tạo thư mục gốc ───────────────────────────────────────────────────────────
mkdir -p "$BASE_DIR"
mkdir -p "$BASE_DIR/wiki"
mkdir -p "$BASE_DIR/.db"
mkdir -p "$BASE_DIR/.cache/extracted"

echo "Đang tạo cây thư mục taxonomy..."
echo ""

# ── 01: Chẩn đoán hình ảnh ────────────────────────────────────────────────────
make_dir "$BASE_DIR/01_chan_doan_hinh_anh" "Chẩn đoán hình ảnh" "Diagnostic imaging"
make_dir "$BASE_DIR/01_chan_doan_hinh_anh/x_quang" "X-quang" "X-Ray"
make_dir "$BASE_DIR/01_chan_doan_hinh_anh/ct" "CT-Scanner" "CT Scanner"
make_dir "$BASE_DIR/01_chan_doan_hinh_anh/mri" "MRI" "MRI"
make_dir "$BASE_DIR/01_chan_doan_hinh_anh/sieu_am" "Siêu âm" "Ultrasound"
make_dir "$BASE_DIR/01_chan_doan_hinh_anh/noi_soi" "Nội soi chẩn đoán" "Diagnostic endoscopy"
make_dir "$BASE_DIR/01_chan_doan_hinh_anh/mamography" "X-quang tuyến vú" "Mammography"

# ── 02: Xét nghiệm sinh hóa ───────────────────────────────────────────────────
make_dir "$BASE_DIR/02_xet_nghiem_sinh_hoa" "Xét nghiệm sinh hóa" "Biochemistry analyzers"
make_dir "$BASE_DIR/02_xet_nghiem_sinh_hoa/sinh_hoa" "Sinh hóa tự động" "Auto biochemistry analyzer"
make_dir "$BASE_DIR/02_xet_nghiem_sinh_hoa/huyet_hoc" "Huyết học" "Hematology"
make_dir "$BASE_DIR/02_xet_nghiem_sinh_hoa/dong_mau" "Đông máu" "Coagulation"
make_dir "$BASE_DIR/02_xet_nghiem_sinh_hoa/mien_dich" "Miễn dịch huỳnh quang" "Immunofluorescence"
make_dir "$BASE_DIR/02_xet_nghiem_sinh_hoa/pcr" "PCR định lượng" "Quantitative PCR"

# ── 03: Hồi sức cấp cứu ──────────────────────────────────────────────────────
make_dir "$BASE_DIR/03_hoi_suc_cap_cuu" "Hồi sức cấp cứu" "ICU/Emergency"
make_dir "$BASE_DIR/03_hoi_suc_cap_cuu/may_tho" "Máy thở" "Ventilator"
make_dir "$BASE_DIR/03_hoi_suc_cap_cuu/monitor" "Monitor đa năng" "Patient monitor"
make_dir "$BASE_DIR/03_hoi_suc_cap_cuu/bom_tiem" "Bơm tiêm truyền" "Infusion pump"
make_dir "$BASE_DIR/03_hoi_suc_cap_cuu/defibrillator" "Phá sốc điện" "Defibrillator"
make_dir "$BASE_DIR/03_hoi_suc_cap_cuu/ventilator" "Thở máy" "Mechanical ventilator"

# ── 04: Gây mê hồi sức ───────────────────────────────────────────────────────
make_dir "$BASE_DIR/04_gay_me" "Gây mê hồi sức" "Anesthesia"
make_dir "$BASE_DIR/04_gay_me/may_gay_me" "Máy gây mê" "Anesthesia machine"
make_dir "$BASE_DIR/04_gay_me/gas_monitor" "Theo dõi khí gây mê" "Anesthetic gas monitor"
make_dir "$BASE_DIR/04_gay_me/suction" "Hút dịch phẫu thuật" "Surgical suction"

# ── 05: Phẫu thuật nội soi ───────────────────────────────────────────────────
make_dir "$BASE_DIR/05_phau_thuat_noi_soi" "Phẫu thuật nội soi" "Surgical endoscopy"
make_dir "$BASE_DIR/05_phau_thuat_noi_soi/laparos" "Nội soi ổ bụng" "Laparoscopy"
make_dir "$BASE_DIR/05_phau_thuat_noi_soi/thoracos" "Nội soi lồng ngực" "Thoracoscopy"
make_dir "$BASE_DIR/05_phau_thuat_noi_soi/endoscopic_tower" "Tower nội soi" "Endoscopic tower"
make_dir "$BASE_DIR/05_phau_thuat_noi_soi/electrosurgery" "Dao điện cao tần" "Electrosurgery unit"

# ── 06: Tim mạch ─────────────────────────────────────────────────────────────
make_dir "$BASE_DIR/06_tim_mach" "Tim mạch" "Cardiology"
make_dir "$BASE_DIR/06_tim_mach/ecg" "Điện tim" "ECG"
make_dir "$BASE_DIR/06_tim_mach/echo" "Siêu âm tim" "Echocardiography"
make_dir "$BASE_DIR/06_tim_mach/cathlab" "Can thiệp mạch" "Cath lab"
make_dir "$BASE_DIR/06_tim_mach/pacemaker" "Tạo nhịp tim" "Pacemaker"

# ── 07: Thận nhân tạo ────────────────────────────────────────────────────────
make_dir "$BASE_DIR/07_than_nhan_tao" "Thận nhân tạo" "Dialysis"
make_dir "$BASE_DIR/07_than_nhan_tao/hemodialysis" "Thẩm phân máu" "Hemodialysis"
make_dir "$BASE_DIR/07_than_nhan_tao/crrt" "Lọc máu liên tục" "CRRT"
make_dir "$BASE_DIR/07_than_nhan_tao/ro_water" "Nước RO" "RO water system"

# ── 08: Nhãn khoa ────────────────────────────────────────────────────────────
make_dir "$BASE_DIR/08_nhan_khoa" "Nhãn khoa" "Ophthalmology"
make_dir "$BASE_DIR/08_nhan_khoa/slit_lamp" "Đèn khe" "Slit lamp"
make_dir "$BASE_DIR/08_nhan_khoa/phaco" "Phẫu thuật đục thủy tinh thể" "Phacoemulsification"
make_dir "$BASE_DIR/08_nhan_khoa/excimer" "Laser khúc xạ" "Excimer laser"

# ── 09: Sản phụ khoa ─────────────────────────────────────────────────────────
make_dir "$BASE_DIR/09_san_phu_khoa" "Sản phụ khoa" "Obstetrics"
make_dir "$BASE_DIR/09_san_phu_khoa/ultrasound_ob" "Siêu âm sản khoa" "Obstetric ultrasound"
make_dir "$BASE_DIR/09_san_phu_khoa/ctg" "Theo dõi tim thai" "CTG monitor"
make_dir "$BASE_DIR/09_san_phu_khoa/delivery_bed" "Giường sinh" "Delivery bed"

# ── 10: Tai mũi họng ─────────────────────────────────────────────────────────
make_dir "$BASE_DIR/10_tai_mui_hong" "Tai mũi họng" "ENT"
make_dir "$BASE_DIR/10_tai_mui_hong/ent_unit" "Bàn khám TMH" "ENT examination unit"
make_dir "$BASE_DIR/10_tai_mui_hong/endoscope_ent" "Nội soi TMH" "ENT endoscope"

# ── 11: Răng hàm mặt ─────────────────────────────────────────────────────────
make_dir "$BASE_DIR/11_rang_ham_mat" "Răng hàm mặt" "Dental"
make_dir "$BASE_DIR/11_rang_ham_mat/dental_unit" "Ghế nha khoa" "Dental unit"
make_dir "$BASE_DIR/11_rang_ham_mat/dental_xray" "X-quang răng" "Dental X-ray"

# ── 12: Ngoại tổng quát ──────────────────────────────────────────────────────
make_dir "$BASE_DIR/12_ngoai_tong_quat" "Ngoại tổng quát" "General surgery"
make_dir "$BASE_DIR/12_ngoai_tong_quat/operating_table" "Bàn mổ" "Operating table"
make_dir "$BASE_DIR/12_ngoai_tong_quat/operating_light" "Đèn mổ" "Operating light"
make_dir "$BASE_DIR/12_ngoai_tong_quat/suction_surgical" "Hút phẫu thuật" "Surgical suction"

# ── 13: Nội tổng quát ────────────────────────────────────────────────────────
make_dir "$BASE_DIR/13_noi_tong_quat" "Nội tổng quát" "Internal medicine"
make_dir "$BASE_DIR/13_noi_tong_quat/ecg_portable" "Điện tim cầm tay" "Portable ECG"
make_dir "$BASE_DIR/13_noi_tong_quat/bp_monitor" "Đo huyết áp" "Blood pressure monitor"
make_dir "$BASE_DIR/13_noi_tong_quat/glucometer" "Đo đường huyết" "Glucometer"

# ── 14: Tiêu hóa ─────────────────────────────────────────────────────────────
make_dir "$BASE_DIR/14_tieu_hoa" "Tiêu hóa" "Gastroenterology"
make_dir "$BASE_DIR/14_tieu_hoa/gastroscope" "Nội soi dạ dày" "Gastroscope"
make_dir "$BASE_DIR/14_tieu_hoa/colonoscopy" "Nội soi đại tràng" "Colonoscopy"

# ── 15: Tiết niệu ────────────────────────────────────────────────────────────
make_dir "$BASE_DIR/15_tiet_nieu" "Tiết niệu" "Urology"
make_dir "$BASE_DIR/15_tiet_nieu/cystoscope" "Nội soi bàng quang" "Cystoscope"
make_dir "$BASE_DIR/15_tiet_nieu/lithotripsy" "Tán sỏi" "Lithotripsy"

# ── 16: Ung bướu ─────────────────────────────────────────────────────────────
make_dir "$BASE_DIR/16_ung_buou" "Ung bướu" "Oncology"
make_dir "$BASE_DIR/16_ung_buou/linear_accelerator" "Gia tốc tuyến tính" "Linear accelerator"
make_dir "$BASE_DIR/16_ung_buou/brachytherapy" "Xạ trị trong" "Brachytherapy"

# ── 17: Kiểm soát nhiễm khuẩn ────────────────────────────────────────────────
make_dir "$BASE_DIR/17_kiem_soat_nhiem_khuan" "Kiểm soát nhiễm khuẩn" "Sterilization"
make_dir "$BASE_DIR/17_kiem_soat_nhiem_khuan/autoclave" "Nồi hấp tiệt trùng" "Autoclave"
make_dir "$BASE_DIR/17_kiem_soat_nhiem_khuan/washer_disinfector" "Máy rửa khử khuẩn" "Washer disinfector"

# ── 18: Phục hồi chức năng ───────────────────────────────────────────────────
make_dir "$BASE_DIR/18_phuc_hoi_chuc_nang" "Phục hồi chức năng" "Rehabilitation"
make_dir "$BASE_DIR/18_phuc_hoi_chuc_nang/physio" "Vật lý trị liệu" "Physiotherapy"
make_dir "$BASE_DIR/18_phuc_hoi_chuc_nang/electrotherapy" "Kích thích điện" "Electrotherapy"

# ── 19: Chẩn đoán chức năng ──────────────────────────────────────────────────
make_dir "$BASE_DIR/19_chan_doan_chuc_nang" "Chẩn đoán chức năng" "Functional diagnostics"
make_dir "$BASE_DIR/19_chan_doan_chuc_nang/eeg" "Điện não đồ" "EEG"
make_dir "$BASE_DIR/19_chan_doan_chuc_nang/emg" "Điện cơ đồ" "EMG"

# ── 20: Khí y tế ─────────────────────────────────────────────────────────────
make_dir "$BASE_DIR/20_khi_y_te" "Khí y tế" "Medical gases"
make_dir "$BASE_DIR/20_khi_y_te/oxygen_concentrator" "Máy tạo oxy" "Oxygen concentrator"
make_dir "$BASE_DIR/20_khi_y_te/vacuum_system" "Hệ thống chân không" "Vacuum system"

# ── 21: CNTT y tế ────────────────────────────────────────────────────────────
make_dir "$BASE_DIR/21_cntt_y_te" "CNTT y tế" "Health IT"
make_dir "$BASE_DIR/21_cntt_y_te/pacs" "PACS" "PACS"
make_dir "$BASE_DIR/21_cntt_y_te/ris" "RIS" "RIS"
make_dir "$BASE_DIR/21_cntt_y_te/his" "HIS" "HIS"

# ── 22: Theo dõi sinh hiệu cầm tay ───────────────────────────────────────────
make_dir "$BASE_DIR/22_theo_doi_camtay" "Theo dõi sinh hiệu cầm tay" "Portable monitors"
make_dir "$BASE_DIR/22_theo_doi_camtay/spo2_portable" "SpO2 cầm tay" "Portable SpO2"
make_dir "$BASE_DIR/22_theo_doi_camtay/patient_monitor_portable" "Monitor di động" "Portable patient monitor"

# ── 23: Hỗ trợ phẫu thuật ────────────────────────────────────────────────────
make_dir "$BASE_DIR/23_ho_tro_phau_thuat" "Hỗ trợ phẫu thuật" "Surgical support"
make_dir "$BASE_DIR/23_ho_tro_phau_thuat/endoscopy_camera" "Camera nội soi" "Endoscopy camera"
make_dir "$BASE_DIR/23_ho_tro_phau_thuat/navigation_system" "Định vị phẫu thuật" "Surgical navigation"

# ── 24: Hô hấp ───────────────────────────────────────────────────────────────
make_dir "$BASE_DIR/24_ho_hap" "Hô hấp" "Respiratory"
make_dir "$BASE_DIR/24_ho_hap/nebulizer" "Máy khí dung" "Nebulizer"
make_dir "$BASE_DIR/24_ho_hap/spirometer" "Đo chức năng hô hấp" "Spirometer"

# ── 25: Khác ─────────────────────────────────────────────────────────────────
make_dir "$BASE_DIR/25_khac" "Khác" "Others"
make_dir "$BASE_DIR/25_khac/miscellaneous" "Thiết bị khác" "Miscellaneous"

# ── Tổng kết ─────────────────────────────────────────────────────────────────
echo ""
echo "=== Hoàn thành ==="
echo "Cây thư mục đã tạo tại: $BASE_DIR"
echo ""
# Đếm số thư mục đã tạo
DIR_COUNT=$(find "$BASE_DIR" -mindepth 1 -maxdepth 3 -type d | wc -l | tr -d ' ')
echo "Tổng số thư mục: $DIR_COUNT"
echo ""
echo "Cấu trúc (3 cấp đầu):"
find "$BASE_DIR" -mindepth 1 -maxdepth 3 -type d | sort | head -50
