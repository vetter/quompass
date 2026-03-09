"""Plugin namespace for third-party Quompass extensions.

Third-party packages can register backends, QEC schemes, and algorithm
templates via entry points in their ``pyproject.toml``::

    [project.entry-points."quompass.logical_estimators"]
    my_backend = "my_package.adapter:MyLogicalEstimator"

    [project.entry-points."quompass.physical_estimators"]
    my_backend = "my_package.adapter:MyPhysicalEstimator"

    [project.entry-points."quompass.qec_schemes"]
    my_code = "my_package.qec:MyQECScheme"

    [project.entry-points."quompass.algorithm_templates"]
    my_algo = "my_package.templates:MyTemplate"

See ``quompass.backends.base`` for the ``LogicalEstimator`` and
``PhysicalEstimator`` ABCs, ``quompass.core.qec`` for the ``QECScheme``
ABC, and ``quompass.templates.base`` for the ``AlgorithmTemplate`` ABC.
"""
