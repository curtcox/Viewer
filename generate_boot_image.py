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
from typing import Any, Dict, Set

from cid_core import generate_cid


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
        with open(file_path, 'rb') as f:
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

        # Store in cids directory
        cid_file_path = self.cids_dir / cid
        if not cid_file_path.exists():
            with open(cid_file_path, 'wb') as f:
                f.write(content)
            print(f"  Stored {relative_path} -> {cid}")
        else:
            print(f"  Already exists: {relative_path} -> {cid}")

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
                if key.endswith('_cid') or key.endswith('_file'):
                    # This is a file reference
                    if isinstance(value, str) and value.startswith('reference_templates/'):
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
                if key.endswith('_cid') or key.endswith('_file'):
                    # Replace filename with CID
                    if isinstance(value, str) and value.startswith('reference_templates/'):
                        if value in self.file_to_cid:
                            result[key] = self.file_to_cid[value]
                        else:
                            print(f"  WARNING: No CID found for {value}")
                            result[key] = value
                    else:
                        result[key] = value
                else:
                    result[key] = self.replace_filenames_with_cids(value)
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
        with open(source_path, 'r', encoding='utf-8') as f:
            source_data = json.load(f)

        # Process all referenced files
        print("\nProcessing referenced files...")
        self.process_referenced_files(source_data)

        # Replace filenames with CIDs
        print("\nReplacing filenames with CIDs...")
        templates_data = self.replace_filenames_with_cids(source_data)

        # Write templates.json
        target_path = self.reference_templates_dir / "templates.json"
        with open(target_path, 'w', encoding='utf-8') as f:
            json.dump(templates_data, f, indent=2)
        print(f"\nGenerated: {target_path}")

        # Generate CID for templates.json
        templates_json_content = json.dumps(templates_data, indent=2).encode('utf-8')
        templates_cid = generate_cid(templates_json_content)

        # Store templates.json CID
        cid_file_path = self.cids_dir / templates_cid
        with open(cid_file_path, 'wb') as f:
            f.write(templates_json_content)
        print(f"Stored templates.json -> {templates_cid}")

        return templates_cid

    def generate_boot_json(self, templates_cid: str, source_name: str = "boot") -> str:
        """Generate boot.json from a boot.source.json file.

        Args:
            templates_cid: CID of the templates.json file
            source_name: Name prefix for source/output files (e.g., "boot", "minimal", "default")

        Returns:
            CID of the generated boot.json
        """
        source_filename = f"{source_name}.boot.source.json" if source_name != "boot" else "boot.source.json"
        target_filename = f"{source_name}.boot.json" if source_name != "boot" else "boot.json"
        cid_filename = f"{source_name}.boot.cid" if source_name != "boot" else "boot.cid"

        print(f"\nStep 2: Processing {source_filename}")
        print("=" * 60)

        # Read boot.source.json
        source_path = self.reference_templates_dir / source_filename
        with open(source_path, 'r', encoding='utf-8') as f:
            source_data = json.load(f)

        # Process all referenced files (that weren't already processed)
        print("\nProcessing additional referenced files...")
        self.process_referenced_files(source_data)

        # Replace filenames with CIDs
        print("\nReplacing filenames with CIDs...")
        boot_data = self.replace_filenames_with_cids(source_data)

        # Replace GENERATED:templates.json marker with actual templates CID
        print(f"\nReplacing templates variable with CID: {templates_cid}")
        if 'variables' in boot_data:
            for var in boot_data['variables']:
                if var.get('name') == 'templates' and var.get('definition') == 'GENERATED:templates.json':
                    var['definition'] = templates_cid

        # Write boot.json
        target_path = self.reference_templates_dir / target_filename
        with open(target_path, 'w', encoding='utf-8') as f:
            json.dump(boot_data, f, indent=2)
        print(f"\nGenerated: {target_path}")

        # Generate CID for boot.json
        boot_json_content = json.dumps(boot_data, indent=2).encode('utf-8')
        boot_cid = generate_cid(boot_json_content)

        # Store boot.json CID
        cid_file_path = self.cids_dir / boot_cid
        with open(cid_file_path, 'wb') as f:
            f.write(boot_json_content)
        print(f"Stored {target_filename} -> {boot_cid}")

        # Save boot CID to boot.cid file
        boot_cid_file = self.reference_templates_dir / cid_filename
        with open(boot_cid_file, 'w', encoding='utf-8') as f:
            f.write(boot_cid)
        print(f"Saved boot CID to: {boot_cid_file}")

        return boot_cid

    def generate(self) -> Dict[str, str]:
        """Generate the complete boot image.

        Returns:
            Dictionary with 'templates_cid', 'minimal_boot_cid', and 'default_boot_cid' keys
        """
        print("Generating Boot Image")
        print("=" * 60)

        # Ensure cids directory exists
        self.ensure_cids_directory()

        # Generate templates.json and get its CID
        templates_cid = self.generate_templates_json()

        # Generate minimal.boot.json using the templates CID
        minimal_boot_cid = self.generate_boot_json(templates_cid, "minimal")

        # Generate default.boot.json using the templates CID
        default_boot_cid = self.generate_boot_json(templates_cid, "default")

        # Also generate legacy boot.json for backwards compatibility
        # This is a copy of minimal.boot.json
        boot_cid = self.generate_boot_json(templates_cid, "boot")

        # Summary
        print("\n" + "=" * 60)
        print("Boot Image Generation Complete")
        print("=" * 60)
        print(f"Templates CID:     {templates_cid}")
        print(f"Minimal Boot CID:  {minimal_boot_cid}")
        print(f"Default Boot CID:  {default_boot_cid}")
        print(f"Boot CID (legacy): {boot_cid}")
        print(f"\nTotal files processed: {len(self.processed_files)}")
        print("\nTo boot with these images, run:")
        print(f"  python main.py --boot-cid {minimal_boot_cid}  # Minimal boot (ai_stub only)")
        print(f"  python main.py --boot-cid {default_boot_cid}  # Default boot (all servers)")

        return {
            'templates_cid': templates_cid,
            'boot_cid': boot_cid,
            'minimal_boot_cid': minimal_boot_cid,
            'default_boot_cid': default_boot_cid
        }


def main():
    """Main entry point."""
    generator = BootImageGenerator()
    result = generator.generate()
    return result


if __name__ == '__main__':
    main()
