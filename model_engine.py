import os
import io
import json
import zipfile
import tempfile
import joblib
from collections import Counter
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score

class ModelEngine:
    def __init__(self, tmodel_path=None):
        self.tmodel_path = tmodel_path
        self.categories = []
        self.config = {
            "confidence_threshold": 0.80, 
            "min_examples_per_category": 5, 
            "cv_accuracy": None, 
            "cv_small_data": False,
            "auto_learn": True
        }
        self.dataset = []
        self.pipeline = None
        if tmodel_path and os.path.exists(tmodel_path): self.load_model(tmodel_path)

    def _make_pipeline(self):
        features = FeatureUnion([
            ("word_tfidf", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True)),
            ("char_tfidf", TfidfVectorizer(analyzer="char", ngram_range=(3, 5), sublinear_tf=True)),
        ])
        return Pipeline([("features", features), ("clf", LogisticRegression(max_iter=1000, class_weight="balanced"))])

    def create_new_model(self, categories, config=None):
        self.categories = list(categories)
        if config: self.config.update(config)
        self.dataset = []
        self.pipeline = None
        self.config["cv_accuracy"] = None
        self.config["cv_small_data"] = False

    def load_model(self, path):
        try:
            with zipfile.ZipFile(path, 'r') as zf:
                data = json.loads(zf.read('data.json').decode('utf-8'))
                self.categories = data.get("categories", [])
                self.config = data.get("config", self.config)
                self.config.setdefault("auto_learn", True)
                self.dataset = data.get("dataset", [])
                
                if 'model.joblib' in zf.namelist():
                    with zf.open('model.joblib') as f:
                        self.pipeline = joblib.load(f)
                else:
                    self.pipeline = None
        except Exception as e:
            raise RuntimeError(f"Failed to load model. It may be outdated or corrupted.\n{e}")
        self.tmodel_path = path

    def save_model(self, path=None, backup_manager=None):
        target_path = path or self.tmodel_path
        if not target_path: raise ValueError("No target path specified.")
        if backup_manager and os.path.exists(target_path):
            try: backup_manager.create_backup(target_path)
            except Exception: pass
            
        payload_data = {
            "categories": self.categories,
            "config": self.config,
            "dataset": self.dataset
        }
        
        dir_name = os.path.dirname(os.path.abspath(target_path))
        os.makedirs(dir_name, exist_ok=True)
        
        with zipfile.ZipFile(target_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('data.json', json.dumps(payload_data, indent=4))
            if self.pipeline:
                model_bytes = io.BytesIO()
                joblib.dump(self.pipeline, model_bytes)
                zf.writestr('model.joblib', model_bytes.getvalue())
                
        self.tmodel_path = target_path

    def check_readiness(self):
        if not self.categories: return False, "No categories defined."
        if self.pipeline is None: return False, "Model has not been trained yet."
        min_required = self.config.get("min_examples_per_category", 5)
        counts = {cat: 0 for cat in self.categories}
        for _, cat in self.dataset:
            if cat in counts: counts[cat] += 1
        for cat, count in counts.items():
            if count < min_required: return False, f"Category '{cat}' has {count}/{min_required} required examples."
        return True, "Model is ready for automatic classification."

    def _compute_cv(self, texts, labels):
        counts = Counter(labels)
        if len(set(labels)) < 2 or min(counts.values()) < 2: return None, True
        n_folds = min(5, min(counts.values()))
        small = min(counts.values()) < 5 or len(texts) < 30
        try:
            scores = cross_val_score(self._make_pipeline(), texts, labels, cv=n_folds)
            return float(scores.mean()), small
        except Exception: return None, True

    def train(self, new_examples):
        updated = list(self.dataset) + list(new_examples)
        texts = [t for t, _ in updated]
        labels = [c for _, c in updated]
        if len(set(labels)) < 2: raise ValueError("Training requires examples from at least 2 distinct categories.")
        try:
            pipe = self._make_pipeline()
            pipe.fit(texts, labels)
            self.dataset = updated
            self.pipeline = pipe
            cv, small = self._compute_cv(texts, labels)
            self.config["cv_accuracy"] = cv
            self.config["cv_small_data"] = small
            return True
        except Exception as e: raise RuntimeError(f"Training failed securely. Error: {e}")

    def classify_batch(self, paragraphs):
        is_ready, _ = self.check_readiness()
        threshold = self.config.get("confidence_threshold", 0.80)
        results = []
        for text in paragraphs:
            if not is_ready or not self.pipeline:
                results.append({"text": text, "category": "Uncertain", "confidence": 0.0, "probabilities": {c: 0.0 for c in self.categories}, "top3": [], "is_uncertain": True})
                continue
            probs = self.pipeline.predict_proba([text])[0]
            prob_map = {cls: float(p) for cls, p in zip(self.pipeline.classes_, probs)}
            ranked = sorted(prob_map.items(), key=lambda kv: kv[1], reverse=True)
            best_cat, best_conf = ranked[0]
            results.append({"text": text, "category": "Uncertain" if best_conf < threshold else best_cat, "confidence": best_conf, "probabilities": prob_map, "top3": ranked[:3], "is_uncertain": best_conf < threshold})
        return results

    def rename_category(self, old, new):
        if old not in self.categories: raise ValueError(f"Category '{old}' not found.")
        if new != old and new in self.categories: raise ValueError(f"Category '{new}' already exists.")
        self.categories = [new if c == old else c for c in self.categories]
        self.dataset = [(t, new if c == old else c) for t, c in self.dataset]
        self._retrain_after_category_change()

    def merge_categories(self, sources, target):
        if len(self.categories) - len(set(sources) - {target}) < 2: raise ValueError("Cannot merge: model must have at least 2 categories.")
        sources = set(sources)
        new_cats = []
        for c in self.categories:
            if c in sources and c != target: continue
            if c == target and target in new_cats: continue
            new_cats.append(c)
        if target not in new_cats: new_cats.append(target)
        self.categories = new_cats
        self.dataset = [(t, target if c in sources else c) for t, c in self.dataset]
        self._retrain_after_category_change()

    def delete_category(self, cat):
        if cat not in self.categories: raise ValueError(f"Category '{cat}' not found.")
        if len(self.categories) - 1 < 2: raise ValueError("Cannot delete: model must have at least 2 categories.")
        removed = sum(1 for _, c in self.dataset if c == cat)
        self.categories = [c for c in self.categories if c != cat]
        self.dataset = [(t, c) for t, c in self.dataset if c != cat]
        self._retrain_after_category_change()
        return removed

    def _retrain_after_category_change(self):
        if len(set(c for _, c in self.dataset)) >= 2:
            try:
                self.train([])
                return
            except Exception: pass
        self.pipeline = None
        self.config["cv_accuracy"] = None
        self.config["cv_small_data"] = False
