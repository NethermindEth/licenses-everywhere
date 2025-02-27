"""
License manager for License Everywhere.
Handles license templates and customization.
"""

import os
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import jinja2
from .config import config


class LicenseManager:
    """Manager for license templates and customization."""

    # Dictionary of license types and their template files
    LICENSE_TYPES = {
        "MIT": "mit.txt",
        "Apache-2.0": "apache-2.0.txt",
        "GPL-3.0": "gpl-3.0.txt",
        "BSD-3-Clause": "bsd-3-clause.txt",
        "MPL-2.0": "mpl-2.0.txt",
        "LGPL-3.0": "lgpl-3.0.txt",
        "AGPL-3.0": "agpl-3.0.txt",
        "Unlicense": "unlicense.txt",
    }

    def __init__(self):
        """Initialize the license manager."""
        self._templates_dir = self._get_templates_dir()
        self._env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self._templates_dir),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def _get_templates_dir(self) -> Path:
        """Get the directory containing license templates."""
        # First check if templates are in the package directory
        package_dir = Path(__file__).parent
        templates_dir = package_dir / "templates"
        
        if templates_dir.exists():
            return templates_dir
        
        # If not found, create the directory and populate with default templates
        templates_dir.mkdir(exist_ok=True)
        self._create_default_templates(templates_dir)
        return templates_dir

    def _create_default_templates(self, templates_dir: Path) -> None:
        """Create default license templates."""
        # MIT License
        mit_template = """MIT License

Copyright (c) {{ year }} {{ copyright_holder }}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
        # Apache 2.0 License (abbreviated for brevity)
        apache_template = """                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   Copyright {{ year }} {{ copyright_holder }}

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
        # Create template files
        with open(templates_dir / "mit.txt", "w") as f:
            f.write(mit_template)
        
        with open(templates_dir / "apache-2.0.txt", "w") as f:
            f.write(apache_template)
        
        # Note: In a real implementation, we would include all license templates
        # For brevity, we're only including MIT and Apache 2.0 here

    def get_available_licenses(self) -> List[str]:
        """
        Get a list of available license types.
        
        Returns:
            List of license type names.
        """
        return list(self.LICENSE_TYPES.keys())

    def get_license_content(self, license_type: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Get the content of a license with variables filled in.
        
        Args:
            license_type: Type of license (e.g., "MIT", "Apache-2.0").
            context: Dictionary of variables to fill in the template.
            
        Returns:
            License content as a string.
            
        Raises:
            ValueError: If the license type is not supported.
        """
        if license_type not in self.LICENSE_TYPES:
            raise ValueError(f"Unsupported license type: {license_type}")
        
        template_file = self.LICENSE_TYPES[license_type]
        
        # Default context
        default_context = {
            "year": datetime.datetime.now().year,
            "copyright_holder": config.get("copyright_holder", ""),
        }
        
        # Merge with provided context
        if context:
            default_context.update(context)
        
        try:
            template = self._env.get_template(template_file)
            return template.render(**default_context)
        except jinja2.exceptions.TemplateNotFound:
            # If template not found, try to create it
            self._create_default_templates(self._templates_dir)
            template = self._env.get_template(template_file)
            return template.render(**default_context)

    def get_license_info(self, license_type: str) -> Dict[str, Any]:
        """
        Get information about a license type.
        
        Args:
            license_type: Type of license.
            
        Returns:
            Dictionary with license information.
            
        Raises:
            ValueError: If the license type is not supported.
        """
        if license_type not in self.LICENSE_TYPES:
            raise ValueError(f"Unsupported license type: {license_type}")
        
        # Basic info for now, could be expanded
        return {
            "name": license_type,
            "template_file": self.LICENSE_TYPES[license_type],
            "description": self._get_license_description(license_type),
        }

    def _get_license_description(self, license_type: str) -> str:
        """Get a description of a license type."""
        descriptions = {
            "MIT": "A short and simple permissive license with conditions only requiring preservation of copyright and license notices.",
            "Apache-2.0": "A permissive license that also provides an express grant of patent rights from contributors to users.",
            "GPL-3.0": "A copyleft license that requires anyone who distributes your code or a derivative work to make the source available under the same terms.",
            "BSD-3-Clause": "A permissive license similar to the MIT License, but with a non-endorsement clause.",
            "MPL-2.0": "A copyleft license that is file-based rather than project-based, allowing for more license compatibility.",
            "LGPL-3.0": "A copyleft license that allows you to link to the licensed library without requiring your code to be licensed under the same terms.",
            "AGPL-3.0": "A copyleft license similar to GPL but with an additional provision addressing use over a network.",
            "Unlicense": "A license with no conditions whatsoever which dedicates works to the public domain.",
        }
        return descriptions.get(license_type, "No description available.") 