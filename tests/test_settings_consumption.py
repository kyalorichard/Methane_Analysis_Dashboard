from analysis_engine.ml import configured_estimator
from analysis_engine.settings_config import defaults


def test_model_hyperparameters_and_seed_are_consumed_by_estimator():
    cfg = defaults()
    cfg['models']['Random Forest']['n_estimators'] = 37
    cfg['models']['Random Forest']['min_samples_leaf'] = 4
    cfg['comparison']['random_state'] = 123
    model = configured_estimator('Random Forest', cfg)
    assert model.n_estimators == 37
    assert model.min_samples_leaf == 4
    assert model.random_state == 123


def test_unconfigured_model_uses_catalogue_defaults():
    model = configured_estimator('SVR', defaults())
    assert model.kernel == 'rbf'
    assert model.C == 1.0
