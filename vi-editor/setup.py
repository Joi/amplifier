"""Setup script for vi editor."""

from setuptools import find_packages, setup

setup(
    name="vi-editor",
    version="0.1.0",
    description="A complete vi editor clone implementation in Python",
    author="Vi Editor Team",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[],
    entry_points={
        "console_scripts": [
            "vi=vi_editor.main:main",
            "vi-editor=vi_editor.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Topic :: Text Editors",
    ],
)
