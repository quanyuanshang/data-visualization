"""
Export Potential Artists with SHAP Explanations for Visualization.
(Fixed: Ensure leverage_ratio is included in SHAP calculation)
"""
import argparse
import pickle
import json
import pandas as pd
import shap
import numpy as np
from pathlib import Path

# ================= 配置区域 =================
# 输入文件路径
INPUT_PREDS = Path("output/artist_success_predictions.csv")
INPUT_FEATURES = Path("output/artist_features.parquet")
INPUT_MODEL = Path("output/artist_success_xgb.pkl")

# 输出目录
OUTPUT_DIR = Path(r"D:\cs\数据可视化\Topic1\genre-visualization\public\data")

# 筛选阈值
FILTER_CONFIG = {
    "max_target_score": 1.3,      
    "max_total_works": 10,         
    "min_neighbor_pr": 1e-9,      
    "min_predicted_score": 2   
}
# ===========================================

def main():
    print(f"🚀 Starting export process...")
    
    if not (INPUT_PREDS.exists() and INPUT_FEATURES.exists() and INPUT_MODEL.exists()):
        print(f"❌ Error: Input files not found in 'output/' directory.")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 加载数据
    print("📥 Loading data and model...")
    df_preds = pd.read_csv(INPUT_PREDS)
    df_features = pd.read_parquet(INPUT_FEATURES)
    
    with open(INPUT_MODEL, "rb") as f:
        model = pickle.load(f)

    # 2. 合并数据
    # 确保 leverage_ratio 存在。如果特征文件里没有（可能在训练脚本里计算了但没存进parquet），这里需要重新计算并补全
    # 检查 df_features 是否包含 leverage_ratio，如果没有，手动补上
    if "leverage_ratio" not in df_features.columns and "max_neighbor_pr" in df_features.columns and "pagerank" in df_features.columns:
        print("⚠️ 'leverage_ratio' missing in features, recalculating...")
        df_features["leverage_ratio"] = df_features["max_neighbor_pr"] / (df_features["pagerank"] + 1e-9)

    df_full = pd.merge(
        df_preds[["person_id", "name", "target_score", "predicted_score", "residual"]],
        df_features, # 直接合并所有特征列
        on="person_id",
        how="inner",
        suffixes=("", "_dup") # 防止重复列报错
    )
    # 清理可能产生的重复列
    df_full = df_full.loc[:, ~df_full.columns.str.endswith('_dup')]

    # 3. 筛选逻辑
    print("🔍 Filtering for 'Co-Signed' potential artists...")
    
    # 确保用于筛选的列存在
    if "leverage_ratio" not in df_full.columns:
         df_full["leverage_ratio"] = df_full["max_neighbor_pr"] / (df_full["pagerank"] + 1e-9)

    mask = (
        (df_full["target_score"] < FILTER_CONFIG["max_target_score"]) &
        (df_full["total_works"] <= FILTER_CONFIG["max_total_works"]) &
        (df_full["max_neighbor_pr"] > FILTER_CONFIG["min_neighbor_pr"]) &
        (df_full["predicted_score"] > FILTER_CONFIG["min_predicted_score"])
    )
    
    candidates = df_full[mask].copy()
    candidates = candidates.sort_values(by="leverage_ratio", ascending=False)
    
    print(f"💎 Found {len(candidates)} candidates matching criteria.")
    
    if candidates.empty:
        print("⚠️ No candidates found! Falling back to Top 10 by leverage...")
        mask_fallback = (
            (df_full["target_score"] < FILTER_CONFIG["max_target_score"]) & 
            (df_full["max_neighbor_pr"] > 0)
        )
        candidates = df_full[mask_fallback].sort_values(by="leverage_ratio", ascending=False).head(10)

    # 4. 导出 CSV
    csv_output_path = OUTPUT_DIR / "potential_artists_list.csv"
    cols_to_save = [
        "person_id", "name", "total_works", "target_score", 
        "predicted_score", "max_neighbor_pr", "leverage_ratio", "pagerank"
    ]
    candidates[cols_to_save].to_csv(csv_output_path, index=False)
    print(f"✅ Saved CSV list to: {csv_output_path}")

    # 5. SHAP 分析 (关键修复部分)
    print("🧠 Calculating SHAP values for visualization...")
    
    # === 修复：确保特征列与训练时完全一致 ===
    if hasattr(model, "feature_names_in_"):
        # 优先使用模型记录的特征名（顺序和名称必须完全匹配）
        feature_cols = list(model.feature_names_in_)
        print(f"   Using {len(feature_cols)} features defined in model.")
    else:
        # 备选方案：排除非特征列
        # 【重要】 这里删掉了 'leverage_ratio'，因为它现在是特征之一了！
        exclude = {"person_id", "name", "target_score", "predicted_score", "residual"} 
        feature_cols = [c for c in df_features.columns if c not in exclude]
        print(f"   Using {len(feature_cols)} features (inferred).")

    # 检查特征是否对齐
    missing_cols = [c for c in feature_cols if c not in candidates.columns]
    if missing_cols:
        print(f"❌ Error: The following features are missing in the data: {missing_cols}")
        print("   Please make sure 'artist_features.parquet' contains all training features.")
        return

    explainer = shap.TreeExplainer(model)
    viz_data = []
    
    for idx, row in candidates.iterrows():
        # 提取单行特征矩阵 (严格按照 feature_cols 顺序)
        X_single = pd.DataFrame([row[feature_cols]])
        
        # 计算 SHAP
        shap_obj = explainer(X_single)
        base_value = float(shap_obj.base_values[0])
        shap_values = shap_obj.values[0]
        
        # 整理 JSON
        contributions = []
        for feat_name, feat_val, impact in zip(feature_cols, X_single.iloc[0], shap_values):
            if abs(impact) > 0.001:
                contributions.append({
                    "feature": feat_name,
                    "value": float(feat_val),
                    "impact": float(impact)
                })
        
        contributions.sort(key=lambda x: abs(x["impact"]), reverse=True)
        
        viz_data.append({
            "id": int(row["person_id"]),
            "name": row["name"],
            "metrics": {
                "total_works": int(row["total_works"]),
                "target_score": float(row["target_score"]),
                "predicted_score": float(row["predicted_score"]),
                "leverage_ratio": float(row.get("leverage_ratio", 0)),
                "max_neighbor_pr": float(row.get("max_neighbor_pr", 0))
            },
            "shap_explanation": {
                "base_value": base_value,
                "final_value": float(base_value + sum(shap_values)),
                "factors": contributions
            }
        })

    json_output_path = OUTPUT_DIR / "potential_artists_shap_viz.json"
    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(viz_data, f, ensure_ascii=False, indent=2)
        
    print(f"✅ Saved JSON for visualization to: {json_output_path}")

if __name__ == "__main__":
    main()