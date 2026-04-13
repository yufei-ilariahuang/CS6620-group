from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "app_config.yml"


def parse_simple_yaml(file_path: Path):
    root = {}
    stack = [(-1, root)]

    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()

        while stack and indent <= stack[-1][0]:
            stack.pop()

        parent = stack[-1][1]

        if line.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError(f"Invalid list item placement: {line}")
            parent.append(line[2:].strip())
            continue

        if ":" not in line:
            raise ValueError(f"Unsupported YAML line: {line}")

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        if value == "":
            next_container = [] if key == "notes" else {}
            parent[key] = next_container
            stack.append((indent, next_container))
        else:
            parent[key] = value.strip("'\"")

    return root


def dump_simple_yaml(data: dict) -> str:
    lines: list[str] = []

    def emit(mapping: dict, indent: int = 0):
        prefix = " " * indent
        for key, value in mapping.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                emit(value, indent + 2)
            elif isinstance(value, list):
                lines.append(f"{prefix}{key}:")
                for item in value:
                    lines.append(f"{prefix}  - {item}")
            else:
                lines.append(f"{prefix}{key}: {value}")

    emit(data)
    return "\n".join(lines) + "\n"


def aws_json(profile: str, region: str, stack_name: str) -> dict:
    command = [
        "aws",
        "cloudformation",
        "describe-stacks",
        "--stack-name",
        stack_name,
        "--region",
        region,
        "--profile",
        profile,
        "--output",
        "json",
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


def extract_outputs(payload: dict) -> dict[str, str]:
    stacks = payload.get("Stacks", [])
    if not stacks:
        raise ValueError("No CloudFormation stacks returned.")

    outputs = {}
    for item in stacks[0].get("Outputs", []):
        key = item.get("OutputKey")
        value = item.get("OutputValue")
        if key and value:
            outputs[key] = value
    return outputs


def find_output(outputs: dict[str, str], needle: str) -> str:
    matches = [value for key, value in outputs.items() if needle in key]
    if not matches:
        raise ValueError(f"Could not find CloudFormation output containing '{needle}'.")
    return matches[0]


def main() -> int:
    config = parse_simple_yaml(CONFIG_PATH)

    parser = argparse.ArgumentParser(
        description="Sync app_config.yml from deployed CloudFormation outputs."
    )
    parser.add_argument(
        "--stack-name",
        default=config["project"]["stack_name"],
        help="CloudFormation stack name",
    )
    parser.add_argument(
        "--profile",
        default=config["project"]["aws_profile"],
        help="AWS CLI profile name",
    )
    parser.add_argument(
        "--region",
        default=config["project"]["aws_region"],
        help="AWS region",
    )
    parser.add_argument(
        "--ses-from-email",
        default=config["backend"]["ses_from_email"],
        help="SES verified sender email to keep in app_config.yml",
    )
    args = parser.parse_args()

    payload = aws_json(args.profile, args.region, args.stack_name)
    outputs = extract_outputs(payload)

    config["project"]["stack_name"] = args.stack_name
    config["project"]["aws_profile"] = args.profile
    config["project"]["aws_region"] = args.region
    config["project"]["user_pool_id"] = find_output(outputs, "UserPoolId")
    config["frontend"]["api_base_url"] = find_output(outputs, "ApiEndpoint")
    config["frontend"]["cognito_region"] = args.region
    config["frontend"]["cognito_app_client_id"] = find_output(outputs, "AppClientId")
    config["backend"]["ses_from_email"] = args.ses_from_email

    CONFIG_PATH.write_text(dump_simple_yaml(config), encoding="utf-8")

    print("Updated app_config.yml with deployed values:")
    print(f"  stack_name: {config['project']['stack_name']}")
    print(f"  aws_profile: {config['project']['aws_profile']}")
    print(f"  aws_region: {config['project']['aws_region']}")
    print(f"  user_pool_id: {config['project']['user_pool_id']}")
    print(f"  api_base_url: {config['frontend']['api_base_url']}")
    print(f"  cognito_app_client_id: {config['frontend']['cognito_app_client_id']}")
    print(f"  ses_from_email: {config['backend']['ses_from_email']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
