from setuptools import setup, find_packages

setup(
    name="bincache",
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    packages=find_packages(),
    install_requires=[
        'six',
    ],
    python_requires=">=2.7, <4",
    entry_points={
        'console_scripts': [
            'bincache = bincache.cli:main',
        ],
    },
    author="simpx",
    author_email="simpxx@gmail.com",
    description="binary runner with cache",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    url="https://github.com/simpx/bincache",
    license='MIT',
    classifiers=[
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    tests_require=[
        'pytest',
        'pytest-mock',
    ],
)
