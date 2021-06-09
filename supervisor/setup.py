import glob
import setuptools

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = f.readlines()

setuptools.setup(
    name="validator_supervisor",
    version="0.1.0",
    author="Jim Posen",
    author_email="jim.posen@gmail.com",
    description="Ethereum 2.0 validator supervisor",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jimpo/eth-staking",
    project_urls={
        "Bug Tracker": "https://github.com/jimpo/eth-staking/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=requirements,
    packages=[
        "validator_supervisor",
        "validator_supervisor.rpc",
        "validator_supervisor.validators",
    ],
    package_data={
        "validator_supervisor": [
            "images/lighthouse/Dockerfile",
            "images/lighthouse/run.sh",
            "images/prysm/Dockerfile",
            "images/prysm/run.sh",
        ],
    },
    python_requires=">=3.8",
)
