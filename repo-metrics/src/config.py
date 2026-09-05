"""Edit REPOS and the two date constants to change the sample."""

REPOS = [
    ("pandas",       "https://github.com/pandas-dev/pandas.git"),
    ("numpy",        "https://github.com/numpy/numpy.git"),
    ("scipy",        "https://github.com/scipy/scipy.git"),
    ("scikit-learn", "https://github.com/scikit-learn/scikit-learn.git"),
    ("matplotlib",   "https://github.com/matplotlib/matplotlib.git"),
    ("django",       "https://github.com/django/django.git"),
    ("sqlalchemy",   "https://github.com/sqlalchemy/sqlalchemy.git"),
    ("sympy",        "https://github.com/sympy/sympy.git"),
    ("ipython",      "https://github.com/ipython/ipython.git"),
    ("pytest",       "https://github.com/pytest-dev/pytest.git"),
]

SINCE = "2014-01-01"   # start of observation window (both panels)
UNTIL = None           # None => extraction date (today, UTC). Set "YYYY-MM-DD" to pin it.
