from setuptools import setup, find_packages

setup(
    name="bincache",
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'bincache = bincache.cli:main',
        ],
    },
    author="simpx",
    author_email="simpxx@gmail.com",
    description="Bincache is a command-line utility designed to cache the output of executable binaries and shell commands.",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    url="https://github.com/simpx/bincache",
    license='MIT',
    install_requires=[],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    tests_require=[
        'pytest',
        'pytest-mock',
    ],
    test_suite='tests',
)
