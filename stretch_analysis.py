import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import joblib
from sklearn.metrics import precision_score, recall_score, f1_score
from sklearn.inspection import permutation_importance
# استيراد الثوابت والدوال من ملفك الأساسي
from model_comparison import load_and_preprocess, NUMERIC_FEATURES

# --- المستوى 1: تحسين العتبة ---
def threshold_sweep_analysis(best_model, X_test, y_test, output_path="results/threshold_sweep.png"):
    y_probs = best_model.predict_proba(X_test)[:, 1]
    thresholds = np.arange(0.1, 0.95, 0.05)
    
    results = []
    for t in thresholds:
        y_pred = (y_probs >= t).astype(int)
        # حساب التنبيهات المتوقعة لكل 1000 عميل
        alerts_per_1000 = (y_pred.sum() / len(y_test)) * 1000
        results.append({
            'threshold': t,
            'precision': precision_score(y_test, y_pred, zero_division=0),
            'recall': recall_score(y_test, y_pred, zero_division=0),
            'f1': f1_score(y_test, y_pred, zero_division=0),
            'alerts_per_1000': alerts_per_1000
        })
    
    sweep_df = pd.DataFrame(results)
    
    # الرسم البياني للعتبة
    plt.figure(figsize=(10, 6))
    plt.plot(sweep_df['threshold'], sweep_df['precision'], label='Precision', marker='o')
    plt.plot(sweep_df['threshold'], sweep_df['recall'], label='Recall', marker='s')
    plt.axhline(y=0.15, color='r', linestyle='--', label='150/1000 Business Limit')
    plt.title("Threshold Sweep for Business Constraints")
    plt.xlabel("Decision Threshold")
    plt.ylabel("Score / Rate")
    plt.legend()
    plt.grid(True)
    plt.savefig(output_path)
    plt.close()
    print(f"Saved threshold sweep plot to {output_path}")
    return sweep_df

# --- المستوى 2: أهمية التبديل ---
def plot_permutation_importance_comparison(models_dict, X_test, y_test, output_path="results/permutation_importance.png"):
    # اختيار النماذج المطلوبة للمقارنة
    target_models = ['RF_balanced', 'LR_balanced']
    
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    
    for i, name in enumerate(target_models):
        if name in models_dict:
            model = models_dict[name]
            # حساب الأهمية (10 تكرارات كما هو مطلوب)
            result = permutation_importance(model, X_test, y_test, n_repeats=10, random_state=42)
            
            sorted_idx = result.importances_mean.argsort()
            axes[i].boxplot(result.importances[sorted_idx].T, vert=False, labels=np.array(NUMERIC_FEATURES)[sorted_idx])
            axes[i].set_title(f"Permutation Importance: {name}")
            axes[i].set_xlabel("Importance Score")
    
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    print(f"Saved permutation importance plot to {output_path}")

if __name__ == "__main__":
    # 1. إنشاء مجلد النتائج إذا لم يكن موجوداً
    import os
    os.makedirs("results", exist_ok=True)

    # 2. تحميل البيانات (80/20)
    X_train, X_test, y_train, y_test = load_and_preprocess()
    
    # 3. تحميل أفضل نموذج محفوظ (للمستوى 1)
    try:
        best_model = joblib.load("results/best_model.joblib")
        print("Loaded best_model.joblib successfully.")
        
        # تنفيذ المستوى 1
        sweep_results = threshold_sweep_analysis(best_model, X_test, y_test)
        
        # اختيار العتبة التشغيلية (للمذكرة)
        ideal_row = sweep_results[sweep_results['alerts_per_1000'] <= 150].iloc[-1]
        print(f"\nRecommended Threshold: {ideal_row['threshold']}")
        print(f"Expected Alerts per 1000: {ideal_row['alerts_per_1000']:.1f}")
        
    except FileNotFoundError:
        print("Error: best_model.joblib not found. Run model_comparison.py first.")

    # 4. للمستوى 2: نحتاج النماذج المدربة (يمكنك إعادة تدريبهم بسرعة هنا أو تحميلهم)
    # ملاحظة: لتبسيط الأمر، سنقوم بتدريب نموذجين فقط للمقارنة
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    print("\nTraining models for Permutation Importance comparison...")
    rf = Pipeline([('scaler', 'passthrough'), ('model', RandomForestClassifier(n_estimators=100, max_depth=10, class_weight='balanced', random_state=42))])
    lr = Pipeline([('scaler', StandardScaler()), ('model', LogisticRegression(class_weight='balanced', max_iter=1000, random_state=42))])
    
    rf.fit(X_train, y_train)
    lr.fit(X_train, y_train)
    
    plot_permutation_importance_comparison({'RF_balanced': rf, 'LR_balanced': lr}, X_test, y_test)