from setuptools import setup

setup(
    name='magisterka',
    version='1.0.4',
    description='Aplikacja Flask do zarządzania wydarzeniami i płatnościami.',
    author='Filip',
    author_email='your.email@example.com',
    py_modules=['app'],  # Uwzględnij pojedyncze moduły jak app.py
    include_package_data=True,  # Uwzględnia dane statyczne i pliki z MANIFEST.in
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
        "": ["*.ini", "templates/*.html"],  # Uwzględnij pliki konfiguracyjne i HTML
    },
)
