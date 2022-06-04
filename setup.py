from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="advanced-collections",
    version="0.0.2",
    description="Extends the builtin collections with advanced collections, including fast resizing lists, sorted containers, better queues, and more.",
    packages=["advanced_collections", "advanced_collections.sorted"],
    python_requires=">=3.7",
    url="https://github.com/SimpleArt/advanced-collections",
    author="Jack Nguyen",
    author_email="jackyeenguyen@gmail.com",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
