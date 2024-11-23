from setuptools import setup, find_packages

setup(
    name='magisterka',
    version='1.0.1',
    description='Aplikacja Flask do zarządzania wydarzeniami i płatnościami.',
    author='Filip',
    author_email='your.email@example.com',
    packages=find_packages(),  # Znajduje pakiety Pythona
    include_package_data=True,  # Uwzględnia dodatkowe pliki określone w MANIFEST.in
    install_requires=[
        'flask',
        'configparser',
        'mysql-connector-python',
        'werkzeug',
        'wtforms',
    ],
    entry_points={
        'console_scripts': [
            'magisterka=app:main',  # Zmień app:main, jeśli masz funkcję main w app.py
        ],
    },
    package_data={
        "": ["*.ini", "*.html"],  # Uwzględnij pliki .ini i .html
    },
)
