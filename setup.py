"""Packaging + dependency definition for Eagle Eye.

Install for use/dev:  pip install -e .[dev]
Build the macOS .app:  scripts/build-app.sh   (PyInstaller; see that script)
"""

from setuptools import setup, find_packages

setup(
    name="eagleeye",
    version="0.1.0",
    description="Personal macOS workflow tracker (app-time + keystrokes + screenshots)",
    packages=find_packages(),
    include_package_data=True,
    package_data={"eagleeye.analysis": ["*.template.md"]},
    python_requires=">=3.9",
    install_requires=[
        "rumps",
        "pynput==1.8.2",
        "Pillow",
        "pyobjc-framework-Cocoa",
        "pyobjc-framework-Quartz",
        "pyobjc-framework-ApplicationServices",
        'tomli; python_version < "3.11"',
    ],
    extras_require={"dev": ["ruff", "black", "pyinstaller"]},
    entry_points={"console_scripts": ["eagleeye = eagleeye.cli:main"]},
)
