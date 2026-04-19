import numpy as np
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import StandardScaler


class HMMIntraday:

    def __init__(self, n_regimes=3, min_covar=1e-6, covariance_type="diag", n_iter=100, tol=1e-2):
        """
        Initialize HMM model with configurable parameters
        
        Args:
            n_regimes: Number of hidden states (default: 3)
            min_covar: Minimum covariance (default: 1e-6)
            covariance_type: Type of covariance (default: "diag")
            n_iter: Maximum iterations (default: 100, use 20-30 for speed)
            tol: Convergence tolerance (default: 0.01, use 0.05 for speed)
        """
        self.n_regimes = n_regimes
        self.min_covar = min_covar
        self.covariance_type = covariance_type
        self.n_iter = n_iter
        self.tol = tol
        self.scaler = StandardScaler()
        self.model = GaussianHMM(
            n_components=n_regimes, 
            covariance_type=covariance_type,
            min_covar=min_covar,
            n_iter=n_iter,
            tol=tol,
            random_state=42
        )

    def fit(self, df):
        """
        df must include intraday returns and volatility features
        """
        # Calculate features
        returns = df["return"].values
        rolling_std = df["return"].rolling(5).std().fillna(0).values
        
        X = np.column_stack([returns, rolling_std])
        
        # Remove rows with NaN or infinite values
        valid_mask = np.isfinite(X).all(axis=1)
        X = X[valid_mask]
        
        # Ensure we have enough data points
        if len(X) < self.n_regimes * 2:
            raise ValueError(f"Insufficient data: need at least {self.n_regimes * 2} valid samples, got {len(X)}")
        
        # Check for sufficient variance in each feature
        feature_stds = X.std(axis=0)
        if feature_stds.min() < 1e-8:
            # If variance is extremely low, add minimal regularization
            for i in range(X.shape[1]):
                if feature_stds[i] < 1e-8:
                    X[:, i] = X[:, i] + np.random.normal(0, 1e-6, len(X))
        
        # Scale features to have zero mean and unit variance
        # This helps with numerical stability and prevents covariance issues
        X_scaled = self.scaler.fit_transform(X)
        
        # Ensure scaled data doesn't have any issues
        if not np.isfinite(X_scaled).all():
            raise ValueError("Scaled features contain NaN or infinite values")
        
        self.model.fit(X_scaled)

    def _prepare_features(self, df):
        """Prepare and validate features for prediction"""
        returns = df["return"].values
        rolling_std = df["return"].rolling(5).std().fillna(0).values
        
        X = np.column_stack([returns, rolling_std])
        
        # Remove rows with NaN or infinite values
        valid_mask = np.isfinite(X).all(axis=1)
        X = X[valid_mask]
        
        # Scale features using the same scaler from training
        if len(X) > 0:
            X = self.scaler.transform(X)
        
        return X, valid_mask

    def predict_regime(self, df):
        X, valid_mask = self._prepare_features(df)
        
        if len(X) == 0:
            # Return default regime if no valid data
            return np.array([0] * len(df))
        
        regimes = self.model.predict(X)
        
        # Map back to original length, filling invalid positions with last valid regime
        full_regimes = np.zeros(len(df), dtype=int)
        if len(regimes) > 0:
            full_regimes[valid_mask] = regimes
            # Fill invalid positions with the last valid regime
            last_valid = regimes[-1] if len(regimes) > 0 else 0
            full_regimes[~valid_mask] = last_valid
        
        return full_regimes

    def regime_probability(self, df):
        X, valid_mask = self._prepare_features(df)
        
        if len(X) == 0:
            # Return uniform probabilities if no valid data
            n_samples = len(df)
            return np.ones((n_samples, self.n_regimes)) / self.n_regimes
        
        probs = self.model.predict_proba(X)
        
        # Map back to original length
        full_probs = np.zeros((len(df), self.n_regimes))
        if len(probs) > 0:
            full_probs[valid_mask] = probs
            # Fill invalid positions with uniform probabilities
            full_probs[~valid_mask] = 1.0 / self.n_regimes
        
        return full_probs

