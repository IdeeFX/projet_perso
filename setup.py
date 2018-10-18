#!/usr/bin/env python

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="harnais-diss-v2",
    version="1.1",
    author="François-Xavier Davanne",
    description="Dissemination harness between openwis and difmet",
    url="http://offre-dsi.meteo.fr/git/summary/?r=openwis/harnais-diss-v2.git",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    install_requires=["flask>=1.0.2",
                      "spyne==2.12.14",
                      "lxml>=3.6.0",
                      "setproctitle>=1.1.10",
                      "sftpserver>=0.3",
                      "pyftpdlib>=1.5.4",
                      "pyOpenSSL>=16.0.0",
                      "pytest>=3.8.0",
                      "pytest-cov>=2.6.0",
                      "zeep>=3.0.0",
                      "paramiko>=2.0.0",
                      "flask_sqlalchemy>=2.3.2"
                     ]
)