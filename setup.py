from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="sniff-cli",
    version="1.0.1",
    author="AlphaOneLabs",
    author_email="hello@alphaonelabs.com",
    description="A terminal-native AI-likelihood detection engine for Git repositories.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/alphaonelabs/sniff",
    packages=find_packages(),
    install_requires=[
        "typer>=0.12.3",
        "rich>=13.7.1",
        "questionary>=2.0.1",
        "gitpython>=3.1.43",
        "nltk>=3.8.1",
        "torch>=2.2.0",
        "transformers>=4.40.0",
        "numpy>=1.26.0",
        "sentence-transformers>=2.7.0",
        "plotille>=5.0.0",
        "pyfiglet>=1.0.2",
        "anthropic",
        "python-dotenv"
    ],
    entry_points={
        "console_scripts": [
            "sniff=sniff_cli.main:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Environment :: Console",
    ],
    python_requires=">=3.9",
)
