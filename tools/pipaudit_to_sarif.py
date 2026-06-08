"""
pip-audit の JSON 出力を SARIF 2.1.0 形式に変換するツール。

pip-audit は SARIF を直接出力しないため、本スクリプトで変換し、Azure DevOps の
Scans タブ（SARIF SAST Scans Tab 拡張）で表示できるようにする。

使い方:
    pip-audit --format json --output pip-audit.json || true
    python tools/pipaudit_to_sarif.py pip-audit.json pip-audit.sarif

標準ライブラリのみで動作する。
"""
import json
import sys


def convert(pipaudit_json):
    """pip-audit JSON を SARIF の dict に変換する。"""
    rules = {}
    results = []

    dependencies = pipaudit_json.get("dependencies", pipaudit_json)
    if isinstance(dependencies, dict):
        dependencies = dependencies.get("dependencies", [])

    for dep in dependencies:
        name = dep.get("name", "unknown")
        version = dep.get("version", "unknown")
        for vuln in dep.get("vulns", []) or []:
            vuln_id = vuln.get("id", "UNKNOWN")
            description = vuln.get("description", "") or ""
            fix_versions = vuln.get("fix_versions", []) or []
            rule_id = f"{name}:{vuln_id}"

            if rule_id not in rules:
                rules[rule_id] = {
                    "id": rule_id,
                    "name": vuln_id,
                    "shortDescription": {
                        "text": f"{name} {version} に既知の脆弱性 {vuln_id}"
                    },
                    "fullDescription": {"text": description[:1000] or vuln_id},
                    "helpUri": "https://pypi.org/project/%s/" % name,
                    "defaultConfiguration": {"level": "warning"},
                }

            fix_text = (
                f" 修正バージョン: {', '.join(fix_versions)}"
                if fix_versions
                else " 修正バージョンは未公開。"
            )
            results.append(
                {
                    "ruleId": rule_id,
                    "level": "warning",
                    "message": {
                        "text": (
                            f"{name} {version} は脆弱性 {vuln_id} の影響を受ける。"
                            + fix_text
                        )
                    },
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {
                                    "uri": "app/requirements.txt"
                                }
                            }
                        }
                    ],
                }
            )

    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "pip-audit",
                        "informationUri": "https://github.com/pypa/pip-audit",
                        "rules": list(rules.values()),
                    }
                },
                "results": results,
            }
        ],
    }


def main():
    if len(sys.argv) != 3:
        print("usage: pipaudit_to_sarif.py <input.json> <output.sarif>")
        return 1

    input_path, output_path = sys.argv[1], sys.argv[2]
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        # 入力が無い・空の場合でも空の SARIF を出力してパイプラインを止めない
        print(f"warning: 入力を読み込めなかったため空の SARIF を出力する: {exc}")
        data = {"dependencies": []}

    sarif = convert(data)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sarif, f, ensure_ascii=False, indent=2)

    count = len(sarif["runs"][0]["results"])
    print(f"pip-audit SARIF を出力した（{count} 件）: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
