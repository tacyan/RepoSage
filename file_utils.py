#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ファイル操作ユーティリティモジュール

このモジュールはファイル操作に関するユーティリティ関数を提供します。
主な機能:
- ファイルツリーの構築
- 無視パターンに基づくファイルのフィルタリング
- ファイルパスの処理
"""

import re
import time
from typing import Dict, List, Any, Optional, Set

def shouldIgnore(path: str, ignorePatterns: List[str]) -> bool:
    """
    指定されたパスが無視パターンに一致するかどうかを判定します。
    
    @param path - 判定するパス
    @param ignorePatterns - 無視パターンのリスト
    @return 無視すべき場合はTrue、そうでない場合はFalse
    """
    if not path or not ignorePatterns:
        return False
    
    for pattern in ignorePatterns:
        # パターンが空の場合はスキップ
        if not pattern:
            continue
            
        # ワイルドカードパターンを正規表現に変換
        regex_pattern = pattern.replace(".", "\\.").replace("*", ".*").replace("?", ".")
        
        # パターンが / で始まる場合は先頭一致、そうでない場合は部分一致
        if pattern.startswith("/"):
            regex_pattern = f"^{regex_pattern[1:]}"
        else:
            regex_pattern = f".*{regex_pattern}"
            
        # パターンが / で終わる場合はディレクトリ一致
        if pattern.endswith("/"):
            regex_pattern = f"{regex_pattern}.*"
            
        # パターンに一致するか確認
        try:
            if re.match(regex_pattern, path):
                return True
        except re.error:
            # 正規表現エラーの場合は単純な文字列比較を試みる
            if pattern in path:
                return True
            
    return False

def buildFileTree(tree: List[Dict[str, Any]], ignorePatterns: List[str] = [], maxDepth: int = -1) -> Dict[str, Any]:
    """
    ファイルツリーを構築します。
    
    @param tree - ファイルとディレクトリのリスト
    @param ignorePatterns - 無視パターンのリスト
    @param maxDepth - 最大深度（-1は無制限）
    @return ファイルツリー
    """
    start_time = time.time()
    
    # treeが空または無効な場合は空のルートを返す
    if not tree:
        return {
            "name": "/",
            "type": "directory",
            "children": []
        }
    
    # ルートディレクトリを作成
    root = {
        "name": "/",
        "type": "directory",
        "children": []
    }
    
    # パスでソート
    try:
        sorted_tree = sorted(tree, key=lambda x: x.get("path", ""))
    except Exception:
        # ソートに失敗した場合はそのまま使用
        sorted_tree = tree
    
    # パスのキャッシュ（既に処理したディレクトリを記録）
    processed_dirs: Set[str] = set()
    
    # ディレクトリノードのキャッシュ
    dir_nodes: Dict[str, Dict[str, Any]] = {"/": root}
    
    for item in sorted_tree:
        # 必須フィールドがない場合はスキップ
        if "path" not in item or "type" not in item:
            continue
            
        path = item["path"]
        item_type = "directory" if item["type"] == "tree" else "file"
        
        # 無視パターンに一致する場合はスキップ
        if shouldIgnore(path, ignorePatterns):
            continue
            
        # パスを分割
        parts = path.split("/")
        
        # 深度を計算
        depth = len(parts) - 1
        
        # 最大深度を超える場合はスキップ
        if maxDepth >= 0 and depth > maxDepth:
            continue
        
        # 親ディレクトリのパスを構築
        parent_path = "/".join(parts[:-1])
        if not parent_path:
            parent_path = "/"
            
        # 親ディレクトリが存在しない場合は作成
        if parent_path not in dir_nodes:
            # 親の親を再帰的に作成
            current_path = ""
            for i, part in enumerate(parts[:-1]):
                if i == 0:
                    current_path = part
                else:
                    current_path = f"{current_path}/{part}"
                
                if current_path and current_path not in dir_nodes:
                    # 親ノードを取得
                    parent_of_parent = "/" if i == 0 else "/".join(parts[:i])
                    if not parent_of_parent:
                        parent_of_parent = "/"
                    
                    # 親ノードが存在することを確認
                    if parent_of_parent not in dir_nodes:
                        continue
                    
                    # 新しいディレクトリノードを作成
                    new_dir = {
                        "name": part,
                        "type": "directory",
                        "path": current_path,
                        "children": []
                    }
                    
                    # 親ノードに追加
                    dir_nodes[parent_of_parent]["children"].append(new_dir)
                    dir_nodes[current_path] = new_dir
            
        # 親ディレクトリが存在することを確認
        if parent_path not in dir_nodes:
            # 親ディレクトリが見つからない場合はルートに追加
            parent_path = "/"
        
        # ファイルまたはディレクトリノードを作成
        node = {
            "name": parts[-1],
            "type": item_type,
            "path": path
        }
        
        # ディレクトリの場合は子ノードリストを追加
        if item_type == "directory":
            node["children"] = []
            dir_nodes[path] = node
        
        # 親ディレクトリに追加
        dir_nodes[parent_path]["children"].append(node)
    
    # 処理時間を計測
    end_time = time.time()
    print(f"ファイルツリー構築時間: {end_time - start_time:.2f}秒")
    
    return root

def countFiles(tree: Dict[str, Any]) -> Dict[str, int]:
    """
    ファイルツリー内のファイルとディレクトリの数を数えます。
    
    @param tree - ファイルツリー
    @return ファイルとディレクトリの数
    """
    result = {"files": 0, "directories": 0}
    
    if not tree:
        return result
    
    # ルートディレクトリの場合
    if tree.get("type") == "directory":
        result["directories"] += 1
        
        # 子要素を処理
        for child in tree.get("children", []):
            child_counts = countFiles(child)
            result["files"] += child_counts["files"]
            result["directories"] += child_counts["directories"]
    else:
        # ファイルの場合
        result["files"] += 1
    
    return result 