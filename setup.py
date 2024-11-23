from setuptools import setup, find_packages

setup(
    name='scrapy-selenium',
    version='0.0.7',
    packages=find_packages(),
    install_requires=[
        'scrapy>=1.4.0',
        'selenium',
    ],
    url='https://github.com/AugustinCombes/scrapy-selenium',
    license='MIT',
    author='Augustin Combes',
    author_email='',
    description='Scrapy middleware to handle javascript pages using selenium'
)