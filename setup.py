from setuptools import setup, find_packages

setup(
    name="repomapper",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "pytest>=7.2.1",
    ],
    entry_points={
        "console_scripts": [
            "repomapper=repomapper.cli:main",
        ],
    },
    python_requires=">=3.7",
    author="Your Name",
    description="Generate a map of code symbols from a directory",
    long_description=open("ROADMAP.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/vphantom/repomapper",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
