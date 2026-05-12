# config/config_loader.py

import yaml
import os


path = os.path.dirname(os.path.abspath(__file__))


class ConfigLoader:
    def __init__(self, config_dict_or_path= os.path.join(path, "config.yaml")):
        if isinstance(config_dict_or_path, dict):
            self.config = config_dict_or_path
        elif isinstance(config_dict_or_path, str):
            self.config_path = config_dict_or_path
            self.config = self._load_config()
        else:
            raise TypeError("config_dict_or_path must be a dict or a str")

    def _load_config(self):
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"配置文件 {self.config_path} 不存在")

        with open(self.config_path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file)

    def get(self, key, default=None):
        """获取配置项，若不存在则返回默认值"""
        keys = key.split(".")
        value = self.config
        for k in keys:
            if not isinstance(value, dict) or k not in value:
                return default
            value = value.get(k)
        return value if value is not None else default


# 创建ConfigLoader实例并获取配置项
if __name__ == "__main__":

    config_loader = ConfigLoader()

    refactingminer_report_path = config_loader.get("refactingminer_report.path", " ")
    print(f"refactingminer_report_path: {refactingminer_report_path}")

