from setuptools import setup, find_packages

setup(
    name="ullama_python",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "ullama_python": ["libs/*.dll"],
    },
)
