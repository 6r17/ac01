from setuptools import setup

setup(
    name="ac01",
    version="0.0.1",
    description="http server to boot up shell jobs",
    author="Patrick Borowy",
    author_email="6r17@protonmail.com",
    py_modules=["ac01"],
    install_requires=["aiohttp"],
    entry_points={"console_scripts": ["ac01 = ac01:run"]},
)
