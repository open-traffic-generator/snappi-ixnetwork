import fnmatch
import os
import re
import sys
import shutil
import subprocess
import platform
import hashlib
from version import Version 

BLACK_VERSION = "22.1.0"
GO_VERSION = "1.21.0"
PROTOC_VERSION = "3.20.3"

# this is where go and protoc shall be installed (and expected to be present)
LOCAL_PATH = os.path.join(os.path.expanduser("~"), ".local")
# path where protoc bin shall be installed or expected to be present
LOCAL_BIN_PATH = os.path.join(LOCAL_PATH, "bin")

models_version = Version.models_version
sdk_version = Version.version

# supported values - local openapiart path or None
USE_OPENAPIART_DIR = None
USE_MODELS_DIR = None

# supported values - branch name or None
USE_OPENAPIART_BRANCH = None
USE_MODELS_BRANCH = "cpdp-convergence"

OPENAPIART_REPO = "https://github.com/open-traffic-generator/openapiart.git"
MODELS_REPO = "https://github.com/open-traffic-generator/models.git"
OPENAPI_YAML_URL = "https://github.com/open-traffic-generator/models/releases/download/v{}/openapi.yaml".format(
    models_version
)


def generate_sdk():

    print("handle openapiart dependency")
    if USE_OPENAPIART_DIR is not None:
        sys.path.insert(0, USE_OPENAPIART_DIR)
    elif USE_OPENAPIART_BRANCH is not None:
        local_path = "openapiart"
        if not os.path.exists(local_path):
            subprocess.check_call(
                "git clone {} && cd {} && git checkout {} && cd ..".format(
                    OPENAPIART_REPO, local_path, USE_OPENAPIART_BRANCH
                ),
                shell=True,
            )
        sys.path.insert(0, local_path)

    import openapiart

    print("handle models dependency")
    if USE_MODELS_DIR is not None:
        API_FILES = [
            os.path.join(USE_MODELS_DIR, "api", "info.yaml"),
            os.path.join(USE_MODELS_DIR, "api", "api.yaml"),
        ]
    elif USE_MODELS_BRANCH is not None:
        local_path = "models"
        if not os.path.exists(local_path):
            subprocess.check_call(
                "git clone {} && cd {} && git checkout {} && cd ..".format(
                    MODELS_REPO, local_path, USE_MODELS_BRANCH
                ),
                shell=True,
            )
        API_FILES = [
            os.path.join(local_path, "api", "info.yaml"),
            os.path.join(local_path, "api", "api.yaml"),
        ]
    else:
        # download openapi.yaml
        import requests

        response = requests.request("GET", OPENAPI_YAML_URL, allow_redirects=True)
        assert response.status_code == 200
        with open(os.path.join("openapi.yaml"), "wb") as fp:
            fp.write(response.content)
        API_FILES = ["openapi.yaml"]

    print("generate python and go sdk")

    pkg_name = Version.package_name
    model_protobuf_name = Version.protobuf_name

    openapiart.OpenApiArt(
        api_files=API_FILES,
        protobuf_name=model_protobuf_name,
        artifact_dir="artifacts",
        extension_prefix=pkg_name,
        generate_version_api=True,
    ).GeneratePythonSdk(package_name=pkg_name, sdk_version=sdk_version)
    print(pkg_name)
    if os.path.exists(pkg_name):
        shutil.rmtree(pkg_name, ignore_errors=True)

    base_dir = os.path.abspath(os.path.dirname(__file__))

    # remove unwanted files
    shutil.copytree(os.path.join("artifacts", pkg_name), pkg_name)
    shutil.copyfile(
        os.path.join("artifacts", "requirements.txt"),
        os.path.join(base_dir, "requirements.txt"),
    )

    shutil.copyfile(
        os.path.join(base_dir, "artifacts", model_protobuf_name + ".proto"),
        os.path.join(base_dir, model_protobuf_name + ".proto"),
    )


    doc_dir = os.path.join(pkg_name, "docs")
    os.mkdir(doc_dir)
    shutil.move(os.path.join("artifacts", "openapi.yaml"), doc_dir)

    for name in os.listdir(pkg_name):
        if name != "artifacts":
            path = os.path.join(pkg_name, name)
            print(path + " will be published")

    print(pkg_name)
    print(os.listdir(pkg_name))
    run(
        [
            py() + " -m pip install {}".format(pkg_name)])


def generate_checksum(file):
    hash_sha256 = hashlib.sha256()
    with open(file, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def generate_distribution_checksum():
    tar_name = "{}-{}.tar.gz".format(*pkg())
    tar_file = os.path.join("dist", tar_name)
    tar_sha = os.path.join("dist", tar_name + ".sha.txt")
    with open(tar_sha, "w") as f:
        f.write(generate_checksum(tar_file))
    wheel_name = "{}-{}-py2.py3-none-any.whl".format(*pkg())
    wheel_file = os.path.join("dist", wheel_name)
    wheel_sha = os.path.join("dist", wheel_name + ".sha.txt")
    with open(wheel_sha, "w") as f:
        f.write(generate_checksum(wheel_file))
    print(tar_name)
    print(os.path.abspath(tar_name))
    run(
        [
            py() + " -m pip install {}".format(tar_name)])

def arch():
    return getattr(platform.uname(), "machine", platform.uname()[-1]).lower()


def on_arm():
    return arch() in ["arm64", "aarch64"]


def on_x86():
    return arch() == "x86_64"


def on_linux():
    print("The platform is {}".format(sys.platform))
    return "linux" in sys.platform


def get_protoc(version=PROTOC_VERSION, zipfile=None):
    if zipfile is None:
        if on_arm():
            zipfile = "protoc-" + version + "-linux-aarch_64.zip"
        elif on_x86():
            zipfile = "protoc-" + version + "-linux-x86_64.zip"
        else:
            print("host architecture not supported")
            return

    print("Installing protoc ...")

    if not os.path.exists(LOCAL_PATH):
        os.mkdir(LOCAL_PATH)

    cmd = "protoc --version 2> /dev/null || (curl -kL -o ./protoc.zip "
    cmd += (
        "https://github.com/protocolbuffers/protobuf/releases/download/v{}/{}".format(
            version, zipfile
        )
    )
    cmd += " && unzip -o ./protoc.zip -d {}".format(LOCAL_PATH)
    cmd += " && rm -rf ./protoc.zip"
    cmd += " && echo 'PATH=$PATH:{}' >> ~/.profile)".format(LOCAL_BIN_PATH)
    run([cmd])


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


def test(card="novus100g"):
    coverage_threshold = 67
    username = os.environ.get("TEST_USERNAME", "admin")
    psd = os.environ.get("TEST_PASSWORD", "admin")

    if card == "novus100g":
        args = [
            '--location="https://snappi-ixn-ci-novus100g.lbj.is.keysight.com:5000"',
            (
                '--ports="snappi-ixn-ci-novus100g.lbj.is.keysight.com;1;1'
                " snappi-ixn-ci-novus100g.lbj.is.keysight.com;1;2"
                " snappi-ixn-ci-novus100g.lbj.is.keysight.com;1;5"
                ' snappi-ixn-ci-novus100g.lbj.is.keysight.com;1;6"'
            ),
            "--speed=speed_100_gbps",
        ]
    elif card == "novus10g":
        args = [
            '--location="https://novus1-715849.ccu.is.keysight.com:443"',
            (
                '--ports="novus1-715849.ccu.is.keysight.com;1;1'
                " novus1-715849.ccu.is.keysight.com;1;2"
                " novus1-715849.ccu.is.keysight.com;1;5"
                ' novus1-715849.ccu.is.keysight.com;1;6"'
            ),
            "--speed=speed_10_gbps",
        ]
    else:
        raise Exception("card %s is not supported for testing" % card)

    args += [
        "--ext=ixnetwork",
        "--username=" + username,
        "--psd='" + psd + "'",
        "tests",
        '-m "not e2e and not l1_manual and not uhd"',
        "--cov=./snappi_ixnetwork --cov-report term"
        " --cov-report html:cov_report",
    ]
    print(args)

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
    if release_flag == "1":
        with open("setup.py") as f:
            out = f.read()
            snappi_convergence = re.findall(
                r"\"snappi_convergence==(.+)\"", out
            )[0]
        release_version = release_version.replace("v", "")
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
