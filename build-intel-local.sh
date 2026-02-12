#!/bin/bash
# build-intel-local.sh - 本地构建 Intel x86_64 版本

set -e

# 统一命名（与yml文件一致）
APP_NAME_CN="表格工具"
APP_NAME_EN="excel_tool"
SPEC_FILE="main.spec"
VERSION=${1:-$(git describe --tags --abbrev=0)}

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}🚀 开始本地 Intel 构建流程${NC}"
echo -e "版本: ${GREEN}$VERSION${NC}"
echo ""

# 检查 gh CLI
if ! command -v gh &> /dev/null; then
    echo -e "${RED}❌ 错误: 未安装 GitHub CLI (gh)${NC}"
    echo "安装: brew install gh"
    exit 1
fi

if ! gh auth status &> /dev/null; then
    echo -e "${YELLOW}⚠️  需要登录 GitHub${NC}"
    gh auth login
fi

REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
echo "仓库: $REPO"

# 检查 Release
echo "🔍 检查 GitHub Release $VERSION..."
if ! gh release view "$VERSION" &> /dev/null; then
    echo -e "${RED}❌ Release $VERSION 不存在${NC}"
    echo "请先推送 tag: git push origin $VERSION"
    exit 1
fi

# 检查是否已存在 Intel 版本
if gh release view "$VERSION" --json assets -q '.assets[].name' | grep -q "_Intel"; then
    echo -e "${YELLOW}⚠️  Intel 版本已存在${NC}"
    read -p "覆盖? (y/n): " confirm
    [[ $confirm != "y" ]] && exit 0
fi

# 清理
echo "🧹 清理旧构建..."
rm -rf build dist build-intel dist-intel venv-intel || true
mkdir -p dist-intel

# 检测架构
CURRENT_ARCH=$(uname -m)
USE_ROSETTA=false
if [ "$CURRENT_ARCH" == "arm64" ]; then
    echo -e "${YELLOW}⚠️  Apple Silicon 检测，将使用 Rosetta 2${NC}"
    USE_ROSETTA=true
    if ! /usr/bin/pgrep oahd &> /dev/null; then
        echo "安装 Rosetta 2..."
        softwareupdate --install-rosetta --agree-to-license
    fi
else
    echo -e "${GREEN}✅ Intel Mac 检测${NC}"
fi

# 创建虚拟环境
echo "🐍 创建虚拟环境..."
if [ "$USE_ROSETTA" == "true" ]; then
    arch -x86_64 /usr/bin/python3 -m venv venv-intel
else
    python3 -m venv venv-intel
fi

source venv-intel/bin/activate

# 安装依赖
echo "📦 安装依赖..."
if [ "$USE_ROSETTA" == "true" ]; then
    arch -x86_64 pip install --upgrade pip setuptools wheel
    arch -x86_64 pip install -r requirements.txt
else
    pip install --upgrade pip setuptools wheel
    pip install -r requirements.txt
fi

# 验证
echo "🔍 验证安装..."
python -c "from PyQt5 import QtCore; print(f'✓ PyQt5 {QtCore.PYQT_VERSION_STR}')"
python -c "import PyInstaller; print(f'✓ PyInstaller {PyInstaller.__version__}')"

# 注入配置
echo "⚙️  注入配置..."
if [ -f ".env.local" ]; then
    export $(grep -v '^#' .env.local | xargs)
elif [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

if [ -f "config/config.ini.template" ]; then
    cp config/config.ini.template config/config.ini
    sed -i '' "s/{{DB_HOST}}/${DB_HOST:-localhost}/g" config/config.ini
    sed -i '' "s/{{DB_PORT}}/${DB_PORT:-3306}/g" config/config.ini
    sed -i '' "s/{{DB_USER}}/${DB_USER:-root}/g" config/config.ini
    sed -i '' "s/{{DB_PASSWORD}}/${DB_PASSWORD:-}/g" config/config.ini
    sed -i '' "s/{{DB_NAME}}/${DB_NAME:-test}/g" config/config.ini
fi

# 修改 spec（统一中文名）
echo "📝 配置 spec (x86_64)..."
cp "$SPEC_FILE" "${SPEC_FILE}.backup"

sed -i '' "s/name='main'/name='main'/g" "$SPEC_FILE"
sed -i '' "s/target_arch=None/target_arch='x86_64'/" "$SPEC_FILE"
sed -i '' "s|entitlements_file=None|entitlements_file='entitlements.plist'|" "$SPEC_FILE"

# 构建
echo -e "${BLUE}🔨 开始构建 (约 5-10 分钟)...${NC}"
START_TIME=$(date +%s)

if [ "$USE_ROSETTA" == "true" ]; then
    arch -x86_64 pyinstaller --noconfirm --distpath dist-intel "$SPEC_FILE"
else
    pyinstaller --noconfirm --distpath dist-intel "$SPEC_FILE"
fi

END_TIME=$(date +%s)
echo "构建耗时: $((END_TIME - START_TIME)) 秒"

# 验证架构
BINARY="dist-intel/${APP_NAME_CN}.app/Contents/MacOS/main"
echo "🔍 验证架构..."
file "$BINARY"
if ! file "$BINARY" | grep -q "x86_64"; then
    echo -e "${RED}❌ 架构验证失败!${NC}"
    mv "${SPEC_FILE}.backup" "$SPEC_FILE"
    exit 1
fi
echo -e "${GREEN}✅ x86_64 验证通过${NC}"

# ==========================================
# 创建 DMG 安装包（修复参数）
# ==========================================
echo "📦 创建 DMG 安装包..."

cd dist-intel

# 检查并安装 create-dmg
if ! command -v create-dmg &> /dev/null; then
    echo "安装 create-dmg..."
    brew install create-dmg
fi

DMG_NAME="${APP_NAME_EN}_Intel.dmg"
VOL_NAME="${APP_NAME_CN} Intel"

echo "正在生成 DMG..."

if create-dmg \
  --volname "$VOL_NAME" \
  --window-pos 200 120 \
  --window-size 800 500 \
  --icon-size 100 \
  --app-drop-link 550 200 \
  --hide-extension "${APP_NAME_CN}.app" \
  --format UDZO \
  --skip-jenkins \
  "$DMG_NAME" \
  "${APP_NAME_CN}.app" 2>/dev/null; then

    echo -e "${GREEN}✅ DMG 创建成功${NC}"
    mv "$DMG_NAME" "../$DMG_NAME"
    cd ..
    FILE_PATH="$DMG_NAME"
    FILE_SIZE=$(du -h "$FILE_PATH" | cut -f1)
    FILE_TYPE="DMG"

else
    echo -e "${YELLOW}⚠️  DMG 创建失败，回退到 ZIP...${NC}"
    ZIP_NAME="${APP_NAME_EN}_Intel.zip"
    ditto -c -k --keepParent "${APP_NAME_CN}.app" "../$ZIP_NAME"
    cd ..
    FILE_PATH="$ZIP_NAME"
    FILE_SIZE=$(du -h "$FILE_PATH" | cut -f1)
    FILE_TYPE="ZIP"
fi

echo -e "${GREEN}✅ 打包完成: $FILE_PATH ($FILE_SIZE) [$FILE_TYPE]${NC}"

# ==========================================
# 上传到 GitHub
# ==========================================
echo -e "${BLUE}📤 上传到 GitHub Release...${NC}"
gh release upload "$VERSION" "$FILE_PATH" --clobber --repo "$REPO"
echo -e "${GREEN}✅ 上传完成${NC}"

# 恢复 spec
mv "${SPEC_FILE}.backup" "$SPEC_FILE"

# ==========================================
# 更新 Release 描述（精确匹配yml格式）
# ==========================================
echo "📝 更新 Release 描述..."

# 获取当前 body
BODY=$(gh release view "$VERSION" --json body -q .body)

# 精确匹配yml中的表格行格式
# 原表格行：| **macOS** | Intel (x86_64) | ⏳ 等待本地构建 | - |
# 要替换为：| **macOS** | Intel (x86_64) | ✅ 已完成 | $FILE_SIZE |

# 使用精确匹配（注意空格）
TABLE_PATTERN="| \\*\\*macOS\\*\\* | Intel (x86_64) | ⏳ 等待本地构建 | - |"
TABLE_REPLACEMENT="| **macOS** | Intel (x86_64) | ✅ 已完成 | $FILE_SIZE |"

echo "正在替换表格状态..."
# 方法1：使用#作为分隔符避免转义问题
NEW_BODY=$(echo "$BODY" | sed "s#${TABLE_PATTERN}#${TABLE_REPLACEMENT}#g")

# 如果精确匹配失败，尝试更灵活的匹配
if echo "$NEW_BODY" | grep -q "⏳ 等待本地构建"; then
    echo "使用备用表格替换方法..."
    NEW_BODY=$(echo "$BODY" | sed "s#⏳ 等待本地构建 | -#✅ 已完成 | $FILE_SIZE#g")
fi

# 替换下载链接描述（精确匹配yml中的文本）
DOWNLOAD_PATTERN="⏳ 请等待 Intel 版本上传..."
FILE_TYPE_LOWER=$(echo "$FILE_TYPE" | tr '[:upper:]' '[:lower:]')
DOWNLOAD_REPLACEMENT="**Intel Mac**: [$APP_NAME_EN\_Intel.$FILE_TYPE_LOWER](https://github.com/$REPO/releases/download/$VERSION/$APP_NAME_EN\_Intel.$FILE_TYPE_LOWER)"

echo "正在替换下载链接..."
NEW_BODY=$(echo "$NEW_BODY" | sed "s#${DOWNLOAD_PATTERN}#${DOWNLOAD_REPLACEMENT}#g")

# 如果上面的精确匹配失败，尝试其他可能的文本格式
if echo "$NEW_BODY" | grep -q "请等待 Intel 版本上传"; then
    echo "使用备用下载链接替换..."
    NEW_BODY=$(echo "$NEW_BODY" | sed "s|请等待 Intel 版本上传|**Intel Mac**: [$APP_NAME_EN\_Intel.$FILE_TYPE_LOWER](https://github.com/$REPO/releases/download/$VERSION/$APP_NAME_EN\_Intel.$FILE_TYPE_LOWER)|g")
fi

# 验证替换结果
echo -e "${GREEN}✅ 替换完成，验证结果...${NC}"
echo "======================================"
echo "$NEW_BODY" | grep -A5 -B5 "Intel" || true
echo "======================================"

# 更新 release
echo "$NEW_BODY" > /tmp/release_body.txt
gh release edit "$VERSION" --notes-file /tmp/release_body.txt --repo "$REPO"

echo -e "${GREEN}✅ Release 描述已更新${NC}"

# ==========================================
# 检查是否发布正式版（修复：在上传后检查）
# ==========================================
echo "🔍 检查是否可以发布正式版..."

# 重新获取 assets（确保包含刚上传的）
ASSETS=$(gh release view "$VERSION" --json assets -q '.assets[].name' 2>/dev/null || echo "")

APPLE_SILICON_EXISTS=$(echo "$ASSETS" | grep -c "_AppleSilicon" || echo "0")
INTEL_EXISTS=$(echo "$ASSETS" | grep -c "_Intel" || echo "0")

echo "检测到 Assets:"
echo "  - Apple Silicon: $APPLE_SILICON_EXISTS"
echo "  - Intel: $INTEL_EXISTS"

if [ "$APPLE_SILICON_EXISTS" -gt 0 ] && [ "$INTEL_EXISTS" -gt 0 ]; then
    echo ""
    echo -e "${GREEN}🎉 双架构版本都已上传！${NC}"

    # 检查是否已经是正式版（非 draft）
    IS_DRAFT=$(gh release view "$VERSION" --json isDraft -q '.isDraft')

    if [ "$IS_DRAFT" == "true" ]; then
        read -p "是否发布正式版? (y/n): " publish
        if [[ "$publish" == "y" ]]; then
            gh release edit "$VERSION" --draft=false --repo "$REPO"
            echo -e "${GREEN}✅ 已发布正式版！${NC}"
        else
            echo "保持 Draft 状态，稍后手动发布"
        fi
    else
        echo "已经是正式版"
    fi
else
    echo ""
    echo -e "${YELLOW}⏳ 等待另一个架构版本...${NC}"
    if [ "$APPLE_SILICON_EXISTS" -eq 0 ]; then
        echo "  - 缺少 Apple Silicon 版本"
    fi
    if [ "$INTEL_EXISTS" -eq 0 ]; then
        echo "  - 缺少 Intel 版本"
    fi
fi

# 清理
deactivate
rm -rf venv-intel

echo ""
echo -e "${GREEN}🎉 本地 Intel 构建流程完成！${NC}"
echo -e "🔗 ${CYAN}https://github.com/$REPO/releases/tag/$VERSION${NC}"

# 打开浏览器
open "https://github.com/$REPO/releases/tag/$VERSION" 2>/dev/null || true