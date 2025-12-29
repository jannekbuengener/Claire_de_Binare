#!/usr/bin/env python3
"""Validate Docker Compose memory.yml file syntax and structure."""
import sys
import yaml

def main():
    compose_file = "infrastructure/compose/memory.yml"

    try:
        with open(compose_file) as f:
            data = yaml.safe_load(f)

        print("=" * 50)
        print("Docker Compose Validation Results")
        print("=" * 50)
        print(f"\nFile: {compose_file}")
        print(f"YAML Syntax: VALID")

        # Check services
        services = data.get("services", {})
        print(f"\nServices ({len(services)}):")
        for name, config in services.items():
            image = config.get("image", "N/A")
            container = config.get("container_name", "N/A")
            ports = config.get("ports", [])
            print(f"  - {name}: {image}")
            print(f"    container_name: {container}")
            print(f"    ports: {ports}")
            if config.get("healthcheck"):
                print(f"    healthcheck: defined")

        # Check volumes
        volumes = data.get("volumes", {})
        print(f"\nVolumes ({len(volumes)}):")
        for name in volumes.keys():
            print(f"  - {name}")

        # Check networks
        networks = data.get("networks", {})
        print(f"\nNetworks ({len(networks)}):")
        for name in networks.keys():
            print(f"  - {name}")

        # Validation checks
        print("\n" + "=" * 50)
        print("Validation Checks")
        print("=" * 50)

        checks = []

        # Check cdb_ prefix
        for name in services.keys():
            container = services[name].get("container_name", "")
            if container.startswith("cdb_"):
                checks.append(("cdb_ prefix for " + name, "PASS"))
            else:
                checks.append(("cdb_ prefix for " + name, "FAIL"))

        # Check healthchecks
        for name in services.keys():
            if services[name].get("healthcheck"):
                checks.append(("healthcheck for " + name, "PASS"))
            else:
                checks.append(("healthcheck for " + name, "FAIL"))

        # Check named volumes
        if "cdb_ollama_data" in volumes and "cdb_graphiti_data" in volumes:
            checks.append(("named volumes for persistence", "PASS"))
        else:
            checks.append(("named volumes for persistence", "FAIL"))

        # Check port security (127.0.0.1 binding)
        all_localhost = True
        for name, config in services.items():
            for port in config.get("ports", []):
                if isinstance(port, str) and not port.startswith("127.0.0.1:"):
                    all_localhost = False
        if all_localhost:
            checks.append(("localhost-only port bindings", "PASS"))
        else:
            checks.append(("localhost-only port bindings", "FAIL"))

        # Check depends_on
        graphiti = services.get("cdb_graphiti", {})
        depends = graphiti.get("depends_on", {})
        if "cdb_ollama" in depends:
            checks.append(("depends_on cdb_ollama", "PASS"))
        else:
            checks.append(("depends_on cdb_ollama", "FAIL"))

        for check, status in checks:
            symbol = "✓" if status == "PASS" else "✗"
            print(f"  [{symbol}] {check}: {status}")

        all_pass = all(s == "PASS" for _, s in checks)
        print("\n" + "=" * 50)
        if all_pass:
            print("RESULT: ALL CHECKS PASSED")
            return 0
        else:
            print("RESULT: SOME CHECKS FAILED")
            return 1

    except FileNotFoundError:
        print(f"ERROR: File not found: {compose_file}")
        return 1
    except yaml.YAMLError as e:
        print(f"ERROR: Invalid YAML syntax: {e}")
        return 1
    except Exception as e:
        print(f"ERROR: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
