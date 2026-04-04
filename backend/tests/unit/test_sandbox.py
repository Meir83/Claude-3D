"""Tests for the script sandbox validator."""
import pytest
from app.utils.sandbox import validate_script, SandboxViolation

VALID_SCRIPT = """\
import cadquery as cq

width = 40.0
height = 20.0

result = (
    cq.Workplane("XY")
    .box(width, 30.0, height, centered=(True, True, False))
)
"""

MALICIOUS_SCRIPTS = [
    # os.system
    ("import cadquery as cq\nimport os\nos.system('rm -rf /')\nresult=cq.Workplane('XY')", "os.system"),
    # subprocess
    ("import cadquery as cq\nimport subprocess\nsubprocess.run(['ls'])\nresult=cq.Workplane('XY')", "subprocess"),
    # eval
    ("import cadquery as cq\neval('1+1')\nresult=cq.Workplane('XY')", "eval"),
    # exec
    ("import cadquery as cq\nexec('x=1')\nresult=cq.Workplane('XY')", "exec"),
    # __import__
    ("import cadquery as cq\n__import__('os')\nresult=cq.Workplane('XY')", "__import__"),
    # socket
    ("import cadquery as cq\nimport socket\nresult=cq.Workplane('XY')", "socket"),
    # requests
    ("import cadquery as cq\nimport requests\nresult=cq.Workplane('XY')", "requests"),
    # open (write)
    ("import cadquery as cq\nopen('/etc/passwd', 'w')\nresult=cq.Workplane('XY')", "open"),
    # pickle
    ("import cadquery as cq\nimport pickle\nresult=cq.Workplane('XY')", "pickle"),
    # urllib
    ("import cadquery as cq\nimport urllib\nresult=cq.Workplane('XY')", "urllib"),
]


def test_valid_script_passes():
    validate_script(VALID_SCRIPT)  # Should not raise


@pytest.mark.parametrize("script,description", MALICIOUS_SCRIPTS)
def test_malicious_scripts_rejected(script: str, description: str):
    with pytest.raises(SandboxViolation):
        validate_script(script)


def test_script_too_large():
    huge = "import cadquery as cq\n" + "x = 1\n" * 100_000
    with pytest.raises(SandboxViolation, match="exceeds maximum size"):
        validate_script(huge)


def test_syntax_error_rejected():
    with pytest.raises(SandboxViolation, match="syntax"):
        validate_script("import cadquery as cq\nresult = (((")


def test_no_cadquery_import_rejected():
    with pytest.raises(SandboxViolation, match="must import cadquery"):
        validate_script("x = 1 + 1")


def test_numpy_allowed():
    script = "import cadquery as cq\nimport numpy as np\nresult = cq.Workplane('XY').box(1,1,1)"
    validate_script(script)  # Should not raise


def test_math_allowed():
    script = "import cadquery as cq\nimport math\nresult = cq.Workplane('XY').box(math.pi, 1, 1)"
    validate_script(script)  # Should not raise
