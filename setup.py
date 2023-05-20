import os
from setuptools import setup, find_packages

os.makedirs("E:/AI/NeuralGPT/NeuralGPT/src", exist_ok=True)
open("E:/AI/NeuralGPT/NeuralGPT/src/main.py", "a").close()

setup(
    name="NeuralGPT",
    version="0.1",
    author="Your Name",
    author_email="your.email@example.com",
    description="A project for neural GPT",
    packages=find_packages(),
    install_requires=[
        "tensorflow>=2.0.0",
        "numpy",
        "pandas"
    ]
)