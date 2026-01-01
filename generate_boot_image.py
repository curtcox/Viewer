#!/usr/bin/env python3
"""Generate boot image from reference templates.

This script:
1. Reads all files in /reference_templates
2. Generates CIDs for all referenced files
3. Stores CIDs in /cids directory
4. Converts templates.source.json to templates.json (filenames -> CIDs)
5. Converts minimal.boot.source.json to minimal.boot.json (filenames -> CIDs)
6. Converts default.boot.source.json to default.boot.json (filenames -> CIDs)
7. Ensures all generated CIDs are stored in /cids
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Set

from cid_core import generate_cid, is_literal_cid


class BootImageGenerator:
    """Generator for boot images from reference templates."""

    def __init__(self, base_dir: Path = None):
        """Initialize the generator.

        Args:
            base_dir: Base directory for the project (defaults to script location)
        """
        if base_dir is None:
            base_dir = Path(__file__).parent
        self.base_dir = base_dir
        self.reference_templates_dir = base_dir / "reference_templates"
        self.cids_dir = base_dir / "cids"
        self.processed_files: Set[str] = set()
        self.file_to_cid: Dict[str, str] = {}

    def ensure_cids_directory(self):
        """Ensure the cids directory exists."""
        self.cids_dir.mkdir(exist_ok=True)

    def read_file_content(self, file_path: Path) -> bytes:
        """Read file content as bytes.

        Args:
            file_path: Path to the file

        Returns:
            File content as bytes
        """
        with open(file_path, "rb") as f:
            return f.read()

    def generate_and_store_cid(self, file_path: Path, relative_path: str) -> str:
        """Generate CID for a file and store it in /cids.

        Args:
            file_path: Absolute path to the file
            relative_path: Relative path (used for tracking)

        Returns:
            The generated CID
        """
        # Check if already processed
        if relative_path in self.file_to_cid:
            return self.file_to_cid[relative_path]

        # Read content and generate CID
        content = self.read_file_content(file_path)
        cid = generate_cid(content)

        # Store in cids directory (skip literal CIDs - they contain the content itself)
        if not is_literal_cid(cid):
            cid_file_path = self.cids_dir / cid
            if not cid_file_path.exists():
                with open(cid_file_path, "wb") as f:
                    f.write(content)
                print(f"  Stored {relative_path} -> {cid}")
            else:
                print(f"  Already exists: {relative_path} -> {cid}")
        else:
            print(f"  Skipped literal CID: {relative_path} -> {cid}")

        # Track the mapping
        self.file_to_cid[relative_path] = cid
        self.processed_files.add(relative_path)

        return cid

    def process_referenced_files(self, data: Any, parent_path: str = "") -> None:
        """Recursively process all files referenced in JSON data.

        Args:
            data: JSON data (dict, list, or primitive)
            parent_path: Parent path for context (used in error messages)
        """
        if isinstance(data, dict):
            for key, value in data.items():
                if key == "templates" and isinstance(value, dict):
                    for template_name, template_value in value.items():
                        if isinstance(template_value, str) and template_value.startswith(
                            "reference_templates/"
                        ):
                            file_path = self.base_dir / template_value
                            if file_path.exists():
                                self.generate_and_store_cid(file_path, template_value)
                            else:
                                print(
                                    f"  WARNING: File not found: {template_value} (template {template_name})"
                                )
                    continue
                if key.endswith("_cid") or key.endswith("_file"):
                    # This is a file reference
                    if isinstance(value, str) and value.startswith(
                        "reference_templates/"
                    ):
                        file_path = self.base_dir / value
                        if file_path.exists():
                            self.generate_and_store_cid(file_path, value)
                        else:
                            print(f"  WARNING: File not found: {value}")
                elif isinstance(value, (dict, list)):
                    self.process_referenced_files(value, f"{parent_path}.{key}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                self.process_referenced_files(item, f"{parent_path}[{i}]")

    def process_server_definition_file(self, server_def_path: str) -> Optional[str]:
        """Process a server definition Python file to replace embedded filenames with CIDs.

        Args:
            server_def_path: Path to the server definition file (e.g., "reference_templates/servers/definitions/urleditor.py")

        Returns:
            CID of the processed server definition, or None if no changes needed
        """
        import re

        file_path = self.base_dir / server_def_path
        if not file_path.exists():
            return None

        # Read the server definition file
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Look for _load_resource_file calls with filename arguments
        # Pattern: _load_resource_file("filename.ext")
        pattern = r'_load_resource_file\(["\']([^"\']+)["\']\)'
        matches = re.findall(pattern, content)

        if not matches:
            # No embedded filenames found, return None to use original file
            return None

        # Process each referenced file
        server_dir = file_path.parent

        for filename in matches:
            resource_path = server_dir / filename
            if not resource_path.exists():
                print(
                    f"  WARNING: Referenced file not found: {filename} in {server_def_path}"
                )
                continue

            # Generate CID for the referenced file
            relative_resource_path = str(resource_path.relative_to(self.base_dir))
            resource_cid = self.generate_and_store_cid(
                resource_path, relative_resource_path
            )

            # Replace the filename with CID in the content
            # Replace _load_resource_file("filename") with direct content loading via CID
            # For now, we'll keep the filename but document it should be replaced
            print(f"    Found reference to {filename} -> {resource_cid}")

        # For now, return None - in production, we'd return a modified CID
        # The current implementation keeps filenames during development
        return None

    def _process_dict_value(self, key: str, value: Any) -> Any:
        """Process a single dictionary value during CID replacement.

        Args:
            key: The dictionary key
            value: The dictionary value

        Returns:
            The processed value (possibly replaced with a CID)
        """
        # Handle CID or file keys
        if key.endswith("_cid") or key.endswith("_file"):
            if isinstance(value, str) and value.startswith("reference_templates/"):
                if value in self.file_to_cid:
                    return self.file_to_cid[value]
                print(f"  WARNING: No CID found for {value}")
                return value
            return value

        if key == "templates" and isinstance(value, dict):
            result: dict[str, Any] = {}
            for template_name, template_value in value.items():
                if isinstance(template_value, str) and template_value.startswith(
                    "reference_templates/"
                ):
                    if template_value in self.file_to_cid:
                        result[template_name] = self.file_to_cid[template_value]
                    else:
                        print(f"  WARNING: No CID found for {template_value}")
                        result[template_name] = template_value
                else:
                    result[template_name] = template_value
            return result

        # Special handling for server definitions
        if key == "definition_cid":
            if isinstance(value, str) and value.endswith(".py"):
                # pylint: disable=assignment-from-none
                modified_cid = self.process_server_definition_file(value)
                if modified_cid:
                    return modified_cid
                # No changes needed, generate CID for original file
                if value in self.file_to_cid:
                    return self.file_to_cid[value]
                return value
            return value

        # Recursively process nested structures
        return self.replace_filenames_with_cids(value)

    def replace_filenames_with_cids(self, data: Any) -> Any:
        """Recursively replace filenames with CIDs in JSON data.

        Args:
            data: JSON data (dict, list, or primitive)

        Returns:
            Modified data with CIDs replacing filenames
        """
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                result[key] = self._process_dict_value(key, value)
            return result
        if isinstance(data, list):
            return [self.replace_filenames_with_cids(item) for item in data]
        return data

    def generate_templates_json(self) -> str:
        """Generate templates.json from templates.source.json.

        Returns:
            CID of the generated templates.json
        """
        print("\nStep 1: Processing templates.source.json")
        print("=" * 60)

        # Read templates.source.json
        source_path = self.reference_templates_dir / "templates.source.json"
        with open(source_path, "r", encoding="utf-8") as f:
            source_data = json.load(f)

        # Process all referenced files
        print("\nProcessing referenced files...")
        self.process_referenced_files(source_data)

        # Replace filenames with CIDs
        print("\nReplacing filenames with CIDs...")
        templates_data = self.replace_filenames_with_cids(source_data)

        # Write templates.json
        target_path = self.reference_templates_dir / "templates.json"
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(templates_data, f, indent=2)
        print(f"\nGenerated: {target_path}")

        # Generate CID for templates.json
        templates_json_content = json.dumps(templates_data, indent=2).encode("utf-8")
        templates_cid = generate_cid(templates_json_content)

        # Store templates.json CID (skip literal CIDs)
        if not is_literal_cid(templates_cid):
            cid_file_path = self.cids_dir / templates_cid
            with open(cid_file_path, "wb") as f:
                f.write(templates_json_content)
            print(f"Stored templates.json -> {templates_cid}")
        else:
            print(f"Skipped literal CID for templates.json -> {templates_cid}")

        return templates_cid

    def generate_uis_json(self) -> str:
        """Generate uis.json from uis.source.json.

        Returns:
            CID of the generated uis.json
        """
        print("\nProcessing uis.source.json")
        print("=" * 60)

        # Read uis.source.json
        source_path = self.reference_templates_dir / "uis.source.json"
        with open(source_path, "r", encoding="utf-8") as f:
            source_data = json.load(f)

        # Process all referenced files (if any)
        print("\nProcessing referenced files...")
        self.process_referenced_files(source_data)

        # Replace filenames with CIDs
        print("\nReplacing filenames with CIDs...")
        uis_data = self.replace_filenames_with_cids(source_data)

        # Write uis.json
        target_path = self.reference_templates_dir / "uis.json"
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(uis_data, f, indent=2)
        print(f"\nGenerated: {target_path}")

        # Generate CID for uis.json
        uis_json_content = json.dumps(uis_data, indent=2).encode("utf-8")
        uis_cid = generate_cid(uis_json_content)

        # Store uis.json CID (skip literal CIDs)
        if not is_literal_cid(uis_cid):
            cid_file_path = self.cids_dir / uis_cid
            with open(cid_file_path, "wb") as f:
                f.write(uis_json_content)
            print(f"Stored uis.json -> {uis_cid}")
        else:
            print(f"Skipped literal CID for uis.json -> {uis_cid}")

        return uis_cid

    def generate_gateways_json(self) -> str:
        """Generate gateways.json from gateways.source.json.

        Returns:
            CID of the generated gateways.json
        """
        print("\nProcessing gateways.source.json")
        print("=" * 60)

        # Read gateways.source.json
        source_path = self.reference_templates_dir / "gateways.source.json"
        with open(source_path, "r", encoding="utf-8") as f:
            source_data = json.load(f)

        # Process all referenced files (transform functions)
        print("\nProcessing referenced files...")
        self.process_referenced_files(source_data)

        # Replace filenames with CIDs
        print("\nReplacing filenames with CIDs...")
        gateways_data = self.replace_filenames_with_cids(source_data)

        # Write gateways.json
        target_path = self.reference_templates_dir / "gateways.json"
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(gateways_data, f, indent=2)
        print(f"\nGenerated: {target_path}")

        # Generate CID for gateways.json
        gateways_json_content = json.dumps(gateways_data, indent=2).encode("utf-8")
        gateways_cid = generate_cid(gateways_json_content)

        # Store gateways.json CID (skip literal CIDs)
        if not is_literal_cid(gateways_cid):
            cid_file_path = self.cids_dir / gateways_cid
            with open(cid_file_path, "wb") as f:
                f.write(gateways_json_content)
            print(f"Stored gateways.json -> {gateways_cid}")
        else:
            print(f"Skipped literal CID for gateways.json -> {gateways_cid}")

        return gateways_cid

    def generate_mcps_json(self) -> Optional[str]:
        """Generate mcps.json from mcps.source.json.

        Returns:
            CID of the generated mcps.json, or None if mcps.source.json doesn't exist
        """
        print("\nProcessing mcps.source.json")
        print("=" * 60)

        # Read mcps.source.json
        source_path = self.reference_templates_dir / "mcps.source.json"
        if not source_path.exists():
            print(f"Skipping: {source_path} does not exist")
            return None
            
        with open(source_path, "r", encoding="utf-8") as f:
            source_data = json.load(f)

        # Process all referenced files (config files)
        print("\nProcessing referenced files...")
        self.process_referenced_files(source_data)

        # Replace filenames with CIDs
        print("\nReplacing filenames with CIDs...")
        mcps_data = self.replace_filenames_with_cids(source_data)

        # Write mcps.json
        target_path = self.reference_templates_dir / "mcps.json"
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(mcps_data, f, indent=2)
        print(f"\nGenerated: {target_path}")

        # Generate CID for mcps.json
        mcps_json_content = json.dumps(mcps_data, indent=2).encode("utf-8")
        mcps_cid = generate_cid(mcps_json_content)

        # Store mcps.json CID (skip literal CIDs)
        if not is_literal_cid(mcps_cid):
            cid_file_path = self.cids_dir / mcps_cid
            with open(cid_file_path, "wb") as f:
                f.write(mcps_json_content)
            print(f"Stored mcps.json -> {mcps_cid}")
        else:
            print(f"Skipped literal CID for mcps.json -> {mcps_cid}")

        return mcps_cid

    def generate_boot_json(
        self,
        templates_cid: str,
        source_name: str = "boot",
        uis_cid: Optional[str] = None,
        gateways_cid: Optional[str] = None,
        mcps_cid: Optional[str] = None,
    ) -> str:
        """Generate boot.json from a boot.source.json file.

        Args:
            templates_cid: CID of the templates.json file
            source_name: Name prefix for source/output files (e.g., "boot", "minimal", "default")
            uis_cid: CID of the uis.json file (optional)
            gateways_cid: CID of the gateways.json file (optional)

        Returns:
            CID of the generated boot.json
        """
        source_filename = (
            f"{source_name}.boot.source.json"
            if source_name != "boot"
            else "boot.source.json"
        )
        target_filename = (
            f"{source_name}.boot.json" if source_name != "boot" else "boot.json"
        )
        cid_filename = (
            f"{source_name}.boot.cid" if source_name != "boot" else "boot.cid"
        )

        print(f"\nStep 2: Processing {source_filename}")
        print("=" * 60)

        # Read boot.source.json
        source_path = self.reference_templates_dir / source_filename
        with open(source_path, "r", encoding="utf-8") as f:
            source_data = json.load(f)

        # Process all referenced files (that weren't already processed)
        print("\nProcessing additional referenced files...")
        self.process_referenced_files(source_data)

        # Replace filenames with CIDs
        print("\nReplacing filenames with CIDs...")
        boot_data = self.replace_filenames_with_cids(source_data)

        # Replace GENERATED:templates.json marker with actual templates CID
        print(f"\nReplacing templates variable with CID: {templates_cid}")
        if "variables" in boot_data:
            for var in boot_data["variables"]:
                if (
                    var.get("name") == "templates"
                    and var.get("definition") == "GENERATED:templates.json"
                ):
                    var["definition"] = templates_cid
                # Replace GENERATED:uis.json marker with actual UIs CID
                if (
                    uis_cid
                    and var.get("name") == "uis"
                    and var.get("definition") == "GENERATED:uis.json"
                ):
                    print(f"Replacing uis variable with CID: {uis_cid}")
                    var["definition"] = uis_cid
                # Replace GENERATED:gateways.json marker with actual gateways CID
                if (
                    gateways_cid
                    and var.get("name") == "gateways"
                    and var.get("definition") == "GENERATED:gateways.json"
                ):
                    print(f"Replacing gateways variable with CID: {gateways_cid}")
                    var["definition"] = gateways_cid
                # Replace GENERATED:mcps.json marker with actual mcps CID
                if (
                    mcps_cid
                    and var.get("name") == "mcps"
                    and var.get("definition") == "GENERATED:mcps.json"
                ):
                    print(f"Replacing mcps variable with CID: {mcps_cid}")
                    var["definition"] = mcps_cid

        # Write boot.json
        target_path = self.reference_templates_dir / target_filename
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(boot_data, f, indent=2)
        print(f"\nGenerated: {target_path}")

        # Generate CID for boot.json
        boot_json_content = json.dumps(boot_data, indent=2).encode("utf-8")
        boot_cid = generate_cid(boot_json_content)

        # Store boot.json CID (skip literal CIDs)
        if not is_literal_cid(boot_cid):
            cid_file_path = self.cids_dir / boot_cid
            with open(cid_file_path, "wb") as f:
                f.write(boot_json_content)
            print(f"Stored {target_filename} -> {boot_cid}")
        else:
            print(f"Skipped literal CID for {target_filename} -> {boot_cid}")

        # Save boot CID to boot.cid file
        boot_cid_file = self.reference_templates_dir / cid_filename
        with open(boot_cid_file, "w", encoding="utf-8") as f:
            f.write(boot_cid)
        print(f"Saved boot CID to: {boot_cid_file}")

        return boot_cid

    def generate(self) -> Dict[str, str]:
        """Generate the complete boot image.

        Returns:
            Dictionary with 'templates_cid', 'uis_cid', 'gateways_cid', 'mcps_cid', 'minimal_boot_cid', 'default_boot_cid', and 'readonly_boot_cid' keys
        """
        print("Generating Boot Image")
        print("=" * 60)

        # Ensure cids directory exists
        self.ensure_cids_directory()

        # Generate templates.json and get its CID
        templates_cid = self.generate_templates_json()

        # Generate uis.json and get its CID
        uis_cid = self.generate_uis_json()

        # Generate gateways.json and get its CID
        gateways_cid = self.generate_gateways_json()

        # Generate mcps.json and get its CID
        mcps_cid = self.generate_mcps_json()

        minimal_boot_cid = self.generate_boot_json(
            templates_cid, "minimal", uis_cid, gateways_cid, mcps_cid
        )
        default_boot_cid = self.generate_boot_json(
            templates_cid, "default", uis_cid, gateways_cid, mcps_cid
        )
        readonly_boot_cid = self.generate_boot_json(
            templates_cid, "readonly", uis_cid, gateways_cid, mcps_cid
        )
        boot_cid = self.generate_boot_json(
            templates_cid, "boot", uis_cid, gateways_cid, mcps_cid
        )

        # Summary
        print("\n" + "=" * 60)
        print("Boot Image Generation Complete")
        print("=" * 60)
        print(f"Templates CID:     {templates_cid}")
        print(f"UIs CID:           {uis_cid}")
        print(f"Gateways CID:      {gateways_cid}")
        if mcps_cid:
            print(f"MCPs CID:          {mcps_cid}")
        print(f"Minimal Boot CID:  {minimal_boot_cid}")
        print(f"Default Boot CID:  {default_boot_cid}")
        print(f"Readonly Boot CID: {readonly_boot_cid}")
        print(f"Boot CID (legacy): {boot_cid}")
        print(f"\nTotal files processed: {len(self.processed_files)}")
        print("\nTo boot with these images, run:")
        print(
            f"  python main.py --boot-cid {minimal_boot_cid}  # Minimal boot (ai_stub only)"
        )
        print(
            f"  python main.py --boot-cid {default_boot_cid}  # Default boot (all servers)"
        )
        print(
            f"  python main.py --boot-cid {readonly_boot_cid}  # Readonly boot (no shell/file access)"
        )

        return {
            "templates_cid": templates_cid,
            "uis_cid": uis_cid,
            "gateways_cid": gateways_cid,
            "mcps_cid": mcps_cid,
            "boot_cid": boot_cid,
            "minimal_boot_cid": minimal_boot_cid,
            "default_boot_cid": default_boot_cid,
            "readonly_boot_cid": readonly_boot_cid,
        }


def main():
    """Main entry point."""
    generator = BootImageGenerator()
    result = generator.generate()
    return result


if __name__ == "__main__":
    main()
