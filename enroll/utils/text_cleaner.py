import re
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

class TextCleaner(BaseEstimator, TransformerMixin):

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        if isinstance(X, list):
            X = pd.Series(X)
        return X.apply(self.clean_text)

    @staticmethod
    def clean_text(x):
        x = str(x)
        x = re.sub(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b', '', x)
        x = re.sub(r'\b(Value\s*Date|Value|Date)\b', '', x, flags=re.I)
        x = re.sub(r'Card\s+xx\d{4}', '', x, flags=re.I)
        x = re.sub(r'xx\d{4}', '', x)
        x = re.sub(r'\b\d+\b', '', x)
        x = re.sub(r'[^a-zA-Z\s]', ' ', x)
        return re.sub(r'\s+', ' ', x).strip()
