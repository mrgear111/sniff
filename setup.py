from setuptools import setup, find_packages

setup(
    name="sniff-cli",
    version="1.0.0",
    description="Sniff out AI contributions in Git history",
    packages=find_packages(),
    install_requires=[
        "typer>=0.12.3",
        "rich>=13.7.1",
        "questionary>=2.0.1",
        "gitpython>=3.1.43",
        "nltk>=3.8.1"
    ],
    entry_points={
        "console_scripts": [
            "sniff=sniff_cli.main:main",
        ],
    },
)
