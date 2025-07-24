import fnmatch
import os
import re
import sys
import shutil
import subprocess
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


global ixnexception

SNAPPI_BRANCH=None
def get_snappi_dev_branch():
    if SNAPPI_BRANCH is not None and SNAPPI_BRANCH != "":
        print(f"Test is using this snappi branch {SNAPPI_BRANCH}")
        snappi_repo = "https://github.com/open-traffic-generator/snappi.git"
        run(
            [
            py() + " -m pip install git+{}@{}".format(snappi_repo,SNAPPI_BRANCH)])

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
    coverage_threshold = 50
    sanity_threshold = 50
    username = os.environ.get("TEST_USERNAME", "admin")
    psd = os.environ.get("TEST_PASSWORD", "wrinkle#B52#B52")

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
            '--location="https://10.36.70.119:443"',
            (
                '--ports="10.36.70.119;1;9'
                " 10.36.70.119;1;10"
                " 10.36.70.119;1;11"
                ' 10.36.70.119;1;12"'
            ),
            "--speed=speed_400_gbps",
        ]
    else:
        raise Exception("card %s is not supported for testing" % card)

    args += [
        "--ext=ixnetwork",
        "--username=" + username,
        "--psd='" + psd + "'",
        "tests",
        '-m "not e2e and not l1_manual and not uhd"',
        "--cov=./snappi_ixnetwork --cov-report term",
        " --cov-report html:cov_report",
        " -o junit_logging=all --junitxml=allure-results/report-pytest.xml"
    ]
    print(args)

    run(
        [
            py() + " -m pip install pytest-cov",
            py() + " -m pytest -sv {} | tee myfile.log ".format(" ".join(args)),
        ]
    )
    import re

    with open("./cov_report/index.html") as fp:
        out = fp.read()
        result = re.findall(r"data-ratio.*?[>](\d+)\b", out)[-1]
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
        select_tc, passed_tc, failed_tc, skip_test = extract_log()
        pass_rate = (int(passed_tc) / (int(failed_tc) + int(passed_tc))) * 100
        print(pass_rate)
        if int(pass_rate) < sanity_threshold:
            raise Exception(
                    "Sanity thresold[{0}] is NOT achieved[{1}]".format(
                        sanity_threshold, pass_rate
                    )
            )
        else:
            print(
                "Sanity thresold[{0}] is achieved[{1}]".format(
                    sanity_threshold, pass_rate
                )
            )


def extract_log():
    with open("myfile.log") as fp:
        out = fp.read()
        total_selected_tests = re.findall(r"collecting.*\s+(\d+)\s+selected", out)[0]
        total_passed_tests = re.findall(r"=.*\s(\d+)\s+passed", out)[0]
        if re.findall(r"=.*\s(\d+)\s+skipped",out):
            total_skipped_tests = re.findall(r"=.*\s(\d+)\s+skipped", out)[0]
        else:
            total_skipped_tests = 0

        total_failed_tests = int(total_selected_tests) - int(total_passed_tests) - int(total_skipped_tests)
        
    val1 = total_selected_tests
    val2 = total_passed_tests
    val3 = total_failed_tests
    val4 = total_skipped_tests

    return val1, val2, val3, val4
    
def generate_allure_report():
        run(["mkdir -p allure-results/history"])
        run(["cp -r $HOME/allure-report/history/* allure-results/history/"])
        run(["rm -rf $HOME/allure-report"])

        run(['echo "CI/CD-Information" > allure-results/environment.properties',
            'echo "Platform = snappi-ixnetwork" >> allure-results/environment.properties',
            'echo "Release = 5.15.0-60-generic" >> allure-results/environment.properties',
            'echo "OS-Version" >> allure-results/environment.properties',
            "lsb_release -a | sed -E 's/([^:]+) /\1-/g' | sed 's/:/=/g' > version.txt",
            'cat version.txt >> allure-results/environment.properties',
            'rm -rf version.txt',
            'echo "Environment-Details" >> allure-results/environment.properties',
            "python_ver=`python3 --version`",
            "pytest_ver=`pytest --version`",
            'echo "Python-Version = $python_ver" >> allure-results/environment.properties',
            'echo "Pytest-Version = $pytest_ver" >> allure-results/environment.properties',
            'go_ver=`go version`',
            'echo "Go-Version = $go_ver" >> allure-results/environment.properties',
            'allure_ver=$(docker exec "$CONTAINER_NAME" allure --version)',
            'echo "Allure-Version = $allure_ver" >> allure-results/environment.properties'])
        

        run(
        [
            "allure generate allure-results -c -o allure-report",
        ]
        )
        
        run(["cp -r allure-report $HOME/allure-report "])


def coverage_mail():

    test_start = (subprocess.check_output("echo $TIMESTAMP", shell=True)).decode('ascii')
    global result
    select_tc, passed_tc, failed_tc, skip_test = extract_log()
    pass_rate = (int(passed_tc) / (int(failed_tc) + int(passed_tc))) * 100

    with open("./cov_report/index.html") as fp:
        out = fp.read()
        result = re.findall(r"data-ratio.*?[>](\d+)\b", out)[-1]

    sender = "ixnetworksnappi@gmail.com"
    receiver = ["arkajyoti.dutta@keysight.com","indrani.bhattacharya@keysight.com","dipendu.ghosh@keysight.com","alakendu.jana@keysight.com", "satyam.singh@keysight.com", "subrata.sa@keysight.com"]
    # receiver = ["indrani.bhattacharya@keysight.com"]
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "Snappi-Ixnetwork Coverage Email"
    msg['From'] = sender
    msg['To'] = ", ".join(receiver)

    val1 = select_tc
    val2 = passed_tc
    val3 = failed_tc
    pass_rate = (int(val2) / (int(val2) + int(val3))) * 100
    val4 = pass_rate
    val5 = skip_test

    build_number = get_workflow_id()

    # Create the body of the message (a plain-text and an HTML version).
    text = "Hi!"
    html = """\
    <html>
    <style>
    table, th, td {
    border:1px solid black;
    }
    </style>
    <body>

    <p>Hi All,<br><br>
    Please find the coverage results for the build execution ID : <b>"""+str(build_number)+"""</b><br>
    Build started on : <b>"""+str(test_start)+""" IST</b><br><br>
    </p>

    <p><b>Test Coverage:</b></p>

    <table style="width:100%">
    <tr>
        <td>Test Coverage Percentage</td>
        <td>""" + str(result) + """</td>
    </tr>
    </table>

    <p><b>Test Summary:</b></p>

    <table style="width:100%">
    <tr>
        <td>Total Testcases</td>
        <td>""" + str(val1) + """</td>
    </tr>
    <tr>
        <td>Skipped Tests</td>
        <td>""" + str(val5) + """</td>
    </tr>
    <tr>
        <td>Test Passed</td>
        <td>""" + str(val2) + """</td>
    </tr>
    <tr>
        <td>Test Failed</td>
        <td>""" + str(val3) + """</td>
    </tr>
    <tr>
        <td>Pass Rate</td>
        <td>""" + str(val4) + """</td>
    </tr>
    </table>

    <p> Click on the url for detailed test execution summary : <a href="https://otg.dev/snappi-ixnetwork/" target="_blank">Report</a></p>
    

    <br><p>Thanks,<br>
        Snappi-Ixnetwork Team<br><br>
    </p>

    </body>
    </html>
    """
    #.format("200","198","2","99%")

    # Record the MIME types of both parts - text/plain and text/html.
    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(html, 'html')

    # Attach parts into message container.
    # According to RFC 2046, the last part of a multipart message, in this case
    # the HTML message, is best and preferred.
    msg.attach(part1)
    msg.attach(part2)

    # Send the message via local SMTP server.
    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.starttls()
    s.login(sender, "fbgt tiid rduu ajar")
    # sendmail function takes 3 arguments: sender's address, recipient's address
    # and message to send - here it is sent as one string.
    s.sendmail(sender, receiver, msg.as_string())
    s.quit()

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
        ixnexception = False
        # sys.exit(1)


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
