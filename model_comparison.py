import os
from datetime import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from joblib import dump
from sklearn.calibration import CalibrationDisplay
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (PrecisionRecallDisplay, average_precision_score,
                             precision_score, recall_score,
                             f1_score, accuracy_score)
from sklearn.model_selection import StratifiedKFold, train_test_split, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

NUMERIC_FEATURES = ["tenure", "monthly_charges", "total_charges",
                    "num_support_calls", "senior_citizen",
                    "has_partner", "has_dependents", "contract_months"]

def load_and_preprocess(filepath="data/telecom_churn.csv", random_state=42):
    """Load data and split into 80/20 stratified sets."""
    df = pd.read_csv(filepath)
    X = df[NUMERIC_FEATURES]
    y = df['churned']
    return train_test_split(X, y, test_size=0.2, random_state=random_state, stratify=y)

def define_models():
    """Define the 6 required model configurations in Pipelines."""
    models = {}
    
    # 1. Dummy Baseline
    models['Dummy'] = Pipeline([
        ('scaler', 'passthrough'),
        ('model', DummyClassifier(strategy='most_frequent'))
    ])
    
    # 2. Logistic Regression Default
    models['LR_default'] = Pipeline([
        ('scaler', StandardScaler()), 
        ('model', LogisticRegression(max_iter=1000, random_state=42))
    ])
    
    # 3. Logistic Regression Balanced
    models['LR_balanced'] = Pipeline([
        ('scaler', StandardScaler()), 
        ('model', LogisticRegression(class_weight='balanced', max_iter=1000, random_state=42))
    ])
    
    # 4. Decision Tree depth 5
    models['DT_depth5'] = Pipeline([
        ('scaler', 'passthrough'), 
        ('model', DecisionTreeClassifier(max_depth=5, random_state=42))
    ])
    
    # 5. Random Forest Default
    models['RF_default'] = Pipeline([
        ('scaler', 'passthrough'), 
        ('model', RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42))
    ])
    
    # 6. Random Forest Balanced
    models['RF_balanced'] = Pipeline([
        ('scaler', 'passthrough'), 
        ('model', RandomForestClassifier(n_estimators=100, max_depth=10, class_weight='balanced', random_state=42))
    ])
    
    return models

def run_cv_comparison(models, X, y, n_splits=5, random_state=42):
    """Run cross-validation and return metrics for all models."""
    results = []
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    
    scoring = {
        'accuracy': 'accuracy',
        'precision': 'precision',
        'recall': 'recall',
        'f1': 'f1',
        'pr_auc': 'average_precision'
    }
    
    for name, pipeline in models.items():
        cv_res = cross_validate(pipeline, X, y, cv=skf, scoring=scoring)
        results.append({
            'model': name,
            'accuracy_mean': cv_res['test_accuracy'].mean(),
            'accuracy_std': cv_res['test_accuracy'].std(),
            'precision_mean': cv_res['test_precision'].mean(),
            'precision_std': cv_res['test_precision'].std(),
            'recall_mean': cv_res['test_recall'].mean(),
            'recall_std': cv_res['test_recall'].std(),
            'f1_mean': cv_res['test_f1'].mean(),
            'f1_std': cv_res['test_f1'].std(),
            'pr_auc_mean': cv_res['test_pr_auc'].mean(),
            'pr_auc_std': cv_res['test_pr_auc'].std()
        })
    return pd.DataFrame(results)

def save_comparison_table(results_df, output_path="results/comparison_table.csv"):
    """Save results to CSV."""
    results_df.to_csv(output_path, index=False)

def plot_pr_curves_top3(models, X_test, y_test, output_path="results/pr_curves.png"):
    """Plot PR Curves for the top 3 models based on PR-AUC."""
    # Compute test PR-AUC to find top 3
    scores = {name: average_precision_score(y_test, mod.predict_proba(X_test)[:, 1]) 
              for name, mod in models.items() if name != 'Dummy'}
    top3_names = sorted(scores, key=scores.get, reverse=True)[:3]
    
    fig, ax = plt.subplots(figsize=(8, 6))
    for name in top3_names:
        PrecisionRecallDisplay.from_estimator(models[name], X_test, y_test, ax=ax, name=name)
    ax.set_title("Precision-Recall Curves: Top 3 Models")
    plt.savefig(output_path)
    plt.close()

def plot_calibration_top3(models, X_test, y_test, output_path="results/calibration.png"):
    """Plot Calibration curves for top 3 models."""
    scores = {name: average_precision_score(y_test, mod.predict_proba(X_test)[:, 1]) 
              for name, mod in models.items() if name != 'Dummy'}
    top3_names = sorted(scores, key=scores.get, reverse=True)[:3]
    
    fig, ax = plt.subplots(figsize=(8, 6))
    for name in top3_names:
        CalibrationDisplay.from_estimator(models[name], X_test, y_test, ax=ax, name=name)
    ax.set_title("Calibration Plots: Top 3 Models")
    plt.savefig(output_path)
    plt.close()

def save_best_model(best_model, output_path="results/best_model.joblib"):
    """Serialize the best model."""
    dump(best_model, output_path)

def log_experiment(results_df, output_path="results/experiment_log.csv"):
    """Create a log entry for the experiment."""
    log_df = results_df[['model', 'accuracy_mean', 'precision_mean', 'recall_mean', 'f1_mean', 'pr_auc_mean']].copy()
    log_df.columns = ['model_name', 'accuracy', 'precision', 'recall', 'f1', 'pr_auc']
    log_df['timestamp'] = datetime.now().isoformat()
    log_df.to_csv(output_path, index=False)

def find_tree_vs_linear_disagreement(rf_model, lr_model, X_test, y_test, feature_names, min_diff=0.15):
    """Identify the sample with the largest disagreement between RF and LR."""
    rf_probs = rf_model.predict_proba(X_test)[:, 1]
    lr_probs = lr_model.predict_proba(X_test)[:, 1]
    diffs = np.abs(rf_probs - lr_probs)
    max_idx = np.argmax(diffs)
    
    if diffs[max_idx] < min_diff:
        return None
        
    return {
        'sample_idx': max_idx,
        'feature_values': X_test.iloc[max_idx].to_dict(),
        'rf_proba': rf_probs[max_idx],
        'lr_proba': lr_probs[max_idx],
        'prob_diff': diffs[max_idx],
        'true_label': int(y_test.iloc[max_idx])
    }