import setuptools

setuptools.setup(
    name="raydor",
    version="0.0.1",
    author="Joel Schumacher",
    author_email="joelschum@gmail.com",
    description="A static site generator",
    # long_description=long_description, # TODO: Read from README.md
    # long_description_content_type="text/markdown",
    url="https://github.com/pfirsich/raydor",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "Pygments==2.11.2",
        "Jinja2==3.0.3",
        "PyYAML==5.4.1",
        "Markdown==3.3.7",
    ],
    entry_points={
        "console_scripts": ["raydor=raydor.raydor:main"],
    },
)
