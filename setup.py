from setuptools import setup

setup(
    name="gainsviz",
    packages=["gainsviz"],
    include_package_data=True,
    install_requires=[
        "flask",
        "pandas",
    ],
)
