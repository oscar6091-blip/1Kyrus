"""Run this outside the web service. It is a reference experiment, not app code."""
import argparse
import hashlib
import json
import platform
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import sklearn
from sklearn.datasets import load_iris
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='experiment_result.json')
    args = parser.parse_args()
    started = datetime.now(timezone.utc).isoformat()
    clock = time.perf_counter()
    data = load_iris()
    x_train, x_test, y_train, y_test = train_test_split(
        data.data, data.target, test_size=0.2, random_state=42,
        stratify=data.target,
    )
    scaler = StandardScaler().fit(x_train)
    x_train = scaler.transform(x_train)
    x_test = scaler.transform(x_test)
    metrics, fit_warnings = [], []
    for solver in ['sgd', 'adam']:
        model = MLPClassifier(
            hidden_layer_sizes=(16,), activation='relu', solver=solver,
            learning_rate_init=0.01, max_iter=200, random_state=42,
            early_stopping=False, tol=1e-4, n_iter_no_change=20,
        )
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter('always')
            model.fit(x_train, y_train)
        fit_warnings.extend([f'{solver}: {w.message}' for w in captured])
        prediction = model.predict(x_test)
        for suffix, value in [
            ('accuracy', accuracy_score(y_test, prediction)),
            ('macro_f1', f1_score(y_test, prediction, average='macro')),
        ]:
            metrics.append({
                'name': f'{solver}_{suffix}', 'split': 'test',
                'value': float(value), 'step': int(model.n_iter_),
                'unit': 'ratio',
            })
    payload = {
        'schema_version': '1.0',
        'experiment_id': 'E1',
        'code_version': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'config': {
            'dataset': 'sklearn.load_iris', 'train_samples': len(x_train),
            'test_samples': len(x_test), 'test_size': 0.2,
            'stratified_split': True,
            'scaler': 'StandardScaler fitted on training data only',
            'hidden_layer_sizes': [16], 'solvers': ['sgd', 'adam'],
            'learning_rate_init': 0.01, 'max_iter': 200,
            'early_stopping': False, 'tol': 1e-4, 'n_iter_no_change': 20,
            'fit_warnings': fit_warnings,
            'interpretation_limit': 'One seed and one split; integration example, not evidence of general superiority.',
        },
        'seed': 42,
        'environment': {
            'python': platform.python_version(), 'numpy': np.__version__,
            'sklearn': sklearn.__version__, 'device': 'CPU',
            'dataset_source': 'https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_iris.html',
        },
        'metrics': metrics,
        'started_at': started,
        'duration_sec': time.perf_counter() - clock,
        'data_origin': 'measured',
    }
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'output': str(destination), 'metrics': metrics, 'warnings': fit_warnings}, ensure_ascii=False))


if __name__ == '__main__':
    run()
