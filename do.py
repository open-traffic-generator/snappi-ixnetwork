import fnmatch
import os
import re
import sys
import shutil
import subprocess


def setup():
    run(
        [
            py() + " -m pip install --upgrade pip",
            py() + " -m pip install --upgrade virtualenv",
            py() + " -m virtualenv .env",
        ]
    )


def init():
    run(
        [
            py() + " -m pip install -r requirements.txt",
        ]
    )


def lint():
    paths = [pkg()[0], "tests", "setup.py", "do.py"]

    run(
        [
            py() + " -m black " + " ".join(paths),
            py() + " -m flake8 " + " ".join(paths),
        ]
    )


def test():
    coverage_threshold = 67
    #     args = [
    #         '--location="https://10.39.71.97:443"',
    #         (
    #             '--ports="10.39.65.230;6;1 10.39.65.230;6;2 10.39.65.230;6;3'
    #             ' 10.39.65.230;6;4"'
    #         ),
    #         '--media="fiber"',
    #         "tests",
    #         '-m "not e2e and not l1_manual"',
    #         '--cov=./snappi_ixnetwork --cov-report term'
    #         ' --cov-report html:cov_report',
    #     ]
    args = [
        '--location="https://otg-novus100g.lbj.is.keysight.com:5000"',
        (
            '--ports="otg-novus100g.lbj.is.keysight.com;1;1'
            " otg-novus100g.lbj.is.keysight.com;1;2"
            " otg-novus100g.lbj.is.keysight.com;1;5"
            ' otg-novus100g.lbj.is.keysight.com;1;6"'
        ),
        "--ext=ixnetwork",
        "--speed=speed_100_gbps",
        "tests",
        '-m "not e2e and not l1_manual and not uhd"',
        "--cov=./snappi_ixnetwork --cov-report term"
        " --cov-report html:cov_report",
    ]
    run(
        [
            py() + " -m pip install pytest-cov",
            py() + " -m pytest -sv {}".format(" ".join(args)),
        ]
    )
    import re

    with open("./cov_report/index.html") as fp:
        out = fp.read()
        result = re.findall(r"data-ratio.*?[>](\d+)\b", out)[0]
        if int(result) < coverage_threshold:
            raise Exception(
                "Coverage thresold[{0}] is NOT achieved[{1}]".format(
                    coverage_threshold, result
                )
            )
        else:
            print(
                "Coverage thresold[{0}] is achieved[{1}]".format(
                    coverage_threshold, result
                )
            )


def dist():
    clean()
    run(
        [
            py() + " setup.py sdist bdist_wheel --universal",
        ]
    )
    print(os.listdir("dist"))


def install():
    wheel = "{}-{}-py2.py3-none-any.whl".format(*pkg())
    run(
        [
            "{} -m pip install --upgrade --force-reinstall {}[testing]".format(
                py(), os.path.join("dist", wheel)
            ),
        ]
    )


def release():
    run(
        [
            py() + " -m pip install --upgrade twine",
            "{} -m twine upload -u {} -p {} dist/*".format(
                py(),
                os.environ["PYPI_USERNAME"],
                os.environ["PYPI_PASSWORD"],
            ),
        ]
    )


def clean():
    """
    Removes filenames or dirnames matching provided patterns.
    """
    pwd_patterns = [
        ".pytype",
        "dist",
        "build",
        "*.egg-info",
    ]
    recursive_patterns = [
        ".pytest_cache",
        ".coverage",
        "__pycache__",
        "*.pyc",
        "*.log",
    ]

    for pattern in pwd_patterns:
        for path in pattern_find(".", pattern, recursive=False):
            rm_path(path)

    for pattern in recursive_patterns:
        for path in pattern_find(".", pattern, recursive=True):
            rm_path(path)


def version():
    print(pkg()[-1])


def pkg():
    """
    Returns name of python package in current directory and its version.
    """
    try:
        return pkg.pkg
    except AttributeError:
        with open("setup.py") as f:
            out = f.read()
            name = re.findall(r"pkg_name = \"(.+)\"", out)[0]
            version = re.findall(r"version = \"(.+)\"", out)[0]

            pkg.pkg = (name, version)
        return pkg.pkg


def rm_path(path):
    """
    Removes a path if it exists.
    """
    if os.path.exists(path):
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)


def pattern_find(src, pattern, recursive=True):
    """
    Recursively searches for a dirname or filename matching given pattern and
    returns all the matches.
    """
    matches = []

    if not recursive:
        for name in os.listdir(src):
            if fnmatch.fnmatch(name, pattern):
                matches.append(os.path.join(src, name))
        return matches

    for dirpath, dirnames, filenames in os.walk(src):
        for names in [dirnames, filenames]:
            for name in names:
                if fnmatch.fnmatch(name, pattern):
                    matches.append(os.path.join(dirpath, name))

    return matches


def py():
    """
    Returns path to python executable to be used.
    """
    try:
        return py.path
    except AttributeError:
        py.path = os.path.join(".env", "bin", "python")
        if not os.path.exists(py.path):
            py.path = sys.executable

        # since some paths may contain spaces
        py.path = '"' + py.path + '"'
        return py.path


def run(commands):
    """
    Executes a list of commands in a native shell and raises exception upon
    failure.
    """
    try:
        for cmd in commands:
            print(cmd)
            if sys.platform != "win32":
                cmd = cmd.encode("utf-8", errors="ignore")
            subprocess.check_call(cmd, shell=True)
    except Exception:
        sys.exit(1)


def get_workflow_id():
    import requests

    cmd = "https://api.github.com/repos/open-traffic-generator/snappi-ixnetwork/actions/runs"
    res = requests.get(cmd)
    workflow_id = res.json()["workflow_runs"][0]["workflow_id"]
    return workflow_id


def check_release_flag(release_flag=None, release_version=None):
    if release_flag == '1':
        with open("setup.py") as f:
            out = f.read()
            snappi_convergence = re.findall(r"\"snappi_convergence==(.+)\"",out)[0]
        release_version = release_version.replace('v', "")
        with open("version.txt", "w+") as f:
            f.write("version: {}\n".format(release_version))
            f.write("snappi_convergence: {}\n".format(snappi_convergence))
    else:
        workflow_id = get_workflow_id()
        with open("version.txt", "w+") as f:
            f.write("workflow_id: {}".format(workflow_id))


def install_requests(path):
    cmd = "{} -m pip install requests".format(path)
    subprocess.check_call(cmd, shell=True)


def main():
    if len(sys.argv) >= 2:
        globals()[sys.argv[1]](*sys.argv[2:])
    else:
        print("usage: python do.py [args]")


if __name__ == "__main__":
    main()
