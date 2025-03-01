#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
マークダウン生成モジュール

このモジュールはGitHubリポジトリの情報からマークダウン形式のドキュメントを生成するための関数を提供します。
主な機能:
- リポジトリ情報のマークダウン生成
- ファイルツリーのマークダウン生成
- ファイル内容のマークダウン生成
- マークダウンからHTMLへの変換
"""

import os
import re
import markdown
from datetime import datetime
from typing import Dict, List, Any, Optional
from pygments import highlight
from pygments.lexers import get_lexer_for_filename, TextLexer
from pygments.formatters import HtmlFormatter

from github_api import getFileContent, GITHUB_TOKEN
from file_utils import shouldIgnore

def formatDate(dateStr: str) -> str:
    """
    日付文字列をフォーマットします。
    
    @param dateStr - ISO形式の日付文字列
    @return フォーマットされた日付文字列
    """
    if not dateStr:
        return "不明"
    
    try:
        date = datetime.fromisoformat(dateStr.replace("Z", "+00:00"))
        return date.strftime("%Y/%m/%d")
    except:
        return dateStr

def getLanguageFromFilename(filename: str) -> str:
    """
    ファイル名から言語を取得します。
    
    @param filename - ファイル名
    @return 言語名
    """
    try:
        lexer = get_lexer_for_filename(filename)
        return lexer.name
    except:
        # 拡張子から推測
        ext = os.path.splitext(filename)[1].lower()
        
        # 一般的な拡張子のマッピング
        ext_map = {
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".jsx": "React JSX",
            ".tsx": "React TSX",
            ".py": "Python",
            ".rb": "Ruby",
            ".java": "Java",
            ".c": "C",
            ".cpp": "C++",
            ".cs": "C#",
            ".go": "Go",
            ".rs": "Rust",
            ".php": "PHP",
            ".html": "HTML",
            ".css": "CSS",
            ".scss": "SCSS",
            ".md": "Markdown",
            ".json": "JSON",
            ".yml": "YAML",
            ".yaml": "YAML",
            ".xml": "XML",
            ".sh": "Shell",
            ".bat": "Batch",
            ".ps1": "PowerShell"
        }
        
        return ext_map.get(ext, "テキスト")

def generateFileTreeMarkdown(fileTree: Dict[str, Any], indent: int = 0) -> str:
    """
    ファイルツリーのマークダウンを生成します。
    
    @param fileTree - ファイルツリー
    @param indent - インデントレベル
    @return マークダウン形式のファイルツリー
    """
    result = []
    
    # fileTreeがNoneまたは必要なキーがない場合の対応
    if not fileTree or "name" not in fileTree or "type" not in fileTree:
        return "ファイルツリーを取得できませんでした"
    
    # ルートディレクトリの場合
    if fileTree["name"] == "/" and indent == 0:
        children = fileTree.get("children", [])
    else:
        # ディレクトリの場合
        if fileTree["type"] == "directory":
            result.append(f"{' ' * indent}📁 {fileTree['name']}")
            children = fileTree.get("children", [])
        # ファイルの場合
        else:
            result.append(f"{' ' * indent}📄 {fileTree['name']}")
            return "\n".join(result)
    
    # 子要素を処理
    if "children" in fileTree:
        # 名前でソート（ディレクトリが先）
        sorted_children = sorted(
            fileTree["children"],
            key=lambda x: (0 if x.get("type") == "file" else 1, x.get("name", ""))
        )
        
        for child in sorted_children:
            result.append(generateFileTreeMarkdown(child, indent + 2))
    
    return "\n".join(result)

async def generateRepositoryMarkdown(
    repoInfo: Dict[str, str],
    repoDetails: Dict[str, Any],
    contributors: List[Dict[str, Any]],
    fileTree: Dict[str, Any],
    defaultBranch: str,
    ignorePatterns: List[str] = [],
    sourceIgnorePatterns: List[str] = []
) -> str:
    """
    リポジトリのマークダウンを生成します。
    
    @param repoInfo - リポジトリ情報
    @param repoDetails - リポジトリの詳細情報
    @param contributors - コントリビューター情報
    @param fileTree - ファイルツリー
    @param defaultBranch - デフォルトブランチ
    @param ignorePatterns - 無視パターンのリスト
    @param sourceIgnorePatterns - ソースコード内の無視パターンのリスト
    @return マークダウン形式のリポジトリドキュメント
    """
    # repoInfoがNoneまたは必要なキーがない場合の対応
    if not repoInfo or "owner" not in repoInfo or "repo" not in repoInfo:
        return "リポジトリ情報が不完全です。有効なGitHubリポジトリURLを入力してください。"
    
    # repoDetailsがNoneの場合の対応
    if repoDetails is None:
        repoDetails = {}
    
    owner = repoInfo["owner"]
    repo = repoInfo["repo"]
    
    # リポジトリ情報
    markdown = f"# {repo}\n\n"
    
    # リポジトリの説明
    if repoDetails.get("description"):
        markdown += f"## リポジトリ情報\n\n"
        markdown += f"- **説明**: {repoDetails.get('description', '説明なし')}\n"
        markdown += f"- **所有者**: {owner}\n"
        markdown += f"- **主要言語**: {repoDetails.get('language', '不明')}\n"
        
        # licenseがNoneまたは辞書でない場合の対応
        license_info = repoDetails.get('license')
        if isinstance(license_info, dict):
            license_name = license_info.get('name', 'ライセンス情報なし')
        else:
            license_name = 'ライセンス情報なし'
        markdown += f"- **ライセンス**: {license_name}\n"
        
        markdown += f"- **作成日**: {formatDate(repoDetails.get('created_at', ''))}\n"
        markdown += f"- **最終更新日**: {formatDate(repoDetails.get('updated_at', ''))}\n\n"
    
    # 統計情報
    markdown += f"## 統計\n\n"
    markdown += f"- **スター数**: {repoDetails.get('stargazers_count', 0)}\n"
    markdown += f"- **フォーク数**: {repoDetails.get('forks_count', 0)}\n"
    markdown += f"- **ウォッチャー数**: {repoDetails.get('subscribers_count', 0)}\n"
    markdown += f"- **オープンイシュー数**: {repoDetails.get('open_issues_count', 0)}\n"
    markdown += f"- **デフォルトブランチ**: {defaultBranch}\n\n"
    
    # 言語情報（APIから取得できない場合はスキップ）
    if repoDetails.get("language"):
        markdown += f"## 言語詳細\n\n"
        markdown += f"| 言語 | 割合 | バイト数 |\n"
        markdown += f"| --- | --- | --- |\n"
        markdown += f"| {repoDetails.get('language', '不明')} | 100% | 不明 |\n\n"
    
    # コントリビューター情報
    if contributors:
        markdown += f"## コントリビューター\n\n"
        
        for contributor in contributors:
            if not isinstance(contributor, dict):
                continue
                
            login = contributor.get("login", "不明")
            contributions = contributor.get("contributions", 0)
            avatar_url = contributor.get("avatar_url", "")
            
            markdown += f"### {login}\n\n"
            markdown += f"- **コントリビューション数**: {contributions}\n"
            markdown += f"- **プロフィール**: [GitHub](https://github.com/{login})\n\n"
            
            if avatar_url:
                markdown += f"![{login}]({avatar_url})\n\n"
    
    # ファイル構造
    markdown += f"## ファイル構造\n\n"
    
    # ファイルツリーが空でない場合のみ表示
    if fileTree and fileTree.get("children"):
        tree_markdown = generateFileTreeMarkdown(fileTree)
        markdown += f"```\n{tree_markdown}\n```\n\n"
    else:
        markdown += "ファイル構造を取得できませんでした。GitHub API トークンが必要な可能性があります。\n\n"
    
    # 主要ファイルの内容
    markdown += f"## ファイル内容\n\n"
    
    # 重要なファイルを抽出（例: README.md, package.json など）
    important_files = []
    
    def find_important_files(node):
        if not node:
            return
            
        if node.get("type") == "file":
            filename = node.get("name", "").lower()
            if (filename == "readme.md" or
                filename == "package.json" or
                filename == "requirements.txt" or
                filename.endswith(".py") or
                filename.endswith(".js") or
                filename.endswith(".ts")):
                important_files.append(node.get("path", ""))
        elif node.get("type") == "directory" and "children" in node:
            for child in node.get("children", []):
                find_important_files(child)
    
    # ファイルツリーが有効な場合のみ処理
    if fileTree and fileTree.get("children"):
        find_important_files(fileTree)
    
    # 重要なファイルの内容を取得
    if important_files:
        for file_path in important_files[:5]:  # 最大5つのファイルを表示
            if not file_path:
                continue
                
            try:
                content = await getFileContent(repoInfo, file_path, defaultBranch)
                
                # ソースコード内の無視パターンに一致する行をフィルタリング
                if sourceIgnorePatterns and content:
                    lines = content.split("\n")
                    filtered_lines = [line for line in lines if not shouldIgnore(line, sourceIgnorePatterns)]
                    content = "\n".join(filtered_lines)
                
                # ファイル名から言語を取得
                language = getLanguageFromFilename(file_path)
                
                markdown += f"### {file_path}\n\n"
                markdown += f"```{language.lower()}\n{content}\n```\n\n"
            except Exception as e:
                markdown += f"### {file_path}\n\n"
                markdown += f"ファイル内容の取得に失敗しました: {str(e)}\n\n"
    else:
        markdown += "重要なファイルが見つかりませんでした。GitHub API トークンが必要な可能性があります。\n\n"
    
    # GitHub API トークンがない場合の注意書き
    if not GITHUB_TOKEN:
        markdown += "---\n\n"
        markdown += "**注意**: GitHub API トークンが設定されていないため、一部の情報が制限されています。\n"
        markdown += "より詳細な情報を取得するには、GitHub API トークンを設定してください。\n"
    
    return markdown

def convertMarkdownToHtml(markdown_text: str) -> str:
    """
    マークダウンをHTMLに変換します。
    
    @param markdown_text - マークダウンテキスト
    @return HTML形式のテキスト
    """
    # Pygmentsのスタイルシートを取得
    pygments_style = HtmlFormatter().get_style_defs('.codehilite')
    
    # マークダウンをHTMLに変換
    html = markdown.markdown(
        markdown_text,
        extensions=[
            'markdown.extensions.fenced_code',
            'markdown.extensions.tables',
            'markdown.extensions.codehilite'
        ]
    )
    
    # HTMLテンプレート
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>リポジトリドキュメント</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 900px;
                margin: 0 auto;
                padding: 20px;
            }}
            h1, h2, h3, h4, h5, h6 {{
                margin-top: 24px;
                margin-bottom: 16px;
                font-weight: 600;
                line-height: 1.25;
            }}
            h1 {{
                font-size: 2em;
                border-bottom: 1px solid #eaecef;
                padding-bottom: 0.3em;
            }}
            h2 {{
                font-size: 1.5em;
                border-bottom: 1px solid #eaecef;
                padding-bottom: 0.3em;
            }}
            a {{
                color: #0366d6;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
            pre {{
                background-color: #f6f8fa;
                border-radius: 3px;
                padding: 16px;
                overflow: auto;
            }}
            code {{
                font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
                background-color: rgba(27, 31, 35, 0.05);
                border-radius: 3px;
                padding: 0.2em 0.4em;
                font-size: 85%;
            }}
            pre code {{
                background-color: transparent;
                padding: 0;
            }}
            blockquote {{
                margin: 0;
                padding: 0 1em;
                color: #6a737d;
                border-left: 0.25em solid #dfe2e5;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin-bottom: 16px;
            }}
            table th, table td {{
                padding: 6px 13px;
                border: 1px solid #dfe2e5;
            }}
            table tr {{
                background-color: #fff;
                border-top: 1px solid #c6cbd1;
            }}
            table tr:nth-child(2n) {{
                background-color: #f6f8fa;
            }}
            img {{
                max-width: 100%;
                box-sizing: content-box;
            }}
            {pygments_style}
        </style>
    </head>
    <body>
        {html}
    </body>
    </html>
    """
    
    return html_template 