from setuptools import setup

setup(
    name='magisterka',
    version='1.0.0',
    description='Aplikacja Flask do zarządzania wydarzeniami i płatnościami.',
    author='Filip',
    author_email='your.email@example.com',
    py_modules=['app'],  # Uwzględnij pojedyncze moduły jak app.py
    include_package_data=True,  # Uwzględnia dane statyczne i pliki z MANIFEST.in
    packages=find_packages(),
    install_requires=[
        'flask',
        'configparser',
        'mysql-connector-python',
        'werkzeug',
        'wtforms',
    ],
    entry_points={
        'console_scripts': [
            'magisterka=app:main',  # Odpowiada za uruchomienie funkcji main w app.py
        ],
    },
    package_data={
        "": ["*.ini"],  # Uwzględnij pliki konfiguracyjne
        "templates": ["*.html"],  # Uwzględnij wszystkie pliki HTML z folderu templates
    },
)
