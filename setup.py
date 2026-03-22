from setuptools import setup, find_packages

setup(
    name="ozon_reports",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        'gspread',
        'oauth2client',
        'requests',
        'google-auth',
        'pandas',
        'flask',
    ],
    entry_points={
        'console_scripts': [
            'ozon-products=scripts.run_products_report:main',
        ],
    },
)