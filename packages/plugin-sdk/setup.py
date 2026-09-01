from setuptools import setup, find_packages

setup(
    name="reflow-plugin-sdk",
    version="1.0.0",
    description="Official Developer Plugin SDK for the Reflow Content Operating System",
    author="Reflow Open Source Community",
    packages=find_packages(),
    install_requires=[
        "pydantic>=2.0.0",
        "httpx>=0.24.0"
    ],
    python_requires=">=3.9",
)
