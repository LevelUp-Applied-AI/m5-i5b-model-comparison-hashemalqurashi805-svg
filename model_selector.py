import json
import os
import joblib
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier

# Importing your existing logic to stay consistent with the main project
from model_comparison import load_and_preprocess

class ModelSelector:
    """
    A framework to dynamically build, train, and export machine learning 
    models based on a JSON configuration file.
    """
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.fitted_models = {}

    def _load_config(self):
        """Load the JSON configuration file."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file {self.config_path} not found.")
        with open(self.config_path, 'r') as f:
            return json.load(f)

    def _get_model_object(self, model_type, params):
        """Map string types from JSON to Scikit-Learn objects."""
        if model_type == "LogisticRegression":
            return LogisticRegression(**params)
        elif model_type == "RandomForestClassifier":
            return RandomForestClassifier(**params)
        elif model_type == "DecisionTreeClassifier":
            return DecisionTreeClassifier(**params)
        else:
            raise ValueError(f"Model type '{model_type}' is not supported.")

    def build_and_train(self, X_train, y_train):
        """Build pipelines and train models defined in the config."""
        for entry in self.config.get('models', []):
            name = entry['name']
            m_type = entry['type']
            params = entry.get('params', {})
            use_scaling = entry.get('scale', False)

            print(f"Building and Training: {name} ({m_type})...")
            
            # Define Pipeline steps
            scaler = StandardScaler() if use_scaling else 'passthrough'
            model_obj = self._get_model_object(m_type, params)
            
            pipeline = Pipeline([
                ('scaler', scaler),
                ('model', model_obj)
            ])
            
            # Train the model
            pipeline.fit(X_train, y_train)
            self.fitted_models[name] = pipeline

    def export_model(self, model_name, output_dir="results"):
        """Save a specific trained model to a .joblib file."""
        if model_name not in self.fitted_models:
            print(f"Error: Model '{model_name}' has not been trained.")
            return

        os.makedirs(output_dir, exist_ok=True)
        save_path = os.path.join(output_dir, f"{model_name}.joblib")
        joblib.dump(self.fitted_models[model_name], save_path)
        print(f"Successfully exported {model_name} to {save_path}")

# --- Self-contained execution example ---
if __name__ == "__main__":
    # 1. Create a sample config.json for testing
    test_config = {
        "models": [
            {
                "name": "Production_LR",
                "type": "LogisticRegression",
                "params": {"max_iter": 1000, "class_weight": "balanced", "random_state": 42},
                "scale": True
            },
            {
                "name": "Production_RF",
                "type": "RandomForestClassifier",
                "params": {"n_estimators": 100, "max_depth": 10, "random_state": 42},
                "scale": False
            }
        ]
    }
    
    with open("config.json", "w") as f:
        json.dump(test_config, f, indent=4)

    # 2. Load data using your previous preprocessing function
    X_train, X_test, y_train, y_test = load_and_preprocess()

    # 3. Run the Selector
    selector = ModelSelector("config.json")
    selector.build_and_train(X_train, y_train)
    
    # 4. Export the best model (e.g., the RF one)
    selector.export_model("Production_RF")