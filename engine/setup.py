"""
WorkBuddy Evolution Engine
让 WorkBuddy 具备自我进化和持久记忆能力的 pip 包
"""
from setuptools import setup, find_packages

setup(
    name="workbuddy-evolution",
    version="1.0.0",
    description="WorkBuddy AI Evolution Engine - Self-learning and persistent memory for WorkBuddy AI agents",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="liuboacean",
    author_email="",
    url="https://github.com/liuboacean/workbuddy-evolution-stack",
    py_modules=["evolution_engine"],
    python_requires=">=3.10",
    install_requires=[],  # 无外部依赖
    extras_require={
        "cli": [],  # 直接用 python3 -m workbuddy_evolution 运行
    },
    entry_points={
        "console_scripts": [
            "workbuddy-evolution=evolution_engine:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    license="MIT",
)
