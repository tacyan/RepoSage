#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RepoSage - Hugging Face Spaces エントリーポイント

このファイルは Hugging Face Spaces で RepoSage を実行するためのエントリーポイントです。
"""

import os
import sys
import flet as ft
from main import main

# Hugging Face Spaces 用のエントリーポイント
if __name__ == "__main__":
    try:
        # 環境変数からポートを取得（デフォルトは8080）
        port = int(os.environ.get("PORT", 8080))
        
        # アプリケーションの起動
        print(f"RepoSage を起動しています（ポート: {port}）...")
        ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=port)
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        sys.exit(1) 