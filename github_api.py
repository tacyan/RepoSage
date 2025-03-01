#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
GitHub API 操作モジュール

このモジュールは GitHub API を使用してリポジトリ情報を取得するための関数を提供します。
主な機能:
- リポジトリ URL の解析
- リポジトリ情報の取得
- コントリビューター情報の取得
- ファイルツリーの取得
- ファイル内容の取得
"""

import os
import re
import base64
import httpx
import time
import json
from typing import Dict, List, Optional, Any, Tuple
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# GitHub API の設定
GITHUB_API_URL = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# HTTPクライアントの設定
headers = {
    "Accept": "application/vnd.github.v3+json"
}

if GITHUB_TOKEN:
    headers["Authorization"] = f"token {GITHUB_TOKEN}"

"""
GitHub API 関連の関数
"""

def parseRepoUrl(repoUrl: str) -> Optional[Dict[str, str]]:
    """
    GitHub リポジトリ URL を解析し、所有者とリポジトリ名を抽出します。
    
    @param repoUrl - GitHub リポジトリの URL
    @return 所有者とリポジトリ名を含む辞書、または無効な URL の場合は None
    """
    if not repoUrl:
        return None
        
    # GitHub URL のパターン
    pattern = r"github\.com[:/]([^/]+)/([^/]+)"
    match = re.search(pattern, repoUrl)
    
    if match:
        owner = match.group(1)
        repo = match.group(2)
        
        # .git 拡張子がある場合は削除
        if repo.endswith(".git"):
            repo = repo[:-4]
            
        return {
            "owner": owner,
            "repo": repo
        }
    
    return None

async def getDefaultBranch(repoInfo: Dict[str, str]) -> str:
    """
    リポジトリのデフォルトブランチを取得します。
    
    @param repoInfo - リポジトリ情報（所有者とリポジトリ名）
    @return デフォルトブランチ名
    """
    if not repoInfo or "owner" not in repoInfo or "repo" not in repoInfo:
        return "main"
        
    owner = repoInfo["owner"]
    repo = repoInfo["repo"]
    
    try:
        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            response = await client.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}")
            response.raise_for_status()
            data = response.json()
            
            return data.get("default_branch", "main")
    except Exception as e:
        print(f"デフォルトブランチの取得に失敗しました: {str(e)}")
        return "main"  # デフォルト値として "main" を返す

async def getRepositoryInfo(repoUrl: str) -> Dict[str, Any]:
    """
    リポジトリの詳細情報を取得します。
    
    @param repoUrl - GitHub リポジトリの URL
    @return リポジトリの詳細情報
    """
    repoInfo = parseRepoUrl(repoUrl)
    if not repoInfo:
        return {
            "name": "unknown",
            "owner": {"login": "unknown"},
            "description": "無効なGitHub URLです。",
            "language": "不明",
            "stargazers_count": 0,
            "forks_count": 0,
            "subscribers_count": 0,
            "open_issues_count": 0,
            "created_at": "",
            "updated_at": ""
        }
    
    owner = repoInfo["owner"]
    repo = repoInfo["repo"]
    
    try:
        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            response = await client.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}")
            response.raise_for_status()
            
            return response.json()
    except Exception as e:
        print(f"リポジトリ情報の取得に失敗しました: {str(e)}")
        # 基本的な情報を含むダミーデータを返す
        return {
            "name": repo,
            "owner": {"login": owner},
            "description": "情報を取得できませんでした",
            "language": "不明",
            "stargazers_count": 0,
            "forks_count": 0,
            "subscribers_count": 0,
            "open_issues_count": 0,
            "created_at": "",
            "updated_at": ""
        }

async def getRepositoryContributors(repoUrl: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    リポジトリのコントリビューター情報を取得します。
    
    @param repoUrl - GitHub リポジトリの URL
    @param limit - 取得するコントリビューターの最大数
    @return コントリビューター情報のリスト
    """
    repoInfo = parseRepoUrl(repoUrl)
    if not repoInfo:
        return [{
            "login": "unknown",
            "contributions": 0,
            "avatar_url": ""
        }]
    
    owner = repoInfo["owner"]
    repo = repoInfo["repo"]
    
    try:
        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            response = await client.get(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/contributors",
                params={"per_page": limit}
            )
            response.raise_for_status()
            
            return response.json()
    except Exception as e:
        print(f"コントリビューター情報の取得に失敗しました: {str(e)}")
        # 所有者をコントリビューターとして返す
        return [{
            "login": owner,
            "contributions": 1,
            "avatar_url": ""
        }]

async def getRepoTree(repoInfo: Dict[str, str], branch: str) -> List[Dict[str, Any]]:
    """
    リポジトリのファイルツリーを取得します。
    
    @param repoInfo - リポジトリ情報（所有者とリポジトリ名）
    @param branch - ブランチ名
    @return ファイルツリー情報
    """
    if not repoInfo or "owner" not in repoInfo or "repo" not in repoInfo:
        return []
        
    owner = repoInfo["owner"]
    repo = repoInfo["repo"]
    
    try:
        async with httpx.AsyncClient(headers=headers, timeout=60.0) as client:
            # リポジトリのルートツリーを取得
            response = await client.get(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/trees/{branch}",
                params={"recursive": "1"}
            )
            response.raise_for_status()
            data = response.json()
            
            # APIレート制限に達した場合
            if response.status_code == 403 and "API rate limit exceeded" in response.text:
                print("GitHub API レート制限に達しました。しばらく待ってから再試行してください。")
                return []
                
            # 再帰的に取得できなかった場合（大きなリポジトリの場合）
            if data.get("truncated", False):
                print("リポジトリが大きすぎるため、完全なツリーを取得できませんでした。手動で構築します。")
                return await buildManualTree(client, repoInfo, branch)
            
            return data.get("tree", [])
    except Exception as e:
        print(f"ファイルツリーの取得に失敗しました: {str(e)}")
        # 空のツリーを返す
        return []

async def buildManualTree(client: httpx.AsyncClient, repoInfo: Dict[str, str], branch: str) -> List[Dict[str, Any]]:
    """
    大きなリポジトリのファイルツリーを手動で構築します。
    
    @param client - HTTPクライアント
    @param repoInfo - リポジトリ情報
    @param branch - ブランチ名
    @return ファイルツリー情報
    """
    owner = repoInfo["owner"]
    repo = repoInfo["repo"]
    result = []
    
    # ルートディレクトリの取得
    try:
        response = await client.get(
            f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents",
            params={"ref": branch}
        )
        response.raise_for_status()
        root_items = response.json()
        
        # ルートディレクトリの各アイテムを処理
        for item in root_items:
            if isinstance(item, dict):
                item_type = "tree" if item.get("type") == "dir" else "blob"
                result.append({
                    "path": item.get("path", ""),
                    "type": item_type,
                    "sha": item.get("sha", ""),
                    "size": item.get("size", 0) if item_type == "blob" else 0
                })
                
                # ディレクトリの場合は再帰的に処理
                if item_type == "tree":
                    await processDirectory(client, repoInfo, branch, item.get("path", ""), result)
    except Exception as e:
        print(f"ルートディレクトリの取得に失敗しました: {str(e)}")
    
    return result

async def processDirectory(client: httpx.AsyncClient, repoInfo: Dict[str, str], branch: str, path: str, result: List[Dict[str, Any]]):
    """
    ディレクトリを再帰的に処理します。
    
    @param client - HTTPクライアント
    @param repoInfo - リポジトリ情報
    @param branch - ブランチ名
    @param path - ディレクトリパス
    @param result - 結果リスト
    """
    owner = repoInfo["owner"]
    repo = repoInfo["repo"]
    
    try:
        # APIレート制限を回避するために少し待機
        await asyncio.sleep(0.5)
        
        response = await client.get(
            f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{path}",
            params={"ref": branch}
        )
        response.raise_for_status()
        items = response.json()
        
        for item in items:
            if isinstance(item, dict):
                item_type = "tree" if item.get("type") == "dir" else "blob"
                result.append({
                    "path": item.get("path", ""),
                    "type": item_type,
                    "sha": item.get("sha", ""),
                    "size": item.get("size", 0) if item_type == "blob" else 0
                })
                
                # ディレクトリの場合は再帰的に処理（深さ制限を設ける）
                if item_type == "tree" and path.count("/") < 5:  # 深さ制限
                    await processDirectory(client, repoInfo, branch, item.get("path", ""), result)
    except Exception as e:
        print(f"ディレクトリ {path} の処理に失敗しました: {str(e)}")

async def getFileContent(repoInfo: Dict[str, str], filePath: str, branch: str) -> str:
    """
    ファイルの内容を取得します。
    
    @param repoInfo - リポジトリ情報（所有者とリポジトリ名）
    @param filePath - ファイルパス
    @param branch - ブランチ名
    @return ファイルの内容
    """
    if not repoInfo or "owner" not in repoInfo or "repo" not in repoInfo or not filePath:
        return "// ファイル情報が不完全です"
        
    owner = repoInfo["owner"]
    repo = repoInfo["repo"]
    
    try:
        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            response = await client.get(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{filePath}",
                params={"ref": branch}
            )
            response.raise_for_status()
            data = response.json()
            
            # ディレクトリの場合は空文字列を返す
            if isinstance(data, list):
                return ""
            
            # ファイルの場合は内容をデコード
            if "content" in data:
                content = data["content"]
                # Base64 デコード
                try:
                    decoded_content = base64.b64decode(content).decode("utf-8")
                    return decoded_content
                except UnicodeDecodeError:
                    return "// バイナリファイルのため表示できません"
            
            return ""
    except Exception as e:
        print(f"ファイル内容の取得に失敗しました ({filePath}): {str(e)}")
        return f"// ファイル内容を取得できませんでした: {filePath}"

# 非同期処理のためのモジュールをインポート
import asyncio 