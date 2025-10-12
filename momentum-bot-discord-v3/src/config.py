import yaml
import os

def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_all():
    base = os.path.join(os.path.dirname(__file__), "..", "config")
    global_cfg = load_yaml(os.path.join(base, "global.yml"))
    rules_cfg = load_yaml(os.path.join(base, "rules.yml"))
    uni_cfg   = load_yaml(os.path.join(base, "universe.yml"))
    opt_cfg   = load_yaml(os.path.join(base, "optimizer.yml"))
    return global_cfg, rules_cfg, uni_cfg, opt_cfg
