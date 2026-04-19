import xgboost as xgb
import numpy as np


class XGBDailyReturns:

    def __init__(self, n_estimators=300, max_depth=5, learning_rate=0.03, 
                 subsample=0.8, colsample_bytree=0.8, n_jobs=1):
        """
        Initialize XGBoost model with configurable parameters
        
        Args:
            n_estimators: Number of boosting rounds (default: 300, use 20-50 for speed)
            max_depth: Maximum tree depth (default: 5, use 3 for speed)
            learning_rate: Step size shrinkage (default: 0.03)
            subsample: Subsample ratio (default: 0.8)
            colsample_bytree: Column subsample ratio (default: 0.8)
            n_jobs: Number of parallel threads (default: 1)
        """
        self.model = xgb.XGBRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            subsample=subsample,
            colsample_bytree=colsample_bytree,
            n_jobs=n_jobs,
            random_state=42
        )

    def fit(self, df, features):
        X = df[features]
        y = df["daily_return"]
        self.model.fit(X, y, verbose=False)

    def predict(self, df, features):
        return self.model.predict(df[features])
