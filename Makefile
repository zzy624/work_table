# Makefile - 表格生成工具

APP_NAME_CN := 表格生成工具
APP_NAME_EN := excel_tool
APP := excel_tool
VERSION := $(shell git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.1")
ICON_SRC := res/$(APP).png
ICONSET := $(APP).iconset
SHELL := /bin/bash

# 虚拟环境路径
VENV_DIR := venv
PYTHON_VENV := $(VENV_DIR)/bin/python
PIP_VENV := $(VENV_DIR)/bin/pip
PYINSTALLER_VENV := $(VENV_DIR)/bin/pyinstaller
PYUIC5_VENV := $(VENV_DIR)/bin/pyuic5
PYRCC5_VENV := $(VENV_DIR)/bin/pyrcc5

# 检测当前平台
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
    PLATFORM := macos
else ifeq ($(UNAME_S),Linux)
    PLATFORM := linux
else
    PLATFORM := windows
endif

# 颜色定义
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
CYAN := \033[0;36m
NC := \033[0m

.DEFAULT_GOAL := help

.PHONY: help pyui qrc builds icon clean clean-all install run status view-release info \
        setup check build-intel build-version \
        release release-auto release-manual wait-actions venv venv-activate \
        fix-setuptools fix-numpy quick-fix fix-python312 setup-python312 \
        check-python-version fix-pyinstaller generate-spec check-pyinstaller

help:
	@printf "$(BLUE)🛠️  $(APP_NAME_CN) 构建工具$(NC)\n\n"
	@printf "$(CYAN)【虚拟环境】$(NC)\n"
	@printf "  make venv          创建/更新虚拟环境\n"
	@printf "  make install       安装依赖包\n\n"
	@printf "$(CYAN)【问题修复】$(NC)\n"
	@printf "  make quick-fix     快速修复 numpy 问题\n"
	@printf "  make fix-python312 修复 Python 3.12 问题\n"
	@printf "  make fix-pyinstaller 修复 PyInstaller\n"
	@printf "  make generate-spec 生成新的 spec 文件\n\n"
	@printf "$(CYAN)【UI/资源构建】$(NC)\n"
	@printf "  make pyui          编译 UI 文件\n"
	@printf "  make qrc           编译资源文件\n"
	@printf "  make icon          生成 macOS icns 图标\n"
	@printf "  make builds        本地快速构建\n\n"
	@printf "$(CYAN)【发布流程】$(NC)\n"
	@printf "  make release       智能发布 (推荐)\n"
	@printf "  make release-auto  全自动发布\n"
	@printf "  make release-manual手动发布\n"
	@printf "  make build-intel   仅构建 Intel (当前 tag: %s)\n" "$(VERSION)"
	@printf "  make build-version V=v1.0.0  指定版本\n"
	@printf "  make wait-actions  监控 GitHub Actions\n\n"
	@printf "$(CYAN)【环境管理】$(NC)\n"
	@printf "  make setup         初始化环境\n"
	@printf "  make check         检查环境\n"
	@printf "  make clean         清理构建产物\n"
	@printf "  make run           运行程序\n"
	@printf "  make status        查看 Actions 状态\n"
	@printf "  make view-release  查看最新发布\n"
	@printf "  make info          显示项目信息\n\n"

# ==================== 环境修复 ====================
venv:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		printf "$(BLUE)🔧 创建虚拟环境...$(NC)\n"; \
		python3 -m venv $(VENV_DIR); \
		printf "$(GREEN)✅ 虚拟环境创建完成$(NC)\n"; \
	fi

install: venv
	@printf "$(BLUE)📦 安装依赖包...$(NC)\n"
	@$(PIP_VENV) install --upgrade pip setuptools wheel
	@$(PIP_VENV) install -r requirements.txt
	@printf "$(GREEN)✅ 依赖安装完成$(NC)\n"

fix-pyinstaller: venv
	@printf "$(BLUE)🔧 修复 PyInstaller...$(NC)\n"
	@$(PIP_VENV) uninstall -y pyinstaller 2>/dev/null || true
	@$(PIP_VENV) install pyinstaller==5.13.0
	@printf "$(GREEN)✅ PyInstaller 修复完成$(NC)\n"

quick-fix: venv
	@printf "$(BLUE)🔧 快速修复...$(NC)\n"
	@$(PIP_VENV) install --upgrade pip setuptools wheel
	@$(PIP_VENV) install numpy==1.24.3
	@$(PIP_VENV) install pyinstaller==5.13.0
	@printf "$(GREEN)✅ 快速修复完成$(NC)\n"

fix-python312: venv
	@printf "$(BLUE)🔧 修复 Python 3.12 问题...$(NC)\n"
	@$(PIP_VENV) install --upgrade pip
	@$(PIP_VENV) install setuptools==69.0.0
	@$(PIP_VENV) install numpy==1.24.3
	@printf "$(GREEN)✅ Python 3.12 修复完成$(NC)\n"

# ==================== UI/资源编译 ====================
pyui: venv
	@printf "$(BLUE)🎨 编译 UI 文件...$(NC)\n"
	@mkdir -p ./ui/pyui
	@if [ -f "./skin/config.ui" ]; then \
		$(PYUIC5_VENV) -o ./ui/pyui/ui_config.py ./skin/config.ui 2>/dev/null || printf "$(YELLOW)⚠️  config.ui 编译失败$(NC)\n"; \
	fi
	@if [ -f "./skin/main.ui" ]; then \
		$(PYUIC5_VENV) -o ./ui/pyui/ui_main.py ./skin/main.ui 2>/dev/null || printf "$(YELLOW)⚠️  main.ui 编译失败$(NC)\n"; \
	fi
	@printf "$(GREEN)✅ UI 编译完成$(NC)\n"

qrc: venv
	@printf "$(BLUE)🎨 编译资源文件...$(NC)\n"
	@mkdir -p ./ui/pyui
	@if [ -f "./res/icon.qrc" ]; then \
		$(PYRCC5_VENV) -o ./ui/pyui/icon_rc.py ./res/icon.qrc 2>/dev/null || printf "$(YELLOW)⚠️  icon.qrc 编译失败$(NC)\n"; \
	fi
	@printf "$(GREEN)✅ 资源编译完成$(NC)\n"

icon: ICONSET
	@printf "$(BLUE)🎨 生成 icns 图标...$(NC)\n"
	@if command -v iconutil >/dev/null 2>&1 && [ -d "$(ICONSET)" ]; then \
		iconutil -c icns $(ICONSET) -o res/$(APP).icns 2>/dev/null || printf "$(YELLOW)⚠️  icns 生成失败$(NC)\n"; \
		rm -rf $(ICONSET); \
	else \
		printf "$(YELLOW)⚠️  跳过图标生成 (非 macOS 或无图标集)$(NC)\n"; \
	fi
	@printf "$(GREEN)✅ 图标处理完成$(NC)\n"

ICONSET:
	@if [ "$(PLATFORM)" = "macos" ] && [ -f "$(ICON_SRC)" ]; then \
		printf "$(BLUE)📦 生成图标集...$(NC)\n"; \
		mkdir -p $(ICONSET); \
		sips -z 16 16     $(ICON_SRC) --out $(ICONSET)/icon_16x16.png 2>/dev/null || true; \
		sips -z 32 32     $(ICON_SRC) --out $(ICONSET)/icon_16x16@2x.png 2>/dev/null || true; \
		sips -z 32 32     $(ICON_SRC) --out $(ICONSET)/icon_32x32.png 2>/dev/null || true; \
		sips -z 64 64     $(ICON_SRC) --out $(ICONSET)/icon_32x32@2x.png 2>/dev/null || true; \
		sips -z 128 128   $(ICON_SRC) --out $(ICONSET)/icon_128x128.png 2>/dev/null || true; \
		sips -z 256 256   $(ICON_SRC) --out $(ICONSET)/icon_128x128@2x.png 2>/dev/null || true; \
		sips -z 256 256   $(ICON_SRC) --out $(ICONSET)/icon_256x256.png 2>/dev/null || true; \
		sips -z 512 512   $(ICON_SRC) --out $(ICONSET)/icon_256x256@2x.png 2>/dev/null || true; \
		sips -z 512 512   $(ICON_SRC) --out $(ICONSET)/icon_512x512.png 2>/dev/null || true; \
		sips -z 1024 1024 $(ICON_SRC) --out $(ICONSET)/icon_512x512@2x.png 2>/dev/null || true; \
		printf "$(GREEN)✅ 图标集生成完成$(NC)\n"; \
	else \
		printf "$(YELLOW)⚠️  跳过图标集生成$(NC)\n"; \
	fi

# ==================== 构建 ====================
generate-spec: venv
	@printf "$(BLUE)📝 生成 spec 文件...$(NC)\n"
	@if [ -f "main.spec" ]; then \
		mv main.spec main.spec.backup.$$(date +%s); \
		printf "$(YELLOW)已备份原文件$(NC)\n"; \
	fi
	@$(PYINSTALLER_VENV) --noconfirm --windowed --icon=res/$(APP).icns --name="$(APP)" main.py 2>/dev/null || \
		$(PYINSTALLER_VENV) --noconfirm --windowed --name="$(APP)" main.py 2>/dev/null || \
		printf "$(RED)❌ spec 文件生成失败$(NC)\n"
	@if [ -f "$(APP).spec" ]; then \
		mv $(APP).spec main.spec; \
		printf "$(GREEN)✅ spec 文件生成完成$(NC)\n"; \
	else \
		printf "$(YELLOW)⚠️  未生成 spec 文件$(NC)\n"; \
	fi

builds: venv install icon
	@printf "$(BLUE)🚀 开始本地构建...$(NC)\n"

	# 确保环境正常
	@if ! $(PYINSTALLER_VENV) --version >/dev/null 2>&1; then \
		printf "$(YELLOW)安装 PyInstaller...$(NC)\n"; \
		$(PIP_VENV) install pyinstaller==5.13.0; \
	fi

	# 生成或使用 spec 文件
	@if [ ! -f "main.spec" ]; then \
		printf "$(YELLOW)生成 spec 文件...$(NC)\n"; \
		$(MAKE) generate-spec; \
	fi

	# 清理并构建
	@rm -rf build dist || true
	@printf "$(BLUE)执行构建...$(NC)\n"
	@if $(PYINSTALLER_VENV) --noconfirm main.spec; then \
		printf "$(GREEN)✅ 构建成功!$(NC)\n"; \
		printf "$(GREEN)📦 输出目录: dist/$(NC)\n"; \
		ls -lh dist/; \
		\
		if [ "$(PLATFORM)" = "macos" ]; then \
			if [ -d "dist/$(APP_NAME_CN).app" ]; then \
				printf "\n$(YELLOW)💡 测试: open dist/$(APP_NAME_CN).app$(NC)\n"; \
			elif [ -d "dist/$(APP).app" ]; then \
				printf "\n$(YELLOW)💡 测试: open dist/$(APP).app$(NC)\n"; \
			fi \
		fi \
	else \
		printf "$(RED)❌ 构建失败!$(NC)\n"; \
		exit 1; \
	fi

# ==================== 发布流程 ====================
wait-actions:
	@printf "$(YELLOW)等待 3 秒...$(NC)\n"
	@sleep 3
	@printf "$(YELLOW)获取最新 run-id...$(NC)\n"
	@RUN_ID=$$(gh run list --limit 1 --json databaseId --jq '.[0].databaseId' 2>/dev/null || true); \
	if [ -z "$$RUN_ID" ]; then \
		printf "$(RED)❌ 未找到运行中的 workflow$(NC)\n"; \
		exit 1; \
	fi; \
	printf "$(CYAN)监控 run-id: $$RUN_ID$(NC)\n"; \
	gh run watch $$RUN_ID --exit-status

release:
	@printf "$(BLUE)🚀 智能发布模式$(NC)\n"
	@printf "版本: $(GREEN)%s$(NC)\n\n" "$(VERSION)"
	@if [ "$(VERSION)" = "v0.0.1" ]; then \
		printf "$(RED)❌ 请先创建 git tag$(NC)\n"; \
		exit 1; \
	fi
	@printf "$(BLUE)步骤 1/2: 检查 GitHub Actions 状态...$(NC)\n"
	@if gh release view $(VERSION) >/dev/null 2>&1 && \
		gh release view $(VERSION) --json assets -q '.assets[].name' 2>/dev/null | grep -q "_AppleSilicon"; then \
		printf "$(GREEN)✅ ARM64 版本已存在，跳过等待$(NC)\n"; \
	else \
		git push origin $(VERSION) 2>/dev/null || true; \
		printf "\n$(YELLOW)⏳ 等待 ARM64 构建...$(NC)\n"; \
		$(MAKE) wait-actions || exit 1; \
		printf "\n$(GREEN)✅ ARM64 完成!$(NC)\n"; \
	fi
	@printf "\n$(BLUE)步骤 2/2: 本地构建 Intel...$(NC)\n"
	@$(MAKE) build-intel

release-auto:
	@printf "$(BLUE)🚀 全自动发布模式$(NC)\n"
	@printf "版本: $(GREEN)%s$(NC)\n\n" "$(VERSION)"
	@if [ "$(VERSION)" = "v0.0.1" ]; then \
		printf "$(RED)❌ 请先创建 git tag$(NC)\n"; \
		exit 1; \
	fi
	@git push origin $(VERSION) 2>/dev/null || true
	@printf "\n$(YELLOW)⏳ 等待 GitHub Actions...$(NC)\n"
	@$(MAKE) wait-actions || exit 1
	@printf "\n$(GREEN)✅ ARM64 成功!$(NC)\n"
	@$(MAKE) build-intel

release-manual:
	@printf "$(BLUE)🚀 手动发布模式$(NC)\n"
	@if [ "$(VERSION)" = "v0.0.1" ]; then \
		printf "$(RED)❌ 请先创建 git tag$(NC)\n"; \
		exit 1; \
	fi
	@git push origin $(VERSION) 2>/dev/null || true
	@printf "$(GREEN)✅ 已触发 GitHub Actions$(NC)\n"
	@printf "$(YELLOW)等待 Actions 完成后手动构建 Intel 版本...$(NC)\n"
	@printf "请使用: make build-intel\n"

build-intel:
	@printf "$(BLUE)🚀 构建 Intel 版本...$(NC)\n"
	@printf "$(BLUE)版本: $(GREEN)%s$(NC)\n" "$(VERSION)"
	@if [ "$(VERSION)" = "v0.0.1" ]; then \
		printf "$(YELLOW)⚠️  未检测到 git tag$(NC)\n"; \
		read -p "继续? (y/n): " confirm; \
		[ "$$confirm" != "y" ] && exit 1; \
	fi
	@if [ -f "build-intel-local.sh" ]; then \
		./build-intel-local.sh $(VERSION); \
	else \
		printf "$(YELLOW)⚠️  build-intel-local.sh 不存在，使用本地构建替代$(NC)\n"; \
		$(MAKE) builds; \
	fi

build-version:
	@if [ -z "$(V)" ]; then \
		printf "$(RED)❌ 请指定版本: make build-version V=v1.0.0$(NC)\n"; \
		exit 1; \
	fi
	@if [ -f "build-intel-local.sh" ]; then \
		./build-intel-local.sh $(V); \
	else \
		printf "$(YELLOW)⚠️  build-intel-local.sh 不存在，使用本地构建替代$(NC)\n"; \
		$(MAKE) builds; \
	fi

# ==================== 环境管理 ====================
setup:
	@printf "$(BLUE)🔧 初始化环境...$(NC)\n"
	@if [ ! -f "build-intel-local.sh" ]; then \
		printf "$(YELLOW)创建 build-intel-local.sh...$(NC)\n"; \
		echo '#!/bin/bash' > build-intel-local.sh; \
		echo '# Intel Mac 本地构建脚本' >> build-intel-local.sh; \
		echo 'echo "Intel 构建脚本 - 请根据实际需求完善"' >> build-intel-local.sh; \
		chmod +x build-intel-local.sh; \
	fi
	@chmod +x build-intel-local.sh 2>/dev/null || true
	@if ! command -v gh >/dev/null 2>&1; then \
		printf "$(YELLOW)安装 GitHub CLI...$(NC)\n"; \
		if [ "$(PLATFORM)" = "macos" ]; then \
			brew install gh || printf "$(RED)❌ 安装失败，请手动安装$(NC)\n"; \
		else \
			printf "$(YELLOW)请手动安装 GitHub CLI$(NC)\n"; \
		fi \
	fi
	@if ! gh auth status >/dev/null 2>&1; then \
		printf "$(YELLOW)请登录 GitHub CLI$(NC)\n"; \
		printf "$(CYAN)运行: gh auth login$(NC)\n"; \
	fi
	@printf "$(GREEN)✅ 环境初始化完成$(NC)\n"

check:
	@printf "$(BLUE)🔍 环境检查$(NC)\n"
	@printf "最新 Tag: $(GREEN)%s$(NC)\n" "$(VERSION)"
	@printf "平台: $(GREEN)$(PLATFORM)$(NC)\n"
	@[ -d "$(VENV_DIR)" ] && printf "  ✅ 虚拟环境\n" || printf "  ❌ 虚拟环境\n"
	@[ -f "main.spec" ] && printf "  ✅ spec 文件\n" || printf "  ❌ spec 文件\n"
	@[ -f "res/$(APP).icns" ] && printf "  ✅ 应用图标\n" || printf "  ❌ 应用图标\n"
	@command -v gh >/dev/null 2>&1 && printf "  ✅ GitHub CLI\n" || printf "  ❌ GitHub CLI\n"
	@[ -f "build-intel-local.sh" ] && printf "  ✅ Intel 构建脚本\n" || printf "  ❌ Intel 构建脚本\n"

clean:
	@printf "$(BLUE)🧹 清理...$(NC)\n"
	@rm -rf build dist __pycache__ *.spec.backup*
	@rm -rf $(ICONSET)
	@find . -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@printf "$(GREEN)✅ 清理完成$(NC)\n"

clean-all: clean
	@rm -rf $(VENV_DIR) venv-intel .venv
	@printf "$(GREEN)✅ 完全清理完成$(NC)\n"

run: venv
	@printf "$(BLUE)🚀 运行应用...$(NC)\n"
	@$(PYTHON_VENV) main.py

status:
	@printf "$(BLUE)📊 GitHub Actions 状态$(NC)\n"
	@gh run list --limit 5

view-release:
	@printf "$(BLUE)📦 查看最新发布$(NC)\n"
	@open "https://github.com/$$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo 'owner/repo')/releases/latest" 2>/dev/null || \
		printf "$(YELLOW)请手动打开发布页面$(NC)\n"

info:
	@printf "$(BLUE)📋 项目信息$(NC)\n"
	@printf "  中文名: %s\n" "$(APP_NAME_CN)"
	@printf "  英文名: %s\n" "$(APP_NAME_EN)"
	@printf "  版本:   %s\n" "$(VERSION)"
	@printf "  平台:   %s\n" "$(PLATFORM)"
	@REPO=$$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "未连接 GitHub"); \
	printf "  GitHub: %s\n" "$$REPO"