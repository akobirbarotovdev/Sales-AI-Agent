import json
import os

PRODUCT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "product_config.json")


def get_product_info() -> dict:
    try:
        with open(PRODUCT_CONFIG_PATH) as f:
            config = json.load(f)
            return {
                "product_name": config.get("product_name", "IT Maxsulot"),
                "product_description": config.get("product_description", ""),
                "company_name": config.get("company_name", ""),
                "website": config.get("website", ""),
                "target_industries": config.get("target_industries", []),
                "benefits": config.get("product_benefits", []),
            }
    except Exception:
        return {
            "product_name": "IT Maxsulot",
            "product_description": "",
            "company_name": "",
            "website": "",
            "target_industries": [],
            "benefits": [],
        }
