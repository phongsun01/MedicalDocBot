#!/bin/bash

# ============================================================
#  git-push.sh — Generic Git Sync Tool (Mac / Linux)
#  Chức năng: Add → Commit → Pull (rebase) → Push → Tag
#  Cách dùng: ./git-push.sh ["commit message"]
#  Để dùng cho dự án khác: copy file này vào thư mục gốc
#  của dự án rồi chạy: chmod +x git-push.sh && ./git-push.sh
# ============================================================

# --- Màu sắc ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# --- Hàm tiện ích ---
info()    { echo -e "${CYAN}ℹ️  $1${NC}"; }
success() { echo -e "${GREEN}✅ $1${NC}"; }
warn()    { echo -e "${YELLOW}⚠️  $1${NC}"; }
error()   { echo -e "${RED}❌ $1${NC}"; }
header()  { echo -e "\n${BOLD}$1${NC}"; }

# ============================================================
# 0. Kiểm tra thư mục Git
# ============================================================
if [ ! -d ".git" ]; then
    error "Đây không phải là thư mục Git!"
    echo "   → Chạy 'git init' để khởi tạo, hoặc di chuyển đến đúng thư mục."
    exit 1
fi

# ============================================================
# 1. Lấy tên nhánh hiện tại
# ============================================================
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null)
if [ -z "$CURRENT_BRANCH" ]; then
    error "Không xác định được nhánh hiện tại. Có thể repo đang ở trạng thái detached HEAD."
    exit 1
fi
info "Nhánh hiện tại: ${BOLD}$CURRENT_BRANCH${NC}"

# ============================================================
# 2. Kiểm tra remote origin
# ============================================================
if ! git remote get-url origin &>/dev/null; then
    error "Chưa có remote 'origin'. Vui lòng thêm remote trước:"
    echo "   → git remote add origin <URL>"
    exit 1
fi
REMOTE_URL=$(git remote get-url origin)
info "Remote: $REMOTE_URL"

# ============================================================
# 3. Nhập commit message
# ============================================================
COMMIT_MSG="$1"
if [ -z "$COMMIT_MSG" ]; then
    echo ""
    echo -n "📝 Commit message (Enter để dùng mặc định): "
    read COMMIT_MSG
fi

if [ -z "$COMMIT_MSG" ]; then
    COMMIT_MSG="chore: update $(date '+%Y-%m-%d %H:%M')"
fi

# ============================================================
# 4. Git Add
# ============================================================
header "📁 [1/4] Staging thay đổi..."
git add .
if [ $? -ne 0 ]; then
    error "git add thất bại."
    exit 1
fi

# Kiểm tra có gì để commit không
if git diff --cached --quiet; then
    warn "Không có thay đổi nào để commit."
    echo "   → Bỏ qua bước commit và push."
    exit 0
fi

# ============================================================
# 5. Git Commit
# ============================================================
header "📦 [2/4] Committing..."
git commit -m "$COMMIT_MSG"
if [ $? -ne 0 ]; then
    error "git commit thất bại."
    exit 1
fi

# ============================================================
# 6. Git Pull (rebase) — tránh conflict khi push
# ============================================================
header "⬇️  [3/4] Pulling từ remote (rebase)..."
git pull --rebase origin "$CURRENT_BRANCH" 2>/dev/null
PULL_STATUS=$?
if [ $PULL_STATUS -ne 0 ]; then
    warn "git pull --rebase gặp lỗi (có thể nhánh chưa tồn tại trên remote). Tiếp tục push..."
fi

# ============================================================
# 7. Git Push
# ============================================================
header "☁️  [4/4] Pushing lên GitHub..."
git push -u origin "$CURRENT_BRANCH"
if [ $? -ne 0 ]; then
    error "git push thất bại!"
    echo "   → Kiểm tra kết nối mạng, quyền truy cập, hoặc conflict."
    exit 1
fi

echo ""
success "SYNC HOÀN THÀNH! Nhánh '${CURRENT_BRANCH}' đã được đẩy lên remote."

# ============================================================
# 8. Tạo Tag (tùy chọn)
# ============================================================
echo ""
echo -n "🏷️  Tạo Tag cho bản này? (y/N): "
read CREATE_TAG

if [[ "$CREATE_TAG" =~ ^[Yy]$ ]]; then
    # Gợi ý tag tiếp theo dựa trên tag mới nhất
    LATEST_TAG=$(git describe --tags --abbrev=0 2>/dev/null)
    if [ -n "$LATEST_TAG" ]; then
        info "Tag mới nhất hiện tại: $LATEST_TAG"
    fi

    echo -n "📌 Tên Tag (VD: v1.0.0): "
    read TAG_NAME
    if [ -z "$TAG_NAME" ]; then
        warn "Không nhập tên Tag. Bỏ qua."
    else
        echo -n "💬 Mô tả Tag (Enter để dùng commit message): "
        read TAG_MSG
        if [ -z "$TAG_MSG" ]; then
            TAG_MSG="$COMMIT_MSG"
        fi

        git tag -a "$TAG_NAME" -m "$TAG_MSG"
        git push origin "$TAG_NAME"
        if [ $? -eq 0 ]; then
            success "Đã tạo và push Tag: $TAG_NAME"
        else
            error "Push Tag thất bại."
        fi
    fi
fi

echo ""
success "🎉 TẤT CẢ ĐÃ XONG!"
