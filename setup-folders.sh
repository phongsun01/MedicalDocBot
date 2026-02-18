#!/usr/bin/env bash
# setup-folders.sh — Tạo thư mục ~/MedicalDevices từ taxonomy V2
# Thuần bash, không cần Python/YAML parser
# Idempotent: chạy lại không xóa folder có sẵn

set -euo pipefail

ROOT="${MEDICAL_DEVICES_ROOT:-$HOME/MedicalDevices}"
COUNT=0

mkdir_safe() {
    if [[ ! -d "$ROOT/$1" ]]; then
        mkdir -p "$ROOT/$1"
        COUNT=$((COUNT + 1))
    fi
}

echo "🏗️  Tạo cây thư mục MedicalDevices (Taxonomy V2)"
echo "📁 Root: $ROOT"
echo ""

# 1. Chẩn đoán hình ảnh
mkdir_safe "chan_doan_hinh_anh/x_quang"
mkdir_safe "chan_doan_hinh_anh/ct_scanner"
mkdir_safe "chan_doan_hinh_anh/mri"
mkdir_safe "chan_doan_hinh_anh/sieu_am"
mkdir_safe "chan_doan_hinh_anh/c_arm"
mkdir_safe "chan_doan_hinh_anh/x_quang_rang"

# 2. Thiết bị nội soi
mkdir_safe "noi_soi/noi_soi_tieu_hoa"
mkdir_safe "noi_soi/noi_soi_tmh"
mkdir_safe "noi_soi/noi_soi_phe_quan"
mkdir_safe "noi_soi/noi_soi_o_bung"
mkdir_safe "noi_soi/noi_soi_khop"
mkdir_safe "noi_soi/he_thong_tower"

# 3. Xét nghiệm huyết học
mkdir_safe "xet_nghiem_huyet_hoc/may_dem_tb_mau"
mkdir_safe "xet_nghiem_huyet_hoc/may_dong_mau"
mkdir_safe "xet_nghiem_huyet_hoc/may_phan_tich_huyet_hoc"

# 4. Xét nghiệm sinh hóa – miễn dịch
mkdir_safe "xet_nghiem_sinh_hoa/may_sinh_hoa"
mkdir_safe "xet_nghiem_sinh_hoa/may_mien_dich"
mkdir_safe "xet_nghiem_sinh_hoa/may_dien_giai"

# 5. Xét nghiệm vi sinh – sinh học phân tử
mkdir_safe "xet_nghiem_vi_sinh/he_thong_pcr"
mkdir_safe "xet_nghiem_vi_sinh/may_nuoi_cay"
mkdir_safe "xet_nghiem_vi_sinh/tu_an_toan_sinh_hoc"
mkdir_safe "xet_nghiem_vi_sinh/tu_u_co2"

# 6. Xét nghiệm giải phẫu bệnh – tế bào học
mkdir_safe "xet_nghiem_giai_phau_benh/may_xu_ly_mo"
mkdir_safe "xet_nghiem_giai_phau_benh/may_cat_lanh"
mkdir_safe "xet_nghiem_giai_phau_benh/may_nhuom_mo"
mkdir_safe "xet_nghiem_giai_phau_benh/kinh_hien_vi"

# 7. Gây mê, máy thở
mkdir_safe "gay_me_may_tho/may_gay_me"
mkdir_safe "gay_me_may_tho/may_tho_hoi_suc"
mkdir_safe "gay_me_may_tho/may_tho_van_chuyen"
mkdir_safe "gay_me_may_tho/may_theo_doi_khi_me"

# 8. Hồi sức cấp cứu – theo dõi bệnh nhân
mkdir_safe "hoi_suc_cap_cuu/monitor"
mkdir_safe "hoi_suc_cap_cuu/may_pha_soc_dien"
mkdir_safe "hoi_suc_cap_cuu/bom_tiem_dien"
mkdir_safe "hoi_suc_cap_cuu/oxy_lieu_phap"
mkdir_safe "hoi_suc_cap_cuu/may_hut_dich"

# 9. Tim mạch – can thiệp
mkdir_safe "tim_mach_can_thiep/may_dien_tam_do"
mkdir_safe "tim_mach_can_thiep/may_sieu_am_tim"
mkdir_safe "tim_mach_can_thiep/he_thong_can_thiep"
mkdir_safe "tim_mach_can_thiep/may_tao_nhip"
mkdir_safe "tim_mach_can_thiep/dien_sinh_ly"

# 10. Phẫu thuật – phòng mổ
mkdir_safe "phau_thuat_phong_mo/ban_mo"
mkdir_safe "phau_thuat_phong_mo/den_mo"
mkdir_safe "phau_thuat_phong_mo/dao_mo_dien"
mkdir_safe "phau_thuat_phong_mo/dao_sieu_am"
mkdir_safe "phau_thuat_phong_mo/he_thong_treo_tran"
mkdir_safe "phau_thuat_phong_mo/tourniquet"

# 11. Sản – Nhi
mkdir_safe "san_nhi/may_sieu_am_san"
mkdir_safe "san_nhi/monitor_san_khoa"
mkdir_safe "san_nhi/giuong_san"
mkdir_safe "san_nhi/lồng_ap"
mkdir_safe "san_nhi/giuong_suoi"
mkdir_safe "san_nhi/den_chieu_vang_da"

# 12. Chuyên khoa mắt
mkdir_safe "chuyen_khoa_mat/may_sinh_hien_vi"
mkdir_safe "chuyen_khoa_mat/may_do_khuc_xa"
mkdir_safe "chuyen_khoa_mat/oct"
mkdir_safe "chuyen_khoa_mat/phaco"
mkdir_safe "chuyen_khoa_mat/laser_quang_dong"

# 13. Chuyên khoa tai mũi họng
mkdir_safe "chuyen_khoa_tmh/ban_kham_tmh"
mkdir_safe "chuyen_khoa_tmh/may_do_thinh_luc"
mkdir_safe "chuyen_khoa_tmh/may_do_nhi_luong"

# 14. Chuyên khoa răng hàm mặt
mkdir_safe "chuyen_khoa_rang/ghe_nha_khoa"
mkdir_safe "chuyen_khoa_rang/may_noi_nha"
mkdir_safe "chuyen_khoa_rang/den_tram"
mkdir_safe "chuyen_khoa_rang/thiet_bi_labo_rang"

# 15. Phục hồi chức năng – vật lý trị liệu
mkdir_safe "phuc_hoi_chuc_nang/may_keo_gian"
mkdir_safe "phuc_hoi_chuc_nang/song_ngan"
mkdir_safe "phuc_hoi_chuc_nang/sieu_am_dieu_tri"
mkdir_safe "phuc_hoi_chuc_nang/dien_xung"
mkdir_safe "phuc_hoi_chuc_nang/thiet_bi_tap_van_dong"

# 16. Lọc máu – thận nhân tạo
mkdir_safe "loc_mau_than_nhan_tao/may_than_nhan_tao"
mkdir_safe "loc_mau_than_nhan_tao/he_thong_crrt"
mkdir_safe "loc_mau_than_nhan_tao/he_thong_ro"
mkdir_safe "loc_mau_than_nhan_tao/may_loc_hap_phu"

# 17. Phẫu thuật nội soi – phẫu thuật ít xâm lấn
mkdir_safe "phau_thuat_noi_soi/tower_noi_soi"
mkdir_safe "phau_thuat_noi_soi/bom_co2"
mkdir_safe "phau_thuat_noi_soi/dao_dien_luong_cuc"
mkdir_safe "phau_thuat_noi_soi/camera_4k_3d"

# 18. Ung bướu – xạ trị
mkdir_safe "ung_buou_xa_tri/may_xa_tri_ngoai"
mkdir_safe "ung_buou_xa_tri/xa_phau"
mkdir_safe "ung_buou_xa_tri/he_thong_lap_ke_hoach"
mkdir_safe "ung_buou_xa_tri/may_xa_ap_sat"

# 19. Kiểm soát nhiễm khuẩn – tiệt khuẩn
mkdir_safe "kiem_soat_nhiem_khuan/noi_hap"
mkdir_safe "kiem_soat_nhiem_khuan/may_tiet_trung_plasma"
mkdir_safe "kiem_soat_nhiem_khuan/may_rua_khu_khuan"
mkdir_safe "kiem_soat_nhiem_khuan/tu_say"
mkdir_safe "kiem_soat_nhiem_khuan/tu_uv"

# 20. Xét nghiệm chẩn đoán tại điểm chăm sóc (POCT)
mkdir_safe "poct/test_nhanh"
mkdir_safe "poct/may_duong_huyet"
mkdir_safe "poct/khi_mau_cam_tay"
mkdir_safe "poct/may_xn_tieu_tien"

# 21. CNTT y tế – PACS, HIS, LIS, RIS
mkdir_safe "cntt_y_te/ris_pacs"
mkdir_safe "cntt_y_te/his_emr"
mkdir_safe "cntt_y_te/lis"
mkdir_safe "cntt_y_te/phan_mem_chuyen_dung"
mkdir_safe "cntt_y_te/may_chu_luu_tru"

# 22. Thiết bị y tế gia đình và cộng đồng
mkdir_safe "y_te_gia_dinh_cong_dong/may_do_huyet_ap"
mkdir_safe "y_te_gia_dinh_cong_dong/may_do_duong_huyet"
mkdir_safe "y_te_gia_dinh_cong_dong/thiet_bi_theo_doi_suc_khoe"
mkdir_safe "y_te_gia_dinh_cong_dong/thiet_bi_tram_y_te_xa"

# 23. Trang thiết bị y tế implant – cấy ghép, thay thế
mkdir_safe "implant_cay_ghep/khop_nhan_tao"
mkdir_safe "implant_cay_ghep/stent"
mkdir_safe "implant_cay_ghep/van_tim_nhan_tao"
mkdir_safe "implant_cay_ghep/dung_cu_co_dinh_xuong"
mkdir_safe "implant_cay_ghep/may_tao_nhip_cay"
mkdir_safe "implant_cay_ghep/thuy_tinh_the_nhan_tao"

# 24. Vật tư y tế tiêu hao
mkdir_safe "vat_tu_tieu_hao/bong_gac"
mkdir_safe "vat_tu_tieu_hao/day_truyen_kim"
mkdir_safe "vat_tu_tieu_hao/ong_thong"
mkdir_safe "vat_tu_tieu_hao/gang_tay_bao_cao_su"
mkdir_safe "vat_tu_tieu_hao/khau_trang_y_te"
mkdir_safe "vat_tu_tieu_hao/dung_cu_phau_thuat_mot_lan"

# 25. Thiết bị chuyên dụng khác
mkdir_safe "thiet_bi_khac/ghe_benh_nhan"
mkdir_safe "thiet_bi_khac/giuong_benh"
mkdir_safe "thiet_bi_khac/xe_lan"
mkdir_safe "thiet_bi_khac/giuong_hoi_suc"
mkdir_safe "thiet_bi_khac/dung_cu_tieu_phau"
mkdir_safe "thiet_bi_khac/bo_dung_cu_kham"
mkdir_safe "thiet_bi_khac/thiet_bi_chua_phan_loai"

# Thư mục hệ thống
mkdir_safe "wiki/devices"
mkdir_safe ".cache/extracted"
mkdir_safe ".backup"

# Đếm tổng
TOTAL=$(find "$ROOT" -mindepth 1 -maxdepth 2 -type d | wc -l | tr -d ' ')

echo "✅ $COUNT thư mục mới tạo"
echo "📊 $TOTAL folders ready!"
